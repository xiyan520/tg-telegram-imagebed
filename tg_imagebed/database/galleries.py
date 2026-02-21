#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户画集 + 访问控制 + 分享 + Token 授权"""
import sqlite3
import secrets
from typing import Optional, Dict, Any, List

from ..config import logger
from .connection import get_connection
from .tokens import _parse_datetime


# ===================== 画集 CRUD =====================

def _read_gallery(cursor, gallery_id: int) -> Optional[Dict[str, Any]]:
    """用已有 cursor 读取画集（避免在未提交事务中开新连接读不到最新数据）"""
    cursor.execute('SELECT * FROM galleries WHERE id = ?', (gallery_id,))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    cursor.execute('SELECT COUNT(*) FROM gallery_images WHERE gallery_id = ?', (gallery_id,))
    data['image_count'] = cursor.fetchone()[0]
    return data


def create_gallery(owner_token: str, name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """创建画集"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO galleries (owner_type, owner_token, name, description)
                VALUES ('token', ?, ?, ?)
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
            # 注意：使用 resolved_cover_image 避免与 g.* 中的 cover_image 列名冲突
            cursor.execute('''
                SELECT g.*,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT fs.encrypted_id FROM gallery_images gi2
                        JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                        WHERE gi2.gallery_id = g.id ORDER BY gi2.added_at ASC LIMIT 1
                    )) AS resolved_cover_image
                FROM galleries g
                WHERE g.owner_token = ?
                ORDER BY g.updated_at DESC
                LIMIT ? OFFSET ?
            ''', (owner_token, limit, offset))
            items = [dict(row) for row in cursor.fetchall()]
            for item in items:
                item['cover_image'] = item.pop('resolved_cover_image', None)
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
            return _read_gallery(cursor, gallery_id)
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
            return _read_gallery(cursor, gallery_id)
    except Exception as e:
        logger.error(f"设置画集封面失败: {e}")
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

# ===================== 分享 =====================
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
            return _read_gallery(cursor, gallery_id)
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
                from .admin_galleries import admin_get_gallery
                return admin_get_gallery(gallery_id)
            return _read_gallery(cursor, gallery_id)
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
