#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证路由模块 - Token 认证 API
"""
import time
import requests as http_requests
from datetime import datetime
from flask import request, jsonify

from . import auth_bp
from .auth_helpers import extract_bearer_token, get_bound_token_session_issue
from ..config import logger
from ..utils import add_cache_headers, format_size, get_domain, get_image_domain, get_client_ip
from ..database import (
    verify_auth_token, verify_auth_token_access, get_token_info,
    update_token_description, is_token_generation_allowed, is_token_upload_allowed,
    get_system_setting_int,
    create_auth_token, get_token_uploads,
    get_system_setting, verify_tg_session, get_user_token_count, bind_token_to_user, unbind_token_from_user,
    create_auth_token_with_ip_limit, reserve_token_upload, release_upload_reservation,
)
from ..database.connection import get_connection
from ..services.file_service import process_upload
from .upload import validate_image_magic, is_extension_allowed, validate_upload_file


def _extract_bearer_token() -> str:
    """从 Authorization 头提取 Bearer Token（委托给 auth_helpers）"""
    return extract_bearer_token()


def _get_client_ip() -> str:
    """提取客户端 IP（兼容 Cloudflare + 反向代理）"""
    return get_client_ip(request)


@auth_bp.route('/api/auth/token/generate', methods=['POST'])
def generate_token():
    """Generate a guest token."""
    try:
        ip_address = _get_client_ip()
        user_agent = request.headers.get('User-Agent', '')

        tg_user_id = None
        if get_system_setting('tg_auth_required_for_token') == '1':
            tg_session_token = request.cookies.get('tg_session', '')
            session_info = verify_tg_session(tg_session_token)
            if not session_info:
                return add_cache_headers(jsonify({
                    'success': False,
                    'error': 'Telegram login required',
                }), 'no-cache'), 401

            tg_user_id = session_info['tg_user_id']
            max_tokens = get_system_setting_int('tg_max_tokens_per_user', 5, minimum=1)
            if get_user_token_count(tg_user_id) >= max_tokens:
                return add_cache_headers(jsonify({
                    'success': False,
                    'error': f'Token limit reached ({max_tokens})',
                }), 'no-cache'), 403
        else:
            if not is_token_generation_allowed():
                return add_cache_headers(jsonify({
                    'success': False,
                    'error': 'Token generation is disabled',
                }), 'no-cache'), 403

            if get_system_setting('tg_bind_token_enabled') == '1':
                tg_session_token = request.cookies.get('tg_session', '')
                if tg_session_token:
                    session_info = verify_tg_session(tg_session_token)
                    if session_info:
                        tg_user_id = session_info['tg_user_id']

        data = request.get_json(silent=True) or {}
        max_upload_limit = get_system_setting_int('guest_token_max_upload_limit', 1000, minimum=1, maximum=1000000)
        max_expires_days = get_system_setting_int('guest_token_max_expires_days', 365, minimum=1, maximum=36500)

        try:
            upload_limit = int(data.get('upload_limit', max_upload_limit))
        except (TypeError, ValueError):
            return add_cache_headers(jsonify({'success': False, 'error': 'upload_limit must be an integer'}), 'no-cache'), 400
        if upload_limit < 1 or upload_limit > max_upload_limit:
            return add_cache_headers(jsonify({
                'success': False,
                'error': f'upload_limit must be between 1 and {max_upload_limit}',
            }), 'no-cache'), 400

        try:
            expires_days = int(data.get('expires_days', max_expires_days))
        except (TypeError, ValueError):
            return add_cache_headers(jsonify({'success': False, 'error': 'expires_days must be an integer'}), 'no-cache'), 400
        if expires_days < 1 or expires_days > max_expires_days:
            return add_cache_headers(jsonify({
                'success': False,
                'error': f'expires_days must be between 1 and {max_expires_days}',
            }), 'no-cache'), 400

        description = str(data.get('description', 'guest-token'))[:200]

        create_reason = None
        if tg_user_id:
            token = create_auth_token(
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                upload_limit=upload_limit,
                expires_days=expires_days,
            )
        else:
            max_guest_tokens = get_system_setting_int('max_guest_tokens_per_ip', 3, minimum=1, maximum=100)
            token, create_reason = create_auth_token_with_ip_limit(
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                upload_limit=upload_limit,
                expires_days=expires_days,
                max_tokens_for_ip=max_guest_tokens,
            )
            if create_reason == 'ip_limit':
                return add_cache_headers(jsonify({
                    'success': False,
                    'error': f'Per-IP token limit reached ({max_guest_tokens})',
                }), 'no-cache'), 403

        if not token:
            return add_cache_headers(jsonify({'success': False, 'error': 'Failed to create token'}), 'no-cache'), 500

        if tg_user_id:
            bind_token_to_user(token, tg_user_id)

        token_info = get_token_info(token)
        return add_cache_headers(jsonify({
            'success': True,
            'data': {
                'token': token,
                'upload_limit': upload_limit,
                'expires_days': expires_days,
                'expires_at': token_info['expires_at'] if token_info else None,
                'message': f'Token created. Upload limit: {upload_limit}, expires in {expires_days} days.',
            }
        }), 'no-cache')

    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        return add_cache_headers(jsonify({
            'success': False,
            'error': 'Failed to generate token, please try again later',
        }), 'no-cache'), 500
@auth_bp.route('/api/auth/token/verify', methods=['POST'])
def verify_token_api():
    """验证 Token 是否有效"""
    try:
        token = _extract_bearer_token()
        if not token:
            data = request.get_json(silent=True) or {}
            token = data.get('token', '')

        if not token:
            return add_cache_headers(jsonify({'success': False, 'valid': False, 'error': '未提供Token'}), 'no-cache'), 400

        # 使用 access 验证（配额用完的Token也应能验证，以便查看相册）
        verification = verify_auth_token_access(token)

        if verification['valid']:
            token_data = verification['token_data']
            issue = get_bound_token_session_issue(token_data)
            if issue:
                # verify 接口保持 200 返回，前端才能稳定识别为 tokenInvalid 并移除本地失效 token
                return add_cache_headers(jsonify({
                    'success': False,
                    'valid': False,
                    'reason': issue['reason']
                }), 'no-cache')
            return add_cache_headers(jsonify({
                'success': True,
                'valid': True,
                'data': {
                    'upload_count': token_data['upload_count'],
                    'upload_limit': token_data['upload_limit'],
                    'remaining_uploads': verification.get('remaining_uploads', 0),
                    'can_upload': verification.get('can_upload', False),
                    'description': token_data.get('description'),
                    'expires_at': token_data['expires_at'],
                    'created_at': token_data['created_at'],
                    'last_used': token_data['last_used'],
                    'tg_user_id': token_data.get('tg_user_id'),
                }
            }), 'no-cache')
        else:
            return add_cache_headers(jsonify({
                'success': False,
                'valid': False,
                'reason': verification['reason']
            }), 'no-cache')

    except Exception as e:
        logger.error(f"验证token失败: {e}")
        return add_cache_headers(jsonify({'success': False, 'valid': False, 'error': '验证失败，请稍后重试'}), 'no-cache'), 500

@auth_bp.route('/api/auth/upload', methods=['POST'])
def upload_with_token():
    """Upload an image with a token."""
    if not is_token_upload_allowed():
        return add_cache_headers(jsonify({
            'success': False,
            'error': 'Token uploads are disabled',
        }), 'no-cache'), 403

    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': 'Missing token'}), 'no-cache'), 401

    # Check token access validity here; the atomic reservation step below is the
    # single source of truth for remaining upload quota and daily limits.
    verification = verify_auth_token_access(token)
    if not verification['valid']:
        return add_cache_headers(jsonify({
            'success': False,
            'error': f"Invalid token: {verification['reason']}",
        }), 'no-cache'), 401

    issue = get_bound_token_session_issue(verification.get('token_data'))
    if issue:
        return add_cache_headers(jsonify({'success': False, 'error': issue['reason']}), 'no-cache'), issue['status']

    if 'file' not in request.files:
        return add_cache_headers(jsonify({'success': False, 'error': 'Missing file'}), 'no-cache'), 400

    file = request.files['file']
    if file.filename == '':
        return add_cache_headers(jsonify({'success': False, 'error': 'Missing file'}), 'no-cache'), 400

    err, validated = validate_upload_file(file)
    if err:
        return err

    daily_limit = get_system_setting_int('daily_upload_limit', 0, minimum=0, maximum=1000000)
    reservation_key = None

    try:
        reservation = reserve_token_upload(token, daily_limit=daily_limit)
        if not reservation.get('ok'):
            return add_cache_headers(jsonify({
                'success': False,
                'error': reservation.get('reason', 'Upload blocked'),
            }), 'no-cache'), reservation.get('status', 429)

        reservation_key = reservation.get('reservation_key')
        remaining = reservation.get('remaining_uploads', 0)

        result = process_upload(
            file_content=None,
            filename=file.filename,
            content_type=validated.detected_mime,
            username='guest_user',
            source='guest_token',
            auth_token=token,
            staged_file_path=validated.temp_path,
            reservation_key=reservation_key,
        )

        if not result:
            if reservation_key:
                release_upload_reservation(reservation_key)
            return add_cache_headers(jsonify({'success': False, 'error': 'Failed to upload to storage backend'}), 'no-cache'), 500

        base_url = get_image_domain(request, scene='token')
        permanent_url = f"{base_url}/image/{result['encrypted_id']}"

        logger.info(f"Token upload complete: {file.filename} -> {result['encrypted_id']}, remaining={remaining}")
        return add_cache_headers(jsonify({
            'success': True,
            'data': {
                'url': permanent_url,
                'filename': file.filename,
                'size': format_size(result['file_size']),
                'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'remaining_uploads': remaining,
            }
        }), 'no-cache')

    except Exception as e:
        if reservation_key:
            release_upload_reservation(reservation_key)
        logger.error(f"Token upload failed: {e}")
        return add_cache_headers(jsonify({'success': False, 'error': 'Upload failed, please try again later'}), 'no-cache'), 500
    finally:
        if validated:
            validated.cleanup()
@auth_bp.route('/api/auth/uploads', methods=['GET'])
def get_token_uploads_api():
    """获取 Token 上传的图片列表"""
    try:
        token = _extract_bearer_token()
        if not token:
            token = request.args.get('token', '')

        if not token:
            return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

        # 使用 access 验证（即使额度用完也能查看相册）
        verification = verify_auth_token_access(token)
        if not verification['valid']:
            return add_cache_headers(jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 'no-cache'), 401
        issue = get_bound_token_session_issue(verification.get('token_data'))
        if issue:
            return add_cache_headers(jsonify({'success': False, 'error': issue['reason']}), 'no-cache'), issue['status']

        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)

        uploads = get_token_uploads(token, limit, page)

        base_url = get_image_domain(request)
        for upload in uploads:
            upload['image_url'] = f"{base_url}/image/{upload['encrypted_id']}"
            if upload.get('created_at'):
                try:
                    dt = datetime.fromisoformat(upload['created_at'].replace('Z', '+00:00'))
                    upload['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

        token_info = get_token_info(token)

        return add_cache_headers(jsonify({
            'success': True,
            'data': {
                'uploads': uploads,
                'total_uploads': token_info['upload_count'] if token_info else 0,
                'upload_limit': token_info['upload_limit'] if token_info else 0,
                'remaining_uploads': verification.get('remaining_uploads', 0),
                'can_upload': verification.get('can_upload', False),
                'page': page,
                'limit': limit,
                'has_more': len(uploads) == limit
            }
        }), 'no-cache')

    except Exception as e:
        logger.error(f"获取token上传列表失败: {e}")
        return add_cache_headers(jsonify({'success': False, 'error': '获取上传列表失败，请稍后重试'}), 'no-cache'), 500

@auth_bp.route('/api/auth/token', methods=['GET', 'PATCH', 'DELETE'])
def token_profile_api():
    """Token(=相册)信息：获取/更新描述（相册名称）/ 用户侧删除"""
    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

    # DELETE: 用户侧删除 Token（级联删除，可选同时删除图片）
    if request.method == 'DELETE':
        from ..services.token_service import TokenService
        delete_images = request.args.get('delete_images', '').lower() in ('true', '1')
        deleted = TokenService.delete_token_by_string(token, delete_images=delete_images)
        if not deleted:
            return add_cache_headers(jsonify({'success': False, 'error': 'Token 不存在'}), 'no-cache'), 404
        msg = 'Token 及关联图片已删除' if delete_images else 'Token 已删除'
        return add_cache_headers(jsonify({'success': True, 'message': msg}), 'no-cache')

    verification = verify_auth_token_access(token)
    if not verification['valid']:
        return add_cache_headers(jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 'no-cache'), 401
    issue = get_bound_token_session_issue(verification.get('token_data'))
    if issue:
        return add_cache_headers(jsonify({'success': False, 'error': issue['reason']}), 'no-cache'), issue['status']

    token_data = verification['token_data']

    if request.method == 'GET':
        # GET 响应中不返回完整 token（客户端已持有，无需回显；防止日志/代理泄露）
        raw = token
        token_masked = f"{raw[:8]}…{raw[-4:]}" if len(raw) > 12 else raw
        return add_cache_headers(jsonify({
            'success': True,
            'data': {
                'token_masked': token_masked,
                'description': token_data.get('description')
            }
        }), 'no-cache')

    # PATCH: 更新描述
    data = request.get_json(silent=True) or {}
    if 'description' not in data:
        return add_cache_headers(jsonify({'success': False, 'error': '缺少 description 参数'}), 'no-cache'), 400

    new_description = str(data.get('description') or '').strip()[:200]

    if not update_token_description(token, new_description):
        return add_cache_headers(jsonify({'success': False, 'error': '更新失败'}), 'no-cache'), 500

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'description': new_description
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/token/bind', methods=['POST'])
def bind_token_to_tg():
    """将当前 Token 绑定到当前 TG 用户"""
    # 检查 TG 认证总开关
    if get_system_setting('tg_auth_enabled') != '1':
        return add_cache_headers(jsonify({'success': False, 'error': 'TG 认证未启用'}), 'no-cache'), 403

    # 检查绑定开关
    if get_system_setting('tg_bind_token_enabled') != '1':
        return add_cache_headers(jsonify({'success': False, 'error': '绑定功能未开启'}), 'no-cache'), 403

    # 验证 TG 登录
    tg_session_token = request.cookies.get('tg_session', '')
    session_info = verify_tg_session(tg_session_token)
    if not session_info:
        return add_cache_headers(jsonify({'success': False, 'error': '需要先通过 Telegram 登录'}), 'no-cache'), 401

    # 验证 Token
    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

    result = verify_auth_token_access(token)
    if not result.get('valid'):
        return add_cache_headers(jsonify({'success': False, 'error': 'Token无效'}), 'no-cache'), 401

    # 检查 Token 是否已被其他用户绑定
    token_data = result['token_data']
    existing_tg_user_id = token_data.get('tg_user_id')
    current_tg_user_id = session_info['tg_user_id']

    if existing_tg_user_id and str(existing_tg_user_id) != str(current_tg_user_id):
        return add_cache_headers(jsonify({
            'success': False, 'error': '该 Token 已被其他用户绑定'
        }), 'no-cache'), 409

    # 未绑定时检查当前用户 Token 数量上限
    if not existing_tg_user_id:
        max_tokens = get_system_setting_int('tg_max_tokens_per_user', 5, minimum=1)
        if get_user_token_count(current_tg_user_id) >= max_tokens:
            return add_cache_headers(jsonify({
                'success': False, 'error': f'已达到 Token 上限（{max_tokens}个）'
            }), 'no-cache'), 403

    bind_token_to_user(token, current_tg_user_id)
    return add_cache_headers(jsonify({'success': True, 'message': '绑定成功'}), 'no-cache')


@auth_bp.route('/api/auth/token/unbind', methods=['POST'])
def unbind_token_from_tg():
    """解除当前 Token 与 TG 用户的绑定"""
    # 检查 TG 认证总开关
    if get_system_setting('tg_auth_enabled') != '1':
        return add_cache_headers(jsonify({'success': False, 'error': 'TG 认证未启用'}), 'no-cache'), 403

    # 验证 TG 登录
    tg_session_token = request.cookies.get('tg_session', '')
    session_info = verify_tg_session(tg_session_token)
    if not session_info:
        return add_cache_headers(jsonify({'success': False, 'error': '需要先通过 Telegram 登录'}), 'no-cache'), 401

    # 验证 Token
    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

    result = verify_auth_token_access(token)
    if not result.get('valid'):
        return add_cache_headers(jsonify({'success': False, 'error': 'Token无效'}), 'no-cache'), 401

    unbind_token_from_user(token, session_info['tg_user_id'])
    return add_cache_headers(jsonify({'success': True, 'message': '解绑成功'}), 'no-cache')


def _delete_tg_message(file_row: dict) -> bool:
    """
    同步删除 Telegram 频道中的消息（单一职责：仅处理 TG 消息删除）
    返回是否成功删除
    """
    chat_id = file_row.get('group_chat_id')
    message_id = file_row.get('group_message_id')
    storage_backend = (file_row.get('storage_backend') or 'telegram').strip()

    # 兼容历史数据：从 storage_meta 中提取 message_id，从后端配置获取 chat_id
    if not message_id or not chat_id:
        try:
            import json as _json
            meta_raw = file_row.get('storage_meta') or '{}'
            meta = _json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
            if not message_id:
                message_id = meta.get('message_id')
            if not chat_id and storage_backend:
                from ..storage.router import get_storage_router as _get_router
                be = _get_router().get_backend(storage_backend)
                if hasattr(be, '_chat_id'):
                    chat_id = be._chat_id
        except Exception:
            pass

    if not (chat_id and message_id):
        return False

    try:
        from ..bot_control import get_effective_bot_token
        bot_token, _ = get_effective_bot_token()
        if not bot_token:
            return False
        resp = http_requests.post(
            f"https://api.telegram.org/bot{bot_token}/deleteMessage",
            data={'chat_id': chat_id, 'message_id': message_id},
            timeout=5,
        )
        return resp.ok and resp.json().get('ok', False)
    except Exception:
        return False


def _delete_storage_file(file_row: dict) -> None:
    """
    删除存储后端文件（单一职责：仅处理存储文件删除）
    失败时仅记录日志，不抛出异常
    """
    storage_backend = (file_row.get('storage_backend') or 'telegram').strip()
    storage_key = file_row.get('storage_key') or ''
    encrypted_id = file_row.get('encrypted_id', '')

    if not storage_key:
        return

    try:
        from ..storage.router import get_storage_router
        router = get_storage_router()
        backend = router.get_backend(storage_backend)
        backend.delete(storage_key=storage_key)
    except Exception as e:
        logger.debug(f"用户删除-存储文件删除失败: {encrypted_id}, {e}")


def _delete_file_record(encrypted_id: str, token: str, *, delete_storage: bool = True) -> dict:
    """
    删除单个图片记录，可选同时删除存储后端文件。
    - delete_storage=True: 删除存储文件 + TG消息 + 数据库记录（完全删除）
    - delete_storage=False: 仅删除数据库记录（保留存储文件）
    返回 { 'deleted': bool, 'tg_deleted': bool, 'error': str|None }
    """
    result = {'deleted': False, 'tg_deleted': False, 'error': None}
    file_row = None

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询图片，确认属于该 Token
            cursor.execute(
                "SELECT encrypted_id, file_size, storage_backend, storage_key, "
                "group_chat_id, group_message_id, storage_meta "
                "FROM file_storage WHERE encrypted_id = ? AND auth_token = ?",
                (encrypted_id, token),
            )
            row = cursor.fetchone()
            if not row:
                result['error'] = '图片不存在或不属于当前Token'
                return result

            file_row = dict(row)

            # 删除数据库记录（先完成 DB 操作，释放锁）
            cursor.execute(
                "DELETE FROM file_storage WHERE encrypted_id = ? AND auth_token = ?",
                (encrypted_id, token),
            )
            if cursor.rowcount > 0:
                result['deleted'] = True
                # 递减 token 的 upload_count（不低于 0）
                cursor.execute(
                    "UPDATE auth_tokens SET upload_count = MAX(0, upload_count - 1) WHERE token = ?",
                    (token,),
                )

        # 外部操作放在事务外，避免长时间持有 DB 锁
        if result['deleted'] and delete_storage and file_row:
            _delete_storage_file(file_row)
            tg_sync_enabled = str(get_system_setting('tg_sync_delete_enabled') or '1') == '1'
            if tg_sync_enabled:
                result['tg_deleted'] = _delete_tg_message(file_row)

    except Exception as e:
        logger.error(f"用户删除图片失败: {encrypted_id}, {e}")
        result['error'] = '删除失败'

    return result


@auth_bp.route('/api/auth/images/<encrypted_id>', methods=['DELETE'])
def user_delete_image(encrypted_id):
    """用户侧删除单张图片（仅能删除自己Token关联的图片）"""
    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

    verification = verify_auth_token_access(token)
    if not verification['valid']:
        return add_cache_headers(jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 'no-cache'), 401
    issue = get_bound_token_session_issue(verification.get('token_data'))
    if issue:
        return add_cache_headers(jsonify({'success': False, 'error': issue['reason']}), 'no-cache'), issue['status']

    # 是否同时删除存储文件（默认 true，仅删记录时传 false）
    delete_storage = request.args.get('delete_storage', 'true').lower() not in ('false', '0')
    result = _delete_file_record(encrypted_id, token, delete_storage=delete_storage)
    if result['error']:
        return add_cache_headers(jsonify({'success': False, 'error': result['error']}), 'no-cache'), 404

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'deleted': 1 if result['deleted'] else 0,
            'tg_deleted': 1 if result['tg_deleted'] else 0,
        }
    }), 'no-cache')


@auth_bp.route('/api/auth/images/batch-delete', methods=['POST'])
def user_batch_delete_images():
    """用户侧批量删除图片"""
    token = _extract_bearer_token()
    if not token:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供Token'}), 'no-cache'), 401

    verification = verify_auth_token_access(token)
    if not verification['valid']:
        return add_cache_headers(jsonify({'success': False, 'error': f"Token无效: {verification['reason']}"}), 'no-cache'), 401
    issue = get_bound_token_session_issue(verification.get('token_data'))
    if issue:
        return add_cache_headers(jsonify({'success': False, 'error': issue['reason']}), 'no-cache'), issue['status']

    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])

    if not isinstance(ids, list) or not ids:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供要删除的图片ID'}), 'no-cache'), 400

    # 去重 + 清洗
    ids = list(dict.fromkeys(str(x).strip() for x in ids if x is not None and str(x).strip()))
    if not ids:
        return add_cache_headers(jsonify({'success': False, 'error': '未提供要删除的图片ID'}), 'no-cache'), 400

    # 限制单次批量删除数量
    if len(ids) > 100:
        return add_cache_headers(jsonify({'success': False, 'error': '单次最多删除100张图片'}), 'no-cache'), 400

    # 是否同时删除存储文件（默认 true）
    delete_storage = bool(data.get('delete_storage', True))

    deleted = 0
    failed = 0
    tg_deleted = 0

    for eid in ids:
        result = _delete_file_record(eid, token, delete_storage=delete_storage)
        if result['deleted']:
            deleted += 1
            if result['tg_deleted']:
                tg_deleted += 1
        else:
            failed += 1

    token_masked = f"{token[:8]}…{token[-4:]}" if len(token) > 12 else token
    logger.info(f"用户批量删除图片: token={token_masked}, 删除={deleted}, 失败={failed}, TG同步={tg_deleted}")

    return add_cache_headers(jsonify({
        'success': True,
        'data': {
            'deleted': deleted,
            'failed': failed,
            'tg_deleted': tg_deleted,
        }
    }), 'no-cache')
