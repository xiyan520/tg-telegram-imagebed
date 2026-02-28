#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置路由模块 - 公共设置和管理员设置 API
"""
import os
import re
from flask import request, jsonify, make_response

from . import admin_bp, images_bp
from ..config import logger, PROXY_URL
from ..utils import add_cache_headers, clear_domain_cache, clear_domains_cache
from ..database import (
    get_public_settings, get_all_system_settings, update_system_settings,
    disable_guest_tokens, disable_all_tokens
)
from ..database.domains import _normalize_domain

from .. import admin_module

OFFICIAL_UPDATE_REPO_URL = 'https://github.com/xiyan520/tg-telegram-imagebed.git'
OFFICIAL_UPDATE_RELEASE_REPO = 'xiyan520/tg-telegram-imagebed'
OFFICIAL_UPDATE_ASSET_NAME = 'tg-imagebed-release.zip'
OFFICIAL_UPDATE_SHA_NAME = 'tg-imagebed-release.zip.sha256'


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


def _format_settings_for_response(settings: dict) -> dict:
    """格式化设置用于 API 响应（敏感配置只返回是否已设置）"""
    from ..bot_control import is_bot_token_configured

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
        'group_upload_tg_bound_only': settings.get('group_upload_tg_bound_only', '0') == '1',
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
        'bot_update_mode': settings.get('bot_update_mode', 'polling'),
        'bot_webhook_url': settings.get('bot_webhook_url', ''),
        'bot_settoken_ttl_seconds': _safe_int(settings.get('bot_settoken_ttl_seconds'), 600, 30, 3600),
        'bot_template_strict_mode': settings.get('bot_template_strict_mode', '0') == '1',
        # Bot 回复配置
        'bot_reply_link_formats': settings.get('bot_reply_link_formats', 'url'),
        'bot_reply_template': settings.get('bot_reply_template', ''),
        'bot_reply_show_size': settings.get('bot_reply_show_size', '1') == '1',
        'bot_reply_show_filename': settings.get('bot_reply_show_filename', '0') == '1',
        # 网络代理
        'proxy_url_set': bool(settings.get('proxy_url', '')),
        'proxy_env_set': bool(PROXY_URL),
        # 允许的文件后缀
        'allowed_extensions': settings.get('allowed_extensions', 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico'),
        # TG 认证
        'tg_auth_enabled': settings.get('tg_auth_enabled', '0') == '1',
        'bot_token_configured': is_bot_token_configured(),
        'tg_auth_required_for_token': settings.get('tg_auth_required_for_token', '0') == '1',
        'tg_bind_token_enabled': settings.get('tg_bind_token_enabled', '0') == '1',
        'tg_max_tokens_per_user': _safe_int(settings.get('tg_max_tokens_per_user'), 5, 1, 100),
        'tg_login_code_expire_minutes': _safe_int(settings.get('tg_login_code_expire_minutes'), 5, 1, 60),
        'tg_session_expire_days': _safe_int(settings.get('tg_session_expire_days'), 30, 1, 365),
        # 非 TG 用户 Token 限制
        'max_guest_tokens_per_ip': _safe_int(settings.get('max_guest_tokens_per_ip'), 3, 1, 100),
        # 私聊上传配置
        'bot_private_upload_enabled': settings.get('bot_private_upload_enabled', '1') == '1',
        'bot_private_upload_mode': settings.get('bot_private_upload_mode', 'open'),
        'bot_private_admin_ids': settings.get('bot_private_admin_ids', ''),
        # SEO 配置
        'seo_site_name': settings.get('seo_site_name', ''),
        'seo_site_description': settings.get('seo_site_description', ''),
        'seo_site_keywords': settings.get('seo_site_keywords', ''),
        'seo_logo_mode': settings.get('seo_logo_mode', 'icon'),
        'seo_logo_url': settings.get('seo_logo_url', ''),
        'seo_favicon_url': settings.get('seo_favicon_url', ''),
        'seo_og_title': settings.get('seo_og_title', ''),
        'seo_og_description': settings.get('seo_og_description', ''),
        'seo_og_image': settings.get('seo_og_image', ''),
        'seo_og_site_name': settings.get('seo_og_site_name', ''),
        'seo_og_type': settings.get('seo_og_type', 'website'),
        'seo_canonical_url': settings.get('seo_canonical_url', ''),
        'seo_robots_index': settings.get('seo_robots_index', '1') == '1',
        'seo_robots_follow': settings.get('seo_robots_follow', '1') == '1',
        'seo_twitter_card_type': settings.get('seo_twitter_card_type', 'summary_large_image'),
        'seo_twitter_site': settings.get('seo_twitter_site', ''),
        'seo_twitter_creator': settings.get('seo_twitter_creator', ''),
        'seo_author': settings.get('seo_author', ''),
        'seo_theme_color': settings.get('seo_theme_color', ''),
        'seo_default_locale': settings.get('seo_default_locale', 'zh_CN'),
        'seo_footer_text': settings.get('seo_footer_text', ''),
        # 图片域名限制
        'image_domain_restriction_enabled': settings.get('image_domain_restriction_enabled', '0') == '1',
        # 热更新配置（Release Artifact）
        'app_update_source': settings.get('app_update_source', 'release'),
        'app_update_release_repo': settings.get('app_update_release_repo', OFFICIAL_UPDATE_RELEASE_REPO),
        'app_update_release_asset_name': settings.get('app_update_release_asset_name', OFFICIAL_UPDATE_ASSET_NAME),
        'app_update_release_sha_name': settings.get('app_update_release_sha_name', OFFICIAL_UPDATE_SHA_NAME),
        # 兼容旧字段（只读）
        'app_update_repo_url': settings.get('app_update_repo_url', OFFICIAL_UPDATE_REPO_URL),
        'app_update_branch': settings.get('app_update_branch', 'main'),
        'app_update_last_status': settings.get('app_update_last_status', 'idle'),
        'app_update_last_error': settings.get('app_update_last_error', ''),
        'app_update_last_version': settings.get('app_update_last_version', ''),
        'app_update_last_commit': settings.get('app_update_last_commit', ''),
        'app_update_last_run_at': settings.get('app_update_last_run_at', ''),
        'app_update_last_duration_ms': _safe_int(settings.get('app_update_last_duration_ms'), 0, 0),
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
                domain = _normalize_domain(data['cloudflare_cdn_domain'])
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

            if 'group_upload_tg_bound_only' in data:
                settings_to_update['group_upload_tg_bound_only'] = '1' if data['group_upload_tg_bound_only'] else '0'

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

            if 'bot_update_mode' in data:
                mode = str(data.get('bot_update_mode') or '').strip().lower()
                if mode not in ('polling', 'webhook'):
                    errors.append('Bot 更新模式必须为 polling 或 webhook')
                else:
                    settings_to_update['bot_update_mode'] = mode

            if 'bot_webhook_url' in data:
                webhook_url = str(data.get('bot_webhook_url') or '').strip()
                if webhook_url and not webhook_url.startswith(('http://', 'https://')):
                    errors.append('Webhook URL 必须以 http:// 或 https:// 开头')
                else:
                    settings_to_update['bot_webhook_url'] = webhook_url

            if 'bot_settoken_ttl_seconds' in data:
                ttl = _safe_int(data.get('bot_settoken_ttl_seconds'), 600)
                if ttl < 30 or ttl > 3600:
                    errors.append('/settoken 有效期必须在 30-3600 秒之间')
                else:
                    settings_to_update['bot_settoken_ttl_seconds'] = str(ttl)

            if 'bot_template_strict_mode' in data:
                settings_to_update['bot_template_strict_mode'] = '1' if data['bot_template_strict_mode'] else '0'

            # Bot 回复配置
            if 'bot_reply_link_formats' in data:
                raw_formats = str(data.get('bot_reply_link_formats') or 'url').strip()
                valid_formats = {'url', 'markdown', 'html', 'bbcode'}
                fmt_list = [f.strip().lower() for f in raw_formats.split(',') if f.strip()]
                invalid_fmts = [f for f in fmt_list if f not in valid_formats]
                if invalid_fmts:
                    errors.append(f'无效的链接格式: {", ".join(invalid_fmts)}')
                elif not fmt_list:
                    errors.append('至少需要启用一种链接格式')
                else:
                    settings_to_update['bot_reply_link_formats'] = ','.join(fmt_list)

            if 'bot_reply_template' in data:
                tpl = str(data.get('bot_reply_template') or '').strip()
                if len(tpl) > 500:
                    errors.append('自定义回复模板不能超过 500 个字符')
                else:
                    settings_to_update['bot_reply_template'] = tpl

            for reply_bool_key in ('bot_reply_show_size', 'bot_reply_show_filename'):
                if reply_bool_key in data:
                    settings_to_update[reply_bool_key] = '1' if data[reply_bool_key] else '0'

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

            # Bot 未配置时不允许开启 TG 认证
            if settings_to_update.get('tg_auth_enabled') == '1':
                from ..bot_control import is_bot_token_configured
                if not is_bot_token_configured():
                    errors.append('TG 认证需要先配置 Telegram Bot Token')
                    settings_to_update.pop('tg_auth_enabled', None)

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

            # 私聊上传配置
            if 'bot_private_upload_enabled' in data:
                settings_to_update['bot_private_upload_enabled'] = '1' if data['bot_private_upload_enabled'] else '0'

            if 'bot_private_upload_mode' in data:
                mode = str(data['bot_private_upload_mode']).strip().lower()
                if mode not in ('open', 'tg_bound', 'admin_only'):
                    errors.append('无效的私聊上传模式')
                else:
                    settings_to_update['bot_private_upload_mode'] = mode

            if 'bot_private_admin_ids' in data:
                ids_str = str(data['bot_private_admin_ids']).strip()
                if ids_str:
                    try:
                        [int(x.strip()) for x in ids_str.split(',') if x.strip()]
                    except ValueError:
                        errors.append('私聊管理员 ID 格式无效')
                settings_to_update['bot_private_admin_ids'] = ids_str

            # SEO 配置
            if 'seo_site_name' in data:
                val = str(data.get('seo_site_name') or '').strip()
                if len(val) > 100:
                    errors.append('网站名称不能超过 100 个字符')
                else:
                    settings_to_update['seo_site_name'] = val

            if 'seo_site_description' in data:
                val = str(data.get('seo_site_description') or '').strip()
                if len(val) > 500:
                    errors.append('网站描述不能超过 500 个字符')
                else:
                    settings_to_update['seo_site_description'] = val

            if 'seo_site_keywords' in data:
                val = str(data.get('seo_site_keywords') or '').strip()
                if len(val) > 500:
                    errors.append('网站关键词不能超过 500 个字符')
                else:
                    settings_to_update['seo_site_keywords'] = val

            if 'seo_logo_mode' in data:
                mode = str(data.get('seo_logo_mode') or '').strip().lower()
                if mode not in ('icon', 'custom'):
                    errors.append('无效的 Logo 模式')
                else:
                    settings_to_update['seo_logo_mode'] = mode

            for seo_url_key in ('seo_logo_url', 'seo_favicon_url', 'seo_og_image'):
                if seo_url_key in data:
                    settings_to_update[seo_url_key] = str(data.get(seo_url_key) or '').strip()

            if 'seo_og_title' in data:
                val = str(data.get('seo_og_title') or '').strip()
                if len(val) > 200:
                    errors.append('OG 标题不能超过 200 个字符')
                else:
                    settings_to_update['seo_og_title'] = val

            if 'seo_og_description' in data:
                val = str(data.get('seo_og_description') or '').strip()
                if len(val) > 500:
                    errors.append('OG 描述不能超过 500 个字符')
                else:
                    settings_to_update['seo_og_description'] = val

            if 'seo_og_site_name' in data:
                val = str(data.get('seo_og_site_name') or '').strip()
                if len(val) > 100:
                    errors.append('OG 站点名称不能超过 100 个字符')
                else:
                    settings_to_update['seo_og_site_name'] = val

            if 'seo_og_type' in data:
                val = str(data.get('seo_og_type') or '').strip().lower()
                if val not in ('website', 'article', 'profile'):
                    errors.append('OG 类型必须是 website、article 或 profile')
                else:
                    settings_to_update['seo_og_type'] = val

            if 'seo_canonical_url' in data:
                val = str(data.get('seo_canonical_url') or '').strip()
                if len(val) > 500:
                    errors.append('Canonical URL 不能超过 500 个字符')
                else:
                    settings_to_update['seo_canonical_url'] = val

            if 'seo_robots_index' in data:
                settings_to_update['seo_robots_index'] = '1' if data.get('seo_robots_index') else '0'

            if 'seo_robots_follow' in data:
                settings_to_update['seo_robots_follow'] = '1' if data.get('seo_robots_follow') else '0'

            if 'seo_twitter_card_type' in data:
                val = str(data.get('seo_twitter_card_type') or '').strip().lower()
                if val not in ('summary', 'summary_large_image'):
                    errors.append('Twitter Card 类型必须是 summary 或 summary_large_image')
                else:
                    settings_to_update['seo_twitter_card_type'] = val

            if 'seo_twitter_site' in data:
                val = str(data.get('seo_twitter_site') or '').strip()
                if len(val) > 100:
                    errors.append('Twitter 站点账号不能超过 100 个字符')
                else:
                    settings_to_update['seo_twitter_site'] = val

            if 'seo_twitter_creator' in data:
                val = str(data.get('seo_twitter_creator') or '').strip()
                if len(val) > 100:
                    errors.append('Twitter 作者账号不能超过 100 个字符')
                else:
                    settings_to_update['seo_twitter_creator'] = val

            if 'seo_author' in data:
                val = str(data.get('seo_author') or '').strip()
                if len(val) > 100:
                    errors.append('作者名称不能超过 100 个字符')
                else:
                    settings_to_update['seo_author'] = val

            if 'seo_theme_color' in data:
                val = str(data.get('seo_theme_color') or '').strip()
                if val and not re.match(r'^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6})$', val):
                    errors.append('主题色必须是合法的 HEX 颜色值，例如 #f59e0b')
                else:
                    settings_to_update['seo_theme_color'] = val

            if 'seo_default_locale' in data:
                val = str(data.get('seo_default_locale') or '').strip()
                if len(val) > 20:
                    errors.append('默认 locale 不能超过 20 个字符')
                else:
                    settings_to_update['seo_default_locale'] = val

            if 'seo_footer_text' in data:
                val = str(data.get('seo_footer_text') or '').strip()
                if len(val) > 200:
                    errors.append('页脚文字不能超过 200 个字符')
                else:
                    settings_to_update['seo_footer_text'] = val

            # 图片域名限制
            if 'image_domain_restriction_enabled' in data:
                settings_to_update['image_domain_restriction_enabled'] = '1' if data['image_domain_restriction_enabled'] else '0'

            # 热更新配置（Release Artifact）
            if 'app_update_source' in data:
                source = str(data.get('app_update_source') or '').strip().lower()
                if source != 'release':
                    errors.append('更新源仅支持 release')
                else:
                    settings_to_update['app_update_source'] = 'release'

            if 'app_update_release_repo' in data:
                repo = str(data.get('app_update_release_repo') or '').strip()
                if repo and repo != OFFICIAL_UPDATE_RELEASE_REPO:
                    errors.append('Release 仓库仅允许使用官方仓库')
                else:
                    settings_to_update['app_update_release_repo'] = OFFICIAL_UPDATE_RELEASE_REPO

            if 'app_update_release_asset_name' in data:
                asset_name = str(data.get('app_update_release_asset_name') or '').strip()
                if asset_name and asset_name != OFFICIAL_UPDATE_ASSET_NAME:
                    errors.append('Release 资产名仅允许使用官方默认值')
                else:
                    settings_to_update['app_update_release_asset_name'] = OFFICIAL_UPDATE_ASSET_NAME

            if 'app_update_release_sha_name' in data:
                sha_name = str(data.get('app_update_release_sha_name') or '').strip()
                if sha_name and sha_name != OFFICIAL_UPDATE_SHA_NAME:
                    errors.append('Release 校验文件名仅允许使用官方默认值')
                else:
                    settings_to_update['app_update_release_sha_name'] = OFFICIAL_UPDATE_SHA_NAME

            # 热更新兼容配置（固定）
            if 'app_update_repo_url' in data:
                incoming_repo = str(data.get('app_update_repo_url') or '').strip()
                if incoming_repo and incoming_repo != OFFICIAL_UPDATE_REPO_URL:
                    errors.append('更新仓库仅允许使用官方仓库地址')
                else:
                    settings_to_update['app_update_repo_url'] = OFFICIAL_UPDATE_REPO_URL

            if 'app_update_branch' in data:
                branch = str(data.get('app_update_branch') or '').strip().lower()
                if branch not in ('main', 'master'):
                    errors.append('更新分支仅支持 main 或 master')
                else:
                    settings_to_update['app_update_branch'] = branch

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

                # Bot 运行时关键配置变更后，触发热重启
                restart_sensitive_keys = {
                    'bot_update_mode',
                    'bot_webhook_url',
                    'bot_settoken_ttl_seconds',
                    'bot_template_strict_mode',
                    'proxy_url',
                }
                if restart_sensitive_keys.intersection(settings_to_update.keys()):
                    try:
                        from ..bot_control import request_bot_restart
                        request_bot_restart(reason='system_settings_updated')
                    except Exception as e:
                        logger.debug(f"触发 Bot 热重启失败（可忽略）: {e}")

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
