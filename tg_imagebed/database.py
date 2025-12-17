#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据访问层模块 - 从 main.py 提取的数据库操作

提供统一的数据库访问接口，包含：
- 数据库初始化
- 文件存储 CRUD 操作
- Token 管理
- 统计查询
- 公告管理

兼容 admin_module.py 的接口要求。
"""
import sqlite3
import time
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from .config import (
    DATABASE_PATH, CDN_ENABLED, CLOUDFLARE_CDN_DOMAIN,
    CDN_MONITOR_ENABLED, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD,
    logger
)


# ===================== 数据库连接管理 =====================
@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ===================== 数据库初始化 =====================
def init_database() -> None:
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

            # 插入默认管理员配置（如果表为空）
            cursor.execute("SELECT COUNT(*) FROM admin_config")
            if cursor.fetchone()[0] == 0:
                password_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
                cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)",
                              ('username', DEFAULT_ADMIN_USERNAME))
                cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)",
                              ('password_hash', password_hash))
                logger.info(f"已初始化管理员配置: 用户名={DEFAULT_ADMIN_USERNAME}")

            # 检查并添加新列（用于升级现有数据库）
            cursor.execute("PRAGMA table_info(file_storage)")
            columns = [column[1] for column in cursor.fetchall()]

            new_columns = [
                ('is_group_upload', 'BOOLEAN DEFAULT 0'),
                ('group_message_id', 'INTEGER'),
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

            # 创建画集表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS galleries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_token TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    share_enabled INTEGER DEFAULT 0,
                    share_token TEXT UNIQUE,
                    share_expires_at TIMESTAMP,
                    FOREIGN KEY (owner_token) REFERENCES auth_tokens(token) ON DELETE CASCADE
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
                ('idx_galleries_share_token', 'galleries(share_token)'),
                ('idx_galleries_access_mode', 'galleries(access_mode)'),
                ('idx_galleries_hide_share_all', 'galleries(hide_from_share_all)'),
                ('idx_gallery_images_gallery', 'gallery_images(gallery_id, added_at DESC)'),
                ('idx_share_all_token', 'share_all_links(share_token)'),
                ('idx_gallery_token_access_gallery', 'gallery_token_access(gallery_id)'),
                ('idx_gallery_token_access_token', 'gallery_token_access(token)'),
                ('idx_gallery_token_access_expires', 'gallery_token_access(expires_at)'),
            ]

            for idx_name, idx_def in indexes:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')

        logger.info(f"数据库初始化完成: {DATABASE_PATH}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


# ===================== 文件存储操作 =====================
def get_file_info(encrypted_id: str) -> Optional[Dict[str, Any]]:
    """获取文件信息"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM file_storage WHERE encrypted_id = ?', (encrypted_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def save_file_info(encrypted_id: str, file_info: Dict[str, Any]) -> None:
    """保存文件信息到数据库"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 生成 ETag
        etag = f'W/"{encrypted_id}-{file_info.get("file_size", 0)}"'

        # 生成 CDN URL（仅在 CDN Mode：域名已配置 + cdn_enabled=1）
        cdn_url = None
        cdn_enabled = str(get_system_setting('cdn_enabled') or '0') == '1'
        cdn_domain = str(get_system_setting('cloudflare_cdn_domain') or '').strip()
        if cdn_enabled and cdn_domain:
            cdn_url = f"https://{cdn_domain}/image/{encrypted_id}"

        # 处理存储字段（类型防御：确保是字符串）
        storage_backend = str(file_info.get('storage_backend') or 'telegram').strip() or 'telegram'
        storage_key = str(file_info.get('storage_key') or file_info.get('file_id') or '').strip()
        storage_meta = file_info.get('storage_meta')
        if isinstance(storage_meta, str):
            storage_meta_json = storage_meta
        else:
            try:
                storage_meta_json = json.dumps(storage_meta or {}, ensure_ascii=False, separators=(",", ":"))
            except Exception:
                storage_meta_json = "{}"

        cursor.execute('''
            INSERT INTO file_storage (
                encrypted_id, file_id, file_path, upload_time,
                user_id, username, file_size, source,
                original_filename, mime_type, etag, file_hash,
                cdn_url, cdn_cached, is_group_upload, group_message_id,
                auth_token, storage_backend, storage_key, storage_meta,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            encrypted_id,
            file_info['file_id'],
            file_info.get('file_path', ''),
            file_info['upload_time'],
            file_info.get('user_id'),
            file_info.get('username', 'unknown'),
            file_info.get('file_size', 0),
            file_info.get('source', 'unknown'),
            file_info.get('original_filename', ''),
            file_info.get('mime_type', 'image/jpeg'),
            etag,
            file_info.get('file_hash', ''),
            cdn_url,
            0,  # cdn_cached
            1 if file_info.get('is_group_upload') else 0,
            file_info.get('group_message_id'),
            file_info.get('auth_token'),
            storage_backend,
            storage_key,
            storage_meta_json,
            datetime.now().isoformat()
        ))

        logger.info(f"文件信息已保存: {encrypted_id}")


def update_file_path_in_db(encrypted_id: str, new_file_path: str) -> None:
    """更新数据库中的文件路径"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE file_storage
            SET file_path = ?, last_file_path_update = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (new_file_path, encrypted_id))
        logger.debug(f"更新file_path: {encrypted_id} -> {new_file_path}")


def update_cdn_cache_status(encrypted_id: str, cached: bool) -> None:
    """更新CDN缓存状态"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE file_storage
            SET cdn_cached = ?, cdn_cache_time = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (1 if cached else 0, encrypted_id))
        logger.info(f"更新CDN缓存状态: {encrypted_id} -> {'已缓存' if cached else '未缓存'}")


def update_access_count(encrypted_id: str, access_type: str = 'direct_access') -> None:
    """更新访问计数

    Args:
        encrypted_id: 加密的文件ID
        access_type: 访问类型 ('cdn_pull' 或 'direct_access')
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cdn_inc = 1 if access_type == 'cdn_pull' else 0
        direct_inc = 1 if access_type == 'direct_access' else 0
        try:
            cursor.execute('''
                UPDATE file_storage
                SET access_count = access_count + 1,
                    cdn_hit_count = cdn_hit_count + ?,
                    direct_hit_count = direct_hit_count + ?,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE encrypted_id = ?
            ''', (cdn_inc, direct_inc, encrypted_id))
        except sqlite3.OperationalError as e:
            # 仅在列不存在时回退到旧逻辑（兼容旧数据库结构）
            if 'no such column' in str(e).lower():
                cursor.execute('''
                    UPDATE file_storage
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE encrypted_id = ?
                ''', (encrypted_id,))
            else:
                raise


def delete_files_by_ids(encrypted_ids: List[str]) -> tuple:
    """批量删除文件记录"""
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(encrypted_ids))

        # 获取要删除的文件大小
        cursor.execute(f'''
            SELECT SUM(file_size) FROM file_storage
            WHERE encrypted_id IN ({placeholders})
        ''', encrypted_ids)
        result = cursor.fetchone()
        deleted_size = result[0] if result and result[0] else 0

        # 删除记录
        cursor.execute(f'''
            DELETE FROM file_storage
            WHERE encrypted_id IN ({placeholders})
        ''', encrypted_ids)
        deleted_count = cursor.rowcount

        return deleted_count, deleted_size


# ===================== 统计查询（admin_module.py 兼容） =====================
def get_all_files_count() -> int:
    """获取所有文件数量（admin_module.py 兼容接口）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_storage')
        return cursor.fetchone()[0]


def get_total_size() -> int:
    """获取所有文件总大小（admin_module.py 兼容接口）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COALESCE(SUM(file_size), 0) FROM file_storage')
        return cursor.fetchone()[0]


