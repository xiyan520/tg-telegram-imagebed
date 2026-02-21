#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - Telegram Bot 配置
"""
from flask import request, jsonify, Response

from . import admin_bp
from .admin_helpers import _admin_json, _admin_options
from ..config import logger
from ..utils import add_cache_headers
from ..database import update_system_setting
from .. import admin_module


@admin_bp.route('/api/admin/telegram/bot', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def admin_telegram_bot_config():
    """
    Telegram Bot Token 配置 API:
    - GET: 获取 Bot Token 配置状态
    - PUT: 更新 Bot Token（仅当未通过环境变量设置时）
    """
    if request.method == 'OPTIONS':
        return _admin_options('GET, PUT, OPTIONS')

    try:
        from ..bot_control import get_bot_token_status, clear_token_cache

        if request.method == 'GET':
            status = get_bot_token_status()
            return _admin_json({'success': True, 'data': status})

        # PUT: 更新 Bot Token
        data = request.get_json(silent=True) or {}
        new_token = (data.get('token') or '').strip()

        # 验证 Token 格式（基本格式检查）
        if new_token and ':' not in new_token:
            return _admin_json({
                'success': False,
                'error': 'Bot Token 格式无效，应为 数字:字符串 格式'
            }, 400)

        # 保存到数据库
        update_system_setting('telegram_bot_token', new_token)
        clear_token_cache()

        logger.info(f"更新 Telegram Bot Token: {'已设置' if new_token else '已清除'}")

        return _admin_json({
            'success': True,
            'message': 'Bot Token 已更新' if new_token else 'Bot Token 已清除',
            'data': get_bot_token_status()
        })

    except Exception as e:
        logger.error(f"Telegram Bot 配置 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/telegram/bot/restart', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_telegram_bot_restart():
    """请求 Telegram Bot 热重启"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    try:
        from ..bot_control import request_bot_restart, get_bot_token_status

        status = get_bot_token_status()
        if not status.get('configured'):
            return _admin_json({
                'success': False,
                'error': 'Bot Token 未配置，无法重启'
            }, 400)

        success, message = request_bot_restart()
        return _admin_json({'success': success, 'message': message}, 200 if success else 429)

    except Exception as e:
        logger.error(f"Telegram Bot 重启 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)
