#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由 - 存储配置管理
"""
import re
import json

from flask import request, jsonify, Response, session

from . import admin_bp
from .admin_helpers import _admin_json, _admin_options
from ..config import logger
from ..utils import add_cache_headers, format_size, get_domain
from ..database import get_system_setting, update_system_setting
from ..services.file_service import process_upload
from ..storage.router import get_storage_router, reload_storage_router, _load_storage_config
from .. import admin_module

# 敏感字段列表（需要掩码）
_SENSITIVE_FIELDS = {'bot_token', 'secret_key', 'access_key'}
_MASKED_VALUE = '__MASKED__'
# 允许的驱动类型
_ALLOWED_DRIVERS = {'telegram', 'local', 's3', 'rclone'}
# 后端名称正则（字母、数字、下划线、连字符，1-32字符）
_BACKEND_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')


def _mask_sensitive(cfg: dict) -> dict:
    """对配置中的敏感字段进行掩码处理"""
    result = {}
    for k, v in (cfg or {}).items():
        if isinstance(v, dict):
            result[k] = _mask_sensitive(v)
        elif k in _SENSITIVE_FIELDS and v:
            result[k] = _MASKED_VALUE
        else:
            result[k] = v
    return result


def _merge_sensitive(new_cfg: dict, old_cfg: dict) -> dict:
    """合并配置，保留被掩码的敏感字段原值，并保留旧配置中未在新配置中出现的字段"""
    result = dict(old_cfg or {})
    for k, v in (new_cfg or {}).items():
        if isinstance(v, dict) and isinstance(old_cfg.get(k), dict):
            result[k] = _merge_sensitive(v, old_cfg[k])
        elif k in _SENSITIVE_FIELDS and v == _MASKED_VALUE:
            result[k] = old_cfg.get(k, '')
        else:
            result[k] = v
    return result


def _save_storage_config(config: dict) -> None:
    """保存存储配置到数据库"""
    update_system_setting('storage_config_json', json.dumps(config, ensure_ascii=False))
    reload_storage_router()


@admin_bp.route('/api/admin/storage', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def get_storage_backends():
    """获取所有配置的存储后端"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        router = get_storage_router()
        backends = router.list_backends()
        active_name = router.get_active_backend_name()

        return _admin_json({
            'success': True,
            'data': {'active': active_name, 'backends': backends}
        })

    except Exception as e:
        logger.error(f"获取存储后端列表失败: {e}")
        return _admin_json({'success': False, 'error': '获取存储后端列表失败'}, 500)


