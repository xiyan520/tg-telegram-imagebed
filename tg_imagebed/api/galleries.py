#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画集路由模块 - Gallery API
"""
from flask import request, jsonify, session

from . import auth_bp
from .auth_helpers import extract_bearer_token, verify_request_token
from ..config import logger, SECRET_KEY
from ..utils import add_cache_headers, get_domain
from ..database import (
    verify_auth_token, verify_auth_token_access,
    create_gallery, get_gallery, list_galleries, update_gallery, delete_gallery,
    set_gallery_cover,
    add_images_to_gallery, remove_images_from_gallery, get_gallery_images,
    update_gallery_share, get_shared_gallery,
    update_gallery_access, verify_gallery_password,
    get_share_all_link, create_or_update_share_all_link, get_share_all_galleries,
    get_share_all_gallery, get_share_all_gallery_images,
    grant_gallery_token_access, revoke_gallery_token_access,
    list_gallery_token_access, is_token_authorized_for_gallery, is_gallery_owner
)


def _extract_bearer_token() -> str:
    """从 Authorization 头提取 Bearer Token（委托给 auth_helpers）"""
    return extract_bearer_token()


def _is_admin_logged_in() -> bool:
    """检查管理员是否已登录"""
    return session.get('admin_logged_in', False)


def _verify_token():
    """验证 Token 并返回验证结果（委托给 auth_helpers）"""
    return verify_request_token()


def _json_response(data, status=200, cache='no-cache'):
    """创建带缓存头的 JSON 响应（CORS 由 Flask-CORS 统一管理）"""
    return add_cache_headers(jsonify(data), cache), status


# ===================== 画集 CRUD =====================

@auth_bp.route('/api/auth/galleries', methods=['GET', 'POST'])
def galleries_list_create():
    """获取画集列表 / 创建画集"""
    token, error_resp, status = _verify_token()
    if error_resp:
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
        return _json_response({'success': True, 'data': result})

    # POST - 创建画集
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _json_response({'success': False, 'error': '画集名称不能为空'}, 400)
    if len(name) > 100:
        return _json_response({'success': False, 'error': '画集名称不能超过100字符'}, 400)
    description = (data.get('description') or '').strip()[:500]
    gallery = create_gallery(token, name, description)
    if not gallery:
        return _json_response({'success': False, 'error': '创建画集失败'}, 500)
    return _json_response({'success': True, 'data': {'gallery': gallery}})


@auth_bp.route('/api/auth/galleries/<int:gallery_id>', methods=['GET', 'PATCH', 'DELETE'])
def gallery_detail(gallery_id: int):
    """获取/更新/删除画集"""
    token, error_resp, status = _verify_token()
    if error_resp:
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        gallery = get_gallery(gallery_id, token)
        if not gallery:
            return _json_response({'success': False, 'error': '画集不存在'}, 404)
        base_url = get_domain(request)
        if gallery.get('share_enabled') and gallery.get('share_token'):
            gallery['share_url'] = f"{base_url}/g/{gallery['share_token']}"
        return _json_response({'success': True, 'data': {'gallery': gallery}})

    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        description = data.get('description')
        if name is not None:
            name = str(name).strip()
            if not name:
                return _json_response({'success': False, 'error': '画集名称不能为空'}, 400)
            if len(name) > 100:
                return _json_response({'success': False, 'error': '画集名称不能超过100字符'}, 400)
        if description is not None:
            description = str(description).strip()[:500]
        gallery = update_gallery(gallery_id, token, name, description)
        if not gallery:
            return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
        return _json_response({'success': True, 'data': {'gallery': gallery}})

    # DELETE
    deleted = delete_gallery(gallery_id, token)
    if not deleted:
        return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
    return _json_response({'success': True})


# ===================== 画集图片管理 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/images', methods=['GET', 'POST', 'DELETE'])
def gallery_images(gallery_id: int):
    """获取/添加/移除画集图片"""
    token, error_resp, status = _verify_token()
    if error_resp:
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(100, limit))
        result = get_gallery_images(gallery_id, token, page, limit)
        base_url = get_domain(request)
        for item in result['items']:
            item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"
        return _json_response({'success': True, 'data': result})

    data = request.get_json(silent=True) or {}
    encrypted_ids = data.get('encrypted_ids', [])
    if not isinstance(encrypted_ids, list) or not encrypted_ids:
        return _json_response({'success': False, 'error': '请提供图片ID列表'}, 400)
    encrypted_ids = [str(eid).strip() for eid in encrypted_ids if eid][:100]

    if request.method == 'POST':
        result = add_images_to_gallery(gallery_id, token, encrypted_ids)
        return _json_response({'success': True, 'data': result})

    # DELETE
    removed = remove_images_from_gallery(gallery_id, token, encrypted_ids)
    return _json_response({'success': True, 'data': {'removed': removed}})


# ===================== 画集封面 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/cover', methods=['PUT', 'DELETE'])
def gallery_cover(gallery_id: int):
    """设置/清除画集封面"""
    token, error_resp, status = _verify_token()
    if error_resp:
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        encrypted_id = (data.get('encrypted_id') or '').strip()
        if not encrypted_id:
            return _json_response({'success': False, 'error': '请提供图片ID'}, 400)
        gallery = set_gallery_cover(gallery_id, token, encrypted_id)
        if not gallery:
            return _json_response({'success': False, 'error': '画集不存在、无权限或图片不在画集中'}, 404)
        base_url = get_domain(request)
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
        return _json_response({'success': True, 'data': {'gallery': gallery}})

    # DELETE - 清除封面
    gallery = set_gallery_cover(gallery_id, token, None)
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
    return _json_response({'success': True, 'data': {'gallery': gallery}})


# ===================== 画集分享 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/share', methods=['POST', 'DELETE'])
def gallery_share(gallery_id: int):
    """开启/关闭画集分享"""
    token, error_resp, status = _verify_token()
    if error_resp:
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled', True)
        expires_at = data.get('expires_at')
        gallery = update_gallery_share(gallery_id, token, enabled, expires_at)
        if not gallery:
            return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
        base_url = get_domain(request)
        share_url = None
        if gallery.get('share_enabled') and gallery.get('share_token'):
            share_url = f"{base_url}/g/{gallery['share_token']}"
        return _json_response({
            'success': True,
            'data': {
                'share_url': share_url,
                'share_expires_at': gallery.get('share_expires_at')
            }
        })

    # DELETE - 关闭分享
    gallery = update_gallery_share(gallery_id, token, False)
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
    return _json_response({'success': True})


# ===================== 画集 Token 授权管理 =====================

@auth_bp.route('/api/auth/galleries/<int:gallery_id>/access-tokens', methods=['GET', 'POST', 'DELETE'])
def gallery_access_tokens(gallery_id: int):
    """管理画集的授权 Token 列表"""
    token, error_resp, status = _verify_token()
    if error_resp:
        return add_cache_headers(error_resp, 'no-cache'), status

    if request.method == 'GET':
        items = list_gallery_token_access(gallery_id, owner_token=token)
        if items is None:
            return _json_response({'success': False, 'error': '画集不存在或无权限'}, 404)
        # 隐藏完整 token，只返回 masked
        for item in items:
            item.pop('token', None)
        return _json_response({'success': True, 'data': {'items': items}})

    data = request.get_json(silent=True) or {}

    if request.method == 'POST':
        target_token = (data.get('token') or '').strip()
        if not target_token:
            return _json_response({'success': False, 'error': '请提供要授权的 Token'}, 400)
        expires_at = data.get('expires_at')
        success = grant_gallery_token_access(gallery_id, target_token, owner_token=token, expires_at=expires_at)
        if not success:
            return _json_response({'success': False, 'error': '授权失败，画集不存在、无权限或 Token 无效'}, 400)
        return _json_response({'success': True, 'message': '授权成功'})

    # DELETE
    target_token = (data.get('token') or '').strip()
    if not target_token:
        return _json_response({'success': False, 'error': '请提供要撤销的 Token'}, 400)
    success = revoke_gallery_token_access(gallery_id, target_token, owner_token=token)
    if not success:
        return _json_response({'success': False, 'error': '撤销失败，画集不存在、无权限或授权不存在'}, 400)
    return _json_response({'success': True, 'message': '撤销成功'})


# ===================== 公开访问分享画集 =====================

@auth_bp.route('/api/shared/galleries/<share_token>', methods=['GET'])
def shared_gallery_api(share_token: str):
    """公开访问分享的画集"""
    gallery = get_shared_gallery(share_token)
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在或分享已关闭'}, 404)

    # 检查访问控制
    access_mode = gallery.get('access_mode', 'public')
    is_admin = _is_admin_logged_in()

    # 管理员跳过所有访问限制
    if not is_admin:
        if access_mode == 'admin_only':
            return _json_response({'success': False, 'error': '画集不存在或分享已关闭'}, 404)

        if access_mode == 'password':
            unlock_cookie = request.cookies.get(f'gallery_unlock_{gallery["id"]}')
            is_unlocked = False
            if unlock_cookie:
                try:
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(SECRET_KEY)
                    data = serializer.loads(unlock_cookie, max_age=86400)
                    is_unlocked = data.get('gallery_id') == gallery['id']
                except Exception:
                    pass
            if not is_unlocked:
                return _json_response({
                    'success': False,
                    'error': '需要密码访问',
                    'requires_password': True,
                    'gallery_id': gallery['id'],
                    'gallery_name': gallery['name']
                }, 403)

        # Token 访问模式检查
        if access_mode == 'token':
            unlock_cookie = request.cookies.get(f'gallery_token_unlock_{gallery["id"]}')
            is_unlocked = False
            if unlock_cookie:
                try:
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(SECRET_KEY)
                    data = serializer.loads(unlock_cookie, max_age=86400)
                    is_unlocked = data.get('gallery_id') == gallery['id']
                except Exception:
                    pass
            if not is_unlocked:
                viewer_token = _extract_bearer_token()
                if viewer_token:
                    verification = verify_auth_token_access(viewer_token)
                    if verification['valid']:
                        if is_gallery_owner(gallery['id'], viewer_token) or is_token_authorized_for_gallery(gallery['id'], viewer_token):
                            is_unlocked = True
            if not is_unlocked:
                return _json_response({
                    'success': False,
                    'error': '需要授权 Token 访问',
                    'requires_token': True,
                    'gallery_id': gallery['id'],
                    'gallery_name': gallery['name']
                }, 403)

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(100, limit))

    images_result = get_gallery_images(gallery['id'], None, page, limit)
    base_url = get_domain(request)
    for item in images_result['items']:
        item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"

    return _json_response({
        'success': True,
        'data': {
            'gallery': {
                'name': gallery['name'],
                'description': gallery.get('description'),
                'image_count': gallery['image_count'],
                'access_mode': access_mode
            },
            'images': images_result['items'],
            'total': images_result['total'],
            'page': page,
            'limit': limit,
            'has_more': page * limit < images_result['total']
        }
    })


# ===================== 密码解锁 =====================

@auth_bp.route('/api/shared/galleries/<share_token>/unlock', methods=['POST'])
def unlock_gallery(share_token: str):
    """密码解锁画集"""
    gallery = get_shared_gallery(share_token)
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在或分享已关闭'}, 404)

    if gallery.get('access_mode') != 'password':
        return _json_response({'success': False, 'error': '该画集不需要密码'}, 400)

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if not password:
        return _json_response({'success': False, 'error': '请输入密码'}, 400)

    if not verify_gallery_password(gallery['id'], password):
        return _json_response({'success': False, 'error': '密码错误'}, 401)

    # 生成签名解锁 token（24小时有效）
    from itsdangerous import URLSafeTimedSerializer
    from ..config import SECRET_KEY
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    unlock_token = serializer.dumps({'gallery_id': gallery['id']})

    response = jsonify({'success': True, 'message': '解锁成功'})
    response.set_cookie(
        f'gallery_unlock_{gallery["id"]}',
        unlock_token,
        max_age=86400,
        httponly=True,
        samesite='Lax'
    )
    return add_cache_headers(response, 'no-cache')


# ===================== Token 解锁 =====================

@auth_bp.route('/api/shared/galleries/<share_token>/unlock-token', methods=['POST'])
def unlock_gallery_with_token(share_token: str):
    """使用 Token 解锁画集"""
    gallery = get_shared_gallery(share_token)
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在或分享已关闭'}, 404)

    if gallery.get('access_mode') != 'token':
        return _json_response({'success': False, 'error': '该画集不需要 Token 验证'}, 400)

    data = request.get_json(silent=True) or {}
    unlock_token_str = (data.get('token') or '').strip()
    if not unlock_token_str:
        return _json_response({'success': False, 'error': '请提供 Token'}, 400)

    # 验证 Token 有效性
    verification = verify_auth_token_access(unlock_token_str)
    if not verification['valid']:
        return _json_response({'success': False, 'error': f"Token 无效: {verification['reason']}"}, 401)

    # 检查是否为所有者或已授权
    if not (is_gallery_owner(gallery['id'], unlock_token_str) or is_token_authorized_for_gallery(gallery['id'], unlock_token_str)):
        return _json_response({'success': False, 'error': '该 Token 未被授权访问此画集'}, 403)

    # 生成解锁 cookie（24小时有效）
    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    cookie_token = serializer.dumps({'gallery_id': gallery['id']})

    response = jsonify({'success': True, 'message': '解锁成功'})
    response.set_cookie(
        f'gallery_token_unlock_{gallery["id"]}',
        cookie_token,
        max_age=86400,
        httponly=True,
        samesite='Lax'
    )
    return add_cache_headers(response, 'no-cache')


# ===================== 全部分享（公开访问） =====================

@auth_bp.route('/api/shared/all/<share_token>', methods=['GET'])
def shared_all_galleries_api(share_token: str):
    """公开访问全部分享画集列表"""
    logger.info(f"访问全部分享API: token={share_token[:8]}...")

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(100, limit))

    result = get_share_all_galleries(share_token, page, limit)
    if not result:
        logger.warning(f"全部分享链接无效: token={share_token[:8]}...")
        return _json_response({'success': False, 'error': '分享链接无效或已过期'}, 404)

    base_url = get_domain(request)
    for item in result['items']:
        # 标记需要验证的画集
        item['is_locked'] = item.get('access_mode') in ('password', 'token')
        # 封面图（优先手动设置，否则为第一张图）
        if item.get('cover_image'):
            item['cover_url'] = f"{base_url}/image/{item['cover_image']}"
        # 单独分享链接（如有）
        if item.get('share_token'):
            item['share_url'] = f"{base_url}/g/{item['share_token']}"
        # 全部分享详情链接
        item['detail_url'] = f"/galleries/{share_token}/{item['id']}"

    return _json_response({
        'success': True,
        'data': result
    })


# ===================== 全部分享 - 单个画集访问 =====================

@auth_bp.route('/api/shared/all/<share_all_token>/galleries/<int:gallery_id>', methods=['GET'])
def shared_all_gallery_detail_api(share_all_token: str, gallery_id: int):
    """全部分享上下文中访问单个画集"""
    gallery = get_share_all_gallery(share_all_token, gallery_id)
    if not gallery:
        return _json_response({'success': False, 'error': '分享链接无效或画集不可见'}, 404)

    access_mode = gallery.get('access_mode', 'public')
    is_admin = _is_admin_logged_in()

    # 管理员跳过所有访问限制
    if not is_admin:
        # 检查密码保护
        if access_mode == 'password':
            unlock_cookie = request.cookies.get(f'gallery_unlock_{gallery["id"]}')
            is_unlocked = False
            if unlock_cookie:
                try:
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(SECRET_KEY)
                    data = serializer.loads(unlock_cookie, max_age=86400)
                    is_unlocked = data.get('gallery_id') == gallery['id']
                except Exception:
                    pass
            if not is_unlocked:
                return _json_response({
                    'success': False,
                    'error': '需要密码访问',
                    'requires_password': True,
                    'gallery_id': gallery['id'],
                    'gallery_name': gallery['name']
                }, 403)

        # 检查 Token 访问控制（避免通过 share-all 绕过）
        if access_mode == 'token':
            unlock_cookie = request.cookies.get(f'gallery_token_unlock_{gallery["id"]}')
            is_unlocked = False
            if unlock_cookie:
                try:
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(SECRET_KEY)
                    data = serializer.loads(unlock_cookie, max_age=86400)
                    is_unlocked = data.get('gallery_id') == gallery['id']
                except Exception:
                    pass
            if not is_unlocked:
                viewer_token = _extract_bearer_token()
                if viewer_token:
                    verification = verify_auth_token_access(viewer_token)
                    if verification['valid']:
                        if is_gallery_owner(gallery['id'], viewer_token) or is_token_authorized_for_gallery(gallery['id'], viewer_token):
                            is_unlocked = True
            if not is_unlocked:
                return _json_response({
                    'success': False,
                    'error': '需要授权 Token 访问',
                    'requires_token': True,
                    'gallery_id': gallery['id'],
                    'gallery_name': gallery['name']
                }, 403)

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(100, limit))

    images_result = get_share_all_gallery_images(share_all_token, gallery['id'], page, limit)
    if not images_result:
        return _json_response({'success': False, 'error': '分享链接无效或画集不可见'}, 404)

    base_url = get_domain(request)
    for item in images_result['items']:
        item['image_url'] = f"{base_url}/image/{item['encrypted_id']}"

    return _json_response({
        'success': True,
        'data': {
            'gallery': {
                'id': gallery['id'],
                'name': gallery['name'],
                'description': gallery.get('description'),
                'image_count': gallery.get('image_count', 0),
                'access_mode': access_mode
            },
            'images': images_result['items'],
            'total': images_result['total'],
            'page': page,
            'limit': limit,
            'has_more': page * limit < images_result['total']
        }
    })


@auth_bp.route('/api/shared/all/<share_all_token>/galleries/<int:gallery_id>/unlock', methods=['POST'])
def shared_all_unlock_gallery_api(share_all_token: str, gallery_id: int):
    """全部分享上下文中解锁密码保护的画集"""
    gallery = get_share_all_gallery(share_all_token, gallery_id)
    if not gallery:
        return _json_response({'success': False, 'error': '分享链接无效或画集不可见'}, 404)

    if gallery.get('access_mode') != 'password':
        return _json_response({'success': False, 'error': '该画集不需要密码'}, 400)

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if not password:
        return _json_response({'success': False, 'error': '请输入密码'}, 400)

    if not verify_gallery_password(gallery['id'], password):
        return _json_response({'success': False, 'error': '密码错误'}, 401)

    from itsdangerous import URLSafeTimedSerializer
    from ..config import SECRET_KEY
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    unlock_token = serializer.dumps({'gallery_id': gallery['id']})

    response = jsonify({'success': True, 'message': '解锁成功'})
    response.set_cookie(
        f'gallery_unlock_{gallery["id"]}',
        unlock_token,
        max_age=86400,
        httponly=True,
        samesite='Lax'
    )
    return add_cache_headers(response, 'no-cache')


@auth_bp.route('/api/shared/all/<share_all_token>/galleries/<int:gallery_id>/unlock-token', methods=['POST'])
def shared_all_unlock_gallery_with_token_api(share_all_token: str, gallery_id: int):
    """全部分享上下文中使用 Token 解锁画集"""
    gallery = get_share_all_gallery(share_all_token, gallery_id)
    if not gallery:
        return _json_response({'success': False, 'error': '分享链接无效或画集不可见'}, 404)

    if gallery.get('access_mode') != 'token':
        return _json_response({'success': False, 'error': '该画集不需要 Token 验证'}, 400)

    data = request.get_json(silent=True) or {}
    unlock_token_str = (data.get('token') or '').strip()
    if not unlock_token_str:
        return _json_response({'success': False, 'error': '请提供 Token'}, 400)

    verification = verify_auth_token_access(unlock_token_str)
    if not verification['valid']:
        return _json_response({'success': False, 'error': f"Token 无效: {verification['reason']}"}, 401)

    if not (is_gallery_owner(gallery['id'], unlock_token_str) or is_token_authorized_for_gallery(gallery['id'], unlock_token_str)):
        return _json_response({'success': False, 'error': '该 Token 未被授权访问此画集'}, 403)

    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    cookie_token = serializer.dumps({'gallery_id': gallery['id']})

    response = jsonify({'success': True, 'message': '解锁成功'})
    response.set_cookie(
        f'gallery_token_unlock_{gallery["id"]}',
        cookie_token,
        max_age=86400,
        httponly=True,
        samesite='Lax'
    )
    return add_cache_headers(response, 'no-cache')


# ===================== 管理员API - 画集访问控制 =====================

from . import admin_bp
from ..admin_module import login_required

@admin_bp.route('/api/admin/galleries/<int:gallery_id>/access', methods=['PATCH'])
@login_required
def admin_gallery_access(gallery_id: int):
    """管理员设置画集访问控制"""
    data = request.get_json(silent=True) or {}
    access_mode = data.get('access_mode')
    password = data.get('password')
    hide_from_share_all = data.get('hide_from_share_all')

    if access_mode and access_mode not in ('public', 'password', 'admin_only', 'token'):
        return _json_response({'success': False, 'error': '无效的访问模式'}, 400)

    if access_mode == 'password' and not password:
        return _json_response({'success': False, 'error': '密码模式需要设置密码'}, 400)

    gallery = update_gallery_access(
        gallery_id,
        access_mode=access_mode,
        password=password,
        hide_from_share_all=hide_from_share_all,
        is_admin=True
    )
    if not gallery:
        return _json_response({'success': False, 'error': '画集不存在'}, 404)

    return _json_response({'success': True, 'data': {'gallery': gallery}})


# ===================== 管理员API - 画集 Token 授权管理 =====================

@admin_bp.route('/api/admin/galleries/<int:gallery_id>/access-tokens', methods=['GET', 'POST', 'DELETE'])
@login_required
def admin_gallery_access_tokens(gallery_id: int):
    """管理员管理画集的授权 Token 列表"""
    if request.method == 'GET':
        items = list_gallery_token_access(gallery_id, is_admin=True)
        if items is None:
            return _json_response({'success': False, 'error': '画集不存在'}, 404)
        return _json_response({'success': True, 'data': {'items': items}})

    data = request.get_json(silent=True) or {}

    if request.method == 'POST':
        target_token = (data.get('token') or '').strip()
        if not target_token:
            return _json_response({'success': False, 'error': '请提供要授权的 Token'}, 400)
        expires_at = data.get('expires_at')
        success = grant_gallery_token_access(gallery_id, target_token, expires_at=expires_at, is_admin=True)
        if not success:
            return _json_response({'success': False, 'error': '授权失败，画集不存在或 Token 无效'}, 400)
        return _json_response({'success': True, 'message': '授权成功'})

    # DELETE
    target_token = (data.get('token') or '').strip()
    if not target_token:
        return _json_response({'success': False, 'error': '请提供要撤销的 Token'}, 400)
    success = revoke_gallery_token_access(gallery_id, target_token, is_admin=True)
    if not success:
        return _json_response({'success': False, 'error': '撤销失败，画集不存在或授权不存在'}, 400)
    return _json_response({'success': True, 'message': '撤销成功'})


# ===================== 管理员API - 全部分享链接管理 =====================

@admin_bp.route('/api/admin/share-all', methods=['GET', 'POST', 'DELETE'])
@login_required
def admin_share_all():
    """管理员管理全部分享链接"""
    base_url = get_domain(request)

    if request.method == 'GET':
        link = get_share_all_link()
        if link:
            link['share_url'] = f"{base_url}/galleries/{link['share_token']}"
        return _json_response({'success': True, 'data': {'link': link}})

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled', True)
        expires_at = data.get('expires_at')
        rotate = data.get('rotate', False)

        link = create_or_update_share_all_link(enabled, expires_at, rotate)
        if not link:
            return _json_response({'success': False, 'error': '创建分享链接失败'}, 500)

        link['share_url'] = f"{base_url}/galleries/{link['share_token']}"
        return _json_response({'success': True, 'data': {'link': link}})

    # DELETE - 禁用分享链接
    link = create_or_update_share_all_link(enabled=False)
    return _json_response({'success': True})
