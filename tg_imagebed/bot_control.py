#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot 控制模块

提供:
- Bot Token 配置管理（支持 DB 与环境变量）
- Bot 热重启信号机制
"""
import time
import threading
from typing import Optional, Tuple

from .config import BOT_TOKEN as ENV_BOT_TOKEN, logger


# Bot 重启信号
_bot_restart_event = threading.Event()
_bot_restart_lock = threading.Lock()
_last_restart_request = 0.0
_RESTART_COOLDOWN = 5.0  # 重启冷却时间（秒）

# Token 缓存（线程安全）
_TOKEN_CACHE_LOCK = threading.Lock()
_TOKEN_CACHE = {"ts": 0.0, "token": "", "source": ""}


def get_effective_bot_token() -> Tuple[str, str]:
    """
    获取有效的 Bot Token

    优先级: 环境变量 > 数据库

    Returns:
        (token, source) 元组，source 为 'env' 或 'db' 或 ''
    """
    now = time.time()

    with _TOKEN_CACHE_LOCK:
        if (now - _TOKEN_CACHE["ts"]) < 1.0:
            return _TOKEN_CACHE["token"], _TOKEN_CACHE["source"]

    # 优先使用环境变量
    if ENV_BOT_TOKEN:
        with _TOKEN_CACHE_LOCK:
            _TOKEN_CACHE.update({"ts": now, "token": ENV_BOT_TOKEN, "source": "env"})
        return ENV_BOT_TOKEN, "env"

    # 从数据库读取
    db_token = ""
    try:
        from .database import get_system_setting
        db_token = str(get_system_setting("telegram_bot_token") or "").strip()
    except Exception as e:
        logger.debug(f"从数据库读取 Bot Token 失败: {e}")

    with _TOKEN_CACHE_LOCK:
        if db_token:
            _TOKEN_CACHE.update({"ts": now, "token": db_token, "source": "db"})
        else:
            _TOKEN_CACHE.update({"ts": now, "token": "", "source": ""})

    return db_token, "db" if db_token else ""


def is_bot_token_configured() -> bool:
    """检查 Bot Token 是否已配置"""
    token, _ = get_effective_bot_token()
    return bool(token)


def request_bot_restart() -> Tuple[bool, str]:
    """
    请求 Bot 热重启

    Returns:
        (success, message) 元组
    """
    global _last_restart_request

    with _bot_restart_lock:
        now = time.time()
        if (now - _last_restart_request) < _RESTART_COOLDOWN:
            remaining = _RESTART_COOLDOWN - (now - _last_restart_request)
            return False, f"请等待 {remaining:.1f} 秒后再试"

        _last_restart_request = now
        _bot_restart_event.set()
        logger.info("Bot 重启信号已发送")
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
            "env_set": bool(ENV_BOT_TOKEN),
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
        "env_set": bool(ENV_BOT_TOKEN),
    }


__all__ = [
    "get_effective_bot_token",
    "is_bot_token_configured",
    "request_bot_restart",
    "wait_for_restart_signal",
    "clear_token_cache",
    "get_bot_token_status",
]
