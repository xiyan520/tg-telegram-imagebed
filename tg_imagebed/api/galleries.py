#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画集路由模块 - Gallery API
"""
from flask import request, jsonify, make_response

from . import auth_bp
from ..config import logger
from ..utils import add_cache_headers, get_domain
from ..database import (
    verify_auth_token,
    create_gallery, get_gallery, list_galleries, update_gallery, delete_gallery,
    add_images_to_gallery, remove_images_from_gallery, get_gallery_images,
    update_gallery_share, get_shared_gallery
)


def _extract_bearer_token() -> str:
    """从 Authorization 头提取 Bearer Token"""
    auth_header = (request.headers.get('Authorization') or '').strip()
    if not auth_header:
        return ''
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()
    return auth_header


def _verify_token():
    """验证 Token 并返回验证结果"""
    token = _extract_bearer_token()
    if not token:
        token = request.args.get('token', '')
    if not token:
        return None, jsonify({'success': False, 'error': '未提供Token'}), 401
    verification = verify_auth_token(token)
    if not verification['valid']:
        return None, jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 401
    return token, None, None


def _cors_response(data, status=200, cache='no-cache'):
    """创建带 CORS 头的响应"""
    response = jsonify(data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, cache), status


def _options_response():
    """处理 OPTIONS 预检请求"""
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return add_cache_headers(response, 'no-cache')


# ===================== 画集 CRUD =====================

@auth_bp.route('/api/auth/galleries', methods=['GET', 'POST', 'OPTIONS'])
def galleries_list_create():
    """获取画集列表 / 创建画集"""
    if request.method == 'OPTIONS':
        return _options_response()

    token, error_resp, status = _verify_token()
    if error_resp:
        error_resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(100, limit))
        result = list_galleries(token, page, limit)
        base_url = get_domain(request)
        for item in result['items']:
            if item.get('cover_image'):
                item['cover_url'] = f"{base_url}/image/{item['cover_image']}"
        return _cors_response({'success': True, 'data': result})

    # POST - 创建画集
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _cors_response({'success': False, 'error': '画集名称不能为空'}, 400)
    if len(name) > 100:
        return _cors_response({'success': False, 'error': '画集名称不能超过100字符'}, 400)
    description = (data.get('description') or '').strip()[:500]
    gallery = create_gallery(token, name, description)
    if not gallery:
        return _cors_response({'success': False, 'error': '创建画集失败'}, 500)
    return _cors_response({'success': True, 'data': {'gallery': gallery}})


@auth_bp.route('/api/auth/galleries/<int:gallery_id>', methods=['GET', 'PATCH', 'DELETE', 'OPTIONS'])
def gallery_detail(gallery_id: int):
    """获取/更新/删除画集"""
    if request.method == 'OPTIONS':
        return _options_response()

    token, error_resp, status = _verify_token()
    if error_resp:
        error_resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        gallery = get_gallery(gallery_id, token)
        if not gallery:
            return _cors_response({'success': False, 'error': '画集不存在'}, 404)
        base_url = get_domain(request)
        if gallery.get('share_enabled') and gallery.get('share_token'):
            gallery['share_url'] = f"{base_url}/g/{gallery['share_token']}"
        return _cors_response({'success': True, 'data': {'gallery': gallery}})

    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        description = data.get('description')
        if name is not None:
            name = str(name).strip()
            if not name:
                return _cors_response({'success': False, 'error': '画集名称不能为空'}, 400)
            if len(name) > 100:
                return _cors_response({'success': False, 'error': '画集名称不能超过100字符'}, 400)
        if description is not None:
            description = str(description).strip()[:500]
        gallery = update_gallery(gallery_id, token, name, description)
        if not gallery:
            return _cors_response({'success': False, 'error': '画集不存在或无权限'}, 404)
        return _cors_response({'success': True, 'data': {'gallery': gallery}})

    # DELETE
    deleted = delete_gallery(gallery_id, token)
    if not deleted:
        return _cors_response({'success': False, 'error': '画集不存在或无权限'}, 404)
    return _cors_response({'success': True})


# ===================== 画集图片管理 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/images', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def gallery_images(gallery_id: int):
    """获取/添加/移除画集图片"""
    if request.method == 'OPTIONS':
        return _options_response()

    token, error_resp, status = _verify_token()
    if error_resp:
        error_resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(100, limit))
        result = get_gallery_images(gallery_id, token, page, limit)
        base_url = get_domain(request)
        for item in result['items']:
            item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"
        return _cors_response({'success': True, 'data': result})

    data = request.get_json(silent=True) or {}
    encrypted_ids = data.get('encrypted_ids', [])
    if not isinstance(encrypted_ids, list) or not encrypted_ids:
        return _cors_response({'success': False, 'error': '请提供图片ID列表'}, 400)
    encrypted_ids = [str(eid).strip() for eid in encrypted_ids if eid][:100]

    if request.method == 'POST':
        result = add_images_to_gallery(gallery_id, token, encrypted_ids)
        return _cors_response({'success': True, 'data': result})

    # DELETE
    removed = remove_images_from_gallery(gallery_id, token, encrypted_ids)
    return _cors_response({'success': True, 'data': {'removed': removed}})


# ===================== 画集分享 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/share', methods=['POST', 'DELETE', 'OPTIONS'])
def gallery_share(gallery_id: int):
    """开启/关闭画集分享"""
    if request.method == 'OPTIONS':
        return _options_response()

    token, error_resp, status = _verify_token()
    if error_resp:
        error_resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled', True)
        expires_at = data.get('expires_at')
        gallery = update_gallery_share(gallery_id, token, enabled, expires_at)
        if not gallery:
            return _cors_response({'success': False, 'error': '画集不存在或无权限'}, 404)
        base_url = get_domain(request)
        share_url = None
        if gallery.get('share_enabled') and gallery.get('share_token'):
            share_url = f"{base_url}/g/{gallery['share_token']}"
        return _cors_response({
            'success': True,
            'data': {
                'share_url': share_url,
                'share_expires_at': gallery.get('share_expires_at')
            }
        })

    # DELETE - 关闭分享
    gallery = update_gallery_share(gallery_id, token, False)
    if not gallery:
        return _cors_response({'success': False, 'error': '画集不存在或无权限'}, 404)
    return _cors_response({'success': True})


# ===================== 公开访问分享画集 =====================

@auth_bp.route('/api/shared/galleries/<share_token>', methods=['GET', 'OPTIONS'])
def shared_gallery_api(share_token: str):
    """公开访问分享的画集"""
    if request.method == 'OPTIONS':
        return _options_response()

    gallery = get_shared_gallery(share_token)
    if not gallery:
        return _cors_response({'success': False, 'error': '画集不存在或分享已关闭'}, 404)

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(100, limit))

    images_result = get_gallery_images(gallery['id'], None, page, limit)
    base_url = get_domain(request)
    for item in images_result['items']:
        item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"

    return _cors_response({
        'success': True,
        'data': {
            'gallery': {
                'name': gallery['name'],
                'description': gallery.get('description'),
                'image_count': gallery['image_count']
            },
            'images': images_result['items'],
            'total': images_result['total'],
            'page': page,
            'limit': limit,
            'has_more': page * limit < images_result['total']
        }
    })
