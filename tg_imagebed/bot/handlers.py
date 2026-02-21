#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 消息处理器模块

包含 /start 命令处理和图片上传处理。
"""
import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from telegram import Update

from ..config import logger
from .media_batch import _MediaBatch, _media_group_batches, _flush_media_group, _MAX_BATCH_ITEMS
from .state import _inc_bot_stats

# 文件下载超时（秒）
_DOWNLOAD_TIMEOUT = 60


async def start(update: Update, context):
    """处理 /start 命令"""
    from ..database import get_stats
    from ..utils import get_domain
    from .state import _get_bot_status

    stats = get_stats()
    bot_status = _get_bot_status()
    await update.message.reply_text(
        "☁️ *Telegram 云图床机器人*\n\n"
        "✨ 直接发送图片获取永久直链\n\n"
        f"🌐 *Web界面:* {get_domain(None)}\n"
        f"📊 *已存储:* {stats['total_files']} 个文件\n"
        f"💾 *总大小:* {stats['total_size'] / 1024 / 1024:.1f} MB\n"
        f"🤖 *Bot统计:* 处理 {bot_status['stats_processed']} 张"
        f"（✅{bot_status['stats_success']} ❌{bot_status['stats_failed']}）\n\n"
        "直接发送图片即可开始使用！",
        parse_mode='Markdown'
    )


def _parse_id_list(raw: str) -> set:
    """解析逗号分隔的 ID 列表"""
    if not raw:
        return set()
    try:
        return {int(x.strip()) for x in raw.split(',') if x.strip()}
    except ValueError:
        return set()


async def handle_photo(update: Update, context):
    """处理图片上传（私聊/群组/频道）"""
    from ..services.file_service import process_upload, record_existing_telegram_file
    from ..utils import get_domain, get_mime_type as _get_mime_type
    from ..database import get_system_setting

    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return

    chat_type = (getattr(chat, 'type', '') or '').lower()
    is_group = chat_type in ('group', 'supergroup', 'channel')

    # 群组/频道：执行权限检查
    reply_enabled = True
    delete_delay = 0
    if is_group:
        if str(get_system_setting('group_upload_admin_only') or '0') == '1':
            admin_raw = str(get_system_setting('group_admin_ids') or '').strip()
            admin_ids = _parse_id_list(admin_raw)
            user = update.effective_user
            if not user or not admin_ids or user.id not in admin_ids:
                return

        reply_enabled = str(get_system_setting('group_upload_reply') or '1') == '1'
        try:
            delete_delay = max(0, int(get_system_setting('group_upload_delete_delay') or '0'))
        except (ValueError, TypeError):
            delete_delay = 0

    # 获取用户信息
    user = update.effective_user
    if user:
        username = user.username or user.full_name or str(user.id)
    else:
        username = getattr(chat, 'title', '') or 'channel'

    # 检测批量上传（media_group_id）
    media_group_id = getattr(message, 'media_group_id', None)
    use_batch = bool(is_group and reply_enabled and media_group_id)

    # 发送处理中消息（批量模式下延迟到首张图片时发送）
    status_msg = None
    if reply_enabled and not use_batch:
        try:
            status_msg = await message.reply_text("⏳ 正在处理图片...")
        except Exception:
            pass

    try:
        # 提取图片：优先photo，其次document（文件形式发送的图片）
        tg_file = None
        filename = ""
        content_type = "image/jpeg"
        file_unique_id = None

        if message.photo:
            tg_file = message.photo[-1]
            file_unique_id = tg_file.file_unique_id
            filename = f"telegram_{file_unique_id}.jpg"
            content_type = "image/jpeg"
        elif message.document:
            doc = message.document
            mime = (doc.mime_type or "").lower()
            doc_name = (doc.file_name or "").lower()
            from ..config import get_allowed_extensions
            allowed = get_allowed_extensions()
            is_image = mime.startswith("image/") or any(
                doc_name.endswith(f'.{ext}') for ext in allowed
            )
            if is_image:
                tg_file = doc
                file_unique_id = doc.file_unique_id
                filename = doc.file_name or f"telegram_{file_unique_id}"
                content_type = doc.mime_type or _get_mime_type(filename)

        if not tg_file:
            if status_msg:
                await status_msg.edit_text("❌ 请发送图片文件")
            elif reply_enabled:
                try:
                    await message.reply_text("❌ 请发送图片文件")
                except Exception:
                    pass
            return

        # Caption 自定义文件名：用说明文字替换默认文件名（保留原始扩展名）
        if message.caption and str(get_system_setting('bot_caption_filename_enabled') or '1') == '1':
            from .commands import _sanitize_filename
            original_ext = os.path.splitext(filename)[1] or '.jpg'
            custom_name = _sanitize_filename(message.caption, original_ext)
            if custom_name:
                filename = custom_name

        # 批量模式：添加到累加器，延迟统一处理
        if use_batch:
            batch_key = (chat.id, str(media_group_id))
            batch = _media_group_batches.get(batch_key)
            if not batch:
                batch = _MediaBatch(
                    chat_id=chat.id,
                    media_group_id=str(media_group_id),
                    message_thread_id=getattr(message, 'message_thread_id', None),
                    delete_delay=delete_delay,
                )
                _media_group_batches[batch_key] = batch

            # 批量上限保护
            if len(batch.items) >= _MAX_BATCH_ITEMS:
                logger.warning(f"批量上传超过上限 {_MAX_BATCH_ITEMS}，忽略多余图片: chat={chat.id} group={media_group_id}")
                return

            batch.items.append({
                "file_id": tg_file.file_id,
                "file_unique_id": file_unique_id,
                "filename": filename,
                "content_type": content_type,
                "message_id": message.message_id,
                "username": username,
            })
            batch.updated_at = time.monotonic()
            if batch.first_message_id is None or message.message_id < batch.first_message_id:
                batch.first_message_id = message.message_id

            # 首张图片时发送状态消息
            if batch.status_message_id is None:
                try:
                    status_msg = await message.reply_text("⏳ 正在处理相册图片，请稍候...")
                    batch.status_message_id = status_msg.message_id
                except Exception:
                    pass

            # 重置 debounce 定时器
            if batch.flush_task:
                batch.flush_task.cancel()
            batch.flush_task = asyncio.create_task(
                _flush_media_group(batch_key, context.bot, debounce_seconds=1.5)
            )
            return

        file_info = await asyncio.wait_for(context.bot.get_file(tg_file.file_id), timeout=_DOWNLOAD_TIMEOUT)
        file_bytes = await asyncio.wait_for(file_info.download_as_bytearray(), timeout=_DOWNLOAD_TIMEOUT)

        if is_group:
            result = record_existing_telegram_file(
                file_id=tg_file.file_id,
                file_unique_id=file_unique_id,
                file_path=getattr(file_info, 'file_path', '') or '',
                file_content=bytes(file_bytes),
                filename=filename,
                content_type=content_type,
                username=username,
                source='telegram_group',
                is_group_upload=True,
                group_message_id=message.message_id,
                group_chat_id=chat.id,
            )
        else:
            result = process_upload(
                file_content=bytes(file_bytes),
                filename=filename,
                content_type=content_type,
                username=username,
                source='telegram_bot',
                is_group_upload=False,
                group_message_id=None,
                upload_scene=None
            )

        if not reply_enabled:
            return

        if result:
            _inc_bot_stats(success=1)
            base_url = get_domain(None)
            permanent_url = f"{base_url}/image/{result['encrypted_id']}"
            text = (
                f"✅ *上传成功！*\n\n"
                f"🔗 *永久直链:*\n`{permanent_url}`\n\n"
                f"📊 *文件大小:* {result['file_size']} bytes\n"
                f"💡 链接永久有效"
            )

            # 私聊场景添加 inline 按钮（打开链接 + 删除）
            reply_markup = None
            if not is_group and str(get_system_setting('bot_inline_buttons_enabled') or '1') == '1':
                from .commands import build_upload_success_keyboard
                reply_markup = build_upload_success_keyboard(
                    permanent_url, result['encrypted_id']
                )

            reply_msg_id = None
            if status_msg:
                await status_msg.edit_text(
                    text, parse_mode='Markdown', reply_markup=reply_markup
                )
                reply_msg_id = status_msg.message_id
            else:
                sent = await message.reply_text(
                    text, parse_mode='Markdown', reply_markup=reply_markup
                )
                reply_msg_id = sent.message_id

            # 群组延迟删除回复（后台执行，不阻塞）
            if is_group and delete_delay > 0 and reply_msg_id:
                async def delayed_delete():
                    try:
                        await asyncio.sleep(delete_delay)
                        await context.bot.delete_message(chat_id=chat.id, message_id=reply_msg_id)
                    except Exception as e:
                        logger.debug(f"删除回复消息失败: {e}")
                asyncio.create_task(delayed_delete())
        else:
            _inc_bot_stats(failed=1)
            if status_msg:
                await status_msg.edit_text("❌ 存储后端处理失败，请稍后重试")
    except asyncio.TimeoutError:
        _inc_bot_stats(failed=1)
        logger.error("文件下载超时")
        if status_msg:
            try:
                await status_msg.edit_text("❌ 文件下载超时，请检查网络后重试")
            except Exception:
                pass
    except Exception as e:
        _inc_bot_stats(failed=1)
        err_type = type(e).__name__
        logger.error(f"Error processing photo: {err_type}: {e}")

        # 区分错误类型给出友好提示
        if "Forbidden" in str(e) or "权限" in str(e):
            err_msg = "❌ 权限不足，请检查 Bot 权限设置"
        elif "NetworkError" in err_type or "TimedOut" in err_type:
            err_msg = "❌ 网络错误，请稍后重试"
        elif "BadRequest" in err_type:
            err_msg = "❌ 文件无法处理（可能过大或格式不支持）"
        else:
            err_msg = f"❌ 处理失败（{err_type}），请重试"

        if status_msg:
            try:
                await status_msg.edit_text(err_msg)
            except Exception:
                pass
