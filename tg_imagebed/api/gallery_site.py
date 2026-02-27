#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画集站点公开 API - 画集域名专用路由

提供画集域名下的公开浏览接口，无需认证。
管理端点需要通过 SSO token 或 session 认证。
"""
from functools import wraps
from urllib.parse import quote, urlparse
from flask import request, jsonify, make_response, session, redirect

from . import gallery_site_bp
from ..config import logger
from ..utils import add_cache_headers, get_image_domain, get_domain
from ..database import (
    get_system_setting, get_system_setting_int,
    update_system_setting,
    is_gallery_domain,
    get_gallery_home_config,
    update_gallery_home_config,
    list_gallery_home_sections,
    update_gallery_home_section,
    replace_gallery_home_section_items,
    get_gallery_home_public_payload,
)
from ..database.connection import get_connection
from ..database.domains import get_active_gallery_domains, build_domain_url
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
    SELECT g.id, g.name, g.description, g.card_subtitle, g.editor_pick_weight,
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

        # 始终返回画集站点信息，供 /gallery-site/ 页面使用（不依赖域名模式）
        site_name = get_system_setting('gallery_site_name') or '画集'
        site_description = get_system_setting('gallery_site_description') or '精选图片画集'

        mode = 'gallery' if (gallery_enabled and is_gallery_domain(host)) else 'default'

        response = jsonify({
            'success': True,
            'data': {
                'mode': mode,
                'site_name': site_name,
                'site_description': site_description,
            }
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
                SELECT g.id, g.name, g.description, g.share_token,
                    g.card_subtitle, g.seo_title, g.seo_description, g.seo_keywords,
                    g.og_image_encrypted_id, g.editor_pick_weight,
                    g.created_at, g.updated_at,
                    g.layout_mode, g.theme_color, g.show_image_info,
                    g.allow_download, g.sort_order, g.nsfw_warning, g.custom_header_text,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count
                FROM galleries g
                WHERE g.id = ? AND g.share_enabled = 1 AND g.access_mode = 'public'
            ''', (gallery_id,))
            gallery_row = cursor.fetchone()
            if not gallery_row:
                response = jsonify({'success': False, 'error': '画集不存在或不可访问'})
                return _set_public_cors_headers(response), 404

            gallery = dict(gallery_row)

            # 构建分享链接
            share_token = gallery.pop('share_token', None)
            if share_token:
                gallery['share_url'] = f"{_get_gallery_site_url(request)}/g/{share_token}"
            else:
                gallery['share_url'] = None

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


@gallery_site_bp.route('/api/gallery-site/home-config', methods=['GET', 'OPTIONS'])
def gallery_site_home_config():
    """获取首页编排配置与展示数据（公开）"""
    if request.method == 'OPTIONS':
        return _handle_options()

    try:
        payload = get_gallery_home_public_payload()

        hero = payload.get('hero')
        if isinstance(hero, dict):
            _build_cover_urls([hero])

        for section in payload.get('sections', []):
            _build_cover_urls(section.get('items', []))

        _build_cover_urls(payload.get('recent_items', []))

        response = jsonify({'success': True, 'data': payload})
        return _set_public_cors_headers(add_cache_headers(response, 'public', 60))
    except Exception as e:
        logger.error(f"获取首页编排配置失败: {e}")
        response = jsonify({'success': False, 'error': '获取首页编排失败'})
        return _set_public_cors_headers(response), 500


# ===================== SSO 重定向端点 =====================

def _get_main_site_url(request):
    """获取主站 URL，用于 SSO 重定向

    优先级：default域名 > gallery_sso_main_url（校验后）> 非gallery活跃域名 > get_domain fallback
    """
    def _host_aliases(host: str) -> set[str]:
        h = (host or '').strip().lower()
        if not h:
            return set()
        aliases = {h}
        if h == 'localhost':
            aliases.update({'127.0.0.1', '::1'})
        elif h in {'127.0.0.1', '::1'}:
            aliases.update({'localhost', '127.0.0.1', '::1'})
        return aliases

    def _url_host(url: str) -> str:
        try:
            return (urlparse(url).hostname or '').lower()
        except Exception:
            return ''

    gallery_hosts: set[str] = set()
    try:
        for d in get_active_gallery_domains():
            gallery_hosts.update(_host_aliases(d.get('domain', '')))
    except Exception:
        pass

    # 1. 优先使用 domain_type='default' 的活跃域名（主站域名）
    # 注意：custom_domains.is_default 可能被 image 域名占用，不能直接等价为主站域名
    default_url = ''
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT domain, use_https, port
                FROM custom_domains
                WHERE domain_type = 'default' AND is_active = 1
                ORDER BY is_default DESC, sort_order ASC, id ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                default_url = build_domain_url(
                    row['domain'],
                    row['port'],
                    bool(row['use_https'])
                )
    except Exception:
        pass

    # 2. 使用管理员配置 gallery 域名时自动保存的主站 URL（需校验）
    saved_url = get_system_setting('gallery_sso_main_url')
    if saved_url:
        saved_host = _url_host(saved_url)
        saved_aliases = _host_aliases(saved_host)
        # 防止主站 URL 被错误记录成 gallery 域名（会导致回调无主站会话）
        if saved_aliases and saved_aliases.isdisjoint(gallery_hosts):
            if default_url:
                # default 域名存在时，以 default 为准（避免 http/https 或端口历史漂移）
                return default_url
            return saved_url

    if default_url:
        return default_url

    # 3. 尝试获取非 gallery 类型的活跃域名
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT domain, use_https, port FROM custom_domains
                WHERE domain_type != 'gallery' AND is_active = 1
                ORDER BY is_default DESC, sort_order ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return build_domain_url(
                    row['domain'],
                    row['port'],
                    bool(row['use_https'])
                )
    except Exception:
        pass

    # 4. 最终 fallback
    return get_domain(request)


def _get_gallery_site_url(request):
    """获取画集站点 URL，用于构建画集分享链接

    优先级：画集域名（get_active_gallery_domains 第一个） > 主站 URL（向后兼容）
    """
    # 1. 优先使用画集域名
    gallery_domains = get_active_gallery_domains()
    if gallery_domains:
        first = gallery_domains[0]
        return build_domain_url(
            first['domain'],
            first.get('port'),
            bool(first.get('use_https', 1))
        )

    # 2. 没有画集域名时，fallback 到主站 URL（保持向后兼容）
    return _get_main_site_url(request)


@gallery_site_bp.route('/api/gallery-site/sso-redirect', methods=['GET'])
def gallery_sso_redirect():
    """SSO 重定向入口：画集站点发起，重定向到主站 SSO 回调"""
    return_url = request.args.get('return_url', '/gallery-site/admin')

    # return_url 仅接受相对路径；兼容历史前端传入的“同源绝对 URL”
    if not return_url.startswith('/'):
        try:
            parsed = urlparse(return_url)
            # 允许 http(s) 且 host 与当前请求 host 一致（忽略端口）
            req_host = (
                request.headers.get('X-Forwarded-Host')
                or request.headers.get('Host')
                or request.host
                or ''
            ).split(':')[0].lower()
            parsed_host = (parsed.hostname or '').lower()
            if parsed.scheme in ('http', 'https') and parsed_host and parsed_host == req_host:
                return_url = parsed.path or '/gallery-site/admin'
                if parsed.query:
                    return_url = f"{return_url}?{parsed.query}"
            else:
                return_url = '/gallery-site/admin'
        except Exception:
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
    """设置管理端点的 CORS 头（仅允许已配置的 Origin，支持 credentials）"""
    origin = request.headers.get('Origin')
    if origin:
        # 从配置中获取允许的 Origin 列表（与主站 CORS 策略保持一致）
        from ..config import ALLOWED_ORIGINS
        allowed = [o.strip() for o in ALLOWED_ORIGINS.split(',') if o.strip()]
        # ALLOWED_ORIGINS='*' 时反射请求 Origin（开发模式）；否则严格白名单
        if ALLOWED_ORIGINS == '*' or origin in allowed:
            response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


def _handle_admin_options():
    """统一处理管理端点 OPTIONS 预检请求"""
    response = make_response()
    origin = request.headers.get('Origin')
    if origin:
        from ..config import ALLOWED_ORIGINS
        allowed = [o.strip() for o in ALLOWED_ORIGINS.split(',') if o.strip()]
        if ALLOWED_ORIGINS == '*' or origin in allowed:
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


@gallery_site_bp.route('/api/gallery-site/admin/home-config', methods=['GET', 'PUT', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_home_config():
    """获取/更新首页全局编排配置"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    try:
        if request.method == 'GET':
            data = get_gallery_home_config()
            response = jsonify({'success': True, 'data': data})
            return _set_admin_cors_headers(response)

        payload = request.get_json(silent=True) or {}
        updated = update_gallery_home_config(payload)
        response = jsonify({'success': True, 'data': updated})
        return _set_admin_cors_headers(response)
    except Exception as e:
        logger.error(f"首页全局编排配置操作失败: {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/home-sections', methods=['GET', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_home_sections():
    """获取首页分区配置（含手动编排项）"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    try:
        sections = list_gallery_home_sections(include_items=True)
        for section in sections:
            _build_cover_urls(section.get('items', []))
        response = jsonify({'success': True, 'data': {'sections': sections}})
        return _set_admin_cors_headers(response)
    except Exception as e:
        logger.error(f"获取首页分区配置失败: {e}")
        response = jsonify({'success': False, 'error': '获取分区配置失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/home-sections/<string:section_key>', methods=['PATCH', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_home_section_update(section_key: str):
    """更新首页单个分区配置"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    try:
        payload = request.get_json(silent=True) or {}
        section = update_gallery_home_section(section_key, payload)
        if not section:
            response = jsonify({'success': False, 'error': '分区不存在'})
            return _set_admin_cors_headers(response), 404
        response = jsonify({'success': True, 'data': {'section': section}})
        return _set_admin_cors_headers(response)
    except Exception as e:
        logger.error(f"更新首页分区配置失败: key={section_key}, err={e}")
        response = jsonify({'success': False, 'error': '更新分区失败'})
        return _set_admin_cors_headers(response), 500


@gallery_site_bp.route('/api/gallery-site/admin/home-sections/<string:section_key>/items', methods=['PUT', 'OPTIONS'])
@gallery_admin_required
def gallery_admin_home_section_items_replace(section_key: str):
    """替换首页分区手动编排项"""
    if request.method == 'OPTIONS':
        return _handle_admin_options()

    try:
        payload = request.get_json(silent=True) or {}
        gallery_ids = payload.get('gallery_ids') or []
        if not isinstance(gallery_ids, list):
            response = jsonify({'success': False, 'error': 'gallery_ids 必须是数组'})
            return _set_admin_cors_headers(response), 400
        result = replace_gallery_home_section_items(section_key, gallery_ids)
        if not result.get('section'):
            response = jsonify({'success': False, 'error': '分区不存在'})
            return _set_admin_cors_headers(response), 404
        response = jsonify({'success': True, 'data': result})
        return _set_admin_cors_headers(response)
    except Exception as e:
        logger.error(f"替换首页分区编排项失败: key={section_key}, err={e}")
        response = jsonify({'success': False, 'error': '更新分区编排失败'})
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
                SELECT g.id, g.name, g.description, g.card_subtitle,
                    g.share_enabled, g.access_mode, g.editor_pick_weight,
                    COALESCE(g.homepage_expose_enabled, 1) AS homepage_expose_enabled,
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
    """更新画集展示配置、分享状态与访问模式"""
    try:
        data = request.get_json(silent=True) or {}
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
            if mode != 'password':
                updates.append('password_hash = NULL')

        if 'name' in data:
            name = str(data.get('name') or '').strip()
            if not name:
                response = jsonify({'success': False, 'error': '画集名称不能为空'})
                return _set_admin_cors_headers(response), 400
            if len(name) > 100:
                response = jsonify({'success': False, 'error': '画集名称不能超过100字符'})
                return _set_admin_cors_headers(response), 400
            updates.append('name = ?')
            params.append(name)

        if 'description' in data:
            updates.append('description = ?')
            params.append(str(data.get('description') or '').strip()[:500] or None)

        if 'layout_mode' in data:
            layout_mode = str(data.get('layout_mode') or '').strip()
            if layout_mode in ('masonry', 'grid', 'justified'):
                updates.append('layout_mode = ?')
                params.append(layout_mode)

        if 'theme_color' in data:
            updates.append('theme_color = ?')
            params.append(str(data.get('theme_color') or '').strip()[:20])

        if 'show_image_info' in data:
            updates.append('show_image_info = ?')
            params.append(1 if data.get('show_image_info') else 0)

        if 'allow_download' in data:
            updates.append('allow_download = ?')
            params.append(1 if data.get('allow_download') else 0)

        if 'sort_order' in data:
            sort_order = str(data.get('sort_order') or '').strip()
            if sort_order in ('newest', 'oldest', 'filename'):
                updates.append('sort_order = ?')
                params.append(sort_order)

        if 'nsfw_warning' in data:
            updates.append('nsfw_warning = ?')
            params.append(1 if data.get('nsfw_warning') else 0)

        if 'custom_header_text' in data:
            updates.append('custom_header_text = ?')
            params.append(str(data.get('custom_header_text') or '').strip()[:200])

        if 'editor_pick_weight' in data:
            try:
                value = int(data.get('editor_pick_weight'))
            except (TypeError, ValueError):
                value = 0
            updates.append('editor_pick_weight = ?')
            params.append(max(0, min(1000, value)))

        if 'homepage_expose_enabled' in data:
            updates.append('homepage_expose_enabled = ?')
            params.append(1 if data.get('homepage_expose_enabled') else 0)

        if 'card_subtitle' in data:
            updates.append('card_subtitle = ?')
            params.append(str(data.get('card_subtitle') or '').strip()[:120])

        if 'seo_title' in data:
            updates.append('seo_title = ?')
            params.append(str(data.get('seo_title') or '').strip()[:120])

        if 'seo_description' in data:
            updates.append('seo_description = ?')
            params.append(str(data.get('seo_description') or '').strip()[:300])

        if 'seo_keywords' in data:
            updates.append('seo_keywords = ?')
            params.append(str(data.get('seo_keywords') or '').strip()[:300])

        if 'og_image_encrypted_id' in data:
            og_image = str(data.get('og_image_encrypted_id') or '').strip()
            updates.append('og_image_encrypted_id = ?')
            params.append(og_image or None)

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

        gallery = admin_get_gallery(gallery_id)
        if not gallery:
            response = jsonify({'success': False, 'error': '画集不存在'})
            return _set_admin_cors_headers(response), 404

        base_url = get_image_domain(request)
        if gallery.get('cover_image'):
            gallery['cover_url'] = f"{base_url}/image/{gallery['cover_image']}"
        else:
            gallery['cover_url'] = None

        if gallery.get('share_enabled') and gallery.get('share_token'):
            gallery['share_url'] = f"{_get_gallery_site_url(request)}/g/{gallery['share_token']}"
        else:
            gallery['share_url'] = None

        gallery['has_password'] = bool(gallery.get('password_hash'))
        gallery.pop('password_hash', None)

        response = jsonify({'success': True, 'data': {'gallery': gallery}})
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
            gallery['share_url'] = f"{_get_gallery_site_url(request)}/g/{gallery['share_token']}"
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
            result['share_url'] = f"{_get_gallery_site_url(request)}/g/{result['share_token']}"
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
            result['share_url'] = f"{_get_gallery_site_url(request)}/g/{result['share_token']}"
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
