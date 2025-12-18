#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - 从 main.py 提取的配置参数

集中管理所有环境变量和配置参数，保持与原有环境变量名的完全兼容。
"""
import os
import sys
import time
import logging
import warnings
from pathlib import Path
from typing import List

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _normalize_proxy_url(proxy: str) -> str:
    """规范化代理 URL，确保包含协议前缀"""
    proxy = (proxy or "").strip()
    if not proxy:
        return ""
    if "://" not in proxy:
        return f"http://{proxy}"
    return proxy


# ===================== 基础路径配置 =====================
# 注意：移动到 tg_imagebed/ 后，BASE_DIR 指向项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
STATIC_FOLDER = os.path.join(os.getcwd(), "frontend", ".output", "public")

# ===================== 敏感配置警告标记 =====================
# 用于延迟输出警告（在 logger 初始化后）
_config_warnings = []

# ===================== Telegram 配置 =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID", "0") or "0")

# Telegram Bot 代理配置（python-telegram-bot 使用 httpx）
_http_proxy = os.getenv("HTTP_PROXY", "") or os.getenv("http_proxy", "")
_https_proxy = os.getenv("HTTPS_PROXY", "") or os.getenv("https_proxy", "")
PROXY_URL = _normalize_proxy_url(_http_proxy or _https_proxy)

# SECRET_KEY 必须从环境变量读取，无默认值时自动生成
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    import secrets as _secrets
    _secret_key = _secrets.token_hex(32)
    _config_warnings.append(("SECRET_KEY 未配置，已自动生成临时密钥。请在 .env 文件中设置 SECRET_KEY", "secret_key"))
SECRET_KEY = _secret_key

# ===================== 服务器配置 =====================
PORT = int(os.getenv("PORT", "18793"))
HOST = os.getenv("HOST", "0.0.0.0")

# ===================== 前端自动启动配置 =====================
FRONTEND_AUTOSTART = os.getenv("FRONTEND_AUTOSTART", "true").lower() == "true"
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))
FRONTEND_DEV_CMD = os.getenv("FRONTEND_DEV_CMD", "npm run dev")

# ===================== 群组上传功能配置（已迁移到数据库，此处仅为首次启动迁移用） =====================
ENABLE_GROUP_UPLOAD = os.getenv("ENABLE_GROUP_UPLOAD", "false").lower() == "true"
GROUP_UPLOAD_ADMIN_ONLY = os.getenv("GROUP_UPLOAD_ADMIN_ONLY", "false").lower() == "true"
GROUP_ADMIN_IDS = os.getenv("GROUP_ADMIN_IDS", "")
GROUP_UPLOAD_ALLOWED_CHAT_IDS = os.getenv("GROUP_UPLOAD_ALLOWED_CHAT_IDS", "")
GROUP_UPLOAD_REPLY = os.getenv("GROUP_UPLOAD_REPLY", "true").lower() == "true"
GROUP_UPLOAD_DELETE_DELAY = int(os.getenv("GROUP_UPLOAD_DELETE_DELAY", "0"))
TG_SYNC_DELETE_ENABLED = os.getenv("TG_SYNC_DELETE_ENABLED", "true").lower() == "true"

def _parse_id_list(raw: str) -> List[int]:
    """解析逗号分隔的 ID 列表（支持负数如 -100xxx）"""
    if not raw:
        return []
    try:
        return [int(x.strip()) for x in raw.split(',') if x.strip()]
    except Exception:
        return []

GROUP_ADMIN_ID_LIST: List[int] = _parse_id_list(GROUP_ADMIN_IDS)
GROUP_UPLOAD_ALLOWED_CHAT_ID_LIST: List[int] = _parse_id_list(GROUP_UPLOAD_ALLOWED_CHAT_IDS)

# ===================== CDN 相关配置（已迁移到数据库，此处仅为首次启动迁移用） =====================
CDN_ENABLED = os.getenv("CDN_ENABLED", "false").lower() == "true"
CDN_CACHE_TTL = int(os.getenv("CDN_CACHE_TTL", "31536000"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# CDN重定向配置
CDN_REDIRECT_ENABLED = os.getenv("CDN_REDIRECT_ENABLED", "false").lower() == "true"
CDN_REDIRECT_MAX_COUNT = int(os.getenv("CDN_REDIRECT_MAX_COUNT", "2"))
CDN_REDIRECT_CACHE_TIME = int(os.getenv("CDN_REDIRECT_CACHE_TIME", "300"))
CDN_REDIRECT_DELAY = int(os.getenv("CDN_REDIRECT_DELAY", "10"))

# Cloudflare CDN 特定配置
CLOUDFLARE_CDN_DOMAIN = os.getenv("CLOUDFLARE_CDN_DOMAIN", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CLOUDFLARE_CACHE_LEVEL = os.getenv("CLOUDFLARE_CACHE_LEVEL", "aggressive")
CLOUDFLARE_BROWSER_TTL = int(os.getenv("CLOUDFLARE_BROWSER_TTL", "14400"))
CLOUDFLARE_EDGE_TTL = int(os.getenv("CLOUDFLARE_EDGE_TTL", "2592000"))

# 智能路由配置
ENABLE_SMART_ROUTING = os.getenv("ENABLE_SMART_ROUTING", "false").lower() == "true"
FALLBACK_TO_ORIGIN = os.getenv("FALLBACK_TO_ORIGIN", "true").lower() == "true"

# 缓存预热配置
ENABLE_CACHE_WARMING = os.getenv("ENABLE_CACHE_WARMING", "false").lower() == "true"
CACHE_WARMING_DELAY = int(os.getenv("CACHE_WARMING_DELAY", "5"))

# CDN缓存监控配置
CDN_MONITOR_ENABLED = os.getenv("CDN_MONITOR_ENABLED", "false").lower() == "true"
CDN_MONITOR_INTERVAL = int(os.getenv("CDN_MONITOR_INTERVAL", "5"))
CDN_MONITOR_MAX_RETRIES = int(os.getenv("CDN_MONITOR_MAX_RETRIES", "15"))
CDN_MONITOR_QUEUE_SIZE = int(os.getenv("CDN_MONITOR_QUEUE_SIZE", "1000"))

# ===================== 版本控制 =====================
STATIC_VERSION = os.getenv("STATIC_VERSION", str(int(time.time())))
FORCE_REFRESH = os.getenv("FORCE_REFRESH", "false").lower() == "true"

# ===================== 数据库路径 =====================
DEFAULT_DB_PATH = os.path.join(os.getcwd(), "telegram_imagebed.db")
DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

# 确保数据库目录存在
db_dir = os.path.dirname(DATABASE_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# ===================== 日志配置 =====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "telegram_imagebed.log")

# 确保日志文件目录存在
log_dir = os.path.dirname(LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL.upper()),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== 单实例锁文件 =====================
if sys.platform == 'win32':
    LOCK_FILE = os.path.join(os.environ.get('TEMP', '.'), 'telegram_imagebed.lock')
else:
    LOCK_FILE = '/tmp/telegram_imagebed.lock'

# ===================== 管理员配置 =====================
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
# 管理员密码必须从环境变量读取，无默认值时生成随机密码
_admin_password = os.getenv("ADMIN_PASSWORD")
_admin_password_generated = False
if not _admin_password:
    import secrets as _secrets
    _admin_password = _secrets.token_urlsafe(12)
    _admin_password_generated = True
    _config_warnings.append(("ADMIN_PASSWORD 未配置，已自动生成临时密码。请在 .env 文件中设置 ADMIN_PASSWORD", "admin_password"))
DEFAULT_ADMIN_PASSWORD = _admin_password
SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "3600"))

# ===================== 启动时间记录 =====================
START_TIME = time.time()


def print_config_info():
    """打印配置信息"""
    # 先输出延迟的配置警告（不输出敏感信息明文）
    if _config_warnings:
        logger.warning("=" * 60)
        logger.warning("配置警告:")
        for warning_msg, warning_type in _config_warnings:
            logger.warning(f"  - {warning_msg}")
        logger.warning("=" * 60)

    logger.info("=" * 60)
    logger.info("Telegram 图床机器人 - 模块化重构版")
    logger.info("=" * 60)
    logger.info(f"BOT_TOKEN: {'已配置' if BOT_TOKEN else '未配置'}")
    logger.info(f"PROXY_URL: {PROXY_URL if PROXY_URL else '未配置'}")
    logger.info(f"STORAGE_CHAT_ID: {STORAGE_CHAT_ID}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"DATABASE_PATH: {DATABASE_PATH}")
    logger.info(f"CDN_ENABLED: {CDN_ENABLED}")
    logger.info(f"群组上传功能: {ENABLE_GROUP_UPLOAD}")
    if ENABLE_GROUP_UPLOAD:
        logger.info(f"仅管理员: {GROUP_UPLOAD_ADMIN_ONLY}")
        logger.info(f"管理员ID: {GROUP_ADMIN_IDS or '未配置'}")
        logger.info(f"回复消息: {GROUP_UPLOAD_REPLY}")
    if CDN_ENABLED:
        logger.info(f"CLOUDFLARE_CDN_DOMAIN: {CLOUDFLARE_CDN_DOMAIN or '未配置'}")
        logger.info(f"智能路由: {ENABLE_SMART_ROUTING}")
        logger.info(f"缓存预热: {ENABLE_CACHE_WARMING}")
        logger.info(f"CDN监控: {CDN_MONITOR_ENABLED}")
        logger.info(f"CDN重定向: {CDN_REDIRECT_ENABLED}")
        logger.info(f"最大重定向次数: {CDN_REDIRECT_MAX_COUNT}")
        logger.info(f"新文件重定向延迟: {CDN_REDIRECT_DELAY}秒")
    logger.info("=" * 60)


__all__ = [
    # 基础路径
    'BASE_DIR', 'FRONTEND_DIR', 'STATIC_FOLDER',
    # Telegram
    'BOT_TOKEN', 'STORAGE_CHAT_ID', 'SECRET_KEY', 'PROXY_URL',
    # 服务器
    'PORT', 'HOST',
    # 前端
    'FRONTEND_AUTOSTART', 'FRONTEND_PORT', 'FRONTEND_DEV_CMD',
    # 群组上传
    'ENABLE_GROUP_UPLOAD', 'GROUP_UPLOAD_ADMIN_ONLY', 'GROUP_ADMIN_IDS',
    'GROUP_UPLOAD_ALLOWED_CHAT_IDS', 'GROUP_UPLOAD_ALLOWED_CHAT_ID_LIST',
    'GROUP_UPLOAD_REPLY', 'GROUP_UPLOAD_DELETE_DELAY', 'GROUP_ADMIN_ID_LIST',
    'TG_SYNC_DELETE_ENABLED',
    # CDN
    'CDN_ENABLED', 'CDN_CACHE_TTL', 'ALLOWED_ORIGINS',
    'CDN_REDIRECT_ENABLED', 'CDN_REDIRECT_MAX_COUNT', 'CDN_REDIRECT_CACHE_TIME', 'CDN_REDIRECT_DELAY',
    'CLOUDFLARE_CDN_DOMAIN', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ZONE_ID',
    'CLOUDFLARE_CACHE_LEVEL', 'CLOUDFLARE_BROWSER_TTL', 'CLOUDFLARE_EDGE_TTL',
    'ENABLE_SMART_ROUTING', 'FALLBACK_TO_ORIGIN',
    'ENABLE_CACHE_WARMING', 'CACHE_WARMING_DELAY',
    'CDN_MONITOR_ENABLED', 'CDN_MONITOR_INTERVAL', 'CDN_MONITOR_MAX_RETRIES', 'CDN_MONITOR_QUEUE_SIZE',
    # 版本
    'STATIC_VERSION', 'FORCE_REFRESH',
    # 数据库
    'DATABASE_PATH',
    # 日志
    'LOG_LEVEL', 'LOG_FILE', 'logger',
    # 锁文件
    'LOCK_FILE',
    # 管理员
    'DEFAULT_ADMIN_USERNAME', 'DEFAULT_ADMIN_PASSWORD', 'SESSION_LIFETIME',
    # 启动时间
    'START_TIME',
    # 函数
    'print_config_info',
]
