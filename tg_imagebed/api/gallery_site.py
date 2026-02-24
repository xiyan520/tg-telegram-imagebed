#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画集站点公开 API - 画集域名专用路由

提供画集域名下的公开浏览接口，无需认证。
管理端点需要通过 SSO token 或 session 认证。
"""
from functools import wraps
from urllib.parse import quote
from flask import request, jsonify, make_response, session, redirect

from . import gallery_site_bp
from ..config import logger
from ..utils import add_cache_headers, get_image_domain, get_domain
from ..database import (
    get_system_setting, get_system_setting_int,
    update_system_setting,
    is_gallery_domain,
)
from ..database.connection import get_connection
from ..database.domains import get_default_domain, get_active_gallery_domains
from .. import admin_module
from ..database.admin_galleries import admin_get_gallery, admin_delete_gallery, admin_get_gallery_images, admin_update_gallery_share, admin_add_images_to_gallery, admin_remove_images_from_gallery, admin_set_gallery_cover
from ..database.galleries import update_gallery_access, list_gallery_token_access, grant_gallery_token_access, revoke_gallery_token_access


def _set_public_cors_headers(response):
    """设置公开 API 的 CORS 头"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


def _handle_options():
    """统一处理 OPTIONS 预检请求"""
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return add_cache_headers(response, 'no-cache')


def _build_cover_urls(items):
    """为画集列表项构建封面图 URL"""
    base_url = get_image_domain(request)
    for item in items:
        if item.get('cover_image'):
            item['cover_url'] = f"{base_url}/image/{item['cover_image']}"
        else:
            item['cover_url'] = None


# 公开画集列表的通用 SQL（含封面和图片数量）
_GALLERY_LIST_SQL = '''
    SELECT g.id, g.name, g.description, g.created_at, g.updated_at,
        (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
        COALESCE(g.cover_image, (
            SELECT fs.encrypted_id
            FROM gallery_images gi2
            JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
            WHERE gi2.gallery_id = g.id
            ORDER BY gi2.added_at ASC LIMIT 1
        )) AS cover_image
    FROM galleries g
    WHERE g.share_enabled = 1 AND g.access_mode = 'public'
    ORDER BY g.updated_at DESC
'''


# ===================== 站点模式检测 =====================
@gallery_site_bp.route('/api/public/site-mode', methods=['GET', 'OPTIONS'])
def site_mode_api():
    """检测当前域名的站点模式（画集域名返回 gallery 模式）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        host = request.headers.get('Host', '').split(':')[0]

        # 检查画集站点总开关
        gallery_enabled = str(get_system_setting('gallery_site_enabled') or '1') == '1'

        if gallery_enabled and is_gallery_domain(host):
            site_name = get_system_setting('gallery_site_name') or '画集'
            site_description = get_system_setting('gallery_site_description') or '精选图片画集'
            response = jsonify({
                'success': True,
                'data': {
                    'mode': 'gallery',
                    'site_name': site_name,
                    'site_description': site_description,
                }
            })
        else:
            response = jsonify({
                'success': True,
                'data': {'mode': 'default'}
            })

        return _set_public_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"站点模式检测失败: {e}")
        response = jsonify({'success': False, 'error': '检测失败'})
        return _set_public_cors_headers(response), 500


# ===================== 画集公开浏览 API =====================
@gallery_site_bp.route('/api/gallery-site/galleries', methods=['GET', 'OPTIONS'])
def gallery_site_list():
    """获取所有公开画集列表（share_enabled=1, access_mode='public'）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        page = max(1, page)
        per_page = max(1, min(100, per_page))

        with get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page

            # 统计总数
            cursor.execute('''
                SELECT COUNT(*) FROM galleries
                WHERE share_enabled = 1 AND access_mode = 'public'
            ''')
            total = cursor.fetchone()[0]

            # 获取画集列表（含封面和图片数量）
            cursor.execute(_GALLERY_LIST_SQL + 'LIMIT ? OFFSET ?', (per_page, offset))
            items = [dict(row) for row in cursor.fetchall()]

        _build_cover_urls(items)

        response = jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'has_more': page * per_page < total,
            }
        })
        return _set_public_cors_headers(add_cache_headers(response, 'public', 60))

    except Exception as e:
        logger.error(f"获取公开画集列表失败: {e}")
        response = jsonify({'success': False, 'error': '获取画集列表失败'})
        return _set_public_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/galleries/<int:gallery_id>', methods=['GET', 'OPTIONS'])
