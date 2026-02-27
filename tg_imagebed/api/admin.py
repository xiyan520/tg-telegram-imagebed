#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由模块 - 管理员 API 入口

路由已按功能拆分到子模块：
- admin_helpers: 共享辅助函数（_admin_json, _admin_options, _get_cdn_domain）
- admin_setup: 初始化设置（/api/setup/*）
- admin_cdn: CDN 管理（/api/admin/cdn/*）
- admin_storage: 存储配置（/api/admin/storage/*, /api/admin/upload）
- admin_tokens: Token 管理（/api/admin/tokens/*）
- admin_telegram: Telegram Bot 配置（/api/admin/telegram/*）
- admin_galleries: 画集管理（/api/admin/galleries/*）

本文件保留：管理员账号设置 + 公告管理
"""
from flask import request, jsonify, Response, session

from . import admin_bp
from ..config import logger
from ..utils import add_cache_headers
from ..database import get_announcement, update_announcement
from .. import admin_module

# 导入子模块以注册路由（副作用导入）
from . import admin_setup      # noqa: F401
from . import admin_cdn        # noqa: F401
from . import admin_storage    # noqa: F401
from . import admin_tokens     # noqa: F401
from . import admin_telegram   # noqa: F401
from . import admin_galleries  # noqa: F401
from . import admin_domains    # noqa: F401
from . import admin_dashboard  # noqa: F401

# 注意：/api/admin/check 端点已在 admin_module.py 中定义
# 此处不再重复定义，避免路由冲突


@admin_bp.route('/api/admin/settings', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_update_settings():
    """更新管理员设置"""
    data = request.get_json()
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()

    if not new_username and not new_password:
        return jsonify({'success': False, 'message': '请提供新的用户名或密码'}), 400

    if new_username and len(new_username) < 3:
        return jsonify({'success': False, 'message': '用户名至少需要3个字符'}), 400

    if new_password:
        valid, msg = admin_module.validate_password_strength(new_password)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400

    if admin_module.update_admin_credentials(new_username, new_password):
        if new_username:
            session['admin_username'] = new_username

        return jsonify({
            'success': True,
            'message': '设置更新成功'
        })

    return jsonify({'success': False, 'message': '更新失败'}), 500


@admin_bp.route('/api/announcement', methods=['GET', 'OPTIONS'])
def get_announcement_api():
    """获取当前公告"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        announcement = get_announcement()

        if announcement:
            response = jsonify({
                'success': True,
                'data': {
                    'id': announcement['id'],
                    'enabled': bool(announcement['enabled']),
                    'content': announcement['content'],
                    'created_at': announcement['created_at'],
                    'updated_at': announcement['updated_at']
                }
            })
        else:
            response = jsonify({
                'success': True,
                'data': {
                    'id': 0,
                    'enabled': False,
                    'content': '',
                    'created_at': None,
                    'updated_at': None
                }
            })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公告失败: {e}")
        response = jsonify({'success': False, 'error': '获取公告失败，请稍后重试'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/announcement', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_announcement():
    """管理员公告管理"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            announcement = get_announcement()

            if announcement:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': announcement['id'],
                        'enabled': bool(announcement['enabled']),
                        'content': announcement['content'],
                        'created_at': announcement['created_at'],
                        'updated_at': announcement['updated_at']
                    }
                })
            else:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': 0,
                        'enabled': False,
                        'content': '',
                        'created_at': None,
                        'updated_at': None
                    }
                })

        elif request.method == 'POST':
            data = request.get_json()
            enabled = data.get('enabled', True)
            content = data.get('content', '')

            announcement_id = update_announcement(enabled, content)

            response = jsonify({
                'success': True,
                'message': '公告更新成功',
                'data': {
                    'id': announcement_id,
                    'enabled': enabled,
                    'content': content
                }
            })

        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"公告管理失败: {e}")
        response = jsonify({'success': False, 'error': '操作失败，请稍后重试'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500
