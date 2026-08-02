"""
Dice Bot 67 — برای گروه Six Seven Chat

دو حالت:
  1) userbot (پیشنهادی): با Telethon مستقیم 🎲/🎰 می‌فرستد
  2) desktop: با موس روی تلگرام دسکتاپ کلیک می‌کند

اجرا:
  python main.py
  python main.py --mode userbot
  python main.py --mode desktop
  python main.py --calibrate
  python main.py --capture-templates

F8 = شروع / توقف
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def setup_logging(log_file: str) -> None:
    from bot.config import resolve_path

    path = resolve_path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dice Bot 67")
    p.add_argument(
        "--mode",
        choices=("userbot", "desktop"),
        default=None,
        help="userbot=Telethon | desktop=کلیک موس",
    )
    p.add_argument("--calibrate", action="store_true", help="کالیبره مختصات موس")
    p.add_argument(
        "--capture-templates",
        action="store_true",
        help="از مختصات فعلی قالب OpenCV بساز",
    )
    p.add_argument("--config", default=None, help="مسیر config.json")
    return p.parse_args()


def run_desktop(cfg: dict) -> int:
    from bot.actions import configure_pyautogui, perform_roll
    from bot.timing import DelayScheduler

    try:
        import keyboard
        import pyautogui
    except ImportError as exc:
        print("وابستگی دسکتاپ نصب نیست:")
        print("  pip install pyautogui keyboard opencv-python-headless Pillow")
        print(exc)
        return 1

    configure_pyautogui(cfg)
    scheduler = DelayScheduler(
        min_delay=int(cfg.get("min_delay_sec", 61)),
        max_delay=int(cfg.get("max_delay_sec", 80)),
        change_every=int(cfg.get("delay_change_every_cycles", 10)),
        dice_min=int(cfg.get("dice_min", cfg.get("dice_per_cycle", 10))),
        dice_max=int(cfg.get("dice_max", cfg.get("dice_per_cycle", 15))),
        slot_per_cycle=int(cfg.get("slot_per_cycle", 5)),
    )
    state = {"running": False}
    log = logging.getLogger("dice67")

    def toggle() -> None:
        state["running"] = not state["running"]
        status = "RUNNING ▶" if state["running"] else "STOPPED ⏸"
        log.info(
            "%s | actions=%s cycles=%s delay=%ss",
            status,
            scheduler.actions_done,
            scheduler.cycles_done,
            scheduler.current_delay,
        )
        print(status)

    hotkey = str(cfg.get("hotkey_toggle", "f8"))
    keyboard.add_hotkey(hotkey, toggle)

    print("=" * 56)
    print(" Dice Bot 67 — حالت Desktop (کلیک موس)")
    print(" گروه Six Seven Chat را جلو بگذارید.")
    print(" Send = کلمه Send داخل باکس سیاه راهنما")
    print(f" کلید: {hotkey.upper()} | موس گوشه بالا-چپ = اضطراری")
    print(f" تأخیر فعلی: {scheduler.current_delay}s")
    print("=" * 56)

    try:
        while True:
            if not state["running"]:
                time.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = "🎲" if action == "dice" else "🎰"
            print(f"[{datetime.now():%H:%M:%S}] {emoji} {action}")

            try:
                perform_roll(action, cfg)
            except pyautogui.FailSafeException:
                log.error("FAILSAFE فعال شد.")
                state["running"] = False
                continue
            except Exception:
                log.exception("خطا در اکشن")
                state["running"] = False
                print("خطا — متوقف شد.")
                continue

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
                time.sleep(step)
                slept += step
    except KeyboardInterrupt:
        print("\nخروج...")
    finally:
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
    return 0


def main() -> int:
    from bot.calibrator import capture_templates, run_calibration
    from bot.config import ensure_config, load_config

    args = parse_args()
    cfg_path = Path(args.config) if args.config else None
    if cfg_path:
        ensure_config(cfg_path)
        cfg = load_config(cfg_path)
    else:
        ensure_config()
        cfg = load_config()

    setup_logging(str(cfg.get("log_file", "logs/dice_bot.log")))

    if args.calibrate:
        run_calibration(cfg)
        return 0
    if args.capture_templates:
        capture_templates(cfg)
        return 0

    mode = args.mode or str(cfg.get("mode") or "userbot")
    if mode == "userbot":
        from bot.userbot import run_userbot_sync

        return run_userbot_sync(cfg)
    return run_desktop(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
