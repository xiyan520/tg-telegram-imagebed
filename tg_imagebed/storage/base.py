#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储后端抽象基类

定义统一的存储接口，所有存储后端都需要实现这些接口。
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class PutResult:
    """上传结果"""
    file_id: str                    # 文件标识符
    file_path: str                  # 文件路径
    file_size: int                  # 文件大小
    storage_backend: str            # 存储后端名称
    storage_key: str                # 存储后端内部 key
    storage_meta: Dict[str, Any] = field(default_factory=dict)  # 存储元数据


@dataclass(frozen=True)
class DownloadResult:
    """下载结果"""
    status_code: int                # HTTP 状态码 (200, 206, 404, etc.)
    content_type: str               # MIME 类型
    headers: Dict[str, str]         # 响应头
    body: Iterable[bytes]           # 响应体（流式）
    updated_fields: Optional[Dict[str, Any]] = None  # 需要更新的字段（如 file_path）


class StorageBackend(abc.ABC):
    """存储后端抽象基类"""

    name: str  # 后端名称

    @abc.abstractmethod
    def put_bytes(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_size: int,
        caption: str,
        source: str,
        username: str,
    ) -> Optional[PutResult]:
        """
        上传文件

        Args:
            file_content: 文件内容
            filename: 原始文件名
            content_type: MIME 类型
            file_size: 文件大小
            caption: 描述/标题
            source: 来源
            username: 用户名

        Returns:
            PutResult 或 None（失败时）
        """
        raise NotImplementedError

    @abc.abstractmethod
    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """
        下载文件

        Args:
            file_info: 文件信息（从数据库读取）
            range_header: HTTP Range 头（用于断点续传）

        Returns:
            DownloadResult
        """
        raise NotImplementedError

    def delete(self, *, storage_key: str) -> bool:
        """
        删除文件（可选实现）

        Args:
            storage_key: 存储 key

        Returns:
            是否成功
        """
        return False

    def healthcheck(self) -> bool:
        """
        健康检查（可选实现）

        Returns:
            后端是否可用
        """
        return True

    def get_public_url(self, *, storage_key: str, file_info: Dict[str, Any]) -> Optional[str]:
        """
        获取公开访问 URL（可选实现，用于重定向）

        Args:
            storage_key: 存储 key
            file_info: 文件信息

        Returns:
            公开 URL 或 None
        """
        return None
