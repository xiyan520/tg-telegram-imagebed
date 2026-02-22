#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 命令模块

包含 /help, /id, /myuploads, /delete 命令处理，
callback_query 统一分发，以及上传成功 inline keyboard 构建。
"""
import math
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..config import logger


# ===================== 工具函数 =====================

def _sanitize_filename(caption: str, original_ext: str) -> str:
    """清理 caption 文本为安全文件名（保留原始扩展名）

    Args:
        caption: 用户发送的说明文字
        original_ext: 原始文件扩展名（含点号，如 '.jpg'）

    Returns:
        安全的文件名字符串
    """
    # 去除首尾空白
    name = caption.strip()
    # 移除路径分隔符和危险字符
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name)
    # 压缩连续下划线/空格
    name = re.sub(r'[_\s]+', '_', name).strip('_')
    # 限制长度（Telegram callback_data 64字节限制 + 文件系统兼容）
    if len(name.encode('utf-8')) > 100:
        while len(name.encode('utf-8')) > 100 and name:
            name = name[:-1]
        name = name.strip('_')
    # 空名称回退
    if not name:
        return None
    return f"{name}{original_ext}"


def build_upload_success_keyboard(
    permanent_url: str, encrypted_id: str
) -> InlineKeyboardMarkup:
    """构建上传成功后的 inline keyboard（私聊场景）

    Args:
        permanent_url: 图片永久直链
        encrypted_id: 加密文件ID（用于删除回调）
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 打开链接", url=permanent_url),
            InlineKeyboardButton("🗑 删除", callback_data=f"qdel:{encrypted_id}"),
        ]
    ])