def get_stats() -> Dict[str, Any]:
    """获取完整统计信息"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取总文件数和大小
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM file_storage')
        total_files, total_size = cursor.fetchone()

        # 获取今日上传数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_timestamp = int(today_start.timestamp())
        cursor.execute(
            'SELECT COUNT(*) FROM file_storage WHERE upload_time >= ?',
            (today_timestamp,)
        )
        today_uploads = cursor.fetchone()[0]

        # 获取CDN缓存的文件数
        cursor.execute('SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 1')
        cached_files = cursor.fetchone()[0]

        # 获取待缓存数
        cursor.execute(
            'SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 0 AND cdn_url IS NOT NULL'
        )
        pending_cache = cursor.fetchone()[0]

        # 获取群组上传数
        cursor.execute('SELECT COUNT(*) FROM file_storage WHERE is_group_upload = 1')
        group_uploads = cursor.fetchone()[0]

        return {
            'total_files': total_files,
            'total_size': total_size,
            'today_uploads': today_uploads,
            'group_uploads': group_uploads,
            'cdn_stats': {
                'cached_files': cached_files,
                'pending_cache': pending_cache,
                'monitor_queue_size': 0  # 由 cdn_service 更新
            }
        }


def get_recent_uploads(limit: int = 10, page: int = 1) -> List[Dict[str, Any]]:
    """获取最近上传的文件"""
    with get_connection() as conn:
        cursor = conn.cursor()
        offset = (page - 1) * limit

        cursor.execute('''
            SELECT encrypted_id, original_filename, file_size,
                   created_at, username, cdn_cached, is_group_upload
            FROM file_storage
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        return [dict(row) for row in cursor.fetchall()]


def get_uncached_files(since_timestamp: int, limit: int = 100) -> List[Dict[str, Any]]:
    """获取未缓存的文件（用于恢复CDN监控任务）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT encrypted_id, upload_time FROM file_storage
            WHERE cdn_cached = 0
            AND upload_time > ?
            AND cdn_url IS NOT NULL
            ORDER BY upload_time DESC
            LIMIT ?
        ''', (since_timestamp, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_cdn_dashboard_stats(window_hours: Optional[int] = None) -> Dict[str, Any]:
    """
    CDN 仪表盘统计
    注意：无法从源站精确推断 Cloudflare 边缘 HIT 率，边缘命中不会到达源站
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # 文件缓存统计
        cursor.execute("SELECT COUNT(*) FROM file_storage")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 1")
        cached_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 0 OR cdn_cached IS NULL")
        uncached_files = cursor.fetchone()[0]

        # 访问统计（可选时间窗口）
        where = ""
        params: List[Any] = []
        if window_hours is not None:
            hours = int(window_hours)
            where = "WHERE last_accessed IS NOT NULL AND last_accessed >= datetime('now', ?)"
            params = [f"-{hours} hours"]

        cursor.execute(
            f"""
            SELECT
              COALESCE(SUM(access_count), 0),
              COALESCE(SUM(cdn_hit_count), 0),
              COALESCE(SUM(direct_hit_count), 0)
            FROM file_storage
            {where}
            """,
            params
        )
        row = cursor.fetchone()
        access_total = int(row[0] or 0)
        cdn_origin_requests = int(row[1] or 0)
        direct_origin_requests = int(row[2] or 0)

        origin_total = cdn_origin_requests + direct_origin_requests
        direct_share = (direct_origin_requests / origin_total) if origin_total else 0.0
        cdn_origin_share = (cdn_origin_requests / origin_total) if origin_total else 0.0

        return {
            "files": {
                "total": total_files,
                "cached": cached_files,
                "uncached": uncached_files,
                "cache_rate": (cached_files / total_files) if total_files else 0.0,
            },
            "origin_requests": {
                "window_hours": window_hours,
                "total_access_count": access_total,
                "origin_total": origin_total,
                "cdn_origin_requests": cdn_origin_requests,
                "direct_origin_requests": direct_origin_requests,
                "cdn_origin_share": cdn_origin_share,
                "direct_origin_share": direct_share,
                "note": "Edge HITs do not reach origin; use Cloudflare analytics for real hit rate.",
            },
        }


# ===================== Token 管理 =====================
def generate_auth_token() -> str:
    """生成唯一的 auth_token"""
    token = secrets.token_hex(32)
    return f"guest_{token}"


def create_auth_token(
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None,
    upload_limit: int = 100,
    expires_days: int = 30
) -> Optional[str]:
    """创建新的 auth_token"""
    try:
        token = generate_auth_token()
        expires_at = datetime.now() + timedelta(days=expires_days)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auth_tokens
                (token, expires_at, upload_limit, ip_address, user_agent, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (token, expires_at, upload_limit, ip_address, user_agent, description or '游客Token'))

        logger.info(f"创建新的auth_token: {token[:20]}... (限制: {upload_limit}张, 有效期: {expires_days}天)")
        return token

    except Exception as e:
        logger.error(f"创建auth_token失败: {e}")
        return None


def verify_auth_token(token: str) -> Dict[str, Any]:
    """验证 auth_token 是否有效"""
    if not token:
        return {'valid': False, 'reason': 'Token为空'}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,))
            row = cursor.fetchone()

            if not row:
                return {'valid': False, 'reason': 'Token不存在'}

            token_data = dict(row)

            # 检查是否激活
            if not token_data['is_active']:
                return {'valid': False, 'reason': 'Token已被禁用'}

            # 检查是否过期
            if token_data.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(str(token_data['expires_at']).replace('Z', '+00:00'))
                    if datetime.now() > expires_at.replace(tzinfo=None):
                        return {'valid': False, 'reason': 'Token已过期'}
                except Exception:
                    pass  # 解析失败则忽略过期检查

            # 计算剩余上传次数
            upload_count = token_data.get('upload_count', 0)
            upload_limit = token_data.get('upload_limit', 999999)
            remaining_uploads = upload_limit - upload_count

            # 检查上传限制
            if remaining_uploads <= 0:
                return {'valid': False, 'reason': f'已达到上传限制({upload_limit}张)'}

            return {
                'valid': True,
                'token_data': token_data,
                'remaining_uploads': remaining_uploads
            }

    except Exception as e:
        logger.error(f"验证auth_token失败: {e}")
        return {'valid': False, 'reason': '验证失败'}


def verify_auth_token_access(token: str) -> Dict[str, Any]:
    """验证 auth_token 是否有效（访问级别：不检查上传额度，用于查看相册）"""
    if not token:
        return {'valid': False, 'reason': 'Token为空'}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,))
            row = cursor.fetchone()

            if not row:
                return {'valid': False, 'reason': 'Token不存在'}

            token_data = dict(row)

            # 检查是否激活
            if not token_data.get('is_active', 1):
                return {'valid': False, 'reason': 'Token已被禁用'}

            # 检查是否过期
            if token_data.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(str(token_data['expires_at']).replace('Z', '+00:00'))
                    if datetime.now() > expires_at.replace(tzinfo=None):
                        return {'valid': False, 'reason': 'Token已过期'}
                except Exception:
                    pass

            # 计算剩余上传次数（但不作为验证条件）
            upload_count = int(token_data.get('upload_count') or 0)
            upload_limit = int(token_data.get('upload_limit') or 999999)
            remaining_uploads = upload_limit - upload_count

            return {
                'valid': True,
                'token_data': token_data,
                'remaining_uploads': max(0, remaining_uploads),
                'can_upload': remaining_uploads > 0
            }

    except Exception as e:
        logger.error(f"验证auth_token(access)失败: {e}")
        return {'valid': False, 'reason': '验证失败'}


def update_token_description(token: str, description: Optional[str]) -> bool:
    """更新 Token 描述（前端可用作相册名称）"""
    try:
        token = (token or '').strip()
        if not token:
            return False
        desc_value = (str(description or '').strip()[:200]) or None
        with get_connection() as conn:
            cursor = conn.cursor()
            # 先检查token是否存在
            cursor.execute("SELECT 1 FROM auth_tokens WHERE token = ?", (token,))
            if not cursor.fetchone():
                return False
            # 执行更新（即使值相同也返回成功，保证幂等性）
            cursor.execute(
                "UPDATE auth_tokens SET description = ? WHERE token = ?",
                (desc_value, token)
            )
            return True
    except Exception as e:
        logger.error(f"更新token描述失败: {e}")
        return False


def update_token_usage(token: str) -> None:
    """更新 token 使用记录"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE auth_tokens
                SET upload_count = upload_count + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE token = ?
            ''', (token,))
    except Exception as e:
        logger.error(f"更新token使用记录失败: {e}")


