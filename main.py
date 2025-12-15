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

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置
from tg_imagebed.config import (
    PORT, SECRET_KEY, ALLOWED_ORIGINS, DATABASE_PATH,
    CDN_ENABLED, CLOUDFLARE_CDN_DOMAIN, CDN_MONITOR_ENABLED,
    BOT_TOKEN, STATIC_FOLDER,
    logger, print_config_info
)

# 导入工具函数
from tg_imagebed.utils import acquire_lock, release_lock, add_cache_headers, get_static_file_version

# 导入数据库
from tg_imagebed.database import init_database, get_all_files_count, get_total_size, init_system_settings

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

    return app


def run_flask():
    """运行 Flask 应用"""
    from tg_imagebed.utils import LOCAL_IP
    logger.info(f"Flask服务器启动在: {LOCAL_IP}:{PORT}")
    app = create_app()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)


def run_telegram_bot():
    """运行 Telegram 机器人"""
    import asyncio
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    from tg_imagebed.config import STORAGE_CHAT_ID, ENABLE_GROUP_UPLOAD

    # Telegram 处理函数（简化版，完整版应放在 services/telegram_service.py）
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
            # 获取图片
            if update.message.photo:
                photo = update.message.photo[-1]
                file_info = await context.bot.get_file(photo.file_id)

                # 下载图片
                file_bytes = await file_info.download_as_bytearray()

                # 处理上传
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
        """异步启动机器人"""
        try:
            # 禁用 job_queue 以解决 Python 3.13 兼容性问题
            telegram_app = Application.builder().token(BOT_TOKEN).job_queue(None).build()

            # 添加处理器
            telegram_app.add_handler(CommandHandler("start", start))
            telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

            logger.info("Telegram机器人启动中...")

            bot_info = await telegram_app.bot.get_me()
            logger.info(f"机器人信息: @{bot_info.username} (ID: {bot_info.id})")

            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling(drop_pending_updates=True)

            logger.info("Telegram机器人已成功启动")

            await asyncio.Event().wait()

        except Exception as e:
            logger.error(f"Telegram机器人启动失败: {e}")
            import traceback
            traceback.print_exc()

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Telegram机器人收到停止信号")
    except Exception as e:
        logger.error(f"运行Telegram机器人时发生错误: {e}")


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

    try:
        if BOT_TOKEN:
            run_telegram_bot()
        else:
            logger.warning("Telegram机器人未启动，请配置Token后重启")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("服务已停止")
    finally:
        stop_cdn_monitor()
        release_lock()


if __name__ == '__main__':
    main()
