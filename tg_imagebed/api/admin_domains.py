#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名管理 API - 管理员域名 CRUD + 公开域名列表
"""
import json
from flask import request, jsonify, make_response

from . import admin_bp, images_bp
from ..config import logger
from ..utils import add_cache_headers
from ..database import (
    get_all_domains, get_active_image_domains,
    add_domain, update_domain, delete_domain, set_default_domain,
    get_active_gallery_domains, update_system_setting,
)
from ..database.domains import _normalize_domain
from .. import admin_module


def _set_admin_cors_headers(response):
    """设置管理员 API 的 CORS 头"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


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
        domain = _normalize_domain(raw_domain)
        if not domain:
            response = jsonify({'success': False, 'error': '无效的域名'})
            return _set_admin_cors_headers(response), 400

        domain_type = data.get('domain_type', 'image')
        if domain_type not in ('default', 'image', 'gallery'):
            response = jsonify({'success': False, 'error': '无效的域名类型，仅支持 default、image 和 gallery'})
            return _set_admin_cors_headers(response), 400

        use_https = 1 if data.get('use_https', True) else 0
        remark = str(data.get('remark', '')).strip()[:200]

        domain_id = add_domain(domain, domain_type, use_https, remark)
        if not domain_id:
            response = jsonify({'success': False, 'error': '添加域名失败，该域名可能已存在'})
            return _set_admin_cors_headers(response), 400

        # 添加 gallery 域名时，自动记录当前主站 URL（用于 SSO 回调）
        if domain_type == 'gallery':
            from ..utils import get_domain
            main_url = get_domain(request)
            update_system_setting('gallery_sso_main_url', main_url)

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
            domain = _normalize_domain(data['domain'])
            if not domain:
                response = jsonify({'success': False, 'error': '无效的域名'})
                return _set_admin_cors_headers(response), 400
            kwargs['domain'] = domain

        if 'domain_type' in data:
            if data['domain_type'] not in ('default', 'image', 'gallery'):
                response = jsonify({'success': False, 'error': '无效的域名类型，仅支持 default、image 和 gallery'})
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


@admin_bp.route('/api/admin/domains/policy', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def admin_domains_policy():
    """域名场景路由策略 — 配置不同上传场景使用的图片域名"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        from ..database import get_system_setting, update_system_setting

        if request.method == 'GET':
            raw = get_system_setting('domain_upload_policy_json') or ''
            policy = {}
            if raw:
                try:
                    policy = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    pass
            response = jsonify({'success': True, 'data': policy})
            return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

        # PUT: 保存策略
        data = request.get_json()
        if not isinstance(data, dict):
            response = jsonify({'success': False, 'error': '无效的请求数据'})
            return _set_admin_cors_headers(response), 400

        # 获取活跃图片域名列表用于校验
        active_domains = get_active_image_domains()
        active_domain_set = {d['domain'] for d in active_domains}

        valid_scenes = ('guest', 'token', 'group', 'admin_default')
        cleaned = {}
        for scene in valid_scenes:
            val = str(data.get(scene, '')).strip()
            if val and val not in active_domain_set:
                response = jsonify({
                    'success': False,
                    'error': f'场景 {scene} 指定的域名 {val} 不在活跃图片域名列表中'
                })
                return _set_admin_cors_headers(response), 400
            cleaned[scene] = val

        update_system_setting('domain_upload_policy_json', json.dumps(cleaned))

        # 清除域名策略缓存
        from ..utils import clear_domains_cache
        clear_domains_cache()

        response = jsonify({'success': True, 'message': '域名场景路由策略已保存', 'data': cleaned})
        return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"域名策略操作失败: {e}")
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


# ===================== 画集站点入口 API =====================
@admin_bp.route('/api/admin/gallery-site/entry', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_gallery_site_entry():
    """返回画集域名信息（用于主站"进入画集管理"按钮）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        # 管理员从主站访问此端点，更新主站 URL 记录
        from ..utils import get_domain
        main_url = get_domain(request)
        update_system_setting('gallery_sso_main_url', main_url)

        gallery_domains = get_active_gallery_domains()
        if not gallery_domains:
            response = jsonify({
                'success': True,
                'data': {'available': False, 'domain': None, 'url': None}
            })
            return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

        # 返回第一个活跃画集域名
        d = gallery_domains[0]
        scheme = 'https' if d.get('use_https', 1) else 'http'
        domain = d['domain']
        response = jsonify({
            'success': True,
            'data': {
                'available': True,
                'domain': domain,
                'url': f"{scheme}://{domain}",
                'remark': d.get('remark', ''),
            }
        })
        return _set_admin_cors_headers(add_cache_headers(response, 'no-cache'))

    except Exception as e:
        logger.error(f"获取画集站点入口失败: {e}")
        response = jsonify({'success': False, 'error': '获取失败'})
        return _set_admin_cors_headers(response), 500
