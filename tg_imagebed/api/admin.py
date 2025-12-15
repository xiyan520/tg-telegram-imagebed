#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由模块 - 管理员 API
"""
import os
import json
from flask import request, jsonify, Response, session

from . import admin_bp
from ..config import (
    CLOUDFLARE_CDN_DOMAIN, STATIC_VERSION, DATABASE_PATH, logger
)
from ..utils import add_cache_headers, format_size, get_domain
from ..database import (
    get_announcement, update_announcement,
    update_system_setting, get_system_setting,
    admin_list_tokens, admin_create_token,
    admin_update_token_status, admin_delete_token,
    update_cdn_cache_status, get_uncached_files, get_cdn_dashboard_stats,
)
from ..services.cdn_service import cloudflare_cdn, add_to_cdn_monitor, get_monitor_queue_size
from ..services.file_service import process_upload
from ..storage.router import get_storage_router, reload_storage_router, _load_storage_config

# 导入 admin_module 用于登录验证装饰器
from .. import admin_module


# 注意：/api/admin/check 端点已在 admin_module.py 中定义
# 此处不再重复定义，避免路由冲突


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
    for url in urls:
        if '/image/' in url:
            encrypted_id = url.split('/image/')[-1]
            if CLOUDFLARE_CDN_DOMAIN:
                cdn_urls.append(f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}")

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
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    data = request.get_json() or {}
    encrypted_ids = data.get('encrypted_ids') or []
    max_items = int(data.get('max_items') or 200)

    if not encrypted_ids:
        return add_cache_headers(jsonify({'success': False, 'error': 'No encrypted_ids provided'}), 'no-cache'), 400

    if not CLOUDFLARE_CDN_DOMAIN:
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
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    if not CLOUDFLARE_CDN_DOMAIN:
        return add_cache_headers(jsonify({'success': False, 'error': 'CDN domain not configured'}), 'no-cache'), 400

    data = request.get_json() or {}
    encrypted_ids = data.get('encrypted_ids') or []
    all_uncached = bool(data.get('all_uncached'))
    limit = int(data.get('limit') or 200)
    since_seconds = int(data.get('since_seconds') or 86400)

    import time
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
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    window_hours = request.args.get('window_hours')
    window_hours = int(window_hours) if window_hours is not None else None

    data = get_cdn_dashboard_stats(window_hours=window_hours)
    data['monitor'] = {'queue_size': get_monitor_queue_size()}
    data['cloudflare'] = {'cdn_domain': CLOUDFLARE_CDN_DOMAIN or None}

    return add_cache_headers(jsonify({'success': True, 'data': data}), 'no-cache')


@admin_bp.route('/api/admin/clear_cache', methods=['POST', 'OPTIONS'])
@admin_bp.route('/api/admin/clear-cache', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def clear_cache():
    """清理 CDN 缓存（仅限管理员）"""
    import time
    from .. import config as app_config

    # 更新静态版本号（强制客户端刷新静态资源）
    new_version = str(int(time.time()))
    app_config.STATIC_VERSION = new_version

    cloudflare_success = False
    if CLOUDFLARE_CDN_DOMAIN and cloudflare_cdn.zone_id:
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


@admin_bp.route('/api/admin/settings', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_update_settings():
    """更新管理员设置"""
    data = request.get_json()
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()

    if not new_username and not new_password:
        return jsonify({'success': False, 'message': '请提供新的用户名或密码'}), 400

    if new_username and len(new_username) < 3:
        return jsonify({'success': False, 'message': '用户名至少需要3个字符'}), 400

    if new_password and len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少需要6个字符'}), 400

    if admin_module.update_admin_credentials(new_username, new_password):
        if new_username:
            session['admin_username'] = new_username

        return jsonify({
            'success': True,
            'message': '设置更新成功'
        })

    return jsonify({'success': False, 'message': '更新失败'}), 500


@admin_bp.route('/api/announcement', methods=['GET', 'OPTIONS'])
def get_announcement_api():
    """获取当前公告"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        announcement = get_announcement()

        if announcement:
            response = jsonify({
                'success': True,
                'data': {
                    'id': announcement['id'],
                    'enabled': bool(announcement['enabled']),
                    'content': announcement['content'],
                    'created_at': announcement['created_at'],
                    'updated_at': announcement['updated_at']
                }
            })
        else:
            response = jsonify({
                'success': True,
                'data': {
                    'id': 0,
                    'enabled': False,
                    'content': '',
                    'created_at': None,
                    'updated_at': None
                }
            })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公告失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/announcement', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_announcement():
    """管理员公告管理"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            announcement = get_announcement()

            if announcement:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': announcement['id'],
                        'enabled': bool(announcement['enabled']),
                        'content': announcement['content'],
                        'created_at': announcement['created_at'],
                        'updated_at': announcement['updated_at']
                    }
                })
            else:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': 0,
                        'enabled': False,
                        'content': '',
                        'created_at': None,
                        'updated_at': None
                    }
                })

        elif request.method == 'POST':
            data = request.get_json()
            enabled = data.get('enabled', True)
            content = data.get('content', '')

            announcement_id = update_announcement(enabled, content)

            response = jsonify({
                'success': True,
                'message': '公告更新成功',
                'data': {
                    'id': announcement_id,
                    'enabled': enabled,
                    'content': content
                }
            })

        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"公告管理失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


# ===================== 存储配置 API =====================

@admin_bp.route('/api/admin/storage', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def get_storage_backends():
    """获取所有配置的存储后端"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        router = get_storage_router()
        backends = router.list_backends()
        active_name = router.get_active_backend_name()

        response = jsonify({
            'success': True,
            'data': {
                'active': active_name,
                'backends': backends
            }
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取存储后端列表失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/storage/active', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def set_active_storage():
    """设置激活的存储后端"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        data = request.get_json() or {}
        backend_name = (data.get('backend') or '').strip()

        if not backend_name:
            response = jsonify({'success': False, 'error': '请指定后端名称'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 验证后端是否存在
        router = get_storage_router()
        backends = router.list_backends()
        if backend_name not in backends:
            response = jsonify({'success': False, 'error': f'后端 {backend_name} 不存在'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 更新配置（通过环境变量或数据库）
        # 这里我们使用数据库存储 active 后端
        update_system_setting('storage_active_backend', backend_name)

        # 重新加载路由器
        reload_storage_router()

        logger.info(f"存储后端已切换到: {backend_name}")

        response = jsonify({
            'success': True,
            'message': f'已切换到 {backend_name} 后端',
            'active': backend_name
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"切换存储后端失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/storage/health', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def check_storage_health():
    """检查存储后端健康状态"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        router = get_storage_router()
        backends = router.list_backends()
        health_status = {}

        for name in backends.keys():
            try:
                backend = router.get_backend(name)
                health_status[name] = backend.healthcheck()
            except Exception as e:
                logger.warning(f"后端 {name} 健康检查失败: {e}")
                health_status[name] = False

        response = jsonify({
            'success': True,
            'data': health_status
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"存储健康检查失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/storage/policy', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def storage_upload_policy():
    """获取/更新上传场景路由策略"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        router = get_storage_router()
        backends = router.list_backends()

        if request.method == 'GET':
            response = jsonify({
                'success': True,
                'data': {
                    'policy': router.get_effective_upload_policy(),
                    'available_backends': list(backends.keys()),
                }
            })
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache')

        # PUT 请求：更新策略
        data = request.get_json(silent=True) or {}
        policy = data.get('policy') if isinstance(data.get('policy'), dict) else data
        if not isinstance(policy, dict):
            response = jsonify({'success': False, 'error': 'policy 必须为 JSON 对象'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 校验后端名称
        def _check_name(v: str) -> str:
            v = str(v or '').strip()
            if v and v not in backends:
                raise ValueError(f"后端 {v} 未配置")
            return v

        normalized = {
            'guest': _check_name(policy.get('guest')),
            'token': _check_name(policy.get('token')),
            'group': _check_name(policy.get('group')),
            'admin_default': _check_name(policy.get('admin_default')),
            'admin_allowed': [str(x).strip() for x in (policy.get('admin_allowed') or []) if str(x).strip()],
        }
        for x in normalized['admin_allowed']:
            if x not in backends:
                raise ValueError(f"admin_allowed 包含未配置后端: {x}")

        update_system_setting('storage_upload_policy_json', json.dumps(normalized, ensure_ascii=False))

        response = jsonify({'success': True, 'data': {'policy': normalized}})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"存储策略操作失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/upload', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_upload():
    """管理员上传（可选指定后端）"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    if 'file' not in request.files:
        response = jsonify({'success': False, 'error': '未提供文件'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 400

    f = request.files['file']
    if not f.filename:
        response = jsonify({'success': False, 'error': '未选择文件'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 400

    content_type = (f.content_type or '').strip()
    if not content_type.startswith('image/'):
        response = jsonify({'success': False, 'error': '只允许上传图片文件'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 400

    backend = (request.form.get('backend') or '').strip()

    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    file_content = f.read()

    try:
        result = process_upload(
            file_content=file_content,
            filename=f.filename,
            content_type=content_type,
            username=session.get('admin_username', 'admin'),
            source='admin_upload',
            upload_scene='admin',
            requested_backend=backend or None,
        )
    except ValueError as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 400

    if not result:
        response = jsonify({'success': False, 'error': '上传失败'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500

    base_url = get_domain(request)
    url = f"{base_url}/image/{result['encrypted_id']}"

    response = jsonify({
        'success': True,
        'data': {
            'url': url,
            'encrypted_id': result['encrypted_id'],
            'filename': f.filename,
            'size': format_size(result['file_size']),
        }
    })
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(response, 'no-cache')


# ===================== 存储后端配置 CRUD API =====================

# 敏感字段列表（需要掩码）
_SENSITIVE_FIELDS = {'bot_token', 'secret_key', 'access_key'}
_MASKED_VALUE = '__MASKED__'
# 允许的驱动类型
_ALLOWED_DRIVERS = {'telegram', 'local', 's3', 'rclone'}
# 后端名称正则（字母、数字、下划线、连字符，1-32字符）
import re
_BACKEND_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')


def _mask_sensitive(cfg: dict) -> dict:
    """对配置中的敏感字段进行掩码处理"""
    result = {}
    for k, v in (cfg or {}).items():
        if isinstance(v, dict):
            result[k] = _mask_sensitive(v)
        elif k in _SENSITIVE_FIELDS and v:
            result[k] = _MASKED_VALUE
        else:
            result[k] = v
    return result


def _merge_sensitive(new_cfg: dict, old_cfg: dict) -> dict:
    """合并配置，保留被掩码的敏感字段原值，并保留旧配置中未在新配置中出现的字段"""
    result = dict(old_cfg or {})  # 先复制旧配置，保留未知字段
    for k, v in (new_cfg or {}).items():
        if isinstance(v, dict) and isinstance(old_cfg.get(k), dict):
            result[k] = _merge_sensitive(v, old_cfg[k])
        elif k in _SENSITIVE_FIELDS and v == _MASKED_VALUE:
            result[k] = old_cfg.get(k, '')
        else:
            result[k] = v
    return result


def _save_storage_config(config: dict) -> None:
    """保存存储配置到数据库"""
    update_system_setting('storage_config_json', json.dumps(config, ensure_ascii=False))
    reload_storage_router()


def _is_env_override() -> bool:
    """检查是否通过环境变量覆盖配置"""
    return bool((os.getenv('STORAGE_CONFIG_JSON') or '').strip())


@admin_bp.route('/api/admin/storage/config', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def get_storage_config():
    """获取完整存储配置（敏感字段掩码）"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        config = _load_storage_config()
        masked_backends = {}
        for name, cfg in (config.get('backends') or {}).items():
            masked_backends[name] = _mask_sensitive(cfg)

        response = jsonify({
            'success': True,
            'data': {
                'active': config.get('active', 'telegram'),
                'backends': masked_backends,
                'env_override': _is_env_override(),
            }
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取存储配置失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/storage/backends', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def add_storage_backend():
    """添加新的存储后端"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if _is_env_override():
            response = jsonify({'success': False, 'error': '配置由环境变量控制，无法通过界面修改'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        backend_config = data.get('config') or {}

        if not name:
            response = jsonify({'success': False, 'error': '后端名称不能为空'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 校验后端名称格式
        if not _BACKEND_NAME_PATTERN.match(name):
            response = jsonify({'success': False, 'error': '后端名称只能包含字母、数字、下划线和连字符，长度1-32字符'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        driver = (backend_config.get('driver') or '').strip()
        if not driver:
            response = jsonify({'success': False, 'error': '必须指定驱动类型'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 校验驱动类型
        if driver not in _ALLOWED_DRIVERS:
            response = jsonify({'success': False, 'error': f"不支持的驱动类型: {driver}，允许: {', '.join(_ALLOWED_DRIVERS)}"})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        config = _load_storage_config()
        backends = config.get('backends') or {}

        if name in backends:
            response = jsonify({'success': False, 'error': f"后端 '{name}' 已存在"})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        backends[name] = backend_config
        config['backends'] = backends
        _save_storage_config(config)

        logger.info(f"添加存储后端: {name}")

        response = jsonify({
            'success': True,
            'message': f"后端 '{name}' 添加成功",
            'data': {'name': name, 'config': _mask_sensitive(backend_config)}
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"添加存储后端失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/storage/backends/<name>', methods=['PUT', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def modify_storage_backend(name: str):
    """编辑或删除存储后端"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if _is_env_override():
            response = jsonify({'success': False, 'error': '配置由环境变量控制，无法通过界面修改'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        config = _load_storage_config()
        backends = config.get('backends') or {}

        if name not in backends:
            response = jsonify({'success': False, 'error': f"后端 '{name}' 不存在"})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 404

        if request.method == 'DELETE':
            # 检查是否为当前激活后端（使用路由器获取真实激活后端）
            router = get_storage_router()
            active = router.get_active_backend_name()
            if name == active:
                response = jsonify({'success': False, 'error': '无法删除当前激活的后端'})
                response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                return add_cache_headers(response, 'no-cache'), 400

            del backends[name]
            config['backends'] = backends
            _save_storage_config(config)

            logger.info(f"删除存储后端: {name}")

            response = jsonify({'success': True, 'message': f"后端 '{name}' 已删除"})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache')

        # PUT 请求：更新后端配置
        data = request.get_json(silent=True) or {}
        new_config = data.get('config') or {}

        driver = (new_config.get('driver') or '').strip()
        if not driver:
            response = jsonify({'success': False, 'error': '必须指定驱动类型'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 校验驱动类型
        if driver not in _ALLOWED_DRIVERS:
            response = jsonify({'success': False, 'error': f"不支持的驱动类型: {driver}，允许: {', '.join(_ALLOWED_DRIVERS)}"})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 合并敏感字段（保留被掩码的原值）
        old_config = backends[name]
        merged_config = _merge_sensitive(new_config, old_config)

        backends[name] = merged_config
        config['backends'] = backends
        _save_storage_config(config)

        logger.info(f"更新存储后端: {name}")

        response = jsonify({
            'success': True,
            'message': f"后端 '{name}' 更新成功",
            'data': {'name': name, 'config': _mask_sensitive(merged_config)}
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"修改存储后端失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


# ===================== Token 管理 API =====================

@admin_bp.route('/api/admin/tokens', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_tokens_api():
    """
    Token 管理 API：
    - GET: 获取 Token 列表（分页、筛选）
    - POST: 创建新的 Token
    """
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            # 获取查询参数
            status = (request.args.get('status') or 'all').strip().lower()
            try:
                page = int(request.args.get('page', 1))
            except (TypeError, ValueError):
                page = 1
            try:
                page_size = int(request.args.get('page_size', 20))
            except (TypeError, ValueError):
                page_size = 20

            # 调用数据库函数
            data = admin_list_tokens(status=status, page=page, page_size=page_size)

            response = jsonify({'success': True, 'data': data})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache')

        # POST: 创建新 Token
        payload = request.get_json(silent=True) or {}

        created = admin_create_token(
            description=payload.get('description'),
            expires_at=payload.get('expires_at'),
            upload_limit=payload.get('upload_limit', 100),
            is_active=payload.get('is_active', True),
        )

        if not created:
            response = jsonify({'success': False, 'error': '创建 Token 失败'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 500

        response = jsonify({'success': True, 'data': created})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 201

    except ValueError as e:
        # 参数验证错误
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 400

    except Exception as e:
        logger.error(f"Token 管理 API 失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500


@admin_bp.route('/api/admin/tokens/<int:token_id>', methods=['PATCH', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def admin_token_detail_api(token_id: int):
    """
    单个 Token 操作 API：
    - PATCH: 更新 Token 状态（启用/禁用）
    - DELETE: 删除 Token
    """
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'DELETE':
            deleted = admin_delete_token(token_id=token_id)

            if not deleted:
                response = jsonify({'success': False, 'error': 'Token 不存在'})
                response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                return add_cache_headers(response, 'no-cache'), 404

            response = jsonify({'success': True, 'message': 'Token 已删除'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache')

        # PATCH: 更新 Token 状态
        payload = request.get_json(silent=True) or {}

        if 'is_active' not in payload:
            response = jsonify({'success': False, 'error': '缺少 is_active 参数'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        # 严格校验 is_active 类型，只接受布尔值
        is_active_value = payload.get('is_active')
        if not isinstance(is_active_value, bool):
            response = jsonify({'success': False, 'error': 'is_active 必须为布尔值'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 400

        updated = admin_update_token_status(
            token_id=token_id,
            is_active=is_active_value
        )

        if not updated:
            response = jsonify({'success': False, 'error': 'Token 不存在'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return add_cache_headers(response, 'no-cache'), 404

        response = jsonify({'success': True, 'data': updated})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"Token 详情 API 失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500
