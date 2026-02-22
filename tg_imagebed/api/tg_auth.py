#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TG 认证 API 路由"""
import asyncio
from flask import request, jsonify, make_response

from . import auth_bp
from ..config import logger
from ..utils import add_cache_headers
from ..database import (
    get_system_setting, get_tg_user_by_username,
    create_login_code, verify_login_code,
    create_tg_session, verify_tg_session, delete_tg_session,
    get_user_token_count, get_user_tokens,
    get_system_setting_int,
    get_web_verify_status,
)


def _get_client_ip() -> str:
    """提取客户端 IP"""
    xff = (request.headers.get('X-Forwarded-For') or '').strip()
    return xff.split(',')[0].strip() if xff else request.remote_addr


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
    return verify_tg_session(session_token)


@auth_bp.route('/api/auth/tg/request-code', methods=['POST'])
def tg_request_code():
    """Web 端请求发送验证码到 TG"""
    err = _check_tg_auth_enabled()
    if err:
        return err

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
    session_token = create_tg_session(
        tg_user_id=result['tg_user_id'],
        ip_address=_get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')
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
        httponly=True, samesite='Lax', path='/'
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

    session_token = create_tg_session(
        tg_user_id=result['tg_user_id'],
        ip_address=_get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')
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
        httponly=True, samesite='Lax', path='/'
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

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'tg_user_id': tg_user_id,
            'username': session_info.get('username'),
            'first_name': session_info.get('first_name'),
            'token_count': token_count,
            'max_tokens': max_tokens,
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
        # 验证码已被 Bot 消费，设置 Cookie
        expire_days = get_system_setting_int('tg_session_expire_days', 30, minimum=1)
        resp = make_response(jsonify({
            'success': True, 'data': {'status': 'ok'}
        }))
        resp.set_cookie(
            'tg_session', result['session_token'],
            max_age=expire_days * 86400,
            httponly=True, samesite='Lax', path='/'
        )
        return resp

    return add_cache_headers(jsonify({
        'success': True, 'data': {'status': result['status']}
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
