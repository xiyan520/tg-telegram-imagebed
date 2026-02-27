#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员更新 API
"""
from flask import jsonify, request, Response

from . import admin_bp
from .. import admin_module
from ..config import logger
from ..utils import add_cache_headers
from ..services.update_service import (
    get_update_runtime_info,
    check_for_updates,
    start_update_task,
    get_update_status,
)


def _admin_update_cors(response: Response) -> Response:
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


def _admin_update_options(methods: str) -> Response:
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Methods'] = methods
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(response, 'no-cache')


@admin_bp.route('/api/admin/update/info', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_update_info():
    if request.method == 'OPTIONS':
        return _admin_update_options('GET, OPTIONS')

    try:
        data = get_update_runtime_info()
        response = jsonify({'success': True, 'data': data})
        return add_cache_headers(_admin_update_cors(response), 'no-cache')
    except Exception as e:
        logger.error(f"获取更新运行信息失败: {e}")
        response = jsonify({'success': False, 'error': '获取更新信息失败'})
        return add_cache_headers(_admin_update_cors(response), 'no-cache'), 500


@admin_bp.route('/api/admin/update/check', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_update_check():
    if request.method == 'OPTIONS':
        return _admin_update_options('POST, OPTIONS')

    try:
        data = check_for_updates()
        response = jsonify({'success': True, 'data': data})
        return add_cache_headers(_admin_update_cors(response), 'no-cache')
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cache_headers(_admin_update_cors(response), 'no-cache'), 400


@admin_bp.route('/api/admin/update/run', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_update_run():
    if request.method == 'OPTIONS':
        return _admin_update_options('POST, OPTIONS')

    try:
        ok, message, task_id = start_update_task()
        status_code = 200 if ok else 409
        response = jsonify({
            'success': ok,
            'message': message,
            'data': {'task_id': task_id},
        })
        return add_cache_headers(_admin_update_cors(response), 'no-cache'), status_code
    except Exception as e:
        logger.error(f"启动更新任务失败: {e}")
        response = jsonify({'success': False, 'error': '启动更新任务失败'})
        return add_cache_headers(_admin_update_cors(response), 'no-cache'), 500


@admin_bp.route('/api/admin/update/status', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def admin_update_status():
    if request.method == 'OPTIONS':
        return _admin_update_options('GET, OPTIONS')

    try:
        data = get_update_status()
        response = jsonify({'success': True, 'data': data})
        return add_cache_headers(_admin_update_cors(response), 'no-cache')
    except Exception as e:
        logger.error(f"获取更新状态失败: {e}")
        response = jsonify({'success': False, 'error': '获取更新状态失败'})
        return add_cache_headers(_admin_update_cors(response), 'no-cache'), 500

