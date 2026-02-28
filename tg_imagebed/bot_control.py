#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot 控制模块

提供:
- Bot Token 配置管理（支持 DB 与环境变量）
- Bot 热重启信号机制
"""
import os
import time
import hashlib
import threading
from typing import Optional, Tuple

from .config import logger


# Bot 重启信号
_bot_restart_event = threading.Event()
_bot_restart_lock = threading.Lock()
_last_restart_request = 0.0
_last_restart_reason = "manual"
_RESTART_COOLDOWN = 5.0  # 重启冷却时间（秒）

# Token 缓存（线程安全）
_TOKEN_CACHE_LOCK = threading.Lock()
_TOKEN_CACHE = {"ts": 0.0, "token": "", "source": ""}


def get_effective_bot_token() -> Tuple[str, str]:
    """
    获取有效的 Bot Token（优先数据库，回退环境变量）

    Returns:
        (token, source) 元组，source 为 'db' / 'env' / ''
    """
    now = time.time()

    with _TOKEN_CACHE_LOCK:
        if (now - _TOKEN_CACHE["ts"]) < 1.0:
            return _TOKEN_CACHE["token"], _TOKEN_CACHE["source"]

    # 优先从数据库读取
    db_token = ""
    try:
        from .database import get_system_setting
        db_token = str(get_system_setting("telegram_bot_token") or "").strip()
    except Exception as e:
        logger.debug(f"从数据库读取 Bot Token 失败: {e}")

    # 数据库有值则使用数据库
    if db_token:
        with _TOKEN_CACHE_LOCK:
            _TOKEN_CACHE.update({"ts": now, "token": db_token, "source": "db"})
        return db_token, "db"

    # 回退到环境变量
    env_token = os.environ.get("BOT_TOKEN", "").strip() or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if env_token:
        with _TOKEN_CACHE_LOCK:
            _TOKEN_CACHE.update({"ts": now, "token": env_token, "source": "env"})
        return env_token, "env"

    with _TOKEN_CACHE_LOCK:
        _TOKEN_CACHE.update({"ts": now, "token": "", "source": ""})
    return "", ""


def is_bot_token_configured() -> bool:
    """检查 Bot Token 是否已配置"""
    token, _ = get_effective_bot_token()
    return bool(token)


def request_bot_restart(reason: str = "manual") -> Tuple[bool, str]:
    """
    请求 Bot 热重启

    Returns:
        (success, message) 元组
    """
    global _last_restart_request, _last_restart_reason

    with _bot_restart_lock:
        now = time.time()
        if (now - _last_restart_request) < _RESTART_COOLDOWN:
            remaining = _RESTART_COOLDOWN - (now - _last_restart_request)
            return False, f"请等待 {remaining:.1f} 秒后再试"

        _last_restart_request = now
        _last_restart_reason = str(reason or "manual").strip()[:64] or "manual"
        _bot_restart_event.set()
        logger.info(f"Bot 重启信号已发送: reason={_last_restart_reason}")
        return True, "重启信号已发送"


def wait_for_restart_signal(timeout: float = 1.0) -> bool:
    """
    等待重启信号（供 Bot 线程使用）

    Args:
        timeout: 等待超时时间（秒）

    Returns:
        是否收到重启信号
    """
    triggered = _bot_restart_event.wait(timeout=timeout)
    if triggered:
        _bot_restart_event.clear()
    return triggered


def clear_token_cache() -> None:
    """清除 Token 缓存（配置更新后调用）"""
    with _TOKEN_CACHE_LOCK:
        _TOKEN_CACHE["ts"] = 0.0


def consume_last_restart_reason(default: str = "manual") -> str:
    """消费最近一次重启原因（读取后清空）"""
    global _last_restart_reason
    with _bot_restart_lock:
        reason = _last_restart_reason or default
        _last_restart_reason = default
        return reason


def get_webhook_secret(token: str = "") -> str:
    """基于 token 生成 webhook secret 路径片段（不暴露 token）"""
    if not token:
        token, _ = get_effective_bot_token()
    token = str(token or "").strip()
    if not token:
        return ""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:32]


def build_webhook_url(base_url: str, token: str = "") -> str:
    """构建 Telegram webhook 完整地址"""
    base = str(base_url or "").strip().rstrip("/")
    secret = get_webhook_secret(token)
    if not base or not secret:
        return ""
    return f"{base}/api/auth/tg/webhook/{secret}"


def get_bot_token_status() -> dict:
    """
    获取 Bot Token 配置状态（供管理界面使用）

    Returns:
        包含 configured, source, masked_token 的字典
    """
    token, source = get_effective_bot_token()

    if not token:
        return {
            "configured": False,
            "source": None,
            "masked_token": None,
        }

    # 掩码处理
    if len(token) > 20:
        masked = f"{token[:6]}...{token[-6:]}"
    else:
        masked = f"{token[:3]}..." if len(token) > 3 else "***"

    return {
        "configured": True,
        "source": source,
        "masked_token": masked,
    }


__all__ = [
    "get_effective_bot_token",
    "is_bot_token_configured",
    "request_bot_restart",
    "wait_for_restart_signal",
    "clear_token_cache",
    "consume_last_restart_reason",
    "get_webhook_secret",
    "build_webhook_url",
    "get_bot_token_status",
]
