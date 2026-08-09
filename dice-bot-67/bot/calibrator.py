"""کالیبره / Teach برای قالب‌های هوشمند."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pyautogui

from bot.config import clone_config, save_config
from bot.finder import ensure_builtin_templates, teach_capture

STEPS = (
    ("dice", "پنل ایموجی باز باشد. موس را روی 🎲 بگذار و Enter بزن (برای یادگیری تصویر)"),
    ("slot", "موس را روی 🎰 بگذار و Enter بزن"),
    ("send", "روی 🎲 بزن تا مثلث ارسال بیاید، موس روی مثلث ارسال بگذار و Enter بزن"),
)


def run_calibration(cfg: dict[str, Any], config_path=None) -> dict[str, Any]:
    print("=" * 56)
    print("یادگیری هوشمند (Teach)")
    print("از روی تصویر واقعی تلگرام قالب می‌سازد.")
    print("بعداً خودش 🎲 و 🎰 را روی صفحه پیدا می‌کند.")
    print("=" * 56)

    updated = clone_config(cfg)
    base = Path(updated.get("_base_dir") or Path.cwd())
    ensure_builtin_templates(base)

    for key, message in STEPS:
        input(f"\n[{key}] {message} ... ")
        path = teach_capture(key, updated, size=56)
        # teach_capture positions را هم می‌نویسد
        print(f"  قالب ذخیره شد: {path}")
        time.sleep(0.2)

    updated["open_emoji_panel_each_roll"] = False
    updated["use_opencv"] = True
    updated["calibrated_v2"] = True
    updated["smart_emoji"] = True
    save_config(updated, config_path)
    print("\nیادگیری تمام شد. از این به بعد هوشمند پیدا می‌کند.")
    return updated


def capture_templates(cfg: dict[str, Any], size: int = 56) -> None:
    run_calibration(cfg)
