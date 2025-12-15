#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置路由模块 - 公共设置和管理员设置 API
"""
from flask import request, jsonify, make_response

from . import admin_bp, images_bp
from ..config import logger
from ..utils import add_cache_headers
from ..database import (
    get_public_settings, get_all_system_settings, update_system_settings,
    disable_guest_tokens, disable_all_tokens
)

from .. import admin_module


def _set_admin_cors_headers(response):
    """设置管理员 API 的 CORS 头"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


# ===================== 公共设置 API =====================
@images_bp.route('/api/public/settings', methods=['GET', 'OPTIONS'])
def get_public_settings_api():
    """获取公开的系统设置（供前端使用）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        settings = get_public_settings()

        response = jsonify({
            'success': True,
            'data': settings
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公共设置失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


# ===================== 管理员系统设置 API =====================
@admin_bp.route('/api/admin/system/settings', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def admin_system_settings():
    """管理员系统设置 API"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            # 获取所有系统设置
            settings = get_all_system_settings()

            response = jsonify({
                'success': True,
                'data': {
                    'guest_upload_policy': settings.get('guest_upload_policy', 'open'),
                    'guest_token_generation_enabled': settings.get('guest_token_generation_enabled', '1') == '1',
                    'guest_existing_tokens_policy': settings.get('guest_existing_tokens_policy', 'keep'),
                    'guest_token_max_upload_limit': int(settings.get('guest_token_max_upload_limit', '1000')),
                    'guest_token_max_expires_days': int(settings.get('guest_token_max_expires_days', '365')),
                    'max_file_size_mb': int(settings.get('max_file_size_mb', '20')),
                    'daily_upload_limit': int(settings.get('daily_upload_limit', '0')),
                },
                'policy_options': {
                    'guest_upload_policy': [
                        {'value': 'open', 'label': '完全开放', 'description': '允许匿名上传和 Token 上传'},
                        {'value': 'token_only', 'label': '仅 Token', 'description': '禁止匿名上传，允许 Token 上传'},
                        {'value': 'admin_only', 'label': '仅管理员', 'description': '禁止所有游客上传'},
                    ],
                    'guest_existing_tokens_policy': [
                        {'value': 'keep', 'label': '保留有效', 'description': '关闭游客模式后，已有 Token 仍可使用'},
                        {'value': 'disable_guest', 'label': '禁用游客 Token', 'description': '关闭时禁用所有游客生成的 Token'},
                        {'value': 'disable_all', 'label': '禁用所有 Token', 'description': '关闭时禁用所有 Token'},
                    ]
                }
            })

        elif request.method == 'PUT':
            # 更新系统设置
            data = request.get_json()
            if not data:
                response = jsonify({'success': False, 'error': '无效的请求数据'})
                response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                return add_cache_headers(response, 'no-cache'), 400

            # 构建要更新的设置
            settings_to_update = {}

            if 'guest_upload_policy' in data:
                policy = data['guest_upload_policy']
                if policy not in ['open', 'token_only', 'admin_only']:
                    response = jsonify({'success': False, 'error': '无效的上传策略'})
                    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    return add_cache_headers(response, 'no-cache'), 400
                settings_to_update['guest_upload_policy'] = policy

            if 'guest_token_generation_enabled' in data:
                enabled = '1' if data['guest_token_generation_enabled'] else '0'
                settings_to_update['guest_token_generation_enabled'] = enabled

            if 'guest_existing_tokens_policy' in data:
                tokens_policy = data['guest_existing_tokens_policy']
                if tokens_policy not in ['keep', 'disable_guest', 'disable_all']:
                    response = jsonify({'success': False, 'error': '无效的 Token 策略'})
                    response = _set_admin_cors_headers(response)
                    return add_cache_headers(response, 'no-cache'), 400
                settings_to_update['guest_existing_tokens_policy'] = tokens_policy

            if 'guest_token_max_upload_limit' in data:
                try:
                    limit = int(data['guest_token_max_upload_limit'])
                    if limit < 1 or limit > 1000000:
                        raise ValueError("Token 最大上传数必须在 1-1000000 之间")
                    settings_to_update['guest_token_max_upload_limit'] = str(limit)
                except ValueError as e:
                    response = jsonify({'success': False, 'error': str(e)})
                    response = _set_admin_cors_headers(response)
                    return add_cache_headers(response, 'no-cache'), 400

            if 'guest_token_max_expires_days' in data:
                try:
                    days = int(data['guest_token_max_expires_days'])
                    if days < 1 or days > 36500:
                        raise ValueError("Token 最大有效期必须在 1-36500 天之间")
                    settings_to_update['guest_token_max_expires_days'] = str(days)
                except ValueError as e:
                    response = jsonify({'success': False, 'error': str(e)})
                    response = _set_admin_cors_headers(response)
                    return add_cache_headers(response, 'no-cache'), 400

            if 'max_file_size_mb' in data:
                try:
                    max_size = int(data['max_file_size_mb'])
                    if max_size < 1 or max_size > 100:
                        raise ValueError("文件大小限制必须在 1-100 MB 之间")
                    settings_to_update['max_file_size_mb'] = str(max_size)
                except ValueError as e:
                    response = jsonify({'success': False, 'error': str(e)})
                    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    return add_cache_headers(response, 'no-cache'), 400

            if 'daily_upload_limit' in data:
                try:
                    limit = int(data['daily_upload_limit'])
                    if limit < 0:
                        raise ValueError("每日上传限制不能为负数")
                    settings_to_update['daily_upload_limit'] = str(limit)
                except ValueError as e:
                    response = jsonify({'success': False, 'error': str(e)})
                    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    return add_cache_headers(response, 'no-cache'), 400

            # 更新设置
            if settings_to_update:
                update_system_settings(settings_to_update)

            # 处理 Token 禁用策略
            disabled_count = 0
            if data.get('apply_token_policy'):
                tokens_policy = data.get('guest_existing_tokens_policy', 'keep')
                if tokens_policy == 'disable_guest':
                    disabled_count = disable_guest_tokens()
                elif tokens_policy == 'disable_all':
                    disabled_count = disable_all_tokens()

            # 获取更新后的设置
            updated_settings = get_all_system_settings()

            response = jsonify({
                'success': True,
                'message': '设置已更新',
                'data': {
                    'guest_upload_policy': updated_settings.get('guest_upload_policy', 'open'),
                    'guest_token_generation_enabled': updated_settings.get('guest_token_generation_enabled', '1') == '1',
                    'guest_existing_tokens_policy': updated_settings.get('guest_existing_tokens_policy', 'keep'),
                    'guest_token_max_upload_limit': int(updated_settings.get('guest_token_max_upload_limit', '1000')),
                    'guest_token_max_expires_days': int(updated_settings.get('guest_token_max_expires_days', '365')),
                    'max_file_size_mb': int(updated_settings.get('max_file_size_mb', '20')),
                    'daily_upload_limit': int(updated_settings.get('daily_upload_limit', '0')),
                },
                'tokens_disabled': disabled_count
            })

        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"系统设置操作失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/tokens/revoke', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_revoke_tokens():
    """管理员批量禁用 Token"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        data = request.get_json() or {}
        revoke_type = data.get('type', 'guest')  # guest/all

        if revoke_type == 'all':
            count = disable_all_tokens()
            message = f'已禁用所有 {count} 个 Token'
        else:
            count = disable_guest_tokens()
            message = f'已禁用 {count} 个游客 Token'

        response = jsonify({
            'success': True,
            'message': message,
            'disabled_count': count
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"批量禁用 Token 失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500