def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    """获取 token 详细信息"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取token信息失败: {e}")
        return None


def get_token_uploads(token: str, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    """获取 token 上传的所有图片"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * limit

            cursor.execute('''
                SELECT encrypted_id, original_filename, file_size, created_at,
                       cdn_cached, cdn_url, mime_type
                FROM file_storage
                WHERE auth_token = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (token, limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"获取token上传记录失败: {e}")
        return []


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
    'cloudflare_api_token', 'telegram_bot_token'
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
}

# 环境变量迁移标记（避免每次启动重复覆盖管理员修改）
_ENV_MIGRATED_KEY = '__env_settings_migrated_v1__'
_STORAGE_CHAT_ID_MIGRATED_KEY = '__storage_chat_id_to_storage_config_v1__'


def migrate_storage_chat_id_env_to_storage_config() -> int:
    """一次性迁移：将环境变量 STORAGE_CHAT_ID 迁移到 storage_config_json (DB)。

    规则:
    - 仅运行一次（标记键）
    - 如果设置了 STORAGE_CONFIG_JSON 环境变量则跳过
    - 仅当 storage_config_json 为空/默认 或 telegram.chat_id 未设置/0/env:STORAGE_CHAT_ID 时写入
    """
    try:
        import os as _os
        from . import config as app_config

        env_chat_id = int(getattr(app_config, "STORAGE_CHAT_ID", 0) or 0)
        if not env_chat_id:
            return 0

        if (_os.getenv("STORAGE_CONFIG_JSON") or "").strip():
            return 0

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT value FROM admin_config WHERE key = ?', (_STORAGE_CHAT_ID_MIGRATED_KEY,))
            row = cursor.fetchone()
            if row and str(row[0] or '') == '1':
                return 0

            cursor.execute('SELECT value FROM admin_config WHERE key = ?', ('storage_config_json',))
            row = cursor.fetchone()
            raw = (row[0] if row else '') or ''

            cfg = None
            if raw.strip():
                try:
                    cfg = json.loads(raw)
                except Exception:
                    cfg = None
            if not isinstance(cfg, dict):
                cfg = {}

            changed = False
            backends = cfg.get('backends')
            if not isinstance(backends, dict):
                backends = {}
                cfg['backends'] = backends
                changed = True

            telegram = backends.get('telegram')
            if not isinstance(telegram, dict):
                telegram = {'driver': 'telegram', 'bot_token': 'env:BOT_TOKEN'}
                backends['telegram'] = telegram
                changed = True

            existing_chat_id = telegram.get('chat_id')
            existing_norm = str(existing_chat_id).strip() if existing_chat_id is not None else ''
            if existing_norm in ('', '0', 'env:STORAGE_CHAT_ID'):
                telegram['chat_id'] = str(env_chat_id)
                changed = True

            if not str(cfg.get('active') or '').strip():
                cfg['active'] = 'telegram'
                changed = True

            if changed:
                cursor.execute('''
                    INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', ('storage_config_json', json.dumps(cfg, ensure_ascii=False)))
                logger.info("迁移 STORAGE_CHAT_ID -> storage_config_json 完成")

            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (_STORAGE_CHAT_ID_MIGRATED_KEY, '1'))

        return 1 if changed else 0
    except Exception as e:
        logger.error(f"迁移 STORAGE_CHAT_ID -> storage_config_json 失败: {e}")
        return 0


def _settings_schema_fingerprint() -> str:
    """系统设置 schema 指纹：用于新增配置项后触发一次 env 迁移"""
    keys = ','.join(sorted(DEFAULT_SYSTEM_SETTINGS.keys()))
    return hashlib.sha1(keys.encode('utf-8')).hexdigest()[:12]


def _get_env_config_value(db_key: str):
    """从 config.py 获取对应的环境变量配置值"""
    from . import config

    # 数据库 key -> config.py 变量名的映射
    mapping = {
        # CDN 配置
        'cdn_enabled': ('CDN_ENABLED', 'bool'),
        'cloudflare_cdn_domain': ('CLOUDFLARE_CDN_DOMAIN', 'str'),
        'cloudflare_api_token': ('CLOUDFLARE_API_TOKEN', 'str'),
        'cloudflare_zone_id': ('CLOUDFLARE_ZONE_ID', 'str'),
        'cloudflare_cache_level': ('CLOUDFLARE_CACHE_LEVEL', 'str'),
        'cloudflare_browser_ttl': ('CLOUDFLARE_BROWSER_TTL', 'int'),
        'cloudflare_edge_ttl': ('CLOUDFLARE_EDGE_TTL', 'int'),
        'enable_smart_routing': ('ENABLE_SMART_ROUTING', 'bool'),
        'fallback_to_origin': ('FALLBACK_TO_ORIGIN', 'bool'),
        'enable_cache_warming': ('ENABLE_CACHE_WARMING', 'bool'),
        'cache_warming_delay': ('CACHE_WARMING_DELAY', 'int'),
        'cdn_monitor_enabled': ('CDN_MONITOR_ENABLED', 'bool'),
        'cdn_redirect_enabled': ('CDN_REDIRECT_ENABLED', 'bool'),
        'cdn_redirect_max_count': ('CDN_REDIRECT_MAX_COUNT', 'int'),
        'cdn_redirect_delay': ('CDN_REDIRECT_DELAY', 'int'),
        # 群组上传配置
        'group_upload_admin_only': ('GROUP_UPLOAD_ADMIN_ONLY', 'bool'),
        'group_admin_ids': ('GROUP_ADMIN_IDS', 'str'),
        'group_upload_reply': ('GROUP_UPLOAD_REPLY', 'bool'),
        'group_upload_delete_delay': ('GROUP_UPLOAD_DELETE_DELAY', 'int'),
    }

    if db_key not in mapping:
        return None

    config_name, value_type = mapping[db_key]

    if not hasattr(config, config_name):
        return None

    value = getattr(config, config_name)

    # 转换为数据库存储格式
    if value_type == 'bool':
        return '1' if value else '0'
    elif value_type == 'int':
        return str(value)
    else:
        return str(value) if value else ''


