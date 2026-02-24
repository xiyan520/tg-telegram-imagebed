#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram图床机器人 - 管理员功能模块（简化版）
提供Web管理后台功能
"""
import os
import sqlite3
import hashlib
import secrets
import logging
import time
import json
import re
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, render_template, make_response, redirect, url_for
from flask.sessions import SecureCookieSessionInterface

from .database.connection import get_connection

# 日志配置
logger = logging.getLogger(__name__)

# ===================== 画集域名 SSO Token 存储 =====================
# 格式: {token_str: {'created_at': float, 'username': str, 'used': bool}}
_gallery_auth_tokens: dict[str, dict] = {}

_GALLERY_TOKEN_EXPIRE_SECONDS = 60  # token 有效期 60 秒


def _cleanup_gallery_tokens():
    """清理过期的画集 SSO token"""
    now = time.time()
    expired = [
        t for t, info in _gallery_auth_tokens.items()
        if now - info['created_at'] > _GALLERY_TOKEN_EXPIRE_SECONDS
    ]
    for t in expired:
        del _gallery_auth_tokens[t]


def generate_gallery_auth_token(username: str) -> str:
    """生成一次性画集 SSO token（60秒有效，一次性使用）"""
    _cleanup_gallery_tokens()
    token = secrets.token_urlsafe(32)
    _gallery_auth_tokens[token] = {
        'created_at': time.time(),
        'username': username,
        'used': False,
    }
    return token


def verify_gallery_auth_token(token: str) -> tuple[bool, str]:
    """
    验证画集 SSO token
    返回: (valid, username)
    验证后立即标记为已使用，防止重放
    """
    _cleanup_gallery_tokens()
    info = _gallery_auth_tokens.get(token)
    if not info:
        return False, ''
    if info['used']:
        return False, ''
    if time.time() - info['created_at'] > _GALLERY_TOKEN_EXPIRE_SECONDS:
        del _gallery_auth_tokens[token]
        return False, ''
    # 标记为已使用
    info['used'] = True
    return True, info['username']


# 从 utils.py 导入 get_domain 和 format_size
try:
    from .utils import get_domain, get_image_domain, format_size
except ImportError:
    # 兼容独立运行场景
    def get_domain(req):
        """简化版 get_domain 函数"""
        return req.host_url.rstrip('/')
    get_image_domain = get_domain

# 从 config.py 导入配置
try:
    from .config import (
        SESSION_LIFETIME,
        REMEMBER_ME_LIFETIME,
        DATABASE_PATH,
        LOGIN_MAX_ATTEMPTS,
        LOGIN_LOCKOUT_DURATIONS,
        LOGIN_ATTEMPT_WINDOW,
        MAX_CONCURRENT_SESSIONS,
    )
except ImportError:
    # 兼容独立运行场景
    SESSION_LIFETIME = 3600
    REMEMBER_ME_LIFETIME = 30 * 24 * 3600
    DEFAULT_DB_PATH = os.path.join(os.getcwd(), "data", "telegram_imagebed.db")
    DATABASE_PATH = DEFAULT_DB_PATH
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATIONS = [300, 900, 1800]
    LOGIN_ATTEMPT_WINDOW = 900
    MAX_CONCURRENT_SESSIONS = 3


# ===================== 登录速率限制器（内存级） =====================
_login_tracker: dict[str, dict] = {}
# 结构: { ip: { 'attempts': int, 'locked_until': float, 'lockout_level': int, 'last_attempt': float } }


def _get_client_ip(req) -> str:
    """获取真实客户端 IP（ProxyFix 已将 X-Forwarded-For 解析到 remote_addr）"""
    return req.remote_addr or '127.0.0.1'


def _cleanup_expired_trackers():
    """清理过期的登录追踪记录"""
    now = time.time()
    expired_ips = [
        ip for ip, info in _login_tracker.items()
        if now - info.get('last_attempt', 0) > LOGIN_ATTEMPT_WINDOW
        and now > info.get('locked_until', 0)
    ]
    for ip in expired_ips:
        del _login_tracker[ip]


def _check_login_allowed(ip: str) -> tuple[bool, int, int]:
    """
    检查 IP 是否允许登录
    返回: (allowed, retry_after_seconds, remaining_attempts)
    """
    _cleanup_expired_trackers()
    info = _login_tracker.get(ip)
    if not info:
        return True, 0, LOGIN_MAX_ATTEMPTS

    now = time.time()

    # 检查是否在锁定期内
    locked_until = info.get('locked_until', 0)
    if now < locked_until:
        retry_after = int(locked_until - now) + 1
        return False, retry_after, 0

    # 检查失败计数窗口是否已过期（自动重置）
    if now - info.get('last_attempt', 0) > LOGIN_ATTEMPT_WINDOW:
        del _login_tracker[ip]
        return True, 0, LOGIN_MAX_ATTEMPTS

    remaining = max(0, LOGIN_MAX_ATTEMPTS - info.get('attempts', 0))
    return True, 0, remaining


def _record_login_failure(ip: str):
    """记录登录失败，累加计数，达到阈值时触发渐进式锁定"""
    now = time.time()
    info = _login_tracker.get(ip)

    if not info:
        _login_tracker[ip] = {
            'attempts': 1,
            'locked_until': 0,
            'lockout_level': 0,
            'last_attempt': now,
        }
        return

    info['attempts'] = info.get('attempts', 0) + 1
    info['last_attempt'] = now

    # 达到阈值 → 触发锁定
    if info['attempts'] >= LOGIN_MAX_ATTEMPTS:
        level = info.get('lockout_level', 0)
        duration = LOGIN_LOCKOUT_DURATIONS[min(level, len(LOGIN_LOCKOUT_DURATIONS) - 1)]
        info['locked_until'] = now + duration
        info['lockout_level'] = min(level + 1, len(LOGIN_LOCKOUT_DURATIONS) - 1)
        info['attempts'] = 0  # 重置计数，解锁后重新开始计数


def _record_login_success(ip: str):
    """登录成功后清除该 IP 的失败记录"""
    _login_tracker.pop(ip, None)


# ===================== 密码强度校验 =====================
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    校验密码强度
    返回: (valid, message)
    """
    if not password or len(password) < 8:
        return False, '密码长度至少需要8个字符'
    if not re.search(r'[a-zA-Z]', password):
        return False, '密码必须包含字母'
    if not re.search(r'[0-9]', password):
        return False, '密码必须包含数字'
    return True, ''


