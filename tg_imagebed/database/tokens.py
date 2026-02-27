#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Token 管理（用户 + 管理员）"""
import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..config import logger
from .connection import get_connection


# ===================== 内部辅助 =====================
def _mask_token(token: str, prefix_len: int = 8, suffix_len: int = 4) -> str:
    """对 Token 进行脱敏处理，只显示前后各几位字符"""
    token = str(token or '')
    if len(token) <= prefix_len + suffix_len:
        return token
    return f"{token[:prefix_len]}...{token[-suffix_len:]}"


def _parse_datetime(value: Any) -> Optional[str]:
    """
    解析 ISO8601 格式的日期时间字符串，转换为 SQLite 兼容的格式。
    支持带时区和不带时区的格式。
    """
    if value is None:
        return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            # 处理 ISO8601 格式，包括 'Z' 时区标记
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"无效的日期时间格式: {raw}") from e

        # 如果有时区信息，转换为本地时间
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    raise ValueError(f"不支持的日期时间类型: {type(value)}")


def _token_row_to_dict(row: sqlite3.Row, *, include_full_token: bool = False) -> Dict[str, Any]:
    """
    将数据库行转换为字典，并进行数据格式化。

    Args:
        row: 数据库查询结果行
        include_full_token: 是否包含完整 token（仅在创建时返回）
    """
    if not row:
        return {}

    data = dict(row)
    token_value = data.get('token', '')

    # 添加脱敏后的 token
    data['token_masked'] = _mask_token(token_value)

    # 根据参数决定是否保留完整 token
    if not include_full_token:
        data.pop('token', None)

    # 布尔字段转换
    if 'is_active' in data:
        data['is_active'] = bool(data['is_active'])
    if 'is_expired' in data:
        data['is_expired'] = bool(data['is_expired'])

    return data


# 过期判断 SQL 表达式（避免重复）
_EXPIRED_EXPR = "(expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP)"


# ===================== 用户侧 Token =====================
def generate_auth_token() -> str:
    """生成唯一的 auth_token"""
    token = secrets.token_hex(32)
    return f"guest_{token}"


def create_auth_token(
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None,
    upload_limit: int = 100,
    expires_days: int = 30
) -> Optional[str]:
    """创建新的 auth_token"""
    try:
        token = generate_auth_token()
        expires_at = datetime.now() + timedelta(days=expires_days)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auth_tokens
                (token, expires_at, upload_limit, ip_address, user_agent, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (token, expires_at, upload_limit, ip_address, user_agent, description or '游客Token'))

        logger.info(f"创建新的auth_token: {token[:20]}... (限制: {upload_limit}张, 有效期: {expires_days}天)")
        return token

    except Exception as e:
        logger.error(f"创建auth_token失败: {e}")
        return None


def _verify_token_core(token: str, *, check_quota: bool = True) -> Dict[str, Any]:
    """
    Token 验证核心逻辑。

    Args:
        token: Token 字符串
        check_quota: True=配额用完返回 invalid（上传场景）；
                     False=配额用完仍 valid，返回 can_upload=False（访问场景）
    """
    if not token:
        return {'valid': False, 'reason': 'Token为空'}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,))
            row = cursor.fetchone()

            if not row:
                return {'valid': False, 'reason': 'Token不存在'}

            token_data = dict(row)

            # 检查是否激活
            if not token_data.get('is_active', 1):
                return {'valid': False, 'reason': 'Token已被禁用'}

            # 检查是否过期（统一时区处理）
            if token_data.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(
                        str(token_data['expires_at']).replace('Z', '+00:00')
                    )
                    # 统一转为本地时间再比较
                    if expires_at.tzinfo is not None:
                        expires_at = expires_at.astimezone().replace(tzinfo=None)
                    if datetime.now() > expires_at:
                        return {'valid': False, 'reason': 'Token已过期'}
                except (ValueError, TypeError):
                    return {'valid': False, 'reason': 'Token过期时间异常'}

            # 计算剩余上传次数
            upload_count = int(token_data.get('upload_count') or 0)
            upload_limit = int(token_data.get('upload_limit') or 999999)
            remaining_uploads = upload_limit - upload_count

            # 配额检查
            if check_quota and remaining_uploads <= 0:
                return {'valid': False, 'reason': f'已达到上传限制({upload_limit}张)'}

            result = {
                'valid': True,
                'token_data': token_data,
                'remaining_uploads': max(0, remaining_uploads),
            }
            if not check_quota:
                result['can_upload'] = remaining_uploads > 0
            return result

    except Exception as e:
        label = "验证auth_token失败" if check_quota else "验证auth_token(access)失败"
        logger.error(f"{label}: {e}")
        return {'valid': False, 'reason': '验证失败'}