def init_system_settings() -> None:
    """初始化系统设置（在 admin_config 表中），并从环境变量迁移现有配置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for key, default_value in DEFAULT_SYSTEM_SETTINGS.items():
                cursor.execute(
                    'SELECT value FROM admin_config WHERE key = ?', (key,)
                )
                existing = cursor.fetchone()

                if not existing:
                    # 尝试从环境变量/config.py 获取值
                    env_value = _get_env_config_value(key)
                    value_to_insert = env_value if env_value is not None else default_value

                    cursor.execute(
                        'INSERT INTO admin_config (key, value) VALUES (?, ?)',
                        (key, value_to_insert)
                    )

                    if key in SENSITIVE_SETTINGS:
                        logger.info(f"初始化系统设置: {key}=[REDACTED]")
                    else:
                        source = "从环境变量迁移" if env_value is not None else "默认值"
                        logger.info(f"初始化系统设置: {key}={value_to_insert} ({source})")

        # 一次性迁移 STORAGE_CHAT_ID -> storage_config_json
        migrate_storage_chat_id_env_to_storage_config()
    except Exception as e:
        logger.error(f"初始化系统设置失败: {e}")


def migrate_env_settings() -> int:
    """将环境变量配置迁移到数据库（schema 变化时触发迁移）"""
    migrated = 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 使用 schema 指纹：当新增配置项时会触发一次迁移
            schema_fp = _settings_schema_fingerprint()
            cursor.execute('SELECT value FROM admin_config WHERE key = ?', (_ENV_MIGRATED_KEY,))
            marker = cursor.fetchone()
            marker_value = str(marker[0] or '') if marker else ''
            if marker_value == schema_fp:
                return 0

            for key, default_value in DEFAULT_SYSTEM_SETTINGS.items():
                env_value = _get_env_config_value(key)
                if env_value is None:
                    continue

                # 检查当前值是否为默认值
                cursor.execute('SELECT value FROM admin_config WHERE key = ?', (key,))
                row = cursor.fetchone()
                current_value = row[0] if row else default_value

                # 只有当当前值等于默认值且环境变量值不同时才更新
                if current_value == default_value and env_value != default_value:
                    cursor.execute('''
                        INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (key, env_value))
                    migrated += 1
                    if key in SENSITIVE_SETTINGS:
                        logger.info(f"迁移环境变量配置: {key}=[REDACTED]")
                    else:
                        logger.info(f"迁移环境变量配置: {key}={env_value}")

            # 标记迁移完成（写入 schema 指纹）
            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (_ENV_MIGRATED_KEY, schema_fp))

        if migrated > 0:
            logger.info(f"共迁移 {migrated} 项环境变量配置到数据库")
    except Exception as e:
        logger.error(f"迁移环境变量配置失败: {e}")
    return migrated


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


# ===================== Token 管理（管理员后台） =====================
def _mask_token(token: str, prefix_len: int = 6, suffix_len: int = 6) -> str:
    """对 Token 进行脱敏处理，只显示前后各几位字符"""
    token = str(token or '')
    if len(token) <= prefix_len + suffix_len:
        return token
    return f"{token[:prefix_len]}...{token[-suffix_len:]}"


def _parse_datetime(value: Any) -> Optional[str]:
    """
    解析 ISO8601 格式的日期时间字符串，转换为 SQLite 兼容的格式。
    支持带时区和不带时区的格式。
    """
    if value is None:
        return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            # 处理 ISO8601 格式，包括 'Z' 时区标记
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"无效的日期时间格式: {raw}") from e

        # 如果有时区信息，转换为本地时间
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    raise ValueError(f"不支持的日期时间类型: {type(value)}")


def _token_row_to_dict(row: sqlite3.Row, *, include_full_token: bool = False) -> Dict[str, Any]:
    """
    将数据库行转换为字典，并进行数据格式化。

    Args:
        row: 数据库查询结果行
        include_full_token: 是否包含完整 token（仅在创建时返回）
    """
    if not row:
        return {}

    data = dict(row)
    token_value = data.get('token', '')

    # 添加脱敏后的 token
    data['token_masked'] = _mask_token(token_value)

    # 根据参数决定是否保留完整 token
    if not include_full_token:
        data.pop('token', None)

    # 布尔字段转换
    if 'is_active' in data:
        data['is_active'] = bool(data['is_active'])
    if 'is_expired' in data:
        data['is_expired'] = bool(data['is_expired'])

    return data


# 过期判断 SQL 表达式（避免重复）
_EXPIRED_EXPR = "(expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP)"


def admin_list_tokens(
    *,
    status: str = 'all',
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    管理员获取 Token 列表（分页）。

    Args:
        status: 筛选状态
            - 'all': 全部
            - 'active': 启用且未过期
            - 'disabled': 禁用但未过期
            - 'expired': 已过期（无论是否启用）
        page: 页码（从 1 开始）
        page_size: 每页数量（最大 100）

    Returns:
        包含 page, page_size, total, items 的字典
    """
    # 参数规范化
    status = (status or 'all').strip().lower()
    page = max(1, int(page) if isinstance(page, (int, str)) and str(page).isdigit() else 1)
    page_size = max(1, min(100, int(page_size) if isinstance(page_size, (int, str)) and str(page_size).isdigit() else 20))
    offset = (page - 1) * page_size

    # 根据状态构建 WHERE 子句
    where_sql = ""
    where_params: tuple = ()

    if status == 'active':
        where_sql = f"WHERE is_active = 1 AND NOT {_EXPIRED_EXPR}"
    elif status == 'disabled':
        where_sql = f"WHERE is_active = 0 AND NOT {_EXPIRED_EXPR}"
    elif status == 'expired':
        where_sql = f"WHERE {_EXPIRED_EXPR}"
    elif status != 'all':
        raise ValueError(f"无效的状态筛选: {status}")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询总数
            cursor.execute(f"SELECT COUNT(1) FROM auth_tokens {where_sql}", where_params)
            total = cursor.fetchone()[0] or 0

            # 查询列表
            cursor.execute(f"""
                SELECT
                    rowid AS id,
                    token,
                    created_at,
                    expires_at,
                    last_used,
                    upload_count,
                    upload_limit,
                    is_active,
                    ip_address,
                    user_agent,
                    description,
                    CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                FROM auth_tokens
                {where_sql}
                ORDER BY created_at DESC, rowid DESC
                LIMIT ? OFFSET ?
            """, (*where_params, page_size, offset))

            items = [_token_row_to_dict(row, include_full_token=False) for row in cursor.fetchall()]

        return {
            'page': page,
            'page_size': page_size,
            'total': total,
            'items': items
        }

    except Exception as e:
        logger.error(f"管理员获取 Token 列表失败: {e}")
        raise


