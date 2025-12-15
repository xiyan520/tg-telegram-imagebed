#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块 - 从 main.py 提取的通用工具函数

包含：
- 单实例锁管理（支持 Windows 和 Linux）
- 网络工具（获取本机IP）
- 加密工具（文件ID加密）
- MIME类型检测
- HTTP缓存头部管理
- 文件大小格式化
- 域名获取
"""
import os
import sys
import time
import socket
import base64
import hashlib
import atexit
from pathlib import Path
from typing import Optional
from flask import Response

from .config import (
    SECRET_KEY, CDN_ENABLED, CDN_CACHE_TTL, CLOUDFLARE_CDN_DOMAIN,
    CLOUDFLARE_EDGE_TTL, CLOUDFLARE_BROWSER_TTL, STATIC_VERSION,
    FORCE_REFRESH, LOCK_FILE, PORT, logger
)

# ===================== 单实例锁管理 =====================
# 全局锁文件句柄
_lock_file_handle = None
_lock_fd = None


def acquire_lock() -> bool:
    """获取锁以确保只有一个实例在运行（支持 Windows 和 Linux）"""
    global _lock_file_handle, _lock_fd
    try:
        if sys.platform == 'win32':
            import msvcrt
            _lock_file_handle = open(LOCK_FILE, 'w')
            try:
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except IOError:
                logger.error("另一个实例正在运行")
                return False
        else:
            import fcntl
            _lock_fd = open(LOCK_FILE, 'w')
            try:
                fcntl.lockf(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                logger.error("另一个实例正在运行")
                return False
    except Exception as e:
        logger.error(f"获取锁失败: {e}")
        return False


def release_lock() -> None:
    """释放锁"""
    global _lock_file_handle, _lock_fd
    try:
        if sys.platform == 'win32':
            if _lock_file_handle is not None:
                _lock_file_handle.close()
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
        else:
            if _lock_fd is not None:
                _lock_fd.close()
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"释放锁失败: {e}")


# 注册退出时释放锁
atexit.register(release_lock)


# ===================== 网络工具 =====================
def get_local_ip() -> str:
    """获取本机IPv4地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


# 缓存本机IP
LOCAL_IP = get_local_ip()


# ===================== 加密工具 =====================
def encrypt_file_id(file_id: str, file_path: str) -> str:
    """
    生成不可预测的文件 ID

    使用 HMAC-SHA256 替代 MD5，确保 ID 不可预测且不可逆向
    """
    import hmac
    import secrets

    # 添加随机盐增加不可预测性
    salt = secrets.token_hex(8)
    data = f"{file_id}:{file_path}:{int(time.time())}:{salt}"

    # 使用 HMAC-SHA256 生成签名
    signature = hmac.new(
        SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    # 返回 URL 安全的 ID（取前24位 + 8位随机）
    return f"{signature[:24]}{salt[:8]}"


# ===================== MIME类型检测 =====================
def get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = Path(file_path).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    return mime_types.get(ext, 'image/jpeg')


# ===================== HTTP缓存头部管理 =====================
def add_cache_headers(response: Response, cache_type: str = 'public', max_age: Optional[int] = None) -> Response:
    """
    添加CDN缓存头部

    Args:
        response: Flask Response 对象
        cache_type: 缓存类型 ('public', 'private', 'no-cache', 'static')
        max_age: 最大缓存时间（秒）

    Returns:
        添加了缓存头部的 Response 对象
    """
    # 如果已经设置了 Cache-Control 且是 public 类型，只添加安全头部
    if 'Cache-Control' in response.headers and cache_type == 'public':
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # CDN 未启用时的处理
    if not CDN_ENABLED:
        if cache_type == 'static':
            response.headers['Cache-Control'] = 'public, max-age=3600'
        else:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    # 设置默认 max_age
    if max_age is None:
        max_age = CDN_CACHE_TTL

    # 根据缓存类型设置头部
    if cache_type == 'public':
        response.headers['Cache-Control'] = f'public, max-age={max_age}, s-maxage={CLOUDFLARE_EDGE_TTL}, stale-while-revalidate=86400, stale-if-error=604800'
        response.headers['Cloudflare-CDN-Cache-Control'] = f'max-age={CLOUDFLARE_EDGE_TTL}'
        response.headers['CDN-Cache-Control'] = f'max-age={CLOUDFLARE_EDGE_TTL}'
    elif cache_type == 'private':
        response.headers['Cache-Control'] = f'private, max-age={max_age}'
    elif cache_type == 'no-cache':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif cache_type == 'static':
        response.headers['Cache-Control'] = f'public, max-age={CLOUDFLARE_BROWSER_TTL}, s-maxage={CLOUDFLARE_EDGE_TTL}'

    # 添加安全头部
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # 添加 CDN 标签
    if cache_type in ['public', 'static']:
        response.headers['CF-Cache-Tag'] = 'imagebed'

    return response


# ===================== 文件大小格式化 =====================
def format_size(size_bytes: int) -> str:
    """
    将字节数格式化为人类可读的大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.5 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"


# ===================== 域名获取 =====================
def get_domain(request) -> str:
    """
    根据请求动态获取域名

    Args:
        request: Flask request 对象，可以为 None

    Returns:
        完整的域名 URL
    """
    if request:
        # 如果启用了 CDN 且不是 API 请求，返回 CDN 域名
        if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
            if not request.path.startswith('/api/'):
                return f"https://{CLOUDFLARE_CDN_DOMAIN}"

        # 检测 Cloudflare 访问者信息
        cf_visitor = request.headers.get('CF-Visitor')
        if cf_visitor:
            try:
                import json
                visitor_data = json.loads(cf_visitor)
                scheme = visitor_data.get('scheme', 'https')
            except Exception:
                scheme = 'https'
        else:
            scheme = request.headers.get('X-Forwarded-Proto', 'http')

        # 获取主机名
        host = (request.headers.get('X-Forwarded-Host') or
                request.headers.get('Host') or
                request.host)

        base_url = f"{scheme}://{host}"

        # 处理前缀
        forwarded_prefix = request.headers.get('X-Forwarded-Prefix', '')
        if forwarded_prefix:
            base_url += forwarded_prefix.rstrip('/')

        return base_url

    # 当 request 为 None 时（如 Telegram Bot 场景），优先使用 CDN 域名
    if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
        return f"https://{CLOUDFLARE_CDN_DOMAIN}"

    # 回退到本地地址（仅用于开发环境）
    return f"http://{LOCAL_IP}:{PORT}"


# ===================== 静态文件版本管理 =====================
def get_static_file_version(filename: str) -> str:
    """
    获取静态文件版本号

    Args:
        filename: 文件名

    Returns:
        版本号字符串
    """
    if FORCE_REFRESH:
        return str(int(time.time()))
    return STATIC_VERSION


__all__ = [
    # 单实例锁
    'acquire_lock', 'release_lock',
    # 网络工具
    'get_local_ip', 'LOCAL_IP',
    # 加密工具
    'encrypt_file_id',
    # MIME类型
    'get_mime_type',
    # 缓存头部
    'add_cache_headers',
    # 格式化
    'format_size',
    # 域名
    'get_domain',
    # 静态文件版本
    'get_static_file_version',
]
