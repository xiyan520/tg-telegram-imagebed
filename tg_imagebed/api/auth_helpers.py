#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证辅助模块 - 提取公共的 Token 验证逻辑

供 auth.py 和 galleries.py 共享使用，避免重复代码。
"""
from flask import request, jsonify
from typing import Optional, Dict, Any

from ..database import verify_auth_token, verify_tg_session, get_system_setting


def extract_bearer_token(req=None) -> str:
    """
    从 Authorization 头提取 Bearer Token

    Args:
        req: Flask request 对象，默认使用当前请求上下文

    Returns:
        提取到的 token 字符串，未找到则返回空字符串
    """
    if req is None:
        req = request
    auth_header = (req.headers.get('Authorization') or '').strip()
    if not auth_header:
        return ''
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()
    return auth_header


def verify_request_token(req=None):
    """
    提取并验证请求中的 Token

    优先从 Authorization 头提取，其次从查询参数 token 获取。

    Args:
        req: Flask request 对象，默认使用当前请求上下文

    Returns:
        tuple: (token, error_response, status_code)
        - 验证成功: (token_str, None, None)
        - 验证失败: (None, jsonify_response, http_status)
    """
    if req is None:
        req = request
    token = extract_bearer_token(req)
    if not token:
        token = req.args.get('token', '')
    if not token:
        return None, jsonify({'success': False, 'error': '未提供Token'}), 401
    verification = verify_auth_token(token)
    if not verification['valid']:
        return None, jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 401
    issue = get_bound_token_session_issue(verification.get('token_data'), req)
    if issue:
        return None, jsonify({'success': False, 'error': issue['reason']}), issue['status']
    return token, None, None


def get_bound_token_session_issue(token_data: Optional[Dict[str, Any]], req=None) -> Optional[Dict[str, Any]]:
    """
    检查「已绑定 TG 用户」的 Token 是否绑定在有效 TG 会话上。

    规则：
    - 非绑定 Token（tg_user_id 为空）不受影响；
    - 当 TG 认证启用时，绑定 Token 必须携带有效 tg_session，且用户一致。

    Returns:
        无问题返回 None；
        有问题返回 {'status': int, 'reason': str, 'code': str}
    """
    if not token_data:
        return None

    tg_user_id = token_data.get('tg_user_id')
    if tg_user_id in (None, '', 0):
        return None

    # 关闭 TG 认证时，不对绑定 token 追加会话约束，避免历史 token 全量失效
    if str(get_system_setting('tg_auth_enabled') or '0') != '1':
        return None

    if req is None:
        req = request
    tg_session_token = (req.cookies.get('tg_session') or '').strip()
    session_info = verify_tg_session(tg_session_token) if tg_session_token else None

    if not session_info:
        return {
            'status': 401,
            'reason': '该 Token 已绑定 Telegram 账号，当前设备会话已失效，请先重新登录 TG',
            'code': 'tg_session_required'
        }

    if str(session_info.get('tg_user_id')) != str(tg_user_id):
        return {
            'status': 403,
            'reason': '当前 TG 账号与 Token 绑定账号不一致',
            'code': 'tg_user_mismatch'
        }

    return None
