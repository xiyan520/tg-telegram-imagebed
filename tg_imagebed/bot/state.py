#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 状态管理模块

管理 Telegram 机器人的全局运行状态。
"""
import threading
import time
from datetime import datetime, timezone

from ..config import get_proxy_url


_BOT_STATUS_LOCK = threading.Lock()
_BOT_STATUS = {
    "enabled": False,  # 延迟初始化
    "state": "pending",
    "message": "等待启动",
    "last_ok_at": None,
    "last_error_at": None,
    "last_error_type": None,
    "last_error": None,
    "conflict_retry": 0,
    "next_retry_in_seconds": None,
    "proxy_enabled": bool(get_proxy_url()),
    # 运行时统计
    "stats_processed": 0,
    "stats_success": 0,
    "stats_failed": 0,
}


def _utc_iso(ts: float = None) -> str:
    """生成 UTC ISO 时间字符串"""
    if ts is None:
        ts = time.time()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _set_bot_status(**updates) -> None:
    """更新机器人状态"""
    with _BOT_STATUS_LOCK:
        _BOT_STATUS.update(updates)


def _get_bot_status() -> dict:
    """获取机器人状态"""
    with _BOT_STATUS_LOCK:
        return dict(_BOT_STATUS)


def _inc_bot_stats(*, success: int = 0, failed: int = 0) -> None:
    """递增运行时统计计数器"""
    with _BOT_STATUS_LOCK:
        _BOT_STATUS["stats_processed"] += success + failed
        _BOT_STATUS["stats_success"] += success
        _BOT_STATUS["stats_failed"] += failed


# ===================== Bot 实例引用（跨线程桥接） =====================
_bot_instance = None
_bot_loop = None

def set_bot_instance(bot):
    """保存 Bot 实例引用（在 Bot 启动后调用）"""
    global _bot_instance
    _bot_instance = bot

def get_bot_instance():
    """获取 Bot 实例"""
    return _bot_instance

def set_bot_loop(loop):
    """保存 Bot 事件循环引用"""
    global _bot_loop
    _bot_loop = loop

def get_bot_loop():
    """获取 Bot 事件循环"""
    return _bot_loop
