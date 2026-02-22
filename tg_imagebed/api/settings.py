#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置路由模块 - 公共设置和管理员设置 API
"""
import os
import re
from urllib.parse import urlsplit
from flask import request, jsonify, make_response

from . import admin_bp, images_bp
from ..config import logger, PROXY_URL
from ..utils import add_cache_headers, clear_domain_cache
from ..database import (
    get_public_settings, get_all_system_settings, update_system_settings,
    disable_guest_tokens, disable_all_tokens
)

from .. import admin_module


def _set_admin_cors_headers(response):
    """设置管理员 API 的 CORS 头"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


def _safe_int(value, default=0, minimum=None, maximum=None):
    """安全转换整数"""
    try:
        result = int(value)
        if minimum is not None and result < minimum:
            return minimum
        if maximum is not None and result > maximum:
            return maximum
        return result
    except (TypeError, ValueError):
        return default


def _normalize_cdn_domain(value) -> str:
    """标准化 CDN 域名（提取主机名，去除协议和路径）"""
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


def _format_settings_for_response(settings: dict) -> dict:
    """格式化设置用于 API 响应（敏感配置只返回是否已设置）"""
    return {
        # 游客上传策略
        'guest_upload_policy': settings.get('guest_upload_policy', 'open'),
        'guest_token_generation_enabled': settings.get('guest_token_generation_enabled', '1') == '1',
        'guest_existing_tokens_policy': settings.get('guest_existing_tokens_policy', 'keep'),
        'guest_token_max_upload_limit': _safe_int(settings.get('guest_token_max_upload_limit'), 1000, 1),
        'guest_token_max_expires_days': _safe_int(settings.get('guest_token_max_expires_days'), 365, 1),
        'max_file_size_mb': _safe_int(settings.get('max_file_size_mb'), 20, 1, 100),
        'daily_upload_limit': _safe_int(settings.get('daily_upload_limit'), 0, 0),
        # CDN 配置
        'cdn_enabled': settings.get('cdn_enabled', '0') == '1',
        'cloudflare_cdn_domain': settings.get('cloudflare_cdn_domain', ''),
        'cloudflare_api_token_set': bool(settings.get('cloudflare_api_token', '')),
        'cloudflare_zone_id': settings.get('cloudflare_zone_id', ''),
        'cloudflare_cache_level': settings.get('cloudflare_cache_level', 'aggressive'),
        'cloudflare_browser_ttl': _safe_int(settings.get('cloudflare_browser_ttl'), 14400, 0),
        'cloudflare_edge_ttl': _safe_int(settings.get('cloudflare_edge_ttl'), 2592000, 0),
        'enable_smart_routing': settings.get('enable_smart_routing', '0') == '1',
        'fallback_to_origin': settings.get('fallback_to_origin', '1') == '1',
        'enable_cache_warming': settings.get('enable_cache_warming', '0') == '1',
        'cache_warming_delay': _safe_int(settings.get('cache_warming_delay'), 5, 0),
        'cdn_monitor_enabled': settings.get('cdn_monitor_enabled', '0') == '1',
        'cdn_redirect_enabled': settings.get('cdn_redirect_enabled', '0') == '1',
        'cdn_redirect_max_count': _safe_int(settings.get('cdn_redirect_max_count'), 2, 1),
        'cdn_redirect_delay': _safe_int(settings.get('cdn_redirect_delay'), 10, 0),
        # 群组上传配置
        'group_upload_admin_only': settings.get('group_upload_admin_only', '0') == '1',
        'group_admin_ids': settings.get('group_admin_ids', ''),
        'group_upload_reply': settings.get('group_upload_reply', '1') == '1',
        'group_upload_delete_delay': _safe_int(settings.get('group_upload_delete_delay'), 0, 0),
        # TG 同步删除
        'tg_sync_delete_enabled': settings.get('tg_sync_delete_enabled', '1') == '1',
        # Bot 功能开关
        'bot_caption_filename_enabled': settings.get('bot_caption_filename_enabled', '1') == '1',
        'bot_inline_buttons_enabled': settings.get('bot_inline_buttons_enabled', '1') == '1',
        'bot_user_delete_enabled': settings.get('bot_user_delete_enabled', '1') == '1',
        'bot_myuploads_enabled': settings.get('bot_myuploads_enabled', '1') == '1',
        'bot_myuploads_page_size': _safe_int(settings.get('bot_myuploads_page_size'), 8, 1, 50),
        # 网络代理
        'proxy_url_set': bool(settings.get('proxy_url', '')),
        'proxy_env_set': bool(PROXY_URL),
        # 允许的文件后缀
        'allowed_extensions': settings.get('allowed_extensions', 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico'),
        # TG 认证
        'tg_auth_enabled': settings.get('tg_auth_enabled', '0') == '1',
        'tg_auth_required_for_token': settings.get('tg_auth_required_for_token', '0') == '1',
        'tg_bind_token_enabled': settings.get('tg_bind_token_enabled', '0') == '1',
        'tg_max_tokens_per_user': _safe_int(settings.get('tg_max_tokens_per_user'), 5, 1, 100),
        'tg_login_code_expire_minutes': _safe_int(settings.get('tg_login_code_expire_minutes'), 5, 1, 60),
        'tg_session_expire_days': _safe_int(settings.get('tg_session_expire_days'), 30, 1, 365),
        # 非 TG 用户 Token 限制
        'max_guest_tokens_per_ip': _safe_int(settings.get('max_guest_tokens_per_ip'), 3, 1, 100),
    }


# ===================== 公共设置 API =====================
@images_bp.route('/api/public/settings', methods=['GET', 'OPTIONS'])
def get_public_settings_api():
    """获取公开的系统设置（供前端使用）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        settings = get_public_settings()

        response = jsonify({
            'success': True,
            'data': settings
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公共设置失败: {e}")
        response = jsonify({'success': False, 'error': '获取设置失败，请稍后重试'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


# ===================== 管理员系统设置 API =====================
@admin_bp.route('/api/admin/system/settings', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def admin_system_settings():
    """管理员系统设置 API"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        if request.method == 'GET':
            settings = get_all_system_settings()

            response = jsonify({
                'success': True,
                'data': _format_settings_for_response(settings),
                'policy_options': {
                    'guest_upload_policy': [
                        {'value': 'open', 'label': '完全开放', 'description': '允许匿名上传和 Token 上传'},
                        {'value': 'token_only', 'label': '仅 Token', 'description': '禁止匿名上传，允许 Token 上传'},
                        {'value': 'admin_only', 'label': '仅管理员', 'description': '禁止所有游客上传'},
                    ],
                    'guest_existing_tokens_policy': [
                        {'value': 'keep', 'label': '保留有效', 'description': '关闭游客模式后，已有 Token 仍可使用'},
                        {'value': 'disable_guest', 'label': '禁用游客 Token', 'description': '关闭时禁用所有游客生成的 Token'},
                        {'value': 'disable_all', 'label': '禁用所有 Token', 'description': '关闭时禁用所有 Token'},
                    ],
                    'cloudflare_cache_level': [
                        {'value': 'basic', 'label': '基础', 'description': '基础缓存策略'},
                        {'value': 'aggressive', 'label': '激进', 'description': '更激进的缓存策略'},
                        {'value': 'simplified', 'label': '简化', 'description': '简化缓存策略'},
                    ]
                }
            })

        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                response = jsonify({'success': False, 'error': '无效的请求数据'})
                return _set_admin_cors_headers(response), 400

            settings_to_update = {}
            errors = []
            svg_warning = ''

            # 游客上传策略
            if 'guest_upload_policy' in data:
                policy = data['guest_upload_policy']
                if policy not in ['open', 'token_only', 'admin_only']:
                    errors.append('无效的上传策略')
                else:
                    settings_to_update['guest_upload_policy'] = policy

            if 'guest_token_generation_enabled' in data:
                settings_to_update['guest_token_generation_enabled'] = '1' if data['guest_token_generation_enabled'] else '0'

            if 'guest_existing_tokens_policy' in data:
                policy = data['guest_existing_tokens_policy']
                if policy not in ['keep', 'disable_guest', 'disable_all']:
                    errors.append('无效的 Token 策略')
                else:
                    settings_to_update['guest_existing_tokens_policy'] = policy

            if 'guest_token_max_upload_limit' in data:
                limit = _safe_int(data['guest_token_max_upload_limit'], -1)
                if limit < 1 or limit > 1000000:
                    errors.append('Token 最大上传数必须在 1-1000000 之间')
                else:
                    settings_to_update['guest_token_max_upload_limit'] = str(limit)

            if 'guest_token_max_expires_days' in data:
                days = _safe_int(data['guest_token_max_expires_days'], -1)
                if days < 1 or days > 36500:
                    errors.append('Token 最大有效期必须在 1-36500 天之间')
                else:
                    settings_to_update['guest_token_max_expires_days'] = str(days)

            if 'max_file_size_mb' in data:
                size = _safe_int(data['max_file_size_mb'], -1)
                if size < 1 or size > 100:
                    errors.append('文件大小限制必须在 1-100 MB 之间')
                else:
                    settings_to_update['max_file_size_mb'] = str(size)

            if 'daily_upload_limit' in data:
                limit = _safe_int(data['daily_upload_limit'], -1)
                if limit < 0:
                    errors.append('每日上传限制不能为负数')
                else:
                    settings_to_update['daily_upload_limit'] = str(limit)

            # CDN 配置
            if 'cdn_enabled' in data:
                settings_to_update['cdn_enabled'] = '1' if data['cdn_enabled'] else '0'

            if 'cloudflare_cdn_domain' in data:
                domain = _normalize_cdn_domain(data['cloudflare_cdn_domain'])
                settings_to_update['cloudflare_cdn_domain'] = domain
                logger.info(f"准备保存域名配置: 原始值={data['cloudflare_cdn_domain']}, 标准化后={domain}")

            if 'cloudflare_api_token' in data:
                token = str(data.get('cloudflare_api_token') or '').strip()
                if token:
                    settings_to_update['cloudflare_api_token'] = token

            if 'cloudflare_zone_id' in data:
                settings_to_update['cloudflare_zone_id'] = str(data['cloudflare_zone_id']).strip()

            if 'cloudflare_cache_level' in data:
                level = data['cloudflare_cache_level']
                if level in ['basic', 'aggressive', 'simplified']:
                    settings_to_update['cloudflare_cache_level'] = level

            if 'cloudflare_browser_ttl' in data:
                ttl = _safe_int(data['cloudflare_browser_ttl'], 14400)
                settings_to_update['cloudflare_browser_ttl'] = str(max(0, ttl))

            if 'cloudflare_edge_ttl' in data:
                ttl = _safe_int(data['cloudflare_edge_ttl'], 2592000)
                settings_to_update['cloudflare_edge_ttl'] = str(max(0, ttl))

            if 'enable_smart_routing' in data:
                settings_to_update['enable_smart_routing'] = '1' if data['enable_smart_routing'] else '0'

            if 'fallback_to_origin' in data:
                settings_to_update['fallback_to_origin'] = '1' if data['fallback_to_origin'] else '0'

            if 'enable_cache_warming' in data:
                settings_to_update['enable_cache_warming'] = '1' if data['enable_cache_warming'] else '0'

            if 'cache_warming_delay' in data:
                delay = _safe_int(data['cache_warming_delay'], 5)
                settings_to_update['cache_warming_delay'] = str(max(0, delay))

            if 'cdn_monitor_enabled' in data:
                settings_to_update['cdn_monitor_enabled'] = '1' if data['cdn_monitor_enabled'] else '0'

            if 'cdn_redirect_enabled' in data:
                settings_to_update['cdn_redirect_enabled'] = '1' if data['cdn_redirect_enabled'] else '0'

            if 'cdn_redirect_max_count' in data:
                count = _safe_int(data['cdn_redirect_max_count'], 2)
                settings_to_update['cdn_redirect_max_count'] = str(max(1, count))

            if 'cdn_redirect_delay' in data:
                delay = _safe_int(data['cdn_redirect_delay'], 10)
                settings_to_update['cdn_redirect_delay'] = str(max(0, delay))

            # 群组上传配置
            if 'group_upload_admin_only' in data:
                settings_to_update['group_upload_admin_only'] = '1' if data['group_upload_admin_only'] else '0'

            if 'group_admin_ids' in data:
                ids_str = str(data['group_admin_ids']).strip()
                if ids_str:
                    try:
                        [int(x.strip()) for x in ids_str.split(',') if x.strip()]
                    except ValueError:
                        errors.append('管理员 ID 格式无效，应为逗号分隔的数字')
                settings_to_update['group_admin_ids'] = ids_str

            if 'group_upload_reply' in data:
                settings_to_update['group_upload_reply'] = '1' if data['group_upload_reply'] else '0'

            if 'group_upload_delete_delay' in data:
                delay = _safe_int(data['group_upload_delete_delay'], 0)
                settings_to_update['group_upload_delete_delay'] = str(max(0, delay))

            # TG 同步删除
            if 'tg_sync_delete_enabled' in data:
                settings_to_update['tg_sync_delete_enabled'] = '1' if data['tg_sync_delete_enabled'] else '0'

            # Bot 功能开关
            for bool_key in (
                'bot_caption_filename_enabled', 'bot_inline_buttons_enabled',
                'bot_user_delete_enabled', 'bot_myuploads_enabled',
            ):
                if bool_key in data:
                    settings_to_update[bool_key] = '1' if data[bool_key] else '0'

            if 'bot_myuploads_page_size' in data:
                ps = _safe_int(data['bot_myuploads_page_size'], 8)
                if ps < 1 or ps > 50:
                    errors.append('上传历史每页数量必须在 1-50 之间')
                else:
                    settings_to_update['bot_myuploads_page_size'] = str(ps)

            # 网络代理
            if 'proxy_url' in data:
                proxy_val = str(data.get('proxy_url') or '').strip()
                if proxy_val:
                    if not proxy_val.startswith(('http://', 'https://')):
                        errors.append('代理 URL 必须以 http:// 或 https:// 开头')
                    else:
                        settings_to_update['proxy_url'] = proxy_val
                else:
                    # 空值清除代理
                    settings_to_update['proxy_url'] = ''

            # TG 认证配置
            for tg_bool_key in ('tg_auth_enabled', 'tg_auth_required_for_token', 'tg_bind_token_enabled'):
                if tg_bool_key in data:
                    settings_to_update[tg_bool_key] = '1' if data[tg_bool_key] else '0'

            if 'tg_max_tokens_per_user' in data:
                val = _safe_int(data['tg_max_tokens_per_user'], 5)
                if val < 1 or val > 100:
                    errors.append('每用户 Token 上限必须在 1-100 之间')
                else:
                    settings_to_update['tg_max_tokens_per_user'] = str(val)

            if 'tg_login_code_expire_minutes' in data:
                val = _safe_int(data['tg_login_code_expire_minutes'], 5)
                if val < 1 or val > 60:
                    errors.append('验证码有效期必须在 1-60 分钟之间')
                else:
                    settings_to_update['tg_login_code_expire_minutes'] = str(val)

            if 'tg_session_expire_days' in data:
                val = _safe_int(data['tg_session_expire_days'], 30)
                if val < 1 or val > 365:
                    errors.append('会话有效期必须在 1-365 天之间')
                else:
                    settings_to_update['tg_session_expire_days'] = str(val)

            # 非 TG 用户 Token 限制
            if 'max_guest_tokens_per_ip' in data:
                val = _safe_int(data['max_guest_tokens_per_ip'], 3)
                if val < 1 or val > 100:
                    errors.append('每 IP Token 上限必须在 1-100 之间')
                else:
                    settings_to_update['max_guest_tokens_per_ip'] = str(val)

            # 允许的文件后缀
            svg_warning = ''
            if 'allowed_extensions' in data:
                raw_exts = str(data.get('allowed_extensions') or '').strip()
                if raw_exts:
                    ext_list = [e.strip().lower().lstrip('.') for e in raw_exts.split(',') if e.strip()]
                    # 验证每项只允许字母数字
                    invalid_exts = [e for e in ext_list if not re.match(r'^[a-zA-Z0-9]+$', e)]
                    if invalid_exts:
                        errors.append(f'文件后缀格式无效: {", ".join(invalid_exts)}')
                    else:
                        if 'svg' in ext_list:
                            svg_warning = '已启用 SVG 上传，请注意 SVG 文件存在 XSS 安全风险'
                        # 去重、排序、小写化
                        unique_exts = sorted(set(ext_list))
                        settings_to_update['allowed_extensions'] = ','.join(unique_exts)
                else:
                    # 空值恢复默认
                    settings_to_update['allowed_extensions'] = 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico'

            # 有错误则返回
            if errors:
                response = jsonify({'success': False, 'error': '; '.join(errors)})
                return _set_admin_cors_headers(response), 400

            # 更新设置
            if settings_to_update:
                if not update_system_settings(settings_to_update):
                    response = jsonify({'success': False, 'error': '更新设置失败'})
                    return _set_admin_cors_headers(response), 500
                # 清除域名缓存，确保设置立即生效
                if any(k in settings_to_update for k in ('cloudflare_cdn_domain', 'cdn_enabled')):
                    clear_domain_cache()

                # 同步代理到环境变量（CDN 服务和 S3 等依赖 os.environ）
                if 'proxy_url' in settings_to_update:
                    proxy_val = settings_to_update['proxy_url']
                    if proxy_val:
                        os.environ['HTTP_PROXY'] = proxy_val
                        os.environ['HTTPS_PROXY'] = proxy_val
                    else:
                        os.environ.pop('HTTP_PROXY', None)
                        os.environ.pop('HTTPS_PROXY', None)

            # 获取更新后的有效配置
            updated_settings = get_all_system_settings()

            # 处理 Token 禁用策略（使用合并后的有效配置）
            disabled_count = 0
            if data.get('apply_token_policy'):
                tokens_policy = updated_settings.get('guest_existing_tokens_policy', 'keep')
                if tokens_policy == 'disable_guest':
                    disabled_count = disable_guest_tokens()
                elif tokens_policy == 'disable_all':
                    disabled_count = disable_all_tokens()

            msg = '设置已更新'
            if svg_warning:
                msg = f'{msg}。⚠️ {svg_warning}'

            response = jsonify({
                'success': True,
                'message': msg,
                'data': _format_settings_for_response(updated_settings),
                'tokens_disabled': disabled_count
            })

        response = _set_admin_cors_headers(response)
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"系统设置操作失败: {e}")
        response = jsonify({'success': False, 'error': '系统设置操作失败'})
        return _set_admin_cors_headers(response), 500


@admin_bp.route('/api/admin/tokens/revoke', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_revoke_tokens():
    """管理员批量禁用 Token"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        data = request.get_json() or {}
        revoke_type = data.get('type', 'guest')

        if revoke_type == 'all':
            count = disable_all_tokens()
            message = f'已禁用所有 {count} 个 Token'
        else:
            count = disable_guest_tokens()
            message = f'已禁用 {count} 个游客 Token'

        response = jsonify({
            'success': True,
            'message': message,
            'disabled_count': count
        })
        return _set_admin_cors_headers(response)

    except Exception as e:
        logger.error(f"批量禁用 Token 失败: {e}")
        response = jsonify({'success': False, 'error': '批量禁用失败，请稍后重试'})
        return _set_admin_cors_headers(response), 500
