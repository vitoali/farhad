"""نقطه ورود: python -m bot"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from aiohttp import web
from telegram.ext import Application

from bot.config import load_settings
from bot.db import Database
from bot.handlers import register_handlers
from bot.webhook import create_webhook_app

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")


async def run() -> None:
    settings = load_settings()
    db = Database(settings.database_path)

    tg_app = Application.builder().token(settings.bot_token).build()
    tg_app.bot_data["db"] = db
    tg_app.bot_data["settings"] = settings
    register_handlers(tg_app)

    webhook_app = create_webhook_app(tg_app)
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webhook_host, settings.webhook_port)

    await tg_app.initialize()
    await tg_app.start()
    assert tg_app.updater is not None
    await tg_app.updater.start_polling(drop_pending_updates=True)
    await site.start()

    me = await tg_app.bot.get_me()
    logger.info("ربات آماده است: @%s", me.username)
    logger.info(
        "وب‌هوک TradingView: http://%s:%s/tv?secret=YOUR_SECRET",
        settings.webhook_host,
        settings.webhook_port,
    )
    if not settings.has_admins:
        logger.warning("ADMIN_IDS خالی است — پنل ادمین برای کسی فعال نمی‌شود.")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    await stop_event.wait()

    logger.info("در حال خاموش شدن...")
    await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()
    await runner.cleanup()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("خروج...")
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
