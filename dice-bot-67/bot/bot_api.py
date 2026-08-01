"""ارسال تاس با BotFather توکن (بدون api_id / my.telegram.org)."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from bot.timing import DelayScheduler

logger = logging.getLogger(__name__)

DICE_EMOJI = {"dice": "🎲", "slot": "🎰"}


def _fix_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def api_call(token: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None
    headers = {}
    if params:
        data = urllib.parse.urlencode(params).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"اتصال به تلگرام شکست خورد: {exc}") from exc

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")
    return payload["result"]


def resolve_chat_id(token: str, target: str) -> int | str:
    """target می‌تواند @username، عدد chat_id، یا نام گروه باشد."""
    target = str(target).strip()
    if not target:
        raise RuntimeError("target_chat خالی است.")

    # numeric id
    if target.lstrip("-").isdigit():
        return int(target)

    # @username
    if target.startswith("@"):
        return target

    # try as public username without @
    if " " not in target and target.isascii():
        try:
            chat = api_call(token, "getChat", {"chat_id": f"@{target}"})
            return chat["id"]
        except Exception:
            pass

    # search in getUpdates / getChat can't find by title easily.
    # Ask user to use numeric id; still try getUpdates for recent chats.
    updates = api_call(token, "getUpdates", {"limit": 50, "timeout": 0})
    needle = target.casefold()
    for upd in reversed(updates):
        for key in ("message", "channel_post", "my_chat_member", "chat_member"):
            msg = upd.get(key) or {}
            chat = msg.get("chat") or {}
            title = str(chat.get("title") or "")
            if title.casefold() == needle or needle in title.casefold():
                return chat["id"]

    raise RuntimeError(
        "گروه پیدا نشد.\n"
        "ربات را به گروه اضافه کن، یک پیام در گروه بفرست،\n"
        "بعد در config مقدار target_chat را chat_id عددی بگذار\n"
        "(مثلاً -1001234567890). برای گرفتن آیدی از @userinfobot یا @RawDataBot استفاده کن."
    )


async def run_bot_api(cfg: dict[str, Any]) -> int:
    _fix_console()
    token = str(cfg.get("bot_token") or "").strip()
    if not token:
        print("bot_token خالی است. از @BotFather توکن بگیر و در config.json بگذار.")
        return 1

    target = cfg.get("target_chat") or "Six Seven Chat 8"
    print("در حال بررسی توکن...")
    me = api_call(token, "getMe")
    print(f"ربات: @{me.get('username')} ({me.get('first_name')})")

    chat_id = resolve_chat_id(token, str(target))
    print(f"هدف: {chat_id}")

    scheduler = DelayScheduler(
        min_delay=int(cfg.get("min_delay_sec", 61)),
        max_delay=int(cfg.get("max_delay_sec", 100)),
        change_every=int(cfg.get("delay_change_every_cycles", 10)),
    )

    state = {"running": False}
    hotkey = str(cfg.get("hotkey_toggle", "f8"))
    hotkeys_ok = False
    try:
        import keyboard

        def toggle() -> None:
            state["running"] = not state["running"]
            print("RUNNING ▶" if state["running"] else "STOPPED ⏸")

        keyboard.add_hotkey(hotkey, toggle)
        hotkeys_ok = True
    except Exception as exc:
        logger.warning("keyboard unavailable: %s", exc)
        state["running"] = True

    print("=" * 56)
    print(" Dice Bot 67 — حالت BotFather")
    print(f" تأخیر فعلی: {scheduler.current_delay}s")
    if hotkeys_ok:
        print(f" {hotkey.upper()} = شروع/توقف | Ctrl+C = خروج")
        print(" الان STOPPED — برای شروع F8")
    print("=" * 56)
    print("نکته: اگر بازی امتیاز نداد، یعنی فقط اکانت واقعی قبول می‌کند.")

    try:
        while True:
            if not state["running"]:
                await asyncio.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = DICE_EMOJI[action]
            print(f"ارسال {emoji} ...")
            try:
                api_call(token, "sendDice", {"chat_id": str(chat_id), "emoji": emoji})
            except Exception as exc:
                logger.exception("sendDice failed")
                print(f"خطا: {exc}")
                state["running"] = False
                continue

            await asyncio.sleep(
                random.uniform(
                    float(cfg.get("send_delay_min_sec", 3)),
                    float(cfg.get("send_delay_max_sec", 10)),
                )
            )
            info = scheduler.mark_action_done()
            if info["delay_changed"]:
                print(
                    f"⏱ زمان جدید: {info['previous_delay']}s → {info['current_delay']}s"
                )

            wait_for = scheduler.wait_seconds()
            print(f"صبر {wait_for} ثانیه...")
            slept = 0.0
            while slept < wait_for:
                if not state["running"]:
                    break
                step = min(0.5, wait_for - slept)
                await asyncio.sleep(step)
                slept += step
    except KeyboardInterrupt:
        print("\nخروج...")
    finally:
        if hotkeys_ok:
            try:
                import keyboard

                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
    return 0


def run_bot_api_sync(cfg: dict[str, Any]) -> int:
    return asyncio.run(run_bot_api(cfg))
