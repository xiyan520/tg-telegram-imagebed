#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TG 认证数据访问层"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from ..config import logger
from .connection import get_connection, db_retry
from .settings import get_system_setting, get_system_setting_int


# ===================== TG 用户管理 =====================

@db_retry()
def upsert_tg_user(tg_user_id: int, username: str = None,
                    first_name: str = None, last_name: str = None) -> bool:
    """创建或更新 TG 用户记录"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tg_users (tg_user_id, username, first_name, last_name, last_login_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tg_user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_login_at = CURRENT_TIMESTAMP
            ''', (tg_user_id, username, first_name, last_name))
            return True
    except Exception as e:
        logger.error(f"upsert_tg_user 失败: {e}")
        return False


@db_retry()
def get_tg_user(tg_user_id: int) -> Optional[Dict]:
    """根据 tg_user_id 获取用户"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tg_users WHERE tg_user_id = ?', (tg_user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_tg_user 失败: {e}")
        return None
@db_retry()
def get_tg_user_by_username(username: str) -> Optional[Dict]:
    """根据 username 获取用户（不区分大小写）"""
    try:
        # 去除 @ 前缀
        username = username.lstrip('@').strip()
        if not username:
            return None
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM tg_users WHERE LOWER(username) = LOWER(?)',
                (username,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_tg_user_by_username 失败: {e}")
        return None


# ===================== 登录验证码/链接 =====================

def _generate_code(code_type: str) -> str:
    """生成验证码或登录链接 code"""
    if code_type in ('verify', 'web_verify'):
        # 6 位数字验证码
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    else:
        # 32 字符随机 token
        return secrets.token_urlsafe(24)


@db_retry()
def create_login_code(code_type: str, tg_user_id: int = None,
                      username_hint: str = None, ip_address: str = None) -> Optional[str]:
    """创建登录验证码或一次性链接

    Args:
        code_type: 'verify' 或 'login_link'
        tg_user_id: TG 用户 ID（login_link 必须提供）
        username_hint: 用户名提示（verify 模式用于关联）
        ip_address: 请求 IP

    Returns:
        生成的 code，失败返回 None
    """
    try:
        expire_minutes = get_system_setting_int('tg_login_code_expire_minutes', 5, minimum=1, maximum=60)
        expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
        code = _generate_code(code_type)

        with get_connection() as conn:
            cursor = conn.cursor()
            # 惰性清理过期记录
            cursor.execute('DELETE FROM tg_login_codes WHERE expires_at < CURRENT_TIMESTAMP')

            cursor.execute('''
                INSERT INTO tg_login_codes (tg_user_id, code, code_type, username_hint, expires_at, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (tg_user_id, code, code_type, username_hint, expires_at.strftime('%Y-%m-%d %H:%M:%S'), ip_address))
            return code
    except Exception as e:
        logger.error(f"create_login_code 失败: {e}")
        return None


@db_retry()
def verify_login_code(code: str, code_type: str = 'verify') -> Optional[Dict]:
    """验证并消费登录码（一次性使用）

    Returns:
        成功返回 {'tg_user_id': int, 'code_type': str}，失败返回 None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, tg_user_id, code_type FROM tg_login_codes
                WHERE code = ? AND code_type = ? AND used_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
            ''', (code, code_type))
            row = cursor.fetchone()
            if not row:
                return None

            # 标记为已使用
            cursor.execute(
                'UPDATE tg_login_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?',
                (row['id'],)
            )
            return {'tg_user_id': row['tg_user_id'], 'code_type': row['code_type']}
    except Exception as e:
        logger.error(f"verify_login_code 失败: {e}")
        return None

# ===================== TG 会话管理 =====================

@db_retry()
def create_tg_session(tg_user_id: int, ip_address: str = None,
                      user_agent: str = None) -> Optional[str]:
    """创建 TG 登录会话

    Returns:
        session_token 字符串，失败返回 None
    """
    try:
        expire_days = get_system_setting_int('tg_session_expire_days', 30, minimum=1, maximum=365)
        expires_at = datetime.utcnow() + timedelta(days=expire_days)
        session_token = secrets.token_urlsafe(48)  # 64 字符

        with get_connection() as conn:
            cursor = conn.cursor()
            # 惰性清理过期会话
            cursor.execute('DELETE FROM tg_sessions WHERE expires_at < CURRENT_TIMESTAMP')

            cursor.execute('''
                INSERT INTO tg_sessions (session_token, tg_user_id, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_token, tg_user_id, expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                  ip_address, user_agent))
            return session_token
    except Exception as e:
        logger.error(f"create_tg_session 失败: {e}")
        return None


@db_retry()
def verify_tg_session(session_token: str) -> Optional[Dict]:
    """验证 TG 会话

    Returns:
        成功返回 {'tg_user_id', 'username', 'first_name', ...}，失败返回 None
    """
    if not session_token:
        return None
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.tg_user_id, s.expires_at, u.username, u.first_name, u.last_name, u.is_blocked
                FROM tg_sessions s
                JOIN tg_users u ON s.tg_user_id = u.tg_user_id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            row = cursor.fetchone()
            if not row:
                return None
            if row['is_blocked']:
                return None
            return dict(row)
    except Exception as e:
        logger.error(f"verify_tg_session 失败: {e}")
        return None


@db_retry()
def delete_tg_session(session_token: str) -> bool:
    """删除 TG 会话（登出）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tg_sessions WHERE session_token = ?', (session_token,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"delete_tg_session 失败: {e}")
        return False

# ===================== Token 绑定管理 =====================

@db_retry()
def get_user_token_count(tg_user_id: int) -> int:
    """获取用户绑定的有效 Token 数量"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM auth_tokens WHERE tg_user_id = ? AND is_active = 1',
                (tg_user_id,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"get_user_token_count 失败: {e}")
        return 0


@db_retry()
def get_user_tokens(tg_user_id: int) -> List[Dict]:
    """获取用户绑定的所有 Token"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT rowid AS id, token, created_at, expires_at, upload_count, upload_limit,
                       is_active, description
                FROM auth_tokens
                WHERE tg_user_id = ?
                ORDER BY created_at DESC
            ''', (tg_user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"get_user_tokens 失败: {e}")
        return []


@db_retry()
def bind_token_to_user(token: str, tg_user_id: int) -> bool:
    """将 Token 绑定到 TG 用户"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE auth_tokens SET tg_user_id = ? WHERE token = ?',
                (tg_user_id, token)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"bind_token_to_user 失败: {e}")
        return False


@db_retry()
def unbind_token_from_user(token: str, tg_user_id: int) -> bool:
    """解除 Token 与 TG 用户的绑定（仅限本人的 Token）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE auth_tokens SET tg_user_id = NULL WHERE token = ? AND tg_user_id = ?',
                (token, tg_user_id)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"unbind_token_from_user 失败: {e}")
        return False


# ===================== Web 验证码登录（新流程） =====================

@db_retry()
def consume_web_verify_code(code: str, tg_user_id: int) -> Optional[str]:
    """Bot 端消费 web_verify 验证码

    1. 查找 code_type='web_verify', used_at IS NULL, 未过期
    2. upsert_tg_user 确保用户已注册
    3. create_tg_session 创建会话
    4. 更新 code 记录：tg_user_id, used_at, session_token

    Returns:
        session_token 或 None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM tg_login_codes
                WHERE code = ? AND code_type = 'web_verify'
                  AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            ''', (code,))
            row = cursor.fetchone()
            if not row:
                return None

            code_id = row['id']

            # 创建会话
            session_token = create_tg_session(tg_user_id=tg_user_id)
            if not session_token:
                return None

            # 标记为已消费，写入 tg_user_id 和 session_token
            cursor.execute('''
                UPDATE tg_login_codes
                SET tg_user_id = ?, used_at = CURRENT_TIMESTAMP, session_token = ?
                WHERE id = ?
            ''', (tg_user_id, session_token, code_id))
            return session_token
    except Exception as e:
        logger.error(f"consume_web_verify_code 失败: {e}")
        return None


@db_retry()
def get_web_verify_status(code: str) -> Optional[Dict]:
    """查询 web_verify 验证码状态

    Returns:
        {'status': 'pending'|'ok'|'expired', 'session_token': str|None}
        不存在返回 None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT used_at, expires_at, session_token FROM tg_login_codes
                WHERE code = ? AND code_type = 'web_verify'
            ''', (code,))
            row = cursor.fetchone()
            if not row:
                return None

            if row['used_at']:
                return {'status': 'ok', 'session_token': row['session_token']}
            if row['expires_at'] <= datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'):
                return {'status': 'expired', 'session_token': None}
            return {'status': 'pending', 'session_token': None}
    except Exception as e:
        logger.error(f"get_web_verify_status 失败: {e}")
        return None


# ===================== 清理 =====================

@db_retry()
def cleanup_expired_codes() -> int:
    """清理过期的登录码"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tg_login_codes WHERE expires_at < CURRENT_TIMESTAMP')
            return cursor.rowcount
    except Exception as e:
        logger.error(f"cleanup_expired_codes 失败: {e}")
        return 0


@db_retry()
def cleanup_expired_sessions() -> int:
    """清理过期的会话"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tg_sessions WHERE expires_at < CURRENT_TIMESTAMP')
            return cursor.rowcount
    except Exception as e:
        logger.error(f"cleanup_expired_sessions 失败: {e}")
        return 0
