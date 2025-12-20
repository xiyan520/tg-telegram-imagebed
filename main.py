#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 图床机器人 - 模块化重构版入口文件

将原有 3638 行的 main.py 拆分为模块化架构：
- config.py: 配置管理
- utils.py: 工具函数
- database.py: 数据访问层
- services/: 服务层
- api/: 路由层
"""
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置
from tg_imagebed.config import (
    PORT, SECRET_KEY, ALLOWED_ORIGINS, DATABASE_PATH,
    PROXY_URL, STATIC_FOLDER,
    logger, print_config_info
)

# 导入 Bot 控制模块
from tg_imagebed.bot_control import (
    get_effective_bot_token, is_bot_token_configured,
    wait_for_restart_signal, get_bot_token_status
)

# ===================== 全局机器人状态管理 =====================
_BOT_STATUS_LOCK = threading.Lock()
_BOT_STATUS = {
    "enabled": False,  # 延迟初始化
    "state": "pending",
    "message": "等待启动",
    "last_ok_at": None,
    "last_error_at": None,
    "last_error_type": None,
    "last_error": None,
    "conflict_retry": 0,
    "next_retry_in_seconds": None,
    "proxy_enabled": bool(PROXY_URL),
}

# ===================== 批量图片处理（media_group）=====================
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


def _format_batch_summary(
    urls: List[str],
    success_count: int,
    total_count: int,
    total_size_bytes: int,
    failure_count: int,
) -> str:
    """格式化批量上传汇总消息（自动截断以避免超过4096字符）"""
    def _human_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 / 1024:.2f} MB"

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
    lines.append(f"📦 *总大小:* {_human_size(total_size_bytes)}")
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
    from tg_imagebed.services.file_service import record_existing_telegram_file
    from tg_imagebed.utils import get_domain

    try:
        await asyncio.sleep(debounce_seconds)
    except asyncio.CancelledError:
        return

    batch = _media_group_batches.get(batch_key)
    if not batch:
        return

    # 确保是当前任务在执行
    current_task = asyncio.current_task()
    if batch.flush_task is not None and batch.flush_task is not current_task:
        return

    # 竞态校验：如果在 sleep 期间有新图片到达，重新调度
    elapsed = time.monotonic() - batch.updated_at
    if elapsed < debounce_seconds:
        # 新图片刚到达，让新的 flush_task 处理
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

            file_info = await bot.get_file(file_id)
            file_bytes = await file_info.download_as_bytearray()

            result = record_existing_telegram_file(
                file_id=file_id,
                file_unique_id=item.get("file_unique_id"),
                file_path=getattr(file_info, "file_path", "") or "",
                file_content=bytes(file_bytes),
                filename=item.get("filename", ""),
                content_type=item.get("content_type", "image/jpeg"),
                username=item.get("username", ""),
                source="telegram_group",
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
    summary_text = _format_batch_summary(
        urls, success_count, total_count, total_size_bytes, failure_count
    )

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


def _utc_iso(ts: float = None) -> str:
    """生成 UTC ISO 时间字符串"""
    if ts is None:
        ts = time.time()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _set_bot_status(**updates) -> None:
    """更新机器人状态"""
    with _BOT_STATUS_LOCK:
        _BOT_STATUS.update(updates)


def _get_bot_status() -> dict:
    """获取机器人状态"""
    with _BOT_STATUS_LOCK:
        return dict(_BOT_STATUS)

# 导入工具函数
from tg_imagebed.utils import acquire_lock, release_lock, add_cache_headers, get_static_file_version

# 导入数据库
from tg_imagebed.database import init_database, get_all_files_count, get_total_size, init_system_settings, migrate_env_settings

# 导入服务
from tg_imagebed.services.cdn_service import start_cdn_monitor, stop_cdn_monitor

# 导入 admin_module（保持兼容）
from tg_imagebed import admin_module


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__, static_folder=None)

    # 应用 ProxyFix 中间件
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # CORS 配置 - 分层策略
    # 管理员 API 需要 credentials（session cookie），必须使用明确的域名白名单
    admin_origins = ALLOWED_ORIGINS.split(',') if ALLOWED_ORIGINS != "*" else [
        "http://localhost:3000", "http://127.0.0.1:3000",
        f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"
    ]
    if ALLOWED_ORIGINS == "*":
        logger.warning("ALLOWED_ORIGINS 为 '*'，管理员 API 已限制为本地域名。生产环境请设置具体域名。")

    CORS(app, resources={
        # 管理员 API - 需要 credentials，严格限制 origins
        r"/api/admin/*": {
            "origins": admin_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "vary_header": True,
            "max_age": 3600
        },
        # 公共 API - 不需要 credentials，允许所有来源
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": False,
            "max_age": 3600
        },
        # 兼容旧的 /upload 路由
        r"/upload": {
            "origins": "*",
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
            "max_age": 3600
        },
        # 图片访问 - 公开
        r"/image/*": {
            "origins": "*",
            "methods": ["GET", "HEAD", "OPTIONS"],
            "allow_headers": ["Content-Type", "Range", "Cache-Control"],
            "expose_headers": ["Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Cache-Control"],
            "supports_credentials": False,
            "max_age": 86400
        },
        # 静态资源 - 公开
        r"/static/*": {
            "origins": "*",
            "methods": ["GET", "HEAD", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
            "max_age": 86400
        }
    })

    # 初始化数据库与系统设置（幂等操作，确保使用 create_app() 时数据库已就绪）
    # 注意：main() 函数也会调用这些初始化，但由于幂等性，重复调用不会有问题
    init_database()
    init_system_settings()
    migrate_env_settings()
    logger.debug("数据库与系统设置初始化检查完成")

    app.secret_key = SECRET_KEY

    # 配置管理员会话
    admin_module.configure_admin_session(app)

    # 注册 Jinja2 全局函数
    app.jinja_env.globals.update(get_static_file_version=get_static_file_version)

    # 注册蓝图 - 必须先导入路由模块以触发路由注册
    from tg_imagebed.api import upload_bp, images_bp, admin_bp, auth_bp
    # 导入路由模块，触发 @bp.route 装饰器执行
    from tg_imagebed.api import upload, images, admin, auth, settings, galleries

    app.register_blueprint(upload_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    # 注册 admin_module 路由（保持兼容）
    admin_module.register_admin_routes(
        app, DATABASE_PATH,
        get_all_files_count, get_total_size,
        add_cache_headers
    )

    # 机器人状态 API
    @app.get("/api/bot/status")
    def bot_status():
        """获取 Telegram 机器人状态"""
        status = _get_bot_status()
        # 公共端点：避免泄露 token 片段
        token_status = get_bot_token_status()
        status["token_config"] = {
            "configured": bool(token_status.get("configured")),
            "source": token_status.get("source"),
            "env_set": bool(token_status.get("env_set")),
        }
        return jsonify(status)

    return app


def run_flask():
    """运行 Flask 应用"""
    from tg_imagebed.utils import LOCAL_IP
    logger.info(f"Flask服务器启动在: {LOCAL_IP}:{PORT}")
    app = create_app()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)


def start_telegram_bot_thread():
    """在后台线程启动 Telegram 机器人（不影响 Flask/Web 功能）"""
    if not is_bot_token_configured():
        _set_bot_status(
            enabled=False,
            state="disabled",
            message="BOT_TOKEN 未配置，机器人将等待配置"
        )
    else:
        _set_bot_status(enabled=True, state="pending", message="等待启动")
    # 始终启动线程，让它等待配置更新
    t = threading.Thread(target=run_telegram_bot, name="telegram-bot", daemon=True)
    t.start()
    return t


def run_telegram_bot():
    """运行 Telegram 机器人（独立线程，失败不影响 Web 服务）"""
    import asyncio
    import telegram.error
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    # Telegram 处理函数
    async def start(update: Update, context):
        """处理 /start 命令"""
        from tg_imagebed.database import get_stats
        from tg_imagebed.utils import get_domain

        stats = get_stats()
        await update.message.reply_text(
            "☁️ *Telegram 云图床机器人*\n\n"
            "✨ 直接发送图片获取永久直链\n\n"
            f"🌐 *Web界面:* {get_domain(None)}\n"
            f"📊 *已存储:* {stats['total_files']} 个文件\n"
            f"💾 *总大小:* {stats['total_size'] / 1024 / 1024:.1f} MB\n\n"
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
        from tg_imagebed.services.file_service import process_upload, record_existing_telegram_file
        from tg_imagebed.utils import get_domain
        from tg_imagebed.database import get_system_setting

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
            # 检查管理员权限
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
            from tg_imagebed.utils import get_mime_type as _get_mime_type

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
                is_image = mime.startswith("image/") or any(
                    doc_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
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

            file_info = await context.bot.get_file(tg_file.file_id)
            file_bytes = await file_info.download_as_bytearray()

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
                base_url = get_domain(None)
                permanent_url = f"{base_url}/image/{result['encrypted_id']}"
                text = (
                    f"✅ *上传成功！*\n\n"
                    f"🔗 *永久直链:*\n`{permanent_url}`\n\n"
                    f"📊 *文件大小:* {result['file_size']} bytes\n"
                    f"💡 链接永久有效"
                )

                reply_msg_id = None
                if status_msg:
                    await status_msg.edit_text(text, parse_mode='Markdown')
                    reply_msg_id = status_msg.message_id
                else:
                    sent = await message.reply_text(text, parse_mode='Markdown')
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
                if status_msg:
                    await status_msg.edit_text("❌ 处理失败，请重试")
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            if status_msg:
                try:
                    await status_msg.edit_text("❌ 处理失败，请重试")
                except Exception:
                    pass

    async def start_bot():
        """异步启动机器人（带指数退避重试）"""
        # 指数退避配置
        backoff_base = 5.0  # 基础等待时间（秒）
        backoff_max = 120.0  # 最大等待时间（秒）
        status_log_interval = 30.0  # 状态日志间隔（秒）
        conflict_retry = 0
        last_status_log_ts = 0.0

        def is_409_conflict(err: BaseException) -> bool:
            """检查是否为 409 Conflict 错误"""
            if isinstance(err, telegram.error.Conflict):
                return True
            msg = str(err).lower()
            return "409" in msg and "conflict" in msg

        def log_conflict_help(retry_no: int, delay: float):
            """输出 409 冲突帮助信息"""
            logger.warning("=" * 60)
            logger.warning("Telegram 轮询出现 409 Conflict（getUpdates 冲突）")
            logger.warning("=" * 60)
            logger.warning("说明: 该 BOT_TOKEN 同一时间只能有一个 polling 实例")
            logger.warning("")
            logger.warning("常见原因:")
            logger.warning("  1. 另一个进程/容器正在运行同一个机器人")
            logger.warning("  2. 该 BOT_TOKEN 配置了 Webhook（Webhook 与 Polling 不能同时使用）")
            logger.warning("")
            logger.warning("解决方案:")
            logger.warning("  - 停止其他机器人实例/容器后再启动")
            logger.warning("  - 如曾设置 Webhook，请先删除:")
            logger.warning("    https://api.telegram.org/bot<TOKEN>/deleteWebhook")
            logger.warning("")
            logger.warning(f"当前策略: Web 服务正常运行，机器人将在 {delay:.0f} 秒后重试（第 {retry_no} 次）")
            logger.warning("=" * 60)

        def log_error_with_help(error_type: str, error: Exception, extra_info: str = ""):
            """输出错误帮助信息"""
            logger.error("=" * 60)
            logger.error(f"Telegram 机器人错误: {error_type}")
            logger.error("=" * 60)
            logger.error(f"错误详情: {error}")
            if extra_info:
                logger.error("")
                logger.error(extra_info)
            logger.error("")
            logger.error("注意: Web 服务（图床、管理后台）不受影响，仍可正常使用")
            logger.error("机器人将在稍后自动重试...")
            logger.error("=" * 60)

        _set_bot_status(state="starting", message="Telegram 机器人启动中...")

        while True:  # 主循环：持续重试，不退出
            # 获取当前有效 Token
            current_token, token_source = get_effective_bot_token()
            if not current_token:
                _set_bot_status(
                    enabled=False,
                    state="disabled",
                    message="BOT_TOKEN 未配置",
                )
                # 等待配置更新或重启信号（可响应管理员配置 Token 后重启）
                if await asyncio.to_thread(wait_for_restart_signal, 10.0):
                    logger.info("收到重启信号，检查配置...")
                continue

            _set_bot_status(enabled=True)
            telegram_app = None
            restart_watcher_task = None
            admin_restart_event = asyncio.Event()

            try:
                # 构建 Application
                builder = Application.builder().token(current_token).job_queue(None)
                if PROXY_URL:
                    logger.info(f"Telegram Bot 使用代理: {PROXY_URL}")
                    builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)

                telegram_app = builder.build()

                # 管理端热重启监听器
                async def restart_watcher():
                    while True:
                        if await asyncio.to_thread(wait_for_restart_signal, 1.0):
                            admin_restart_event.set()
                            break

                restart_watcher_task = asyncio.create_task(restart_watcher())

                # 用于触发 polling 重启的事件
                restart_polling_event = asyncio.Event()

                def polling_error_callback(err: BaseException) -> None:
                    """轮询错误回调"""
                    nonlocal conflict_retry, last_status_log_ts

                    if is_409_conflict(err):
                        _set_bot_status(
                            state="conflict",
                            message="检测到 getUpdates 冲突，轮询将退避后重试",
                            last_error_type=type(err).__name__,
                            last_error=str(err),
                            last_error_at=_utc_iso(),
                        )
                        if not restart_polling_event.is_set():
                            restart_polling_event.set()
                        return

                    # 非 409 错误：记录但继续
                    _set_bot_status(
                        last_error_type=type(err).__name__,
                        last_error=str(err),
                        last_error_at=_utc_iso(),
                    )
                    now = time.time()
                    if now - last_status_log_ts >= status_log_interval:
                        last_status_log_ts = now
                        logger.error(f"Telegram 轮询错误: {type(err).__name__}: {err}")

                async def application_error_handler(update, context) -> None:
                    """应用级错误处理器"""
                    err = getattr(context, "error", None)
                    if err:
                        polling_error_callback(err)

                # 添加处理器
                telegram_app.add_handler(CommandHandler("start", start))
                telegram_app.add_handler(MessageHandler(
                    filters.PHOTO | filters.Document.ALL,
                    handle_photo
                ))
                telegram_app.add_error_handler(application_error_handler)

                logger.info("Telegram 机器人启动中...")
                bot_info = await telegram_app.bot.get_me()
                logger.info(f"机器人信息: @{bot_info.username} (ID: {bot_info.id})")

                await telegram_app.initialize()
                await telegram_app.start()

                # Polling 循环（遇到 409 冲突时退避重试）
                while True:
                    try:
                        await telegram_app.updater.start_polling(
                            drop_pending_updates=True,
                            error_callback=polling_error_callback
                        )
                        conflict_retry = 0
                        _set_bot_status(
                            state="running",
                            message="Telegram 机器人运行中",
                            last_ok_at=_utc_iso(),
                            conflict_retry=0,
                            next_retry_in_seconds=None,
                        )
                        logger.info("Telegram 机器人已成功启动（polling）")

                        # 等待（1）冲突触发的重启请求，（2）管理员手动重启请求
                        wait_conflict = asyncio.create_task(restart_polling_event.wait())
                        wait_admin = asyncio.create_task(admin_restart_event.wait())
                        done, pending = await asyncio.wait(
                            {wait_conflict, wait_admin},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in pending:
                            task.cancel()

                        if wait_admin in done:
                            # 管理员请求重启，退出内层循环重建 Application
                            logger.info("收到管理员重启请求，重新加载配置...")
                            _set_bot_status(
                                state="restarting",
                                message="收到重启请求，重新加载配置...",
                            )
                            break

                        restart_polling_event.clear()

                    except telegram.error.Conflict:
                        if not restart_polling_event.is_set():
                            restart_polling_event.set()

                    # 处理冲突：退避重试
                    conflict_retry += 1
                    delay = min(backoff_base * (2 ** (conflict_retry - 1)), backoff_max)
                    _set_bot_status(
                        state="conflict",
                        message=f"getUpdates 冲突，{delay:.0f} 秒后重试（第 {conflict_retry} 次）",
                        conflict_retry=conflict_retry,
                        next_retry_in_seconds=delay,
                    )
                    log_conflict_help(conflict_retry, delay)

                    try:
                        await telegram_app.updater.stop()
                    except Exception:
                        pass

                    # 等待退避时间
                    await asyncio.sleep(delay)

            except telegram.error.InvalidToken as e:
                _set_bot_status(
                    state="fatal",
                    message="BOT_TOKEN 无效，等待重新配置",
                    last_error_type=type(e).__name__,
                    last_error=str(e),
                    last_error_at=_utc_iso(),
                )
                log_error_with_help(
                    "Token 无效",
                    e,
                    "解决方案:\n"
                    "  1. 在管理后台 > Telegram 设置中更新 Token\n"
                    "  2. 确认 Token 没有多余的空格或换行符\n"
                    "  3. 在 @BotFather 中重新生成 Token\n"
                    "  4. 更新后点击\"重启机器人\"按钮"
                )
                # DB 管理场景：等待管理员更新 token 后通过"重启"恢复
                await asyncio.to_thread(wait_for_restart_signal, 3600.0)
                continue

            except telegram.error.TimedOut as e:
                _set_bot_status(
                    state="error",
                    message="连接 Telegram 超时，稍后重试",
                    last_error_type=type(e).__name__,
                    last_error=str(e),
                    last_error_at=_utc_iso(),
                )
                log_error_with_help(
                    "连接超时",
                    e,
                    f"可能原因:\n"
                    f"  - 网络连接问题\n"
                    f"  - 代理配置: {PROXY_URL if PROXY_URL else '未配置'}\n"
                    f"  - 如在中国大陆，需配置代理访问 Telegram"
                )
                await asyncio.sleep(30)  # 超时后等待 30 秒重试

            except telegram.error.NetworkError as e:
                _set_bot_status(
                    state="error",
                    message="网络错误，稍后重试",
                    last_error_type=type(e).__name__,
                    last_error=str(e),
                    last_error_at=_utc_iso(),
                )
                log_error_with_help(
                    "网络错误",
                    e,
                    f"可能原因:\n"
                    f"  - 网络连接不稳定\n"
                    f"  - 防火墙阻止连接\n"
                    f"  - 代理配置: {PROXY_URL if PROXY_URL else '未配置'}"
                )
                await asyncio.sleep(30)

            except Exception as e:
                _set_bot_status(
                    state="error",
                    message=f"机器人异常: {type(e).__name__}",
                    last_error_type=type(e).__name__,
                    last_error=str(e),
                    last_error_at=_utc_iso(),
                )
                import traceback
                logger.error("=" * 60)
                logger.error(f"Telegram 机器人异常: {type(e).__name__}")
                logger.error("=" * 60)
                logger.error(f"错误详情: {e}")
                logger.error("堆栈跟踪:")
                logger.error(traceback.format_exc())
                logger.error("")
                logger.error("注意: Web 服务不受影响，机器人将在 30 秒后重试")
                logger.error("=" * 60)
                await asyncio.sleep(30)

            finally:
                # 清理资源
                if restart_watcher_task:
                    restart_watcher_task.cancel()
                    try:
                        await restart_watcher_task
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass

                if telegram_app:
                    try:
                        await telegram_app.updater.stop()
                    except Exception:
                        pass
                    try:
                        await telegram_app.stop()
                    except Exception:
                        pass
                    try:
                        await telegram_app.shutdown()
                    except Exception:
                        pass

    # 线程入口：保证异常不会影响 Flask/Web 服务
    while True:
        try:
            asyncio.run(start_bot())
            return
        except Exception as e:
            _set_bot_status(
                state="error",
                message="Telegram 线程异常，5 秒后重试",
                last_error_type=type(e).__name__,
                last_error=str(e),
                last_error_at=_utc_iso(),
            )
            logger.error(f"Telegram 线程异常: {type(e).__name__}: {e}")
            logger.error("Web 服务不受影响，5 秒后重试...")
            time.sleep(5)


def main():
    """主函数"""
    # 检查是否已有实例在运行
    if not acquire_lock():
        logger.error("程序已在运行中，请勿重复启动")
        sys.exit(1)

    # 打印配置信息
    print_config_info()

    # 初始化数据库
    init_database()

    # 初始化系统设置
    init_system_settings()

    # 迁移环境变量配置到数据库
    migrate_env_settings()

    # 启动 CDN 监控（由 start_cdn_monitor 内部判断是否启用）
    start_cdn_monitor()

    logger.info("启动Telegram云图床服务...")

    # 检查前端静态文件
    import os
    if not os.path.exists(STATIC_FOLDER):
        logger.warning("=" * 60)
        logger.warning("前端静态文件未找到！")
        logger.warning("请运行以下命令构建前端：")
        logger.warning("  cd frontend && npm run generate")
        logger.warning("=" * 60)
    else:
        logger.info(f"前端静态文件已就绪: {STATIC_FOLDER}")

    # 启动 Flask 线程
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logger.info("前端已内置到Flask中，统一端口服务")

    time.sleep(2)

    # Telegram 机器人独立线程运行：失败不影响 Web 服务
    bot_thread = start_telegram_bot_thread()
    if not is_bot_token_configured():
        logger.warning("=" * 60)
        logger.warning("Telegram 机器人等待配置（BOT_TOKEN 未设置）")
        logger.warning("可通过管理后台 > Telegram 设置进行配置")
        logger.warning("Web 服务（图床、管理后台）仍可正常使用")
        logger.warning("=" * 60)

    try:
        # 主线程保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
    finally:
        stop_cdn_monitor()
        release_lock()
        logger.info("服务已停止")


if __name__ == '__main__':
    main()
