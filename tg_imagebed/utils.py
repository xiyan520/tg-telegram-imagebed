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
    SECRET_KEY, STATIC_VERSION,
    LOCK_FILE, PORT, logger
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
# 已知后缀 → MIME 映射
_MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.avif': 'image/avif',
    '.heic': 'image/heic',
    '.heif': 'image/heif',
}


def get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型（支持自定义后缀）"""
    ext = Path(file_path).suffix.lower()
    mime = _MIME_TYPES.get(ext)
    if mime:
        return mime
    # 对未知后缀，尝试通过 mimetypes 标准库猜测
    import mimetypes
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or 'application/octet-stream'


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

    # 从数据库获取 CDN 启用状态
    _, cdn_enabled = _get_effective_domain_settings()

    # CDN 未启用时的处理
    if not cdn_enabled:
        if cache_type == 'static':
            response.headers['Cache-Control'] = 'public, max-age=3600'
        else:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    # 设置默认 max_age（从 DB 读取 CDN 缓存 TTL）
    if max_age is None:
        try:
            from .database import get_system_setting_int
            max_age = get_system_setting_int('cdn_cache_ttl', 86400, minimum=0)
        except Exception:
            max_age = 86400

    # 从 DB 读取 edge/browser TTL
    try:
        from .database import get_system_setting_int as _gsi
        edge_ttl = _gsi('cloudflare_edge_ttl', 86400, minimum=0)
        browser_ttl = _gsi('cloudflare_browser_ttl', 3600, minimum=0)
    except Exception:
        edge_ttl = 86400
        browser_ttl = 3600

    # 根据缓存类型设置头部
    if cache_type == 'public':
        response.headers['Cache-Control'] = f'public, max-age={max_age}, s-maxage={edge_ttl}, stale-while-revalidate=86400, stale-if-error=604800'
        response.headers['Cloudflare-CDN-Cache-Control'] = f'max-age={edge_ttl}'
        response.headers['CDN-Cache-Control'] = f'max-age={edge_ttl}'
    elif cache_type == 'private':
        response.headers['Cache-Control'] = f'private, max-age={max_age}'
    elif cache_type == 'no-cache':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif cache_type == 'static':
        response.headers['Cache-Control'] = f'public, max-age={browser_ttl}, s-maxage={edge_ttl}'

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
_DOMAIN_SETTINGS_CACHE = {"ts": 0.0, "domain": "", "cdn_enabled": False}
_DOMAINS_CACHE = {"ts": 0.0, "domains": []}
_DOMAIN_POLICY_CACHE = {"ts": 0.0, "policy": {}}


def clear_domain_cache() -> None:
    """清除域名设置缓存，使设置立即生效"""
    _DOMAIN_SETTINGS_CACHE["ts"] = 0.0
    _DOMAIN_SETTINGS_CACHE["domain"] = ""
    _DOMAIN_SETTINGS_CACHE["cdn_enabled"] = False
    # 同时清除图片域名缓存
    _DOMAINS_CACHE["ts"] = 0.0
    _DOMAINS_CACHE["domains"] = []


def clear_domains_cache() -> None:
    """清除图片域名列表缓存和策略缓存"""
    _DOMAINS_CACHE["ts"] = 0.0
    _DOMAINS_CACHE["domains"] = []
    _DOMAIN_POLICY_CACHE["ts"] = 0.0
    _DOMAIN_POLICY_CACHE["policy"] = {}


def _get_effective_domain_settings():
    """
    从数据库读取域名/cdn_enabled 设置。
    失败时回退到环境变量配置。
    """
    import time as _time
    now = _time.time()
    age = now - _DOMAIN_SETTINGS_CACHE["ts"]
    if 0.0 <= age < 1.0:
        return _DOMAIN_SETTINGS_CACHE["domain"], _DOMAIN_SETTINGS_CACHE["cdn_enabled"]

    domain = ""
    cdn_enabled = False
    try:
        from .database import get_system_setting
        domain = str(get_system_setting("cloudflare_cdn_domain") or "").strip()
        cdn_enabled = str(get_system_setting("cdn_enabled") or "0") == "1"
        logger.debug(f"[域名配置] 从数据库读取: domain='{domain}', cdn_enabled={cdn_enabled}")
    except Exception as e:
        domain = ""
        cdn_enabled = False
        logger.warning(f"[域名配置] 数据库读取失败，使用默认值: error={e}")

    _DOMAIN_SETTINGS_CACHE["ts"] = now
    _DOMAIN_SETTINGS_CACHE["domain"] = domain
    _DOMAIN_SETTINGS_CACHE["cdn_enabled"] = cdn_enabled
    return domain, cdn_enabled


def get_domain(request) -> str:
    """
    根据请求动态获取域名

    三种模式：
    - CDN 模式: 配置了域名 + cdn_enabled=True => https://<domain>
    - 直连模式: 配置了域名 + cdn_enabled=False => https://<domain> (或保持请求 scheme)
    - 默认模式: 未配置域名 => 使用请求 host

    Args:
        request: Flask request 对象，可以为 None

    Returns:
        完整的域名 URL
    """
    configured_domain, cdn_enabled = _get_effective_domain_settings()
    has_domain = bool(configured_domain)
    cdn_mode = has_domain and cdn_enabled

    if request:
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

        # Host 选择：配置了域名则使用配置域名，否则使用请求 host
        if has_domain:
            host = configured_domain
        else:
            host = (
                request.headers.get('X-Forwarded-Host')
                or request.headers.get('Host')
                or request.host
            )

        # Scheme 选择：CDN 模式强制 https，其他模式保持请求 scheme
        effective_scheme = 'https' if cdn_mode else scheme
        base_url = f"{effective_scheme}://{host}"

        # 处理前缀
        forwarded_prefix = request.headers.get('X-Forwarded-Prefix', '')
        if forwarded_prefix:
            base_url += forwarded_prefix.rstrip('/')

        return base_url

    # request 为 None 时（如 Telegram Bot 场景）
    if has_domain:
        return f"https://{configured_domain}"

    # 回退到本地地址（仅用于开发环境）
    return f"http://{LOCAL_IP}:{PORT}"


def _get_domain_upload_policy() -> dict:
    """获取域名上传策略（带缓存）"""
    import time as _time
    import json as _json

    now = _time.time()
    age = now - _DOMAIN_POLICY_CACHE["ts"]
    if 0.0 <= age < 5.0:
        return _DOMAIN_POLICY_CACHE["policy"]

    policy = {}
    try:
        from .database import get_system_setting
        raw = get_system_setting('domain_upload_policy_json') or ''
        if raw:
            policy = _json.loads(raw)
    except Exception:
        policy = {}

    _DOMAIN_POLICY_CACHE["ts"] = now
    _DOMAIN_POLICY_CACHE["policy"] = policy
    return policy


def get_image_domain(request=None, scene: str = '') -> str:
    """
    获取图片专用域名 URL

    优先根据 scene 查询域名策略，匹配活跃图片域名后返回；
    无匹配时从活跃图片域名中随机选择，
    如果没有图片域名，降级到 get_domain(request)。
    """
    import time as _time
    import random as _random

    now = _time.time()
    age = now - _DOMAINS_CACHE["ts"]
    if age < 0 or age >= 1.0:
        # 刷新缓存
        try:
            from .database import get_active_image_domains
            _DOMAINS_CACHE["domains"] = get_active_image_domains()
        except Exception:
            _DOMAINS_CACHE["domains"] = []
        _DOMAINS_CACHE["ts"] = now

    domains = _DOMAINS_CACHE["domains"]
    if not domains:
        # 没有图片域名，降级到原有逻辑
        return get_domain(request)

    # 场景路由：查策略 → 匹配活跃域名
    if scene:
        policy = _get_domain_upload_policy()
        target_domain = policy.get(scene, '')
        if target_domain:
            active_domain_set = {d['domain'] for d in domains}
            if target_domain in active_domain_set:
                # 找到匹配的域名记录，获取 scheme
                for d in domains:
                    if d['domain'] == target_domain:
                        scheme = 'https' if d.get('use_https', 1) else 'http'
                        return f"{scheme}://{target_domain}"

    # 降级：随机选择
    chosen = _random.choice(domains)
    scheme = 'https' if chosen.get('use_https', 1) else 'http'
    return f"{scheme}://{chosen['domain']}"


# ===================== 静态文件版本管理 =====================
def get_static_file_version(filename: str) -> str:
    """
    获取静态文件版本号

    Args:
        filename: 文件名

    Returns:
        版本号字符串
    """
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
    'get_image_domain',
    'clear_domain_cache',
    'clear_domains_cache',
    # 静态文件版本
    'get_static_file_version',
]
