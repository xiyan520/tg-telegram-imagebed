#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - 初始化设置

安全说明：initial_setup() 使用 threading.Lock + 单事务内 check-then-write
消除 TOCTOU 竞态条件，防止并发请求抢先注入管理员凭据。
"""
import threading

from flask import request, jsonify

from . import admin_bp
from ..config import logger

# 应用层互斥锁，防止 waitress 多线程并发进入 initial_setup 事务窗口
_setup_lock = threading.Lock()


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
    """首次设置管理员账号（仅在未设置时可用）

    安全：在 _setup_lock + 单个 SQLite 事务内完成 check-then-write，
    消除 TOCTOU 竞态，保证只有第一个请求能写入管理员凭据。
    """
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': '用户名至少需要3个字符'}), 400

    # 密码强度校验（在锁外完成，避免持锁时做耗时计算）
    from ..admin_module import validate_password_strength
    valid, msg = validate_password_strength(password)
    if not valid:
        return jsonify({'success': False, 'error': msg}), 400

    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    try:
        from ..database import get_connection

        with _setup_lock:
            with get_connection() as conn:
                cursor = conn.cursor()
                # 原子检查：事务内查询是否已配置
                cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
                if cursor.fetchone():
                    return jsonify({'success': False, 'error': '管理员已配置，无法重复设置'}), 403
                # 写入（同一事务，提交前其他连接看不到）
                cursor.execute(
                    "INSERT INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ('username', username)
                )
                cursor.execute(
                    "INSERT INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ('password_hash', password_hash)
                )

        logger.info(f"首次设置管理员账号完成: {username}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"首次设置管理员账号失败: {e}")
        return jsonify({'success': False, 'error': '设置失败'}), 500