def gallery_site_detail(gallery_id):
    """获取单个公开画集详情（含图片列表分页）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        page = request.args.get('page', 1, type=int)
        per_page = get_system_setting_int('gallery_site_images_per_page', 20, minimum=1, maximum=100)
        page = max(1, page)

        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取画集信息（仅公开且已分享）
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.created_at, g.updated_at,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count
                FROM galleries g
                WHERE g.id = ? AND g.share_enabled = 1 AND g.access_mode = 'public'
            ''', (gallery_id,))
            gallery_row = cursor.fetchone()
            if not gallery_row:
                response = jsonify({'success': False, 'error': '画集不存在或不可访问'})
                return _set_public_cors_headers(response), 404

            gallery = dict(gallery_row)

            # 获取图片列表
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT fs.encrypted_id, fs.original_filename, fs.file_size,
                       fs.mime_type, fs.created_at, gi.added_at
                FROM gallery_images gi
                JOIN file_storage fs ON gi.encrypted_id = fs.encrypted_id
                WHERE gi.gallery_id = ?
                ORDER BY gi.added_at DESC
                LIMIT ? OFFSET ?
            ''', (gallery_id, per_page, offset))
            images = [dict(r) for r in cursor.fetchall()]

        # 构建图片 URL
        base_url = get_image_domain(request)
        for img in images:
            img['url'] = f"{base_url}/image/{img['encrypted_id']}"

        total = gallery['image_count']
        response = jsonify({
            'success': True,
            'data': {
                'gallery': gallery,
                'images': {
                    'items': images,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'has_more': page * per_page < total,
                }
            }
        })
        return _set_public_cors_headers(add_cache_headers(response, 'public', 60))

    except Exception as e:
        logger.error(f"获取公开画集详情失败: {e}")
        response = jsonify({'success': False, 'error': '获取画集详情失败'})
        return _set_public_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/featured', methods=['GET', 'OPTIONS'])
def gallery_site_featured():
    """获取推荐/精选画集（最新的公开画集）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        limit = request.args.get('limit', 6, type=int)
        limit = max(1, min(20, limit))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(_GALLERY_LIST_SQL + 'LIMIT ?', (limit,))
            items = [dict(row) for row in cursor.fetchall()]

        _build_cover_urls(items)

        response = jsonify({'success': True, 'data': items})
        return _set_public_cors_headers(add_cache_headers(response, 'public', 60))

    except Exception as e:
        logger.error(f"获取精选画集失败: {e}")
        response = jsonify({'success': False, 'error': '获取精选画集失败'})
        return _set_public_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/stats', methods=['GET', 'OPTIONS'])
