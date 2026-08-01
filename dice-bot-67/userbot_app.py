"""Entry point for Windows exe — BotFather یا UserBot."""

from __future__ import annotations

import logging
import sys
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
    from bot.config import load_config

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = ROOT

    cfg_path = base / "config.json"
    example = ROOT / "config.example.json"
    if not cfg_path.exists():
        src = example
        if not src.exists() and getattr(sys, "_MEIPASS", None):
            src = Path(sys._MEIPASS) / "config.example.json"
        if not src.exists():
            print("config.example.json پیدا نشد.")
            input("Enter...")
            return 1
        copy(src, cfg_path)
        print(f"config.json ساخته شد: {cfg_path}")
        print("الان فقط bot_token را از @BotFather بگذار و دوباره اجرا کن.")
        input("Enter برای خروج...")
        return 1

    cfg = load_config(cfg_path)

    log_file = base / "logs" / "dice_bot.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    cfg["log_file"] = str(log_file)
    cfg["session_name"] = str(base / (cfg.get("session_name") or "dice67_session"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    mode = str(cfg.get("mode") or "bot").strip().lower()
    bot_token = str(cfg.get("bot_token") or "").strip()

    # اگر توکن ربات باشد، همان را استفاده کن (راحت‌ترین راه)
    if mode in ("bot", "botfather", "bot_api") or bot_token:
        if not bot_token:
            print("mode=bot است ولی bot_token خالی است.")
            print("1) در تلگرام به @BotFather برو")
            print("2) /newbot بزن و توکن را بگیر")
            print("3) در config.json داخل bot_token بگذار")
            print(f"مسیر: {cfg_path}")
            input("Enter برای خروج...")
            return 1
        from bot.bot_api import run_bot_api_sync

        cfg["mode"] = "bot"
        return run_bot_api_sync(cfg)

    # حالت قدیمی Telethon
    if not int(cfg.get("api_id") or 0) or not str(cfg.get("api_hash") or "").strip():
        print("برای userbot باید api_id/api_hash داشته باشی.")
        print("چون my.telegram.org برایت باز نشد، از حالت bot استفاده کن:")
        print('  "mode": "bot",')
        print('  "bot_token": "توکن_از_BotFather"')
        print(f"مسیر: {cfg_path}")
        input("Enter برای خروج...")
        return 1

    from bot.userbot import run_userbot_sync

    cfg["mode"] = "userbot"
    return run_userbot_sync(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
