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
import signal
import threading

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置
from tg_imagebed.config import (
    PORT, SECRET_KEY, ALLOWED_ORIGINS, DATABASE_PATH,
    STATIC_FOLDER,
    logger
)

# 导入 Bot 控制模块
from tg_imagebed.bot_control import (
    is_bot_token_configured, get_bot_token_status
)

# Bot 模块（状态管理 + 启动入口）
from tg_imagebed.bot import start_telegram_bot_thread, _get_bot_status

# 导入工具函数
from tg_imagebed.utils import acquire_lock, release_lock, add_cache_headers, get_static_file_version

# 导入数据库
from tg_imagebed.database import init_database, get_all_files_count, get_total_size, init_system_settings

# 导入服务
from tg_imagebed.services.cdn_service import start_cdn_monitor, stop_cdn_monitor

# 导入 admin_module（保持兼容）
from tg_imagebed import admin_module

# 全局关闭信号，供各线程检测退出
shutdown_event = threading.Event()


def _graceful_shutdown(signum, frame):
    """SIGTERM / SIGINT 信号处理器，触发优雅关闭"""
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(f"收到 {sig_name} 信号，正在优雅关闭...")
    shutdown_event.set()


# 注册信号处理器（Windows 不支持 SIGTERM，用 try/except 兼容）
signal.signal(signal.SIGINT, _graceful_shutdown)
try:
    signal.signal(signal.SIGTERM, _graceful_shutdown)
except (OSError, AttributeError):
    pass  # Windows 下 SIGTERM 不可用，忽略


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
        # TG 认证 API - 需要 credentials（tg_session cookie）
        r"/api/auth/tg/*": {
            "origins": admin_origins,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "vary_header": True,
            "max_age": 3600
        },
        # Token 生成 API - 需要 credentials（TG 绑定时读取 tg_session cookie）
        r"/api/auth/token/generate": {
            "origins": admin_origins,
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "vary_header": True,
            "max_age": 3600
        },
        # 画集认证 API - 需要 credentials（Bearer Token + 可能的 Cookie）
        r"/api/auth/galleries/*": {
            "origins": admin_origins,
            "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "vary_header": True,
            "max_age": 3600
        },
        # 公开分享 API - 需要 credentials（解锁 Cookie）
        r"/api/shared/*": {
            "origins": admin_origins,
            "methods": ["GET", "POST", "OPTIONS"],
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

    # 初始化数据库与系统设置（幂等操作，main() 已初始化过，此处确保独立使用 create_app() 时也能就绪）
    init_database(quiet=True)
    init_system_settings()
    logger.debug("数据库与系统设置初始化检查完成")

    app.secret_key = SECRET_KEY

    # 设置 Flask 请求体大小上限（防止超大请求耗尽内存）
    # 动态读取系统设置，回退到 100MB 硬上限
    try:
        from tg_imagebed.database import get_system_setting_int
        max_mb = get_system_setting_int('max_file_size_mb', 20, minimum=1, maximum=1024)
    except Exception:
        max_mb = 20
    # 额外留 2MB 余量给表单字段和 multipart 边界
    app.config['MAX_CONTENT_LENGTH'] = (max_mb + 2) * 1024 * 1024

    # 配置管理员会话
    admin_module.configure_admin_session(app)

    # 注册 Jinja2 全局函数
    app.jinja_env.globals.update(get_static_file_version=get_static_file_version)

    # 注册蓝图 - 必须先导入路由模块以触发路由注册
    from tg_imagebed.api import upload_bp, images_bp, admin_bp, auth_bp, gallery_site_bp
    # 导入路由模块，触发 @bp.route 装饰器执行
    from tg_imagebed.api import upload, images, admin, auth, settings, galleries, tg_auth, gallery_site

    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(gallery_site_bp)
    # images_bp 必须最后注册，因为它包含 /<path:path> catch-all 路由
    app.register_blueprint(images_bp)

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
        }
        return jsonify(status)

    return app


def run_flask():
    """运行 Flask 应用（waitress 生产服务器）"""
    from waitress import serve
    from tg_imagebed.utils import LOCAL_IP
    logger.info(f"Flask服务器启动在: {LOCAL_IP}:{PORT} (waitress)")
    app = create_app()
    serve(app, host='0.0.0.0', port=PORT, threads=4)


def main():
    """主函数"""
    # 检查是否已有实例在运行
    if not acquire_lock():
        logger.error("程序已在运行中，请勿重复启动")
        sys.exit(1)

    # 初始化数据库
    init_database()

    # 初始化系统设置
    init_system_settings()

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

    # 等待 Flask 就绪（健康检查轮询，最多等待 10 秒）
    import urllib.request
    _health_url = f"http://127.0.0.1:{PORT}/api/health"
    for _i in range(20):
        try:
            urllib.request.urlopen(_health_url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        logger.warning("Flask 健康检查超时，继续启动 Bot 线程")

    # Telegram 机器人独立线程运行：失败不影响 Web 服务
    bot_thread = start_telegram_bot_thread()
    if not is_bot_token_configured():
        logger.warning("=" * 60)
        logger.warning("Telegram 机器人等待配置（BOT_TOKEN 未设置）")
        logger.warning("可通过管理后台 > Telegram 设置进行配置")
        logger.warning("Web 服务（图床、管理后台）仍可正常使用")
        logger.warning("=" * 60)

    try:
        # 主线程等待关闭信号（SIGTERM / SIGINT / KeyboardInterrupt）
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1)
    except KeyboardInterrupt:
        logger.info("收到 KeyboardInterrupt，正在关闭服务...")
        shutdown_event.set()
    finally:
        stop_cdn_monitor()
        release_lock()
        logger.info("服务已停止")


if __name__ == '__main__':
    main()
