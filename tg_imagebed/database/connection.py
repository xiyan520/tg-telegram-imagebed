#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库连接管理 + 初始化"""
import sqlite3
import time
import random
import json
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

from ..config import DATABASE_PATH, logger


# ===================== 数据库连接管理 =====================
@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_retry(max_attempts: int = 3, base_delay: float = 0.1, max_delay: float = 2.0):
    """SQLite操作重试装饰器，处理数据库锁定等瞬态错误"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    err_msg = str(e).lower()
                    if 'locked' in err_msg or 'busy' in err_msg:
                        last_error = e
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay *= random.uniform(0.8, 1.2)
                        logger.debug(f"DB locked, retry {attempt + 1}/{max_attempts} after {delay:.2f}s")
                        time.sleep(delay)
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


# ===================== 数据库初始化 =====================
def init_database(quiet: bool = False) -> None:
    """初始化数据库 - 创建所有必要的表和索引"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 创建主表 file_storage
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_storage (
                    encrypted_id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    upload_time INTEGER NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    file_size INTEGER,
                    source TEXT,
                    original_filename TEXT,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    etag TEXT,
                    file_hash TEXT,
                    cdn_url TEXT,
                    cdn_cached BOOLEAN DEFAULT 0,
                    cdn_cache_time TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    cdn_hit_count INTEGER DEFAULT 0,
                    direct_hit_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    last_file_path_update TIMESTAMP,
                    is_group_upload BOOLEAN DEFAULT 0,
                    group_message_id INTEGER,
                    group_chat_id INTEGER,
                    auth_token TEXT,
                    storage_backend TEXT,
                    storage_key TEXT,
                    storage_meta TEXT
                )
            ''')

            # 创建 auth_tokens 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used TIMESTAMP,
                    upload_count INTEGER DEFAULT 0,
                    upload_limit INTEGER DEFAULT 100,
                    is_active BOOLEAN DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    description TEXT
                )
            ''')

            # 创建公告表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled BOOLEAN DEFAULT 1,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 插入默认公告（如果表为空）
            cursor.execute('SELECT COUNT(*) FROM announcements')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO announcements (enabled, content) VALUES (?, ?)
                ''', (1, '''
                    <div class="space-y-4">
                        <h3 class="text-xl font-bold text-gray-900 dark:text-white">欢迎使用 Telegram 云图床</h3>
                        <div class="space-y-2 text-gray-700 dark:text-gray-300">
                            <p>🎉 <strong>无限制使用：</strong>无上传数量限制，无时间限制</p>
                            <p>🚀 <strong>CDN加速：</strong>全球CDN加速，访问更快</p>
                            <p>🔒 <strong>安全可靠：</strong>基于Telegram云存储，永久保存</p>
                            <p>💎 <strong>Token模式：</strong>生成专属Token，管理您的图片</p>
                        </div>
                    </div>
                '''))

            # 创建管理员配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 检查并添加新列（用于升级现有数据库）
            cursor.execute("PRAGMA table_info(file_storage)")
            columns = [column[1] for column in cursor.fetchall()]

            new_columns = [
                ('is_group_upload', 'BOOLEAN DEFAULT 0'),
                ('group_message_id', 'INTEGER'),
                ('group_chat_id', 'INTEGER'),
                ('last_file_path_update', 'TIMESTAMP'),
                ('etag', 'TEXT'),
                ('file_hash', 'TEXT'),
                ('cdn_url', 'TEXT'),
                ('cdn_cached', 'BOOLEAN DEFAULT 0'),
                ('cdn_cache_time', 'TIMESTAMP'),
                ('access_count', 'INTEGER DEFAULT 0'),
                ('cdn_hit_count', 'INTEGER DEFAULT 0'),
                ('direct_hit_count', 'INTEGER DEFAULT 0'),
                ('last_accessed', 'TIMESTAMP'),
                ('auth_token', 'TEXT'),
                ('storage_backend', 'TEXT'),
                ('storage_key', 'TEXT'),
                ('storage_meta', 'TEXT'),
            ]

            # 记录是否新增了 storage 相关列
            storage_columns_added = False
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    logger.info(f"添加 {col_name} 列到 file_storage")
                    cursor.execute(f'ALTER TABLE file_storage ADD COLUMN {col_name} {col_type}')
                    if col_name in ('storage_backend', 'storage_key', 'storage_meta'):
                        storage_columns_added = True

            # 兼容历史数据：只在新增 storage 列时回填，避免每次启动全表扫描
            if storage_columns_added:
                try:
                    cursor.execute("""
                        UPDATE file_storage
                        SET storage_backend = 'telegram'
                        WHERE storage_backend IS NULL OR storage_backend = ''
                    """)
                    cursor.execute("""
                        UPDATE file_storage
                        SET storage_key = file_id
                        WHERE (storage_key IS NULL OR storage_key = '')
                          AND file_id IS NOT NULL AND file_id != ''
                    """)
                    logger.info("已回填历史记录的 storage 字段")
                except Exception as e:
                    logger.debug(f"回填 storage 字段失败（可忽略）: {e}")

            # ===================== TG 认证相关表 =====================
            # TG 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tg_users (
                    tg_user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    is_blocked INTEGER DEFAULT 0
                )
            ''')

            # TG 登录验证码/链接表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tg_login_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER,
                    code TEXT NOT NULL UNIQUE,
                    code_type TEXT NOT NULL DEFAULT 'verify',
                    username_hint TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP,
                    ip_address TEXT,
                    session_token TEXT
                )
            ''')

            # 兼容升级：tg_login_codes 新增 session_token 列
            cursor.execute("PRAGMA table_info(tg_login_codes)")
            tg_code_columns = [col[1] for col in cursor.fetchall()]
            if 'session_token' not in tg_code_columns:
                logger.info("添加 session_token 列到 tg_login_codes")
                cursor.execute('ALTER TABLE tg_login_codes ADD COLUMN session_token TEXT')

            # TG 会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tg_sessions (
                    session_token TEXT PRIMARY KEY,
                    tg_user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (tg_user_id) REFERENCES tg_users(tg_user_id) ON DELETE CASCADE
                )
            ''')

            # 检查并添加 auth_tokens 表的新列
            cursor.execute("PRAGMA table_info(auth_tokens)")
            auth_columns = [column[1] for column in cursor.fetchall()]

            # 兼容历史数据库：老版本的 auth_tokens 可能缺少这些列
            auth_new_columns = [
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('expires_at', 'TIMESTAMP'),
                ('last_used', 'TIMESTAMP'),
                ('upload_count', 'INTEGER DEFAULT 0'),
                ('upload_limit', 'INTEGER DEFAULT 100'),
                ('is_active', 'BOOLEAN DEFAULT 1'),
                ('ip_address', 'TEXT'),
                ('user_agent', 'TEXT'),
                ('description', 'TEXT'),
                ('tg_user_id', 'INTEGER'),
                ('is_default_upload', 'BOOLEAN DEFAULT 0'),
            ]

            for col_name, col_type in auth_new_columns:
                if col_name not in auth_columns:
                    logger.info(f"添加 {col_name} 列到 auth_tokens")
                    cursor.execute(f'ALTER TABLE auth_tokens ADD COLUMN {col_name} {col_type}')
                    auth_columns.append(col_name)

            # 为历史记录回填默认值，避免 NULL 导致排序/展示异常
            try:
                cursor.execute("UPDATE auth_tokens SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                cursor.execute("UPDATE auth_tokens SET upload_count = 0 WHERE upload_count IS NULL")
                cursor.execute("UPDATE auth_tokens SET upload_limit = 100 WHERE upload_limit IS NULL")
                cursor.execute("UPDATE auth_tokens SET is_active = 1 WHERE is_active IS NULL")
            except Exception as e:
                logger.debug(f"回填 auth_tokens 字段失败（可忽略）: {e}")

            # 创建画集表（owner_type 区分管理员/用户画集，无 FK 约束）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS galleries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_type TEXT NOT NULL DEFAULT 'token',
                    owner_token TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    share_enabled INTEGER DEFAULT 0,
                    share_token TEXT UNIQUE,
                    share_expires_at TIMESTAMP
                )
            ''')

            # 创建画集-图片关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gallery_images (
                    gallery_id INTEGER NOT NULL,
                    encrypted_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (gallery_id, encrypted_id),
                    FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
                    FOREIGN KEY (encrypted_id) REFERENCES file_storage(encrypted_id) ON DELETE CASCADE
                )
            ''')

            # 创建全部分享链接表（管理员专属）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS share_all_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    share_token TEXT NOT NULL UNIQUE,
                    enabled INTEGER DEFAULT 1,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建画集 Token 授权表（用于 token 访问模式）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gallery_token_access (
                    gallery_id INTEGER NOT NULL,
                    token TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (gallery_id, token),
                    FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
                    FOREIGN KEY (token) REFERENCES auth_tokens(token) ON DELETE CASCADE
                )
            ''')

            # 迁移：为 galleries 表添加访问控制字段
            cursor.execute("PRAGMA table_info(galleries)")
            gallery_columns = [col[1] for col in cursor.fetchall()]

            # 迁移：owner_type 重建表（移除 FK，新增 owner_type 列）
            if 'owner_type' not in gallery_columns:
                logger.info("迁移 galleries 表：新增 owner_type 列，移除 FK 约束")
                # 关闭 FK 约束，避免 RENAME 时 SQLite 将关联表的 FK 改指向旧表名
                conn.commit()
                cursor.execute('PRAGMA foreign_keys = OFF')

                # 读取 admin_gallery_owner_token 配置
                admin_token = None
                try:
                    cursor.execute("SELECT value FROM admin_config WHERE key = 'admin_gallery_owner_token'")
                    row = cursor.fetchone()
                    if row and row[0]:
                        admin_token = str(row[0]).strip()
                except Exception:
                    pass

                cursor.execute('ALTER TABLE galleries RENAME TO galleries_old')
                cursor.execute('''
                    CREATE TABLE galleries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_type TEXT NOT NULL DEFAULT 'token',
                        owner_token TEXT,
                        name TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        share_enabled INTEGER DEFAULT 0,
                        share_token TEXT UNIQUE,
                        share_expires_at TIMESTAMP
                    )
                ''')
                # 迁移数据：admin token 的行设 owner_type='admin', owner_token=NULL
                if admin_token:
                    cursor.execute('''
                        INSERT INTO galleries (id, owner_type, owner_token, name, description,
                            created_at, updated_at, share_enabled, share_token, share_expires_at)
                        SELECT id,
                            CASE WHEN owner_token = ? THEN 'admin' ELSE 'token' END,
                            CASE WHEN owner_token = ? THEN NULL ELSE owner_token END,
                            name, description, created_at, updated_at,
                            share_enabled, share_token, share_expires_at
                        FROM galleries_old
                    ''', (admin_token, admin_token))
                else:
                    cursor.execute('''
                        INSERT INTO galleries (id, owner_type, owner_token, name, description,
                            created_at, updated_at, share_enabled, share_token, share_expires_at)
                        SELECT id, 'token', owner_token, name, description,
                            created_at, updated_at, share_enabled, share_token, share_expires_at
                        FROM galleries_old
                    ''')
                cursor.execute('DROP TABLE galleries_old')

                # 清理虚拟 token 和配置项
                if admin_token:
                    cursor.execute("DELETE FROM auth_tokens WHERE token = ? AND description = 'internal_admin_gallery_owner'", (admin_token,))
                    cursor.execute("DELETE FROM admin_config WHERE key = 'admin_gallery_owner_token'")
                    logger.info("已清理虚拟 admin gallery owner token")

                # 恢复 FK 约束
                conn.commit()
                cursor.execute('PRAGMA foreign_keys = ON')

                # 重新读取列信息
                cursor.execute("PRAGMA table_info(galleries)")
                gallery_columns = [col[1] for col in cursor.fetchall()]

            # 修复迁移遗留：gallery_images / gallery_token_access 的 FK 可能仍指向 galleries_old
            for tbl_name, create_sql in [
                ('gallery_images', '''
                    CREATE TABLE gallery_images (
                        gallery_id INTEGER NOT NULL,
                        encrypted_id TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (gallery_id, encrypted_id),
                        FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
                        FOREIGN KEY (encrypted_id) REFERENCES file_storage(encrypted_id) ON DELETE CASCADE
                    )
                '''),
                ('gallery_token_access', '''
                    CREATE TABLE gallery_token_access (
                        gallery_id INTEGER NOT NULL,
                        token TEXT NOT NULL,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (gallery_id, token),
                        FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE,
                        FOREIGN KEY (token) REFERENCES auth_tokens(token) ON DELETE CASCADE
                    )
                '''),
            ]:
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tbl_name}'")
                row = cursor.fetchone()
                if row and 'galleries_old' in (row[0] or ''):
                    logger.info(f"修复 {tbl_name} 表：FK 仍指向 galleries_old，重建表")
                    conn.commit()
                    cursor.execute('PRAGMA foreign_keys = OFF')
                    cursor.execute(f'ALTER TABLE {tbl_name} RENAME TO {tbl_name}_broken')
                    cursor.execute(create_sql)
                    cursor.execute(f'INSERT INTO {tbl_name} SELECT * FROM {tbl_name}_broken')
                    cursor.execute(f'DROP TABLE {tbl_name}_broken')
                    conn.commit()
                    cursor.execute('PRAGMA foreign_keys = ON')

            gallery_new_columns = [
                ('access_mode', "TEXT DEFAULT 'public'"),
                ('password_hash', 'TEXT'),
                ('hide_from_share_all', 'INTEGER DEFAULT 0'),
                ('cover_image', 'TEXT'),  # 手动设置的封面图（encrypted_id）
            ]
            for col_name, col_type in gallery_new_columns:
                if col_name not in gallery_columns:
                    logger.info(f"添加 {col_name} 列到 galleries")
                    cursor.execute(f'ALTER TABLE galleries ADD COLUMN {col_name} {col_type}')

            # ===================== 自定义域名表 =====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    domain_type TEXT NOT NULL DEFAULT 'image',
                    use_https INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    is_default INTEGER DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    remark TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 迁移：将旧 cloudflare_cdn_domain 迁移到 custom_domains 表
            try:
                cursor.execute("SELECT COUNT(*) FROM custom_domains")
                domain_count = cursor.fetchone()[0]
                if domain_count == 0:
                    cursor.execute("SELECT value FROM admin_config WHERE key = 'cloudflare_cdn_domain'")
                    cdn_row = cursor.fetchone()
                    if cdn_row and cdn_row[0] and str(cdn_row[0]).strip():
                        old_domain = str(cdn_row[0]).strip()
                        cursor.execute('''
                            INSERT INTO custom_domains (domain, domain_type, use_https, is_active, is_default, remark)
                            VALUES (?, 'image', 1, 1, 1, '从 CDN 配置自动迁移')
                        ''', (old_domain,))
                        logger.info(f"已将旧 CDN 域名迁移到 custom_domains: {old_domain}")
            except Exception as e:
                logger.debug(f"域名迁移检查失败（可忽略）: {e}")

            # 创建索引
            indexes = [
                ('idx_file_storage_created', 'file_storage(created_at)'),
                ('idx_original_filename', 'file_storage(original_filename)'),
                ('idx_file_size', 'file_storage(file_size)'),
                ('idx_cdn_cached', 'file_storage(cdn_cached)'),
                ('idx_group_upload', 'file_storage(is_group_upload)'),
                ('idx_auth_token', 'file_storage(auth_token)'),
                ('idx_storage_backend', 'file_storage(storage_backend)'),
                ('idx_storage_key', 'file_storage(storage_backend, storage_key)'),
                ('idx_auth_tokens_expires', 'auth_tokens(expires_at)'),
                ('idx_auth_tokens_active', 'auth_tokens(is_active)'),
                ('idx_galleries_owner', 'galleries(owner_token)'),
                ('idx_galleries_owner_type', 'galleries(owner_type)'),
                ('idx_galleries_share_token', 'galleries(share_token)'),
                ('idx_galleries_access_mode', 'galleries(access_mode)'),
                ('idx_galleries_hide_share_all', 'galleries(hide_from_share_all)'),
                ('idx_gallery_images_gallery', 'gallery_images(gallery_id, added_at DESC)'),
                ('idx_share_all_token', 'share_all_links(share_token)'),
                ('idx_gallery_token_access_gallery', 'gallery_token_access(gallery_id)'),
                ('idx_gallery_token_access_token', 'gallery_token_access(token)'),
                ('idx_gallery_token_access_expires', 'gallery_token_access(expires_at)'),
                # TG 认证相关索引
                ('idx_tg_login_codes_code', 'tg_login_codes(code)'),
                ('idx_tg_login_codes_expires', 'tg_login_codes(expires_at)'),
                ('idx_tg_sessions_expires', 'tg_sessions(expires_at)'),
                ('idx_tg_sessions_user', 'tg_sessions(tg_user_id)'),
                ('idx_auth_tokens_tg_user', 'auth_tokens(tg_user_id)'),
                # 自定义域名相关索引
                ('idx_custom_domains_domain', 'custom_domains(domain)'),
                ('idx_custom_domains_type', 'custom_domains(domain_type)'),
                ('idx_custom_domains_active', 'custom_domains(is_active)'),
                ('idx_custom_domains_default', 'custom_domains(is_default)'),
                ('idx_custom_domains_sort', 'custom_domains(sort_order)'),
            ]

            for idx_name, idx_def in indexes:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')

        if not quiet:
            logger.info(f"数据库初始化完成: {DATABASE_PATH}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
