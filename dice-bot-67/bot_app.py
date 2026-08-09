"""Entry point: فقط BotFather — با خواندن عدد تاس."""

from __future__ import annotations

import json
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
    from bot.bot_api import run_bot_api_sync
    from bot.config import load_config, save_config

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = ROOT

    cfg_path = base / "config.json"
    example = ROOT / "config.example.json"
    if not example.exists() and getattr(sys, "_MEIPASS", None):
        example = Path(sys._MEIPASS) / "config.example.json"

    if not cfg_path.exists():
        if example.exists():
            copy(example, cfg_path)
        else:
            cfg_path.write_text(
                json.dumps(
                    {
                        "mode": "bot",
                        "bot_token": "",
                        "target_chat": "Six Seven Chat 8",
                        "min_delay_sec": 61,
                        "max_delay_sec": 80,
                        "dice_min": 1,
                        "dice_max": 1,
                        "slot_per_cycle": 1,
                        "hotkey_toggle": "f8",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    cfg = load_config(cfg_path)
    cfg["mode"] = "bot"
    cfg["min_delay_sec"] = 61
    cfg["max_delay_sec"] = 80
    cfg["dice_min"] = 1
    cfg["dice_max"] = 1
    cfg["slot_per_cycle"] = 1
    cfg["_config_path"] = str(cfg_path)

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

    token = str(cfg.get("bot_token") or "").strip()
    if not token or token.startswith("123456") or "TOKEN" in token.upper() or "ABCDEF" in token:
        print("=" * 56)
        print(" Dice Bot 67 — BotFather")
        print(" توکن ربات را از @BotFather اینجا بچسبان:")
        print("=" * 56)
        token = input("> ").strip()
        if not token:
            print("توکن خالی است.")
            input("Enter...")
            return 1
        cfg["bot_token"] = token
        to_save = {k: v for k, v in cfg.items() if not str(k).startswith("_")}
        save_config(to_save, cfg_path)
        print("توکن ذخیره شد در config.json")

    print("\nربات را به گروه Six Seven Chat اضافه کرده باشی.")
    print("اگر Add member نداری: صفحه ربات → Add to Group / یا از ادمین بخواه.\n")

    return run_bot_api_sync(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
