#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Cloud storage backend.

Uploads files to Telegram and proxies them back through the app.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional

import requests

from ..base import DownloadResult, PutResult, StorageBackend
from ...config import logger


class TelegramBackend(StorageBackend):
    """Telegram Cloud storage backend."""

    def __init__(self, *, name: str, bot_token: str, chat_id: int, proxy_url: Optional[str] = None):
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
            masked = proxy_url_norm
            if "@" in masked:
                masked = masked.split("://")[0] + "://" + "***@" + masked.split("@")[-1]
            logger.info(f"Telegram backend initialized: chat_id={chat_id}, proxy={masked}")
        else:
            logger.info(f"Telegram backend initialized: chat_id={chat_id}")

    @staticmethod
    def _should_send_as_photo(*, content_type: str, file_size: int) -> bool:
        """
        Only JPEG images should go through sendPhoto.

        Telegram may transcode photos, which strips transparency from PNG/WebP/GIF/AVIF.
        To preserve original bytes we upload those formats as documents instead.
        """
        normalized = (content_type or "").strip().lower()
        is_jpeg = normalized in {"image/jpeg", "image/jpg", "image/pjpeg"}
        return is_jpeg and file_size <= 10 * 1024 * 1024

    def _get_file_path(self, file_id: str) -> Optional[str]:
        """Fetch the current file path from Telegram."""
        if not self._bot_token or not file_id:
            return None
        try:
            resp = self._session.get(
                f"https://api.telegram.org/bot{self._bot_token}/getFile",
                params={"file_id": file_id},
                timeout=15,
            )
            if not resp.ok:
                return None
            data = resp.json() or {}
            if not data.get("ok"):
                return None
            result = data.get("result") or {}
            return result.get("file_path")
        except Exception as exc:
            logger.error(f"Failed to fetch Telegram file path: {exc}")
            return None

    def _upload_to_telegram(
        self,
        *,
        file_obj,
        filename: str,
        content_type: str,
        file_size: int,
        caption: str,
    ) -> Optional[PutResult]:
        """Upload a file stream to Telegram using photo/document mode as appropriate."""
        send_as_photo = self._should_send_as_photo(content_type=content_type, file_size=file_size)
        field_name = "photo" if send_as_photo else "document"
        endpoint = "sendPhoto" if send_as_photo else "sendDocument"
        timeout = 60 if send_as_photo else 120

        files = {field_name: (filename, file_obj, content_type)}
        data = {"chat_id": self._chat_id, "caption": caption or ""}
        resp = self._session.post(
            f"https://api.telegram.org/bot{self._bot_token}/{endpoint}",
            files=files,
            data=data,
            timeout=timeout,
        )

        if not resp.ok:
            logger.error(f"Telegram upload failed: HTTP {resp.status_code}")
            return None

        payload = resp.json() or {}
        if not payload.get("ok"):
            logger.error(f"Telegram upload failed: {payload.get('description')}")
            return None

        result = payload.get("result") or {}
        if send_as_photo:
            photos = result.get("photo") or []
            if not photos:
                logger.error("Telegram upload failed: missing photo result")
                return None
            file_id = photos[-1].get("file_id")
        else:
            doc = result.get("document") or {}
            file_id = doc.get("file_id")

        if not file_id:
            logger.error("Telegram upload failed: missing file_id")
            return None

        file_path = self._get_file_path(file_id) or ""
        logger.info(f"Telegram storage upload complete: {file_id}")
        return PutResult(
            file_id=file_id,
            file_path=file_path,
            file_size=file_size,
            storage_backend=self.name,
            storage_key=file_id,
            storage_meta={
                "file_path": file_path,
                "uploaded_at": int(time.time()),
                "message_id": result.get("message_id"),
            },
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
        """Upload raw bytes to Telegram."""
        if not self._bot_token or not self._chat_id:
            logger.error("Telegram backend is missing bot_token or chat_id")
            return None

        try:
            return self._upload_to_telegram(
                file_obj=file_content,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                caption=caption,
            )
        except Exception as exc:
            logger.error(f"Telegram storage upload failed: {exc}")
            return None

    def put_file(
        self,
        *,
        file_path: str,
        filename: str,
        content_type: str,
        file_size: int,
        caption: str,
        source: str,
        username: str,
    ) -> Optional[PutResult]:
        """Upload a file from disk to Telegram."""
        if not self._bot_token or not self._chat_id:
            logger.error("Telegram backend is missing bot_token or chat_id")
            return None

        try:
            with open(file_path, "rb") as handle:
                return self._upload_to_telegram(
                    file_obj=handle,
                    filename=filename,
                    content_type=content_type,
                    file_size=file_size,
                    caption=caption,
                )
        except Exception as exc:
            logger.error(f"Telegram storage file upload failed: {exc}")
            return None

    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """Download a file from Telegram."""
        file_id = (file_info.get("storage_key") or file_info.get("file_id") or "").strip()
        file_path = (file_info.get("file_path") or "").strip()

        if not file_id:
            return DownloadResult(
                status_code=404,
                content_type="text/plain",
                headers={},
                body=[b"not found"],
            )

        fresh = self._get_file_path(file_id)
        updated_fields: Optional[Dict[str, Any]] = None
        if fresh and fresh != file_path:
            file_path = fresh
            updated_fields = {"file_path": fresh}

        if not file_path:
            return DownloadResult(
                status_code=404,
                content_type="text/plain",
                headers={},
                body=[b"file path not available"],
                updated_fields=updated_fields,
            )

        if file_path.startswith("https://"):
            file_url = file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{self._bot_token}/{file_path}"

        headers: Dict[str, str] = {}
        if range_header:
            headers["Range"] = range_header

        try:
            resp = self._session.get(file_url, stream=True, timeout=60, headers=headers)
        except Exception as exc:
            logger.error(f"Telegram download failed: {exc}")
            return DownloadResult(
                status_code=502,
                content_type="text/plain",
                headers={},
                body=[b"upstream error"],
                updated_fields=updated_fields,
            )

        if resp.status_code not in (200, 206):
            return DownloadResult(
                status_code=resp.status_code,
                content_type="text/plain",
                headers={},
                body=[b"upstream error"],
                updated_fields=updated_fields,
            )

        def body() -> Iterable[bytes]:
            try:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                resp.close()

        out_headers: Dict[str, str] = {"Accept-Ranges": "bytes"}
        if "content-length" in resp.headers:
            out_headers["Content-Length"] = resp.headers["content-length"]
        if "content-range" in resp.headers:
            out_headers["Content-Range"] = resp.headers["content-range"]

        return DownloadResult(
            status_code=resp.status_code,
            content_type=file_info.get("mime_type") or resp.headers.get("content-type", "application/octet-stream"),
            headers=out_headers,
            body=body(),
            updated_fields=updated_fields,
        )

    def healthcheck(self) -> bool:
        """Check whether the bot token is valid."""
        if not self._bot_token:
            return False
        try:
            resp = self._session.get(
                f"https://api.telegram.org/bot{self._bot_token}/getMe",
                timeout=10,
            )
            return resp.ok and resp.json().get("ok", False)
        except Exception:
            return False
