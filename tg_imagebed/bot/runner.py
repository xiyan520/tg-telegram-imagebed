#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 主循环模块

包含 Telegram 机器人的启动、轮询/Webhook 双模式、重试和线程管理逻辑。
"""
import asyncio
import threading
import time

from ..config import get_proxy_url, logger
from ..bot_control import (
    get_effective_bot_token,
    is_bot_token_configured,
    wait_for_restart_signal,
    consume_last_restart_reason,
    build_webhook_url,
)
from ..database import get_system_setting
from .state import (
    _set_bot_status,
    _utc_iso,
    set_bot_instance,
    set_bot_loop,
    set_bot_application,
    _set_queue_depth,
)
from .handlers import start, handle_photo, handle_verify_text
from .commands import (
    help_command,
    myuploads_command,
    delete_command,
    id_command,
    callback_handler,
    login_command,
    mytokens_command,
    settoken_command,
)


def _get_update_mode() -> str:
    """读取 Bot 更新模式"""
    mode = str(get_system_setting("bot_update_mode") or "polling").strip().lower()
    return mode if mode in ("polling", "webhook") else "polling"


def _get_webhook_base_url() -> str:
    """读取 Bot webhook 基础 URL（不含路径）"""
    return str(get_system_setting("bot_webhook_url") or "").strip()


def _register_handlers(telegram_app):
    """统一注册 Bot 处理器"""
    from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("id", id_command))
    telegram_app.add_handler(CommandHandler("myuploads", myuploads_command))
    telegram_app.add_handler(CommandHandler("delete", delete_command))
    telegram_app.add_handler(CommandHandler("login", login_command))
    telegram_app.add_handler(CommandHandler("mytokens", mytokens_command))
    telegram_app.add_handler(CommandHandler("settoken", settoken_command))
    telegram_app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        handle_photo
    ))
    telegram_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_verify_text
    ))
    telegram_app.add_handler(CallbackQueryHandler(callback_handler))


async def _register_command_menu(bot):
    """注册 Bot 命令菜单"""
    from telegram import BotCommand

    await bot.set_my_commands([
        BotCommand("start", "查看机器人状态和统计"),
        BotCommand("help", "显示所有可用命令"),
        BotCommand("id", "查看你的 Telegram ID"),
        BotCommand("myuploads", "查看个人上传历史"),
        BotCommand("delete", "删除你上传的图片"),
        BotCommand("login", "获取 Web 端登录链接"),
        BotCommand("mytokens", "查看我的 Token"),
        BotCommand("settoken", "设置默认上传 Token"),
    ])


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

    t = threading.Thread(target=run_telegram_bot, name="telegram-bot", daemon=True)
    t.start()
    return t


def run_telegram_bot():
    """运行 Telegram 机器人（独立线程，失败不影响 Web 服务）"""
    import telegram.error
    from telegram import Update
    from telegram.ext import Application

    async def start_bot():
        """异步启动机器人（带指数退避重试）"""
        backoff_base = 5.0
        backoff_max = 120.0
        status_log_interval = 30.0
        conflict_retry = 0
        last_status_log_ts = 0.0

        def is_409_conflict(err: BaseException) -> bool:
            if isinstance(err, telegram.error.Conflict):
                return True
            msg = str(err).lower()
            return "409" in msg and "conflict" in msg

        def log_conflict_help(retry_no: int, delay: float):
            logger.warning(
                f"[409 Conflict] getUpdates 冲突 | "
                f"原因: 同一 Token 存在多个 polling 实例或残留 Webhook | "
                f"策略: {delay:.0f}s 后重试（第 {retry_no} 次）"
            )

        def log_error_with_help(error_type: str, error: Exception, extra_info: str = ""):
            extra_oneline = extra_info.replace("\n", " | ").strip() if extra_info else ""
            logger.error(
                f"[Bot Error] {error_type} | {error}"
                f"{' | ' + extra_oneline if extra_oneline else ''}"
                f" | Web 服务不受影响，机器人将自动重试"
            )

        _set_bot_status(state="starting", message="Telegram 机器人启动中...")

        while True:
            current_token, _token_source = get_effective_bot_token()
            if not current_token:
                _set_bot_status(
                    enabled=False,
                    state="disabled",
                    message="BOT_TOKEN 未配置",
                    webhook_status={
                        "enabled": False,
                        "url": None,
                        "last_set_at": None,
                        "last_error": None,
                    },
                )
                if await asyncio.to_thread(wait_for_restart_signal, 10.0):
                    logger.info("收到重启信号，检查配置...")
                continue

            update_mode = _get_update_mode()
            webhook_base_url = _get_webhook_base_url()

            _set_bot_status(
                enabled=True,
                update_mode=update_mode,
                webhook_status={
                    "enabled": False,
                    "url": None,
                    "last_set_at": None,
                    "last_error": None,
                },
            )
            _set_queue_depth(0)

            telegram_app = None
            restart_watcher_task = None
            admin_restart_event = asyncio.Event()

            try:
                builder = Application.builder().token(current_token).job_queue(None)
                proxy_url = get_proxy_url()
                if proxy_url:
                    logger.info(f"Telegram Bot 使用代理: {proxy_url}")
                    builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)

                telegram_app = builder.build()

                async def restart_watcher():
                    while True:
                        if await asyncio.to_thread(wait_for_restart_signal, 1.0):
                            admin_restart_event.set()
                            break

                restart_watcher_task = asyncio.create_task(restart_watcher())

                def common_error_callback(err: BaseException) -> None:
                    nonlocal last_status_log_ts
                    _set_bot_status(
                        last_error_type=type(err).__name__,
                        last_error=str(err),
                        last_error_at=_utc_iso(),
                    )
                    now = time.time()
                    if now - last_status_log_ts >= status_log_interval:
                        last_status_log_ts = now
                        logger.error(f"Telegram 错误: {type(err).__name__}: {err}")

                async def application_error_handler(update, context) -> None:
                    err = getattr(context, "error", None)
                    if err:
                        common_error_callback(err)

                _register_handlers(telegram_app)
                telegram_app.add_error_handler(application_error_handler)

                logger.info("Telegram 机器人启动中...")
                bot_info = await telegram_app.bot.get_me()
                logger.info(f"机器人信息: @{bot_info.username} (ID: {bot_info.id})")

                set_bot_instance(telegram_app.bot)
                set_bot_loop(asyncio.get_running_loop())
                set_bot_application(telegram_app)

                await _register_command_menu(telegram_app.bot)
                logger.info("Bot 命令菜单已注册")

                await telegram_app.initialize()
                await telegram_app.start()

                if update_mode == "webhook":
                    webhook_url = build_webhook_url(webhook_base_url, current_token)
                    if not webhook_url:
                        raise ValueError("webhook 模式需要配置 bot_webhook_url")

                    await telegram_app.bot.set_webhook(
                        url=webhook_url,
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=True,
                    )

                    _set_bot_status(
                        state="running",
                        message="Telegram 机器人运行中（webhook）",
                        last_ok_at=_utc_iso(),
                        conflict_retry=0,
                        next_retry_in_seconds=None,
                        webhook_status={
                            "enabled": True,
                            "url": webhook_url,
                            "last_set_at": _utc_iso(),
                            "last_error": None,
                        },
                    )
                    logger.info(f"Telegram 机器人已成功启动（webhook）: {webhook_url}")

                    while True:
                        if admin_restart_event.is_set():
                            reason = consume_last_restart_reason()
                            logger.info(f"收到管理员重启请求，重新加载配置... reason={reason}")
                            _set_bot_status(
                                state="restarting",
                                message="收到重启请求，重新加载配置...",
                                last_restart_reason=reason,
                            )
                            break
                        try:
                            _set_queue_depth(telegram_app.update_queue.qsize())
                        except Exception:
                            pass
                        await asyncio.sleep(2)
                else:
                    try:
                        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
                    except Exception as e:
                        logger.debug(f"启动 polling 前 deleteWebhook 失败（可忽略）: {e}")

                    restart_polling_event = asyncio.Event()

                    def polling_error_callback(err: BaseException) -> None:
                        nonlocal conflict_retry

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

                        common_error_callback(err)

                    while True:
                        try:
                            await telegram_app.updater.start_polling(
                                drop_pending_updates=True,
                                allowed_updates=Update.ALL_TYPES,
                                error_callback=polling_error_callback
                            )
                            conflict_retry = 0
                            _set_bot_status(
                                state="running",
                                message="Telegram 机器人运行中（polling）",
                                last_ok_at=_utc_iso(),
                                conflict_retry=0,
                                next_retry_in_seconds=None,
                                webhook_status={
                                    "enabled": False,
                                    "url": None,
                                    "last_set_at": None,
                                    "last_error": None,
                                },
                            )
                            logger.info("Telegram 机器人已成功启动（polling）")

                            wait_conflict = asyncio.create_task(restart_polling_event.wait())
                            wait_admin = asyncio.create_task(admin_restart_event.wait())
                            done, pending = await asyncio.wait(
                                {wait_conflict, wait_admin},
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                            for task in pending:
                                task.cancel()

                            if wait_admin in done:
                                reason = consume_last_restart_reason()
                                logger.info(f"收到管理员重启请求，重新加载配置... reason={reason}")
                                _set_bot_status(
                                    state="restarting",
                                    message="收到重启请求，重新加载配置...",
                                    last_restart_reason=reason,
                                )
                                break

                            restart_polling_event.clear()
                        except telegram.error.Conflict:
                            if not restart_polling_event.is_set():
                                restart_polling_event.set()

                        conflict_retry += 1
                        delay = min(backoff_base * (2 ** (conflict_retry - 1)), backoff_max)

                        if conflict_retry == 1:
                            try:
                                logger.info("首次 409 冲突，尝试自动 deleteWebhook...")
                                await telegram_app.bot.delete_webhook(drop_pending_updates=True)
                                logger.info("deleteWebhook 成功，将立即重试 polling")
                                delay = 1.0
                            except Exception as wh_err:
                                logger.warning(f"deleteWebhook 失败: {wh_err}")

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
                    f"  - 代理配置: {get_proxy_url() or '未配置'}\n"
                    f"  - 如在中国大陆，需配置代理访问 Telegram"
                )
                await asyncio.sleep(30)

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
                    f"  - 代理配置: {get_proxy_url() or '未配置'}"
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
                logger.error(
                    f"[Bot Fatal] {type(e).__name__}: {e} | "
                    f"Web 服务不受影响，30s 后重试"
                )
                await asyncio.sleep(30)

            finally:
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
                        if update_mode == "webhook":
                            await telegram_app.bot.delete_webhook(drop_pending_updates=False)
                    except Exception:
                        pass
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

                set_bot_instance(None)
                set_bot_loop(None)
                set_bot_application(None)
                _set_queue_depth(0)

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
