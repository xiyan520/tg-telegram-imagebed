#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件服务模块 - 文件上传和处理

提供文件上传到 Telegram、获取文件路径等功能。
"""
import time
import hashlib
from typing import Optional, Dict, Any

import requests

from ..config import STORAGE_CHAT_ID, CLOUDFLARE_CDN_DOMAIN, logger
from ..database import save_file_info, get_file_info, update_file_path_in_db
from ..utils import encrypt_file_id, get_mime_type
from .cdn_service import add_to_cdn_monitor
from ..storage.router import get_storage_router
from ..bot_control import get_effective_bot_token


def get_fresh_file_path(file_id: str) -> Optional[str]:
    """
    通过 Telegram API 获取最新的文件路径

    Args:
        file_id: Telegram 文件 ID

    Returns:
        文件路径字符串，失败返回 None
    """
    bot_token, _ = get_effective_bot_token()
    if not bot_token or not file_id:
        return None

    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={'file_id': file_id},
            timeout=10
        )

        if response.ok:
            result = response.json()
            if result.get('ok') and result.get('result'):
                file_path = result['result'].get('file_path')
                logger.debug(f"获取最新file_path成功: {file_id} -> {file_path}")
                return file_path

        logger.error(f"获取文件路径失败: {response.text}")
        return None

    except Exception as e:
        logger.error(f"获取文件路径异常: {e}")
        return None


def upload_to_telegram(
    file_content: bytes,
    filename: str,
    content_type: str,
    file_size: int,
    caption: str = ""
) -> Optional[Dict[str, Any]]:
    """
    上传文件到 Telegram

    Args:
        file_content: 文件内容
        filename: 文件名
        content_type: MIME 类型
        file_size: 文件大小
        caption: 图片说明

    Returns:
        包含 file_id, file_path, file_size 的字典，失败返回 None
    """
    if not BOT_TOKEN or not STORAGE_CHAT_ID:
        logger.error("Telegram 配置不完整")
        return None

    try:
        # 根据文件大小选择上传方式
        if file_size <= 10 * 1024 * 1024:  # 10MB 以下使用 sendPhoto
            files = {'photo': (filename, file_content, content_type)}
            data = {'chat_id': STORAGE_CHAT_ID, 'caption': caption}
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
        else:  # 10MB 以上使用 sendDocument
            files = {'document': (filename, file_content, content_type)}
            data = {'chat_id': STORAGE_CHAT_ID, 'caption': caption}
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                files=files,
                data=data,
                timeout=60
            )

        if not response.ok:
            logger.error(f"Telegram API error: {response.text}")
            return None

        result = response.json()
        if not result.get('ok'):
            logger.error(f"Telegram API failed: {result}")
            return None

        # 获取文件信息
        if file_size <= 10 * 1024 * 1024:
            photos = result['result'].get('photo', [])
            if not photos:
                return None
            photo = photos[-1]
            file_id = photo['file_id']
        else:
            document = result['result'].get('document')
            if not document:
                return None
            file_id = document['file_id']

        # 获取文件路径
        file_response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={'file_id': file_id},
            timeout=30
        )

        if not file_response.ok:
            logger.error(f"Failed to get file info: {file_response.text}")
            return None

        file_result = file_response.json()
        if not file_result.get('ok'):
            return None

        return {
            'file_id': file_id,
            'file_path': file_result['result']['file_path'],
            'file_size': file_result['result'].get('file_size', file_size)
        }

    except Exception as e:
        logger.error(f"上传到 Telegram 失败: {e}")
        return None


def process_upload(
    file_content: bytes,
    filename: str,
    content_type: str,
    username: str = 'web_user',
    source: str = 'web_upload',
    auth_token: Optional[str] = None,
    is_group_upload: bool = False,
    group_message_id: Optional[int] = None,
    upload_scene: Optional[str] = None,
    requested_backend: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    处理文件上传的完整流程

    Args:
        file_content: 文件内容
        filename: 文件名
        content_type: MIME 类型
        username: 用户名
        source: 来源
        auth_token: 认证 Token
        is_group_upload: 是否群组上传
        group_message_id: 群组消息 ID
        upload_scene: 上传场景 (guest/token/group/admin)
        requested_backend: 管理员请求的特定后端

    Returns:
        包含 encrypted_id, url 等信息的字典，失败返回 None
    """
    file_size = len(file_content)

    # 规范化 content_type（防止 None 或空字符串导致后端出错）
    if not content_type:
        content_type = get_mime_type(filename)

    # 推断上传场景（可由调用方显式传入 upload_scene 覆盖）
    scene = (upload_scene or "").strip().lower()
    if not scene:
        if is_group_upload:
            scene = "group"
        elif auth_token:
            scene = "token"
        else:
            scene = "guest"

    # 计算文件哈希
    file_hash = hashlib.md5(file_content).hexdigest()

    # 构建说明
    caption = f"{source} | 文件名: {filename} | 大小: {file_size} bytes | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

    # 通过存储路由器选择后端并上传
    router = get_storage_router()
    backend_name = router.resolve_upload_backend(
        scene=scene,
        requested_backend=requested_backend,
        is_admin=(scene == "admin"),
    )
    backend = router.get_backend(backend_name)
    put_result = backend.put_bytes(
        file_content=file_content,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        caption=caption,
        source=source,
        username=username,
    )

    if not put_result:
        return None

    # 生成加密 ID
    encrypted_id = encrypt_file_id(put_result.file_id, put_result.file_path)

    # 获取 MIME 类型
    mime_type = get_mime_type(filename)

    # 保存文件信息
    file_data = {
        'file_id': put_result.file_id,
        'file_path': put_result.file_path,
        'upload_time': int(time.time()),
        'user_id': 0,
        'username': username,
        'file_size': put_result.file_size,
        'source': source,
        'original_filename': filename,
        'mime_type': mime_type,
        'file_hash': file_hash,
        'is_group_upload': is_group_upload,
        'group_message_id': group_message_id,
        'auth_token': auth_token,
        'storage_backend': put_result.storage_backend,
        'storage_key': put_result.storage_key,
        'storage_meta': put_result.storage_meta,
    }
    save_file_info(encrypted_id, file_data)

    # 添加到 CDN 监控
    add_to_cdn_monitor(encrypted_id, file_data['upload_time'])

    logger.info(f"文件上传完成: {filename} -> {encrypted_id}")

    return {
        'encrypted_id': encrypted_id,
        'file_size': put_result.file_size,
        'filename': filename,
        'mime_type': mime_type
    }


