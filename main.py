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
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置
from tg_imagebed.config import (
    PORT, SECRET_KEY, ALLOWED_ORIGINS, DATABASE_PATH,
    CDN_ENABLED, CLOUDFLARE_CDN_DOMAIN, CDN_MONITOR_ENABLED,
    BOT_TOKEN, PROXY_URL, STATIC_FOLDER,
    logger, print_config_info
)

# ===================== 全局机器人状态管理 =====================
_BOT_STATUS_LOCK = threading.Lock()
_BOT_STATUS = {
    "enabled": bool(BOT_TOKEN),
    "state": "disabled" if not BOT_TOKEN else "pending",
    "message": "BOT_TOKEN 未配置" if not BOT_TOKEN else "等待启动",
    "last_ok_at": None,
    "last_error_at": None,
    "last_error_type": None,
    "last_error": None,
    "conflict_retry": 0,
    "next_retry_in_seconds": None,
    "proxy_enabled": bool(PROXY_URL),
}


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
    from tg_imagebed.api import upload, images, admin, auth, settings

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
        return jsonify(_get_bot_status())

    return app


def run_flask():
    """运行 Flask 应用"""
    from tg_imagebed.utils import LOCAL_IP
    logger.info(f"Flask服务器启动在: {LOCAL_IP}:{PORT}")
    app = create_app()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)


def start_telegram_bot_thread():
    """在后台线程启动 Telegram 机器人（不影响 Flask/Web 功能）"""
    if not BOT_TOKEN:
        _set_bot_status(state="disabled", message="BOT_TOKEN 未配置，Telegram 机器人未启动")
        return None
    t = threading.Thread(target=run_telegram_bot, name="telegram-bot", daemon=True)
    t.start()
    return t


def run_telegram_bot():
    """运行 Telegram 机器人（独立线程，失败不影响 Web 服务）"""
    import asyncio
    import telegram.error
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    from tg_imagebed.config import STORAGE_CHAT_ID, ENABLE_GROUP_UPLOAD

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

    async def handle_photo(update: Update, context):
        """处理图片上传"""
        from tg_imagebed.services.file_service import process_upload
        from tg_imagebed.utils import get_domain

        user_id = update.effective_user.id
        username = update.effective_user.username or "未知用户"

        msg = await update.message.reply_text("⏳ 正在处理图片...")

        try:
            if update.message.photo:
                photo = update.message.photo[-1]
                file_info = await context.bot.get_file(photo.file_id)
                file_bytes = await file_info.download_as_bytearray()

                result = process_upload(
                    file_content=bytes(file_bytes),
                    filename=f"telegram_{photo.file_id[:12]}.jpg",
                    content_type='image/jpeg',
                    username=username,
                    source='telegram_bot'
                )

                if result:
                    base_url = get_domain(None)
                    permanent_url = f"{base_url}/image/{result['encrypted_id']}"
                    await msg.edit_text(
                        f"✅ *上传成功！*\n\n"
                        f"🔗 *永久直链:*\n`{permanent_url}`\n\n"
                        f"📊 *文件大小:* {result['file_size']} bytes\n"
                        f"💡 链接永久有效",
                        parse_mode='Markdown'
                    )
                else:
                    await msg.edit_text("❌ 处理失败，请重试")
            else:
                await msg.edit_text("❌ 请发送图片文件")
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await msg.edit_text("❌ 处理失败，请重试")

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
            try:
                # 构建 Application
                builder = Application.builder().token(BOT_TOKEN).job_queue(None)
                if PROXY_URL:
                    logger.info(f"Telegram Bot 使用代理: {PROXY_URL}")
                    builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)

                telegram_app = builder.build()

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
                telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
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

                        # 等待冲突触发的重启请求
                        await restart_polling_event.wait()
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
                    message="BOT_TOKEN 无效，机器人无法启动",
                    last_error_type=type(e).__name__,
                    last_error=str(e),
                    last_error_at=_utc_iso(),
                )
                log_error_with_help(
                    "Token 无效",
                    e,
                    "解决方案:\n"
                    "  1. 检查 .env 文件中的 BOT_TOKEN 是否正确\n"
                    "  2. 确认 Token 没有多余的空格或换行符\n"
                    "  3. 在 @BotFather 中重新生成 Token"
                )
                # Token 无效是致命错误，不重试
                return

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

    # 启动 CDN 监控
    if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN and CDN_MONITOR_ENABLED:
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
    if not bot_thread:
        logger.warning("=" * 60)
        logger.warning("Telegram 机器人未启动（BOT_TOKEN 未配置）")
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
