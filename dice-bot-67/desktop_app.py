"""Entry point: اتوماسیون موس روی تلگرام دسکتاپ — بدون ربات و بدون api."""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import copy

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fix_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _fix_console()
    from bot.actions import configure_pyautogui, perform_roll
    from bot.calibrator import run_calibration
    from bot.config import load_config, save_config
    from bot.timing import DelayScheduler

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = ROOT

    cfg_path = base / "config.json"
    example = ROOT / "config.example.json"
    if not cfg_path.exists():
        src = example if example.exists() else Path(getattr(sys, "_MEIPASS", ROOT)) / "config.example.json"
        copy(src, cfg_path)
        print(f"config.json ساخته شد: {cfg_path}")

    cfg = load_config(cfg_path)
    cfg["mode"] = "desktop"
    cfg["use_opencv"] = False  # فقط مختصات کالیبره
    log_file = base / "logs" / "dice_bot.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    cfg["log_file"] = str(log_file)
    save_config(cfg, cfg_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger("desktop67")

    print("=" * 56)
    print(" Dice Bot 67 — حالت Desktop (کلیک موس)")
    print(" بدون BotFather / بدون api_id")
    print(" تلگرام دسکتاپ را باز کن و گروه Six Seven Chat را جلو بگذار")
    print("=" * 56)

    positions = cfg.get("positions") or {}
    need_cal = any(k not in positions for k in ("dice", "slot", "send"))
    # default placeholder coords mean not calibrated
    if (
        positions.get("dice") == [500, 500]
        and positions.get("send") == [900, 700]
    ):
        need_cal = True

    ans = "y" if need_cal else ""
    if need_cal:
        print("\nاول باید یک‌بار کالیبره کنی.")
        input("تلگرام را جلو بگذار، بعد Enter بزن...")
        cfg = run_calibration(cfg)
    else:
        ans = input("کالیبره دوباره؟ (y/N): ").strip().lower()
        if ans == "y":
            cfg = run_calibration(cfg)

    try:
        import keyboard
        import pyautogui
    except ImportError as exc:
        print("وابستگی کم است:", exc)
        input("Enter...")
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
        print("RUNNING ▶" if state["running"] else "STOPPED ⏸")

    hotkey = str(cfg.get("hotkey_toggle", "f8"))
    keyboard.add_hotkey(hotkey, toggle)

    print()
    print(f"آماده. {hotkey.upper()} = شروع/توقف")
    print("موس گوشه بالا-چپ = توقف اضطراری")
    print(f"تأخیر فعلی: {scheduler.current_delay}s")
    print("Send = کلمه Send داخل باکس سیاه تلگرام")

    try:
        while True:
            if not state["running"]:
                time.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = "🎲" if action == "dice" else "🎰"
            print(f"[{datetime.now():%H:%M:%S}] {emoji}")
            try:
                perform_roll(action, cfg)
            except pyautogui.FailSafeException:
                print("FAILSAFE — متوقف شد")
                state["running"] = False
                continue
            except Exception:
                log.exception("action failed")
                print("خطا — متوقف شد. F8 برای ادامه")
                state["running"] = False
                continue

            info = scheduler.mark_action_done()
            if info["delay_changed"]:
                print(f"⏱ زمان جدید: {info['current_delay']}s")

            wait_for = scheduler.wait_seconds()
            print(f"صبر {wait_for}s ...")
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


if __name__ == "__main__":
    raise SystemExit(main())