def gallery_site_stats():
    """画集站点统计（公开画集数、总图片数）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 公开画集数
            cursor.execute('''
                SELECT COUNT(*) FROM galleries
                WHERE share_enabled = 1 AND access_mode = 'public'
            ''')
            gallery_count = cursor.fetchone()[0]

            # 公开画集中的总图片数
            cursor.execute('''
                SELECT COUNT(*) FROM gallery_images gi
                JOIN galleries g ON gi.gallery_id = g.id
                WHERE g.share_enabled = 1 AND g.access_mode = 'public'
            ''')
            image_count = cursor.fetchone()[0]

        response = jsonify({
            'success': True,
            'data': {
                'gallery_count': gallery_count,
                'image_count': image_count,
            }
        })
        return _set_public_cors_headers(add_cache_headers(response, 'public', 120))

    except Exception as e:
        logger.error(f"获取画集站点统计失败: {e}")
        response = jsonify({'success': False, 'error': '获取统计失败'})
        return _set_public_cors_headers(response), 500


# ===================== SSO 重定向端点 =====================

def _get_main_site_url(request):
    """获取主站 URL，用于 SSO 重定向

    优先级：gallery_sso_main_url 设置 > default域名 > 非gallery活跃域名 > get_domain fallback
    """
    # 0. 优先使用管理员配置 gallery 域名时自动保存的主站 URL
    saved_url = get_system_setting('gallery_sso_main_url')
    if saved_url:
        return saved_url

    # 1. 使用 default 域名
    default_domain = get_default_domain()
    if default_domain:
        scheme = 'https' if default_domain.get('use_https') else 'http'
        return f"{scheme}://{default_domain['domain']}"

    # 2. 尝试获取非 gallery 类型的活跃域名
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT domain, use_https FROM custom_domains
                WHERE domain_type != 'gallery' AND is_active = 1
                ORDER BY is_default DESC, sort_order ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                scheme = 'https' if row['use_https'] else 'http'
                return f"{scheme}://{row['domain']}"
    except Exception:
        pass

    # 3. 最终 fallback
    return get_domain(request)


@gallery_site_bp.route('/api/gallery-site/sso-redirect', methods=['GET'])
def gallery_sso_redirect():
    """SSO 重定向入口：画集站点发起，重定向到主站 SSO 回调"""
    return_url = request.args.get('return_url', '/gallery-site/admin')

    # 纵深防御：return_url 必须是相对路径（以 / 开头），防止构造恶意绝对 URL
    if not return_url.startswith('/'):
        return_url = '/gallery-site/admin'

    # 获取主站 URL（优先级：default域名 > 非gallery类型的活跃域名 > get_domain fallback）
    main_site_url = _get_main_site_url(request)

    # 获取当前请求的完整 URL 前缀（scheme + host）
    forwarded_proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    forwarded_host = (
        request.headers.get('X-Forwarded-Host')
        or request.headers.get('Host')
        or request.host
    )
    current_origin = f"{forwarded_proto}://{forwarded_host}"

    # 构建完整回跳 URL
    full_return_url = f"{current_origin}{return_url}"

    callback_url = f"{main_site_url}/api/admin/gallery-sso-callback?return_url={quote(full_return_url, safe='')}"

    return redirect(callback_url)


# ===================== 管理端点 CORS + 认证 =====================

def _set_admin_cors_headers(response):
    """设置管理端点的 CORS 头（支持 credentials）"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


def _handle_admin_options():
    """统一处理管理端点 OPTIONS 预检请求"""
    response = make_response()
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(response, 'no-cache')


