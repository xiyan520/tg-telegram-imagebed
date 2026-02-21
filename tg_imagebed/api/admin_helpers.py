#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由共享辅助函数
"""
from flask import request, jsonify, Response

from ..utils import add_cache_headers
from ..database import get_system_setting


def _get_cdn_domain() -> str:
    """从数据库获取 CDN 域名"""
    return str(get_system_setting('cloudflare_cdn_domain') or '').strip()


def _admin_json(data, status=200, cache='no-cache'):
    """创建带 CORS 头的管理员 JSON 响应"""
    resp = jsonify(data)
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(resp, cache), status


def _admin_options(methods: str):
    """处理管理员 OPTIONS 预检请求"""
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = methods
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return add_cache_headers(response, 'no-cache')
