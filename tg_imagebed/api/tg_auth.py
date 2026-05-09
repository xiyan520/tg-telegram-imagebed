#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TG 认证 API 路由"""
import time
import asyncio
import threading
from collections import defaultdict
from flask import request, jsonify, make_response

from . import auth_bp
from ..config import logger
from ..utils import add_cache_headers, get_client_ip
from ..device_fingerprint import (
    parse_user_agent,
    build_device_label,
    normalize_device_name,
)
from ..database import (
    get_system_setting, get_tg_user_by_username,
    create_login_code, verify_login_code,
    create_tg_session, verify_tg_session, delete_tg_session,
    touch_tg_session, list_tg_sessions, count_tg_sessions, revoke_tg_session,
    get_user_token_count, get_user_tokens, verify_auth_token_access,
    get_system_setting_int,
    get_web_verify_status,
)


class SimpleRateLimiter:
    """简单的内存速率限制器"""
    # 最大追踪条目数，防止内存无限增长（DoS 防护）
    _MAX_ENTRIES = 10000

    def __init__(self, max_requests: int, window_seconds: int):
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            reqs = self._requests[key]
            # 清理过期记录
            self._requests[key] = [t for t in reqs if t > cutoff]
            if len(self._requests[key]) >= self._max:
                return False
            # 超出最大条目数时，清理最旧的条目（LRU 淘汰）
            if len(self._requests) >= self._MAX_ENTRIES:
                oldest_key = next(iter(self._requests))
                del self._requests[oldest_key]
            self._requests[key].append(now)
            return True


# 速率限制器实例
_code_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)    # 验证码请求
_verify_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)  # 验证码验证
_sessions_limiter = SimpleRateLimiter(max_requests=60, window_seconds=60)  # 会话列表/心跳
_revoke_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)  # 会话下线


def _is_secure_request() -> bool:
    """检测当前请求是否通过 HTTPS（兼容反向代理）"""
    if request.is_secure:
        return True
    proto = (request.headers.get('X-Forwarded-Proto') or '').strip().lower()
    return proto == 'https'


def _get_client_ip() -> str:
    """提取客户端 IP"""
    return get_client_ip(request)


def _safe_text(value: str, max_len: int = 128) -> str:
    """清洗短文本，防止异常长头部值污染存储"""
    return str(value or '').strip()[:max_len]


def _get_device_id() -> str:
    """从请求头读取设备 ID（由前端生成并持久化）"""
    return _safe_text(request.headers.get('X-Device-Id', ''), 128)


def _get_device_name() -> str:
    """读取设备名称，允许前端覆盖默认解析"""
    return _safe_text(request.headers.get('X-Device-Name', ''), 120)


def _guess_platform(user_agent: str) -> str:
    return parse_user_agent(user_agent).get('platform') or 'web'


def _get_request_device_context() -> dict:
    """抽取请求设备上下文"""
    user_agent = _safe_text(request.headers.get('User-Agent', ''), 512)
    parsed_ua = parse_user_agent(user_agent)
    platform = _safe_text(request.headers.get('X-Platform', ''), 32) or parsed_ua.get('platform') or 'web'
    device_name = normalize_device_name(_get_device_name(), parsed_ua)
    device_label = build_device_label(parsed_ua.get('os_name'), parsed_ua.get('browser_name'))
    return {
        'ip_address': _get_client_ip(),
        'user_agent': user_agent,
        'device_id': _get_device_id(),
        'device_name': device_name,
        'platform': platform,
        'os_name': parsed_ua.get('os_name') or 'Unknown OS',
        'browser_name': parsed_ua.get('browser_name') or 'Unknown Browser',
        'browser_version': parsed_ua.get('browser_version') or '',
        'device_label': device_label,
    }


def _check_tg_auth_enabled():
    """检查 TG 认证是否启用，未启用返回错误响应"""
    if get_system_setting('tg_auth_enabled') != '1':
        return add_cache_headers(jsonify({
            'success': False, 'error': 'TG 认证未启用'
        }), 'no-cache'), 403
    return None


