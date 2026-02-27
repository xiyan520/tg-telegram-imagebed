#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - 画集管理
"""
from flask import request

from . import admin_bp
from .admin_helpers import _get_cdn_domain, _admin_json, _admin_options
from ..config import logger
from ..utils import get_domain, get_image_domain
from ..database import (
    get_system_setting,
    admin_list_galleries, admin_create_gallery, admin_get_gallery,
    admin_update_gallery, admin_delete_gallery, admin_set_gallery_cover,
    admin_add_images_to_gallery, admin_remove_images_from_gallery,
    admin_get_gallery_images, admin_update_gallery_share,
)
from .. import admin_module


@admin_bp.route('/api/admin/galleries', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_galleries_list_create():
    """管理员画集列表/创建"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, POST, OPTIONS')

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(200, limit))
        search = request.args.get('search', '').strip() or None
        sort = request.args.get('sort', '').strip() or None
        result = admin_list_galleries(page, limit, search=search, sort=sort)
        base_url = get_domain(request)
        img_base_url = get_image_domain(request)
        for item in result['items']:
            if item.get('cover_image'):
                item['cover_url'] = f"{img_base_url}/image/{item['cover_image']}"
            if item.get('share_enabled') and item.get('share_token'):
                item['share_url'] = f"{base_url}/g/{item['share_token']}"
        return _admin_json({'success': True, 'data': result})

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _admin_json({'success': False, 'error': '画集名称不能为空'}, 400)
    if len(name) > 100:
        return _admin_json({'success': False, 'error': '画集名称不能超过100字符'}, 400)
    description = (data.get('description') or '').strip()[:500]
    gallery = admin_create_gallery(name, description)
    if not gallery:
        return _admin_json({'success': False, 'error': '创建画集失败'}, 500)
    return _admin_json({'success': True, 'data': {'gallery': gallery}})