def gallery_admin_required(f):
    """画集管理端点认证装饰器（复用 Flask session 中的 admin_logged_in）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # OPTIONS 预检请求不携带 cookie，直接放行
        if request.method == 'OPTIONS':
            return _handle_admin_options()
        if not session.get('admin_logged_in'):
            response = jsonify({'success': False, 'error': '未认证'})
            return _set_admin_cors_headers(response), 401
        return f(*args, **kwargs)
    return decorated


# ===================== SSO 认证端点 =====================

@gallery_site_bp.route('/api/gallery-site/admin/auth', methods=['POST', 'OPTIONS'])
def gallery_admin_auth():
    """验证 SSO token，创建 Flask session"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    try:
        data = request.get_json()
        token = (data or {}).get('token', '')
        if not token:
            response = jsonify({'success': False, 'error': '缺少 token'})
            return _set_admin_cors_headers(response), 400

        valid, username = admin_module.verify_gallery_auth_token(token)
        if not valid:
            response = jsonify({'success': False, 'error': 'token 无效或已过期'})
            return _set_admin_cors_headers(response), 401

        # 创建 session
        session['admin_logged_in'] = True
        session['admin_username'] = username
        session.permanent = True

        response = jsonify({
            'success': True,
            'data': {'username': username}
        })
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"画集 SSO 认证失败: {e}")
        response = jsonify({'success': False, 'error': '认证失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/check', methods=['GET', 'OPTIONS'])
def gallery_admin_check():
    """检查当前 session 是否已认证"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    authenticated = bool(session.get('admin_logged_in'))
    response = jsonify({
        'success': True,
        'data': {
            'authenticated': authenticated,
            'username': session.get('admin_username', '') if authenticated else '',
        }
    })
    return _set_admin_cors_headers(response)


@gallery_site_bp.route('/api/gallery-site/admin/logout', methods=['POST', 'OPTIONS'])
def gallery_admin_logout():
    """画集管理登出"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    response = jsonify({'success': True})
    return _set_admin_cors_headers(response)


# ===================== 画集后台设置 API =====================

_GALLERY_SETTINGS_KEYS = [
    'gallery_site_name',
    'gallery_site_description',
    'gallery_site_enabled',
    'gallery_site_images_per_page',
]


@gallery_site_bp.route('/api/gallery-site/admin/settings', methods=['GET', 'PUT', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_settings():
    """获取/更新画集站点设置"""
    try:
        if request.method == 'GET':
            settings = {}
            for key in _GALLERY_SETTINGS_KEYS:
                raw = get_system_setting(key)
                if key == 'gallery_site_enabled':
                    settings[key] = str(raw or '1') == '1'
                elif key == 'gallery_site_images_per_page':
                    try:
                        settings[key] = int(raw) if raw else 20
                    except (TypeError, ValueError):
                        settings[key] = 20
                else:
                    settings[key] = raw or ''
            response = jsonify({'success': True, 'data': settings})
            return _set_admin_cors_headers(response)

        # PUT: 更新设置
        data = request.get_json()
        if not data:
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        updated = {}
        for key in _GALLERY_SETTINGS_KEYS:
            if key in data:
                raw = data[key]
                if key == 'gallery_site_enabled':
                    value = '1' if raw else '0'
                elif key == 'gallery_site_images_per_page':
                    try:
                        value = str(max(1, min(100, int(raw))))
                    except (TypeError, ValueError):
                        value = '20'
                else:
                    value = str(raw).strip()
                update_system_setting(key, value)
                updated[key] = value

        response = jsonify({'success': True, 'data': updated})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"画集设置操作失败: {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


# ===================== 画集管理 API（管理员可见全部） =====================

@gallery_site_bp.route('/api/gallery-site/admin/galleries', methods=['GET', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_list():
    """获取所有画集列表（管理员可见全部，不限 public）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        page = max(1, page)
        per_page = max(1, min(100, per_page))

        with get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page

            # 统计总数（全部画集）
            cursor.execute('SELECT COUNT(*) FROM galleries')
            total = cursor.fetchone()[0]

            # 获取画集列表（含封面和图片数量，不限 share_enabled/access_mode）
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.share_enabled, g.access_mode,
                    g.created_at, g.updated_at,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT fs.encrypted_id
                        FROM gallery_images gi2
                        JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                        WHERE gi2.gallery_id = g.id
                        ORDER BY gi2.added_at ASC LIMIT 1
                    )) AS cover_image
                FROM galleries g
                ORDER BY g.updated_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            items = [dict(row) for row in cursor.fetchall()]

        _build_cover_urls(items)

        response = jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'has_more': page * per_page < total,
            }
        })
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"获取管理画集列表失败: {e}")
        response = jsonify({'success': False, 'error': '获取画集列表失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>', methods=['PATCH', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_toggle(gallery_id):
    """快速切换画集的 share_enabled 和 access_mode"""
    try:
        data = request.get_json()
        if not data:
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        updates = []
        params = []

        if 'share_enabled' in data:
            updates.append('share_enabled = ?')
            params.append(1 if data['share_enabled'] else 0)

        if 'access_mode' in data:
            mode = data['access_mode']
            if mode not in ('public', 'password', 'token', 'admin_only'):
                response = jsonify({'success': False, 'error': '无效的访问模式'})
                return _set_admin_cors_headers(response), 400
            updates.append('access_mode = ?')
            params.append(mode)

        if not updates:
            response = jsonify({'success': False, 'error': '没有要更新的字段'})
            return _set_admin_cors_headers(response), 400

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(gallery_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE galleries SET {", ".join(updates)} WHERE id = ?',
                params
            )
            if cursor.rowcount == 0:
                response = jsonify({'success': False, 'error': '画集不存在'})
                return _set_admin_cors_headers(response), 404

        response = jsonify({'success': True, 'message': '更新成功'})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"更新画集状态失败 (id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '更新失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/detail', methods=['GET', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_detail(gallery_id):
    """获取画集详情 + 图片列表"""
    try:
        gallery = admin_get_gallery(gallery_id)
        if not gallery:
            response = jsonify({'success': False, 'error': '画集不存在'})
            return _set_admin_cors_headers(response), 404

        # 构建封面 URL
        base_url = get_image_domain(request)
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
        else:
            gallery['cover_url'] = None

        # 构建分享链接
        if gallery.get('share_enabled') and gallery.get('share_token'):
            gallery['share_url'] = f"{get_domain(request)}/g/{gallery['share_token']}"
        else:
            gallery['share_url'] = None

        # 标记是否设置了密码
        gallery['has_password'] = bool(gallery.get('password_hash'))
        gallery.pop('password_hash', None)

        # 获取图片列表
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        page = max(1, page)
        per_page = max(1, min(200, per_page))

        images_data = admin_get_gallery_images(gallery_id, page=page, limit=per_page)

        # 构建图片 URL
        for img in images_data.get('items', []):
            img['url'] = f"{base_url}/image/{img['encrypted_id']}"

        response = jsonify({
            'success': True,
            'data': {
                'gallery': gallery,
                'images': {
                    'items': images_data['items'],
                    'total': images_data['total'],
                    'page': images_data['page'],
                    'per_page': images_data['limit'],
                    'has_more': images_data['page'] * images_data['limit'] < images_data['total'],
                }
            }
        })
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"获取画集详情失败 (id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '获取画集详情失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>', methods=['DELETE', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_delete(gallery_id):
    """删除画集"""
    try:
        success = admin_delete_gallery(gallery_id)
        if not success:
            response = jsonify({'success': False, 'error': '画集不存在'})
            return _set_admin_cors_headers(response), 404

        response = jsonify({'success': True, 'message': '画集已删除'})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"删除画集失败 (id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '删除失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/share', methods=['POST', 'DELETE', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_share(gallery_id):
    """管理画集分享（POST 开启，DELETE 关闭）"""
    try:
        enabled = request.method == 'POST'
        result = admin_update_gallery_share(gallery_id, enabled=enabled)
        if result is None:
            response = jsonify({'success': False, 'error': '画集不存在'})
            return _set_admin_cors_headers(response), 404

        # 构建分享链接
        if result.get('share_enabled') and result.get('share_token'):
            result['share_url'] = f"{get_domain(request)}/g/{result['share_token']}"
        else:
            result['share_url'] = None

        # 构建封面 URL
        base_url = get_image_domain(request)
        if result.get('cover_image'):
            result['cover_url'] = f"{base_url}/image/{result['cover_image']}"
        else:
            result['cover_url'] = None

        result['has_password'] = bool(result.get('password_hash'))
        result.pop('password_hash', None)

        response = jsonify({'success': True, 'data': {'gallery': result}})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"更新画集分享失败 (id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/access', methods=['PATCH', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_access(gallery_id):
    """更新画集访问控制"""
    try:
        data = request.get_json()
        if not data:
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        result = update_gallery_access(
            gallery_id,
            access_mode=data.get('access_mode'),
            password=data.get('password'),
            hide_from_share_all=data.get('hide_from_share_all'),
            is_admin=True
        )
        if result is None:
            response = jsonify({'success': False, 'error': '画集不存在或参数无效'})
            return _set_admin_cors_headers(response), 404

        # 构建封面 URL 和分享链接
        base_url = get_image_domain(request)
        if result.get('cover_image'):
            result['cover_url'] = f"{base_url}/image/{result['cover_image']}"
        else:
            result['cover_url'] = None

        if result.get('share_enabled') and result.get('share_token'):
            result['share_url'] = f"{get_domain(request)}/g/{result['share_token']}"
        else:
            result['share_url'] = None

        result['has_password'] = bool(result.get('password_hash'))
        result.pop('password_hash', None)

        response = jsonify({'success': True, 'data': {'gallery': result}})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"更新画集访问控制失败 (id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '更新失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/access-tokens', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_token_access(gallery_id):
    """管理画集 Token 授权"""
    try:
        if request.method == 'GET':
            items = list_gallery_token_access(gallery_id, is_admin=True)
            if items is None:
                response = jsonify({'success': False, 'error': '画集不存在'})
                return _set_admin_cors_headers(response), 404
            response = jsonify({'success': True, 'data': {'items': items}})
            return _set_admin_cors_headers(response)

        data = request.get_json()
        token = (data or {}).get('token', '').strip()
        if not token:
            response = jsonify({'success': False, 'error': '缺少 token 参数'})
            return _set_admin_cors_headers(response), 400

        if request.method == 'POST':
            success = grant_gallery_token_access(gallery_id, token, is_admin=True)
            if not success:
                response = jsonify({'success': False, 'error': '授权失败，画集不存在或 Token 无效/已过期'})
                return _set_admin_cors_headers(response), 400
            response = jsonify({'success': True, 'message': 'Token 已授权'})
            return _set_admin_cors_headers(response)

        if request.method == 'DELETE':
            success = revoke_gallery_token_access(gallery_id, token, is_admin=True)
            if not success:
                response = jsonify({'success': False, 'error': '撤销失败，授权记录不存在'})
                return _set_admin_cors_headers(response), 404
            response = jsonify({'success': True, 'message': 'Token 授权已撤销'})
            return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"Token 授权管理失败 (gallery_id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/images', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_images(gallery_id):
    """管理画集图片（GET 列表，POST 添加，DELETE 移除）"""
    try:
        if request.method == 'GET':
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            page = max(1, page)
            per_page = max(1, min(200, per_page))
            result = admin_get_gallery_images(gallery_id, page=page, limit=per_page)
            # 构建图片 URL
            base_url = get_image_domain(request)
            for item in result.get('items', []):
                item['url'] = f"{base_url}/image/{item['encrypted_id']}"
            response = jsonify({
                'success': True,
                'data': {
                    'items': result['items'],
                    'total': result['total'],
                    'page': result['page'],
                    'per_page': result['limit'],
                    'has_more': result['page'] * result['limit'] < result['total'],
                }
            })
            return _set_admin_cors_headers(response)

        data = request.get_json(silent=True) or {}
        encrypted_ids = data.get('encrypted_ids', [])
        if not isinstance(encrypted_ids, list) or not encrypted_ids:
            response = jsonify({'success': False, 'error': '请提供图片ID列表'})
            return _set_admin_cors_headers(response), 400
        encrypted_ids = list(dict.fromkeys([str(e).strip() for e in encrypted_ids if str(e).strip()]))[:500]
        if not encrypted_ids:
            response = jsonify({'success': False, 'error': '请提供图片ID列表'})
            return _set_admin_cors_headers(response), 400

        if request.method == 'POST':
            result = admin_add_images_to_gallery(gallery_id, encrypted_ids)
            response = jsonify({'success': True, 'data': result})
            return _set_admin_cors_headers(response)

        # DELETE
        removed = admin_remove_images_from_gallery(gallery_id, encrypted_ids)
        response = jsonify({'success': True, 'data': {'removed': removed}})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"画集图片管理失败 (gallery_id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/galleries/<int:gallery_id>/cover', methods=['PUT', 'DELETE', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_cover(gallery_id):
    """设置/清除画集封面"""
    try:
        if request.method == 'PUT':
            data = request.get_json(silent=True) or {}
            encrypted_id = (data.get('encrypted_id') or '').strip()
            if not encrypted_id:
                response = jsonify({'success': False, 'error': '未指定封面图片'})
                return _set_admin_cors_headers(response), 400
            gallery = admin_set_gallery_cover(gallery_id, encrypted_id)
            if not gallery:
                response = jsonify({'success': False, 'error': '画集不存在或图片不在画集中'})
                return _set_admin_cors_headers(response), 404
        else:
            # DELETE - 清除封面
            gallery = admin_set_gallery_cover(gallery_id, None)
            if not gallery:
                response = jsonify({'success': False, 'error': '画集不存在'})
                return _set_admin_cors_headers(response), 404

        # 构建封面 URL
        base_url = get_image_domain(request)
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
        else:
            gallery['cover_url'] = None

        gallery['has_password'] = bool(gallery.get('password_hash'))
        gallery.pop('password_hash', None)

        response = jsonify({'success': True, 'data': {'gallery': gallery}})
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"画集封面管理失败 (gallery_id={gallery_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/images', methods=['GET', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_images_list():
    """获取全部图片列表（用于添加图片到画集）"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 60, type=int)
        search = request.args.get('search', '').strip()

        page = max(1, page)
        limit = max(1, min(200, limit))
        offset = (page - 1) * limit

        with get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            where_params = []
            if search:
                where_clauses.append('(original_filename LIKE ? OR username LIKE ?)')
                pattern = f'%{search}%'
                where_params.extend([pattern, pattern])

            where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

            cursor.execute(f'SELECT COUNT(*) FROM file_storage{where_sql}', where_params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f'SELECT encrypted_id, original_filename, file_size, mime_type, cdn_cached '
                f'FROM file_storage{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?',
                where_params + [limit, offset]
            )
            rows = [dict(r) for r in cursor.fetchall()]

        base_url = get_image_domain(request)
        for img in rows:
            img['url'] = f"{base_url}/image/{img['encrypted_id']}"
            img['cdn_url'] = None

        response = jsonify({
            'success': True,
            'data': {
                'images': rows,
                'total': total,
                'page': page,
                'limit': limit
            }
        })
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"获取图片列表失败: {e}")
        response = jsonify({'success': False, 'error': '获取图片列表失败'})
        return _set_admin_cors_headers(response), 500
