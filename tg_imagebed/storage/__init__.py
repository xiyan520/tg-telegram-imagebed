#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储抽象层模块

提供统一的存储接口，支持多种存储后端：
- telegram: Telegram Cloud 存储（默认）
- local: 本地文件系统存储
- rclone: rclone 支持的各种网盘
- s3: S3 兼容对象存储
"""

from .router import get_storage_router

__all__ = ["get_storage_router"]
