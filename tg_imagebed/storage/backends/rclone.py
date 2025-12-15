#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rclone 存储后端

通过 rclone CLI 支持各种网盘存储（OneDrive、Google Drive、Dropbox 等）。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..base import StorageBackend, PutResult, DownloadResult
from ...config import logger


def _is_not_found(stderr_text: str) -> bool:
    """检查错误是否为'文件不存在'"""
    s = (stderr_text or "").lower()
    return any(
        token in s
        for token in [
            "not found",
            "object not found",
            "no such file or directory",
            "couldn't find object",
            "error 404",
        ]
    )


def _safe_join_posix(base: str, key: str) -> str:
    """安全拼接路径"""
    base = (base or "").strip().strip("/")
    key = (key or "").strip().lstrip("/")
    if not base:
        return key
    if not key:
        return base
    return str(PurePosixPath(base) / PurePosixPath(key))


def _parse_http_range(range_header: str) -> Optional[Tuple[int, Optional[int]]]:
    """解析 HTTP Range 头"""
    if not range_header:
        return None
    value = range_header.strip()
    if not value.startswith("bytes="):
        return None
    spec = value[len("bytes="):].strip()
    if "," in spec:
        return None
    if "-" not in spec:
        return None
    start_s, end_s = spec.split("-", 1)
    start_s = start_s.strip()
    end_s = end_s.strip()
    if start_s == "":
        return None
    try:
        start = int(start_s)
        if start < 0:
            return None
        end: Optional[int]
        if end_s == "":
            end = None
        else:
            end = int(end_s)
            if end < start:
                return None
        return (start, end)
    except Exception:
        return None


