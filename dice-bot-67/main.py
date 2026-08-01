"""
Dice Bot 67
اتوماسیون دسکتاپ برای زدن تاس 🎲 و اسلات 🎰 در تلگرام دسکتاپ.

اجرا:
  python main.py
  python main.py --calibrate
  python main.py --capture-templates

F8 = شروع / توقف
موس را به گوشه بالا-چپ ببرید برای توقف اضطراری (FAILSAFE)
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
    p.add_argument("--calibrate", action="store_true", help="کالیبره مختصات موس")
    p.add_argument(
        "--capture-templates",
        action="store_true",
        help="از مختصات فعلی قالب OpenCV بساز",
    )
    p.add_argument("--config", default=None, help="مسیر config.json")
    return p.parse_args()


def main() -> int:
    from bot.actions import configure_pyautogui, perform_roll
    from bot.calibrator import capture_templates, run_calibration
    from bot.config import ensure_config, load_config
    from bot.timing import DelayScheduler

    args = parse_args()
    cfg_path = Path(args.config) if args.config else None
    if cfg_path:
        ensure_config(cfg_path)
        cfg = load_config(cfg_path)
    else:
        ensure_config()
        cfg = load_config()

    setup_logging(str(cfg.get("log_file", "logs/dice_bot.log")))
    log = logging.getLogger("dice67")

    if args.calibrate:
        run_calibration(cfg)
        return 0

    if args.capture_templates:
        capture_templates(cfg)
        return 0

    try:
        import keyboard
        import pyautogui
    except ImportError as exc:
        print("وابستگی‌ها نصب نیستند. اجرا کنید:")
        print("  pip install -r requirements.txt")
        print(exc)
        return 1

    configure_pyautogui(cfg)

    scheduler = DelayScheduler(
        min_delay=int(cfg.get("min_delay_sec", 61)),
        max_delay=int(cfg.get("max_delay_sec", 100)),
        change_every=int(cfg.get("delay_change_every_cycles", 10)),
    )

    state = {"running": False}

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
    print(" Dice Bot 67 آماده است")
    print(f" کلید شروع/توقف: {hotkey.upper()}")
    print(f" تأخیر فعلی: {scheduler.current_delay} ثانیه")
    print(f" تعویض تأخیر هر {scheduler.change_every} چرخه کامل (🎲+🎰)")
    print(" تلگرام دسکتاپ را باز کنید و گروه بازی را جلو بگذارید.")
    print(" موس به گوشه بالا-چپ = توقف اضطراری")
    print("=" * 56)

    log.info(
        "Bot started | delay=%ss | change_every=%s cycles",
        scheduler.current_delay,
        scheduler.change_every,
    )

    try:
        while True:
            if not state["running"]:
                time.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = "🎲" if action == "dice" else "🎰"
            log.info("=== اجرای %s (%s) ===", emoji, action)
            print(f"[{datetime.now():%H:%M:%S}] {emoji} {action}")

            try:
                perform_roll(action, cfg)
            except pyautogui.FailSafeException:
                log.error("FAILSAFE: موس به گوشه صفحه رفت. توقف.")
                state["running"] = False
                continue
            except Exception:
                log.exception("خطا در اجرای اکشن")
                state["running"] = False
                print("خطا رخ داد — متوقف شد. F8 برای ادامه.")
                continue

            info = scheduler.mark_action_done()
            log.info(
                "تمام شد | actions=%s cycles=%s delay=%ss changed=%s",
                info["actions_done"],
                info["cycles_done"],
                info["current_delay"],
                info["delay_changed"],
            )
            if info["delay_changed"]:
                print(
                    f"⏱ زمان جدید بعد از {info['cycles_done']} چرخه: "
                    f"{info['previous_delay']}s → {info['current_delay']}s"
                )

            wait_for = scheduler.wait_seconds()
            print(f"صبر {wait_for} ثانیه... (F8=توقف)")
            slept = 0.0
            while slept < wait_for:
                if not state["running"]:
                    break
                step = min(0.5, wait_for - slept)
                time.sleep(step)
                slept += step

    except KeyboardInterrupt:
        print("\nخروج...")
        log.info("Interrupted by user")
    finally:
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
