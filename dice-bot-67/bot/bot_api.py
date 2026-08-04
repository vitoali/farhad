"""ارسال تاس با BotFather + خواندن عدد از API."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
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
    target = str(target).strip()
    if not target:
        raise RuntimeError("target_chat خالی است.")

    if target.lstrip("-").isdigit():
        return int(target)

    if target.startswith("@"):
        return target

    if " " not in target and target.isascii():
        try:
            chat = api_call(token, "getChat", {"chat_id": f"@{target}"})
            return chat["id"]
        except Exception:
            pass

    updates = api_call(token, "getUpdates", {"limit": 50, "timeout": 0})
    needle = target.casefold()
    for upd in reversed(updates):
        for key in ("message", "channel_post", "my_chat_member", "chat_member"):
            msg = upd.get(key) or {}
            chat = msg.get("chat") or {}
            title = str(chat.get("title") or "")
            if title and (title.casefold() == needle or needle in title.casefold()):
                return chat["id"]

    # آخرین گروه دیده‌شده را پیشنهاد بده
    for upd in reversed(updates):
        for key in ("message", "my_chat_member"):
            msg = upd.get(key) or {}
            chat = msg.get("chat") or {}
            if chat.get("type") in ("group", "supergroup") and chat.get("id"):
                print(f"گروه پیدا شد از آپدیت‌ها: {chat.get('title')} ({chat['id']})")
                return chat["id"]

    raise RuntimeError(
        "گروه پیدا نشد.\n"
        "1) ربات را به گروه اضافه کن\n"
        "2) در گروه یک پیام بفرست یا ربات را ادمین کن\n"
        "3) target_chat را chat_id عددی بگذار (مثل -100123...)\n"
        "   با @RawDataBot یا @userinfobot می‌توانی آیدی بگیری"
    )


def format_dice_value(emoji: str, value: int | None) -> str:
    if value is None:
        return "؟"
    if emoji == "🎲":
        return f"{value} (تاس ۱–۶)"
    if emoji == "🎰":
        # slot values 1-64; Telegram documents mapping but raw value is enough
        return f"{value} (گردونه ۱–۶۴)"
    return str(value)


async def run_bot_api(cfg: dict[str, Any]) -> int:
    _fix_console()
    token = str(cfg.get("bot_token") or "").strip()
    if not token or token.startswith("123456"):
        print("bot_token را در config.json از @BotFather بگذار.")
        return 1

    # الگوی فعلی کاربر
    cfg["min_delay_sec"] = int(cfg.get("min_delay_sec", 61) or 61)
    cfg["max_delay_sec"] = 80
    cfg["dice_min"] = 1
    cfg["dice_max"] = 1
    cfg["slot_per_cycle"] = 1

    target = cfg.get("target_chat") or "Six Seven Chat 8"
    print("در حال بررسی توکن...")
    me = api_call(token, "getMe")
    print(f"ربات: @{me.get('username')} ({me.get('first_name')})")

    try:
        chat_id = resolve_chat_id(token, str(target))
    except Exception as exc:
        print(exc)
        print("\nاگر آیدی عددی گروه را داری اینجا وارد کن (یا Enter برای خروج):")
        manual = input("> ").strip()
        if not manual:
            return 1
        chat_id = int(manual) if manual.lstrip("-").isdigit() else manual
        cfg["target_chat"] = str(chat_id)

    print(f"هدف: {chat_id}")

    # ذخیره chat_id برای دفعات بعد
    save_path = cfg.get("_config_path")
    if save_path:
        try:
            from bot.config import save_config

            to_save = {k: v for k, v in cfg.items() if not str(k).startswith("_")}
            to_save["mode"] = "bot"
            to_save["bot_token"] = token
            to_save["target_chat"] = str(chat_id)
            to_save["min_delay_sec"] = 61
            to_save["max_delay_sec"] = 80
            to_save["dice_min"] = 1
            to_save["dice_max"] = 1
            to_save["slot_per_cycle"] = 1
            save_config(to_save, Path(save_path))
        except Exception:
            pass

    scheduler = DelayScheduler(
        min_delay=61,
        max_delay=80,
        change_every=int(cfg.get("delay_change_every_cycles", 10)),
        dice_min=1,
        dice_max=1,
        slot_per_cycle=1,
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
    print(" Dice Bot 67 — BotFather")
    print(" الگو: یک 🎲 → یک 🎰 → تکرار")
    print(" فاصله: ۶۱–۸۰ ثانیه")
    print(" عدد تاس/گردونه از API خوانده می‌شود")
    print(f" تأخیر فعلی: {scheduler.current_delay}s")
    if hotkeys_ok:
        print(f" {hotkey.upper()} = شروع/توقف")
        print(" الان STOPPED — F8 برای شروع")
    print("=" * 56)
    print("نکته: اگر بازی امتیاز نداد، یعنی فقط اکانت واقعی را قبول می‌کند.")

    try:
        while True:
            if not state["running"]:
                await asyncio.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = DICE_EMOJI[action]
            print(f"ارسال {emoji} ...")
            try:
                result = api_call(
                    token, "sendDice", {"chat_id": str(chat_id), "emoji": emoji}
                )
                dice = result.get("dice") or {}
                value = dice.get("value")
                print(f"  نتیجه: {format_dice_value(emoji, value)}")
                logger.info("sent %s value=%s", emoji, value)
            except Exception as exc:
                logger.exception("sendDice failed")
                print(f"خطا: {exc}")
                state["running"] = False
                continue

            await asyncio.sleep(
                random.uniform(
                    float(cfg.get("send_delay_min_sec", 1)),
                    float(cfg.get("send_delay_max_sec", 3)),
                )
            )
            info = scheduler.mark_action_done()
            if info["delay_changed"]:
                print(f"⏱ زمان جدید: {info['current_delay']}s")

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
