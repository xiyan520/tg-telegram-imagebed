#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证辅助模块 - 提取公共的 Token 验证逻辑

供 auth.py 和 galleries.py 共享使用，避免重复代码。
"""
from flask import request, jsonify

from ..database import verify_auth_token


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
    return token, None, None
