#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由共享辅助函数
"""
from urllib.parse import urlparse

from flask import request, jsonify, Response

from ..utils import add_cache_headers
from ..database import get_system_setting, get_active_image_domains, get_active_gallery_domains
from ..config import ALLOWED_ORIGINS


def _get_cdn_domain() -> str:
    """从数据库获取 CDN 域名"""
    return str(get_system_setting('cloudflare_cdn_domain') or '').strip()


def _get_allowed_origin() -> str:
    """获取安全的 Access-Control-Allow-Origin 值（仅返回经过验证的 Origin）"""
    origin = (request.headers.get('Origin') or '').strip()
    if not origin:
        # 无 Origin 头的请求不需要 CORS 头（如同源请求）
        return ''

    def _origin_matches(origin_str: str, allowed: str) -> bool:
        """精确比较两个 origin（scheme + host + port）"""
        if origin_str == allowed:
            return True
        try:
            parsed_origin = urlparse(origin_str)
            parsed_allowed = urlparse(allowed)
            return (parsed_origin.scheme == parsed_allowed.scheme
                    and parsed_origin.hostname == parsed_allowed.hostname
                    and parsed_origin.port == parsed_allowed.port)
        except Exception:
            return False

    def _host_matches(origin_str: str, domain: str) -> bool:
        """检查 origin 的主机名是否匹配指定域名（精确匹配或子域名）"""
        try:
            hostname = urlparse(origin_str).hostname or ''
        except Exception:
            return False
        if hostname == domain:
            return True
        if hostname.endswith('.' + domain):
            return True
        return False

    # 1. 检查 ALLOWED_ORIGINS 环境变量配置（精确匹配完整 origin）
    if ALLOWED_ORIGINS and ALLOWED_ORIGINS != '*':
        allowed_list = [a.strip() for a in ALLOWED_ORIGINS.split(',') if a.strip()]
        for allow in allowed_list:
            if _origin_matches(origin, allow):
                return origin

    # 2. 检查数据库配置的域名（匹配主机名）
    try:
        image_domains = get_active_image_domains()
        gallery_domains = get_active_gallery_domains()
        all_domains = set()
        for d in image_domains:
            domain = (d.get('domain') or '').strip()
            if domain:
                all_domains.add(domain)
        for d in gallery_domains:
            domain = (d.get('domain') or '').strip()
            if domain:
                all_domains.add(domain)
        for domain in all_domains:
            try:
                parsed = urlparse(origin)
                domain_origin = f"{parsed.scheme}://{domain}"
                if parsed.port:
                    domain_origin += f":{parsed.port}"
                if _origin_matches(origin, domain_origin):
                    return origin
            except Exception:
                continue
    except Exception:
        pass

    # 3. 回退：允许本地开发域名
    if origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
        return origin

    # 4. 都不匹配时返回空字符串（浏览器将拒绝非法的 CORS 响应）
    return ''


def _admin_json(data, status=200, cache='no-cache'):
    """创建带 CORS 头的管理员 JSON 响应"""
    resp = jsonify(data)
    allowed = _get_allowed_origin()
    if allowed:
        resp.headers['Access-Control-Allow-Origin'] = allowed
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(resp, cache), status


def _admin_options(methods: str):
    """处理管理员 OPTIONS 预检请求"""
    response = Response()
    allowed = _get_allowed_origin()
    if allowed:
        response.headers['Access-Control-Allow-Origin'] = allowed
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = methods
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return add_cache_headers(response, 'no-cache')
