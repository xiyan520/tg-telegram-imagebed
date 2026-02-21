#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - 初始化设置
"""
from flask import request, jsonify

from . import admin_bp
from ..config import logger


def _is_admin_configured() -> bool:
    """检查管理员账号是否已配置（admin_config 表中有 username 和 password_hash）"""
    try:
        from ..database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
            username_row = cursor.fetchone()
            cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
            password_row = cursor.fetchone()
            return bool(username_row and password_row)
    except Exception:
        return False


@admin_bp.route('/api/setup/status', methods=['GET'])
def setup_status():
    """检查是否需要初始化设置（公开端点）"""
    need_setup = not _is_admin_configured()
    return jsonify({'need_setup': need_setup})


@admin_bp.route('/api/setup', methods=['POST'])
def initial_setup():
    """首次设置管理员账号（仅在未设置时可用）"""
    if _is_admin_configured():
        return jsonify({'success': False, 'error': '管理员已配置，无法重复设置'}), 403

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': '用户名至少需要3个字符'}), 400

    # 密码强度校验
    from ..admin_module import _validate_password_strength
    valid, msg = _validate_password_strength(password)
    if not valid:
        return jsonify({'success': False, 'error': msg}), 400

    try:
        from werkzeug.security import generate_password_hash
        from ..database import get_connection
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('username', username)
            )
            cursor.execute(
                "INSERT OR REPLACE INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('password_hash', password_hash)
            )

        logger.info(f"首次设置管理员账号完成: {username}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"首次设置管理员账号失败: {e}")
        return jsonify({'success': False, 'error': '设置失败'}), 500