class RcloneBackend(StorageBackend):
    """rclone 存储后端"""

    def __init__(
        self,
        *,
        name: str,
        rclone_bin: str = "rclone",
        config_path: str = "",
        remote: str,
        base_path: str = "",
        cli_flags: Optional[List[str]] = None,
        upload: Optional[Dict[str, Any]] = None,
        download: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 rclone 存储后端

        Args:
            name: 后端名称
            rclone_bin: rclone 可执行文件路径
            config_path: rclone 配置文件路径
            remote: rclone remote 名称
            base_path: remote 下的基础路径
            cli_flags: 额外的 rclone 命令行参数
            upload: 上传配置
            download: 下载配置
        """
        self.name = name
        self._rclone_bin = (rclone_bin or "rclone").strip()
        self._config_path = (config_path or "").strip()
        self._remote = (remote or "").strip().rstrip(":")
        self._base_path = (base_path or "").strip()
        self._cli_flags = list(cli_flags or [])

        upload_cfg = upload or {}
        download_cfg = download or {}

        self._spool_mb = int(upload_cfg.get("spool_mb", 16))
        self._retries = int(upload_cfg.get("retries", 1))
        self._upload_timeout = int(upload_cfg.get("timeout_seconds", 180))
        self._download_timeout = int(download_cfg.get("timeout_seconds", 60))
        self._stat_timeout = int(download_cfg.get("stat_timeout_seconds", 15))
        self._enable_range = bool(download_cfg.get("enable_range", True))

        if not self._remote:
            raise ValueError("rclone backend requires 'remote'")

        logger.info(f"rclone 存储后端初始化: {self._remote}:{self._base_path}")

    def _base_cmd(self) -> List[str]:
        """构建基础命令"""
        cmd = [self._rclone_bin]
        if self._config_path:
            cmd += ["--config", self._config_path]
        cmd += self._cli_flags
        return cmd

    def _object_path(self, key: str) -> str:
        """构建完整的 remote 路径"""
        rel = _safe_join_posix(self._base_path, key)
        return f"{self._remote}:{rel}"

    def _generate_key(self, filename: str) -> str:
        """生成存储 key"""
        ext = os.path.splitext(filename or "")[1]
        t = time.gmtime()
        date_prefix = f"{t.tm_year:04d}/{t.tm_mon:02d}/{t.tm_mday:02d}"
        uid = uuid.uuid4().hex
        return f"{date_prefix}/{uid}{ext}"

    def _run_capture(self, *, args: List[str], timeout_seconds: int) -> subprocess.CompletedProcess:
        """运行命令并捕获输出"""
        try:
            return subprocess.run(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError as e:
            raise RuntimeError("rclone binary not found") from e
        except subprocess.TimeoutExpired as e:
            raise TimeoutError("rclone command timeout") from e

    def _stat_size(self, key: str) -> Optional[int]:
        """获取文件大小"""
        obj = self._object_path(key)
        args = self._base_cmd() + ["lsjson", "--stat", obj]
        try:
            cp = self._run_capture(args=args, timeout_seconds=self._stat_timeout)
        except Exception as e:
            logger.warning(f"rclone stat failed: {e}")
            return None
        if cp.returncode != 0:
            return None
        try:
            payload = json.loads((cp.stdout or b"").decode("utf-8", errors="replace"))
            if isinstance(payload, dict) and "Size" in payload:
                return int(payload["Size"])
            return None
        except Exception:
            return None

    def put_bytes(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_size: int,
        caption: str,
        source: str,
        username: str,
    ) -> Optional[PutResult]:
        """上传文件到 rclone remote"""
        key = self._generate_key(filename)
        obj = self._object_path(key)

        spool_threshold = max(0, self._spool_mb) * 1024 * 1024
        use_spool = file_size >= spool_threshold and spool_threshold > 0

        last_err = ""
        for attempt in range(max(1, self._retries) + 1):
            try:
                if use_spool:
                    # 大文件：先写临时文件，再用 copyto
                    with tempfile.NamedTemporaryFile(
                        prefix="img_",
                        suffix=os.path.splitext(filename or "")[1],
                        delete=False
                    ) as f:
                        tmp_path = f.name
                        f.write(file_content)
                    try:
                        args = self._base_cmd() + ["copyto", tmp_path, obj]
                        cp = self._run_capture(args=args, timeout_seconds=self._upload_timeout)
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                else:
                    # 小文件：通过 stdin 使用 rcat
                    args = self._base_cmd() + ["rcat", obj]
                    try:
                        p = subprocess.Popen(
                            args,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                    except FileNotFoundError as e:
                        raise RuntimeError("rclone binary not found") from e
                    try:
                        stdout, stderr = p.communicate(input=file_content, timeout=self._upload_timeout)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        stdout, stderr = p.communicate()
                        raise TimeoutError("rclone upload timeout")
                    cp = subprocess.CompletedProcess(args=args, returncode=p.returncode, stdout=stdout, stderr=stderr)

                if cp.returncode == 0:
                    logger.info(f"rclone 存储上传成功: {key}")
                    return PutResult(
                        file_id=key,
                        file_path=key,
                        file_size=file_size,
                        storage_backend=self.name,
                        storage_key=key,
                        storage_meta={
                            "driver": "rclone",
                            "remote": self._remote,
                            "base_path": self._base_path,
                            "content_type": content_type,
                        },
                    )

                last_err = (cp.stderr or b"").decode("utf-8", errors="replace")
                logger.error(f"rclone upload failed (attempt {attempt}): {last_err}")
            except Exception as e:
                last_err = str(e)
                logger.error(f"rclone upload exception (attempt {attempt}): {e}")

            time.sleep(min(1.0 * attempt, 3.0))

        return None

    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """从 rclone remote 下载文件"""
        key = (
            file_info.get("storage_key") or
            file_info.get("file_path") or
            file_info.get("file_id") or ""
        ).strip()

        if not key:
            return DownloadResult(
                status_code=404,
                content_type="text/plain",
                headers={},
                body=[b"not found"]
            )

        obj = self._object_path(key)
        want_range = self._enable_range and bool(range_header)
        parsed = _parse_http_range(range_header or "") if want_range else None

        size = self._stat_size(key) if want_range else None
        offset: Optional[int] = None
        count: Optional[int] = None
        if parsed:
            start, end = parsed
            offset = start
            if end is not None:
                count = (end - start) + 1

        args = self._base_cmd() + ["cat", obj]
        if parsed and offset is not None:
            args += ["--offset", str(offset)]
            if count is not None:
                args += ["--count", str(count)]

        try:
            p = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            return DownloadResult(
                status_code=503,
                content_type="text/plain",
                headers={},
                body=[b"backend unavailable"]
            )

        def body() -> Iterable[bytes]:
            try:
                assert p.stdout is not None
                while True:
                    chunk = p.stdout.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                try:
                    if p.stdout:
                        p.stdout.close()
                except Exception:
                    pass
                try:
                    if p.stderr:
                        p.stderr.close()
                except Exception:
                    pass
                try:
                    p.wait(timeout=1)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass

        content_type = file_info.get("mime_type") or "application/octet-stream"

        if not parsed:
            return DownloadResult(
                status_code=200,
                content_type=content_type,
                headers={"Accept-Ranges": "bytes"},
                body=body(),
            )

        headers: Dict[str, str] = {"Accept-Ranges": "bytes"}
        if offset is not None:
            end_pos: Optional[int]
            if count is not None:
                end_pos = offset + count - 1
            else:
                end_pos = None
            if end_pos is not None:
                total_s = "*" if size is None else str(size)
                headers["Content-Range"] = f"bytes {offset}-{end_pos}/{total_s}"
            else:
                total_s = "*" if size is None else str(size)
                headers["Content-Range"] = f"bytes {offset}-/{total_s}"

        return DownloadResult(
            status_code=206,
            content_type=content_type,
            headers=headers,
            body=body(),
        )

    def delete(self, *, storage_key: str) -> bool:
        """删除文件"""
        try:
            obj = self._object_path(storage_key)
            args = self._base_cmd() + ["deletefile", obj]
            cp = self._run_capture(args=args, timeout_seconds=30)
            return cp.returncode == 0
        except Exception as e:
            logger.error(f"rclone delete failed: {e}")
            return False

    def healthcheck(self) -> bool:
        """检查 rclone 是否可用"""
        try:
            args = self._base_cmd() + ["version"]
            cp = self._run_capture(args=args, timeout_seconds=10)
            return cp.returncode == 0
        except Exception:
            return False
