"""سرور HTTP برای دریافت هشدار TradingView."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web
from telegram.ext import Application

from bot.handlers import publish_signal
from bot.signals import parse_tradingview_payload

logger = logging.getLogger(__name__)


def create_webhook_app(tg_app: Application) -> web.Application:
    app = web.Application()
    app["tg_app"] = tg_app
    app.router.add_get("/health", health)
    app.router.add_post("/tv", tradingview_webhook)
    app.router.add_post("/webhook/tradingview", tradingview_webhook)
    return app


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def tradingview_webhook(request: web.Request) -> web.Response:
    tg_app: Application = request.app["tg_app"]
    settings = tg_app.bot_data["settings"]

    secret = request.headers.get("X-Webhook-Secret") or request.query.get("secret", "")
    if settings.webhook_secret and secret != settings.webhook_secret:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

    raw = await request.text()
    payload: Any
    try:
        payload = json.loads(raw) if raw.strip().startswith(("{", "[")) else raw
    except json.JSONDecodeError:
        payload = raw

    signal = parse_tradingview_payload(payload)
    if signal is None:
        logger.warning("invalid tradingview payload: %s", raw[:300])
        return web.json_response({"ok": False, "error": "invalid payload"}, status=400)

    sent, failed = await publish_signal(tg_app, signal)
    logger.info(
        "TV signal %s %s -> sent=%s failed=%s",
        signal.symbol,
        signal.side,
        sent,
        failed,
    )
    return web.json_response({"ok": True, "sent": sent, "failed": failed})
