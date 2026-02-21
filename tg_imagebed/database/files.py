#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件 CRUD + 统计查询"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..config import logger
from .connection import get_connection, db_retry


# ===================== 文件存储操作 =====================
def get_file_info(encrypted_id: str) -> Optional[Dict[str, Any]]:
    """获取文件信息"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM file_storage WHERE encrypted_id = ?', (encrypted_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


@db_retry(max_attempts=3, base_delay=0.1, max_delay=2.0)
def save_file_info(encrypted_id: str, file_info: Dict[str, Any]) -> None:
    """保存文件信息到数据库（带重试）"""
    from .settings import get_system_setting

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
                group_chat_id, auth_token, storage_backend, storage_key,
                storage_meta, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            file_info.get('group_chat_id'),
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

@db_retry(max_attempts=3, base_delay=0.1, max_delay=2.0)
def update_cdn_cache_status(encrypted_id: str, cached: bool) -> None:
    """更新CDN缓存状态（带重试）"""
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


def get_user_uploads(username: str, limit: int = 10, page: int = 1) -> tuple:
    """获取指定用户的上传记录（分页）

    Args:
        username: 用户名（与上传时保存的 username 字段一致）
        limit: 每页数量
        page: 页码（从1开始）

    Returns:
        (files_list, total_count) 元组
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        offset = (page - 1) * limit

        cursor.execute(
            'SELECT COUNT(*) FROM file_storage WHERE username = ?',
            (username,)
        )
        total = cursor.fetchone()[0]

        cursor.execute('''
            SELECT encrypted_id, original_filename, file_size,
                   created_at, username, mime_type
            FROM file_storage
            WHERE username = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (username, limit, offset))

        files = [dict(row) for row in cursor.fetchall()]
        return files, total


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
