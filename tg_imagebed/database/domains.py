#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""域名管理数据访问层"""
import random
from typing import Optional, Dict, Any, List
from urllib.parse import urlsplit

from ..config import logger
from .connection import get_connection, db_retry


def _normalize_domain(value: str) -> str:
    """标准化域名（去协议、去路径、去端口、拒绝@）"""
    raw = str(value or '').strip()
    if not raw:
        return ''
    if '://' in raw:
        parsed = urlsplit(raw)
        raw = (parsed.netloc or '').strip()
    raw = raw.split('/')[0].split('?')[0].split('#')[0].strip()
    if '@' in raw:
        return ''
    return raw


# ===================== 域名 CRUD =====================
@db_retry()
def get_all_domains() -> List[Dict[str, Any]]:
    """获取所有域名，按 sort_order 排序"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, domain, domain_type, use_https, is_active,
                       is_default, sort_order, remark, created_at, updated_at
                FROM custom_domains
                ORDER BY sort_order ASC, id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"获取所有域名失败: {e}")
        return []


@db_retry()
def get_domains_by_type(domain_type: str) -> List[Dict[str, Any]]:
    """按类型获取域名"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, domain, domain_type, use_https, is_active,
                       is_default, sort_order, remark, created_at, updated_at
                FROM custom_domains
                WHERE domain_type = ?
                ORDER BY sort_order ASC, id ASC
            ''', (domain_type,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"按类型获取域名失败: {e}")
        return []


@db_retry()
def get_active_image_domains() -> List[Dict[str, Any]]:
    """获取所有活跃图片域名"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, domain, use_https, is_default, sort_order, remark
                FROM custom_domains
                WHERE domain_type = 'image' AND is_active = 1
                ORDER BY sort_order ASC, id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"获取活跃图片域名失败: {e}")
        return []


@db_retry()
def get_default_domain() -> Optional[Dict[str, Any]]:
    """获取默认域名"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, domain, domain_type, use_https, is_active,
                       is_default, sort_order, remark
                FROM custom_domains
                WHERE is_default = 1
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取默认域名失败: {e}")
        return None


@db_retry()
def add_domain(domain: str, domain_type: str = 'image',
               use_https: int = 1, remark: str = '') -> Optional[int]:
    """添加域名，返回 id"""
    normalized = _normalize_domain(domain)
    if not normalized:
        logger.warning(f"域名标准化失败: {domain}")
        return None
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 检查域名是否已存在
            cursor.execute(
                'SELECT id FROM custom_domains WHERE domain = ?', (normalized,)
            )
            if cursor.fetchone():
                logger.warning(f"域名已存在: {normalized}")
                return None
            cursor.execute('''
                INSERT INTO custom_domains (domain, domain_type, use_https, remark)
                VALUES (?, ?, ?, ?)
            ''', (normalized, domain_type, use_https, remark))
            domain_id = cursor.lastrowid
            logger.info(f"添加域名: {normalized} (type={domain_type}, id={domain_id})")
            return domain_id
    except Exception as e:
        logger.error(f"添加域名失败: {e}")
        return None


@db_retry()
def update_domain(domain_id: int, **kwargs) -> bool:
    """更新域名"""
    allowed_fields = {
        'domain', 'domain_type', 'use_https', 'is_active',
        'is_default', 'sort_order', 'remark'
    }
    updates = {}
    for key, value in kwargs.items():
        if key in allowed_fields:
            if key == 'domain':
                value = _normalize_domain(value)
                if not value:
                    logger.warning("域名标准化失败，跳过更新")
                    return False
            updates[key] = value

    if not updates:
        return True

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ', '.join(f'{k} = ?' for k in updates)
            values = list(updates.values()) + [domain_id]
            cursor.execute(
                f'UPDATE custom_domains SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                values
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"更新域名失败 (id={domain_id}): {e}")
        return False


@db_retry()
def delete_domain(domain_id: int) -> bool:
    """删除域名"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM custom_domains WHERE id = ?', (domain_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"删除域名: id={domain_id}")
            return deleted
    except Exception as e:
        logger.error(f"删除域名失败 (id={domain_id}): {e}")
        return False


@db_retry()
def set_default_domain(domain_id: int) -> bool:
    """设为默认域名（先清除旧默认）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 清除所有默认标记
            cursor.execute('UPDATE custom_domains SET is_default = 0 WHERE is_default = 1')
            # 设置新默认
            cursor.execute(
                'UPDATE custom_domains SET is_default = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (domain_id,)
            )
            success = cursor.rowcount > 0
            if success:
                logger.info(f"设置默认域名: id={domain_id}")
            return success
    except Exception as e:
        logger.error(f"设置默认域名失败 (id={domain_id}): {e}")
        return False


@db_retry()
def get_random_image_domain() -> Optional[str]:
    """随机获取一个活跃图片域名的完整 URL"""
    try:
        domains = get_active_image_domains()
        if not domains:
            return None
        chosen = random.choice(domains)
        scheme = 'https' if chosen.get('use_https', 1) else 'http'
        return f"{scheme}://{chosen['domain']}"
    except Exception as e:
        logger.error(f"随机获取图片域名失败: {e}")
        return None


@db_retry()
def is_allowed_image_domain(host: str) -> bool:
    """检查 host 是否为允许的图片域名"""
    if not host:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM custom_domains
                WHERE domain = ? AND domain_type = 'image' AND is_active = 1
            ''', (host,))
            row = cursor.fetchone()
            return row[0] > 0 if row else False
    except Exception as e:
        logger.error(f"检查图片域名失败: {e}")
        return False


# ===================== 画集域名 =====================
@db_retry()
def get_active_gallery_domains() -> List[Dict[str, Any]]:
    """获取所有活跃画集域名"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, domain, use_https, is_default, sort_order, remark
                FROM custom_domains
                WHERE domain_type = 'gallery' AND is_active = 1
                ORDER BY sort_order ASC, id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"获取活跃画集域名失败: {e}")
        return []


@db_retry()
def is_gallery_domain(host: str) -> bool:
    """检查 host 是否为画集域名"""
    if not host:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM custom_domains
                WHERE domain = ? AND domain_type = 'gallery' AND is_active = 1
            ''', (host,))
            row = cursor.fetchone()
            return row[0] > 0 if row else False
    except Exception as e:
        logger.error(f"检查画集域名失败: {e}")
        return False
