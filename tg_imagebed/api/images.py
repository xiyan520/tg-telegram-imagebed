#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片路由模块 - 图片访问、统计、信息 API
"""
import os
import time
from pathlib import Path
from datetime import datetime
from flask import request, jsonify, Response, send_file, redirect, make_response

from . import images_bp
from ..config import (
    CDN_ENABLED, CLOUDFLARE_CDN_DOMAIN,
    CDN_REDIRECT_ENABLED, CDN_REDIRECT_MAX_COUNT, CDN_REDIRECT_CACHE_TIME, CDN_REDIRECT_DELAY,
    CDN_MONITOR_ENABLED, ENABLE_GROUP_UPLOAD, GROUP_UPLOAD_ADMIN_ONLY, GROUP_UPLOAD_REPLY,
    STATIC_FOLDER, STATIC_VERSION, START_TIME, PORT,
    logger
)
from ..database import (
    get_file_info, update_access_count, update_cdn_cache_status,
    get_stats, get_recent_uploads
)
from ..utils import (
    add_cache_headers, format_size, get_domain, get_static_file_version, LOCAL_IP
)
from ..services.cdn_service import cloudflare_cdn, get_monitor_queue_size
from ..database import update_file_path_in_db
from ..storage.router import get_storage_router


@images_bp.route('/')
def index():
    """返回主页"""
    index_path = os.path.join(STATIC_FOLDER, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return jsonify({
            'error': '前端文件未找到',
            'message': '请先运行 cd frontend && npm run generate 构建前端',
            'api_base': get_domain(request)
        }), 404


@images_bp.route('/image/<encrypted_id>', methods=['GET', 'HEAD', 'OPTIONS'])
def serve_image(encrypted_id):
    """代理提供 Telegram 图片服务"""
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type, Cache-Control'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response

    # 获取文件信息
    file_info = get_file_info(encrypted_id)

    if not file_info:
        logger.warning(f"图片未找到: {encrypted_id}")
        response = Response(b'Image not found', status=404, mimetype='text/plain')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    # 检查是否是 CDN 回源请求
    cf_headers = {k: v for k, v in request.headers.items() if k.startswith('CF-')}
    is_cdn_request = bool(cf_headers.get('CF-Connecting-IP'))

    # 检查是否来自 CDN 域名
    host = request.headers.get('Host', '')
    is_from_cdn_domain = CLOUDFLARE_CDN_DOMAIN and host == CLOUDFLARE_CDN_DOMAIN

    # 检查 Referer
    referer = request.headers.get('Referer', '')
    is_referer_from_cdn = CLOUDFLARE_CDN_DOMAIN and CLOUDFLARE_CDN_DOMAIN in referer

    # 检查重定向计数
    redirect_count = request.headers.get('X-Redirect-Count', '0')
    try:
        redirect_count = int(redirect_count)
    except ValueError:
        redirect_count = 0

    # 检查是否是新上传的文件
    is_new_file = False
    if file_info.get('upload_time'):
        time_since_upload = time.time() - file_info['upload_time']
        is_new_file = time_since_upload < CDN_REDIRECT_DELAY

    # CDN 重定向逻辑
    if (CDN_REDIRECT_ENABLED and
        not is_cdn_request and
        not is_from_cdn_domain and
        not is_referer_from_cdn and
        not is_new_file and
        redirect_count < CDN_REDIRECT_MAX_COUNT and
        CDN_ENABLED and
        CLOUDFLARE_CDN_DOMAIN):

        if file_info.get('cdn_cached'):
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"
            request_url = request.url
            if cdn_url not in request_url:
                logger.info(f"图片已缓存，重定向到CDN: {encrypted_id} -> {cdn_url}")
                update_access_count(encrypted_id)
                response = redirect(cdn_url, code=302)
                response.headers['Cache-Control'] = f'public, max-age={CDN_REDIRECT_CACHE_TIME}'
                response.headers['X-CDN-Redirect'] = 'true'
                response.headers['X-Redirect-Count'] = str(redirect_count + 1)
                return response
        else:
            if cloudflare_cdn.check_cdn_status(encrypted_id):
                update_cdn_cache_status(encrypted_id, True)
                logger.info(f"更新CDN缓存状态并直接提供图片: {encrypted_id}")

    # 更新访问计数
    update_access_count(encrypted_id)

    # 生成 ETag
    etag = file_info.get('etag') or f'W/"{encrypted_id}-{file_info.get("file_size", 0)}"'

    # 检查条件请求
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match == etag:
        response = Response(status=304)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'public, max-age=31536000, s-maxage=2592000, immutable'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    # 从存储后端下载图片
    try:
        access_type = 'cdn_pull' if is_cdn_request else 'direct_access'
        router = get_storage_router()
        backend = router.get_backend_for_record(file_info)
        range_header = request.headers.get('Range')

        dl = backend.download(file_info=file_info, range_header=range_header)

        # 如果后端返回了更新的字段（如 Telegram 的 file_path 刷新）
        if dl.updated_fields and dl.updated_fields.get('file_path'):
            update_file_path_in_db(encrypted_id, dl.updated_fields['file_path'])
            file_info['file_path'] = dl.updated_fields['file_path']

        if dl.status_code not in (200, 206):
            logger.warning(f"后端文件获取失败: backend={backend.name}, id={encrypted_id}, status={dl.status_code}")
            status = dl.status_code or 502
            body = b'Image not found' if status == 404 else b'Error loading image'
            response = Response(body, status=status, mimetype='text/plain')
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache')

        logger.info(f"从后端获取图片: {encrypted_id} (backend={backend.name}, 访问类型: {access_type})")

        path_for_ext = file_info.get('file_path') or file_info.get('original_filename') or ''
        file_ext = Path(path_for_ext).suffix or '.jpg'
        filename = f"image_{encrypted_id[:12]}{file_ext}"

        resp_headers = dict(dl.headers or {})
        resp_headers.setdefault('Content-Disposition', f'inline; filename="{filename}"')
        resp_headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp_headers.setdefault('Accept-Ranges', 'bytes')
        resp_headers['ETag'] = etag
        resp_headers['X-Access-Type'] = access_type
        resp_headers['X-Storage-Backend'] = backend.name
        resp_headers['Access-Control-Allow-Origin'] = '*'
        resp_headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        resp_headers['Access-Control-Allow-Headers'] = 'Range, Cache-Control'
        resp_headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges, ETag, X-Storage-Backend'

        resp = Response(
            dl.body,
            status=dl.status_code,
            mimetype=dl.content_type or (file_info.get('mime_type') or 'application/octet-stream'),
            headers=resp_headers
        )

        if CDN_ENABLED:
            if is_new_file:
                resp.headers['Cache-Control'] = 'public, max-age=300, s-maxage=300'
            else:
                resp.headers['Cache-Control'] = 'public, max-age=31536000, s-maxage=2592000, immutable'
            resp.headers['Vary'] = 'Accept-Encoding'
            resp.headers['CF-Cache-Tag'] = f'image-{encrypted_id[:8]},imagebed,static'
        else:
            resp.headers['Cache-Control'] = 'public, max-age=3600'

        return resp

    except Exception as e:
        logger.error(f"代理图片失败: {e}")
        response = Response(b'Error loading image', status=500, mimetype='text/plain')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')


@images_bp.route('/api/stats')
def get_stats_api():
    """获取统计信息 API"""
    stats = get_stats()

    uptime_seconds = int(time.time() - START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60

    if days > 0:
        uptime_str = f"{days}天"
    elif hours > 0:
        uptime_str = f"{hours}小时"
    else:
        uptime_str = f"{minutes}分钟"

    response = jsonify({
        'success': True,
        'data': {
            'totalFiles': str(stats['total_files']),
            'totalSize': format_size(stats['total_size']),
            'todayUploads': str(stats['today_uploads']),
            'uptime': uptime_str
        }
    })

    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, 'no-cache')


@images_bp.route('/api/recent')
def get_recent_api():
    """获取最近上传的文件"""
    limit = request.args.get('limit', 12, type=int)
    page = request.args.get('page', 1, type=int)

    try:
        recent_files = get_recent_uploads(limit, page)

        for file in recent_files:
            if file.get('created_at'):
                try:
                    dt = datetime.fromisoformat(file['created_at'].replace('Z', '+00:00'))
                    file['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

            base_url = get_domain(request)
            file['image_url'] = f"{base_url}/image/{file['encrypted_id']}"
            file['cdn_url'] = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{file['encrypted_id']}" if CLOUDFLARE_CDN_DOMAIN else None
            file['cdn_cached'] = file.get('cdn_cached', 0)
            file['is_group_upload'] = file.get('is_group_upload', 0)

        response = jsonify({
            'success': True,
            'files': recent_files,
            'page': page,
            'limit': limit,
            'has_more': len(recent_files) == limit
        })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
        response = jsonify({
            'success': False,
            'error': 'Failed to load gallery',
            'files': [],
            'page': page,
            'limit': limit,
            'has_more': False
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@images_bp.route('/api/info')
def get_info():
    """获取服务器信息"""
    stats = get_stats()

    response = jsonify({
        'server_ip': LOCAL_IP,
        'domain': get_domain(request),
        'cdn_domain': f"https://{CLOUDFLARE_CDN_DOMAIN}" if CLOUDFLARE_CDN_DOMAIN else None,
        'port': PORT,
        'storage_type': 'telegram_cloud + sqlite',
        'total_files': stats['total_files'],
        'group_uploads': stats['group_uploads'],
        'cdn_enabled': CDN_ENABLED,
        'cloudflare_cdn': bool(CLOUDFLARE_CDN_DOMAIN),
        'cdn_monitor_enabled': CDN_MONITOR_ENABLED,
        'cdn_monitor_queue': get_monitor_queue_size(),
        'cdn_redirect_enabled': CDN_REDIRECT_ENABLED,
        'group_upload_enabled': ENABLE_GROUP_UPLOAD,
        'group_upload_admin_only': GROUP_UPLOAD_ADMIN_ONLY,
        'group_upload_reply': GROUP_UPLOAD_REPLY,
        'max_file_size': 20 * 1024 * 1024,
        'static_version': STATIC_VERSION,
    })

    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, 'private', 60)


@images_bp.route('/api/health')
def health_check():
    """健康检查端点"""
    response = jsonify({
        'status': 'healthy',
        'timestamp': int(time.time()),
        'base_url': get_domain(request),
        'cdn_enabled': CDN_ENABLED,
        'cloudflare_cdn': bool(CLOUDFLARE_CDN_DOMAIN),
        'cdn_redirect_enabled': CDN_REDIRECT_ENABLED,
        'group_upload_enabled': ENABLE_GROUP_UPLOAD,
        'version': STATIC_VERSION
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, 'no-cache')


@images_bp.route('/robots.txt')
def robots():
    """提供 robots.txt"""
    robots_content = f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin

Sitemap: {get_domain(request)}/sitemap.xml
"""
    response = Response(robots_content, mimetype='text/plain')
    return add_cache_headers(response, 'public', 86400)


@images_bp.route('/manifest.json')
def manifest():
    """提供 PWA manifest"""
    manifest_data = {
        "name": "Telegram 云图床",
        "short_name": "云图床",
        "description": "基于Telegram云存储的免费图床服务",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#6366f1",
    }
    response = jsonify(manifest_data)
    return add_cache_headers(response, 'public', 86400)


@images_bp.route('/<path:path>')
def catch_all(path):
    """捕获所有路由，SPA 回退"""
    if path.startswith('api/') or path.startswith('image/') or path.startswith('upload'):
        return jsonify({'error': 'Not found'}), 404

    file_path = os.path.join(STATIC_FOLDER, path)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)

    if os.path.exists(file_path) and os.path.isdir(file_path):
        index_in_dir = os.path.join(file_path, 'index.html')
        if os.path.exists(index_in_dir):
            return send_file(index_in_dir)

    fallback_path = os.path.join(STATIC_FOLDER, '200.html')
    if os.path.exists(fallback_path):
        return send_file(fallback_path)

    index_path = os.path.join(STATIC_FOLDER, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)

    return jsonify({'error': 'Not found'}), 404
