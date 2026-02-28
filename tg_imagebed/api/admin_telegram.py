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
from ..database import get_system_setting, get_system_setting_int, update_system_setting
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
        return _admin_json({'success': False, 'error': 'Bot 配置操作失败'}, 500)


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

        success, message = request_bot_restart(reason="manual_restart")
        return _admin_json({'success': success, 'message': message}, 200 if success else 429)

    except Exception as e:
        logger.error(f"Telegram Bot 重启 API 失败: {e}")
        return _admin_json({'success': False, 'error': 'Bot 重启操作失败'}, 500)


@admin_bp.route('/api/admin/telegram/runtime', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def admin_telegram_runtime():
    """读取/更新 Bot 运行时配置"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, PUT, OPTIONS')

    try:
        from ..bot_control import (
            get_bot_token_status, request_bot_restart, build_webhook_url
        )
        from ..bot import _get_bot_status

        if request.method == 'GET':
            mode = str(get_system_setting('bot_update_mode') or 'polling').strip().lower()
            webhook_base = str(get_system_setting('bot_webhook_url') or '').strip()
            status = _get_bot_status()
            data = {
                'mode': mode,
                'webhook_url': webhook_base,
                'webhook_effective_url': build_webhook_url(webhook_base),
                'settoken_ttl_seconds': get_system_setting_int(
                    'bot_settoken_ttl_seconds', 600, minimum=30, maximum=3600
                ),
                'template_strict_mode': str(get_system_setting('bot_template_strict_mode') or '0') == '1',
                'token': get_bot_token_status(),
                'status': status,
            }
            return _admin_json({'success': True, 'data': data})

        payload = request.get_json(silent=True) or {}
        next_mode = str(payload.get('mode') or get_system_setting('bot_update_mode') or 'polling').strip().lower()
        next_webhook = str(payload.get('webhook_url') or get_system_setting('bot_webhook_url') or '').strip()
        next_ttl = payload.get(
            'settoken_ttl_seconds',
            get_system_setting_int('bot_settoken_ttl_seconds', 600, minimum=30, maximum=3600)
        )
        next_strict = payload.get('template_strict_mode', str(get_system_setting('bot_template_strict_mode') or '0') == '1')

        if next_mode not in ('polling', 'webhook'):
            return _admin_json({'success': False, 'error': 'mode 仅支持 polling 或 webhook'}, 400)
        if next_mode == 'webhook' and not next_webhook:
            return _admin_json({'success': False, 'error': 'webhook 模式需要配置 webhook_url'}, 400)
        if next_webhook and not next_webhook.startswith(('http://', 'https://')):
            return _admin_json({'success': False, 'error': 'webhook_url 必须以 http:// 或 https:// 开头'}, 400)
        try:
            ttl_val = int(next_ttl)
        except (TypeError, ValueError):
            return _admin_json({'success': False, 'error': 'settoken_ttl_seconds 必须为整数'}, 400)
        if ttl_val < 30 or ttl_val > 3600:
            return _admin_json({'success': False, 'error': 'settoken_ttl_seconds 必须在 30-3600 之间'}, 400)

        changed = False
        old_mode = str(get_system_setting('bot_update_mode') or 'polling').strip().lower()
        old_webhook = str(get_system_setting('bot_webhook_url') or '').strip()
        old_ttl = get_system_setting_int('bot_settoken_ttl_seconds', 600, minimum=30, maximum=3600)
        old_strict = str(get_system_setting('bot_template_strict_mode') or '0') == '1'

        if next_mode != old_mode:
            update_system_setting('bot_update_mode', next_mode)
            changed = True
        if next_webhook != old_webhook:
            update_system_setting('bot_webhook_url', next_webhook)
            changed = True
        if ttl_val != old_ttl:
            update_system_setting('bot_settoken_ttl_seconds', str(ttl_val))
            changed = True
        if bool(next_strict) != old_strict:
            update_system_setting('bot_template_strict_mode', '1' if bool(next_strict) else '0')
            changed = True

        restarted = False
        restart_message = ''
        if changed:
            restarted, restart_message = request_bot_restart(reason="runtime_config_changed")

        return _admin_json({
            'success': True,
            'message': '运行时配置已更新',
            'restarted': restarted,
            'restart_message': restart_message,
        })

    except Exception as e:
        logger.error(f"Telegram runtime API 失败: {e}")
        return _admin_json({'success': False, 'error': '运行时配置操作失败'}, 500)
