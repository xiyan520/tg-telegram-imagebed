#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - 仪表盘活动流
"""
import json
from datetime import datetime
from typing import Any, Dict, List

from flask import request, jsonify

from . import admin_bp
from .admin_helpers import _admin_options
from ..config import logger
from ..utils import add_cache_headers, format_size
from ..database import get_recent_uploads
from ..database.connection import get_connection
from .. import admin_module


def _parse_datetime(value: Any) -> datetime:
    """容错解析时间字符串，失败时返回最小时间用于排序兜底"""
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.min

    raw = str(value).strip()
    if not raw:
        return datetime.min

    # 优先按 ISO 解析（兼容 Z 后缀）
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except Exception:
        pass

    # 兼容 admin_module 安全日志格式: 2026-02-27 12:00:00
    try:
        return datetime.strptime(raw, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return datetime.min


def _to_iso_string(dt: datetime) -> str:
    """统一输出可被前端 Date 解析的字符串"""
    if dt == datetime.min:
        return datetime.now().isoformat()
    return dt.isoformat()


def _build_upload_activity(upload: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    created_dt = _parse_datetime(upload.get('created_at'))
    encrypted_id = str(upload.get('encrypted_id') or '').strip()
    file_size = int(upload.get('file_size') or 0)
    is_group = bool(upload.get('is_group_upload'))
    actor = str(upload.get('username') or 'unknown').strip() or 'unknown'
    filename = str(upload.get('original_filename') or encrypted_id or '未命名文件').strip()

    source = 'group' if is_group else 'web'
    title = '群组上传图片' if is_group else '图片上传'
    desc = f"{filename} · {format_size(file_size)}"

    ts = int(created_dt.timestamp()) if created_dt != datetime.min else 0
    return {
        'id': f"upload:{encrypted_id}:{ts}:{index}",
        'type': 'upload',
        'level': 'info',
        'title': title,
        'description': desc,
        'actor': actor,
        'ip': '',
        'time': _to_iso_string(created_dt),
        'meta': {
            'encrypted_id': encrypted_id,
            'source': source
        },
        'timestamp': created_dt.timestamp() if created_dt != datetime.min else 0.0,
    }


def _security_event_meta(event_type: str) -> Dict[str, str]:
    mapping = {
        'login_success': {'title': '登录成功', 'level': 'success'},
        'login_failed': {'title': '登录失败', 'level': 'warning'},
        'login_locked': {'title': '登录锁定', 'level': 'error'},
        'logout': {'title': '主动登出', 'level': 'info'},
        'session_kicked': {'title': '会话踢出', 'level': 'warning'},
        'password_changed': {'title': '密码变更', 'level': 'warning'},
    }
    return mapping.get(event_type, {'title': event_type or '安全事件', 'level': 'info'})


def _load_security_activities() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM admin_config WHERE key = 'security_log'")
        row = cursor.fetchone()

    logs = json.loads(row[0]) if row and row[0] else []
    activities: List[Dict[str, Any]] = []

    # 数据库存储是追加顺序，这里反转为最新优先
    for index, event in enumerate(reversed(logs)):
        event_type = str(event.get('type') or '').strip()
        meta = _security_event_meta(event_type)
        event_dt = _parse_datetime(event.get('time'))
        ts = int(event_dt.timestamp()) if event_dt != datetime.min else 0
        ip = str(event.get('ip') or '').strip()
        detail = str(event.get('detail') or '').strip()

        activities.append({
            'id': f"security:{event_type}:{ts}:{index}",
            'type': 'security',
            'level': meta['level'],
            'title': meta['title'],
            'description': detail or (f"来源 IP: {ip}" if ip else '系统安全事件'),
            'actor': str(event.get('username') or '').strip(),
            'ip': ip,
            'time': _to_iso_string(event_dt),
            'meta': {
                'event_type': event_type
            },
            'timestamp': event_dt.timestamp() if event_dt != datetime.min else 0.0,
        })

    return activities


def _serialize_activity_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {k: v for k, v in item.items() if k != 'timestamp'}
        for item in items
    ]


@admin_bp.route('/api/admin/dashboard/activity', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_dashboard_activity():
    """仪表盘活动流（上传事件 + 安全事件）"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    activity_type = (request.args.get('type') or 'all').strip().lower()
    if activity_type not in ('all', 'upload', 'security'):
        activity_type = 'all'

    page = max(1, request.args.get('page', default=1, type=int) or 1)
    limit = request.args.get('limit', default=20, type=int) or 20
    limit = max(1, min(50, limit))

    try:
        offset = (page - 1) * limit

        if activity_type == 'upload':
            upload_rows = get_recent_uploads(limit=limit + 1, page=page)
            has_more = len(upload_rows) > limit
            items = [
                _build_upload_activity(row, idx)
                for idx, row in enumerate(upload_rows[:limit])
            ]

        elif activity_type == 'security':
            security_items = _load_security_activities()
            items = security_items[offset:offset + limit]
            has_more = len(security_items) > offset + limit

        else:
            # all: 合并上传与安全日志后统一排序分页
            upload_fetch_limit = min(max(page * limit * 3, limit * 3), 1000)
            upload_rows = get_recent_uploads(limit=upload_fetch_limit, page=1)
            upload_items = [
                _build_upload_activity(row, idx)
                for idx, row in enumerate(upload_rows)
            ]
            security_items = _load_security_activities()

            merged = sorted(
                upload_items + security_items,
                key=lambda x: float(x.get('timestamp') or 0.0),
                reverse=True
            )
            items = merged[offset:offset + limit]
            has_more = len(merged) > offset + limit
            if not has_more and len(upload_rows) >= upload_fetch_limit:
                # 说明上传记录仍可能有后续分页数据（保守给可继续加载）
                has_more = True

        response = jsonify({
            'success': True,
            'data': {
                'items': _serialize_activity_items(items),
                'page': page,
                'limit': limit,
                'has_more': has_more,
                'type': activity_type,
            }
        })
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取仪表盘活动流失败: {e}")
        response = jsonify({
            'success': False,
            'error': '获取活动流失败',
            'data': {
                'items': [],
                'page': page,
                'limit': limit,
                'has_more': False,
                'type': activity_type,
            }
        })
        return add_cache_headers(response, 'no-cache'), 500