def admin_create_token(
    *,
    description: Optional[str] = None,
    expires_at: Any = None,
    upload_limit: int = 100,
    is_active: bool = True
) -> Optional[Dict[str, Any]]:
    """
    管理员创建新的 Token。

    Args:
        description: Token 描述
        expires_at: 过期时间（ISO8601 格式或 datetime 对象，None 表示永不过期）
        upload_limit: 上传限制（0 表示禁止上传，正整数为限制数）
        is_active: 是否启用

    Returns:
        创建成功返回包含完整 token 的字典（仅此一次），失败返回 None
    """
    # 参数处理
    desc_value = (str(description).strip() if description else None) or None

    # 验证上传限制
    try:
        limit_value = int(upload_limit)
        if limit_value < 0:
            raise ValueError("upload_limit 不能为负数")
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的 upload_limit: {upload_limit}") from e

    # 解析过期时间
    expires_value = _parse_datetime(expires_at)

    # 布尔转换
    active_value = 1 if is_active else 0

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 尝试生成唯一 token（最多重试 5 次）
            for _ in range(5):
                token = f"admin_{secrets.token_hex(32)}"
                try:
                    cursor.execute("""
                        INSERT INTO auth_tokens
                        (token, expires_at, upload_limit, is_active, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (token, expires_value, limit_value, active_value, desc_value))

                    token_id = cursor.lastrowid

                    # 查询刚创建的记录
                    cursor.execute(f"""
                        SELECT
                            rowid AS id,
                            token,
                            created_at,
                            expires_at,
                            last_used,
                            upload_count,
                            upload_limit,
                            is_active,
                            ip_address,
                            user_agent,
                            description,
                            CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                        FROM auth_tokens
                        WHERE rowid = ?
                    """, (token_id,))

                    row = cursor.fetchone()
                    if row:
                        logger.info(f"管理员创建 Token 成功: ID={token_id}")
                        return _token_row_to_dict(row, include_full_token=True)

                except sqlite3.IntegrityError:
                    # Token 冲突，重试
                    continue

        logger.error("管理员创建 Token 失败: 无法生成唯一 token")
        return None

    except Exception as e:
        logger.error(f"管理员创建 Token 失败: {e}")
        raise


def admin_update_token_status(*, token_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
    """
    管理员更新 Token 启用状态。

    Args:
        token_id: Token 的 rowid
        is_active: 是否启用

    Returns:
        更新成功返回更新后的 Token 信息，Token 不存在返回 None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 更新状态
            cursor.execute(
                "UPDATE auth_tokens SET is_active = ? WHERE rowid = ?",
                (1 if is_active else 0, int(token_id))
            )

            if cursor.rowcount == 0:
                return None

            # 查询更新后的记录
            cursor.execute(f"""
                SELECT
                    rowid AS id,
                    token,
                    created_at,
                    expires_at,
                    last_used,
                    upload_count,
                    upload_limit,
                    is_active,
                    ip_address,
                    user_agent,
                    description,
                    CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                FROM auth_tokens
                WHERE rowid = ?
            """, (int(token_id),))

            row = cursor.fetchone()
            if row:
                status_text = "启用" if is_active else "禁用"
                logger.info(f"管理员更新 Token 状态: ID={token_id} -> {status_text}")
                return _token_row_to_dict(row, include_full_token=False)

            return None

    except Exception as e:
        logger.error(f"管理员更新 Token 状态失败: {e}")
        raise


def admin_delete_token(*, token_id: int) -> bool:
    """
    管理员删除 Token。

    Args:
        token_id: Token 的 rowid

    Returns:
        删除成功返回 True，Token 不存在返回 False
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_tokens WHERE rowid = ?", (int(token_id),))
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"管理员删除 Token: ID={token_id}")

            return deleted

    except Exception as e:
        logger.error(f"管理员删除 Token 失败: {e}")
        raise


# ===================== 管理员画集 Owner Token =====================
_ADMIN_GALLERY_OWNER_CONFIG_KEY = 'admin_gallery_owner_token'
_ADMIN_GALLERY_OWNER_TOKEN_DESC = 'internal_admin_gallery_owner'


def _ensure_admin_gallery_owner_token() -> str:
    """确保管理员画集 owner token 存在"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM admin_config WHERE key = ?', (_ADMIN_GALLERY_OWNER_CONFIG_KEY,))
        row = cur.fetchone()
        token = (str(row[0]).strip() if row and row[0] else '')

        def _token_is_safe(t: str) -> bool:
            cur.execute('SELECT is_active, description FROM auth_tokens WHERE token = ?', (t,))
            r = cur.fetchone()
            if not r:
                return True
            return (not bool(r[0])) and (str(r[1] or '') == _ADMIN_GALLERY_OWNER_TOKEN_DESC)

        if not token or not _token_is_safe(token):
            while True:
                token = secrets.token_urlsafe(32)
                if _token_is_safe(token):
                    break
            cur.execute(
                'INSERT OR REPLACE INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                (_ADMIN_GALLERY_OWNER_CONFIG_KEY, token)
            )

        cur.execute('''
            INSERT OR IGNORE INTO auth_tokens (token, expires_at, upload_limit, is_active, description)
            VALUES (?, NULL, 999999999, 0, ?)
        ''', (token, _ADMIN_GALLERY_OWNER_TOKEN_DESC))
        return token


def _get_admin_gallery_owner_token() -> Optional[str]:
    """获取管理员画集 owner token"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT value FROM admin_config WHERE key = ?', (_ADMIN_GALLERY_OWNER_CONFIG_KEY,))
            row = cur.fetchone()
            token = (str(row[0]).strip() if row and row[0] else '')
            if not token:
                return _ensure_admin_gallery_owner_token()
            # 验证token是否在auth_tokens表中存在（可能被删除了）
            cur.execute('SELECT 1 FROM auth_tokens WHERE token = ?', (token,))
            if not cur.fetchone():
                # token不存在，需要重新创建
                logger.warning(f"Admin gallery owner token 在 auth_tokens 表中不存在，重新创建")
                return _ensure_admin_gallery_owner_token()
            return token
    except Exception as e:
        logger.error(f"读取 admin gallery owner token 失败: {e}")
        return None


# ===================== 画集管理 =====================
def create_gallery(owner_token: str, name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """创建画集"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO galleries (owner_token, name, description)
                VALUES (?, ?, ?)
            ''', (owner_token, name.strip(), (description or '').strip() or None))
            gallery_id = cursor.lastrowid
            cursor.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
            row = cursor.fetchone()
            logger.info(f"创建画集: ID={gallery_id}, name={name}")
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"创建画集失败: {e}")
        return None


def get_gallery(gallery_id: int, owner_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取画集详情（可选验证所有者）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if owner_token:
                cursor.execute('SELECT * FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            else:
                cursor.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                cursor.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
                data['image_count'] = cursor.fetchone()[0]
                return data
            return None
    except Exception as e:
        logger.error(f"获取画集失败: {e}")
        return None


def list_galleries(owner_token: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """获取用户的画集列表"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * limit
            cursor.execute('SELECT COUNT(*) FROM galleries WHERE owner_token = ?', (owner_token,))
            total = cursor.fetchone()[0]
            # 优先使用手动设置的封面，否则取第一张图（按添加时间 ASC）
            cursor.execute('''
                SELECT g.*,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT fs.encrypted_id FROM gallery_images gi2
                        JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                        WHERE gi2.gallery_id = g.id ORDER BY gi2.added_at ASC LIMIT 1
                    )) AS cover_image
                FROM galleries g
                WHERE g.owner_token = ?
                ORDER BY g.updated_at DESC
                LIMIT ? OFFSET ?
            ''', (owner_token, limit, offset))
            items = [dict(row) for row in cursor.fetchall()]
            return {'items': items, 'total': total, 'page': page, 'limit': limit}
    except Exception as e:
        logger.error(f"获取画集列表失败: {e}")
        return {'items': [], 'total': 0, 'page': page, 'limit': limit}


def update_gallery(gallery_id: int, owner_token: str, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """更新画集信息"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            updates, params = [], []
            if name is not None:
                updates.append('name = ?')
                params.append(name.strip())
            if description is not None:
                updates.append('description = ?')
                params.append(description.strip() or None)
            if not updates:
                return get_gallery(gallery_id, owner_token)
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.extend([gallery_id, owner_token])
            cursor.execute(f'''
                UPDATE galleries SET {', '.join(updates)}
                WHERE id = ? AND owner_token = ?
            ''', params)
            if cursor.rowcount == 0:
                return None
            logger.info(f"更新画集: ID={gallery_id}")
            return get_gallery(gallery_id, owner_token)
    except Exception as e:
        logger.error(f"更新画集失败: {e}")
        return None


def delete_gallery(gallery_id: int, owner_token: str) -> bool:
    """删除画集"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"删除画集: ID={gallery_id}")
            return deleted
    except Exception as e:
        logger.error(f"删除画集失败: {e}")
        return False


def set_gallery_cover(gallery_id: int, owner_token: str, encrypted_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """设置画集封面图（encrypted_id为None或空字符串则清除手动设置，使用默认第一张图）"""
    # 规范化空字符串为None
    if encrypted_id is not None and not encrypted_id.strip():
        encrypted_id = None
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return None
            # 使用原子操作：如果指定了封面，在UPDATE中验证图片存在于画集
            if encrypted_id:
                cursor.execute('''
                    UPDATE galleries SET cover_image = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND EXISTS (
                        SELECT 1 FROM gallery_images WHERE gallery_id = ? AND encrypted_id = ?
                    )
                ''', (encrypted_id, gallery_id, gallery_id, encrypted_id))
                if cursor.rowcount == 0:
                    return None
            else:
                cursor.execute('''
                    UPDATE galleries SET cover_image = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?
                ''', (gallery_id,))
            logger.info(f"设置画集封面: gallery_id={gallery_id}, cover_image={encrypted_id}")
            return get_gallery(gallery_id, owner_token)
    except Exception as e:
        logger.error(f"设置画集封面失败: {e}")
        return None


def admin_set_gallery_cover(gallery_id: int, encrypted_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """管理员设置画集封面图"""
    # 规范化空字符串为None
    if encrypted_id is not None and not encrypted_id.strip():
        encrypted_id = None
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM galleries WHERE id = ?', (gallery_id,))
            if not cursor.fetchone():
                return None
            if encrypted_id:
                cursor.execute('''
                    UPDATE galleries SET cover_image = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND EXISTS (
                        SELECT 1 FROM gallery_images WHERE gallery_id = ? AND encrypted_id = ?
                    )
                ''', (encrypted_id, gallery_id, gallery_id, encrypted_id))
                if cursor.rowcount == 0:
                    return None
            else:
                cursor.execute('''
                    UPDATE galleries SET cover_image = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?
                ''', (gallery_id,))
            logger.info(f"Admin设置画集封面: gallery_id={gallery_id}, cover_image={encrypted_id}")
            return admin_get_gallery(gallery_id)
    except Exception as e:
        logger.error(f"Admin设置画集封面失败: {e}")
        return None


def add_images_to_gallery(gallery_id: int, owner_token: str, encrypted_ids: List[str]) -> Dict[str, Any]:
    """添加图片到画集"""
    result = {'added': 0, 'skipped': 0, 'not_found': [], 'not_owned': []}
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return result
            for enc_id in encrypted_ids:
                cursor.execute('SELECT auth_token FROM file_storage WHERE encrypted_id = ?', (enc_id,))
                row = cursor.fetchone()
                if not row:
                    result['not_found'].append(enc_id)
                    continue
                if row[0] != owner_token:
                    result['not_owned'].append(enc_id)
                    continue
                try:
                    cursor.execute('INSERT OR IGNORE INTO gallery_images (gallery_id, encrypted_id) VALUES (?, ?)', (gallery_id, enc_id))
                    if cursor.rowcount > 0:
                        result['added'] += 1
                    else:
                        result['skipped'] += 1
                except sqlite3.IntegrityError:
                    result['skipped'] += 1
            cursor.execute('UPDATE galleries SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
        logger.info(f"添加图片到画集: gallery_id={gallery_id}, added={result['added']}")
        return result
    except Exception as e:
        logger.error(f"添加图片到画集失败: {e}")
        return result


def remove_images_from_gallery(gallery_id: int, owner_token: str, encrypted_ids: List[str]) -> int:
    """从画集移除图片"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, cover_image FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            row = cursor.fetchone()
            if not row:
                return 0
            current_cover = row['cover_image']
            placeholders = ','.join('?' * len(encrypted_ids))
            cursor.execute(f'DELETE FROM gallery_images WHERE gallery_id = ? AND encrypted_id IN ({placeholders})', [gallery_id] + encrypted_ids)
            removed = cursor.rowcount
            # 如果移除了当前封面，清除封面设置
            if current_cover and current_cover in encrypted_ids:
                cursor.execute('UPDATE galleries SET cover_image = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
                logger.info(f"封面图片被移除，清除封面设置: gallery_id={gallery_id}")
            else:
                cursor.execute('UPDATE galleries SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
            logger.info(f"从画集移除图片: gallery_id={gallery_id}, removed={removed}")
            return removed
    except Exception as e:
        logger.error(f"从画集移除图片失败: {e}")
        return 0


def get_gallery_images(gallery_id: int, owner_token: Optional[str] = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """获取画集内的图片"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if owner_token:
                cursor.execute('SELECT id FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            else:
                cursor.execute('''
                    SELECT id FROM galleries
                    WHERE id = ? AND share_enabled = 1
                    AND (share_expires_at IS NULL OR share_expires_at > CURRENT_TIMESTAMP)
                ''', (gallery_id,))
            row = cursor.fetchone()
            if not row:
                return {'items': [], 'total': 0, 'page': page, 'limit': limit}
            offset = (page - 1) * limit
            cursor.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT fs.encrypted_id, fs.original_filename, fs.file_size, fs.created_at,
                       fs.cdn_cached, fs.cdn_url, fs.mime_type, gi.added_at
                FROM gallery_images gi
                JOIN file_storage fs ON gi.encrypted_id = fs.encrypted_id
                WHERE gi.gallery_id = ?
                ORDER BY gi.added_at DESC
                LIMIT ? OFFSET ?
            ''', (gallery_id, limit, offset))
            items = [dict(r) for r in cursor.fetchall()]
            return {'items': items, 'total': total, 'page': page, 'limit': limit}
    except Exception as e:
        logger.error(f"获取画集图片失败: {e}")
        return {'items': [], 'total': 0, 'page': page, 'limit': limit}


