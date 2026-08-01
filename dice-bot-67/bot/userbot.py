"""ارسال تاس بومی تلگرام با Telethon (پیشنهادی برای Six Seven)."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from bot.timing import DelayScheduler

logger = logging.getLogger(__name__)

DICE_EMOJI = {"dice": "🎲", "slot": "🎰"}


async def run_userbot(cfg: dict[str, Any]) -> int:
    try:
        from telethon import TelegramClient
        from telethon.tl.types import InputMediaDice
    except ImportError:
        print("Telethon نصب نیست. اجرا کنید:")
        print("  pip install telethon")
        return 1

    api_id = int(cfg.get("api_id") or 0)
    api_hash = str(cfg.get("api_hash") or "").strip()
    session = str(cfg.get("session_name") or "dice67_session").strip()
    target = cfg.get("target_chat") or "Six Seven Chat 8"

    if not api_id or not api_hash:
        print("api_id و api_hash را در config.json بگذارید.")
        print("از این سایت بگیرید: https://my.telegram.org/apps")
        return 1

    scheduler = DelayScheduler(
        min_delay=int(cfg.get("min_delay_sec", 61)),
        max_delay=int(cfg.get("max_delay_sec", 100)),
        change_every=int(cfg.get("delay_change_every_cycles", 10)),
    )

    state = {"running": False}
    hotkey = str(cfg.get("hotkey_toggle", "f8"))

    try:
        import keyboard

        def toggle() -> None:
            state["running"] = not state["running"]
            print("RUNNING ▶" if state["running"] else "STOPPED ⏸")
            logger.info(
                "%s | actions=%s cycles=%s delay=%s",
                "RUNNING" if state["running"] else "STOPPED",
                scheduler.actions_done,
                scheduler.cycles_done,
                scheduler.current_delay,
            )

        keyboard.add_hotkey(hotkey, toggle)
        hotkeys_ok = True
    except Exception as exc:
        logger.warning("keyboard در دسترس نیست (%s) — با Enter شروع می‌شود.", exc)
        hotkeys_ok = False
        state["running"] = True

    client = TelegramClient(session, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    logger.info("وارد شد: %s (%s)", me.first_name, me.id)

    entity = await client.get_entity(target)
    title = getattr(entity, "title", None) or getattr(entity, "username", target)
    print("=" * 56)
    print(" Dice Bot 67 — حالت UserBot (Telethon)")
    print(f" گروه هدف: {title}")
    print(f" تأخیر فعلی: {scheduler.current_delay}s")
    print(f" تعویض تأخیر هر {scheduler.change_every} چرخه")
    if hotkeys_ok:
        print(f" {hotkey.upper()} = شروع/توقف | Ctrl+C = خروج")
        print(" الان STOPPED است — برای شروع F8 را بزنید.")
    else:
        print(" در حال اجرا (بدون hotkey)")
    print("=" * 56)

    try:
        while True:
            if not state["running"]:
                await asyncio.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = DICE_EMOJI[action]
            print(f"ارسال {emoji} ...")
            logger.info("ارسال %s به %s", emoji, title)

            try:
                await client.send_file(entity, InputMediaDice(emoticon=emoji))
            except Exception:
                logger.exception("ارسال تاس شکست خورد")
                state["running"] = False
                print("خطا در ارسال — متوقف شد.")
                continue

            # تأخیر انسانی کوتاه بعد از ارسال (شبیه کلیک Send)
            await asyncio.sleep(
                random.uniform(
                    float(cfg.get("send_delay_min_sec", 3)),
                    float(cfg.get("send_delay_max_sec", 10)),
                )
            )

            info = scheduler.mark_action_done()
            logger.info(
                "OK actions=%s cycles=%s delay=%s changed=%s",
                info["actions_done"],
                info["cycles_done"],
                info["current_delay"],
                info["delay_changed"],
            )
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
        await client.disconnect()

    return 0


def run_userbot_sync(cfg: dict[str, Any]) -> int:
    return asyncio.run(run_userbot(cfg))
