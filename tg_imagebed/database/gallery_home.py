#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画集首页编排配置与数据聚合"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ..config import logger
from .connection import get_connection

_VALID_SOURCE_MODE = {'hybrid', 'manual', 'auto'}
_VALID_AUTO_SORT = {
    'updated_desc',
    'image_count_desc',
    'editor_pick_desc',
    'created_desc',
    'name_asc',
}
_VALID_HERO_MODE = {'auto', 'manual'}


def _to_int(value: Any, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _to_bool_int(value: Any, default: int = 0) -> int:
    if value is None:
        return 1 if default else 0
    return 1 if bool(value) else 0


def _normalize_text(value: Any, max_len: int = 255) -> str:
    return str(value or '').strip()[:max_len]


def _serialize_home_config(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    data = dict(row or {})
    return {
        'hero_mode': data.get('hero_mode') if data.get('hero_mode') in _VALID_HERO_MODE else 'auto',
        'hero_gallery_id': data.get('hero_gallery_id'),
        'mobile_items_per_section': _to_int(data.get('mobile_items_per_section'), 4, minimum=1, maximum=12),
        'desktop_items_per_section': _to_int(data.get('desktop_items_per_section'), 8, minimum=1, maximum=24),
        'enable_recent_strip': bool(_to_int(data.get('enable_recent_strip'), 1, minimum=0, maximum=1)),
    }


def _serialize_section(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': row['id'],
        'section_key': row['section_key'],
        'title': row['title'] or '',
        'subtitle': row['subtitle'] or '',
        'description': row['description'] or '',
        'enabled': bool(_to_int(row.get('enabled'), 1, minimum=0, maximum=1)),
        'display_order': _to_int(row.get('display_order'), 0, minimum=0, maximum=999),
        'max_items': _to_int(row.get('max_items'), 8, minimum=1, maximum=30),
        'source_mode': row['source_mode'] if row.get('source_mode') in _VALID_SOURCE_MODE else 'hybrid',
        'auto_sort': row['auto_sort'] if row.get('auto_sort') in _VALID_AUTO_SORT else 'updated_desc',
        'auto_window_days': _to_int(row.get('auto_window_days'), 0, minimum=0, maximum=3650),
    }


def _gallery_base_query(where_clause: str = '') -> str:
    where_sql = f' AND {where_clause}' if where_clause else ''
    return f'''
        SELECT
            g.id,
            g.name,
            g.description,
            g.card_subtitle,
            g.editor_pick_weight,
            g.created_at,
            g.updated_at,
            (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
            COALESCE(g.cover_image, (
                SELECT fs.encrypted_id
                FROM gallery_images gi2
                JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                WHERE gi2.gallery_id = g.id
                ORDER BY gi2.added_at ASC
                LIMIT 1
            )) AS cover_image
        FROM galleries g
        WHERE g.share_enabled = 1
          AND g.access_mode = 'public'
          AND COALESCE(g.homepage_expose_enabled, 1) = 1
          {where_sql}
    '''


def _auto_sort_sql(auto_sort: str) -> str:
    if auto_sort == 'image_count_desc':
        return 'image_count DESC, g.updated_at DESC'
    if auto_sort == 'editor_pick_desc':
        return 'COALESCE(g.editor_pick_weight, 0) DESC, g.updated_at DESC'
    if auto_sort == 'created_desc':
        return 'g.created_at DESC'
    if auto_sort == 'name_asc':
        return 'g.name COLLATE NOCASE ASC, g.updated_at DESC'
    return 'g.updated_at DESC'


def get_gallery_home_config() -> Dict[str, Any]:
    """获取首页全局配置"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM gallery_home_config WHERE id = 1')
            row = cursor.fetchone()
            return _serialize_home_config(dict(row) if row else None)
    except Exception as e:
        logger.error(f"获取首页配置失败: {e}")
        return _serialize_home_config(None)


def update_gallery_home_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """更新首页全局配置"""
    payload = dict(data or {})

    hero_mode = payload.get('hero_mode')
    if hero_mode not in _VALID_HERO_MODE:
        hero_mode = 'auto'
    hero_gallery_id = payload.get('hero_gallery_id')
    if hero_gallery_id in ('', None):
        hero_gallery_id = None
    else:
        hero_gallery_id = _to_int(hero_gallery_id, 0, minimum=1, maximum=2_147_483_647)
        if hero_gallery_id <= 0:
            hero_gallery_id = None

    mobile_items = _to_int(payload.get('mobile_items_per_section'), 4, minimum=1, maximum=12)
    desktop_items = _to_int(payload.get('desktop_items_per_section'), 8, minimum=1, maximum=24)
    enable_recent_strip = _to_bool_int(payload.get('enable_recent_strip'), 1)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE gallery_home_config
                SET hero_mode = ?, hero_gallery_id = ?, mobile_items_per_section = ?,
                    desktop_items_per_section = ?, enable_recent_strip = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (hero_mode, hero_gallery_id, mobile_items, desktop_items, enable_recent_strip))
            cursor.execute('SELECT * FROM gallery_home_config WHERE id = 1')
            row = cursor.fetchone()
            return _serialize_home_config(dict(row) if row else None)
    except Exception as e:
        logger.error(f"更新首页配置失败: {e}")
        raise


def list_gallery_home_sections(include_items: bool = False) -> List[Dict[str, Any]]:
    """获取首页分区配置（可选含手动编排项）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT *
                FROM gallery_home_sections
                ORDER BY display_order ASC, id ASC
            ''')
            rows = [dict(r) for r in cursor.fetchall()]
            sections = [_serialize_section(row) for row in rows]

            if not include_items:
                return sections

            for section in sections:
                cursor.execute('''
                    SELECT
                        g.id,
                        g.name,
                        g.description,
                        g.card_subtitle,
                        g.share_enabled,
                        g.access_mode,
                        COALESCE(g.homepage_expose_enabled, 1) AS homepage_expose_enabled,
                        g.updated_at,
                        (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                        COALESCE(g.cover_image, (
                            SELECT fs.encrypted_id
                            FROM gallery_images gi2
                            JOIN file_storage fs ON gi2.encrypted_id = fs.encrypted_id
                            WHERE gi2.gallery_id = g.id
                            ORDER BY gi2.added_at ASC
                            LIMIT 1
                        )) AS cover_image
                    FROM gallery_home_section_items si
                    JOIN galleries g ON g.id = si.gallery_id
                    WHERE si.section_id = ?
                    ORDER BY si.pin_order ASC, si.id ASC
                ''', (section['id'],))
                items = []
                for row in cursor.fetchall():
                    item = dict(row)
                    item['publishable'] = (
                        item.get('share_enabled') == 1
                        and item.get('access_mode') == 'public'
                        and _to_int(item.get('homepage_expose_enabled'), 1, minimum=0, maximum=1) == 1
                    )
                    items.append(item)
                section['items'] = items
                section['item_ids'] = [it['id'] for it in items]
            return sections
    except Exception as e:
        logger.error(f"获取首页分区失败: {e}")
        return []


def update_gallery_home_section(section_key: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """更新单个首页分区配置"""
    if not section_key:
        return None
    payload = dict(data or {})
    updates = []
    params: List[Any] = []

    if 'title' in payload:
        updates.append('title = ?')
        params.append(_normalize_text(payload.get('title'), max_len=80))
    if 'subtitle' in payload:
        updates.append('subtitle = ?')
        params.append(_normalize_text(payload.get('subtitle'), max_len=80))
    if 'description' in payload:
        updates.append('description = ?')
        params.append(_normalize_text(payload.get('description'), max_len=220))
    if 'enabled' in payload:
        updates.append('enabled = ?')
        params.append(_to_bool_int(payload.get('enabled'), 1))
    if 'display_order' in payload:
        updates.append('display_order = ?')
        params.append(_to_int(payload.get('display_order'), 0, minimum=0, maximum=999))
    if 'max_items' in payload:
        updates.append('max_items = ?')
        params.append(_to_int(payload.get('max_items'), 8, minimum=1, maximum=30))
    if 'source_mode' in payload:
        mode = str(payload.get('source_mode') or '').strip()
        if mode in _VALID_SOURCE_MODE:
            updates.append('source_mode = ?')
            params.append(mode)
    if 'auto_sort' in payload:
        auto_sort = str(payload.get('auto_sort') or '').strip()
        if auto_sort in _VALID_AUTO_SORT:
            updates.append('auto_sort = ?')
            params.append(auto_sort)
    if 'auto_window_days' in payload:
        updates.append('auto_window_days = ?')
        params.append(_to_int(payload.get('auto_window_days'), 0, minimum=0, maximum=3650))

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(section_key)
                cursor.execute(
                    f'UPDATE gallery_home_sections SET {", ".join(updates)} WHERE section_key = ?',
                    params
                )
            cursor.execute('SELECT * FROM gallery_home_sections WHERE section_key = ?', (section_key,))
            row = cursor.fetchone()
            return _serialize_section(dict(row)) if row else None
    except Exception as e:
        logger.error(f"更新首页分区失败: key={section_key}, err={e}")
        raise


def replace_gallery_home_section_items(section_key: str, gallery_ids: Sequence[Any]) -> Dict[str, Any]:
    """替换分区手动编排项"""
    unique_ids: List[int] = []
    seen = set()
    for raw in list(gallery_ids or [])[:200]:
        gid = _to_int(raw, 0, minimum=1, maximum=2_147_483_647)
        if gid > 0 and gid not in seen:
            seen.add(gid)
            unique_ids.append(gid)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM gallery_home_sections WHERE section_key = ?', (section_key,))
            row = cursor.fetchone()
            if not row:
                return {'section': None, 'saved_gallery_ids': [], 'ignored_gallery_ids': unique_ids}

            section_id = row['id']
            valid_ids = set()
            if unique_ids:
                placeholders = ','.join('?' * len(unique_ids))
                cursor.execute(f'SELECT id FROM galleries WHERE id IN ({placeholders})', unique_ids)
                valid_ids = {int(r['id']) for r in cursor.fetchall()}

            cursor.execute('DELETE FROM gallery_home_section_items WHERE section_id = ?', (section_id,))
            saved_ids: List[int] = []
            for index, gid in enumerate(unique_ids):
                if gid not in valid_ids:
                    continue
                cursor.execute('''
                    INSERT INTO gallery_home_section_items (section_id, gallery_id, pin_order)
                    VALUES (?, ?, ?)
                ''', (section_id, gid, index))
                saved_ids.append(gid)

            ignored = [gid for gid in unique_ids if gid not in valid_ids]
            cursor.execute('UPDATE gallery_home_sections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (section_id,))
            cursor.execute('SELECT * FROM gallery_home_sections WHERE id = ?', (section_id,))
            section_row = cursor.fetchone()

            return {
                'section': _serialize_section(dict(section_row)) if section_row else None,
                'saved_gallery_ids': saved_ids,
                'ignored_gallery_ids': ignored,
            }
    except Exception as e:
        logger.error(f"替换首页分区编排失败: key={section_key}, err={e}")
        raise


def _query_gallery_items(
    cursor,
    *,
    where_clause: str = '',
    where_params: Optional[Sequence[Any]] = None,
    order_clause: str = 'g.updated_at DESC',
    limit: int = 10
) -> List[Dict[str, Any]]:
    limit = _to_int(limit, 10, minimum=1, maximum=100)
    params = list(where_params or [])
    sql = _gallery_base_query(where_clause) + f'\nORDER BY {order_clause}\nLIMIT ?'
    cursor.execute(sql, params + [limit])
    return [dict(row) for row in cursor.fetchall()]


def get_gallery_home_public_payload() -> Dict[str, Any]:
    """获取首页公开编排数据（含自动补位结果）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            config = get_gallery_home_config()
            sections = list_gallery_home_sections(include_items=False)

            section_results: List[Dict[str, Any]] = []
            for section in sections:
                if not section.get('enabled'):
                    continue
                max_items = _to_int(section.get('max_items'), 8, minimum=1, maximum=30)
                source_mode = section.get('source_mode') or 'hybrid'
                items: List[Dict[str, Any]] = []
                used_ids: set[int] = set()

                if source_mode in ('hybrid', 'manual'):
                    cursor.execute('''
                        SELECT si.gallery_id
                        FROM gallery_home_section_items si
                        JOIN gallery_home_sections s ON s.id = si.section_id
                        WHERE s.section_key = ?
                        ORDER BY si.pin_order ASC, si.id ASC
                    ''', (section['section_key'],))
                    pinned_ids = [int(r['gallery_id']) for r in cursor.fetchall()]
                    if pinned_ids:
                        placeholders = ','.join('?' * len(pinned_ids))
                        pinned_order = 'CASE g.id ' + ' '.join(
                            [f'WHEN {gid} THEN {idx}' for idx, gid in enumerate(pinned_ids)]
                        ) + ' END ASC'
                        pinned_items = _query_gallery_items(
                            cursor,
                            where_clause=f'g.id IN ({placeholders})',
                            where_params=pinned_ids,
                            order_clause=pinned_order,
                            limit=max_items,
                        )
                        items.extend(pinned_items)
                        used_ids.update(int(it['id']) for it in pinned_items)

                if source_mode in ('hybrid', 'auto') and len(items) < max_items:
                    where_parts: List[str] = []
                    where_params: List[Any] = []
                    if used_ids:
                        placeholders = ','.join('?' * len(used_ids))
                        where_parts.append(f'g.id NOT IN ({placeholders})')
                        where_params.extend(list(used_ids))
                    window_days = _to_int(section.get('auto_window_days'), 0, minimum=0, maximum=3650)
                    if window_days > 0:
                        where_parts.append("g.updated_at >= datetime('now', ?)")
                        where_params.append(f'-{window_days} days')
                    where_clause = ' AND '.join(where_parts)
                    auto_sort = section.get('auto_sort') or 'updated_desc'
                    auto_items = _query_gallery_items(
                        cursor,
                        where_clause=where_clause,
                        where_params=where_params,
                        order_clause=_auto_sort_sql(auto_sort),
                        limit=max_items - len(items),
                    )
                    items.extend(auto_items)
                    used_ids.update(int(it['id']) for it in auto_items)

                section_results.append({
                    **section,
                    'items': items[:max_items],
                    'item_ids': [int(it['id']) for it in items[:max_items]],
                })

            # Hero：手动优先，失败则回退到第一个分区第一项
            hero_item: Optional[Dict[str, Any]] = None
            if config.get('hero_mode') == 'manual' and config.get('hero_gallery_id'):
                manual_hero = _query_gallery_items(
                    cursor,
                    where_clause='g.id = ?',
                    where_params=[config['hero_gallery_id']],
                    order_clause='g.updated_at DESC',
                    limit=1,
                )
                hero_item = manual_hero[0] if manual_hero else None
            if not hero_item:
                for section in section_results:
                    if section.get('items'):
                        hero_item = section['items'][0]
                        break

            recent_limit = max(
                _to_int(config.get('mobile_items_per_section'), 4, minimum=1, maximum=12),
                _to_int(config.get('desktop_items_per_section'), 8, minimum=1, maximum=24),
            )
            recent_items = _query_gallery_items(
                cursor,
                order_clause='g.updated_at DESC',
                limit=min(24, max(6, recent_limit)),
            )

            return {
                'config': config,
                'sections': section_results,
                'hero': hero_item,
                'recent_items': recent_items if config.get('enable_recent_strip', True) else [],
            }
    except Exception as e:
        logger.error(f"获取首页公开编排数据失败: {e}")
        return {
            'config': _serialize_home_config(None),
            'sections': [],
            'hero': None,
            'recent_items': [],
        }
