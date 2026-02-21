#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - Token 管理
"""
from flask import request, jsonify, Response

from . import admin_bp
from .admin_helpers import _get_cdn_domain, _admin_json, _admin_options
from ..config import logger
from ..utils import add_cache_headers, get_domain
from ..database import (
    get_system_setting, get_system_setting_int,
    admin_list_tokens, admin_create_token,
    admin_update_token_status, admin_update_token, admin_delete_token,
    admin_get_token_detail, admin_get_token_uploads, admin_get_token_galleries,
)
from ..services.token_service import TokenService
from .. import admin_module


@admin_bp.route('/api/admin/tokens', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_tokens_api():
    """
    Token 管理 API：
    - GET: 获取 Token 列表（分页、筛选）
    - POST: 创建新的 Token
    """
    if request.method == 'OPTIONS':
        return _admin_options('GET, POST, OPTIONS')

    try:
        if request.method == 'GET':
            status = (request.args.get('status') or 'all').strip().lower()
            try:
                page = int(request.args.get('page', 1))
            except (TypeError, ValueError):
                page = 1
            try:
                page_size = int(request.args.get('page_size', 20))
            except (TypeError, ValueError):
                page_size = 20

            data = admin_list_tokens(status=status, page=page, page_size=page_size)
            return _admin_json({'success': True, 'data': data})

        # POST: 创建新 Token
        payload = request.get_json(silent=True) or {}

        # 从系统设置读取默认值
        default_upload_limit = get_system_setting_int('guest_token_max_upload_limit', 1000, minimum=1, maximum=1000000)
        default_expires_days = get_system_setting_int('guest_token_max_expires_days', 365, minimum=1, maximum=36500)

        # 处理过期时间：前端未传 expires_at 时，按系统默认天数计算
        expires_at = payload.get('expires_at')
        if expires_at is None and 'expires_at' not in payload:
            from datetime import datetime, timedelta
            expires_at = (datetime.now() + timedelta(days=default_expires_days)).strftime('%Y-%m-%d %H:%M:%S')

        created = TokenService.create_token(
            description=payload.get('description'),
            expires_at=expires_at,
            upload_limit=payload.get('upload_limit', default_upload_limit),
            is_active=payload.get('is_active', True),
        )

        if not created:
            return _admin_json({'success': False, 'error': '创建 Token 失败'}, 500)

        return _admin_json({'success': True, 'data': created}, 201)

    except ValueError as e:
        return _admin_json({'success': False, 'error': str(e)}, 400)

    except Exception as e:
        logger.error(f"Token 管理 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/tokens/<int:token_id>', methods=['GET', 'PATCH', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_token_detail_api(token_id: int):
    """
    单个 Token 操作 API：
    - GET: 获取完整 Token 详情
    - PATCH: 更新 Token 属性
    - DELETE: 删除 Token
    """
    if request.method == 'OPTIONS':
        return _admin_options('GET, PATCH, DELETE, OPTIONS')

    try:
        if request.method == 'GET':
            detail = admin_get_token_detail(token_id)
            if not detail:
                return _admin_json({'success': False, 'error': 'Token 不存在'}, 404)
            return _admin_json({'success': True, 'data': detail})

        if request.method == 'DELETE':
            deleted = TokenService.delete_token(token_id)
            if not deleted:
                return _admin_json({'success': False, 'error': 'Token 不存在'}, 404)
            return _admin_json({'success': True, 'message': 'Token 已删除'})

        # PATCH: 更新 Token 属性
        payload = request.get_json(silent=True) or {}
        update_kwargs = {}

        if 'is_active' in payload:
            is_active_value = payload['is_active']
            if not isinstance(is_active_value, bool):
                return _admin_json({'success': False, 'error': 'is_active 必须为布尔值'}, 400)
            update_kwargs['is_active'] = is_active_value

        if 'description' in payload:
            update_kwargs['description'] = payload['description']

        if 'expires_at' in payload:
            update_kwargs['expires_at'] = payload['expires_at']

        if 'upload_limit' in payload:
            update_kwargs['upload_limit'] = payload['upload_limit']

        if not update_kwargs:
            return _admin_json({'success': False, 'error': '未提供任何更新字段'}, 400)

        updated = admin_update_token(token_id=token_id, **update_kwargs)
        if not updated:
            return _admin_json({'success': False, 'error': 'Token 不存在'}, 404)

        return _admin_json({'success': True, 'data': updated})

    except Exception as e:
        logger.error(f"Token 详情 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/tokens/<int:token_id>/uploads', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_token_uploads_api(token_id: int):
    """获取 Token 上传的图片（分页）"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)

        data = admin_get_token_uploads(token_id, page=page, page_size=page_size)

        # 为每张图片附加 image_url
        base_url = get_domain(request)
        cdn_domain = _get_cdn_domain()
        cdn_enabled = str(get_system_setting('cdn_enabled') or '0') == '1'
        for item in data['items']:
            item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"
            if cdn_enabled and cdn_domain:
                item['cdn_url'] = f"https://{cdn_domain}/image/{item['encrypted_id']}"

        return _admin_json({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"Token 上传记录 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/tokens/<int:token_id>/galleries', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_token_galleries_api(token_id: int):
    """获取 Token 拥有的画集（分页）"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)

        data = admin_get_token_galleries(token_id, page=page, page_size=page_size)

        # 为画集附加 cover_url 和 share_url
        base_url = get_domain(request)
        for item in data['items']:
            if item.get('cover_image'):
                item['cover_url'] = f"{base_url}/image/{item['cover_image']}"
            if item.get('share_enabled') and item.get('share_token'):
                item['share_url'] = f"{base_url}/g/{item['share_token']}"

        return _admin_json({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"Token 画集 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/tokens/<int:token_id>/impact', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_token_impact_api(token_id: int):
    """查询单个 Token 删除影响范围"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        impact = TokenService.get_token_impact(token_id)
        if impact is None:
            return _admin_json({'success': False, 'error': 'Token 不存在'}, 404)
        return _admin_json({'success': True, 'data': impact})

    except Exception as e:
        logger.error(f"Token 影响范围 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)


@admin_bp.route('/api/admin/tokens/batch', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_tokens_batch_api():
    """
    批量操作 API：
    body: { action: "enable"|"disable"|"delete"|"impact", ids: [1,2,3] }
    """
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    try:
        payload = request.get_json(silent=True) or {}
        action = (payload.get('action') or '').strip().lower()
        ids = payload.get('ids')

        if not isinstance(ids, list) or not ids:
            return _admin_json({'success': False, 'error': '请提供有效的 ids 列表'}, 400)

        # 转为整数列表
        try:
            int_ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return _admin_json({'success': False, 'error': 'ids 中包含无效值'}, 400)

        if action == 'enable':
            result = TokenService.batch_update_status(int_ids, is_active=True)
        elif action == 'disable':
            result = TokenService.batch_update_status(int_ids, is_active=False)
        elif action == 'delete':
            result = TokenService.batch_delete(int_ids)
        elif action == 'impact':
            result = TokenService.batch_get_impact(int_ids)
        else:
            return _admin_json({'success': False, 'error': f'无效的操作: {action}'}, 400)

        return _admin_json({'success': True, 'data': result})

    except Exception as e:
        logger.error(f"Token 批量操作 API 失败: {e}")
        return _admin_json({'success': False, 'error': str(e)}, 500)