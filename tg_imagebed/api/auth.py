#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证路由模块 - Token 认证 API
"""
import time
from datetime import datetime
from flask import request, jsonify, make_response

from . import auth_bp
from ..config import logger
from ..utils import add_cache_headers, format_size, get_domain
from ..database import (
    verify_auth_token, verify_auth_token_access, get_token_info, update_token_usage,
    update_token_description, is_token_generation_allowed, is_token_upload_allowed,
    get_system_setting_int, get_upload_count_today
)
from ..services.auth_service import create_token, get_token_upload_history
from ..services.file_service import process_upload


def _extract_bearer_token() -> str:
    """从 Authorization 头提取 Bearer Token"""
    auth_header = (request.headers.get('Authorization') or '').strip()
    if not auth_header:
        return ''
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()
    return auth_header


@auth_bp.route('/api/auth/token/generate', methods=['POST', 'OPTIONS'])
def generate_guest_token():
    """生成游客 Token"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    # 检查是否允许生成 Token
    if not is_token_generation_allowed():
        response = jsonify({
            'success': False,
            'error': 'Token 生成已关闭，请联系管理员'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 403

    try:
        # 提取客户端 IP（处理代理情况）
        xff = (request.headers.get('X-Forwarded-For') or '').strip()
        ip_address = xff.split(',')[0].strip() if xff else request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        data = request.get_json(silent=True) or {}

        # 获取系统配置的限制
        max_upload_limit = get_system_setting_int('guest_token_max_upload_limit', 1000, minimum=1, maximum=1000000)
        max_expires_days = get_system_setting_int('guest_token_max_expires_days', 365, minimum=1, maximum=36500)

        # 验证 upload_limit 参数
        try:
            upload_limit = int(data.get('upload_limit', min(100, max_upload_limit)))
        except (TypeError, ValueError):
            response = jsonify({'success': False, 'error': 'upload_limit 必须为整数'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400
        if upload_limit < 1 or upload_limit > max_upload_limit:
            response = jsonify({'success': False, 'error': f'upload_limit 必须在 1-{max_upload_limit} 之间'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400

        # 验证 expires_days 参数
        try:
            expires_days = int(data.get('expires_days', min(30, max_expires_days)))
        except (TypeError, ValueError):
            response = jsonify({'success': False, 'error': 'expires_days 必须为整数'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400
        if expires_days < 1 or expires_days > max_expires_days:
            response = jsonify({'success': False, 'error': f'expires_days 必须在 1-{max_expires_days} 之间'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400

        # 限制描述长度
        description = str(data.get('description', '游客Token'))[:200]

        token = create_token(
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            upload_limit=upload_limit,
            expires_days=expires_days
        )

        if not token:
            response = jsonify({'success': False, 'error': '生成Token失败'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 500

        token_info = get_token_info(token)

        response = jsonify({
            'success': True,
            'data': {
                'token': token,
                'upload_limit': upload_limit,
                'expires_days': expires_days,
                'expires_at': token_info['expires_at'] if token_info else None,
                'message': f'Token已生成，可上传{upload_limit}张图片，有效期{expires_days}天'
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"生成token失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@auth_bp.route('/api/auth/token/verify', methods=['POST', 'OPTIONS'])
def verify_guest_token():
    """验证 Token 是否有效"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    try:
        token = _extract_bearer_token()
        if not token:
            data = request.get_json(silent=True) or {}
            token = data.get('token', '')

        if not token:
            response = jsonify({'success': False, 'valid': False, 'error': '未提供Token'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400

        # 使用 access 验证（配额用完的Token也应能验证，以便查看相册）
        verification = verify_auth_token_access(token)

        if verification['valid']:
            token_data = verification['token_data']
            response = jsonify({
                'success': True,
                'valid': True,
                'data': {
                    'upload_count': token_data['upload_count'],
                    'upload_limit': token_data['upload_limit'],
                    'remaining_uploads': max(0, verification.get('remaining_uploads', 0)),
                    'can_upload': verification.get('can_upload', False),
                    'description': token_data.get('description'),
                    'expires_at': token_data['expires_at'],
                    'created_at': token_data['created_at'],
                    'last_used': token_data['last_used']
                }
            })
        else:
            response = jsonify({
                'success': False,
                'valid': False,
                'reason': verification['reason']
            })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"验证token失败: {e}")
        response = jsonify({'success': False, 'valid': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@auth_bp.route('/api/auth/upload', methods=['POST', 'OPTIONS'])
def upload_with_token():
    """使用 Token 上传图片"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    # 检查是否允许 Token 上传
    if not is_token_upload_allowed():
        response = jsonify({
            'success': False,
            'error': 'Token 上传已关闭，仅管理员可上传'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 403

    # 获取并验证 Token
    token = _extract_bearer_token()
    if not token:
        response = jsonify({'success': False, 'error': '未提供Token'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    verification = verify_auth_token(token)
    if not verification['valid']:
        response = jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    # 检查每日上传限制（按 token 统计）
    daily_limit = get_system_setting_int('daily_upload_limit', 0, minimum=0, maximum=1000000)
    if daily_limit > 0:
        uploaded_today = get_upload_count_today(auth_token=token)
        if uploaded_today >= daily_limit:
            response = jsonify({'success': False, 'error': f'已达到每日上传限制({daily_limit}张)'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 429

    # 检查文件
    if 'file' not in request.files:
        response = jsonify({'success': False, 'error': '未提供文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    file = request.files['file']
    if file.filename == '':
        response = jsonify({'success': False, 'error': '未选择文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    if not file.content_type.startswith('image/'):
        response = jsonify({'success': False, 'error': '只允许上传图片文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    # 使用动态配置的文件大小限制
    max_size_mb = get_system_setting_int('max_file_size_mb', 20, minimum=1, maximum=1024)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        response = jsonify({'success': False, 'error': f'文件大小超过 {max_size_mb}MB 限制'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    try:
        file_content = file.read()

        result = process_upload(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            username='guest_user',
            source='guest_token',
            auth_token=token
        )

        if not result:
            resp = jsonify({'success': False, 'error': '上传到Telegram失败'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        # 更新 Token 使用次数
        update_token_usage(token)

        # 生成 URL
        base_url = get_domain(request)
        permanent_url = f"{base_url}/image/{result['encrypted_id']}"

        # 获取剩余上传次数
        verification_after = verify_auth_token(token)
        remaining = verification_after.get('remaining_uploads', 0) if verification_after['valid'] else 0

        logger.info(f"游客上传完成: {file.filename} -> {result['encrypted_id']}, 剩余: {remaining}次")

        resp = jsonify({
            'success': True,
            'data': {
                'url': permanent_url,
                'filename': file.filename,
                'size': format_size(result['file_size']),
                'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'remaining_uploads': remaining
            }
        })

        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache')

    except Exception as e:
        logger.error(f"Token上传错误: {e}")
        resp = jsonify({'success': False, 'error': str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache'), 500


@auth_bp.route('/api/auth/uploads', methods=['GET', 'OPTIONS'])
def get_token_uploads_api():
    """获取 Token 上传的图片列表"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    try:
        token = _extract_bearer_token()
        if not token:
            token = request.args.get('token', '')

        if not token:
            response = jsonify({'success': False, 'error': '未提供Token'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 401

        # 使用 access 验证（即使额度用完也能查看相册）
        verification = verify_auth_token_access(token)
        if not verification['valid']:
            response = jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 401

        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)

        uploads = get_token_upload_history(token, limit, page)

        base_url = get_domain(request)
        for upload in uploads:
            upload['image_url'] = f"{base_url}/image/{upload['encrypted_id']}"
            if upload.get('created_at'):
                try:
                    dt = datetime.fromisoformat(upload['created_at'].replace('Z', '+00:00'))
                    upload['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

        token_info = get_token_info(token)

        response = jsonify({
            'success': True,
            'data': {
                'uploads': uploads,
                'total_uploads': token_info['upload_count'] if token_info else 0,
                'upload_limit': token_info['upload_limit'] if token_info else 0,
                'remaining_uploads': max(0, verification.get('remaining_uploads', 0)),
                'can_upload': verification.get('can_upload', False),
                'page': page,
                'limit': limit,
                'has_more': len(uploads) == limit
            }
        })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'private', 60)

    except Exception as e:
        logger.error(f"获取token上传列表失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500


@auth_bp.route('/api/auth/token', methods=['GET', 'PATCH', 'OPTIONS'])
def token_profile_api():
    """Token(=相册)信息：获取/更新描述（相册名称）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    token = _extract_bearer_token()
    if not token:
        response = jsonify({'success': False, 'error': '未提供Token'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    verification = verify_auth_token_access(token)
    if not verification['valid']:
        response = jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    token_data = verification['token_data']

    if request.method == 'GET':
        response = jsonify({
            'success': True,
            'data': {
                'token': token,
                'description': token_data.get('description')
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    # PATCH: 更新描述
    data = request.get_json(silent=True) or {}
    if 'description' not in data:
        response = jsonify({'success': False, 'error': '缺少 description 参数'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    new_description = str(data.get('description') or '').strip()[:200]

    if not update_token_description(token, new_description):
        response = jsonify({'success': False, 'error': '更新失败'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

    response = jsonify({
        'success': True,
        'data': {
            'token': token,
            'description': new_description
        }
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, 'no-cache')