def update_gallery_share(gallery_id: int, owner_token: str, enabled: bool, expires_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """更新画集分享设置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT share_token FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            row = cursor.fetchone()
            if not row:
                return None
            share_token = row[0]
            if enabled and not share_token:
                share_token = secrets.token_urlsafe(24)
            expires_value = _parse_datetime(expires_at) if expires_at else None
            cursor.execute('''
                UPDATE galleries
                SET share_enabled = ?, share_token = ?, share_expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND owner_token = ?
            ''', (1 if enabled else 0, share_token if enabled else None, expires_value if enabled else None, gallery_id, owner_token))
            logger.info(f"更新画集分享: gallery_id={gallery_id}, enabled={enabled}")
            return get_gallery(gallery_id, owner_token)
    except Exception as e:
        logger.error(f"更新画集分享失败: {e}")
        return None


def get_shared_gallery(share_token: str) -> Optional[Dict[str, Any]]:
    """通过分享链接获取画集"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM galleries
                WHERE share_token = ? AND share_enabled = 1
                AND (share_expires_at IS NULL OR share_expires_at > CURRENT_TIMESTAMP)
            ''', (share_token,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                cursor.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (data['id'],))
                data['image_count'] = cursor.fetchone()[0]
                return data
            return None
    except Exception as e:
        logger.error(f"获取分享画集失败: {e}")
        return None


# ===================== 画集访问控制 =====================
def update_gallery_access(
    gallery_id: int,
    owner_token: Optional[str] = None,
    access_mode: Optional[str] = None,
    password: Optional[str] = None,
    hide_from_share_all: Optional[bool] = None,
    is_admin: bool = False
) -> Optional[Dict[str, Any]]:
    """更新画集访问控制设置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 验证权限
            if is_admin:
                cursor.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
            else:
                cursor.execute('SELECT * FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return None

            updates = []
            params = []
            if access_mode is not None:
                if access_mode not in ('public', 'password', 'admin_only', 'token'):
                    return None
                updates.append('access_mode = ?')
                params.append(access_mode)
                # 清除密码（如果切换到非密码模式）
                if access_mode != 'password':
                    updates.append('password_hash = NULL')
            if password is not None and access_mode == 'password':
                from werkzeug.security import generate_password_hash
                updates.append('password_hash = ?')
                params.append(generate_password_hash(password))
            if hide_from_share_all is not None:
                updates.append('hide_from_share_all = ?')
                params.append(1 if hide_from_share_all else 0)

            if not updates:
                return None

            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(gallery_id)
            cursor.execute(f"UPDATE galleries SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

            if is_admin:
                return admin_get_gallery(gallery_id)
            return get_gallery(gallery_id, owner_token)
    except Exception as e:
        logger.error(f"更新画集访问控制失败: {e}")
        return None


def verify_gallery_password(gallery_id: int, password: str) -> bool:
    """验证画集密码"""
    try:
        from werkzeug.security import check_password_hash
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM galleries WHERE id = ? AND access_mode = ?', (gallery_id, 'password'))
            row = cursor.fetchone()
            if not row or not row['password_hash']:
                return False
            return check_password_hash(row['password_hash'], password)
    except Exception as e:
        logger.error(f"验证画集密码失败: {e}")
        return False


# ===================== 全部分享链接（管理员专属） =====================
def get_share_all_link() -> Optional[Dict[str, Any]]:
    """获取全部分享链接"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM share_all_links WHERE enabled = 1 ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取全部分享链接失败: {e}")
        return None


def create_or_update_share_all_link(enabled: bool = True, expires_at: Optional[str] = None, rotate: bool = False) -> Optional[Dict[str, Any]]:
    """创建或更新全部分享链接"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM share_all_links ORDER BY id DESC LIMIT 1')
            existing = cursor.fetchone()

            expires_value = _parse_datetime(expires_at) if expires_at else None

            if existing and not rotate:
                # 更新现有链接
                cursor.execute('''
                    UPDATE share_all_links
                    SET enabled = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (1 if enabled else 0, expires_value, existing['id']))
                conn.commit()
                cursor.execute('SELECT * FROM share_all_links WHERE id = ?', (existing['id'],))
            else:
                # 创建新链接（或轮换）
                share_token = secrets.token_urlsafe(24)
                if existing:
                    # 禁用旧链接
                    cursor.execute('UPDATE share_all_links SET enabled = 0 WHERE id = ?', (existing['id'],))
                cursor.execute('''
                    INSERT INTO share_all_links (share_token, enabled, expires_at)
                    VALUES (?, ?, ?)
                ''', (share_token, 1 if enabled else 0, expires_value))
                conn.commit()
                cursor.execute('SELECT * FROM share_all_links WHERE share_token = ?', (share_token,))

            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"创建/更新全部分享链接失败: {e}")
        return None