@admin_bp.route('/api/admin/galleries/<int:gallery_id>', methods=['GET', 'PATCH', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_gallery_detail(gallery_id: int):
    """管理员画集详情/更新/删除"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, PATCH, DELETE, OPTIONS')

    if request.method == 'GET':
        gallery = admin_get_gallery(gallery_id)
        if not gallery:
            return _admin_json({'success': False, 'error': '画集不存在'}, 404)
        base_url = get_domain(request)
        img_base_url = get_image_domain(request)
        if gallery.get('share_enabled') and gallery.get('share_token'):
            gallery['share_url'] = f"{base_url}/g/{gallery['share_token']}"
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{img_base_url}/image/{gallery['cover_image']}"
        return _admin_json({'success': True, 'data': {'gallery': gallery}})

    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        description = data.get('description')
        if name is not None:
            name = str(name).strip()
            if not name:
                return _admin_json({'success': False, 'error': '画集名称不能为空'}, 400)
            if len(name) > 100:
                return _admin_json({'success': False, 'error': '画集名称不能超过100字符'}, 400)
        if description is not None:
            description = str(description).strip()[:500]
        # 显示设置字段
        layout_mode = data.get('layout_mode')
        theme_color = data.get('theme_color')
        show_image_info = data.get('show_image_info')
        allow_download = data.get('allow_download')
        sort_order = data.get('sort_order')
        nsfw_warning = data.get('nsfw_warning')
        custom_header_text = data.get('custom_header_text')
        gallery = admin_update_gallery(
            gallery_id, name=name, description=description,
            layout_mode=layout_mode, theme_color=theme_color,
            show_image_info=show_image_info, allow_download=allow_download,
            sort_order=sort_order, nsfw_warning=nsfw_warning,
            custom_header_text=custom_header_text
        )
        if not gallery:
            return _admin_json({'success': False, 'error': '画集不存在'}, 404)
        return _admin_json({'success': True, 'data': {'gallery': gallery}})

    deleted = admin_delete_gallery(gallery_id)
    if not deleted:
        return _admin_json({'success': False, 'error': '画集不存在'}, 404)
    return _admin_json({'success': True})


@admin_bp.route('/api/admin/galleries/<int:gallery_id>/images', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_gallery_images(gallery_id: int):
    """管理员画集图片管理"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, POST, DELETE, OPTIONS')

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(200, limit))
        result = admin_get_gallery_images(gallery_id, page, limit)
        base_url = get_image_domain(request)
        cdn_domain = _get_cdn_domain()
        cdn_enabled = str(get_system_setting('cdn_enabled') or '0') == '1'
        for item in result['items']:
            item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"
            if cdn_enabled and cdn_domain:
                item['cdn_url'] = f"https://{cdn_domain}/image/{item['encrypted_id']}"
            else:
                item['cdn_url'] = None
        return _admin_json({'success': True, 'data': result})

    data = request.get_json(silent=True) or {}
    encrypted_ids = data.get('encrypted_ids', [])
    if not isinstance(encrypted_ids, list) or not encrypted_ids:
        return _admin_json({'success': False, 'error': '请提供图片ID列表'}, 400)
    encrypted_ids = list(dict.fromkeys([str(e).strip() for e in encrypted_ids if str(e).strip()]))[:500]
    if not encrypted_ids:
        return _admin_json({'success': False, 'error': '请提供图片ID列表'}, 400)

    if request.method == 'POST':
        result = admin_add_images_to_gallery(gallery_id, encrypted_ids)
        return _admin_json({'success': True, 'data': result})

    removed = admin_remove_images_from_gallery(gallery_id, encrypted_ids)
    return _admin_json({'success': True, 'data': {'removed': removed}})


@admin_bp.route('/api/admin/galleries/<int:gallery_id>/share', methods=['POST', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_gallery_share(gallery_id: int):
    """管理员画集分享管理"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, DELETE, OPTIONS')

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        expires_at = data.get('expires_at')
        try:
            gallery = admin_update_gallery_share(gallery_id, enabled, expires_at)
        except ValueError as e:
            return _admin_json({'success': False, 'error': str(e)}, 400)
        if not gallery:
            return _admin_json({'success': False, 'error': '画集不存在'}, 404)
        base_url = get_domain(request)
        share_url = f"{base_url}/g/{gallery['share_token']}" if gallery.get('share_enabled') and gallery.get('share_token') else None
        return _admin_json({'success': True, 'data': {'share_url': share_url, 'share_expires_at': gallery.get('share_expires_at')}})

    try:
        gallery = admin_update_gallery_share(gallery_id, False)
    except ValueError as e:
        return _admin_json({'success': False, 'error': str(e)}, 400)
    if not gallery:
        return _admin_json({'success': False, 'error': '画集不存在'}, 404)
    return _admin_json({'success': True})


@admin_bp.route('/api/admin/galleries/<int:gallery_id>/cover', methods=['PUT', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_gallery_cover(gallery_id: int):
    """管理员设置/清除画集封面"""
    if request.method == 'OPTIONS':
        return _admin_options('PUT, DELETE, OPTIONS')

    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        encrypted_id = (data.get('encrypted_id') or '').strip()
        if not encrypted_id:
            return _admin_json({'success': False, 'error': '未指定封面图片'}, 400)
        gallery = admin_set_gallery_cover(gallery_id, encrypted_id)
        if not gallery:
            return _admin_json({'success': False, 'error': '画集不存在或图片不在画集中'}, 404)
        base_url = get_image_domain(request)
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
        return _admin_json({'success': True, 'data': {'gallery': gallery}})

    # DELETE - 清除手动设置的封面，恢复默认
    gallery = admin_set_gallery_cover(gallery_id, None)
    if not gallery:
        return _admin_json({'success': False, 'error': '画集不存在'}, 404)
    base_url = get_image_domain(request)
    if gallery.get('cover_image'):
        gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
    return _admin_json({'success': True, 'data': {'gallery': gallery}})