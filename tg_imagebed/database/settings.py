#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统设置 + 公告管理"""
import json
from typing import Optional, Dict, Any, List

from ..config import logger
from .connection import get_connection


# ===================== 公告管理 =====================
def get_announcement() -> Optional[Dict[str, Any]]:
    """获取当前公告"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, enabled, content, created_at, updated_at
                FROM announcements
                ORDER BY id DESC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取公告失败: {e}")
        return None


def update_announcement(enabled: bool, content: str) -> int:
    """更新公告"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取当前公告
            cursor.execute('SELECT id, content FROM announcements ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()

            content_changed = False
            if result:
                old_content = result['content']
                content_changed = (old_content != content)

            if result and not content_changed:
                # 内容没有变化，只更新启用状态
                announcement_id = result['id']
                cursor.execute('''
                    UPDATE announcements
                    SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (enabled, announcement_id))
            else:
                # 内容有变化或没有公告，创建新公告
                if result:
                    cursor.execute('UPDATE announcements SET enabled = 0')

                cursor.execute('''
                    INSERT INTO announcements (enabled, content)
                    VALUES (?, ?)
                ''', (enabled, content))
                announcement_id = cursor.lastrowid

            return announcement_id

    except Exception as e:
        logger.error(f"更新公告失败: {e}")
        return 0


# ===================== 系统设置管理 =====================
# 敏感配置列表（日志中不打印值）
SENSITIVE_SETTINGS = {
    'storage_config_json', 'storage_upload_policy_json',
    'cloudflare_api_token', 'telegram_bot_token', 'proxy_url'
}

# 默认系统设置
DEFAULT_SYSTEM_SETTINGS = {
    # Telegram Bot 配置
    'telegram_bot_token': '',
    # 游客上传策略
    'guest_upload_policy': 'open',  # open/token_only/admin_only
    'guest_token_generation_enabled': '1',  # 0/1
    'guest_existing_tokens_policy': 'keep',  # keep/disable_guest/disable_all
    'max_file_size_mb': '20',
    'daily_upload_limit': '0',  # 0=无限制
    'guest_token_max_upload_limit': '1000',
    'guest_token_max_expires_days': '365',
    # 存储配置
    'storage_active_backend': 'telegram',
    'storage_config_json': '',
    'storage_upload_policy_json': '',
    # CDN 配置（默认不开启）
    'cdn_enabled': '0',
    'cloudflare_cdn_domain': '',
    'cloudflare_api_token': '',
    'cloudflare_zone_id': '',
    'cloudflare_cache_level': 'aggressive',
    'cloudflare_browser_ttl': '14400',
    'cloudflare_edge_ttl': '2592000',
    'enable_smart_routing': '0',
    'fallback_to_origin': '1',
    'enable_cache_warming': '0',
    'cache_warming_delay': '5',
    'cdn_monitor_enabled': '0',
    'cdn_redirect_enabled': '0',
    'cdn_redirect_max_count': '2',
    'cdn_redirect_delay': '10',
    # 群组上传配置
    'group_upload_admin_only': '0',
    'group_admin_ids': '',
    'group_upload_reply': '1',
    'group_upload_delete_delay': '0',
    # TG 同步删除
    'tg_sync_delete_enabled': '1',
    # Bot 功能开关
    'bot_caption_filename_enabled': '1',    # 允许 caption 自定义文件名
    'bot_inline_buttons_enabled': '1',      # 上传成功后显示 inline 按钮
    'bot_user_delete_enabled': '1',         # 允许用户通过 Bot 删除图片
    'bot_myuploads_enabled': '1',           # 允许用户查看上传历史
    'bot_myuploads_page_size': '8',         # 上传历史每页显示数量
    # 网络代理
    'proxy_url': '',
    # 允许的文件后缀（逗号分隔）
    'allowed_extensions': 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico',
    # TG 认证配置
    'tg_auth_enabled': '0',                  # TG 认证总开关
    'tg_auth_required_for_token': '0',       # 生成 Token 需要 TG 登录
    'tg_max_tokens_per_user': '5',           # 每用户 Token 上限
    'tg_login_code_expire_minutes': '5',     # 验证码/链接有效期
    'tg_session_expire_days': '30',          # TG 会话有效期
    'tg_bind_token_enabled': '0',            # Token 自动绑定 TG 用户
    # 非 TG 用户 Token 限制
    'max_guest_tokens_per_ip': '3',          # 非 TG 用户每 IP Token 上限
    # 群组上传 — TG 绑定限制
    'group_upload_tg_bound_only': '0',       # 仅允许 TG 绑定用户在群组上传
    # 私聊上传配置
    'bot_private_upload_enabled': '1',       # 私聊上传总开关
    'bot_private_upload_mode': 'open',       # open / tg_bound / admin_only
    'bot_private_admin_ids': '',             # 私聊管理员 ID（mode=admin_only 时生效）
    # SEO 配置
    'seo_site_name': '',                    # 网站名称（留空使用默认"图床 Pro"）
    'seo_site_description': '',             # 网站描述（留空使用默认值）
    'seo_site_keywords': '',                # 网站关键词（留空使用默认值）
    'seo_logo_mode': 'icon',                # Logo 模式：icon=默认图标 / custom=自定义图片
    'seo_logo_url': '',                     # 自定义 Logo 图片 URL
    'seo_favicon_url': '',                  # 自定义 Favicon URL
    'seo_og_title': '',                     # OG 标题（留空 fallback 到 site_name）
    'seo_og_description': '',               # OG 描述（留空 fallback 到 description）
    'seo_og_image': '',                     # OG 图片 URL
    'seo_footer_text': '',                  # 自定义页脚文字（留空用默认格式）
}

def init_system_settings() -> None:
    """初始化系统设置（在 admin_config 表中），仅插入默认值"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for key, default_value in DEFAULT_SYSTEM_SETTINGS.items():
                cursor.execute(
                    'SELECT value FROM admin_config WHERE key = ?', (key,)
                )
                existing = cursor.fetchone()

                if not existing:
                    cursor.execute(
                        'INSERT INTO admin_config (key, value) VALUES (?, ?)',
                        (key, default_value)
                    )

                    if key in SENSITIVE_SETTINGS:
                        logger.info(f"初始化系统设置: {key}=[REDACTED]")
                    else:
                        logger.info(f"初始化系统设置: {key}={default_value} (默认值)")
    except Exception as e:
        logger.error(f"初始化系统设置失败: {e}")


def get_system_setting(key: str) -> Optional[str]:
    """获取单个系统设置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM admin_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return DEFAULT_SYSTEM_SETTINGS.get(key)
    except Exception as e:
        logger.error(f"获取系统设置失败 {key}: {e}")
        return DEFAULT_SYSTEM_SETTINGS.get(key)


def get_all_system_settings() -> Dict[str, Any]:
    """获取所有系统设置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            settings = dict(DEFAULT_SYSTEM_SETTINGS)  # 从默认值开始

            for key in DEFAULT_SYSTEM_SETTINGS.keys():
                cursor.execute('SELECT value FROM admin_config WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    settings[key] = row[0]

            return settings
    except Exception as e:
        logger.error(f"获取所有系统设置失败: {e}")
        return dict(DEFAULT_SYSTEM_SETTINGS)


def update_system_setting(key: str, value: str) -> bool:
    """更新单个系统设置"""
    if key not in DEFAULT_SYSTEM_SETTINGS:
        logger.warning(f"尝试更新未知的系统设置: {key}")
        return False

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            if key in SENSITIVE_SETTINGS:
                logger.info(f"更新系统设置: {key}=[REDACTED]")
            else:
                logger.info(f"更新系统设置: {key}={value}")
            return True
    except Exception as e:
        logger.error(f"更新系统设置失败 {key}: {e}")
        return False


def update_system_settings(settings: Dict[str, str]) -> bool:
    """批量更新系统设置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for key, value in settings.items():
                if key in DEFAULT_SYSTEM_SETTINGS:
                    cursor.execute('''
                        INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (key, value))
                    if key in SENSITIVE_SETTINGS:
                        logger.info(f"更新系统设置: {key}=[REDACTED]")
                    else:
                        logger.info(f"更新系统设置: {key}={value}")
            return True
    except Exception as e:
        logger.error(f"批量更新系统设置失败: {e}")
        return False

def _safe_int(value: Any, default: int) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_system_setting_int(
    key: str,
    default: int,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None
) -> int:
    """获取 int 类型系统设置（带容错/范围约束）"""
    value = _safe_int(get_system_setting(key), default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_upload_count_today(*, source: Optional[str] = None, auth_token: Optional[str] = None) -> int:
    """获取今天的上传次数（按 source 或 auth_token 过滤）"""
    if not source and auth_token is None:
        return 0

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            conditions = ["date(created_at) = date('now', 'localtime')"]
            params: List[Any] = []

            if source:
                conditions.append("source = ?")
                params.append(source)
            if auth_token is not None:
                conditions.append("auth_token = ?")
                params.append(auth_token)

            where_clause = " AND ".join(conditions)
            cursor.execute(
                f"SELECT COUNT(*) FROM file_storage WHERE {where_clause}",
                tuple(params)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"获取今日上传次数失败: {e}")
        return 0


def get_public_settings() -> Dict[str, Any]:
    """获取公开的系统设置（供前端使用）"""
    settings = get_all_system_settings()
    return {
        'guest_upload_policy': settings.get('guest_upload_policy', 'open'),
        'guest_token_generation_enabled': settings.get('guest_token_generation_enabled', '1') == '1',
        'max_file_size_mb': max(1, _safe_int(settings.get('max_file_size_mb', '20'), 20)),
        'daily_upload_limit': max(0, _safe_int(settings.get('daily_upload_limit', '0'), 0)),
        'guest_token_max_upload_limit': max(1, _safe_int(settings.get('guest_token_max_upload_limit', '1000'), 1000)),
        'guest_token_max_expires_days': max(1, _safe_int(settings.get('guest_token_max_expires_days', '365'), 365)),
        'allowed_extensions': settings.get('allowed_extensions', 'jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico'),
        'tg_auth_enabled': settings.get('tg_auth_enabled', '0') == '1',
        'tg_auth_required_for_token': settings.get('tg_auth_required_for_token', '0') == '1',
        'tg_bind_token_enabled': settings.get('tg_bind_token_enabled', '0') == '1',
        'tg_sync_delete_enabled': settings.get('tg_sync_delete_enabled', '1') == '1',
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
        'seo_footer_text': settings.get('seo_footer_text', ''),
    }

def is_guest_upload_allowed() -> bool:
    """检查是否允许游客上传（匿名上传）"""
    policy = get_system_setting('guest_upload_policy')
    return policy == 'open'


def is_token_upload_allowed() -> bool:
    """检查是否允许 Token 上传"""
    policy = get_system_setting('guest_upload_policy')
    return policy in ['open', 'token_only']


def is_token_generation_allowed() -> bool:
    """检查是否允许生成新 Token"""
    policy = get_system_setting('guest_upload_policy')
    if policy == 'admin_only':
        return False
    return get_system_setting('guest_token_generation_enabled') == '1'


def disable_guest_tokens() -> int:
    """禁用所有游客 Token"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 禁用所有以 'guest_' 开头的 Token
            cursor.execute('''
                UPDATE auth_tokens
                SET is_active = 0
                WHERE token LIKE 'guest_%' AND is_active = 1
            ''')
            count = cursor.rowcount
            logger.info(f"已禁用 {count} 个游客 Token")
            return count
    except Exception as e:
        logger.error(f"禁用游客 Token 失败: {e}")
        return 0


def disable_all_tokens() -> int:
    """禁用所有 Token"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE auth_tokens SET is_active = 0 WHERE is_active = 1')
            count = cursor.rowcount
            logger.info(f"已禁用 {count} 个 Token")
            return count
    except Exception as e:
        logger.error(f"禁用所有 Token 失败: {e}")
        return 0