# ===================== 安全审计日志 =====================
def _log_security_event(event_type: str, ip: str, username: str = '', detail: str = ''):
    """将安全事件写入 admin_config 表（key=security_log，保留最近 200 条）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 读取现有日志
            cursor.execute("SELECT value FROM admin_config WHERE key = 'security_log'")
            row = cursor.fetchone()
            logs = json.loads(row[0]) if row else []

            # 追加新事件
            logs.append({
                'type': event_type,
                'ip': ip,
                'username': username,
                'detail': detail,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })

            # 保留最近 200 条
            logs = logs[-200:]

            cursor.execute(
                "INSERT OR REPLACE INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('security_log', json.dumps(logs, ensure_ascii=False))
            )
    except Exception as e:
        logger.debug(f"写入安全审计日志失败: {e}")


# ===================== Session 并发控制 =====================

def _get_session_lifetime(remember_me: bool = False) -> int:
    """根据是否"记住我"返回对应的 session 有效期（秒）"""
    return REMEMBER_ME_LIFETIME if remember_me else SESSION_LIFETIME


def _get_active_sessions() -> list[dict]:
    """从数据库读取活跃 session 列表"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM admin_config WHERE key = 'active_sessions'")
            row = cursor.fetchone()
            return json.loads(row[0]) if row else []
    except Exception:
        return []


def _save_active_sessions(sessions: list[dict]):
    """保存活跃 session 列表到数据库"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO admin_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('active_sessions', json.dumps(sessions, ensure_ascii=False))
            )
    except Exception as e:
        logger.debug(f"保存活跃 session 失败: {e}")


def _register_session(token: str, ip: str, remember_me: bool = False):
    """注册新 session，超出并发限制时踢掉最早的"""
    now = time.time()
    sessions = _get_active_sessions()

    # 清理过期 session（根据各自的 remember_me 标记使用对应的 lifetime）
    sessions = [
        s for s in sessions
        if now - s.get('login_time', 0) < _get_session_lifetime(s.get('remember_me', False))
    ]

    # 踢掉最早的 session（如果超出限制）
    kicked = []
    while len(sessions) >= MAX_CONCURRENT_SESSIONS:
        oldest = sessions.pop(0)
        kicked.append(oldest)

    # 记录被踢出的 session
    for s in kicked:
        _log_security_event('session_kicked', s.get('ip', ''), detail=f"token={s.get('token', '')[:8]}...")

    # 添加新 session
    sessions.append({
        'token': token,
        'ip': ip,
        'login_time': now,
        'last_active': now,
        'remember_me': remember_me,
    })

    _save_active_sessions(sessions)


def _update_session_activity(token: str):
    """更新 session 的最后活跃时间，若不存在则自动补注册"""
    now = time.time()
    sessions = _get_active_sessions()
    # 清理过期 session（根据各自的 remember_me 标记使用对应的 lifetime）
    sessions = [
        s for s in sessions
        if now - s.get('login_time', 0) < _get_session_lifetime(s.get('remember_me', False))
    ]

    found = False
    for s in sessions:
        if s.get('token') == token:
            s['last_active'] = now
            found = True
            break

    if not found:
        # 当前 session 不在列表中（功能上线前已登录），自动补注册
        ip = '0.0.0.0'
        try:
            ip = _get_client_ip(request)
        except Exception:
            pass
        sessions.append({
            'token': token,
            'ip': ip,
            'login_time': now,
            'last_active': now,
        })

    _save_active_sessions(sessions)


def _remove_session(token: str):
    """移除指定 session"""
    sessions = _get_active_sessions()
    sessions = [s for s in sessions if s.get('token') != token]
    _save_active_sessions(sessions)


def _get_config_status_from_db() -> dict:
    """从数据库读取配置状态（使用 system_settings 表）"""
    cdn_enabled = False
    cdn_monitor_enabled = False
    cdn_domain = ''

    try:
        from .database import get_system_setting
        cdn_enabled = str(get_system_setting('cdn_enabled') or '0') == '1'
        cdn_monitor_enabled = str(get_system_setting('cdn_monitor_enabled') or '0') == '1'
        cdn_domain = str(get_system_setting('cloudflare_cdn_domain') or '').strip()
        group_upload_admin_only = str(get_system_setting('group_upload_admin_only') or '0') == '1'
    except Exception as e:
        logger.debug(f"从数据库读取系统设置失败: {e}")
        group_upload_admin_only = False

    # CDN 监控只有在 CDN 启用时才有意义
    cdn_monitor_display = '已启用' if (cdn_enabled and cdn_monitor_enabled) else '已关闭'

    return {
        'cdnStatus': '已启用' if cdn_enabled else '未启用',
        'cdnDomain': cdn_domain if cdn_domain else '未配置',
        'uptime': '运行中',
        'groupUpload': '仅管理员' if group_upload_admin_only else '已开放',
        'cdnMonitor': cdn_monitor_display
    }

def init_admin_config():
    """初始化管理员配置表（在主数据库中）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

