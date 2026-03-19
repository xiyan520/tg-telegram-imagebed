#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload routes for anonymous web uploads.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from flask import jsonify, request

from . import upload_bp
from ..config import logger
from ..database import (
    get_system_setting_int,
    is_guest_upload_allowed,
    release_upload_reservation,
    reserve_guest_upload,
)
from ..services.file_service import process_upload
from ..utils import add_cache_headers, format_size, get_image_domain


IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",
    b"BM": "image/bmp",
    b"\x49\x49\x2A\x00": "image/tiff",
    b"\x4D\x4D\x00\x2A": "image/tiff",
    b"\x00\x00\x01\x00": "image/x-icon",
}


@dataclass
class ValidatedUpload:
    temp_path: str
    file_size: int
    detected_mime: str

    def cleanup(self) -> None:
        try:
            if self.temp_path and os.path.exists(self.temp_path):
                os.remove(self.temp_path)
        except OSError:
            logger.debug("Failed to clean temporary upload file: %s", self.temp_path)


def validate_image_magic(content: bytes) -> Optional[str]:
    """Validate the upload by file signature."""
    if len(content) < 12:
        return None

    for signature, mime_type in IMAGE_SIGNATURES.items():
        if not content.startswith(signature):
            continue
        if signature == b"RIFF" and content[8:12] != b"WEBP":
            continue
        return mime_type

    if len(content) >= 12 and content[4:8] == b"ftyp":
        # 检查 major brand（字节 8-11）和 compatible brands（字节 16+，每4字节）
        major_brand = content[8:12]
        if major_brand in (b"avif", b"avis"):
            return "image/avif"
        # 检查 compatible brands 区域
        compat_region = content[16:min(32, len(content))]
        for i in range(0, len(compat_region) - 3, 4):
            if compat_region[i:i + 4] in (b"avif", b"avis"):
                return "image/avif"

    return None


def is_extension_allowed(filename: str) -> bool:
    """Check whether the file extension is allowed."""
    from ..config import get_allowed_extensions

    if not filename:
        return True

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext:
        return True

    return ext in get_allowed_extensions()


def _error(message: str, status_code: int):
    return add_cache_headers(jsonify({"success": False, "error": message}), "no-cache"), status_code


def validate_upload_file(file) -> Tuple[Optional[tuple], Optional[ValidatedUpload]]:
    """
    Validate the uploaded file while streaming it into a temporary file.

    Returns (error_response, validated_upload). error_response is None when validation passes.
    """
    content_type = (file.content_type or "").strip().lower()
    if not is_extension_allowed(file.filename):
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
        return _error(f"不支持的文件格式: .{ext}", 400), None

    if content_type and not content_type.startswith("image/"):
        return _error("只允许上传图片文件", 400), None

    max_size_mb = get_system_setting_int("max_file_size_mb", 100, minimum=1, maximum=1024)
    max_size_bytes = max_size_mb * 1024 * 1024

    tmp = tempfile.NamedTemporaryFile(prefix="tg-imagebed-upload-", suffix=".tmp", delete=False)
    tmp_path = tmp.name
    total_size = 0
    header = bytearray()

    try:
        stream = file.stream
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break

            total_size += len(chunk)
            if total_size > max_size_bytes:
                tmp.close()
                os.remove(tmp_path)
                return _error(f"文件大小超过 {max_size_mb}MB 限制", 400), None

            tmp.write(chunk)
            if len(header) < 32:
                header.extend(chunk[: 32 - len(header)])
    except Exception:
        tmp.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    finally:
        if not tmp.closed:
            tmp.close()

    detected_mime = validate_image_magic(bytes(header))
    if not detected_mime:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return _error("无效的图片文件格式", 400), None

    return None, ValidatedUpload(
        temp_path=tmp_path,
        file_size=total_size,
        detected_mime=detected_mime,
    )


@upload_bp.route("/api/upload", methods=["POST"])
@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle anonymous uploads from the web UI."""
    if not is_guest_upload_allowed():
        return add_cache_headers(jsonify({
            "success": False,
            "error": "匿名上传已关闭，请使用 Token 上传或联系管理员",
        }), "no-cache"), 403

    if "file" not in request.files:
        return add_cache_headers(jsonify({"error": "No file provided"}), "no-cache"), 400

    file = request.files["file"]
    if file.filename == "":
        return add_cache_headers(jsonify({"error": "No file selected"}), "no-cache"), 400

    err, validated = validate_upload_file(file)
    if err:
        return err

    daily_limit = get_system_setting_int("daily_upload_limit", 0, minimum=0, maximum=1000000)
    reservation_key = None

    try:
        if daily_limit > 0:
            reservation = reserve_guest_upload(source="web_upload", daily_limit=daily_limit)
            if not reservation.get("ok"):
                return add_cache_headers(jsonify({
                    "success": False,
                    "error": reservation.get("reason", "上传受限"),
                }), "no-cache"), reservation.get("status", 429)
            reservation_key = reservation.get("reservation_key")

        result = process_upload(
            file_content=None,
            filename=file.filename,
            content_type=validated.detected_mime,
            username="web_user",
            source="web_upload",
            staged_file_path=validated.temp_path,
            reservation_key=reservation_key,
        )

        if not result:
            if reservation_key:
                release_upload_reservation(reservation_key)
            return add_cache_headers(jsonify({"error": "Failed to upload to storage"}), "no-cache"), 500

        base_url = get_image_domain(request, scene="guest")
        permanent_url = f"{base_url}/image/{result['encrypted_id']}"

        logger.info("Web upload complete: %s -> %s", file.filename, result["encrypted_id"])
        return add_cache_headers(jsonify({
            "success": True,
            "data": {
                "url": permanent_url,
                "filename": file.filename,
                "size": format_size(result["file_size"]),
                "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }), "no-cache")

    except Exception as e:
        if reservation_key:
            release_upload_reservation(reservation_key)
        logger.error(f"Upload error: {e}")
        return add_cache_headers(jsonify({"error": "上传失败，请稍后重试"}), "no-cache"), 500
    finally:
        if validated:
            validated.cleanup()
