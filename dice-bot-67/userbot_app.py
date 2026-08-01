"""Entry point for Windows exe (UserBot mode only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fix_console() -> None:
    """Avoid UnicodeEncodeError on Windows consoles (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _fix_console()
    from bot.config import load_config
    from bot.userbot import run_userbot_sync
    import logging

    # If running as frozen exe, keep config next to the exe
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = ROOT

    cfg_path = base / "config.json"
    example = ROOT / "config.example.json"
    if not example.exists() and getattr(sys, "_MEIPASS", None):
        # bundled example inside pyinstaller archive
        bundled = Path(sys._MEIPASS) / "config.example.json"
        if bundled.exists() and not cfg_path.exists():
            cfg_path.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")

    if not cfg_path.exists():
        # copy from project example
        from shutil import copy

        src = example if example.exists() else Path(sys._MEIPASS) / "config.example.json"
        copy(src, cfg_path)
        print(f"config.json ساخته شد: {cfg_path}")
        print("api_id و api_hash را ویرایش کنید، بعد دوباره اجرا کنید.")
        print("https://my.telegram.org/apps")
        input("Enter برای خروج...")
        return 1

    cfg = load_config(cfg_path)
    cfg["mode"] = "userbot"

    log_file = base / "logs" / "dice_bot.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    cfg["log_file"] = str(log_file)
    # session next to exe
    cfg["session_name"] = str(base / (cfg.get("session_name") or "dice67_session"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    if not int(cfg.get("api_id") or 0) or not str(cfg.get("api_hash") or "").strip():
        print("در config.json مقدار api_id و api_hash را پر کنید.")
        print(f"مسیر فایل: {cfg_path}")
        print("https://my.telegram.org/apps")
        input("Enter برای خروج...")
        return 1

    return run_userbot_sync(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