@admin_bp.route('/api/admin/storage/active', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def set_active_storage():
    """设置激活的存储后端"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    try:
        data = request.get_json() or {}
        backend_name = (data.get('backend') or '').strip()

        if not backend_name:
            return _admin_json({'success': False, 'error': '请指定后端名称'}, 400)

        router = get_storage_router()
        backends = router.list_backends()
        if backend_name not in backends:
            return _admin_json({'success': False, 'error': f'后端 {backend_name} 不存在'}, 400)

        update_system_setting('storage_active_backend', backend_name)
        reload_storage_router()

        logger.info(f"存储后端已切换到: {backend_name}")
        return _admin_json({'success': True, 'message': f'已切换到 {backend_name} 后端', 'active': backend_name})

    except Exception as e:
        logger.error(f"切换存储后端失败: {e}")
        return _admin_json({'success': False, 'error': '切换存储后端失败'}, 500)


@admin_bp.route('/api/admin/storage/health', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def check_storage_health():
    """检查存储后端健康状态"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        router = get_storage_router()
        backends = router.list_backends()
        health_status = {}

        for name in backends.keys():
            try:
                backend = router.get_backend(name)
                health_status[name] = backend.healthcheck()
            except Exception as e:
                logger.warning(f"后端 {name} 健康检查失败: {e}")
                health_status[name] = False

        return _admin_json({'success': True, 'data': health_status})

    except Exception as e:
        logger.error(f"存储健康检查失败: {e}")
        return _admin_json({'success': False, 'error': '存储健康检查失败'}, 500)


@admin_bp.route('/api/admin/storage/policy', methods=['GET', 'PUT', 'OPTIONS'])
@admin_module.login_required
def storage_upload_policy():
    """获取/更新上传场景路由策略"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, PUT, OPTIONS')

    try:
        router = get_storage_router()
        backends = router.list_backends()

        if request.method == 'GET':
            return _admin_json({
                'success': True,
                'data': {
                    'policy': router.get_effective_upload_policy(),
                    'available_backends': list(backends.keys()),
                }
            })

        # PUT 请求：更新策略
        data = request.get_json(silent=True) or {}
        policy = data.get('policy') if isinstance(data.get('policy'), dict) else data
        if not isinstance(policy, dict):
            return _admin_json({'success': False, 'error': 'policy 必须为 JSON 对象'}, 400)

        def _check_name(v: str) -> str:
            v = str(v or '').strip()
            if v and v not in backends:
                raise ValueError(f"后端 {v} 未配置")
            return v

        normalized = {
            'guest': _check_name(policy.get('guest')),
            'token': _check_name(policy.get('token')),
            'group': _check_name(policy.get('group')),
            'admin_default': _check_name(policy.get('admin_default')),
            'admin_allowed': [str(x).strip() for x in (policy.get('admin_allowed') or []) if str(x).strip()],
        }
        for x in normalized['admin_allowed']:
            if x not in backends:
                raise ValueError(f"admin_allowed 包含未配置后端: {x}")

        update_system_setting('storage_upload_policy_json', json.dumps(normalized, ensure_ascii=False))
        return _admin_json({'success': True, 'data': {'policy': normalized}})

    except Exception as e:
        logger.error(f"存储策略操作失败: {e}")
        return _admin_json({'success': False, 'error': '存储策略操作失败'}, 500)


@admin_bp.route('/api/admin/upload', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_upload():
    """管理员上传（可选指定后端）"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    if 'file' not in request.files:
        return _admin_json({'success': False, 'error': '未提供文件'}, 400)

    f = request.files['file']
    if not f.filename:
        return _admin_json({'success': False, 'error': '未选择文件'}, 400)

    content_type = (f.content_type or '').strip()
    if not content_type.startswith('image/'):
        return _admin_json({'success': False, 'error': '只允许上传图片文件'}, 400)

    backend = (request.form.get('backend') or '').strip()

    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    file_content = f.read()

    try:
        result = process_upload(
            file_content=file_content,
            filename=f.filename,
            content_type=content_type,
            username=session.get('admin_username', 'admin'),
            source='admin_upload',
            upload_scene='admin',
            requested_backend=backend or None,
        )
    except ValueError as e:
        return _admin_json({'success': False, 'error': str(e)}, 400)

    if not result:
        return _admin_json({'success': False, 'error': '上传失败'}, 500)

    base_url = get_domain(request)
    url = f"{base_url}/image/{result['encrypted_id']}"

    return _admin_json({
        'success': True,
        'data': {
            'url': url,
            'encrypted_id': result['encrypted_id'],
            'filename': f.filename,
            'size': format_size(result['file_size']),
        }
    })


@admin_bp.route('/api/admin/storage/config', methods=['GET', 'OPTIONS'])
@admin_module.login_required
def get_storage_config():
    """获取完整存储配置（敏感字段掩码）"""
    if request.method == 'OPTIONS':
        return _admin_options('GET, OPTIONS')

    try:
        config = _load_storage_config()
        current_bot_token = str(get_system_setting('telegram_bot_token') or '').strip()
        masked_backends = {}
        for name, cfg in (config.get('backends') or {}).items():
            masked = _mask_sensitive(cfg)
            # 为 telegram 驱动标记是否正在用作机器人
            if cfg.get('driver') == 'telegram' and current_bot_token:
                raw_token = (cfg.get('bot_token') or '').strip()
                masked['is_bot'] = bool(raw_token and raw_token == current_bot_token)
            masked_backends[name] = masked

        return _admin_json({
            'success': True,
            'data': {
                'active': config.get('active', 'telegram'),
                'backends': masked_backends,
            }
        })

    except Exception as e:
        logger.error(f"获取存储配置失败: {e}")
        return _admin_json({'success': False, 'error': '获取存储配置失败'}, 500)


@admin_bp.route('/api/admin/storage/backends', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def add_storage_backend():
    """添加新的存储后端"""
    if request.method == 'OPTIONS':
        return _admin_options('POST, OPTIONS')

    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        backend_config = data.get('config') or {}

        if not name:
            return _admin_json({'success': False, 'error': '后端名称不能为空'}, 400)

        if not _BACKEND_NAME_PATTERN.match(name):
            return _admin_json({'success': False, 'error': '后端名称只能包含字母、数字、下划线和连字符，长度1-32字符'}, 400)

        driver = (backend_config.get('driver') or '').strip()
        if not driver:
            return _admin_json({'success': False, 'error': '必须指定驱动类型'}, 400)

        if driver not in _ALLOWED_DRIVERS:
            return _admin_json({'success': False, 'error': f"不支持的驱动类型: {driver}，允许: {', '.join(_ALLOWED_DRIVERS)}"}, 400)

        config = _load_storage_config()
        backends = config.get('backends') or {}

        if name in backends:
            return _admin_json({'success': False, 'error': f"后端 '{name}' 已存在"}, 400)

        backends[name] = backend_config
        config['backends'] = backends
        _save_storage_config(config)

        # 同步 Bot Token：将存储 Token 复制到机器人配置
        use_as_bot = data.get('use_as_bot', False)
        if use_as_bot and backend_config.get('driver') == 'telegram':
            real_token = (backend_config.get('bot_token') or '').strip()
            if real_token:
                update_system_setting('telegram_bot_token', real_token)
                from ..bot_control import clear_token_cache, request_bot_restart
                clear_token_cache()
                request_bot_restart()
                logger.info("存储 Bot Token 已同步到机器人配置，已触发重启")
        elif not use_as_bot and backend_config.get('driver') == 'telegram':
            # 未勾选"用作机器人"：若当前 Bot Token 来自该存储则清除
            real_token = (backend_config.get('bot_token') or '').strip()
            current_bot_token = str(get_system_setting('telegram_bot_token') or '').strip()
            if real_token and current_bot_token == real_token:
                update_system_setting('telegram_bot_token', '')
                from ..bot_control import clear_token_cache, request_bot_restart
                clear_token_cache()
                request_bot_restart()
                logger.info("存储未勾选用作机器人，已清除 Bot Token 并触发重启")

        logger.info(f"添加存储后端: {name}")
        return _admin_json({
            'success': True,
            'message': f"后端 '{name}' 添加成功",
            'data': {'name': name, 'config': _mask_sensitive(backend_config)}
        })

    except Exception as e:
        logger.error(f"添加存储后端失败: {e}")
        return _admin_json({'success': False, 'error': '添加存储后端失败'}, 500)


@admin_bp.route('/api/admin/storage/backends/<name>', methods=['PUT', 'DELETE', 'OPTIONS'])
@admin_module.login_required
def modify_storage_backend(name: str):
    """编辑或删除存储后端"""
    if request.method == 'OPTIONS':
        return _admin_options('PUT, DELETE, OPTIONS')

    try:
        config = _load_storage_config()
        backends = config.get('backends') or {}

        if name not in backends:
            return _admin_json({'success': False, 'error': f"后端 '{name}' 不存在"}, 404)

        if request.method == 'DELETE':
            router = get_storage_router()
            active = router.get_active_backend_name()
            if name == active:
                return _admin_json({'success': False, 'error': '无法删除当前激活的后端'}, 400)

            del backends[name]
            config['backends'] = backends
            _save_storage_config(config)

            logger.info(f"删除存储后端: {name}")
            return _admin_json({'success': True, 'message': f"后端 '{name}' 已删除"})

        # PUT 请求：更新后端配置
        data = request.get_json(silent=True) or {}
        new_config = data.get('config') or {}

        driver = (new_config.get('driver') or '').strip()
        if not driver:
            return _admin_json({'success': False, 'error': '必须指定驱动类型'}, 400)

        if driver not in _ALLOWED_DRIVERS:
            return _admin_json({'success': False, 'error': f"不支持的驱动类型: {driver}，允许: {', '.join(_ALLOWED_DRIVERS)}"}, 400)

        old_config = backends[name]
        merged_config = _merge_sensitive(new_config, old_config)

        backends[name] = merged_config
        config['backends'] = backends
        _save_storage_config(config)

        # 同步 Bot Token：将存储 Token 复制到机器人配置
        use_as_bot = data.get('use_as_bot', False)
        if use_as_bot and merged_config.get('driver') == 'telegram':
            real_token = (merged_config.get('bot_token') or '').strip()
            if real_token:
                update_system_setting('telegram_bot_token', real_token)
                from ..bot_control import clear_token_cache, request_bot_restart
                clear_token_cache()
                request_bot_restart()
                logger.info("存储 Bot Token 已同步到机器人配置，已触发重启")
        elif not use_as_bot and merged_config.get('driver') == 'telegram':
            # 未勾选"用作机器人"：若当前 Bot Token 来自该存储则清除
            real_token = (merged_config.get('bot_token') or '').strip()
            current_bot_token = str(get_system_setting('telegram_bot_token') or '').strip()
            if real_token and current_bot_token == real_token:
                update_system_setting('telegram_bot_token', '')
                from ..bot_control import clear_token_cache, request_bot_restart
                clear_token_cache()
                request_bot_restart()
                logger.info("存储未勾选用作机器人，已清除 Bot Token 并触发重启")

        logger.info(f"更新存储后端: {name}")
        return _admin_json({
            'success': True,
            'message': f"后端 '{name}' 更新成功",
            'data': {'name': name, 'config': _mask_sensitive(merged_config)}
        })

    except Exception as e:
        logger.error(f"修改存储后端失败: {e}")
        return _admin_json({'success': False, 'error': '修改存储后端失败'}, 500)