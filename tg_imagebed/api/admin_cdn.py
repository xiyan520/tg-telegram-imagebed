#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - CDN 管理
"""
import time

from flask import request, jsonify, Response

from . import admin_bp
from .admin_helpers import _get_cdn_domain, _admin_json, _admin_options
from ..config import logger
from ..utils import add_cache_headers
from ..database import (
    get_system_setting, update_cdn_cache_status, get_uncached_files,
    get_cdn_dashboard_stats,
)
from ..services.cdn_service import cloudflare_cdn, add_to_cdn_monitor, get_monitor_queue_size
from .. import admin_module


@admin_bp.route('/api/admin/cdn/purge', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def purge_cdn_cache():
    """清除 CDN 缓存（管理员）"""
    data = request.get_json()
    urls = data.get('urls', [])

    if not urls:
        response = jsonify({'error': 'No URLs provided'})
        return add_cache_headers(response, 'no-cache'), 400

    cdn_urls = []
    cdn_domain = _get_cdn_domain()
    for url in urls:
        if '/image/' in url:
            encrypted_id = url.split('/image/')[-1]
            if cdn_domain:
                cdn_urls.append(f"https://{cdn_domain}/image/{encrypted_id}")

    if cdn_urls and cloudflare_cdn.purge_cache(cdn_urls):
        response = jsonify({
            'success': True,
            'message': f'已清除 {len(cdn_urls)} 个URL的缓存'
        })
    else:
        response = jsonify({
            'success': False,
            'error': '缓存清除失败'
        })

    return add_cache_headers(response, 'no-cache')


@admin_bp.route('/api/admin/cdn/probe', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_cdn_probe():
    """实时探测 CDN 状态（管理员）"""
    if request.method == 'OPTIONS':
        return add_cache_headers(Response(), 'no-cache')

    data = request.get_json() or {}
    encrypted_ids = data.get('encrypted_ids') or []
    max_items = int(data.get('max_items') or 200)

    if not encrypted_ids:
        return add_cache_headers(jsonify({'success': False, 'error': 'No encrypted_ids provided'}), 'no-cache'), 400

    if not _get_cdn_domain():
        return add_cache_headers(jsonify({'success': False, 'error': 'CDN domain not configured'}), 'no-cache'), 400

    encrypted_ids = encrypted_ids[:max_items]
    results = []
    cached_count = 0

    for encrypted_id in encrypted_ids:
        probe = cloudflare_cdn.probe_encrypted_id(encrypted_id)
        if probe.cached:
            cached_count += 1
            update_cdn_cache_status(encrypted_id, True)
        results.append({
            'encrypted_id': encrypted_id,
            'url': probe.url,
            'status_code': probe.status_code,
            'cf_cache_status': probe.cf_cache_status,
            'age': probe.age,
            'cf_ray': probe.cf_ray,
            'cached': probe.cached,
            'error': probe.error,
        })

    return add_cache_headers(jsonify({
        'success': True,
        'data': results,
        'summary': {
            'requested': len(encrypted_ids),
            'cached': cached_count,
            'monitor_queue_size': get_monitor_queue_size(),
        }
    }), 'no-cache')


@admin_bp.route('/api/admin/cdn/warm', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_cdn_warm():
    """手动触发 CDN 预热（管理员）"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    if not _get_cdn_domain():
        return add_cache_headers(jsonify({'success': False, 'error': 'CDN domain not configured'}), 'no-cache'), 400

    data = request.get_json() or {}
    encrypted_ids = data.get('encrypted_ids') or []
    all_uncached = bool(data.get('all_uncached'))
    limit = int(data.get('limit') or 200)
    since_seconds = int(data.get('since_seconds') or 86400)

    if all_uncached:
        since_ts = int(time.time()) - max(0, since_seconds)
        rows = get_uncached_files(since_ts, limit=limit)
        encrypted_ids = [r['encrypted_id'] for r in rows]
    else:
        encrypted_ids = encrypted_ids[:limit]

    if not encrypted_ids:
        return add_cache_headers(jsonify({'success': False, 'error': 'No targets to warm'}), 'no-cache'), 400

    warmed = 0
    probed_cached = 0
    results = []

    for encrypted_id in encrypted_ids:
        ok = cloudflare_cdn.warm_cache_sync(encrypted_id)
        probe = cloudflare_cdn.probe_encrypted_id(encrypted_id)
        if ok:
            warmed += 1
        if probe.cached:
            probed_cached += 1
            update_cdn_cache_status(encrypted_id, True)
        else:
            add_to_cdn_monitor(encrypted_id, delay_seconds=0)

        results.append({
            'encrypted_id': encrypted_id,
            'warmed_request_ok': ok,
            'status_code': probe.status_code,
            'cf_cache_status': probe.cf_cache_status,
            'age': probe.age,
            'cf_ray': probe.cf_ray,
            'cached': probe.cached,
            'error': probe.error,
        })

    return add_cache_headers(jsonify({
        'success': True,
        'summary': {
            'requested': len(encrypted_ids),
            'warmed_request_ok': warmed,
            'cached_after_probe': probed_cached,
            'monitor_queue_size': get_monitor_queue_size(),
        },
        'data': results,
    }), 'no-cache')


@admin_bp.route('/api/admin/cdn/stats', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_cdn_stats():
    """CDN 仪表盘统计（管理员）"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    window_hours = request.args.get('window_hours')
    window_hours = int(window_hours) if window_hours is not None else None

    data = get_cdn_dashboard_stats(window_hours=window_hours)
    data['monitor'] = {'queue_size': get_monitor_queue_size()}
    data['cloudflare'] = {'cdn_domain': _get_cdn_domain() or None}

    return add_cache_headers(jsonify({'success': True, 'data': data}), 'no-cache')


@admin_bp.route('/api/admin/clear_cache', methods=['POST', 'OPTIONS'])
@admin_bp.route('/api/admin/clear-cache', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def clear_cache():
    """清理 CDN 缓存（仅限管理员）"""
    from .. import config as app_config

    # 更新静态版本号（强制客户端刷新静态资源）
    new_version = str(int(time.time()))
    app_config.STATIC_VERSION = new_version

    cloudflare_success = False
    cdn_domain = _get_cdn_domain()
    cloudflare_cdn._refresh_config()
    if cdn_domain and cloudflare_cdn.zone_id:
        if cloudflare_cdn.purge_all():
            message = '缓存已清理，Cloudflare缓存已清除'
            cloudflare_success = True
        else:
            message = '缓存已清理，但Cloudflare缓存清除失败'
    else:
        message = '缓存已清理'

    return jsonify({
        'success': True,
        'message': message,
        'static_version': new_version
    })
