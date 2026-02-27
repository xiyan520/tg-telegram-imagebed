#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tg_imagebed - Telegram 图床应用包

模块化架构：
- config: 配置管理
- utils: 工具函数
- database: 数据访问层
- services/: 服务层
- api/: 路由层
"""
from pathlib import Path


def _load_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / 'VERSION'
    try:
        value = version_file.read_text(encoding='utf-8').strip()
        if value:
            return value
    except Exception:
        pass
    return '0.0.0'


__version__ = _load_version()
