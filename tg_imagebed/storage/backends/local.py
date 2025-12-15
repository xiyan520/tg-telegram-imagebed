#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地文件系统存储后端

将文件保存到服务器本地磁盘。
"""
from __future__ import annotations

import os
import uuid
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from ..base import StorageBackend, PutResult, DownloadResult
from ...config import logger


def _parse_range(range_header: str, total_size: int) -> Optional[Tuple[int, int]]:
    """解析 HTTP Range 头"""
    if not range_header:
        return None
    if not range_header.startswith('bytes='):
        return None
    spec = range_header[len('bytes='):].strip()
    if ',' in spec:
        return None
    if '-' not in spec:
        return None
    start_s, end_s = (spec.split('-', 1) + [''])[:2]
    try:
        if start_s == '':
            # suffix: bytes=-N
            length = int(end_s)
            if length <= 0:
                return None
            start = max(0, total_size - length)
            end = total_size - 1
            return (start, end)
        start = int(start_s)
        end = int(end_s) if end_s != '' else total_size - 1
        if start < 0 or end < start:
            return None
        return (start, min(end, total_size - 1))
    except Exception:
        return None


class LocalBackend(StorageBackend):
    """本地文件系统存储后端"""

    def __init__(self, *, name: str, root_dir: str):
        """
        初始化本地存储后端

        Args:
            name: 后端名称
            root_dir: 存储根目录
        """
        self.name = name
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        logger.info(f"本地存储后端初始化: {self._root}")

    def _generate_key(self, filename: str) -> str:
        """生成存储 key（按日期分目录）"""
        ext = Path(filename).suffix or ''
        t = time.gmtime()
        date_prefix = f"{t.tm_year:04d}/{t.tm_mon:02d}/{t.tm_mday:02d}"
        uid = uuid.uuid4().hex
        return f"{date_prefix}/{uid}{ext}"

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
        """上传文件到本地"""
        try:
            key = self._generate_key(filename)
            path = (self._root / key).resolve()

            # 安全检查：确保路径在根目录内
            if not str(path).startswith(str(self._root)):
                logger.error(f"路径安全检查失败: {path}")
                return None

            # 创建目录
            path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            path.write_bytes(file_content)

            logger.info(f"本地存储上传成功: {key} ({file_size} bytes)")

            return PutResult(
                file_id=key,
                file_path=key,
                file_size=file_size,
                storage_backend=self.name,
                storage_key=key,
                storage_meta={
                    'root_dir': str(self._root),
                    'content_type': content_type,
                    'original_filename': filename,
                },
            )
        except Exception as e:
            logger.error(f"本地存储上传失败: {e}")
            return None

    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """从本地下载文件"""
        key = (
            file_info.get('storage_key') or
            file_info.get('file_path') or
            file_info.get('file_id') or ''
        ).strip()

        if not key:
            return DownloadResult(
                status_code=404,
                content_type='text/plain',
                headers={},
                body=[b'not found']
            )

        path = (self._root / key).resolve()

        # 安全检查
        if not str(path).startswith(str(self._root)):
            return DownloadResult(
                status_code=403,
                content_type='text/plain',
                headers={},
                body=[b'forbidden']
            )

        if not path.exists() or not path.is_file():
            return DownloadResult(
                status_code=404,
                content_type='text/plain',
                headers={},
                body=[b'not found']
            )

        st = path.stat()
        total = int(st.st_size)
        content_type = file_info.get('mime_type') or 'application/octet-stream'

        # 解析 Range 头
        r = _parse_range(range_header or '', total) if range_header else None

        if not r:
            # 完整文件
            def body() -> Iterable[bytes]:
                with open(path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk

            return DownloadResult(
                status_code=200,
                content_type=content_type,
                headers={
                    'Content-Length': str(total),
                    'Accept-Ranges': 'bytes',
                },
                body=body(),
            )

        # 部分内容 (206)
        start, end = r
        length = end - start + 1

        def body() -> Iterable[bytes]:
            with open(path, 'rb') as f:
                f.seek(start, os.SEEK_SET)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return DownloadResult(
            status_code=206,
            content_type=content_type,
            headers={
                'Content-Length': str(length),
                'Content-Range': f'bytes {start}-{end}/{total}',
                'Accept-Ranges': 'bytes',
            },
            body=body(),
        )

    def delete(self, *, storage_key: str) -> bool:
        """删除本地文件"""
        try:
            path = (self._root / storage_key).resolve()
            if not str(path).startswith(str(self._root)):
                return False
            if path.exists():
                path.unlink()
                logger.info(f"本地存储删除成功: {storage_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"本地存储删除失败: {e}")
            return False

    def healthcheck(self) -> bool:
        """检查存储目录是否可写"""
        try:
            test_file = self._root / '.healthcheck'
            test_file.write_text('ok')
            test_file.unlink()
            return True
        except Exception:
            return False
