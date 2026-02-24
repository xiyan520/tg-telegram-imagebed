#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据访问层模块 - 包结构重导出

所有公开函数通过此文件重导出，外部 import 零改动：
    from tg_imagebed.database import init_database, get_file_info, ...
"""

# 连接管理 + 初始化
from .connection import get_connection, db_retry, init_database

# 文件 CRUD + 统计
from .files import (
    get_file_info, save_file_info, update_file_path_in_db,
    update_cdn_cache_status, update_access_count, delete_files_by_ids,
    get_all_files_count, get_total_size, get_stats,
    get_recent_uploads, get_uncached_files, get_cdn_dashboard_stats,
    get_user_uploads,
)

# Token 管理（用户 + 管理员）
from .tokens import (
    generate_auth_token, create_auth_token, verify_auth_token,
    verify_auth_token_access, update_token_description,
    update_token_usage, get_token_info, get_token_uploads,
    admin_list_tokens, admin_create_token,
    admin_update_token_status, admin_update_token, admin_delete_token,
    admin_get_token_detail, admin_get_token_uploads, admin_get_token_galleries,
    delete_token_by_string, count_tokens_by_ip,
)

# 系统设置 + 公告
from .settings import (
    get_announcement, update_announcement,
    init_system_settings,
    get_system_setting, get_all_system_settings,
    update_system_setting, update_system_settings,
    get_system_setting_int, get_upload_count_today,
    get_public_settings,
    is_guest_upload_allowed, is_token_upload_allowed, is_token_generation_allowed,
    disable_guest_tokens, disable_all_tokens,
    DEFAULT_SYSTEM_SETTINGS, SENSITIVE_SETTINGS,
)

# 画集管理
from .galleries import (
    create_gallery, get_gallery, list_galleries, update_gallery, delete_gallery,
    set_gallery_cover,
    add_images_to_gallery, remove_images_from_gallery, get_gallery_images,
    update_gallery_share, get_shared_gallery,
    update_gallery_access, verify_gallery_password,
    grant_gallery_token_access, revoke_gallery_token_access,
    list_gallery_token_access, is_token_authorized_for_gallery, is_gallery_owner,
    get_share_all_link, create_or_update_share_all_link, get_share_all_galleries,
    get_share_all_gallery, get_share_all_gallery_images,
)

# 管理员画集
from .admin_galleries import (
    admin_create_gallery, admin_get_gallery, admin_list_galleries,
    admin_update_gallery, admin_delete_gallery, admin_set_gallery_cover,
    admin_add_images_to_gallery, admin_remove_images_from_gallery,
    admin_get_gallery_images, admin_update_gallery_share,
)

# TG 认证
from .tg_auth import (
    upsert_tg_user, get_tg_user, get_tg_user_by_username,
    create_login_code, verify_login_code,
    create_tg_session, verify_tg_session, delete_tg_session,
    has_bound_tokens, get_user_token_count, get_user_tokens,
    bind_token_to_user, unbind_token_from_user,
    get_active_user_tokens, get_default_upload_token, set_default_upload_token,
    cleanup_expired_codes, cleanup_expired_sessions,
    consume_web_verify_code, get_web_verify_status,
)

__all__ = [
    # 连接管理
    'get_connection', 'db_retry',
    # 初始化
    'init_database',
    # 文件操作
    'get_file_info', 'save_file_info', 'update_file_path_in_db',
    'update_cdn_cache_status', 'update_access_count', 'delete_files_by_ids',
    # 统计（admin_module.py 兼容）
    'get_all_files_count', 'get_total_size', 'get_stats',
    'get_recent_uploads', 'get_uncached_files', 'get_cdn_dashboard_stats',
    'get_user_uploads',
    # Token
    'generate_auth_token', 'create_auth_token', 'verify_auth_token',
    'verify_auth_token_access', 'update_token_description',
    'update_token_usage', 'get_token_info', 'get_token_uploads',
    # Token 管理（管理员后台）
    'admin_list_tokens', 'admin_create_token',
    'admin_update_token_status', 'admin_update_token', 'admin_delete_token',
    'admin_get_token_detail', 'admin_get_token_uploads', 'admin_get_token_galleries',
    'delete_token_by_string',
    # 公告
    'get_announcement', 'update_announcement',
    # 系统设置
    'init_system_settings', 'get_system_setting', 'get_all_system_settings',
    'update_system_setting', 'update_system_settings', 'get_public_settings',
    'get_system_setting_int', 'get_upload_count_today',
    'is_guest_upload_allowed', 'is_token_upload_allowed', 'is_token_generation_allowed',
    'disable_guest_tokens', 'disable_all_tokens',
    'DEFAULT_SYSTEM_SETTINGS', 'SENSITIVE_SETTINGS',
    # 画集管理
    'create_gallery', 'get_gallery', 'list_galleries', 'update_gallery', 'delete_gallery',
    'set_gallery_cover',
    'add_images_to_gallery', 'remove_images_from_gallery', 'get_gallery_images',
    'update_gallery_share', 'get_shared_gallery',
    # 画集访问控制
    'update_gallery_access', 'verify_gallery_password',
    # 画集 Token 授权
    'grant_gallery_token_access', 'revoke_gallery_token_access',
    'list_gallery_token_access', 'is_token_authorized_for_gallery', 'is_gallery_owner',
    # 全部分享链接
    'get_share_all_link', 'create_or_update_share_all_link', 'get_share_all_galleries',
    'get_share_all_gallery', 'get_share_all_gallery_images',
    # 管理员画集
    'admin_create_gallery', 'admin_get_gallery', 'admin_list_galleries',
    'admin_update_gallery', 'admin_delete_gallery', 'admin_set_gallery_cover',
    'admin_add_images_to_gallery', 'admin_remove_images_from_gallery',
    'admin_get_gallery_images', 'admin_update_gallery_share',
    # TG 认证
    'upsert_tg_user', 'get_tg_user', 'get_tg_user_by_username',
    'create_login_code', 'verify_login_code',
    'create_tg_session', 'verify_tg_session', 'delete_tg_session',
    'has_bound_tokens', 'get_user_token_count', 'get_user_tokens',
    'bind_token_to_user', 'unbind_token_from_user',
    'get_active_user_tokens', 'get_default_upload_token', 'set_default_upload_token',
    'cleanup_expired_codes', 'cleanup_expired_sessions',
    'consume_web_verify_code', 'get_web_verify_status',
]