def _get_tg_session_info():
    """从 Cookie 获取并验证 TG 会话"""
    session_token = request.cookies.get('tg_session', '')
    if not session_token:
        return None
    session_info = verify_tg_session(session_token)
    if not session_info:
        return None
    ctx = _get_request_device_context()
    # 节流刷新活跃时间，避免每次请求都写库
    touch_tg_session(
        session_token,
        ip_address=ctx['ip_address'],
        user_agent=ctx['user_agent'],
        device_id=ctx['device_id'],
        device_name=ctx['device_name'],
        platform=ctx['platform'],
        min_interval_seconds=30,
    )
    session_info['session_token'] = session_token
    return session_info


@auth_bp.route('/api/auth/tg/request-code', methods=['POST'])
def tg_request_code():
    """Web 端请求发送验证码到 TG"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    if not _code_limiter.is_allowed(_get_client_ip()):
        return add_cache_headers(jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 'no-cache'), 429

    data = request.get_json(silent=True) or {}
    tg_username = (data.get('tg_username') or '').strip().lstrip('@')
    if not tg_username:
        return add_cache_headers(jsonify({
            'success': False, 'error': '请输入 Telegram 用户名'
        }), 'no-cache'), 400

    # 查找用户
    tg_user = get_tg_user_by_username(tg_username)
    if not tg_user:
        return add_cache_headers(jsonify({
            'success': False,
            'error': '未找到该用户，请先向 Bot 发送 /start'
        }), 'no-cache'), 400

    if tg_user.get('is_blocked'):
        return add_cache_headers(jsonify({
            'success': False, 'error': '该账号已被封禁'
        }), 'no-cache'), 403

    # 生成验证码
    code = create_login_code(
        code_type='verify',
        tg_user_id=tg_user['tg_user_id'],
        username_hint=tg_username,
        ip_address=_get_client_ip()
    )
    if not code:
        return add_cache_headers(jsonify({
            'success': False, 'error': '生成验证码失败'
        }), 'no-cache'), 500

    # 通过 Bot 跨线程发送验证码
    from ..bot.state import get_bot_instance, get_bot_loop
    bot = get_bot_instance()
    bot_loop = get_bot_loop()

    if not bot or not bot_loop:
        return add_cache_headers(jsonify({
            'success': False, 'error': 'Bot 未运行，无法发送验证码'
        }), 'no-cache'), 503

    try:
        future = asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=tg_user['tg_user_id'],
                text=f"🔐 你的图床登录验证码：\n\n`{code}`\n\n⏰ 有效期 5 分钟",
                parse_mode='Markdown'
            ),
            bot_loop
        )
        future.result(timeout=10)
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        return add_cache_headers(jsonify({
            'success': False, 'error': '发送验证码失败，请确认已向 Bot 发送过 /start'
        }), 'no-cache'), 500

    return add_cache_headers(jsonify({
        'success': True,
        'data': {'message': '验证码已发送到你的 Telegram'}
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/verify-code', methods=['POST'])
def tg_verify_code():
    """Web 端提交验证码登录"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    if not _verify_limiter.is_allowed(_get_client_ip()):
        return add_cache_headers(jsonify({'success': False, 'error': '验证过于频繁，请稍后再试'}), 'no-cache'), 429

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    if not code:
        return add_cache_headers(jsonify({
            'success': False, 'error': '请输入验证码'
        }), 'no-cache'), 400

    result = verify_login_code(code, code_type='verify')
    if not result:
        return add_cache_headers(jsonify({
            'success': False, 'error': '验证码无效或已过期'
        }), 'no-cache'), 401

    # 创建会话
    ctx = _get_request_device_context()
    session_token = create_tg_session(
        tg_user_id=result['tg_user_id'],
        ip_address=ctx['ip_address'],
        user_agent=ctx['user_agent'],
        device_id=ctx['device_id'],
        device_name=ctx['device_name'],
        platform=ctx['platform'],
    )
    if not session_token:
        return add_cache_headers(jsonify({
            'success': False, 'error': '创建会话失败'
        }), 'no-cache'), 500

    resp = make_response(jsonify({'success': True, 'data': {'message': '登录成功'}}))
    expire_days = get_system_setting_int('tg_session_expire_days', 30, minimum=1)
    resp.set_cookie(
        'tg_session', session_token,
        max_age=expire_days * 86400,
        httponly=True, samesite='Lax', path='/',
        secure=_is_secure_request()
    )
    return resp

