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

            auth_new_columns = [
                ('is_active', 'BOOLEAN DEFAULT 1'),
                ('ip_address', 'TEXT'),
                ('user_agent', 'TEXT'),
                ('description', 'TEXT'),
            ]

            for col_name, col_type in auth_new_columns:
                if col_name not in auth_columns:
                    logger.info(f"添加 {col_name} 列到 auth_tokens")
                    cursor.execute(f'ALTER TABLE auth_tokens ADD COLUMN {col_name} {col_type}')

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

        # 生成 CDN URL
        cdn_url = None
        if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"

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


def update_access_count(encrypted_id: str) -> None:
    """更新访问计数"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE file_storage
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (encrypted_id,))


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
# 默认系统设置
DEFAULT_SYSTEM_SETTINGS = {
    'guest_upload_policy': 'open',  # open/token_only/admin_only
    'guest_token_generation_enabled': '1',  # 0/1
    'guest_existing_tokens_policy': 'keep',  # keep/disable_guest/disable_all
    'max_file_size_mb': '20',  # 最大文件大小（MB）
    'daily_upload_limit': '0',  # 每日上传限制（0=无限制）
    'guest_token_max_upload_limit': '1000',  # 游客 Token 最大上传数
    'guest_token_max_expires_days': '365',  # 游客 Token 最大有效期（天）
    'storage_active_backend': 'telegram',  # 激活的存储后端
    'storage_config_json': '',  # 存储配置 JSON
    'storage_upload_policy_json': '',  # 上传场景路由策略 JSON
}


def init_system_settings() -> None:
    """初始化系统设置（在 admin_config 表中）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for key, default_value in DEFAULT_SYSTEM_SETTINGS.items():
                cursor.execute(
                    'SELECT value FROM admin_config WHERE key = ?', (key,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        'INSERT INTO admin_config (key, value) VALUES (?, ?)',
                        (key, default_value)
                    )
                    logger.info(f"初始化系统设置: {key}={default_value}")
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
            # 敏感配置不打印value，防止泄露密钥
            sensitive_keys = {'storage_config_json', 'storage_upload_policy_json'}
            if key in sensitive_keys:
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
    'init_system_settings', 'get_system_setting', 'get_all_system_settings',
    'update_system_setting', 'update_system_settings', 'get_public_settings',
    'get_system_setting_int', 'get_upload_count_today',
    'is_guest_upload_allowed', 'is_token_upload_allowed', 'is_token_generation_allowed',
    'disable_guest_tokens', 'disable_all_tokens',
]