def get_admin_config():
    """获取管理员配置"""
    init_admin_config()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
        username = cursor.fetchone()
        username = username[0] if username else ''

        cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
        password_hash = cursor.fetchone()

        return {
            'username': username,
            'password_status': '已设置' if password_hash else '使用默认密码',
            'session_lifetime': SESSION_LIFETIME
        }

def verify_admin_password(username, password):
    """验证管理员密码"""
    from werkzeug.security import check_password_hash

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
        stored_username = cursor.fetchone()
        if not stored_username or stored_username[0] != username:
            return False

        cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
        stored_hash = cursor.fetchone()

        if not stored_hash:
            return False

        # 使用 werkzeug.security 验证密码
        # 兼容旧的 sha256 哈希格式
        hash_value = stored_hash[0]
        if hash_value.startswith('pbkdf2:'):
            return check_password_hash(hash_value, password)
        else:
            # 兼容旧格式（sha256）
            import hashlib
            if hash_value == hashlib.sha256(password.encode()).hexdigest():
                # 旧格式验证成功，自动升级为 pbkdf2
                try:
                    update_admin_credentials(new_password=password)
                    logger.info(f"已自动将管理员 {username} 的密码哈希从 SHA256 升级为 pbkdf2")
                except Exception as e:
                    logger.warning(f"密码哈希自动升级失败（不影响登录）: {e}")
                return True
            return False

def update_admin_credentials(new_username=None, new_password=None):
    """更新管理员凭据"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            if new_username:
                cursor.execute('''
                    INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                    VALUES ('username', ?, CURRENT_TIMESTAMP)
                ''', (new_username,))

            if new_password:
                # 使用 werkzeug.security 进行安全的密码哈希
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
                cursor.execute('''
                    INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                    VALUES ('password_hash', ?, CURRENT_TIMESTAMP)
                ''', (password_hash,))

        return True
    except Exception as e:
        logger.error(f"更新管理员凭据失败: {e}")
        return False

class _AutoSecureSessionInterface(SecureCookieSessionInterface):
    """自动根据请求协议设置 cookie Secure 标记的 Session 接口
    HTTPS 请求 → Secure=True（cookie 仅通过 HTTPS 发送）
    HTTP 请求 → Secure=False（cookie 可通过 HTTP 发送）
    同时兼容反向代理（X-Forwarded-Proto）"""

    def get_cookie_secure(self, app):
        try:
            return (
                request.is_secure
                or request.headers.get('X-Forwarded-Proto', '').lower() == 'https'
            )
        except RuntimeError:
            # 请求上下文之外
            return False


def configure_admin_session(app):
    """配置管理员会话"""
    app.session_interface = _AutoSecureSessionInterface()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # 由 _AutoSecureSessionInterface 动态覆盖
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_LIFETIME)

    @app.before_request
    def _dynamic_session_lifetime():
        """根据 session 中的 _remember_me 标记动态调整 session 有效期，并实现活跃续期"""
        if session.get('admin_logged_in'):
            remember_me = session.get('_remember_me', False)
            lifetime = _get_session_lifetime(remember_me)
            app.permanent_session_lifetime = timedelta(seconds=lifetime)
            # 标记 session 已修改，使 Flask 重新设置 cookie 过期时间，实现活跃续期
            session.modified = True

# 添加登录验证装饰器
def login_required(f):
    """需要登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('admin_login'))

        # 检查当前 token 是否仍在活跃 session 列表中（被踢出则拒绝）
        token = session.get('admin_token')
        if token:
            active = _get_active_sessions()
            if active and not any(s.get('token') == token for s in active):
                # token 已被踢出，清除本地 session
                session.pop('admin_logged_in', None)
                session.pop('admin_username', None)
                session.pop('admin_token', None)
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Session revoked', 'kicked': True}), 401
                return redirect(url_for('admin_login'))
            _update_session_activity(token)

        return f(*args, **kwargs)
    return decorated_function