# ===================== 命令处理器 =====================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令 — 显示所有可用命令"""
    text = (
        "📖 *可用命令列表*\n\n"
        "/start — 查看机器人状态和统计\n"
        "/help — 显示此帮助信息\n"
        "/id — 查看你的 Telegram ID 和聊天信息\n"
        "/myuploads — 查看个人上传历史\n"
        "/delete <ID> — 删除你上传的图片\n"
        "/login — 获取 Web 端登录链接\n"
        "/mytokens — 查看我的 Token\n\n"
        "💡 *使用方法*\n"
        "直接发送图片即可获取永久直链\n"
        "发送图片时附带说明文字可自定义文件名"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /id 命令 — 显示用户 ID 和聊天信息"""
    user = update.effective_user
    chat = update.effective_chat

    lines = ["🆔 *你的信息*\n"]
    if user:
        lines.append(f"👤 *用户 ID:* `{user.id}`")
        if user.username:
            lines.append(f"📛 *用户名:* @{user.username}")
        lines.append(f"📝 *全名:* {user.full_name}")
    if chat:
        lines.append(f"\n💬 *聊天 ID:* `{chat.id}`")
        lines.append(f"📋 *聊天类型:* {chat.type}")
        if chat.title:
            lines.append(f"📌 *聊天标题:* {chat.title}")

    lines.append("\n💡 将用户 ID 添加到 `group_admin_ids` 可获得群组管理权限")
    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')


async def myuploads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /myuploads 命令 — 查看个人上传历史"""
    from ..database import get_system_setting

    if str(get_system_setting('bot_myuploads_enabled') or '1') != '1':
        await update.message.reply_text("❌ 上传历史查询功能已关闭")
        return

    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ 无法获取用户信息")
        return
    username = user.username or user.full_name or str(user.id)
    await _show_myuploads(update.message, username, page=1)


async def _show_myuploads(message_or_query, username: str, page: int = 1, edit: bool = False):
    """展示上传历史（支持首次发送和翻页编辑）

    Args:
        message_or_query: Message 对象或 CallbackQuery 对象
        username: 用户名
        page: 页码
        edit: 是否编辑现有消息（翻页时为 True）
    """
    from ..database import get_user_uploads, get_system_setting
    from ..utils import get_domain

    try:
        per_page = max(1, min(50, int(get_system_setting('bot_myuploads_page_size') or '8')))
    except (TypeError, ValueError):
        per_page = 8
    files, total = get_user_uploads(username, limit=per_page, page=page)
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)

    if total == 0:
        text = "📭 你还没有上传过图片"
        if edit:
            await message_or_query.edit_message_text(text)
        else:
            await message_or_query.reply_text(text)
        return

    base_url = get_domain(None)
    lines = [f"📋 *你的上传记录* （共 {total} 张，第 {page}/{total_pages} 页）\n"]
    for f in files:
        name = f.get('original_filename') or f['encrypted_id'][:12]
        size_kb = (f.get('file_size') or 0) / 1024
        eid = f['encrypted_id']
        lines.append(f"• `{eid[:12]}` | {name} | {size_kb:.0f}KB")

    text = '\n'.join(lines)

    # 构建翻页按钮
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"myup:{page - 1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"myup:{page + 1}"))

    markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if edit:
        await message_or_query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
    else:
        await message_or_query.reply_text(text, parse_mode='Markdown', reply_markup=markup)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /delete <ID> 命令 — 删除自己上传的图片"""
    from ..database import get_file_info, get_system_setting

    if str(get_system_setting('bot_user_delete_enabled') or '1') != '1':
        await update.message.reply_text("❌ 自助删除功能已关闭")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ 请提供文件 ID\n\n用法: `/delete <ID>`\n"
            "💡 使用 /myuploads 查看你的文件 ID",
            parse_mode='Markdown'
        )
        return

    encrypted_id = context.args[0].strip()
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ 无法获取用户信息")
        return

    username = user.username or user.full_name or str(user.id)

    # 查询文件并验证所有权
    file_info = get_file_info(encrypted_id)
    if not file_info:
        await update.message.reply_text("❌ 文件不存在")
        return

    if file_info.get('username') != username:
        await update.message.reply_text("❌ 你没有权限删除此文件")
        return

    # 弹出确认按钮
    name = file_info.get('original_filename') or encrypted_id[:12]
    size_kb = (file_info.get('file_size') or 0) / 1024
    text = (
        f"⚠️ *确认删除？*\n\n"
        f"📄 *文件:* {name}\n"
        f"🆔 *ID:* `{encrypted_id[:16]}`\n"
        f"📊 *大小:* {size_kb:.0f} KB\n\n"
        f"此操作不可撤销！"
    )
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 确认删除", callback_data=f"cdel:{encrypted_id}:y"),
        InlineKeyboardButton("❌ 取消", callback_data=f"cdel:{encrypted_id}:n"),
    ]])
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)


# ===================== Callback 统一分发 =====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统一 callback_query 入口，按前缀分发"""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    if data.startswith("myup:"):
        await _handle_myuploads_page(query)
    elif data.startswith("cdel:"):
        await _handle_confirm_delete(query)
    elif data.startswith("qdel:"):
        await _handle_quick_delete(query)
    else:
        logger.warning(f"未知 callback_data: {data}")


async def _handle_myuploads_page(query):
    """处理上传历史翻页"""
    from ..database import get_system_setting

    if str(get_system_setting('bot_myuploads_enabled') or '1') != '1':
        await query.edit_message_text("❌ 上传历史查询功能已关闭")
        return

    try:
        page = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    user = query.from_user
    if not user:
        return
    username = user.username or user.full_name or str(user.id)
    await _show_myuploads(query, username, page=page, edit=True)


