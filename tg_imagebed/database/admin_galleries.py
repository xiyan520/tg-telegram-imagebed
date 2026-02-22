#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理员画集（owner_type='admin' 区分所有权，无虚拟 token）"""
import secrets
from typing import Optional, Dict, Any, List

from ..config import logger
from .connection import get_connection
from .tokens import _parse_datetime


# ===================== 管理员画集操作 =====================
def admin_create_gallery(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """管理员创建画集（owner_type='admin'，无需 token）"""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO galleries (owner_type, name, description)
                VALUES ('admin', ?, ?)
            ''', (name.strip(), (description or '').strip()[:500] or None))
            gallery_id = cur.lastrowid
            cur.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
            row = cur.fetchone()
            logger.info(f"Admin 创建画集: ID={gallery_id}, name={name}")
            return dict(row) if row else None
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

def admin_list_galleries(page: int = 1, limit: int = 50, search: Optional[str] = None, sort: Optional[str] = None) -> Dict[str, Any]:
    """管理员获取画集列表（支持搜索和排序）"""
    page = max(1, int(page or 1))
    limit = max(1, min(200, int(limit or 50)))
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            # 构建 WHERE 条件
            where_clauses = ["g.owner_type = 'admin'"]
            params: list = []
            if search and search.strip():
                where_clauses.append("g.name LIKE ?")
                params.append(f"%{search.strip()}%")
            where_sql = " AND ".join(where_clauses)

            # 计数
            cur.execute(f"SELECT COUNT(*) FROM galleries g WHERE {where_sql}", params)
            total = cur.fetchone()[0]

            # 排序
            sort_map = {
                'newest': 'g.updated_at DESC',
                'oldest': 'g.created_at ASC',
                'most_images': 'image_count DESC, g.updated_at DESC',
                'name': 'g.name ASC',
            }
            order_sql = sort_map.get(sort or '', 'g.updated_at DESC')

            offset = (page - 1) * limit
            query_params = params + [limit, offset]
            cur.execute(f'''
                SELECT g.*,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT fs.encrypted_id FROM gallery_images gi2
                        JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                        WHERE gi2.gallery_id = g.id ORDER BY gi2.added_at ASC LIMIT 1
                    )) AS resolved_cover_image
                FROM galleries g
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
            ''', query_params)
            items = [dict(r) for r in cur.fetchall()]
            for item in items:
                item['cover_image'] = item.pop('resolved_cover_image', None)
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