def verify_auth_token(token: str) -> Dict[str, Any]:
    """验证 auth_token 是否有效（上传场景：配额用完返回 invalid）"""
    return _verify_token_core(token, check_quota=True)


def verify_auth_token_access(token: str) -> Dict[str, Any]:
    """验证 auth_token 是否有效（访问场景：配额用完仍 valid，返回 can_upload=False）"""
    return _verify_token_core(token, check_quota=False)

def update_token_description(token: str, description: Optional[str]) -> bool:
    """更新 Token 描述（前端可用作相册名称）"""
    try:
        token = (token or '').strip()
        if not token:
            return False
        desc_value = (str(description or '').strip()[:200]) or None
        with get_connection() as conn:
            cursor = conn.cursor()
            # 先检查token是否存在
            cursor.execute("SELECT 1 FROM auth_tokens WHERE token = ?", (token,))
            if not cursor.fetchone():
                return False
            # 执行更新（即使值相同也返回成功，保证幂等性）
            cursor.execute(
                "UPDATE auth_tokens SET description = ? WHERE token = ?",
                (desc_value, token)
            )
            return True
    except Exception as e:
        logger.error(f"更新token描述失败: {e}")
        return False


def update_token_usage(token: str) -> None:
    """更新 token 使用记录"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE auth_tokens
                SET upload_count = upload_count + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE token = ?
            ''', (token,))
    except Exception as e:
        logger.error(f"更新token使用记录失败: {e}")


def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    """获取 token 详细信息"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auth_tokens WHERE token = ?', (token,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取token信息失败: {e}")
        return None


def count_tokens_by_ip(ip_address: str) -> int:
    """统计某个 IP 地址创建的活跃 Token 数量"""
    if not ip_address:
        return 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM auth_tokens WHERE ip_address = ? AND is_active = 1',
                (ip_address,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"统计 IP Token 数量失败: {e}")
        return 0


