#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务层模块 - 业务逻辑封装

包含：
- cdn_service: CDN 管理服务
- file_service: 文件处理服务
- telegram_service: Telegram 机器人服务
- auth_service: Token 认证服务
- frontend_service: 前端启动服务
"""

from .cdn_service import (
    CloudflareCDN,
    cloudflare_cdn,
    cdn_monitor_queue,
    start_cdn_monitor,
    stop_cdn_monitor,
    add_to_cdn_monitor,
)

from .auth_service import (
    create_token,
    verify_token,
    get_token_details,
)

__all__ = [
    # CDN
    'CloudflareCDN', 'cloudflare_cdn', 'cdn_monitor_queue',
    'start_cdn_monitor', 'stop_cdn_monitor', 'add_to_cdn_monitor',
    # Auth
    'create_token', 'verify_token', 'get_token_details',
]
