#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot 包

导出 Bot 启动和状态查询接口。
"""
from .runner import start_telegram_bot_thread
from .state import _get_bot_status, _set_bot_status

__all__ = [
    'start_telegram_bot_thread',
    '_get_bot_status',
    '_set_bot_status',
]
