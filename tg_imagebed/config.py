#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 — 纯基础设施配置

所有业务配置（Bot Token、CDN、存储等）通过管理后台（数据库）管理。
此文件仅保留路径、服务器参数、日志等基础设施常量。
"""
import os
import sys
import time
import logging
from pathlib import Path


def _normalize_proxy_url(proxy: str) -> str:
    """规范化代理 URL，确保包含协议前缀"""
    proxy = (proxy or "").strip()
    if not proxy:
        return ""
    if "://" not in proxy:
        return f"http://{proxy}"
    return proxy


# ===================== 基础路径配置 =====================
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
STATIC_FOLDER = os.path.join(os.getcwd(), "frontend", ".output", "public")

# 数据目录（固定，Docker 通过 volume 映射 ./data:/app/data）
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATA_DIR, "telegram_imagebed.db")
LOG_FILE = os.path.join(DATA_DIR, "telegram_imagebed.log")

# ===================== 服务器配置（硬编码） =====================
PORT = 18793
HOST = '0.0.0.0'
ALLOWED_ORIGINS = '*'
SESSION_LIFETIME = 3600

# ===================== 版本 & 启动时间 =====================
STATIC_VERSION = str(int(time.time()))
START_TIME = time.time()

# ===================== 代理（标准系统环境变量，非 .env） =====================
_http_proxy = os.environ.get("HTTP_PROXY", "") or os.environ.get("http_proxy", "")
_https_proxy = os.environ.get("HTTPS_PROXY", "") or os.environ.get("https_proxy", "")
PROXY_URL = _normalize_proxy_url(_http_proxy or _https_proxy)


def get_proxy_url() -> str:
    """获取代理 URL（优先数据库设置，回退环境变量）"""
    try:
        from .database import get_system_setting
        db_proxy = (get_system_setting('proxy_url') or '').strip()
        if db_proxy:
            return _normalize_proxy_url(db_proxy)
    except Exception:
        pass
    return PROXY_URL

# ===================== SECRET_KEY — 持久化到文件 =====================
_secret_key_file = os.path.join(DATA_DIR, '.secret_key')
try:
    if os.path.exists(_secret_key_file):
        with open(_secret_key_file, 'r', encoding='utf-8') as f:
            _secret_key = f.read().strip()
    else:
        _secret_key = ""
except Exception:
    _secret_key = ""

if not _secret_key:
    import secrets as _secrets
    _secret_key = _secrets.token_hex(32)
    try:
        with open(_secret_key_file, 'w', encoding='utf-8') as f:
            f.write(_secret_key)
    except Exception:
        pass  # 写入失败时使用内存中的临时密钥

SECRET_KEY = _secret_key

# ===================== 日志配置 =====================
LOG_LEVEL = 'INFO'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 抑制第三方库的噪音日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('waitress').setLevel(logging.WARNING)
logging.getLogger('waitress.queue').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ===================== 登录安全配置 =====================
LOGIN_MAX_ATTEMPTS = 5              # 最大连续失败次数
LOGIN_LOCKOUT_DURATIONS = [300, 900, 1800]  # 渐进式锁定时间（秒）：5分钟→15分钟→30分钟
LOGIN_ATTEMPT_WINDOW = 900          # 失败计数窗口（秒），15分钟内无失败则重置
MAX_CONCURRENT_SESSIONS = 3        # 最大并发 Session 数

# ===================== 单实例锁文件 =====================
if sys.platform == 'win32':
    LOCK_FILE = os.path.join(os.environ.get('TEMP', '.'), 'telegram_imagebed.lock')
else:
    LOCK_FILE = '/tmp/telegram_imagebed.lock'


# ===================== 允许的文件后缀 =====================
# 内置图片后缀（不可删除的基础集合，用于魔数校验回退）
BUILTIN_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}

# 默认允许的完整后缀集合
_DEFAULT_ALLOWED_EXTENSIONS = BUILTIN_IMAGE_EXTENSIONS | {'avif', 'tiff', 'tif', 'ico'}


def get_allowed_extensions() -> set:
    """获取允许的文件后缀集合（从数据库读取，回退内置默认值）"""
    try:
        from .database import get_system_setting
        raw = (get_system_setting('allowed_extensions') or '').strip()
        if raw:
            exts = {e.strip().lower().lstrip('.') for e in raw.split(',') if e.strip()}
            return exts | BUILTIN_IMAGE_EXTENSIONS  # 始终包含内置后缀
    except Exception:
        pass
    return set(_DEFAULT_ALLOWED_EXTENSIONS)


__all__ = [
    # 基础路径
    'BASE_DIR', 'FRONTEND_DIR', 'STATIC_FOLDER', 'DATA_DIR',
    # 数据库 & 日志
    'DATABASE_PATH', 'LOG_FILE', 'LOG_LEVEL', 'logger',
    # 服务器
    'PORT', 'HOST', 'ALLOWED_ORIGINS', 'SESSION_LIFETIME',
    # 版本 & 时间
    'STATIC_VERSION', 'START_TIME',
    # 安全
    'SECRET_KEY',
    # 登录安全
    'LOGIN_MAX_ATTEMPTS', 'LOGIN_LOCKOUT_DURATIONS', 'LOGIN_ATTEMPT_WINDOW',
    'MAX_CONCURRENT_SESSIONS',
    # 代理
    'PROXY_URL', 'get_proxy_url',
    # 锁文件
    'LOCK_FILE',
    # 文件后缀白名单
    'BUILTIN_IMAGE_EXTENSIONS', 'get_allowed_extensions',
]