def record_existing_telegram_file(
    *,
    file_id: str,
    file_path: str,
    file_content: bytes,
    filename: str,
    content_type: str,
    username: str = 'web_user',
    source: str = 'telegram_group',
    auth_token: Optional[str] = None,
    is_group_upload: bool = False,
    group_message_id: Optional[int] = None,
    file_unique_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    直接记录已存在于 Telegram 的文件（不做二次上传）

    适用于群组监听场景：用户在群里发送图片后，bot 通过 getFile 拿到 file_path，
    同时下载字节用于计算 file_hash（去重/审计），但不再把图片转存到存储频道。
    """
    if not file_id:
        return None

    file_path = file_path or ''
    file_size = len(file_content or b'')

    if not content_type:
        content_type = get_mime_type(filename)

    file_hash = hashlib.md5(file_content or b'').hexdigest()
    encrypted_id = encrypt_file_id(file_id, file_path)
    mime_type = get_mime_type(filename)
    upload_time = int(time.time())

    file_data = {
        'file_id': file_id,
        'file_path': file_path,
        'upload_time': upload_time,
        'user_id': 0,
        'username': username,
        'file_size': file_size,
        'source': source,
        'original_filename': filename,
        'mime_type': mime_type,
        'file_hash': file_hash,
        'is_group_upload': is_group_upload,
        'group_message_id': group_message_id,
        'auth_token': auth_token,
        'storage_backend': 'telegram',
        'storage_key': file_id,
        'storage_meta': {
            'file_path': file_path,
            'recorded_at': upload_time,
            'existing_telegram_file': True,
            'file_unique_id': file_unique_id,
        },
    }
    save_file_info(encrypted_id, file_data)
    add_to_cdn_monitor(encrypted_id, upload_time)

    logger.info(f"已记录 Telegram 既有文件: {filename} -> {encrypted_id}")

    return {
        'encrypted_id': encrypted_id,
        'file_size': file_size,
        'filename': filename,
        'mime_type': mime_type
    }


__all__ = [
    'get_fresh_file_path',
    'upload_to_telegram',
    'process_upload',
    'record_existing_telegram_file',
]