def init_database_admin_update(DATABASE_PATH):
    """为管理功能更新数据库索引"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 检查并添加新列
            cursor.execute("PRAGMA table_info(file_storage)")
            columns = [column[1] for column in cursor.fetchall()]

            # 添加缺失的列
            if 'is_group_upload' not in columns:
                logger.info("管理模块：添加 is_group_upload 列")
                cursor.execute('ALTER TABLE file_storage ADD COLUMN is_group_upload BOOLEAN DEFAULT 0')

            if 'group_message_id' not in columns:
                logger.info("管理模块：添加 group_message_id 列")
                cursor.execute('ALTER TABLE file_storage ADD COLUMN group_message_id INTEGER')

            if 'group_chat_id' not in columns:
                logger.info("管理模块：添加 group_chat_id 列")
                cursor.execute('ALTER TABLE file_storage ADD COLUMN group_chat_id INTEGER')

            # 添加文件名索引以加速搜索
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_original_filename
                ON file_storage(original_filename)
            ''')

            # 添加额外的索引以优化管理查询
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at ON file_storage(created_at DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_size ON file_storage(file_size)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_group_upload ON file_storage(is_group_upload)
            ''')

        logger.info("管理功能数据库索引创建完成")
    except Exception as e:
        logger.error(f"创建管理索引失败: {e}")

def get_static_file_version(filename):
    """获取静态文件版本号"""
    # 如果启用了强制刷新，总是返回当前时间戳
    force_refresh = os.getenv("FORCE_REFRESH", "false").lower() == "true"
    if force_refresh:
        return str(int(time.time()))
    
    # 否则返回配置的静态版本
    return os.getenv("STATIC_VERSION", str(int(time.time())))

def register_admin_routes(app, DATABASE_PATH, get_all_files_count, get_total_size, add_cache_headers):
    """注册管理员路由"""

    # 注意：/admin 和 /admin/login 页面路由已移除
    # 这些路由由前端 SPA (frontend/.output/public/admin/) 处理
    # Flask 通过 serve_frontend() 提供静态文件

    # 添加管理相关API路由
    @app.route('/api/admin/check')
    def admin_check():
        """检查管理员登录状态"""
        if 'admin_logged_in' in session and session['admin_logged_in']:
            return jsonify({
                'authenticated': True,
                'username': session.get('admin_username', 'admin')
            })
        return jsonify({'authenticated': False})

    @app.route('/api/admin/login', methods=['POST'])
    def admin_login_api():
        """管理员登录"""
        ip = _get_client_ip(request)

        # 速率限制检查
        allowed, retry_after, remaining = _check_login_allowed(ip)
        if not allowed:
            logger.warning(f"登录被锁定: IP={ip}, 剩余等待={retry_after}秒")
            _log_security_event('login_locked', ip, detail=f"retry_after={retry_after}s")
            response = jsonify({
                'success': False,
                'message': '登录尝试过多，请稍后再试',
                'locked': True,
                'retry_after': retry_after
            })
            return response, 429

        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = bool(data.get('remember_me', False))

        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

        # 验证用户名和密码
        if verify_admin_password(username, password):
            _record_login_success(ip)

            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['_remember_me'] = remember_me
            session.permanent = True

            # 根据"记住我"设置对应的 session 有效期
            lifetime = _get_session_lifetime(remember_me)
            app.permanent_session_lifetime = timedelta(seconds=lifetime)

            # 生成一个简单的 token（用于前端存储）
            token = secrets.token_urlsafe(32)
            session['admin_token'] = token

            # 注册 session（并发控制），传递 remember_me 标记
            _register_session(token, ip, remember_me=remember_me)

            _log_security_event('login_success', ip, username)
            logger.info(f"管理员登录成功: {username}")
            return jsonify({
                'success': True,
                'data': {
                    'token': token,
                    'username': username
                }
            })

        # 登录失败
        _record_login_failure(ip)
        _log_security_event('login_failed', ip, username)
        _, _, remaining = _check_login_allowed(ip)
        logger.warning(f"管理员登录失败: {username}, IP={ip}, 剩余尝试={remaining}")
        return jsonify({
            'success': False,
            'message': '用户名或密码错误',
            'remaining_attempts': remaining
        }), 401

    @app.route('/api/admin/logout', methods=['POST'])
    def admin_logout():
        """管理员退出登录"""
        username = session.get('admin_username', 'unknown')
        token = session.get('admin_token')
        ip = _get_client_ip(request)

        # 移除 session 记录
        if token:
            _remove_session(token)

        session.pop('admin_logged_in', None)
        session.pop('admin_username', None)
        session.pop('admin_token', None)

        _log_security_event('logout', ip, username)
        logger.info(f"管理员退出登录: {username}")
        return jsonify({'success': True})
    
    @app.route('/api/admin/update_credentials', methods=['POST'])
    @login_required
    def admin_update_credentials():
        """更新管理员凭据"""
        data = request.get_json()
        new_username = data.get('username', '').strip()
        new_password = data.get('password', '').strip()

        if not new_username and not new_password:
            return jsonify({'success': False, 'error': '请提供新的用户名或密码'}), 400

        if new_username and len(new_username) < 3:
            return jsonify({'success': False, 'error': '用户名至少需要3个字符'}), 400

        if new_password:
            valid, msg = validate_password_strength(new_password)
            if not valid:
                return jsonify({'success': False, 'error': msg}), 400

        if update_admin_credentials(new_username, new_password):
            # 如果更改了用户名，更新会话
            if new_username:
                session['admin_username'] = new_username

            ip = _get_client_ip(request)
            _log_security_event('password_changed', ip, session.get('admin_username', ''),
                                detail='username_changed' if new_username else 'password_changed')

            return jsonify({
                'success': True,
                'message': '凭据更新成功',
                'updated_username': new_username is not None,
                'updated_password': new_password is not None
            })

        return jsonify({'success': False, 'error': '更新失败'}), 500

    @app.route('/api/admin/stats', methods=['GET'])
    @login_required
    def admin_stats():
        """获取管理统计信息"""
        try:
            total_files = get_all_files_count()
            total_size = get_total_size()

            # 获取今日上传数
            with get_connection() as conn:
                cursor = conn.cursor()

                try:
                    # 修复日期查询 - 使用时间戳范围查询
                    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                    today_start_ts = int(today_start.timestamp())
                    today_end_ts = int(today_end.timestamp())

                    cursor.execute('''
                        SELECT COUNT(*) FROM file_storage
                        WHERE upload_time >= ? AND upload_time <= ?
                    ''', (today_start_ts, today_end_ts))
                    today_uploads = cursor.fetchone()[0]

                    # 获取 CDN 缓存数量
                    cursor.execute('SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 1')
                    cdn_cached = cursor.fetchone()[0]
                except Exception as e:
                    logger.error(f"查询统计数据失败: {e}")
                    today_uploads = 0
                    cdn_cached = 0

            response_data = {
                'success': True,
                'data': {
                    'stats': {
                        'totalImages': total_files,
                        'totalSize': format_size(total_size),
                        'todayUploads': today_uploads,
                        'cdnCached': cdn_cached
                    },
                    'config': _get_config_status_from_db()
                }
            }

            logger.debug(f"返回统计数据: {response_data}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': '获取统计信息失败',
                'message': '服务器内部错误'
            }), 500

    @app.route('/api/admin/images', methods=['GET'])
    @login_required
    def admin_images():
        """获取图片列表（支持分页、搜索和筛选）"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            search = request.args.get('search', '').strip()
            filter_type = request.args.get('filter', 'all').strip().lower()

            # 边界保护：确保 page >= 1，1 <= limit <= 200
            page = max(1, page)
            limit = max(1, min(200, limit))

            # 验证 filter 参数
            if filter_type not in ('all', 'cached', 'uncached', 'group'):
                filter_type = 'all'

            logger.info(f"获取图片列表请求: page={page}, limit={limit}, search={search}, filter={filter_type}")

            with get_connection() as conn:
                cursor = conn.cursor()

                # 检查列是否存在
                cursor.execute("PRAGMA table_info(file_storage)")
                columns = [column[1] for column in cursor.fetchall()]

                # 构建查询
                offset = (page - 1) * limit

                # 构建SELECT语句，只选择存在的列
                select_columns = [
                    'fs.encrypted_id', 'fs.file_id', 'fs.original_filename',
                    'fs.file_size', 'fs.source', 'fs.created_at', 'fs.username',
                    'fs.access_count', 'fs.last_accessed', 'fs.upload_time',
                    'fs.cdn_cached', 'fs.cdn_cache_time', 'fs.mime_type'
                ]

                # 可选列
                if 'is_group_upload' in columns:
                    select_columns.append('fs.is_group_upload')
                if 'cdn_hit_count' in columns:
                    select_columns.append('fs.cdn_hit_count')
                if 'direct_hit_count' in columns:
                    select_columns.append('fs.direct_hit_count')

                query = f'''
                    SELECT {', '.join(select_columns)}
                    FROM file_storage fs
                '''

                # 构建 WHERE 条件
                where_clauses = []
                where_params = []

                if search:
                    # 搜索文件名和用户名
                    where_clauses.append('(fs.original_filename LIKE ? OR fs.username LIKE ?)')
                    search_pattern = f'%{search}%'
                    where_params.extend([search_pattern, search_pattern])

                # 根据 filter_type 添加筛选条件
                if filter_type == 'cached':
                    if 'cdn_cached' in columns:
                        where_clauses.append('fs.cdn_cached = 1')
                    else:
                        # 如果列不存在，返回空结果
                        where_clauses.append('1 = 0')
                elif filter_type == 'uncached':
                    if 'cdn_cached' in columns:
                        where_clauses.append('(fs.cdn_cached = 0 OR fs.cdn_cached IS NULL)')
                    # 如果列不存在，不添加条件（相当于返回全部）
                elif filter_type == 'group':
                    if 'is_group_upload' in columns:
                        where_clauses.append('fs.is_group_upload = 1')
                    else:
                        # 如果列不存在，返回空结果
                        where_clauses.append('1 = 0')

                # 拼接 WHERE 子句
                if where_clauses:
                    query += ' WHERE ' + ' AND '.join(where_clauses)

                # 获取总数（与查询条件一致）
                count_query = 'SELECT COUNT(*) FROM file_storage fs'
                if where_clauses:
                    count_query += ' WHERE ' + ' AND '.join(where_clauses)
                cursor.execute(count_query, where_params)

                total_count = cursor.fetchone()[0]

                # 获取当前页数据
                query += ' ORDER BY fs.created_at DESC LIMIT ? OFFSET ?'
                params = list(where_params)
                params.extend([limit, offset])

                cursor.execute(query, params)
                images = []

                for row in cursor.fetchall():
                    image_data = dict(row)

                    # 如果没有 is_group_upload 列，默认为 0
                    if 'is_group_upload' not in image_data:
                        image_data['is_group_upload'] = 0
                    # 如果没有访问统计列，默认为 0
                    if 'cdn_hit_count' not in image_data:
                        image_data['cdn_hit_count'] = 0
                    if 'direct_hit_count' not in image_data:
                        image_data['direct_hit_count'] = 0

                    # 处理时间格式
                    if image_data.get('upload_time'):
                        try:
                            timestamp = int(image_data['upload_time'])
                            dt = datetime.fromtimestamp(timestamp)
                            image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            logger.debug(f"处理upload_time失败: {e}")

                    if 'created_at' in image_data and image_data['created_at'] and not isinstance(image_data['created_at'], str):
                        created_at = image_data['created_at']
                        try:
                            if isinstance(created_at, (int, float)):
                                dt = datetime.fromtimestamp(created_at)
                                image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                created_at_str = str(created_at)
                                if 'T' in created_at_str:
                                    dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                    image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                elif ' ' in created_at_str:
                                    image_data['created_at'] = created_at_str
                                else:
                                    dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                                    image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            logger.debug(f"时间格式转换失败 ({created_at}): {e}")
                            image_data['created_at'] = str(created_at) if created_at else '未知时间'

                    # 处理最后访问时间
                    if image_data.get('last_accessed'):
                        try:
                            last_accessed = image_data['last_accessed']
                            if isinstance(last_accessed, str) and 'T' in last_accessed:
                                dt = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                                image_data['last_accessed'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(last_accessed, (int, float)):
                                dt = datetime.fromtimestamp(last_accessed)
                                image_data['last_accessed'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                image_data['last_accessed'] = str(last_accessed)
                        except Exception as e:
                            logger.debug(f"处理last_accessed失败: {e}")
                            image_data['last_accessed'] = None

                    # 处理CDN缓存时间
                    if image_data.get('cdn_cache_time'):
                        try:
                            cdn_cache_time = image_data['cdn_cache_time']
                            if isinstance(cdn_cache_time, str) and 'T' in cdn_cache_time:
                                dt = datetime.fromisoformat(cdn_cache_time.replace('Z', '+00:00'))
                                image_data['cdn_cache_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(cdn_cache_time, (int, float)):
                                dt = datetime.fromtimestamp(cdn_cache_time)
                                image_data['cdn_cache_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                image_data['cdn_cache_time'] = str(cdn_cache_time)
                        except Exception as e:
                            logger.debug(f"处理cdn_cache_time失败: {e}")
                            image_data['cdn_cache_time'] = None

                    # 确保created_at是字符串格式
                    if 'created_at' not in image_data or not image_data['created_at']:
                        image_data['created_at'] = '未知时间'
                    elif not isinstance(image_data['created_at'], str):
                        image_data['created_at'] = str(image_data['created_at'])

                    images.append(image_data)

            # 计算总页数
            total_pages = (total_count + limit - 1) // limit

            # 构建图片 URL（使用 get_image_domain 处理图片域名场景）
            base_url = get_image_domain(request).rstrip('/')

            # 从 system_settings 读取 CDN 域名配置（与 settings.py 保持一致）
            cdn_domain = ''
            cdn_enabled = False
            try:
                from .database import get_system_setting
                cdn_enabled = str(get_system_setting('cdn_enabled') or '0') == '1'
                cdn_domain = str(get_system_setting('cloudflare_cdn_domain') or '').strip()
            except Exception as e:
                logger.debug(f"读取 CDN 域名配置失败: {e}")

            for img in images:
                img['url'] = f"{base_url}/image/{img['encrypted_id']}"
                img['cdn_url'] = f"https://{cdn_domain}/image/{img['encrypted_id']}" if (cdn_enabled and cdn_domain) else None
                img['id'] = img['encrypted_id']
                img['filename'] = img.get('original_filename', '未知文件')
                img['size'] = img.get('file_size', 0)
                img['uploadTime'] = img.get('created_at', '未知时间')
                img['cached'] = bool(img.get('cdn_cached', 0))

            response_data = {
                'success': True,
                'data': {
                    'images': images,
                    'totalPages': total_pages,
                    'total': total_count,
                    'page': page,
                    'limit': limit
                }
            }

            logger.info(f"成功返回图片列表: {len(images)} 张图片, 总页数: {total_pages}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"获取图片列表失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': '获取图片列表失败',
                'message': '服务器内部错误'
            }), 500

    @app.route('/api/admin/delete', methods=['POST'])
    @login_required
    def admin_delete_images():
        """删除图片，支持同步删除存储后端文件和TG群组消息"""
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        # 是否删除存储后端文件，默认为 True（向后兼容）
        delete_storage = data.get('delete_storage', True)

        if not isinstance(ids, list) or not ids:
            return jsonify({'success': False, 'message': '没有选择要删除的图片'}), 400

        ids = [str(x).strip() for x in ids if x is not None and str(x).strip()]
        ids = list(dict.fromkeys(ids))
        if not ids:
            return jsonify({'success': False, 'message': '没有选择要删除的图片'}), 400

        deleted_count = 0
        deleted_size = 0
        tg_deleted_count = 0
        storage_deleted_count = 0

        def _chunked(seq, size=900):
            for i in range(0, len(seq), size):
                yield seq[i:i + size]

        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                files_to_delete = []
                for chunk in _chunked(ids):
                    placeholders = ','.join('?' * len(chunk))
                    try:
                        cursor.execute(f'''
                            SELECT encrypted_id, file_size, group_chat_id, group_message_id,
                                   storage_backend, storage_meta, storage_key
                            FROM file_storage
                            WHERE encrypted_id IN ({placeholders})
                        ''', chunk)
                    except sqlite3.OperationalError as e:
                        if 'no such column' in str(e).lower():
                            cursor.execute(f'''
                                SELECT encrypted_id, file_size, NULL, NULL, NULL, NULL, NULL
                                FROM file_storage
                                WHERE encrypted_id IN ({placeholders})
                            ''', chunk)
                        else:
                            raise
                    files_to_delete.extend(cursor.fetchall())

                for row in files_to_delete:
                    if row[1]:
                        deleted_size += row[1]

                # 检查是否启用TG同步删除
                tg_sync_delete_enabled = True
                try:
                    from .database import get_system_setting
                    tg_sync_delete_enabled = str(get_system_setting('tg_sync_delete_enabled') or '1') == '1'
                except Exception:
                    pass

                # 当 delete_storage=True 且 tg_sync_delete_enabled=True 时，删除存储后端文件和TG消息
                if delete_storage and tg_sync_delete_enabled:
                    # 删除存储后端文件（静默忽略失败）
                    try:
                        from .storage.router import get_storage_router
                        router = get_storage_router()
                        for row in files_to_delete:
                            encrypted_id = row[0]
                            storage_backend_name = row[4] if len(row) > 4 else None
                            storage_key = row[6] if len(row) > 6 else None
                            if storage_key and storage_backend_name:
                                try:
                                    backend = router.get_backend(storage_backend_name.strip())
                                    backend.delete(storage_key=storage_key)
                                    storage_deleted_count += 1
                                except Exception as e:
                                    logger.debug(f"删除存储文件失败: {encrypted_id}, {e}")
                    except Exception as e:
                        logger.debug(f"存储后端删除跳过: {e}")

                # 同步删除TG群组消息（静默忽略失败）
                if delete_storage and tg_sync_delete_enabled:
                    try:
                        from .bot_control import get_effective_bot_token
                        bot_token, _ = get_effective_bot_token()
                        if bot_token:
                            # 获取存储路由器（用于 fallback 获取 chat_id）
                            try:
                                from .storage.router import get_storage_router
                                _router = get_storage_router()
                            except Exception:
                                _router = None

                            seen = set()
                            for row in files_to_delete:
                                chat_id, message_id = row[2], row[3]
                                storage_backend_name = row[4] if len(row) > 4 else None
                                storage_meta_raw = row[5] if len(row) > 5 else None

                                # 兼容历史数据：从 storage_meta 中提取 message_id，从后端配置获取 chat_id
                                if message_id is None or chat_id is None:
                                    try:
                                        import json as _json
                                        meta = _json.loads(storage_meta_raw) if isinstance(storage_meta_raw, str) and storage_meta_raw else {}
                                        if message_id is None:
                                            message_id = meta.get('message_id')
                                        if chat_id is None and storage_backend_name and _router:
                                            try:
                                                be = _router.get_backend(storage_backend_name.strip())
                                                if hasattr(be, '_chat_id'):
                                                    chat_id = be._chat_id
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass

                                if chat_id is None or message_id is None:
                                    continue
                                key = (chat_id, message_id)
                                if key in seen:
                                    continue
                                seen.add(key)
                                try:
                                    url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
                                    resp = requests.post(url, data={
                                        'chat_id': chat_id,
                                        'message_id': message_id
                                    }, timeout=5)
                                    if resp.ok:
                                        try:
                                            payload = resp.json()
                                            if payload.get('ok') is True:
                                                tg_deleted_count += 1
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.debug(f"TG消息删除跳过: {e}")

                # 删除数据库记录（分块处理）
                for chunk in _chunked(ids):
                    placeholders = ','.join('?' * len(chunk))
                    cursor.execute(f'''
                        DELETE FROM file_storage
                        WHERE encrypted_id IN ({placeholders})
                    ''', chunk)
                    deleted_count += cursor.rowcount

            logger.info(f"管理员删除了 {deleted_count} 张图片，TG消息同步删除 {tg_deleted_count} 条，存储文件删除 {storage_deleted_count} 个")

            return jsonify({
                'success': True,
                'data': {
                    'deleted': deleted_count,
                    'tg_deleted': tg_deleted_count,
                    'storage_deleted': storage_deleted_count,
                    'message': f'成功删除 {deleted_count} 张图片'
                }
            })

        except Exception as e:
            logger.error(f"删除图片失败: {e}")
            return jsonify({'success': False, 'message': '删除失败'}), 500
    
    @app.route('/api/admin/security-log', methods=['GET'])
    @login_required
    def admin_security_log():
        """获取安全审计日志"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM admin_config WHERE key = 'security_log'")
                row = cursor.fetchone()

            logs = json.loads(row[0]) if row else []
            # 返回倒序（最新在前）
            logs.reverse()
            return jsonify({'success': True, 'data': logs})
        except Exception as e:
            logger.error(f"获取安全日志失败: {e}")
            return jsonify({'success': False, 'error': '获取安全日志失败'}), 500

    @app.route('/api/admin/active-sessions', methods=['GET'])
    @login_required
    def admin_active_sessions():
        """获取当前活跃 Session 列表"""
        try:
            now = time.time()
            sessions = _get_active_sessions()
            # 清理过期 session（根据各自的 remember_me 标记使用对应的 lifetime）
            sessions = [
                s for s in sessions
                if now - s.get('login_time', 0) < _get_session_lifetime(s.get('remember_me', False))
            ]
            current_token = session.get('admin_token', '')

            result = []
            for s in sessions:
                login_ts = s.get('login_time', 0)
                last_ts = s.get('last_active', 0)
                result.append({
                    'token_prefix': s.get('token', '')[:8] + '...',
                    'ip': s.get('ip', ''),
                    'login_time': datetime.fromtimestamp(login_ts).strftime('%Y-%m-%d %H:%M:%S') if login_ts else '',
                    'last_active': datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M:%S') if last_ts else '',
                    'is_current': s.get('token', '') == current_token,
                })
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            logger.error(f"获取活跃 Session 失败: {e}")
            return jsonify({'success': False, 'error': '获取失败'}), 500

    @app.route('/api/admin/kick-session', methods=['POST'])
    @login_required
    def admin_kick_session():
        """踢出指定 Session"""
        data = request.get_json(silent=True) or {}
        token_prefix = data.get('token_prefix', '')
        if not token_prefix:
            return jsonify({'success': False, 'error': '缺少参数'}), 400

        try:
            sessions = _get_active_sessions()
            target = token_prefix.rstrip('.')
            new_sessions = [s for s in sessions if not s.get('token', '').startswith(target)]
            kicked = len(sessions) - len(new_sessions)
            _save_active_sessions(new_sessions)

            if kicked > 0:
                ip = _get_client_ip(request)
                _log_security_event('session_kicked', ip, session.get('admin_username', ''),
                                    detail=f"手动踢出 token={target}...")
            return jsonify({'success': True, 'kicked': kicked})
        except Exception as e:
            logger.error(f"踢出 Session 失败: {e}")
            return jsonify({'success': False, 'error': '操作失败'}), 500

    @app.route('/api/admin/gallery-auth-token', methods=['POST'])
    @login_required
    def admin_gallery_auth_token():
        """生成画集域名 SSO 一次性 token（60秒有效）"""
        try:
            username = session.get('admin_username', 'admin')
            token = generate_gallery_auth_token(username)
            return jsonify({'success': True, 'data': {'token': token}})
        except Exception as e:
            logger.error(f"生成画集 SSO token 失败: {e}")
            return jsonify({'success': False, 'error': '生成 token 失败'}), 500

    @app.route('/api/admin/gallery-sso-callback', methods=['GET'])
    def admin_gallery_sso_callback():
        """主站 SSO 回调：检查 session，生成 token 并重定向回画集站点"""
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        from .database.domains import get_active_gallery_domains, get_default_domain

        return_url = request.args.get('return_url', '')

        # 安全校验 return_url，防止开放重定向
        if not return_url:
            return jsonify({'success': False, 'error': '缺少 return_url 参数'}), 400

        if return_url.startswith('/'):
            # 相对路径，安全
            pass
        elif return_url.startswith('http://') or return_url.startswith('https://'):
            # 绝对 URL，校验域名
            parsed = urlparse(return_url)
            target_host = parsed.hostname
            if not target_host:
                return jsonify({'success': False, 'error': 'return_url 无效'}), 400

            # 获取合法域名列表
            allowed_domains = set()
            gallery_domains = get_active_gallery_domains()
            for d in gallery_domains:
                allowed_domains.add(d['domain'].lower())

            # 主站域名也允许
            default_domain = get_default_domain()
            if default_domain:
                allowed_domains.add(default_domain['domain'].lower())

            # 已保存的主站 URL 的域名也允许
            try:
                from .database import get_system_setting
                saved_main_url = get_system_setting('gallery_sso_main_url')
                if saved_main_url:
                    from urllib.parse import urlparse as _urlparse
                    _parsed_main = _urlparse(saved_main_url)
                    if _parsed_main.hostname:
                        allowed_domains.add(_parsed_main.hostname.lower())
            except Exception:
                pass

            # 当前请求的 Host 也允许（回调在主站执行，主站自身是可信的）
            try:
                req_host = (request.headers.get('X-Forwarded-Host') or request.host or '').split(':')[0].lower()
                if req_host:
                    allowed_domains.add(req_host)
            except Exception:
                pass

            # 内网 IP 地址直接放行（不存在开放重定向风险）
            import ipaddress
            _is_private = False
            try:
                _is_private = ipaddress.ip_address(target_host).is_private
            except ValueError:
                pass

            if not _is_private and target_host.lower() not in allowed_domains:
                logger.warning(f"SSO 回调 return_url 域名不合法: {target_host}")
                return jsonify({'success': False, 'error': 'return_url 域名不合法'}), 400
        else:
            return jsonify({'success': False, 'error': 'return_url 格式无效'}), 400

        # 在 return_url 中追加参数的辅助函数
        def _append_query_param(url: str, key: str, value: str) -> str:
            """在 URL 中追加查询参数，正确处理已有 query 参数的情况"""
            if url.startswith('/'):
                # 相对路径，简单拼接
                separator = '&' if '?' in url else '?'
                return f"{url}{separator}{key}={value}"
            parsed = urlparse(url)
            qs = parse_qs(parsed.query, keep_blank_values=True)
            qs[key] = [value]
            # 重新构建 query string
            new_query = urlencode(qs, doseq=True)
            return urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

        if session.get('admin_logged_in'):
            # 已登录，生成 token 并回跳
            # 同时更新主站 URL 记录（确保 SSO 重定向始终指向正确的主站）
            try:
                from .utils import get_domain
                from .database import update_system_setting
                main_url = get_domain(request)
                update_system_setting('gallery_sso_main_url', main_url)
            except Exception:
                pass
            username = session.get('admin_username', 'admin')
            token = generate_gallery_auth_token(username)
            final_url = _append_query_param(return_url, 'auth_token', token)
            return redirect(final_url)
        else:
            # 未登录，回跳并标记失败
            final_url = _append_query_param(return_url, 'sso_failed', '1')
            return redirect(final_url)

    logger.info("管理员路由注册完成")