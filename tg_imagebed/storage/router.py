#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储路由器

负责加载配置、实例化后端、路由读写请求。
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from .base import PutResult, StorageBackend
from .backends.telegram import TelegramBackend
from .backends.local import LocalBackend
from .backends.rclone import RcloneBackend
from .backends.s3 import S3Backend

from ..config import PROXY_URL, logger
from ..bot_control import get_effective_bot_token


def _resolve_env_ref(value: Any) -> Any:
    """解析环境变量引用（如 'env:BOT_TOKEN'）"""
    if isinstance(value, str) and value.startswith("env:"):
        return os.getenv(value[4:], "")
    return value


def _resolve_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """递归解析配置中的环境变量引用"""
    result = {}
    for k, v in (cfg or {}).items():
        if isinstance(v, dict):
            result[k] = _resolve_config(v)
        elif isinstance(v, list):
            result[k] = [_resolve_env_ref(item) if isinstance(item, str) else item for item in v]
        else:
            result[k] = _resolve_env_ref(v)
    return result


class StorageRouter:
    """存储路由器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化存储路由器

        Args:
            config: 存储配置
        """
        self._config = config
        self._cache: Dict[str, StorageBackend] = {}

    def get_active_backend_name(self) -> str:
        """获取当前激活的后端名称"""
        # 优先级：环境变量 > 数据库设置 > 配置文件 > 默认值
        from ..database import get_system_setting
        return (
            os.getenv("STORAGE_BACKEND") or
            get_system_setting("storage_active_backend") or
            self._config.get("active") or
            "telegram"
        ).strip()

    def _build_backend(self, name: str, cfg: Dict[str, Any]) -> StorageBackend:
        """构建存储后端实例"""
        cfg2 = _resolve_config(cfg)
        driver = (cfg2.get("driver") or name).strip()

        if driver == "telegram":
            effective_token, _ = get_effective_bot_token()
            bot_token = str(cfg2.get("bot_token") or effective_token or "")
            chat_id = int(cfg2.get("chat_id") or 0)
            proxy_url = str(cfg2.get("proxy_url") or PROXY_URL or "").strip() or None
            return TelegramBackend(name=name, bot_token=bot_token, chat_id=chat_id, proxy_url=proxy_url)

        if driver == "local":
            root_dir = str(cfg2.get("root_dir") or os.path.join(os.getcwd(), "data", "uploads"))
            return LocalBackend(name=name, root_dir=root_dir)

        if driver == "rclone":
            return RcloneBackend(
                name=name,
                rclone_bin=str(cfg2.get("rclone_bin") or "rclone"),
                config_path=str(cfg2.get("config_path") or ""),
                remote=str(cfg2.get("remote") or ""),
                base_path=str(cfg2.get("base_path") or ""),
                cli_flags=list(cfg2.get("cli_flags") or []),
                upload=dict(cfg2.get("upload") or {}),
                download=dict(cfg2.get("download") or {}),
            )

        if driver == "s3":
            return S3Backend(
                name=name,
                endpoint=str(cfg2.get("endpoint") or ""),
                bucket=str(cfg2.get("bucket") or ""),
                access_key=str(cfg2.get("access_key") or ""),
                secret_key=str(cfg2.get("secret_key") or ""),
                region=str(cfg2.get("region") or "auto"),
                public_url_prefix=str(cfg2.get("public_url_prefix") or ""),
                path_style=bool(cfg2.get("path_style", False)),
            )

        raise ValueError(f"未知的存储驱动: {driver}")

    def get_backend(self, name: str) -> StorageBackend:
        """获取指定名称的后端实例"""
        if name in self._cache:
            return self._cache[name]

        backends_cfg = self._config.get("backends") or {}
        cfg = backends_cfg.get(name)

        if not cfg:
            # 回退到 telegram
            logger.warning(f"存储后端 '{name}' 未配置，回退到 telegram")
            cfg = backends_cfg.get("telegram") or {"driver": "telegram"}
            name = "telegram"

        backend = self._build_backend(name, cfg)
        self._cache[name] = backend
        return backend

    def get_backend_for_record(self, file_info: Dict[str, Any]) -> StorageBackend:
        """根据文件记录获取对应的后端"""
        name = (file_info.get("storage_backend") or "telegram").strip() or "telegram"
        return self.get_backend(name)

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
        """上传文件到当前激活的后端"""
        backend = self.get_backend(self.get_active_backend_name())
        return backend.put_bytes(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            caption=caption,
            source=source,
            username=username,
        )

    def list_backends(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置的后端"""
        backends_cfg = self._config.get("backends") or {}
        result = {}
        for name, cfg in backends_cfg.items():
            driver = (cfg.get("driver") or name).strip()
            result[name] = {
                "driver": driver,
                "active": name == self.get_active_backend_name(),
            }
        return result

    def get_upload_policy(self) -> Dict[str, Any]:
        """读取上传场景路由策略（storage_upload_policy_json）"""
        try:
            from ..database import get_system_setting
            raw = (get_system_setting("storage_upload_policy_json") or "").strip()
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return {}

    def get_effective_upload_policy(self) -> Dict[str, Any]:
        """返回补全默认值后的策略（保证字段齐全）"""
        p = self.get_upload_policy() or {}
        admin_allowed = p.get("admin_allowed")
        if not isinstance(admin_allowed, list):
            admin_allowed = []
        return {
            "guest": str(p.get("guest") or ""),
            "token": str(p.get("token") or ""),
            "group": str(p.get("group") or ""),
            "admin_default": str(p.get("admin_default") or ""),
            "admin_allowed": [str(x) for x in admin_allowed if str(x).strip()],
        }

    def resolve_upload_backend(
        self,
        *,
        scene: str,
        requested_backend: Optional[str] = None,
        is_admin: bool = False,
    ) -> str:
        """
        根据上传场景选择后端

        Args:
            scene: 上传场景 (guest/token/group/admin)
            requested_backend: 管理员请求的特定后端
            is_admin: 是否为管理员上传

        Returns:
            后端名称
        """
        scene = (scene or "").strip().lower()
        active = self.get_active_backend_name()
        backends = self.list_backends()
        policy = self.get_effective_upload_policy()

        def normalize(name: str) -> str:
            name = (name or "").strip()
            return name or active

        def exists(name: str) -> bool:
            return name in backends

        if is_admin or scene == "admin":
            allowed: List[str] = policy.get("admin_allowed") or []
            if not allowed:
                allowed = list(backends.keys())
            if requested_backend:
                req = requested_backend.strip()
                if req not in allowed:
                    raise ValueError(f"后端 '{req}' 不在管理员允许列表中")
                if not exists(req):
                    raise ValueError(f"后端 '{req}' 未配置")
                return req
            target = normalize(policy.get("admin_default", ""))
            return target if exists(target) else active

        if scene == "token":
            target = normalize(policy.get("token", ""))
            return target if exists(target) else active

        if scene == "guest":
            target = normalize(policy.get("guest", ""))
            return target if exists(target) else active

        if scene == "group":
            target = normalize(policy.get("group", ""))
            return target if exists(target) else active

        return active


# 全局路由器缓存
_router: Optional[StorageRouter] = None
_router_ts: float = 0.0


def _load_storage_config() -> Dict[str, Any]:
    """加载存储配置"""
    # 优先从环境变量读取
    env_json = (os.getenv("STORAGE_CONFIG_JSON") or "").strip()
    if env_json:
        try:
            return json.loads(env_json)
        except Exception as e:
            logger.error(f"解析 STORAGE_CONFIG_JSON 失败: {e}")

    # 从数据库读取
    try:
        from ..database import get_system_setting
        db_json = (get_system_setting("storage_config_json") or "").strip()
        if db_json:
            return json.loads(db_json)
    except Exception as e:
        logger.debug(f"从数据库读取存储配置失败: {e}")

    # 返回默认配置
    return {
        "active": "telegram",
        "backends": {
            "telegram": {
                "driver": "telegram",
                "bot_token": "env:BOT_TOKEN",
                "chat_id": "0",
            },
            "local": {
                "driver": "local",
                "root_dir": os.path.join(os.getcwd(), "data", "uploads"),
            },
        },
    }


def get_storage_router(*, ttl_seconds: int = 5) -> StorageRouter:
    """
    获取存储路由器实例（带缓存）

    Args:
        ttl_seconds: 缓存有效期（秒）

    Returns:
        StorageRouter 实例
    """
    global _router, _router_ts
    now = time.time()
    if _router and (now - _router_ts) < ttl_seconds:
        return _router
    cfg = _load_storage_config()
    _router = StorageRouter(cfg)
    _router_ts = now
    return _router


def reload_storage_router() -> StorageRouter:
    """强制重新加载存储路由器"""
    global _router, _router_ts
    cfg = _load_storage_config()
    _router = StorageRouter(cfg)
    _router_ts = time.time()
    return _router
