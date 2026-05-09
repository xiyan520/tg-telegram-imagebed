#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库连接管理 + 初始化"""
import sqlite3
import time
import random
import json
import secrets
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


# ===================== 数据库初始化子函数 =====================

def _init_core_tables(cursor) -> None:
    """创建核心表：file_storage、auth_tokens、announcements、admin_config"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_storage (
            encrypted_id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_time INTEGER NOT NULL,
            user_id INTEGER,
            tg_user_id INTEGER,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_reservations (
            reservation_key TEXT PRIMARY KEY,
            auth_token TEXT,
            source TEXT,
            created_day TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')


def _migrate_file_storage_columns(cursor) -> None:
    """file_storage 表列迁移（增量 ALTER TABLE）"""
    cursor.execute("PRAGMA table_info(file_storage)")
    columns = [column[1] for column in cursor.fetchall()]

    new_columns = [
        ('is_group_upload', 'BOOLEAN DEFAULT 0'),
        ('group_message_id', 'INTEGER'),
        ('group_chat_id', 'INTEGER'),
        ('tg_user_id', 'INTEGER'),
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


def _init_tg_auth_tables(cursor) -> None:
    """创建 TG 认证相关表：tg_users、tg_login_codes、tg_sessions"""
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tg_sessions (
            session_token TEXT PRIMARY KEY,
            session_id TEXT UNIQUE,
            tg_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'active',
            revoked_at TIMESTAMP,
            revoke_reason TEXT,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (tg_user_id) REFERENCES tg_users(tg_user_id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tg_session_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token TEXT NOT NULL UNIQUE,
            device_id TEXT,
            device_name TEXT,
            platform TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP,
            revoked_at TIMESTAMP,
            revoke_reason TEXT,
            FOREIGN KEY (session_token) REFERENCES tg_sessions(session_token) ON DELETE CASCADE
        )
    ''')

    # 兼容升级：为 tg_sessions 增加会话管理字段
    cursor.execute("PRAGMA table_info(tg_sessions)")
    tg_session_columns = [col[1] for col in cursor.fetchall()]
    tg_session_new_columns = [
        ('session_id', 'TEXT'),
        ('last_seen_at', 'TIMESTAMP'),
        ('status', "TEXT NOT NULL DEFAULT 'active'"),
        ('revoked_at', 'TIMESTAMP'),
        ('revoke_reason', 'TEXT'),
    ]
    for col_name, col_type in tg_session_new_columns:
        if col_name not in tg_session_columns:
            logger.info(f"添加 {col_name} 列到 tg_sessions")
            cursor.execute(f'ALTER TABLE tg_sessions ADD COLUMN {col_name} {col_type}')
            tg_session_columns.append(col_name)

    # 回填历史会话字段
    try:
        cursor.execute("UPDATE tg_sessions SET status = 'active' WHERE status IS NULL OR status = ''")
        cursor.execute("UPDATE tg_sessions SET last_seen_at = created_at WHERE last_seen_at IS NULL")
        cursor.execute("SELECT session_token FROM tg_sessions WHERE session_id IS NULL OR session_id = ''")
        rows = cursor.fetchall()
        for row in rows:
            cursor.execute(
                "UPDATE tg_sessions SET session_id = ? WHERE session_token = ?",
                (secrets.token_urlsafe(12), row['session_token'])
            )
    except Exception as e:
        logger.debug(f"回填 tg_sessions 字段失败（可忽略）: {e}")


def _migrate_auth_tokens_columns(cursor) -> None:
    """auth_tokens 表列迁移（增量 ALTER TABLE）"""
    cursor.execute("PRAGMA table_info(auth_tokens)")
    auth_columns = [column[1] for column in cursor.fetchall()]
    upload_limit_added = False

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
            if col_name == 'upload_limit':
                upload_limit_added = True

    # 为历史记录回填默认值，避免 NULL 导致排序/展示异常
    try:
        cursor.execute("UPDATE auth_tokens SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        cursor.execute("UPDATE auth_tokens SET upload_count = 0 WHERE upload_count IS NULL")
        cursor.execute("UPDATE auth_tokens SET upload_limit = 100 WHERE upload_limit IS NULL")
        cursor.execute("UPDATE auth_tokens SET is_active = 1 WHERE is_active IS NULL")
    except Exception as e:
        logger.debug(f"回填 auth_tokens 字段失败（可忽略）: {e}")


def _init_gallery_tables(cursor) -> None:
    """创建画集相关表：galleries、gallery_images、share_all_links、gallery_token_access"""
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


def _init_gallery_home_tables(cursor) -> None:
    """创建首页编排相关表并初始化默认配置"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery_home_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            hero_mode TEXT NOT NULL DEFAULT 'auto',
            hero_gallery_id INTEGER,
            mobile_items_per_section INTEGER NOT NULL DEFAULT 4,
            desktop_items_per_section INTEGER NOT NULL DEFAULT 8,
            enable_recent_strip INTEGER NOT NULL DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hero_gallery_id) REFERENCES galleries(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery_home_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT DEFAULT '',
            description TEXT DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            max_items INTEGER NOT NULL DEFAULT 8,
            source_mode TEXT NOT NULL DEFAULT 'hybrid',
            auto_sort TEXT NOT NULL DEFAULT 'updated_desc',
            auto_window_days INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery_home_section_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            gallery_id INTEGER NOT NULL,
            pin_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (section_id, gallery_id),
            FOREIGN KEY (section_id) REFERENCES gallery_home_sections(id) ON DELETE CASCADE,
            FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        INSERT OR IGNORE INTO gallery_home_config (
            id, hero_mode, hero_gallery_id, mobile_items_per_section,
            desktop_items_per_section, enable_recent_strip
        ) VALUES (1, 'auto', NULL, 4, 8, 1)
    ''')

    default_sections = [
        ('featured', '编辑精选', 'Editors Pick', '先看最有代表性的画集，快速建立站点内容风格。', 1, 8, 1, 'hybrid', 'editor_pick_desc', 0),
        ('category', '分区浏览', 'Curated Sections', '按更新节奏、内容体量和策展推荐拆分，浏览效率和沉浸感两边都不掉。', 2, 8, 1, 'hybrid', 'updated_desc', 0),
        ('high-volume', '高内容量', 'High Volume', '优先展示图片量更高、更适合深度浏览的画集。', 3, 10, 1, 'hybrid', 'image_count_desc', 0),
    ]
    for section in default_sections:
        cursor.execute('''
            INSERT OR IGNORE INTO gallery_home_sections (
                section_key, title, subtitle, description, display_order,
                max_items, enabled, source_mode, auto_sort, auto_window_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', section)


def _migrate_galleries_table(cursor, conn) -> list:
    """
    galleries 表迁移：
    1. 新增 owner_type 列（重建表）
    2. 修复关联表 FK 指向
    3. 新增访问控制列

    Returns:
        gallery_columns: 迁移后的列名列表
    """
    cursor.execute("PRAGMA table_info(galleries)")
    gallery_columns = [col[1] for col in cursor.fetchall()]

    # 迁移：owner_type 重建表（移除 FK，新增 owner_type 列）
    if 'owner_type' not in gallery_columns:
        logger.info("迁移 galleries 表：新增 owner_type 列，移除 FK 约束")
        conn.commit()
        cursor.execute('PRAGMA foreign_keys = OFF')

        try:
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

            if admin_token:
                cursor.execute(
                    "DELETE FROM auth_tokens WHERE token = ? AND description = 'internal_admin_gallery_owner'",
                    (admin_token,)
                )
                cursor.execute("DELETE FROM admin_config WHERE key = 'admin_gallery_owner_token'")
                logger.info("已清理虚拟 admin gallery owner token")

            conn.commit()
        finally:
            cursor.execute('PRAGMA foreign_keys = ON')

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
            try:
                cursor.execute(f'ALTER TABLE {tbl_name} RENAME TO {tbl_name}_broken')
                cursor.execute(create_sql)
                cursor.execute(f'INSERT INTO {tbl_name} SELECT * FROM {tbl_name}_broken')
                cursor.execute(f'DROP TABLE {tbl_name}_broken')
                conn.commit()
            finally:
                cursor.execute('PRAGMA foreign_keys = ON')

    # 新增访问控制列 + 显示设置列
    gallery_new_columns = [
        ('access_mode', "TEXT DEFAULT 'public'"),
        ('password_hash', 'TEXT'),
        ('hide_from_share_all', 'INTEGER DEFAULT 0'),
        ('cover_image', 'TEXT'),
        # 显示设置字段
        ('layout_mode', "TEXT DEFAULT 'masonry'"),
        ('theme_color', "TEXT DEFAULT ''"),
        ('show_image_info', 'INTEGER DEFAULT 1'),
        ('allow_download', 'INTEGER DEFAULT 1'),
        ('sort_order', "TEXT DEFAULT 'newest'"),
        ('nsfw_warning', 'INTEGER DEFAULT 0'),
        ('custom_header_text', "TEXT DEFAULT ''"),
        # 首页与 SEO 展示增强
        ('editor_pick_weight', 'INTEGER DEFAULT 0'),
        ('homepage_expose_enabled', 'INTEGER DEFAULT 1'),
        ('card_subtitle', "TEXT DEFAULT ''"),
        ('seo_title', "TEXT DEFAULT ''"),
        ('seo_description', "TEXT DEFAULT ''"),
        ('seo_keywords', "TEXT DEFAULT ''"),
        ('og_image_encrypted_id', 'TEXT'),
    ]
    for col_name, col_type in gallery_new_columns:
        if col_name not in gallery_columns:
            logger.info(f"添加 {col_name} 列到 galleries")
            cursor.execute(f'ALTER TABLE galleries ADD COLUMN {col_name} {col_type}')

    return gallery_columns


def _init_custom_domains_table(cursor, quiet: bool = False) -> None:
    """创建并迁移自定义域名表"""
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

    # 迁移：为 custom_domains 添加 port 列
    cursor.execute("PRAGMA table_info(custom_domains)")
    cd_columns = {row[1] for row in cursor.fetchall()}
    if 'port' not in cd_columns:
        logger.info("添加 port 列到 custom_domains")
        cursor.execute('ALTER TABLE custom_domains ADD COLUMN port INTEGER')

    # 迁移：标准化已有域名记录（转小写），并拆分端口到 port 列
    try:
        cursor.execute("SELECT id, domain, port FROM custom_domains")
        for row in cursor.fetchall():
            old_val = row[1] or ''
            old_port = row[2]
            raw = old_val.strip().lower()
            extracted_port = None
            if ':' in raw:
                parts = raw.split(':', 1)
                raw = parts[0]
                try:
                    extracted_port = int(parts[1])
                except (ValueError, IndexError):
                    pass
            new_port = old_port if old_port is not None else extracted_port
            if raw and (raw != old_val or new_port != old_port):
                cursor.execute(
                    'UPDATE custom_domains SET domain = ?, port = ? WHERE id = ?',
                    (raw, new_port, row[0])
                )
                if not quiet:
                    logger.info(f"标准化域名: {old_val} -> {raw}, port={new_port}")
    except Exception as e:
        logger.debug(f"域名标准化迁移失败（可忽略）: {e}")


def _create_indexes(cursor) -> None:
    """创建所有数据库索引"""
    indexes = [
        ('idx_file_storage_created', 'file_storage(created_at)'),
        ('idx_original_filename', 'file_storage(original_filename)'),
        ('idx_file_size', 'file_storage(file_size)'),
        ('idx_cdn_cached', 'file_storage(cdn_cached)'),
        ('idx_group_upload', 'file_storage(is_group_upload)'),
        ('idx_file_storage_tg_user', 'file_storage(tg_user_id)'),
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
        ('idx_galleries_homepage_expose', 'galleries(homepage_expose_enabled)'),
        ('idx_galleries_editor_pick', 'galleries(editor_pick_weight DESC, updated_at DESC)'),
        ('idx_gallery_images_gallery', 'gallery_images(gallery_id, added_at DESC)'),
        ('idx_share_all_token', 'share_all_links(share_token)'),
        ('idx_gallery_token_access_gallery', 'gallery_token_access(gallery_id)'),
        ('idx_gallery_token_access_token', 'gallery_token_access(token)'),
        ('idx_gallery_token_access_expires', 'gallery_token_access(expires_at)'),
        ('idx_gallery_home_sections_order', 'gallery_home_sections(display_order, id)'),
        ('idx_gallery_home_items_section_order', 'gallery_home_section_items(section_id, pin_order, id)'),
        ('idx_gallery_home_items_gallery', 'gallery_home_section_items(gallery_id)'),
        ('idx_tg_login_codes_code', 'tg_login_codes(code)'),
        ('idx_tg_login_codes_expires', 'tg_login_codes(expires_at)'),
        ('idx_tg_sessions_expires', 'tg_sessions(expires_at)'),
        ('idx_tg_sessions_user', 'tg_sessions(tg_user_id)'),
        ('idx_tg_sessions_status', 'tg_sessions(status)'),
        ('idx_tg_sessions_user_status', 'tg_sessions(tg_user_id, status, expires_at)'),
        ('idx_tg_sessions_last_seen', 'tg_sessions(last_seen_at)'),
        ('idx_tg_sessions_session_id', 'tg_sessions(session_id)'),
        ('idx_tg_session_devices_token', 'tg_session_devices(session_token)'),
        ('idx_tg_session_devices_device_id', 'tg_session_devices(device_id)'),
        ('idx_tg_session_devices_last_seen', 'tg_session_devices(last_seen_at)'),
        ('idx_auth_tokens_tg_user', 'auth_tokens(tg_user_id)'),
        ('idx_upload_reservations_token_day', 'upload_reservations(auth_token, created_day)'),
        ('idx_upload_reservations_source_day', 'upload_reservations(source, created_day)'),
        ('idx_upload_reservations_created_at', 'upload_reservations(created_at)'),
        ('idx_custom_domains_domain', 'custom_domains(domain)'),
        ('idx_custom_domains_type', 'custom_domains(domain_type)'),
        ('idx_custom_domains_active', 'custom_domains(is_active)'),
        ('idx_custom_domains_default', 'custom_domains(is_default)'),
        ('idx_custom_domains_sort', 'custom_domains(sort_order)'),
    ]

    for idx_name, idx_def in indexes:
        cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')


# ===================== 数据库初始化入口 =====================
def init_database(quiet: bool = False) -> None:
    """初始化数据库 - 创建所有必要的表和索引"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            _init_core_tables(cursor)
            _migrate_file_storage_columns(cursor)
            _init_tg_auth_tables(cursor)
            _migrate_auth_tokens_columns(cursor)
            _init_gallery_tables(cursor)
            _migrate_galleries_table(cursor, conn)
            _init_gallery_home_tables(cursor)
            _init_custom_domains_table(cursor, quiet=quiet)
            _create_indexes(cursor)

        if not quiet:
            logger.info(f"数据库初始化完成: {DATABASE_PATH}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