def get_token_uploads(token: str, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    """获取 token 上传的所有图片"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * limit

            cursor.execute('''
                SELECT encrypted_id, original_filename, file_size, created_at,
                       cdn_cached, cdn_url, mime_type
                FROM file_storage
                WHERE auth_token = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (token, limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"获取token上传记录失败: {e}")
        return []

# ===================== Token 管理（管理员后台） =====================
def admin_list_tokens(
    *,
    status: str = 'all',
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    tg_user_id: int = None,
    tg_bind: str = None,
    sort_by: str = 'created_at',
    sort_order: str = 'desc',
) -> Dict[str, Any]:
    """
    管理员获取 Token 列表（分页）。

    Args:
        status: 筛选状态
            - 'all': 全部
            - 'active': 启用且未过期
            - 'disabled': 禁用但未过期
            - 'expired': 已过期（无论是否启用）
        page: 页码（从 1 开始）
        page_size: 每页数量（最大 100）
        search: 搜索关键词（匹配 token / description / tg_username / tg_first_name）
        tg_user_id: 按 TG 用户 ID 筛选
        tg_bind: TG 绑定筛选（'bound'=已绑定, 'unbound'=未绑定, None/其他=全部）
        sort_by: 排序字段（created_at / upload_count / expires_at / last_used）
        sort_order: 排序方向（asc / desc）

    Returns:
        包含 page, page_size, total, items 的字典
    """
    # 参数规范化
    status = (status or 'all').strip().lower()
    page = max(1, int(page) if isinstance(page, (int, str)) and str(page).isdigit() else 1)
    page_size = max(1, min(100, int(page_size) if isinstance(page_size, (int, str)) and str(page_size).isdigit() else 20))
    offset = (page - 1) * page_size
    sort_by = (sort_by or 'created_at').strip().lower()
    sort_order = (sort_order or 'desc').strip().lower()
    if sort_order not in ('asc', 'desc'):
        sort_order = 'desc'

    # 搜索或 tg_bind 筛选需要 JOIN tg_users
    need_join = bool(
        (search and search.strip()) or
        tg_user_id is not None or
        tg_bind in ('bound', 'unbound')
    )

    # 根据状态构建 WHERE 子句
    where_clauses = []
    where_params_list = []

    if status == 'active':
        where_clauses.append(f"a.is_active = 1 AND NOT (a.expires_at IS NOT NULL AND a.expires_at < CURRENT_TIMESTAMP)")
    elif status == 'disabled':
        where_clauses.append(f"a.is_active = 0 AND NOT (a.expires_at IS NOT NULL AND a.expires_at < CURRENT_TIMESTAMP)")
    elif status == 'expired':
        where_clauses.append(f"(a.expires_at IS NOT NULL AND a.expires_at < CURRENT_TIMESTAMP)")
    elif status != 'all':
        raise ValueError(f"无效的状态筛选: {status}")

    # TG 用户 ID 筛选
    if tg_user_id is not None:
        where_clauses.append("a.tg_user_id = ?")
        where_params_list.append(tg_user_id)

    # TG 绑定状态筛选
    if tg_bind == 'bound':
        where_clauses.append("a.tg_user_id IS NOT NULL")
    elif tg_bind == 'unbound':
        where_clauses.append("a.tg_user_id IS NULL")

    # 搜索条件（扩展到 tg_username / tg_first_name）
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        if need_join:
            where_clauses.append("(a.token LIKE ? OR a.description LIKE ? OR u.username LIKE ? OR u.first_name LIKE ?)")
            where_params_list.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        else:
            where_clauses.append("(a.token LIKE ? OR a.description LIKE ?)")
            where_params_list.extend([search_pattern, search_pattern])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    where_params = tuple(where_params_list)

    if sort_by == 'upload_count':
        order_sql = f"a.upload_count {sort_order}, a.rowid DESC"
    elif sort_by == 'expires_at':
        order_sql = f"(a.expires_at IS NULL) ASC, a.expires_at {sort_order}, a.rowid DESC"
    elif sort_by == 'last_used':
        order_sql = f"(a.last_used IS NULL) ASC, a.last_used {sort_order}, a.rowid DESC"
    else:
        order_sql = f"a.created_at {sort_order}, a.rowid DESC"

    # COUNT 查询需要与主查询保持一致的 JOIN
    join_sql = "LEFT JOIN tg_users u ON a.tg_user_id = u.tg_user_id" if need_join else ""

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询总数
            cursor.execute(f"SELECT COUNT(1) FROM auth_tokens a {join_sql} {where_sql}", where_params)
            total = cursor.fetchone()[0] or 0

            # 查询列表
            cursor.execute(f"""
                SELECT
                    a.rowid AS id,
                    a.token,
                    a.created_at,
                    a.expires_at,
                    a.last_used,
                    a.upload_count,
                    a.upload_limit,
                    a.is_active,
                    a.ip_address,
                    a.user_agent,
                    a.description,
                    a.tg_user_id,
                    CASE WHEN a.expires_at IS NOT NULL AND a.expires_at < CURRENT_TIMESTAMP THEN 1 ELSE 0 END AS is_expired,
                    u.username AS tg_username,
                    u.first_name AS tg_first_name
                FROM auth_tokens a
                LEFT JOIN tg_users u ON a.tg_user_id = u.tg_user_id
                {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
            """, (*where_params, page_size, offset))

            items = [_token_row_to_dict(row, include_full_token=False) for row in cursor.fetchall()]

        return {
            'page': page,
            'page_size': page_size,
            'total': total,
            'items': items
        }

    except Exception as e:
        logger.error(f"管理员获取 Token 列表失败: {e}")
        raise


def admin_get_token_metrics() -> Dict[str, int]:
    """管理员 Token 聚合统计。"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(1) FROM auth_tokens")
            total = int(cursor.fetchone()[0] or 0)

            cursor.execute(f"""
                SELECT COUNT(1)
                FROM auth_tokens
                WHERE is_active = 1
                AND NOT {_EXPIRED_EXPR}
            """)
            active = int(cursor.fetchone()[0] or 0)

            cursor.execute(f"""
                SELECT COUNT(1)
                FROM auth_tokens
                WHERE {_EXPIRED_EXPR}
            """)
            expired = int(cursor.fetchone()[0] or 0)

            cursor.execute("""
                SELECT COUNT(1)
                FROM auth_tokens
                WHERE tg_user_id IS NOT NULL
            """)
            tg_bound = int(cursor.fetchone()[0] or 0)

        return {
            'total': total,
            'active': active,
            'expired': expired,
            'disabled': max(0, total - active - expired),
            'tg_bound': tg_bound,
        }

    except Exception as e:
        logger.error(f"管理员获取 Token 统计失败: {e}")
        raise

def admin_create_token(
    *,
    description: Optional[str] = None,
    expires_at: Any = None,
    upload_limit: int = 100,
    is_active: bool = True
) -> Optional[Dict[str, Any]]:
    """
    管理员创建新的 Token。

    Args:
        description: Token 描述
        expires_at: 过期时间（ISO8601 格式或 datetime 对象，None 表示永不过期）
        upload_limit: 上传限制（0 表示禁止上传，正整数为限制数）
        is_active: 是否启用

    Returns:
        创建成功返回包含完整 token 的字典（仅此一次），失败返回 None
    """
    # 参数处理
    desc_value = (str(description).strip() if description else None) or None

    # 验证上传限制
    try:
        limit_value = int(upload_limit)
        if limit_value < 0:
            raise ValueError("upload_limit 不能为负数")
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的 upload_limit: {upload_limit}") from e

    # 解析过期时间
    expires_value = _parse_datetime(expires_at)

    # 布尔转换
    active_value = 1 if is_active else 0

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 尝试生成唯一 token（最多重试 5 次）
            for _ in range(5):
                token = f"admin_{secrets.token_hex(32)}"
                try:
                    cursor.execute("""
                        INSERT INTO auth_tokens
                        (token, expires_at, upload_limit, is_active, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (token, expires_value, limit_value, active_value, desc_value))

                    token_id = cursor.lastrowid

                    # 查询刚创建的记录
                    cursor.execute(f"""
                        SELECT
                            rowid AS id,
                            token,
                            created_at,
                            expires_at,
                            last_used,
                            upload_count,
                            upload_limit,
                            is_active,
                            ip_address,
                            user_agent,
                            description,
                            CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                        FROM auth_tokens
                        WHERE rowid = ?
                    """, (token_id,))

                    row = cursor.fetchone()
                    if row:
                        logger.info(f"管理员创建 Token 成功: ID={token_id}")
                        return _token_row_to_dict(row, include_full_token=True)

                except sqlite3.IntegrityError:
                    # Token 冲突，重试
                    continue

        logger.error("管理员创建 Token 失败: 无法生成唯一 token")
        return None

    except Exception as e:
        logger.error(f"管理员创建 Token 失败: {e}")
        raise

def admin_update_token_status(*, token_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
    """
    管理员更新 Token 启用状态。

    Args:
        token_id: Token 的 rowid
        is_active: 是否启用

    Returns:
        更新成功返回更新后的 Token 信息，Token 不存在返回 None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 更新状态
            cursor.execute(
                "UPDATE auth_tokens SET is_active = ? WHERE rowid = ?",
                (1 if is_active else 0, int(token_id))
            )

            if cursor.rowcount == 0:
                return None

            # 查询更新后的记录
            cursor.execute(f"""
                SELECT
                    rowid AS id,
                    token,
                    created_at,
                    expires_at,
                    last_used,
                    upload_count,
                    upload_limit,
                    is_active,
                    ip_address,
                    user_agent,
                    description,
                    CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                FROM auth_tokens
                WHERE rowid = ?
            """, (int(token_id),))

            row = cursor.fetchone()
            if row:
                status_text = "启用" if is_active else "禁用"
                logger.info(f"管理员更新 Token 状态: ID={token_id} -> {status_text}")
                return _token_row_to_dict(row, include_full_token=False)

            return None

    except Exception as e:
        logger.error(f"管理员更新 Token 状态失败: {e}")
        raise


def admin_update_token(
    *,
    token_id: int,
    description: Optional[str] = ...,
    expires_at: Any = ...,
    upload_limit: Any = ...,
    is_active: Optional[bool] = ...,
) -> Optional[Dict[str, Any]]:
    """
    管理员更新 Token 属性（仅更新传入的字段）。

    使用 ... (Ellipsis) 作为默认值区分"未传入"和"传入 None"。

    Args:
        token_id: Token 的 rowid
        description: 描述（None 清空）
        expires_at: 过期时间（ISO8601 / datetime / None 表示永不过期）
        upload_limit: 上传限制（None 表示不限制）
        is_active: 是否启用

    Returns:
        更新成功返回更新后的 Token 信息，Token 不存在返回 None
    """
    sets: list = []
    params: list = []

    if description is not ...:
        sets.append("description = ?")
        params.append((str(description).strip()[:200]) if description else None)

    if expires_at is not ...:
        sets.append("expires_at = ?")
        params.append(_parse_datetime(expires_at))

    if upload_limit is not ...:
        if upload_limit is None:
            sets.append("upload_limit = ?")
            params.append(None)
        else:
            val = int(upload_limit)
            if val < 0:
                raise ValueError("upload_limit 不能为负数")
            sets.append("upload_limit = ?")
            params.append(val)

    if is_active is not ...:
        sets.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not sets:
        raise ValueError("未提供任何更新字段")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            sql = f"UPDATE auth_tokens SET {', '.join(sets)} WHERE rowid = ?"
            params.append(int(token_id))
            cursor.execute(sql, params)

            if cursor.rowcount == 0:
                return None

            # 查询更新后的记录
            cursor.execute(f"""
                SELECT
                    rowid AS id,
                    token,
                    created_at,
                    expires_at,
                    last_used,
                    upload_count,
                    upload_limit,
                    is_active,
                    ip_address,
                    user_agent,
                    description,
                    CASE WHEN {_EXPIRED_EXPR} THEN 1 ELSE 0 END AS is_expired
                FROM auth_tokens
                WHERE rowid = ?
            """, (int(token_id),))

            row = cursor.fetchone()
            if row:
                logger.info(f"管理员更新 Token: ID={token_id}, 字段={list(s.split(' =')[0] for s in sets)}")
                return _token_row_to_dict(row, include_full_token=False)

            return None

    except Exception as e:
        logger.error(f"管理员更新 Token 失败: {e}")
        raise


def admin_delete_token(*, token_id: int) -> bool:
    """
    管理员删除 Token。

    Args:
        token_id: Token 的 rowid

    Returns:
        删除成功返回 True，Token 不存在返回 False
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_tokens WHERE rowid = ?", (int(token_id),))
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"管理员删除 Token: ID={token_id}")

            return deleted

    except Exception as e:
        logger.error(f"管理员删除 Token 失败: {e}")
        raise


def delete_token_by_string(token: str, *, delete_images: bool = False) -> bool:
    """
    按 token 字符串级联删除（用户侧删除）。

    级联：file_storage.auth_token 置空 → galleries.owner_token 置空
          → gallery_token_access 清理 → auth_tokens 删除

    Args:
        token: Token 字符串
        delete_images: 是否同时删除关联图片（存储后端 + 数据库记录）
    """
    token = (token or '').strip()
    if not token:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # 检查 token 是否存在
            cursor.execute("SELECT 1 FROM auth_tokens WHERE token = ?", (token,))
            if not cursor.fetchone():
                return False

            # 可选：删除关联图片
            if delete_images:
                from ..services.token_service import TokenService
                TokenService._delete_images_for_token_str(token, cursor)
            else:
                # 仅置空 auth_token
                cursor.execute(
                    "UPDATE file_storage SET auth_token = NULL WHERE auth_token = ?",
                    (token,),
                )

            # 级联清理
            cursor.execute(
                "UPDATE galleries SET owner_token = NULL WHERE owner_token = ?",
                (token,),
            )
            cursor.execute(
                "DELETE FROM gallery_token_access WHERE token = ?",
                (token,),
            )
            cursor.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        action = "级联删除（含图片）" if delete_images else "级联删除"
        logger.info(f"用户侧{action} Token: {token[:20]}...")
        return True
    except Exception as e:
        logger.error(f"用户侧删除 Token 失败: {e}")
        return False


def admin_get_token_detail(token_id: int) -> Optional[Dict[str, Any]]:
    """按 rowid 获取完整 Token 信息（含完整 token 字符串 + TG 用户信息）"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT
                    a.rowid AS id,
                    a.token,
                    a.created_at,
                    a.expires_at,
                    a.last_used,
                    a.upload_count,
                    a.upload_limit,
                    a.is_active,
                    a.ip_address,
                    a.user_agent,
                    a.description,
                    a.tg_user_id,
                    CASE WHEN a.expires_at IS NOT NULL AND a.expires_at < CURRENT_TIMESTAMP THEN 1 ELSE 0 END AS is_expired,
                    u.username AS tg_username,
                    u.first_name AS tg_first_name,
                    u.last_name AS tg_last_name
                FROM auth_tokens a
                LEFT JOIN tg_users u ON a.tg_user_id = u.tg_user_id
                WHERE a.rowid = ?
            """, (int(token_id),))

            row = cursor.fetchone()
            if not row:
                return None

            return _token_row_to_dict(row, include_full_token=True)

    except Exception as e:
        logger.error(f"管理员获取 Token 详情失败: {e}")
        raise


def admin_get_token_overview(token_id: int) -> Optional[Dict[str, Any]]:
    """
    按 rowid 获取 Token 概览信息（详情 + 关联统计）。
    用于列表侧滑详情快速展示，减少前端多次请求。
    """
    detail = admin_get_token_detail(token_id)
    if not detail:
        return None

    token_str = detail.get('token')
    if not token_str:
        return detail

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(1), MAX(created_at) FROM file_storage WHERE auth_token = ?",
                (token_str,),
            )
            upload_row = cursor.fetchone() or (0, None)

            cursor.execute(
                "SELECT COUNT(1), MAX(created_at) FROM galleries WHERE owner_token = ?",
                (token_str,),
            )
            gallery_row = cursor.fetchone() or (0, None)

            cursor.execute(
                "SELECT COUNT(1) FROM gallery_token_access WHERE token = ?",
                (token_str,),
            )
            access_count = int((cursor.fetchone() or (0,))[0] or 0)

        detail['summary'] = {
            'upload_total': int(upload_row[0] or 0),
            'gallery_total': int(gallery_row[0] or 0),
            'access_total': access_count,
            'last_upload_at': upload_row[1],
            'last_gallery_at': gallery_row[1],
        }
        return detail

    except Exception as e:
        logger.error(f"管理员获取 Token 概览失败: {e}")
        raise


def admin_get_token_uploads(
    token_id: int,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    """按 rowid 获取 Token 上传的图片（分页，含 total）"""
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
    offset = (page - 1) * page_size

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 先查 token 字符串
            cursor.execute("SELECT token FROM auth_tokens WHERE rowid = ?", (int(token_id),))
            token_row = cursor.fetchone()
            if not token_row:
                return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}

            token_str = token_row[0]

            # 查总数
            cursor.execute(
                "SELECT COUNT(1) FROM file_storage WHERE auth_token = ?",
                (token_str,)
            )
            total = cursor.fetchone()[0] or 0

            # 查分页数据
            cursor.execute("""
                SELECT encrypted_id, original_filename, file_size, created_at,
                       cdn_cached, cdn_url, mime_type
                FROM file_storage
                WHERE auth_token = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (token_str, page_size, offset))

            items = [dict(row) for row in cursor.fetchall()]

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
            }

    except Exception as e:
        logger.error(f"管理员获取 Token 上传记录失败: {e}")
        raise


