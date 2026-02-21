#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 主循环模块

包含 Telegram 机器人的启动、轮询、重试和线程管理逻辑。
"""
import asyncio
import threading
import time

from ..config import get_proxy_url, logger
from ..bot_control import (
    get_effective_bot_token, is_bot_token_configured, wait_for_restart_signal
)
from .state import _set_bot_status, _get_bot_status, _utc_iso
from .handlers import start, handle_photo
from .commands import help_command, myuploads_command, delete_command, id_command, callback_handler


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
    import telegram.error
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

    async def start_bot():
        """异步启动机器人（带指数退避重试）"""
        # 指数退避配置
        backoff_base = 5.0
        backoff_max = 120.0
        status_log_interval = 30.0
        conflict_retry = 0
        last_status_log_ts = 0.0

        def is_409_conflict(err: BaseException) -> bool:
            """检查是否为 409 Conflict 错误"""
            if isinstance(err, telegram.error.Conflict):
                return True
            msg = str(err).lower()
            return "409" in msg and "conflict" in msg

        def log_conflict_help(retry_no: int, delay: float):
            """输出 409 冲突帮助信息（结构化单行）"""
            logger.warning(
                f"[409 Conflict] getUpdates 冲突 | "
                f"原因: 同一 Token 存在多个 polling 实例或残留 Webhook | "
                f"策略: {delay:.0f}s 后重试（第 {retry_no} 次）"
            )

        def log_error_with_help(error_type: str, error: Exception, extra_info: str = ""):
            """输出错误帮助信息（结构化单行）"""
            extra_oneline = extra_info.replace('\n', ' | ').strip() if extra_info else ""
            logger.error(
                f"[Bot Error] {error_type} | {error}"
                f"{' | ' + extra_oneline if extra_oneline else ''}"
                f" | Web 服务不受影响，机器人将自动重试"
            )
        # PLACEHOLDER_RUNNER_MAIN_LOOP

        _set_bot_status(state="starting", message="Telegram 机器人启动中...")

        while True:  # 主循环：持续重试，不退出
            current_token, token_source = get_effective_bot_token()
            if not current_token:
                _set_bot_status(
                    enabled=False,
                    state="disabled",
                    message="BOT_TOKEN 未配置",
                )
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
                proxy_url = get_proxy_url()
                if proxy_url:
                    logger.info(f"Telegram Bot 使用代理: {proxy_url}")
                    builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)

                telegram_app = builder.build()

                # 管理端热重启监听器
                async def restart_watcher():
                    while True:
                        if await asyncio.to_thread(wait_for_restart_signal, 1.0):
                            admin_restart_event.set()
                            break

                restart_watcher_task = asyncio.create_task(restart_watcher())
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
                telegram_app.add_handler(CommandHandler("help", help_command))
                telegram_app.add_handler(CommandHandler("id", id_command))
                telegram_app.add_handler(CommandHandler("myuploads", myuploads_command))
                telegram_app.add_handler(CommandHandler("delete", delete_command))
                telegram_app.add_handler(MessageHandler(
                    filters.PHOTO | filters.Document.ALL,
                    handle_photo
                ))
                telegram_app.add_handler(CallbackQueryHandler(callback_handler))
                telegram_app.add_error_handler(application_error_handler)

                logger.info("Telegram 机器人启动中...")
                bot_info = await telegram_app.bot.get_me()
                logger.info(f"机器人信息: @{bot_info.username} (ID: {bot_info.id})")

                # 注册命令菜单（让 Telegram 客户端显示命令提示）
                from telegram import BotCommand
                await telegram_app.bot.set_my_commands([
                    BotCommand("start", "查看机器人状态和统计"),
                    BotCommand("help", "显示所有可用命令"),
                    BotCommand("id", "查看你的 Telegram ID"),
                    BotCommand("myuploads", "查看个人上传历史"),
                    BotCommand("delete", "删除你上传的图片"),
                ])
                logger.info("Bot 命令菜单已注册")

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

                        wait_conflict = asyncio.create_task(restart_polling_event.wait())
                        wait_admin = asyncio.create_task(admin_restart_event.wait())
                        done, pending = await asyncio.wait(
                            {wait_conflict, wait_admin},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in pending:
                            task.cancel()

                        if wait_admin in done:
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

                    # 首次冲突时尝试自动删除 Webhook
                    if conflict_retry == 1:
                        try:
                            logger.info("首次 409 冲突，尝试自动 deleteWebhook...")
                            await telegram_app.bot.delete_webhook(drop_pending_updates=True)
                            logger.info("deleteWebhook 成功，将立即重试 polling")
                            delay = 1.0  # 成功删除后缩短等待时间
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
                import traceback
                logger.error(
                    f"[Bot Fatal] {type(e).__name__}: {e} | "
                    f"Web 服务不受影响，30s 后重试"
                )
                logger.debug(f"堆栈跟踪:\n{traceback.format_exc()}")
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
