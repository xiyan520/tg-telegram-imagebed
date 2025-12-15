#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3 兼容对象存储后端

支持 AWS S3、Cloudflare R2、MinIO、阿里云 OSS 等 S3 兼容存储。
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Iterable, Optional

from ..base import StorageBackend, PutResult, DownloadResult
from ...config import logger

# 尝试导入 boto3
try:
    import boto3
    from botocore.config import Config as BotoConfig
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None
    BotoConfig = None


class S3Backend(StorageBackend):
    """S3 兼容对象存储后端"""

    def __init__(
        self,
        *,
        name: str,
        endpoint: str = "",
        bucket: str,
        access_key: str = "",
        secret_key: str = "",
        region: str = "auto",
        public_url_prefix: str = "",
        path_style: bool = False,
        **kwargs: Any,
    ):
        """
        初始化 S3 存储后端

        Args:
            name: 后端名称
            endpoint: S3 端点 URL（如 https://s3.amazonaws.com）
            bucket: 存储桶名称
            access_key: 访问密钥
            secret_key: 密钥
            region: 区域
            public_url_prefix: 公开访问 URL 前缀（用于重定向）
            path_style: 是否使用路径风格（而非虚拟主机风格）
        """
        self.name = name
        self._endpoint = (endpoint or "").strip()
        self._bucket = (bucket or "").strip()
        self._access_key = (access_key or "").strip()
        self._secret_key = (secret_key or "").strip()
        self._region = (region or "auto").strip()
        self._public_url_prefix = (public_url_prefix or "").strip().rstrip("/")
        self._path_style = path_style
        self._client = None

        if not self._bucket:
            raise ValueError("S3 backend requires 'bucket'")

        if not HAS_BOTO3:
            logger.warning("boto3 未安装，S3 存储后端将不可用。请运行: pip install boto3")
        else:
            self._init_client()

        logger.info(f"S3 存储后端初始化: {self._endpoint or 'AWS'}/{self._bucket}")

    def _init_client(self):
        """初始化 S3 客户端"""
        if not HAS_BOTO3:
            return

        try:
            config = BotoConfig(
                s3={'addressing_style': 'path' if self._path_style else 'auto'},
                signature_version='s3v4',
            )

            client_kwargs = {
                'service_name': 's3',
                'config': config,
            }

            if self._endpoint:
                client_kwargs['endpoint_url'] = self._endpoint
            if self._access_key and self._secret_key:
                client_kwargs['aws_access_key_id'] = self._access_key
                client_kwargs['aws_secret_access_key'] = self._secret_key
            if self._region and self._region != 'auto':
                client_kwargs['region_name'] = self._region

            self._client = boto3.client(**client_kwargs)
        except Exception as e:
            logger.error(f"S3 客户端初始化失败: {e}")
            self._client = None

    def _generate_key(self, filename: str) -> str:
        """生成存储 key"""
        ext = os.path.splitext(filename or "")[1]
        t = time.gmtime()
        date_prefix = f"{t.tm_year:04d}/{t.tm_mon:02d}/{t.tm_mday:02d}"
        uid = uuid.uuid4().hex
        return f"{date_prefix}/{uid}{ext}"

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
        """上传文件到 S3"""
        if not HAS_BOTO3 or not self._client:
            logger.error("S3 客户端不可用")
            return None

        try:
            key = self._generate_key(filename)

            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

            logger.info(f"S3 存储上传成功: {key}")

            return PutResult(
                file_id=key,
                file_path=key,
                file_size=file_size,
                storage_backend=self.name,
                storage_key=key,
                storage_meta={
                    "driver": "s3",
                    "bucket": self._bucket,
                    "endpoint": self._endpoint,
                    "content_type": content_type,
                },
            )
        except Exception as e:
            logger.error(f"S3 存储上传失败: {e}")
            return None

    def download(
        self,
        *,
        file_info: Dict[str, Any],
        range_header: Optional[str],
    ) -> DownloadResult:
        """从 S3 下载文件"""
        if not HAS_BOTO3 or not self._client:
            return DownloadResult(
                status_code=503,
                content_type="text/plain",
                headers={},
                body=[b"S3 backend unavailable"]
            )

        key = (
            file_info.get("storage_key") or
            file_info.get("file_path") or
            file_info.get("file_id") or ""
        ).strip()

        if not key:
            return DownloadResult(
                status_code=404,
                content_type="text/plain",
                headers={},
                body=[b"not found"]
            )

        try:
            get_kwargs: Dict[str, Any] = {
                'Bucket': self._bucket,
                'Key': key,
            }

            if range_header:
                get_kwargs['Range'] = range_header

            response = self._client.get_object(**get_kwargs)

            content_type = file_info.get("mime_type") or response.get('ContentType', 'application/octet-stream')
            content_length = response.get('ContentLength', 0)

            def body() -> Iterable[bytes]:
                try:
                    stream = response['Body']
                    while True:
                        chunk = stream.read(8192)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    try:
                        response['Body'].close()
                    except Exception:
                        pass

            headers: Dict[str, str] = {
                'Accept-Ranges': 'bytes',
            }
            if content_length:
                headers['Content-Length'] = str(content_length)
            if 'ContentRange' in response:
                headers['Content-Range'] = response['ContentRange']

            status_code = 206 if range_header and 'ContentRange' in response else 200

            return DownloadResult(
                status_code=status_code,
                content_type=content_type,
                headers=headers,
                body=body(),
            )
        except self._client.exceptions.NoSuchKey:
            return DownloadResult(
                status_code=404,
                content_type="text/plain",
                headers={},
                body=[b"not found"]
            )
        except Exception as e:
            logger.error(f"S3 下载失败: {e}")
            return DownloadResult(
                status_code=502,
                content_type="text/plain",
                headers={},
                body=[b"upstream error"]
            )

    def delete(self, *, storage_key: str) -> bool:
        """删除文件"""
        if not HAS_BOTO3 or not self._client:
            return False

        try:
            self._client.delete_object(Bucket=self._bucket, Key=storage_key)
            logger.info(f"S3 存储删除成功: {storage_key}")
            return True
        except Exception as e:
            logger.error(f"S3 删除失败: {e}")
            return False

    def get_public_url(self, *, storage_key: str, file_info: Dict[str, Any]) -> Optional[str]:
        """获取公开访问 URL"""
        if self._public_url_prefix:
            return f"{self._public_url_prefix}/{storage_key}"
        return None

    def healthcheck(self) -> bool:
        """检查 S3 是否可用"""
        if not HAS_BOTO3 or not self._client:
            return False

        try:
            self._client.head_bucket(Bucket=self._bucket)
            return True
        except Exception:
            return False
