#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传路由模块 - 处理文件上传 API
"""
import time
from flask import request, jsonify, make_response

from . import upload_bp
from ..config import logger
from ..utils import add_cache_headers, format_size, get_domain
from ..services.file_service import process_upload
from ..database import is_guest_upload_allowed, get_system_setting_int, get_upload_count_today

# 图片魔数签名
IMAGE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'RIFF': 'image/webp',  # WebP (需额外检查 WEBP 标识)
    b'BM': 'image/bmp',
}

# SVG 文本特征（去除 BOM 后匹配）
_SVG_PREFIXES = (b'<?xml', b'<svg', b'<SVG')


def validate_image_magic(content: bytes) -> str | None:
    """基于魔数验证图片类型，返回 MIME 类型或 None"""
    if len(content) < 5:
        return None
    for sig, mime in IMAGE_SIGNATURES.items():
        if content.startswith(sig):
            if sig == b'RIFF' and content[8:12] != b'WEBP':
                continue
            return mime
    # SVG 是基于文本的 XML，无二进制魔数，单独检测
    # 去除可能的 UTF-8 BOM (0xEF 0xBB 0xBF)
    stripped = content[3:] if content.startswith(b'\xef\xbb\xbf') else content
    stripped = stripped.lstrip()
    if stripped.startswith(_SVG_PREFIXES):
        return 'image/svg+xml'
    return None


@upload_bp.route('/api/upload', methods=['POST', 'OPTIONS'])
@upload_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    """处理前端文件上传（匿名上传）"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    # 检查游客上传权限
    if not is_guest_upload_allowed():
        response = jsonify({
            'success': False,
            'error': '匿名上传已关闭，请使用 Token 上传或联系管理员'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 403

    # 检查文件
    if 'file' not in request.files:
        response = jsonify({'error': 'No file provided'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    file = request.files['file']
    if file.filename == '':
        response = jsonify({'error': 'No file selected'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    content_type = (file.content_type or '').strip().lower()

    # 初步检查 Content-Type
    if content_type and not content_type.startswith('image/'):
        response = jsonify({'success': False, 'error': '只允许上传图片文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    # 检查每日上传限制（匿名上传按来源全局限制）
    daily_limit = get_system_setting_int('daily_upload_limit', 0, minimum=0, maximum=1000000)
    if daily_limit > 0:
        uploaded_today = get_upload_count_today(source='web_upload')
        if uploaded_today >= daily_limit:
            response = jsonify({'success': False, 'error': f'已达到每日上传限制({daily_limit}张)'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 429

    # 检查文件大小（使用动态配置）
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    max_size_mb = get_system_setting_int('max_file_size_mb', 20, minimum=1, maximum=1024)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        response = jsonify({'success': False, 'error': f'文件大小超过 {max_size_mb}MB 限制'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    try:
        file_content = file.read()

        # 魔数校验：验证文件实际类型
        detected_mime = validate_image_magic(file_content)
        if not detected_mime:
            response = jsonify({'success': False, 'error': '无效的图片文件格式'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400

        # 处理上传
        result = process_upload(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            username='web_user',
            source='web_upload'
        )

        if not result:
            resp = jsonify({'error': 'Failed to upload to Telegram'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        # 生成 URL
        base_url = get_domain(request)
        permanent_url = f"{base_url}/image/{result['encrypted_id']}"

        logger.info(f"Web上传完成: {file.filename} -> {result['encrypted_id']}")

        resp = jsonify({
            'success': True,
            'data': {
                'url': permanent_url,
                'filename': file.filename,
                'size': format_size(result['file_size']),
                'upload_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache')

    except Exception as e:
        logger.error(f"Upload error: {e}")
        resp = jsonify({'error': str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache'), 500
