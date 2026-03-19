#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Cloud 存储后端

小文件继续走 Bot API，大文件在配置 api_id/api_hash 后切换到 Kurigram
（Pyrogram fork）走 MTProto，绕开 Bot API 的大文件限制。
"""
from __future__ import annotations

import asyncio
import io
import os
import queue
import re
import shutil
import threading
import time
import uuid
from typing import Any, Dict, Iterable, Optional
from urllib.parse import unquote, urlparse

import requests

from ..base import StorageBackend, PutResult, DownloadResult
from ...config import DATA_DIR, logger

_BOT_API_PHOTO_LIMIT = 10 * 1024 * 1024
_KURIGRAM_THRESHOLD = 20 * 1024 * 1024
_KURIGRAM_STREAM_CHUNK_SIZE = 1024 * 1024
_STREAM_CHUNK_SIZE = 8192
_KURIGRAM_CLIENT_CLASS = None
_KURIGRAM_CLIENT_CLASS_LOCK = threading.Lock()


class TelegramBackend(StorageBackend):
    """Telegram Cloud 存储后端"""

    def __init__(
        self,
        *,
        name: str,
        bot_token: str,
        chat_id: int,
        api_id: Optional[str] = None,
        api_hash: Optional[str] = None,
        proxy_url: Optional[str] = None,
    ):
        """
        初始化 Telegram 存储后端

        Args:
            name: 后端名称
            bot_token: Telegram Bot Token
            chat_id: 存储频道/群组 ID
            api_id: Telegram API ID（启用 Kurigram 大文件通道）
            api_hash: Telegram API Hash（启用 Kurigram 大文件通道）
            proxy_url: 可选代理 URL
        """
        self.name = name
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._api_id = str(api_id or "").strip()
        self._api_hash = str(api_hash or "").strip()
        self._session = requests.Session()
        self._session.trust_env = True
        proxy_url_norm = (proxy_url or "").strip()
        self._proxy_url = proxy_url_norm
        if proxy_url_norm:
            if "://" not in proxy_url_norm:
                proxy_url_norm = f"http://{proxy_url_norm}"
            self._session.proxies = {"http": proxy_url_norm, "https": proxy_url_norm}
            # 掩码代理凭据避免日志泄露
            masked = proxy_url_norm
            if "@" in masked:
                masked = masked.split("://")[0] + "://" + "***@" + masked.split("@")[-1]
            logger.info(
                f"Telegram 存储后端初始化: chat_id={chat_id}, proxy={masked}, "
                f"kurigram={'on' if self._can_use_kurigram() else 'off'}"
            )
        else:
            logger.info(
                f"Telegram 存储后端初始化: chat_id={chat_id}, "
                f"kurigram={'on' if self._can_use_kurigram() else 'off'}"
            )

    def _can_use_kurigram(self) -> bool:
        """是否具备 Kurigram/MTProto 所需配置"""
        return bool(self._bot_token and self._api_id and self._api_hash)

    def _should_use_kurigram_upload(self, file_size: int) -> bool:
        """超过 20 MB 时优先走 Kurigram 大文件上传"""
        return self._can_use_kurigram() and file_size > _KURIGRAM_THRESHOLD

    def _should_use_kurigram_download(self, *, file_size: int, file_path: str) -> bool:
        """
        大文件下载优先走 Kurigram。

        Bot API getFile/file 链路对大文件能力偏弱，文件路径缺失时也回退到 Kurigram。
        """
        return self._can_use_kurigram() and (file_size > _KURIGRAM_THRESHOLD or not file_path)

    def _build_kurigram_proxy(self) -> Optional[Dict[str, Any]]:
        """将 URL 形式代理转换为 Pyrogram/Kurigram 需要的 dict"""
        raw = (self._proxy_url or "").strip()
        if not raw:
            return None
        if "://" not in raw:
            raw = f"http://{raw}"

        parsed = urlparse(raw)
        if not parsed.hostname or not parsed.port:
            return None

        scheme = (parsed.scheme or "").lower()
        if scheme in {"socks5", "socks5h"}:
            pyrogram_scheme = "socks5"
        elif scheme in {"socks4", "socks4a"}:
            pyrogram_scheme = "socks4"
        elif scheme in {"http", "https"}:
            pyrogram_scheme = "http"
        else:
            logger.warning(f"Kurigram 不支持的代理协议: {scheme}")
            return None

        proxy: Dict[str, Any] = {
            "scheme": pyrogram_scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
        }
        if parsed.username:
            proxy["username"] = unquote(parsed.username)
        if parsed.password:
            proxy["password"] = unquote(parsed.password)
        return proxy

    def _build_kurigram_client(self):
        """构建 Kurigram Client（延迟导入，避免无依赖时启动失败）"""
        Client = self._get_kurigram_client_class()

        kwargs: Dict[str, Any] = {
            "name": f"tg_imagebed_{re.sub(r'[^a-zA-Z0-9_]+', '_', self.name or 'telegram')}",
            "api_id": self._api_id,
            "api_hash": self._api_hash,
            "bot_token": self._bot_token,
            "in_memory": True,
        }
        proxy = self._build_kurigram_proxy()
        if proxy:
            kwargs["proxy"] = proxy
        return Client(**kwargs)

    @staticmethod
    def _get_kurigram_client_class():
        """
        返回禁用 pyrogram.sync 包装层的 Client 子类。

        Kurigram 导出的 pyrogram 默认会在导入时给 Methods 打一层 sync shim。
        这层兼容逻辑在多线程 + 多事件循环场景下会把协程转投到别的 loop，
        直接引爆 "Future attached to a different loop"。
        """
        global _KURIGRAM_CLIENT_CLASS

        if _KURIGRAM_CLIENT_CLASS is not None:
            return _KURIGRAM_CLIENT_CLASS

        with _KURIGRAM_CLIENT_CLASS_LOCK:
            if _KURIGRAM_CLIENT_CLASS is not None:
                return _KURIGRAM_CLIENT_CLASS

            from pyrogram.client import Client as BaseClient
            from pyrogram.methods import Methods

            class AsyncKurigramClient(BaseClient):
                """专供本项目后台任务使用的纯 async Kurigram Client"""

            for name in dir(Methods):
                if name.startswith("_"):
                    continue
                method = getattr(Methods, name, None)
                original = getattr(method, "__wrapped__", None)
                if callable(original):
                    setattr(AsyncKurigramClient, name, original)

            _KURIGRAM_CLIENT_CLASS = AsyncKurigramClient
            return _KURIGRAM_CLIENT_CLASS

    def _run_async_task(self, coro_func):
        """
        在独立线程中运行异步任务。

        process_upload() 既会被 Flask 同步路由调用，也会被 Telegram Bot 的 async
        handler 调用，不能直接在这里 asyncio.run() 把现有事件循环顶翻。
        """
        result: Dict[str, Any] = {}
        error: Dict[str, BaseException] = {}

        def runner():
            try:
                result["value"] = asyncio.run(coro_func())
            except BaseException as exc:  # pragma: no cover - 透传给调用方
                error["value"] = exc

        thread = threading.Thread(target=runner, name=f"{self.name}-kurigram", daemon=True)
        thread.start()
        thread.join()
        if "value" in error:
            raise error["value"]
        return result.get("value")

    def _get_file_path(self, file_id: str) -> Optional[str]:
        """通过 Telegram API 获取文件路径"""
        if not self._bot_token or not file_id:
            return None
        try:
            resp = self._session.get(
                f"https://api.telegram.org/bot{self._bot_token}/getFile",
                params={'file_id': file_id},
                timeout=15,
            )
            if not resp.ok:
                return None
            data = resp.json() or {}
            if not data.get('ok'):
                return None
            result = data.get('result') or {}
            return result.get('file_path')
        except Exception as e:
            logger.error(f"获取 Telegram 文件路径失败: {e}")
            return None

    def _upload_via_bot_api(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_size: int,
        caption: str,
    ) -> Optional[PutResult]:
        """沿用现有 Bot API 上传逻辑"""
        # Telegram 对 sendPhoto 有 10MB 限制，超过使用 sendDocument
        if file_size <= _BOT_API_PHOTO_LIMIT and content_type.startswith('image/'):
            files = {'photo': (filename, file_content, content_type)}
            data = {'chat_id': self._chat_id, 'caption': caption or ''}
            resp = self._session.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendPhoto",
                files=files,
                data=data,
                timeout=60,
            )
        else:
            files = {'document': (filename, file_content, content_type)}
            data = {'chat_id': self._chat_id, 'caption': caption or ''}
            resp = self._session.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendDocument",
                files=files,
                data=data,
                timeout=120,
            )

        if not resp.ok:
            logger.error(f"Telegram 上传失败: HTTP {resp.status_code}")
            return None

        payload = resp.json() or {}
        if not payload.get('ok'):
            logger.error(f"Telegram 上传失败: {payload.get('description')}")
            return None

        result = payload.get('result') or {}

        if file_size <= _BOT_API_PHOTO_LIMIT and content_type.startswith('image/'):
            photos = result.get('photo') or []
            if not photos:
                logger.error("Telegram 上传失败: 无法获取 photo")
                return None
            file_id = photos[-1].get('file_id')
        else:
            doc = result.get('document') or {}
            file_id = doc.get('file_id')

        if not file_id:
            logger.error("Telegram 上传失败: 无法获取 file_id")
            return None

        file_path = self._get_file_path(file_id) or ''
        logger.info(f"Telegram 存储上传成功(Bot API): {file_id}")

        return PutResult(
            file_id=file_id,
            file_path=file_path,
            file_size=file_size,
            storage_backend=self.name,
            storage_key=file_id,
            storage_meta={
                'file_path': file_path,
                'uploaded_at': int(time.time()),
                'message_id': result.get('message_id'),
                'upload_transport': 'bot_api',
            },
        )

    def _upload_via_kurigram(
        self,
        *,
        file_content: bytes,
        filename: str,
        file_size: int,
        caption: str,
    ) -> PutResult:
        """通过 Kurigram 走 MTProto 上传大文件"""

        async def task():
            app = self._build_kurigram_client()
            payload = io.BytesIO(file_content)
            payload.name = filename or "upload.bin"

            async with app:
                message = await app.send_document(
                    chat_id=self._chat_id,
                    document=payload,
                    file_name=filename or None,
                    caption=caption or "",
                )

            document = getattr(message, "document", None)
            if not document or not getattr(document, "file_id", None):
                raise RuntimeError("Kurigram 上传成功但未返回 document.file_id")

            return {
                "file_id": document.file_id,
                "message_id": getattr(message, "id", None) or getattr(message, "message_id", None),
            }

        upload_data = self._run_async_task(task)
        file_id = str(upload_data.get("file_id") or "").strip()
        if not file_id:
            raise RuntimeError("Kurigram 未返回有效 file_id")

        file_path = self._get_file_path(file_id) or ""
        logger.info(f"Telegram 存储上传成功(Kurigram): {file_id}")

        return PutResult(
            file_id=file_id,
            file_path=file_path,
            file_size=file_size,
            storage_backend=self.name,
            storage_key=file_id,
            storage_meta={
                'file_path': file_path,
                'uploaded_at': int(time.time()),
                'message_id': upload_data.get("message_id"),
                'upload_transport': 'kurigram',
            },
        )

    def _download_to_temp_via_kurigram(self, *, file_id: str) -> str:
        """通过 Kurigram 下载到临时目录，返回实际文件路径"""
        temp_root = os.path.join(DATA_DIR, "tmp")
        os.makedirs(temp_root, exist_ok=True)
        temp_dir = os.path.join(temp_root, f"tg-imagebed-kurigram-{uuid.uuid4().hex}")
        os.makedirs(temp_dir, exist_ok=True)

        async def task():
            app = self._build_kurigram_client()
            async with app:
                return await app.download_media(file_id, file_name=temp_dir)

        try:
            downloaded_path = self._run_async_task(task)
            if not downloaded_path or not os.path.exists(downloaded_path):
                raise RuntimeError("Kurigram 下载未生成临时文件")
            return str(downloaded_path)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _download_via_kurigram_stream(
        self,
        *,
        file_id: str,
        file_info: Dict[str, Any],
        range_header: Optional[str],
        updated_fields: Optional[Dict[str, Any]],
    ) -> DownloadResult:
        """
        通过 Kurigram 直接流式读取媒体。

        旧实现会先把完整文件落到临时目录，再开始给 HTTP 客户端回数据。
        大文件下这会让直链首包时间长得离谱，看起来就像访问挂死了一样。
        """
        total_size = int(file_info.get('file_size') or 0)
        if total_size <= 0:
            raise RuntimeError("Kurigram 流式下载需要有效的 file_size")

        parsed_range = self._parse_range_header(range_header or "", total_size) if range_header else None
        if range_header and not parsed_range:
            return DownloadResult(
                status_code=416,
                content_type='text/plain',
                headers={'Content-Range': f'bytes */{total_size}'},
                body=[b'range not satisfiable'],
                updated_fields=updated_fields,
            )

        if parsed_range:
            start, end = parsed_range
            status_code = 206
            content_length = end - start + 1
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(content_length),
                'Content-Range': f'bytes {start}-{end}/{total_size}',
            }
        else:
            start, end = 0, total_size - 1
            status_code = 200
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(total_size),
            }

        stream_body = self._stream_kurigram_body(file_id=file_id, start=start, end=end)
        return DownloadResult(
            status_code=status_code,
            content_type=file_info.get('mime_type') or 'application/octet-stream',
            headers=headers,
            body=stream_body,
            updated_fields=updated_fields,
        )

    def _stream_kurigram_body(self, *, file_id: str, start: int, end: int) -> Iterable[bytes]:
        """
        把 Kurigram 的 async chunk 流桥接成 Flask 可消费的同步生成器。
        """
        if end < start:
            return iter(())

        event_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=8)
        abort_event = threading.Event()
        total_remaining = end - start + 1
        chunk_offset = start // _KURIGRAM_STREAM_CHUNK_SIZE
        limit_chunks = (end // _KURIGRAM_STREAM_CHUNK_SIZE) - chunk_offset + 1
        skip_bytes = start % _KURIGRAM_STREAM_CHUNK_SIZE

        def emit(kind: str, payload: Any) -> bool:
            while not abort_event.is_set():
                try:
                    event_queue.put((kind, payload), timeout=0.1)
                    return True
                except queue.Full:
                    continue
            return False

        async def task():
            remaining = total_remaining
            trim_leading = skip_bytes
            app = self._build_kurigram_client()

            async with app:
                async for chunk in app.stream_media(file_id, limit=limit_chunks, offset=chunk_offset):
                    if trim_leading:
                        chunk = chunk[trim_leading:]
                        trim_leading = 0
                    if not chunk:
                        continue
                    if len(chunk) > remaining:
                        chunk = chunk[:remaining]
                    remaining -= len(chunk)
                    if not emit("chunk", bytes(chunk)):
                        return
                    if remaining <= 0:
                        return

            if remaining > 0:
                raise RuntimeError(f"Kurigram 流式下载提前结束，剩余 {remaining} 字节未返回")

        def runner():
            try:
                asyncio.run(task())
            except BaseException as exc:  # pragma: no cover - 流式线程异常透传给消费端
                emit("error", exc)
            finally:
                emit("done", None)

        thread = threading.Thread(target=runner, name=f"{self.name}-kurigram-stream", daemon=True)
        thread.start()

        first_kind, first_payload = event_queue.get()
        if first_kind == "error":
            abort_event.set()
            thread.join(timeout=1)
            raise first_payload
        if first_kind == "done":
            abort_event.set()
            thread.join(timeout=1)
            raise RuntimeError("Kurigram 流式下载未返回任何数据")

        def body() -> Iterable[bytes]:
            try:
                yield first_payload
                while True:
                    kind, payload = event_queue.get()
                    if kind == "chunk":
                        yield payload
                        continue
                    if kind == "error":
                        logger.warning(f"Kurigram 流式下载中断: {type(payload).__name__}: {payload}")
                    break
            finally:
                abort_event.set()
                thread.join(timeout=1)

        return body()

    @staticmethod
    def _parse_range_header(range_header: str, total_size: int) -> Optional[tuple[int, int]]:
        """解析单段 Range 请求"""
        if not range_header:
            return None
        match = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
        if not match:
            return None

        start_raw, end_raw = match.groups()
        if not start_raw and not end_raw:
            return None

        if start_raw:
            start = int(start_raw)
            end = int(end_raw) if end_raw else total_size - 1
        else:
            suffix_len = int(end_raw)
            if suffix_len <= 0:
                return None
            start = max(total_size - suffix_len, 0)
            end = total_size - 1

        if start < 0 or end < start or start >= total_size:
            return None

        return start, min(end, total_size - 1)

    @staticmethod
    def _cleanup_local_artifact(path: str) -> None:
        """删除临时下载文件及其父目录"""
        if not path:
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        try:
            parent = os.path.dirname(path)
            if parent and os.path.basename(parent).startswith("tg-imagebed-kurigram-"):
                shutil.rmtree(parent, ignore_errors=True)
        except Exception:
            pass

    def _download_from_local_file(
        self,
        *,
        temp_path: str,
        file_info: Dict[str, Any],
        range_header: Optional[str],
        updated_fields: Optional[Dict[str, Any]],
    ) -> DownloadResult:
        """将临时文件包装成统一下载响应"""
        total_size = os.path.getsize(temp_path)
        parsed_range = self._parse_range_header(range_header or "", total_size) if range_header else None

        if range_header and not parsed_range:
            self._cleanup_local_artifact(temp_path)
            return DownloadResult(
                status_code=416,
                content_type='text/plain',
                headers={'Content-Range': f'bytes */{total_size}'},
                body=[b'range not satisfiable'],
                updated_fields=updated_fields,
            )

        if parsed_range:
            start, end = parsed_range
            status_code = 206
            content_length = end - start + 1
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(content_length),
                'Content-Range': f'bytes {start}-{end}/{total_size}',
            }
        else:
            start, end = 0, total_size - 1
            status_code = 200
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(total_size),
            }

        def body() -> Iterable[bytes]:
            try:
                with open(temp_path, 'rb') as fh:
                    fh.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk = fh.read(min(_STREAM_CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            finally:
                self._cleanup_local_artifact(temp_path)

        return DownloadResult(
            status_code=status_code,
            content_type=file_info.get('mime_type') or 'application/octet-stream',
            headers=headers,
            body=body(),
            updated_fields=updated_fields,
        )

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
        """上传文件到 Telegram"""
        if not self._bot_token or not self._chat_id:
            logger.error("Telegram 存储后端未配置 bot_token 或 chat_id")
            return None

        try:
            if self._should_use_kurigram_upload(file_size):
                try:
                    return self._upload_via_kurigram(
                        file_content=file_content,
                        filename=filename,
                        file_size=file_size,
                        caption=caption,
                    )
                except Exception as e:
                    logger.warning(f"Kurigram 上传失败，回退 Bot API: {type(e).__name__}: {e}")

            return self._upload_via_bot_api(
                file_content=file_content,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                caption=caption,
            )
        except Exception as e:
            logger.error(f"Telegram 存储上传异常: {e}")
            return None

    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """从 Telegram 下载文件"""
        file_id = (
            file_info.get('storage_key') or
            file_info.get('file_id') or ''
        ).strip()
        file_path = (file_info.get('file_path') or '').strip()
        file_size = int(file_info.get('file_size') or 0)

        if not file_id:
            return DownloadResult(
                status_code=404,
                content_type='text/plain',
                headers={},
                body=[b'not found']
            )

        # 刷新 file_path（Telegram 的 file_path 会过期）
        fresh = self._get_file_path(file_id)
        updated_fields: Optional[Dict[str, Any]] = None
        if fresh and fresh != file_path:
            file_path = fresh
            updated_fields = {'file_path': fresh}

        if self._should_use_kurigram_download(file_size=file_size, file_path=file_path):
            try:
                return self._download_via_kurigram_stream(
                    file_id=file_id,
                    file_info=file_info,
                    range_header=range_header,
                    updated_fields=updated_fields,
                )
            except Exception as e:
                logger.warning(f"Kurigram 流式下载失败，回退临时文件方案: {type(e).__name__}: {e}")
                try:
                    temp_path = self._download_to_temp_via_kurigram(file_id=file_id)
                    return self._download_from_local_file(
                        temp_path=temp_path,
                        file_info=file_info,
                        range_header=range_header,
                        updated_fields=updated_fields,
                    )
                except Exception as e2:
                    logger.warning(f"Kurigram 下载失败，回退 Bot API: {type(e2).__name__}: {e2}")

        if not file_path:
            return DownloadResult(
                status_code=404,
                content_type='text/plain',
                headers={},
                body=[b'file path not available'],
                updated_fields=updated_fields
            )

        # 构建文件 URL
        if file_path.startswith('https://'):
            file_url = file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{self._bot_token}/{file_path}"

        # 请求文件
        headers: Dict[str, str] = {}
        if range_header:
            headers['Range'] = range_header

        try:
            resp = self._session.get(file_url, stream=True, timeout=60, headers=headers)
        except Exception as e:
            logger.error(f"Telegram 下载失败: {e}")
            return DownloadResult(
                status_code=502,
                content_type='text/plain',
                headers={},
                body=[b'upstream error'],
                updated_fields=updated_fields
            )

        if resp.status_code not in (200, 206):
            return DownloadResult(
                status_code=resp.status_code,
                content_type='text/plain',
                headers={},
                body=[b'upstream error'],
                updated_fields=updated_fields
            )

        def body() -> Iterable[bytes]:
            try:
                for chunk in resp.iter_content(chunk_size=_STREAM_CHUNK_SIZE):
                    if chunk:
                        yield chunk
            finally:
                resp.close()

        out_headers: Dict[str, str] = {'Accept-Ranges': 'bytes'}
        if 'content-length' in resp.headers:
            out_headers['Content-Length'] = resp.headers['content-length']
        if 'content-range' in resp.headers:
            out_headers['Content-Range'] = resp.headers['content-range']

        return DownloadResult(
            status_code=resp.status_code,
            content_type=file_info.get('mime_type') or resp.headers.get('content-type', 'application/octet-stream'),
            headers=out_headers,
            body=body(),
            updated_fields=updated_fields,
        )

    def healthcheck(self) -> bool:
        """检查 Bot Token 是否有效"""
        if not self._bot_token:
            return False
        try:
            resp = self._session.get(
                f"https://api.telegram.org/bot{self._bot_token}/getMe",
                timeout=10
            )
            return resp.ok and resp.json().get('ok', False)
        except Exception:
            return False
