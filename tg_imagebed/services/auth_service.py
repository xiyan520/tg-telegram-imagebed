#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务模块 - Token 认证管理

提供 Token 的创建、验证、查询功能的高级封装。
"""
from typing import Optional, Dict, Any, List

from ..config import logger
from ..database import (
    create_auth_token,
    verify_auth_token,
    get_token_info,
    update_token_usage,
    get_token_uploads as db_get_token_uploads,
)


def create_token(
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None,
    upload_limit: int = 999999,
    expires_days: int = 36500
) -> Optional[str]:
    """
    创建新的认证 Token

    Args:
        ip_address: 客户端 IP 地址
        user_agent: 客户端 User-Agent
        description: Token 描述
        upload_limit: 上传限制（默认无限制）
        expires_days: 有效期天数（默认100年）

    Returns:
        生成的 Token 字符串，失败返回 None
    """
    return create_auth_token(
        ip_address=ip_address,
        user_agent=user_agent,
        description=description or '游客Token',
        upload_limit=upload_limit,
        expires_days=expires_days
    )


def verify_token(token: str) -> Dict[str, Any]:
    """
    验证 Token 是否有效

    Args:
        token: Token 字符串

    Returns:
        验证结果字典，包含 valid、reason、token_data 等字段
    """
    return verify_auth_token(token)


def get_token_details(token: str) -> Optional[Dict[str, Any]]:
    """
    获取 Token 详细信息

    Args:
        token: Token 字符串

    Returns:
        Token 信息字典，不存在返回 None
    """
    return get_token_info(token)


def record_token_usage(token: str) -> None:
    """
    记录 Token 使用

    Args:
        token: Token 字符串
    """
    update_token_usage(token)


def get_token_upload_history(token: str, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    """
    获取 Token 的上传历史

    Args:
        token: Token 字符串
        limit: 每页数量
        page: 页码

    Returns:
        上传记录列表
    """
    return db_get_token_uploads(token, limit, page)


__all__ = [
    'create_token',
    'verify_token',
    'get_token_details',
    'record_token_usage',
    'get_token_upload_history',
]