def get_share_all_galleries(share_token: str, page: int = 1, limit: int = 50) -> Optional[Dict[str, Any]]:
    """通过全部分享链接获取画集列表（自动包含所有画集，排除隐藏和仅管理员可见的）"""
    page = max(1, int(page or 1))
    limit = max(1, min(100, int(limit or 50)))
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 验证分享链接
            cursor.execute('''
                SELECT * FROM share_all_links
                WHERE share_token = ? AND enabled = 1
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''', (share_token,))
            if not cursor.fetchone():
                return None

            offset = (page - 1) * limit
            # 获取画集列表，所有画集都返回封面（优先手动设置，否则用第一张图）
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.share_token, g.access_mode,
                       g.created_at, g.updated_at,
                       (SELECT COUNT(*) FROM gallery_images WHERE gallery_id = g.id) as image_count,
                       COALESCE(g.cover_image, (
                           SELECT fs.encrypted_id
                           FROM gallery_images gi2
                           JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                           WHERE gi2.gallery_id = g.id
                           ORDER BY gi2.added_at ASC
                           LIMIT 1
                       )) AS cover_image
                FROM galleries g
                WHERE g.hide_from_share_all = 0
                AND g.access_mode != 'admin_only'
                ORDER BY g.updated_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            items = [dict(row) for row in cursor.fetchall()]

            # 获取总数
            cursor.execute('''
                SELECT COUNT(*) FROM galleries
                WHERE hide_from_share_all = 0 AND access_mode != 'admin_only'
            ''')
            total = cursor.fetchone()[0]

            return {
                'items': items,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': page * limit < total
            }
    except Exception as e:
        logger.error(f"获取全部分享画集列表失败: {e}")
        return None


def _validate_share_all_token(cursor, share_token: str) -> bool:
    """验证全部分享链接有效性"""
    cursor.execute('''
        SELECT 1 FROM share_all_links
        WHERE share_token = ? AND enabled = 1
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        LIMIT 1
    ''', (share_token,))
    return cursor.fetchone() is not None


def get_share_all_gallery(share_token: str, gallery_id: int) -> Optional[Dict[str, Any]]:
    """在全部分享上下文中获取单个画集信息（不含图片）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if not _validate_share_all_token(cursor, share_token):
                return None

            cursor.execute('''
                SELECT g.id, g.name, g.description, g.access_mode,
                       g.hide_from_share_all, g.created_at, g.updated_at,
                       (SELECT COUNT(*) FROM gallery_images WHERE gallery_id = g.id) AS image_count
                FROM galleries g
                WHERE g.id = ?
                  AND g.hide_from_share_all = 0
                  AND g.access_mode != 'admin_only'
                LIMIT 1
            ''', (gallery_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Share-all 获取画集失败: {e}")
        return None


def get_share_all_gallery_images(
    share_token: str,
    gallery_id: int,
    page: int = 1,
    limit: int = 50
) -> Optional[Dict[str, Any]]:
    """在全部分享上下文中获取画集图片（不检查解锁 cookie，由 API 层处理）"""
    page = max(1, int(page or 1))
    limit = max(1, min(200, int(limit or 50)))
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if not _validate_share_all_token(cursor, share_token):
                return None

            # 确保画集在 share-all 中可见
            cursor.execute('''
                SELECT 1 FROM galleries
                WHERE id = ?
                  AND hide_from_share_all = 0
                  AND access_mode != 'admin_only'
                LIMIT 1
            ''', (gallery_id,))
            if not cursor.fetchone():
                return None

            offset = (page - 1) * limit
            cursor.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
            total = cursor.fetchone()[0]

            cursor.execute('''
                SELECT fs.encrypted_id, fs.original_filename, fs.file_size, fs.created_at,
                       fs.cdn_cached, fs.cdn_url, fs.mime_type, gi.added_at
                FROM gallery_images gi
                JOIN file_storage fs ON gi.encrypted_id = fs.encrypted_id
                WHERE gi.gallery_id = ?
                ORDER BY gi.added_at DESC
                LIMIT ? OFFSET ?
            ''', (gallery_id, limit, offset))
            items = [dict(r) for r in cursor.fetchall()]
            return {'items': items, 'total': total, 'page': page, 'limit': limit}
    except Exception as e:
        logger.error(f"Share-all 获取画集图片失败: {e}")
        return None


# ===================== 画集 Token 授权管理 =====================
def grant_gallery_token_access(
    gallery_id: int,
    token: str,
    owner_token: Optional[str] = None,
    expires_at: Optional[str] = None,
    is_admin: bool = False
) -> bool:
    """授权 Token 访问画集"""
    try:
        expires_value = _parse_datetime(expires_at) if expires_at else None
        with get_connection() as conn:
            cursor = conn.cursor()
            # 验证权限
            if is_admin:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ?', (gallery_id,))
            else:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return False
            # 验证 token 可用（存在 + 未禁用 + 未过期）
            cursor.execute('''
                SELECT 1 FROM auth_tokens
                WHERE token = ? AND is_active = 1
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''', (token,))
            if not cursor.fetchone():
                return False
            cursor.execute('''
                INSERT OR REPLACE INTO gallery_token_access (gallery_id, token, expires_at, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (gallery_id, token, expires_value))
            logger.info(f"授权 Token 访问画集: gallery_id={gallery_id}, token={token[:12]}...")
            return True
    except Exception as e:
        logger.error(f"授权 Token 访问画集失败: {e}")
        return False


def revoke_gallery_token_access(
    gallery_id: int,
    token: str,
    owner_token: Optional[str] = None,
    is_admin: bool = False
) -> bool:
    """撤销 Token 访问画集权限"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if is_admin:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ?', (gallery_id,))
            else:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return False
            cursor.execute('DELETE FROM gallery_token_access WHERE gallery_id = ? AND token = ?', (gallery_id, token))
            if cursor.rowcount > 0:
                logger.info(f"撤销 Token 访问画集: gallery_id={gallery_id}, token={token[:12]}...")
                return True
            return False
    except Exception as e:
        logger.error(f"撤销 Token 访问画集失败: {e}")
        return False


def list_gallery_token_access(
    gallery_id: int,
    owner_token: Optional[str] = None,
    is_admin: bool = False
) -> Optional[List[Dict[str, Any]]]:
    """获取画集的授权 Token 列表"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if is_admin:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ?', (gallery_id,))
            else:
                cursor.execute('SELECT 1 FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, owner_token))
            if not cursor.fetchone():
                return None
            cursor.execute('''
                SELECT gta.token, gta.expires_at, gta.created_at,
                       at.description, at.is_active,
                       CASE WHEN at.expires_at IS NOT NULL AND at.expires_at < CURRENT_TIMESTAMP THEN 1 ELSE 0 END AS token_expired
                FROM gallery_token_access gta
                LEFT JOIN auth_tokens at ON gta.token = at.token
                WHERE gta.gallery_id = ?
                ORDER BY gta.created_at DESC
            ''', (gallery_id,))
            items = []
            for row in cursor.fetchall():
                data = dict(row)
                token_full = data.pop('token', '')
                data['token_masked'] = f"{token_full[:8]}...{token_full[-4:]}" if len(token_full) > 12 else token_full
                data['token'] = token_full
                items.append(data)
            return items
    except Exception as e:
        logger.error(f"获取画集授权 Token 列表失败: {e}")
        return None


def is_token_authorized_for_gallery(gallery_id: int, token: str) -> bool:
    """检查 Token 是否有权访问画集"""
    if not token:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM gallery_token_access
                WHERE gallery_id = ? AND token = ?
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''', (gallery_id, token))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"检查 Token 画集授权失败: {e}")
        return False


def is_gallery_owner(gallery_id: int, token: str) -> bool:
    """检查 Token 是否为画集所有者"""
    if not token:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM galleries WHERE id = ? AND owner_token = ?', (gallery_id, token))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"检查画集所有权失败: {e}")
        return False


__all__ = [
    # 连接管理
    'get_connection',
    # 初始化
    'init_database',
    # 文件操作
    'get_file_info', 'save_file_info', 'update_file_path_in_db',
    'update_cdn_cache_status', 'update_access_count', 'delete_files_by_ids',
    # 统计（admin_module.py 兼容）
    'get_all_files_count', 'get_total_size', 'get_stats',
    'get_recent_uploads', 'get_uncached_files',
    # Token
    'generate_auth_token', 'create_auth_token', 'verify_auth_token',
    'update_token_usage', 'get_token_info', 'get_token_uploads',
    # Token 管理（管理员后台）
    'admin_list_tokens', 'admin_create_token',
    'admin_update_token_status', 'admin_delete_token',
    # 公告
    'get_announcement', 'update_announcement',
    # 系统设置
    'init_system_settings', 'migrate_env_settings', 'get_system_setting', 'get_all_system_settings',
    'update_system_setting', 'update_system_settings', 'get_public_settings',
    'get_system_setting_int', 'get_upload_count_today',
    'is_guest_upload_allowed', 'is_token_upload_allowed', 'is_token_generation_allowed',
    'disable_guest_tokens', 'disable_all_tokens',
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
]


# ===================== 管理员画集操作 =====================
def admin_create_gallery(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """管理员创建画集（使用内部 admin owner token）"""
    try:
        token = _get_admin_gallery_owner_token()
        if not token:
            token = _ensure_admin_gallery_owner_token()
        if not token:
            logger.error("无法获取 admin gallery owner token")
            return None
        return create_gallery(token, name, description)
    except Exception as e:
        logger.error(f"Admin 创建画集失败: {e}")
        return None


def admin_get_gallery(gallery_id: int) -> Optional[Dict[str, Any]]:
    """管理员获取画集详情（无所有者限制）"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            cur.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
            data['image_count'] = cur.fetchone()[0]
            # 优先使用手动设置的封面，否则取第一张图（按添加时间 ASC）
            if not data.get('cover_image'):
                cur.execute('''
                    SELECT fs.encrypted_id FROM gallery_images gi
                    JOIN file_storage fs ON gi.encrypted_id = fs.encrypted_id
                    WHERE gi.gallery_id = ? ORDER BY gi.added_at ASC LIMIT 1
                ''', (gallery_id,))
                cover = cur.fetchone()
                data['cover_image'] = cover[0] if cover else None
            return data
    except Exception as e:
        logger.error(f"Admin 获取画集失败: {e}")
        return None