async def _handle_confirm_delete(query):
    """处理 /delete 确认/取消回调"""
    from ..database import get_file_info, delete_files_by_ids, get_system_setting

    parts = query.data.split(":")
    if len(parts) != 3:
        return

    encrypted_id, action = parts[1], parts[2]

    if action == 'n':
        await query.edit_message_text("❎ 已取消删除")
        return

    if str(get_system_setting('bot_user_delete_enabled') or '1') != '1':
        await query.edit_message_text("❌ 自助删除功能已关闭")
        return

    # 验证所有权
    user = query.from_user
    if not user:
        return
    username = user.username or user.full_name or str(user.id)

    file_info = get_file_info(encrypted_id)
    if not file_info:
        await query.edit_message_text("❌ 文件不存在或已被删除")
        return

    if file_info.get('username') != username:
        await query.edit_message_text("❌ 你没有权限删除此文件")
        return

    deleted_count, deleted_size = delete_files_by_ids([encrypted_id])
    if deleted_count > 0:
        await query.edit_message_text("✅ 文件已成功删除")
    else:
        await query.edit_message_text("❌ 删除失败，请稍后重试")


async def _handle_quick_delete(query):
    """处理上传成功后的快速删除按钮"""
    from ..database import get_file_info, delete_files_by_ids, get_system_setting

    if str(get_system_setting('bot_user_delete_enabled') or '1') != '1':
        await query.edit_message_text("❌ 自助删除功能已关闭")
        return

    encrypted_id = query.data.split(":", 1)[1] if ":" in query.data else ""
    if not encrypted_id:
        return

    user = query.from_user
    if not user:
        return
    username = user.username or user.full_name or str(user.id)

    file_info = get_file_info(encrypted_id)
    if not file_info:
        await query.edit_message_text("❌ 文件不存在或已被删除")
        return

    if file_info.get('username') != username:
        await query.edit_message_text("❌ 你没有权限删除此文件")
        return

    deleted_count, _ = delete_files_by_ids([encrypted_id])
    if deleted_count > 0:
        await query.edit_message_text("✅ 文件已删除")
    else:
        await query.edit_message_text("❌ 删除失败，请稍后重试")


# ===================== TG 认证命令 =====================

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /login 命令 — 生成 Web 端一次性登录链接"""
    from ..database import get_system_setting, upsert_tg_user, create_login_code
    from ..utils import get_domain

    if str(get_system_setting('tg_auth_enabled') or '0') != '1':
        await update.message.reply_text("❌ TG 认证功能未启用")
        return

    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ 无法获取用户信息")
        return

    # 记录/更新用户信息
    upsert_tg_user(
        tg_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # 生成一次性登录链接
    code = create_login_code(code_type='login_link', tg_user_id=user.id)
    if not code:
        await update.message.reply_text("❌ 生成登录链接失败，请稍后重试")
        return

    base_url = get_domain(None)
    login_url = f"{base_url}/tg-login?code={code}"

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 点击登录 Web 端", url=login_url)
    ]])

    await update.message.reply_text(
        "🔐 *Web 端登录*\n\n"
        "点击下方按钮登录图床 Web 端：\n\n"
        "⏰ 链接有效期 5 分钟，仅可使用一次",
        parse_mode='Markdown',
        reply_markup=markup
    )


async def mytokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /mytokens 命令 — 查看绑定的 Token"""
    from ..database import get_system_setting, get_user_tokens

    if str(get_system_setting('tg_auth_enabled') or '0') != '1':
        await update.message.reply_text("❌ TG 认证功能未启用")
        return

    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ 无法获取用户信息")
        return

    tokens = get_user_tokens(user.id)
    if not tokens:
        await update.message.reply_text("📭 你还没有绑定任何 Token\n\n💡 通过 Web 端登录后生成的 Token 会自动绑定")
        return

    lines = [f"🔑 *你的 Token*（共 {len(tokens)} 个）\n"]
    for t in tokens:
        token_str = t['token']
        masked = f"{token_str[:8]}…{token_str[-4:]}" if len(token_str) > 12 else token_str
        status = "✅" if t['is_active'] else "❌"
        usage = f"{t['upload_count']}/{t['upload_limit']}"
        desc = t.get('description') or ''
        desc_str = f" | {desc}" if desc else ''
        lines.append(f"• `{masked}` {status} {usage}{desc_str}")

    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')
