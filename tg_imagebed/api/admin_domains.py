#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名管理 API - 管理员域名 CRUD + 公开域名列表
"""
from urllib.parse import urlsplit
from flask import request, jsonify, make_response

from . import admin_bp, images_bp
from ..config import logger
from ..utils import add_cache_headers
from ..database import (
    get_all_domains, get_active_image_domains,
    add_domain, update_domain, delete_domain, set_default_domain,
)
from .. import admin_module


def _set_admin_cors_headers(response):
    """设置管理员 API 的 CORS 头"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


def _normalize_cdn_domain(value) -> str:
    """标准化域名（提取主机名，去除协议和路径）"""
    raw = str(value or '').strip()
    if not raw:
        return ''
    if '://' in raw:
        parsed = urlsplit(raw)
        raw = (parsed.netloc or '').strip()
    raw = raw.split('/')[0].split('?')[0].split('#')[0].strip()
    if '@' in raw:
        return ''
    return raw


# ===================== 管理员域名 API =====================
@admin_bp.route('/api/admin/domains', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_domains_api():
    """管理员域名列表 / 添加域名"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            domains = get_all_domains()
            response = jsonify({'success': True, 'data': domains})
            return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

        # POST: 添加域名
        data = request.get_json()
        if not data:
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        raw_domain = data.get('domain', '')
        domain = _normalize_cdn_domain(raw_domain)
        if not domain:
            response = jsonify({'success': False, 'error': '无效的域名'})
            return _set_admin_cors_headers(response), 400

        domain_type = data.get('domain_type', 'image')
        if domain_type not in ('default', 'image'):
            response = jsonify({'success': False, 'error': '无效的域名类型，仅支持 default 和 image'})
            return _set_admin_cors_headers(response), 400

        # 默认域名只能有一个
        if domain_type == 'default':
            existing_defaults = get_all_domains()
            if any(d.get('domain_type') == 'default' for d in existing_defaults):
                response = jsonify({'success': False, 'error': '默认域名已存在，请先删除现有默认域名'})
                return _set_admin_cors_headers(response), 400

        use_https = 1 if data.get('use_https', True) else 0
        remark = str(data.get('remark', '')).strip()[:200]

        domain_id = add_domain(domain, domain_type, use_https, remark)
        if not domain_id:
            response = jsonify({'success': False, 'error': '添加域名失败，该域名可能已存在'})
            return _set_admin_cors_headers(response), 400

        # 清除域名缓存
        from ..utils import clear_domains_cache
        clear_domains_cache()

        response = jsonify({
            'success': True,
            'message': '域名添加成功',
            'data': {'id': domain_id, 'domain': domain}
        })
        return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"域名管理操作失败: {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@admin_bp.route('/api/admin/domains/<int:domain_id>', methods=['PUT', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_domain_detail(domain_id):
    """更新 / 删除单个域名"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'DELETE':
            if not delete_domain(domain_id):
                response = jsonify({'success': False, 'error': '域名不存在'})
                return _set_admin_cors_headers(response), 404

            from ..utils import clear_domains_cache
            clear_domains_cache()

            response = jsonify({'success': True, 'message': '域名已删除'})
            return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

        # PUT: 更新域名
        data = request.get_json()
        if not data:
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        kwargs = {}
        if 'domain' in data:
            domain = _normalize_cdn_domain(data['domain'])
            if not domain:
                response = jsonify({'success': False, 'error': '无效的域名'})
                return _set_admin_cors_headers(response), 400
            kwargs['domain'] = domain

        if 'domain_type' in data:
            if data['domain_type'] not in ('default', 'image'):
                response = jsonify({'success': False, 'error': '无效的域名类型，仅支持 default 和 image'})
                return _set_admin_cors_headers(response), 400
            kwargs['domain_type'] = data['domain_type']

        if 'use_https' in data:
            kwargs['use_https'] = 1 if data['use_https'] else 0
        if 'is_active' in data:
            kwargs['is_active'] = 1 if data['is_active'] else 0
        if 'sort_order' in data:
            try:
                kwargs['sort_order'] = int(data['sort_order'])
            except (TypeError, ValueError):
                pass
        if 'remark' in data:
            kwargs['remark'] = str(data['remark']).strip()[:200]

        if not update_domain(domain_id, **kwargs):
            response = jsonify({'success': False, 'error': '更新失败或域名不存在'})
            return _set_admin_cors_headers(response), 404

        from ..utils import clear_domains_cache
        clear_domains_cache()

        response = jsonify({'success': True, 'message': '域名已更新'})
        return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"域名操作失败 (id={domain_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


@admin_bp.route('/api/admin/domains/<int:domain_id>/set-default', methods=['PUT', 'OPTIONS'])
@admin_module.login_required
def admin_domain_set_default(domain_id):
    """设为默认域名"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if not set_default_domain(domain_id):
            response = jsonify({'success': False, 'error': '域名不存在'})
            return _set_admin_cors_headers(response), 404

        from ..utils import clear_domains_cache
        clear_domains_cache()

        response = jsonify({'success': True, 'message': '已设为默认域名'})
        return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"设置默认域名失败 (id={domain_id}): {e}")
        response = jsonify({'success': False, 'error': '操作失败'})
        return _set_admin_cors_headers(response), 500


# ===================== 公开域名 API =====================
@images_bp.route('/api/public/domains', methods=['GET', 'OPTIONS'])
def public_domains_api():
    """返回活跃图片域名列表（公开）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        domains = get_active_image_domains()
        result = []
        for d in domains:
            scheme = 'https' if d.get('use_https', 1) else 'http'
            result.append({
                'domain': d['domain'],
                'url': f"{scheme}://{d['domain']}",
                'is_default': bool(d.get('is_default', 0)),
                'remark': d.get('remark', ''),
            })

        response = jsonify({'success': True, 'data': result})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公开域名列表失败: {e}")
        response = jsonify({'success': False, 'error': '获取域名列表失败'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500
