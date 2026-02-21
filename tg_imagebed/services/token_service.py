#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 统一调度层 — 级联删除 / 影响范围查询 / 批量操作
"""
from typing import Any, Dict, List, Optional

from ..config import logger
from ..database import (
    admin_create_token,
    admin_delete_token,
)
from ..database.connection import get_connection


class TokenService:
    """Token 管理统一入口，封装级联清理与批量操作逻辑。"""

    # ── 创建 ──────────────────────────────────────────────
    @staticmethod
    def create_token(
        *,
        description: Optional[str] = None,
        expires_at: Any = None,
        upload_limit: int = 100,
        is_active: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """统一创建 Token，委托给 database 层。"""
        return admin_create_token(
            description=description,
            expires_at=expires_at,
            upload_limit=upload_limit,
            is_active=is_active,
        )

    # ── 级联删除 ──────────────────────────────────────────
    @staticmethod
    def delete_token(token_id: int) -> bool:
        """
        级联删除 Token：
        1. file_storage.auth_token 置空
        2. galleries.owner_token 置空（owner_type='token' 的画集）
        3. gallery_token_access 清理
        4. 删除 auth_tokens 记录
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                # 先查出 token 字符串
                cursor.execute(
                    "SELECT token FROM auth_tokens WHERE rowid = ?",
                    (int(token_id),),
                )
                row = cursor.fetchone()
                if not row:
                    return False

                token_str = row[0]

                # 1) file_storage.auth_token 置空
                cursor.execute(
                    "UPDATE file_storage SET auth_token = NULL WHERE auth_token = ?",
                    (token_str,),
                )
                # 2) galleries.owner_token 置空
                cursor.execute(
                    "UPDATE galleries SET owner_token = NULL WHERE owner_token = ?",
                    (token_str,),
                )
                # 3) gallery_token_access 清理
                cursor.execute(
                    "DELETE FROM gallery_token_access WHERE token = ?",
                    (token_str,),
                )
                # 4) 删除 auth_tokens
                cursor.execute(
                    "DELETE FROM auth_tokens WHERE rowid = ?",
                    (int(token_id),),
                )

            logger.info(f"TokenService 级联删除 Token: ID={token_id}")
            return True

        except Exception as e:
            logger.error(f"TokenService 级联删除 Token 失败: {e}")
            raise

    # ── 影响范围查询 ──────────────────────────────────────
    @staticmethod
    def get_token_impact(token_id: int) -> Optional[Dict[str, Any]]:
        """查询删除该 Token 的影响范围。返回 None 表示 Token 不存在。"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT token FROM auth_tokens WHERE rowid = ?",
                    (int(token_id),),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                token_str = row[0]

                cursor.execute(
                    "SELECT COUNT(1) FROM file_storage WHERE auth_token = ?",
                    (token_str,),
                )
                upload_count = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(1) FROM galleries WHERE owner_token = ?",
                    (token_str,),
                )
                gallery_count = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(1) FROM gallery_token_access WHERE token = ?",
                    (token_str,),
                )
                access_count = cursor.fetchone()[0] or 0

            return {
                "upload_count": upload_count,
                "gallery_count": gallery_count,
                "access_count": access_count,
            }

        except Exception as e:
            logger.error(f"TokenService 查询影响范围失败: {e}")
            raise

    # ── 批量操作 ──────────────────────────────────────────
    @staticmethod
    def batch_update_status(token_ids: List[int], is_active: bool) -> Dict[str, int]:
        """批量启用/禁用，返回 {success_count, fail_count}。"""
        success = 0
        fail = 0
        active_val = 1 if is_active else 0
        for tid in token_ids:
            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE auth_tokens SET is_active = ? WHERE rowid = ?",
                        (active_val, int(tid)),
                    )
                    if cursor.rowcount > 0:
                        success += 1
                    else:
                        fail += 1
            except Exception:
                fail += 1
        status_text = "启用" if is_active else "禁用"
        logger.info(f"TokenService 批量{status_text}: 成功={success}, 失败={fail}")
        return {"success_count": success, "fail_count": fail}

    @staticmethod
    def batch_delete(token_ids: List[int]) -> Dict[str, int]:
        """批量级联删除，返回 {success_count, fail_count}。"""
        success = 0
        fail = 0
        for tid in token_ids:
            try:
                if TokenService.delete_token(tid):
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
        logger.info(f"TokenService 批量删除: 成功={success}, 失败={fail}")
        return {"success_count": success, "fail_count": fail}

    @staticmethod
    def batch_get_impact(token_ids: List[int]) -> Dict[str, Any]:
        """批量影响范围汇总。"""
        total_uploads = 0
        total_galleries = 0
        total_access = 0
        for tid in token_ids:
            impact = TokenService.get_token_impact(tid)
            if impact:
                total_uploads += impact["upload_count"]
                total_galleries += impact["gallery_count"]
                total_access += impact["access_count"]
        return {
            "token_count": len(token_ids),
            "upload_count": total_uploads,
            "gallery_count": total_galleries,
            "access_count": total_access,
        }