def admin_list_galleries(page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """管理员获取画集列表"""
    page = max(1, int(page or 1))
    limit = max(1, min(200, int(limit or 50)))
    try:
        admin_token = _get_admin_gallery_owner_token()
        with get_connection() as conn:
            cur = conn.cursor()
            where = 'WHERE g.owner_token = ?' if admin_token else ''
            params = [admin_token] if admin_token else []
            cur.execute(f'SELECT COUNT(*) FROM galleries g {where}', params)
            total = cur.fetchone()[0]
            offset = (page - 1) * limit
            # 优先使用手动设置的封面，否则取第一张图（按添加时间 ASC）
            cur.execute(f'''
                SELECT g.*,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT fs.encrypted_id FROM gallery_images gi2
                        JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                        WHERE gi2.gallery_id = g.id ORDER BY gi2.added_at ASC LIMIT 1
                    )) AS cover_image
                FROM galleries g {where}
                ORDER BY g.updated_at DESC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])
            items = [dict(r) for r in cur.fetchall()]
            return {'items': items, 'total': total, 'page': page, 'limit': limit}
    except Exception as e:
        logger.error(f"Admin 获取画集列表失败: {e}")
        return {'items': [], 'total': 0, 'page': page, 'limit': limit}


def admin_update_gallery(gallery_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """管理员更新画集（无所有者限制）"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            updates, params = [], []
            if name is not None:
                updates.append('name = ?')
                params.append(str(name).strip())
            if description is not None:
                updates.append('description = ?')
                params.append(str(description).strip()[:500] or None)
            if not updates:
                return admin_get_gallery(gallery_id)
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(gallery_id)
            cur.execute(f'UPDATE galleries SET {", ".join(updates)} WHERE id = ?', params)
            if cur.rowcount == 0:
                return None
            return admin_get_gallery(gallery_id)
    except Exception as e:
        logger.error(f"Admin 更新画集失败: {e}")
        return None


def admin_delete_gallery(gallery_id: int) -> bool:
    """管理员删除画集（无所有者限制）"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM galleries WHERE id = ?', (gallery_id,))
            return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Admin 删除画集失败: {e}")
        return False


def admin_add_images_to_gallery(gallery_id: int, encrypted_ids: List[str]) -> Dict[str, Any]:
    """管理员添加图片到画集（无所有权限制）"""
    result = {'added': 0, 'skipped': 0, 'not_found': []}
    if not encrypted_ids:
        return result
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT 1 FROM galleries WHERE id = ?', (gallery_id,))
            if not cur.fetchone():
                return result
            normalized = list(dict.fromkeys([str(e).strip() for e in encrypted_ids if str(e).strip()]))
            if not normalized:
                return result
            placeholders = ','.join('?' * len(normalized))
            cur.execute(f'SELECT encrypted_id FROM file_storage WHERE encrypted_id IN ({placeholders})', normalized)
            exists = {r[0] for r in cur.fetchall()}
            for eid in normalized:
                if eid not in exists:
                    result['not_found'].append(eid)
            to_insert = [(gallery_id, eid) for eid in normalized if eid in exists]
            before = conn.total_changes
            cur.executemany('INSERT OR IGNORE INTO gallery_images (gallery_id, encrypted_id) VALUES (?, ?)', to_insert)
            inserted = conn.total_changes - before
            result['added'] = inserted
            result['skipped'] = max(0, len(to_insert) - inserted)
            cur.execute('UPDATE galleries SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
            return result
    except Exception as e:
        logger.error(f"Admin 添加图片到画集失败: {e}")
        return result


def admin_remove_images_from_gallery(gallery_id: int, encrypted_ids: List[str]) -> int:
    """管理员从画集移除图片"""
    if not encrypted_ids:
        return 0
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT id, cover_image FROM galleries WHERE id = ?', (gallery_id,))
            row = cur.fetchone()
            if not row:
                return 0
            current_cover = row['cover_image']
            placeholders = ','.join('?' * len(encrypted_ids))
            cur.execute(f'DELETE FROM gallery_images WHERE gallery_id = ? AND encrypted_id IN ({placeholders})', [gallery_id] + encrypted_ids)
            removed = cur.rowcount
            # 如果移除了当前封面，清除封面设置
            if current_cover and current_cover in encrypted_ids:
                cur.execute('UPDATE galleries SET cover_image = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
                logger.info(f"封面图片被移除，清除封面设置: gallery_id={gallery_id}")
            else:
                cur.execute('UPDATE galleries SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (gallery_id,))
            return removed
    except Exception as e:
        logger.error(f"Admin 从画集移除图片失败: {e}")
        return 0


def admin_get_gallery_images(gallery_id: int, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """管理员获取画集图片"""
    page = max(1, int(page or 1))
    limit = max(1, min(200, int(limit or 50)))
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT 1 FROM galleries WHERE id = ?', (gallery_id,))
            if not cur.fetchone():
                return {'items': [], 'total': 0, 'page': page, 'limit': limit}
            offset = (page - 1) * limit
            cur.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
            total = cur.fetchone()[0]
            cur.execute('''
                SELECT fs.encrypted_id, fs.original_filename, fs.file_size, fs.created_at,
                       fs.cdn_cached, fs.cdn_url, fs.mime_type, gi.added_at
                FROM gallery_images gi
                JOIN file_storage fs ON gi.encrypted_id = fs.encrypted_id
                WHERE gi.gallery_id = ?
                ORDER BY gi.added_at DESC
                LIMIT ? OFFSET ?
            ''', (gallery_id, limit, offset))
            items = [dict(r) for r in cur.fetchall()]
            return {'items': items, 'total': total, 'page': page, 'limit': limit}
    except Exception as e:
        logger.error(f"Admin 获取画集图片失败: {e}")
        return {'items': [], 'total': 0, 'page': page, 'limit': limit}


def admin_update_gallery_share(gallery_id: int, enabled: bool, expires_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """管理员更新画集分享设置"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT share_token FROM galleries WHERE id = ?', (gallery_id,))
            row = cur.fetchone()
            if not row:
                return None
            share_token = row[0]
            if enabled and not share_token:
                share_token = secrets.token_urlsafe(24)
            expires_value = _parse_datetime(expires_at) if expires_at else None
            cur.execute('''
                UPDATE galleries
                SET share_enabled = ?, share_token = ?, share_expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (1 if enabled else 0, share_token if enabled else None, expires_value if enabled else None, gallery_id))
            return admin_get_gallery(gallery_id)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Admin 更新画集分享失败: {e}")
        return None