@auth_bp.route('/api/auth/tg/login-link', methods=['POST'])
def tg_login_link():
    """消费一次性登录链接"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    if not code:
        return add_cache_headers(jsonify({
            'success': False, 'error': '缺少登录码'
        }), 'no-cache'), 400

    result = verify_login_code(code, code_type='login_link')
    if not result:
        return add_cache_headers(jsonify({
            'success': False, 'error': '登录链接无效或已过期'
        }), 'no-cache'), 401

    ctx = _get_request_device_context()
    session_token = create_tg_session(
        tg_user_id=result['tg_user_id'],
        ip_address=ctx['ip_address'],
        user_agent=ctx['user_agent'],
        device_id=ctx['device_id'],
        device_name=ctx['device_name'],
        platform=ctx['platform'],
    )
    if not session_token:
        return add_cache_headers(jsonify({
            'success': False, 'error': '创建会话失败'
        }), 'no-cache'), 500

    resp = make_response(jsonify({'success': True, 'data': {'message': '登录成功'}}))
    expire_days = get_system_setting_int('tg_session_expire_days', 30, minimum=1)
    resp.set_cookie(
        'tg_session', session_token,
        max_age=expire_days * 86400,
        httponly=True, samesite='Lax', path='/',
        secure=_is_secure_request()
    )
    return resp


@auth_bp.route('/api/auth/tg/session', methods=['GET'])
def tg_session_info():
    """获取当前 TG 会话信息"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': '未登录'
        }), 'no-cache'), 401

    tg_user_id = session_info['tg_user_id']
    max_tokens = get_system_setting_int('tg_max_tokens_per_user', 5, minimum=1)
    token_count = get_user_token_count(tg_user_id)
    online_sessions_count = count_tg_sessions(tg_user_id)

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'tg_user_id': tg_user_id,
            'username': session_info.get('username'),
            'first_name': session_info.get('first_name'),
            'token_count': token_count,
            'max_tokens': max_tokens,
            'current_session_id': session_info.get('session_id'),
            'online_sessions_count': online_sessions_count,
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/logout', methods=['POST'])
def tg_logout():
    """TG 登出"""
    session_token = request.cookies.get('tg_session', '')
    if session_token:
        delete_tg_session(session_token)

    resp = make_response(jsonify({'success': True, 'data': {'message': '已登出'}}))
    resp.delete_cookie('tg_session', path='/')
    return resp


