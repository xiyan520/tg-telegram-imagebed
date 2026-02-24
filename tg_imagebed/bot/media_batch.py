#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量图片处理模块（media_group）

处理群组/频道中的批量图片上传，使用 debounce 机制合并汇总消息。
"""
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..config import logger
from ..utils import format_size

# 单个 media_group 最大图片数
_MAX_BATCH_ITEMS = 20
# 残留 batch 过期时间（秒）
_STALE_BATCH_TIMEOUT = 300
# 文件下载超时（秒）
_DOWNLOAD_TIMEOUT = 60


@dataclass
class _MediaBatch:
    """群组/频道批量图片上传的累加器"""
    chat_id: int
    media_group_id: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    status_message_id: Optional[int] = None
    first_message_id: Optional[int] = None
    message_thread_id: Optional[int] = None
    delete_delay: int = 0
    flush_task: Optional[Any] = None
    updated_at: float = field(default_factory=time.monotonic)


_media_group_batches: Dict[Tuple[int, str], _MediaBatch] = {}


def _cleanup_stale_batches() -> None:
    """清理超过 _STALE_BATCH_TIMEOUT 秒的残留 batch，防止内存泄漏"""
    now = time.monotonic()
    stale_keys = [
        k for k, v in _media_group_batches.items()
        if now - v.updated_at > _STALE_BATCH_TIMEOUT
    ]
    for k in stale_keys:
        batch = _media_group_batches.pop(k, None)
        if batch and batch.flush_task:
            batch.flush_task.cancel()
        logger.warning(f"清理残留 batch: chat={k[0]} group={k[1]}, items={len(batch.items) if batch else '?'}")


def _format_batch_summary(
    urls: List[str],
    success_count: int,
    total_count: int,
    total_size_bytes: int,
    failure_count: int,
) -> str:
    """格式化批量上传汇总消息（自动截断以避免超过4096字符）"""
    lines = [f"✅ *批量上传完成* (成功: {success_count} / 总数: {total_count})"]

    if urls:
        lines.append("")
        # 超过10张时使用紧凑模式
        if len(urls) <= 10:
            for i, url in enumerate(urls, 1):
                lines.append(f"{i}. `{url}`")
        else:
            # 紧凑模式：只显示前8条 + 省略提示
            for i, url in enumerate(urls[:8], 1):
                lines.append(f"{i}. `{url}`")
            lines.append(f"... 及其他 {len(urls) - 8} 张")

    lines.append("")
    lines.append(f"📦 *总大小:* {format_size(total_size_bytes)}")
    if failure_count:
        lines.append(f"❌ *失败:* {failure_count} 张")
    lines.append("💡 链接永久有效")
    return "\n".join(lines)


async def _flush_media_group(
    batch_key: Tuple[int, str],
    bot: Any,
    debounce_seconds: float = 1.5,
) -> None:
    """延迟处理批量图片并发送汇总消息"""
    import asyncio
    from ..services.file_service import record_existing_telegram_file
    from ..utils import get_domain
    from .state import _inc_bot_stats

    try:
        await asyncio.sleep(debounce_seconds)
    except asyncio.CancelledError:
        return

    # 入口处清理残留 batch
    _cleanup_stale_batches()

    batch = _media_group_batches.get(batch_key)
    if not batch:
        return

    # 确保是当前任务在执行
    current_task = asyncio.current_task()
    if batch.flush_task is not None and batch.flush_task is not current_task:
        return

    # 竞态校验：如果在 sleep 期间有新图片到达，重新调度剩余等待时间
    elapsed = time.monotonic() - batch.updated_at
    if elapsed < debounce_seconds:
        remaining = debounce_seconds - elapsed
        batch.flush_task = asyncio.create_task(
            _flush_media_group(batch_key, bot, debounce_seconds=remaining)
        )
        return

    _media_group_batches.pop(batch_key, None)

    base_url = get_domain(None)
    urls: List[str] = []
    total_size_bytes = 0
    total_count = len(batch.items)
    failure_count = 0

    # 按消息ID排序处理
    for item in sorted(batch.items, key=lambda x: x.get("message_id", 0)):
        try:
            file_id = item.get("file_id")
            if not file_id:
                failure_count += 1
                continue

            file_info = await asyncio.wait_for(bot.get_file(file_id), timeout=_DOWNLOAD_TIMEOUT)
            file_bytes = await asyncio.wait_for(file_info.download_as_bytearray(), timeout=_DOWNLOAD_TIMEOUT)

            result = record_existing_telegram_file(
                file_id=file_id,
                file_unique_id=item.get("file_unique_id"),
                file_path=getattr(file_info, "file_path", "") or "",
                file_content=bytes(file_bytes),
                filename=item.get("filename", ""),
                content_type=item.get("content_type", "image/jpeg"),
                username=item.get("username", ""),
                source="telegram_group",
                auth_token=item.get("auth_token"),
                is_group_upload=True,
                group_message_id=item.get("message_id"),
                group_chat_id=batch.chat_id,
            )

            if not result:
                failure_count += 1
                continue

            urls.append(f"{base_url}/image/{result['encrypted_id']}")
            total_size_bytes += int(result.get("file_size", 0) or 0)
        except Exception as e:
            failure_count += 1
            logger.error(f"批量处理图片失败: {e}")

    success_count = len(urls)
    failure_count = total_count - success_count

    # 更新运行时统计
    _inc_bot_stats(success=success_count, failed=failure_count)

    summary_text = _format_batch_summary(
        urls, success_count, total_count, total_size_bytes, failure_count
    )
    # PLACEHOLDER_FLUSH_SEND

    reply_msg_id: Optional[int] = None

    # 优先编辑已有的状态消息
    if batch.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=batch.chat_id,
                message_id=batch.status_message_id,
                text=summary_text,
                parse_mode="Markdown",
            )
            reply_msg_id = batch.status_message_id
        except Exception:
            pass

    # 如果编辑失败，发送新消息
    if reply_msg_id is None:
        send_kwargs: Dict[str, Any] = {
            "chat_id": batch.chat_id,
            "text": summary_text,
            "parse_mode": "Markdown",
        }
        if batch.message_thread_id is not None:
            send_kwargs["message_thread_id"] = batch.message_thread_id
        if batch.first_message_id is not None:
            send_kwargs["reply_to_message_id"] = batch.first_message_id

        try:
            sent = await bot.send_message(**send_kwargs)
            reply_msg_id = getattr(sent, "message_id", None)
        except Exception:
            send_kwargs.pop("reply_to_message_id", None)
            try:
                sent = await bot.send_message(**send_kwargs)
                reply_msg_id = getattr(sent, "message_id", None)
            except Exception as e:
                logger.error(f"发送批量汇总消息失败: {e}")

    # 延迟删除回复
    if batch.delete_delay > 0 and reply_msg_id:
        async def delayed_delete():
            try:
                await asyncio.sleep(batch.delete_delay)
                await bot.delete_message(chat_id=batch.chat_id, message_id=reply_msg_id)
            except Exception as e:
                logger.debug(f"删除回复消息失败: {e}")
        asyncio.create_task(delayed_delete())
