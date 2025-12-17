#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Cloud 存储后端

将文件上传到 Telegram 频道，通过 Bot API 获取和代理文件。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional

import requests

from ..base import StorageBackend, PutResult, DownloadResult
from ...config import logger


class TelegramBackend(StorageBackend):
    """Telegram Cloud 存储后端"""

    def __init__(self, *, name: str, bot_token: str, chat_id: int, proxy_url: Optional[str] = None):
        """
        初始化 Telegram 存储后端

        Args:
            name: 后端名称
            bot_token: Telegram Bot Token
            chat_id: 存储频道/群组 ID
            proxy_url: 可选代理 URL
        """
        self.name = name
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._session = requests.Session()
        self._session.trust_env = True
        proxy_url_norm = (proxy_url or "").strip()
        if proxy_url_norm:
            if "://" not in proxy_url_norm:
                proxy_url_norm = f"http://{proxy_url_norm}"
            self._session.proxies = {"http": proxy_url_norm, "https": proxy_url_norm}
            # 掩码代理凭据避免日志泄露
            masked = proxy_url_norm
            if "@" in masked:
                masked = masked.split("://")[0] + "://" + "***@" + masked.split("@")[-1]
            logger.info(f"Telegram 存储后端初始化: chat_id={chat_id}, proxy={masked}")
        else:
            logger.info(f"Telegram 存储后端初始化: chat_id={chat_id}")

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
            # 根据文件大小选择上传方式
            # Telegram 对 sendPhoto 有 10MB 限制，超过使用 sendDocument
            if file_size <= 10 * 1024 * 1024 and content_type.startswith('image/'):
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

            # 获取 file_id
            if file_size <= 10 * 1024 * 1024 and content_type.startswith('image/'):
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

            # 获取 file_path
            file_path = self._get_file_path(file_id) or ''

            logger.info(f"Telegram 存储上传成功: {file_id}")

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
                },
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
                for chunk in resp.iter_content(chunk_size=8192):
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
