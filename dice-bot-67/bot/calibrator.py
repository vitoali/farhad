"""کالیبره ساده: فقط 🎲 و 🎰 و مثلث ارسال."""

from __future__ import annotations

import time
from typing import Any

import pyautogui

from bot.config import clone_config, save_config

STEPS = (
    ("dice", "پنل ایموجی را باز کن، موس را روی 🎲 بگذار و Enter بزن"),
    ("slot", "موس را روی 🎰 بگذار و Enter بزن"),
    ("send", "یک‌بار روی 🎲 بزن تا مثلث ارسال بیاید، موس را روی مثلث ارسال بگذار و Enter بزن"),
)


def run_calibration(cfg: dict[str, Any], config_path=None) -> dict[str, Any]:
    print("=" * 56)
    print("کالیبره ساده — فقط ۳ نقطه")
    print("1) موقعیت 🎲")
    print("2) موقعیت 🎰")
    print("3) مثلث ارسال (همان که بعد از انتخاب ایموجی می‌آید)")
    print("خودت پنل ایموجی را باز نگه دار. برنامه پنل را باز/بسته نمی‌کند.")
    print("انصراف: Ctrl+C")
    print("=" * 56)

    updated = clone_config(cfg)
    positions = dict(updated.get("positions") or {})

    for key, message in STEPS:
        input(f"\n[{key}] {message} ... ")
        x, y = pyautogui.position()
        positions[key] = [int(x), int(y)]
        print(f"  ذخیره شد: {key} = ({x}, {y})")
        time.sleep(0.2)

    # دیگر به دکمه باز کردن ایموجی نیاز نیست
    positions.pop("emoji_button", None)
    updated["positions"] = positions
    updated["open_emoji_panel_each_roll"] = False
    updated["use_opencv"] = False
    updated["calibrated_v2"] = True
    save_config(updated, config_path)
    print("\nconfig.json ذخیره شد.")
    return updated


def capture_templates(cfg: dict[str, Any], size: int = 48) -> None:
    from bot.config import ROOT, resolve_path

    print("گرفتن قالب تصویری از مختصات فعلی...")
    templates = dict(cfg.get("templates") or {})
    positions = cfg.get("positions") or {}
    half = size // 2

    for name in ("dice", "slot", "send"):
        if name not in positions:
            continue
        x, y = positions[name]
        left = max(0, int(x) - half)
        top = max(0, int(y) - half)
        img = pyautogui.screenshot(region=(left, top, size, size))
        rel = templates.get(name, f"assets/{name}.png")
        path = resolve_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        templates[name] = str(path.relative_to(ROOT)).replace("\\", "/")
        print(f"  قالب {name} -> {path}")

    cfg["templates"] = templates
    save_config(cfg)
    print("قالب‌ها ذخیره شدند.")
