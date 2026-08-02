"""Desktop هوشمند: پیدا کردن 🎲/🎰 با تصویر + مثلث ارسال."""

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
    from bot.finder import ensure_builtin_templates, find_with_opencv
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
    cfg["_base_dir"] = str(base)
    cfg["mode"] = "desktop"
    cfg["use_opencv"] = True
    cfg["smart_emoji"] = True
    cfg["open_emoji_panel_each_roll"] = False
    cfg.setdefault("min_delay_sec", 61)
    cfg.setdefault("max_delay_sec", 100)
    cfg.setdefault("delay_change_every_cycles", 10)
    cfg["send_delay_min_sec"] = float(cfg.get("send_click_delay_min_sec", 0.4))
    cfg["send_delay_max_sec"] = float(cfg.get("send_click_delay_max_sec", 1.2))
    cfg["mouse_jitter_px"] = int(cfg.get("mouse_jitter_px", 2))
    cfg["pre_click_delay_min_sec"] = float(cfg.get("pre_click_delay_min_sec", 0.15))
    cfg["pre_click_delay_max_sec"] = float(cfg.get("pre_click_delay_max_sec", 0.5))
    cfg.setdefault("opencv_confidence", 0.58)

    log_file = base / "logs" / "dice_bot.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    cfg["log_file"] = str(log_file)

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
    print(" Dice Bot 67 — Desktop هوشمند")
    print(" الگو: ۱۰ تا 🎲  بعد  ۵ تا 🎰  بعد تکرار")
    print(" فاصله بین هر ارسال: ۶۱–۱۰۰ ثانیه")
    print("=" * 56)

    print("در حال آماده‌سازی قالب‌ها...")
    ensure_builtin_templates(base)

    assets_ok = (base / "assets" / "dice.png").exists() and (base / "assets" / "slot.png").exists()
    taught = bool(cfg.get("calibrated_v2")) and assets_ok

    print("\nقبل از شروع پنل ایموجی را در گروه Six Seven باز کن و باز نگه دار.")
    if not taught:
        print("بار اول باید یک‌بار یاد بگیرد (Teach) تا تصویر واقعی تلگرام را داشته باشد.")
        input("پنل ایموجی باز است؟ Enter بزن...")
        cfg = run_calibration(cfg, cfg_path)
        cfg["_base_dir"] = str(base)
    else:
        ans = input("Teach دوباره؟ (y = بله / Enter = نه): ").strip().lower()
        if ans == "y":
            input("پنل ایموجی را باز کن، Enter...")
            cfg = run_calibration(cfg, cfg_path)
            cfg["_base_dir"] = str(base)
        else:
            # تست سریع پیدا کردن
            print("تست پیدا کردن هوشمند...")
            input("پنل ایموجی باز باشد، Enter برای اسکن...")
            d = find_with_opencv("dice", cfg)
            s = find_with_opencv("slot", cfg)
            print(f"  dice: {d}")
            print(f"  slot: {s}")
            if d is None or s is None:
                print("پیدا نشد — Teach لازم است.")
                cfg = run_calibration(cfg, cfg_path)
                cfg["_base_dir"] = str(base)

    # _base_dir را در فایل ذخیره نکن
    to_save = {k: v for k, v in cfg.items() if k != "_base_dir"}
    save_config(to_save, cfg_path)

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
        dice_per_cycle=int(cfg.get("dice_per_cycle", 10)),
        slot_per_cycle=int(cfg.get("slot_per_cycle", 5)),
    )
    state = {"running": False}

    def toggle() -> None:
        state["running"] = not state["running"]
        print("RUNNING ▶" if state["running"] else "STOPPED ⏸")

    hotkey = str(cfg.get("hotkey_toggle", "f8"))
    keyboard.add_hotkey(hotkey, toggle)

    print()
    print(f"آماده. {hotkey.upper()} = شروع/توقف")
    print("مهم: پنل ایموجی باز بماند")
    print(f"فاصله ارسال‌ها: {scheduler.current_delay}s")

    try:
        while True:
            if not state["running"]:
                time.sleep(0.25)
                continue

            action = scheduler.next_action
            emoji = "🎲" if action == "dice" else "🎰"
            print(
                f"[{datetime.now():%H:%M:%S}] {scheduler.progress_in_cycle} — جستجو {emoji} ..."
            )
            try:
                perform_roll(action, cfg)
            except pyautogui.FailSafeException:
                print("FAILSAFE")
                state["running"] = False
                continue
            except Exception:
                log.exception("action failed")
                print("خطا — F8 برای ادامه. اگر تکرار شد Teach دوباره کن.")
                state["running"] = False
                continue

            info = scheduler.mark_action_done()
            if info["delay_changed"]:
                print(f"⏱ فاصله جدید: {info['current_delay']}s")

            wait_for = scheduler.wait_seconds()
            print(f"صبر تا ارسال بعدی: {wait_for}s ...")
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