def admin_get_token_galleries(
    token_id: int,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    """按 rowid 获取 Token 拥有的画集（分页）"""
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
    offset = (page - 1) * page_size

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 先查 token 字符串
            cursor.execute("SELECT token FROM auth_tokens WHERE rowid = ?", (int(token_id),))
            token_row = cursor.fetchone()
            if not token_row:
                return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}

            token_str = token_row[0]

            # 查总数
            cursor.execute(
                "SELECT COUNT(1) FROM galleries WHERE owner_token = ?",
                (token_str,)
            )
            total = cursor.fetchone()[0] or 0

            # 查分页数据（含图片数和封面）
            cursor.execute("""
                SELECT g.*,
                    (SELECT COUNT(*) FROM gallery_images gi WHERE gi.gallery_id = g.id) AS image_count,
                    COALESCE(g.cover_image, (
                        SELECT gi2.encrypted_id FROM gallery_images gi2
                        WHERE gi2.gallery_id = g.id
                        ORDER BY gi2.added_at ASC
                        LIMIT 1
                    )) AS resolved_cover_image
                FROM galleries g
                WHERE g.owner_token = ?
                ORDER BY g.created_at DESC
                LIMIT ? OFFSET ?
            """, (token_str, page_size, offset))

            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item['cover_image'] = item.pop('resolved_cover_image', item.get('cover_image'))
                items.append(item)

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
            }

    except Exception as e:
        logger.error(f"管理员获取 Token 画集失败: {e}")
        raise