@auth_bp.route('/api/auth/tg/web-code', methods=['POST'])
def tg_web_code():
    """生成 web_verify 验证码，返回验证码和 bot_username"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    if not _code_limiter.is_allowed(_get_client_ip()):
        return add_cache_headers(jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 'no-cache'), 429

    # 生成 web_verify 验证码（tg_user_id=NULL，等待 Bot 端消费）
    code = create_login_code(
        code_type='web_verify',
        tg_user_id=None,
        ip_address=_get_client_ip()
    )
    if not code:
        return add_cache_headers(jsonify({
            'success': False, 'error': '生成验证码失败'
        }), 'no-cache'), 500

    # 获取 bot_username
    from ..bot.state import get_bot_instance
    bot = get_bot_instance()
    bot_username = getattr(bot, 'username', None) or ''

    return add_cache_headers(jsonify({
        'success': True,
        'data': {'code': code, 'bot_username': bot_username}
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/code-status', methods=['GET'])
def tg_code_status():
    """轮询 web_verify 验证码状态"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    code = (request.args.get('code') or '').strip()
    if not code:
        return add_cache_headers(jsonify({
            'success': False, 'error': '缺少验证码参数'
        }), 'no-cache'), 400

    result = get_web_verify_status(code)
    if not result:
        return add_cache_headers(jsonify({
            'success': True, 'data': {'status': 'expired'}
        }), 'no-cache')

    if result['status'] == 'ok' and result['session_token']:
        ctx = _get_request_device_context()
        touch_tg_session(
            result['session_token'],
            ip_address=ctx['ip_address'],
            user_agent=ctx['user_agent'],
            device_id=ctx['device_id'],
            device_name=ctx['device_name'],
            platform=ctx['platform'],
            min_interval_seconds=0,
        )
        # 验证码已被 Bot 消费，设置 Cookie
        expire_days = get_system_setting_int('tg_session_expire_days', 30, minimum=1)
        resp = make_response(jsonify({
            'success': True, 'data': {'status': 'ok'}
        }))
        resp.set_cookie(
            'tg_session', result['session_token'],
            max_age=expire_days * 86400,
            httponly=True, samesite='Lax', path='/',
            secure=_is_secure_request()
        )
        return resp

    return add_cache_headers(jsonify({
        'success': True, 'data': {'status': result['status']}
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/sessions', methods=['GET'])
def tg_sessions_list():
    """获取当前 TG 用户的在线会话列表"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    ip = _get_client_ip()
    if not _sessions_limiter.is_allowed(ip):
        return add_cache_headers(jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 'no-cache'), 429

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': '未登录'
        }), 'no-cache'), 401

    current_session_id = session_info.get('session_id', '')
    items = list_tg_sessions(session_info['tg_user_id'], current_session_token=session_info.get('session_token', ''))
    sessions = []
    for item in items:
        ua = item.get('user_agent') or ''
        parsed_ua = parse_user_agent(ua)
        ip_addr = item.get('ip_address') or ''
        device_name = normalize_device_name(item.get('device_name'), parsed_ua)
        platform = item.get('platform') or parsed_ua.get('platform') or _guess_platform(ua)
        sessions.append({
            'session_id': item.get('session_id'),
            'device_id': item.get('device_id') or '',
            'device_name': device_name,
            'device_label': build_device_label(parsed_ua.get('os_name'), parsed_ua.get('browser_name')),
            'os_name': parsed_ua.get('os_name') or 'Unknown OS',
            'browser_name': parsed_ua.get('browser_name') or 'Unknown Browser',
            'browser_version': parsed_ua.get('browser_version') or '',
            'platform': platform,
            'ip_address': ip_addr,
            'user_agent': ua,
            'created_at': item.get('created_at'),
            'last_seen_at': item.get('last_seen_at') or item.get('device_last_seen_at'),
            'expires_at': item.get('expires_at'),
            'is_current': bool(item.get('is_current')),
        })

    # 兜底：确保当前浏览器会话在列表中（避免历史数据缺失导致“当前设备”不显示）
    has_current = any(s.get('is_current') for s in sessions)
    if not has_current and current_session_id:
        ctx = _get_request_device_context()
        sessions.insert(0, {
            'session_id': current_session_id,
            'device_id': ctx.get('device_id') or '',
            'device_name': ctx.get('device_name') or ctx.get('device_label') or 'current-browser',
            'device_label': ctx.get('device_label') or build_device_label(ctx.get('os_name'), ctx.get('browser_name')),
            'os_name': ctx.get('os_name') or 'Unknown OS',
            'browser_name': ctx.get('browser_name') or 'Unknown Browser',
            'browser_version': ctx.get('browser_version') or '',
            'platform': ctx.get('platform') or _guess_platform(ctx.get('user_agent', '')),
            'ip_address': session_info.get('ip_address') or ctx.get('ip_address') or '',
            'user_agent': session_info.get('user_agent') or ctx.get('user_agent') or '',
            'created_at': session_info.get('created_at') or session_info.get('last_seen_at') or '',
            'last_seen_at': session_info.get('last_seen_at') or '',
            'expires_at': session_info.get('expires_at') or '',
            'is_current': True,
        })

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'sessions': sessions,
            'current_session_id': current_session_id,
            'count': len(sessions),
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/sessions/revoke', methods=['POST'])
def tg_sessions_revoke():
    """撤销指定会话（不允许撤销当前会话）"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    ip = _get_client_ip()
    if not _revoke_limiter.is_allowed(ip):
        return add_cache_headers(jsonify({'success': False, 'error': '操作过于频繁，请稍后再试'}), 'no-cache'), 429

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': '未登录'
        }), 'no-cache'), 401

    data = request.get_json(silent=True) or {}
    target_session_id = _safe_text(data.get('session_id', ''), 64)
    if not target_session_id:
        return add_cache_headers(jsonify({
            'success': False, 'error': '缺少 session_id'
        }), 'no-cache'), 400
    if target_session_id == session_info.get('session_id'):
        return add_cache_headers(jsonify({
            'success': False, 'error': '不能下线当前会话'
        }), 'no-cache'), 400

    ok = revoke_tg_session(target_session_id, session_info['tg_user_id'], reason='manual')
    if not ok:
        return add_cache_headers(jsonify({
            'success': False, 'error': '会话不存在或已失效'
        }), 'no-cache'), 404

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'revoked_session_id': target_session_id
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/sessions/heartbeat', methods=['POST'])
def tg_sessions_heartbeat():
    """刷新当前会话活跃状态"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    ip = _get_client_ip()
    if not _sessions_limiter.is_allowed(ip):
        return add_cache_headers(jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 'no-cache'), 429

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': '未登录'
        }), 'no-cache'), 401

    ctx = _get_request_device_context()
    ok = touch_tg_session(
        session_info.get('session_token', ''),
        ip_address=ctx['ip_address'],
        user_agent=ctx['user_agent'],
        device_id=ctx['device_id'],
        device_name=ctx['device_name'],
        platform=ctx['platform'],
        min_interval_seconds=0,
    )
    if not ok:
        return add_cache_headers(jsonify({
            'success': False, 'error': '会话已失效'
        }), 'no-cache'), 401

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'server_time': int(time.time())
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/tokens', methods=['GET'])
def tg_user_tokens():
    """获取当前 TG 用户绑定的 Token 列表"""
    err = _check_tg_auth_enabled()
    if err:
        return err

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': '未登录'
        }), 'no-cache'), 401

    tokens = get_user_tokens(session_info['tg_user_id'])
    # 脱敏 token 值
    for t in tokens:
        raw = t.get('token', '')
        t['token_masked'] = f"{raw[:8]}…{raw[-4:]}" if len(raw) > 12 else raw
        del t['token']

    return add_cache_headers(jsonify({
        'success': True,
        'data': {'tokens': tokens}
    }), 'no-cache')


@auth_bp.route('/api/auth/tg/sync-tokens', methods=['GET'])
def tg_sync_tokens():
    """Sync all active tokens for the current TG user to the frontend vault."""
    err = _check_tg_auth_enabled()
    if err:
        return err

    session_info = _get_tg_session_info()
    if not session_info:
        return add_cache_headers(jsonify({
            'success': False, 'error': 'Not logged in'
        }), 'no-cache'), 401

    tokens = get_user_tokens(session_info['tg_user_id'])
    tg_user_id = session_info['tg_user_id']
    result = []
    for item in tokens:
        token_value = item.get('token')
        if not token_value:
            continue

        verification = verify_auth_token_access(token_value)
        if not verification.get('valid'):
            continue

        token_data = verification.get('token_data') or {}
        result.append({
            'token': token_value,
            'description': token_data.get('description', ''),
            'upload_count': token_data.get('upload_count', 0),
            'upload_limit': token_data.get('upload_limit'),
            'remaining_uploads': verification.get('remaining_uploads', 0),
            'expires_at': token_data.get('expires_at', ''),
            'created_at': token_data.get('created_at', ''),
            'last_used': token_data.get('last_used') or None,
            'can_upload': verification.get('can_upload', False),
            'tg_user_id': tg_user_id,
        })

    return add_cache_headers(jsonify({
        'success': True,
        'data': {'tokens': result}
    }), 'no-cache')
@auth_bp.route('/api/auth/tg/webhook/<secret>', methods=['POST'])
def tg_webhook_ingest(secret: str):
    """
    Telegram Webhook 入站端点

    将更新转发到 Bot 线程中的 Application.update_queue。
    """
    from telegram import Update
    from ..bot.state import (
        get_bot_application, get_bot_instance, get_bot_loop, _set_queue_depth
    )
    from ..bot_control import get_webhook_secret

    expected_secret = get_webhook_secret()
    if not expected_secret or secret != expected_secret:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    telegram_app = get_bot_application()
    bot = get_bot_instance()
    bot_loop = get_bot_loop()
    if not telegram_app or not bot or not bot_loop:
        return jsonify({'ok': False, 'error': 'bot_not_ready'}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'ok': False, 'error': 'invalid_payload'}), 400

    try:
        update_obj = Update.de_json(payload, bot)
        fut = asyncio.run_coroutine_threadsafe(
            telegram_app.update_queue.put(update_obj),
            bot_loop
        )
        fut.result(timeout=3)
        try:
            _set_queue_depth(telegram_app.update_queue.qsize())
        except Exception:
            pass
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Webhook 更新入队失败: {type(e).__name__}: {e}")
        return jsonify({'ok': False, 'error': 'enqueue_failed'}), 500
