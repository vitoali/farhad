"""کالیبره کردن مختصات با موس."""

from __future__ import annotations

import logging
import time
from typing import Any

import pyautogui

from bot.config import clone_config, save_config

logger = logging.getLogger(__name__)


STEPS = (
    ("dice", "موس را روی ایموجی 🎲 بگذارید و Enter بزنید"),
    ("slot", "موس را روی ایموجی 🎰 بگذارید و Enter بزنید"),
    ("send", "موس را روی دکمه SEND بگذارید و Enter بزنید"),
)


def run_calibration(cfg: dict[str, Any]) -> dict[str, Any]:
    print("=" * 50)
    print("حالت کالیبره — پنجره تلگرام را باز و گروه بازی را جلو بگذارید.")
    print("برای هر مرحله موس را روی هدف بگذارید و Enter بزنید.")
    print("برای انصراف Ctrl+C")
    print("=" * 50)

    updated = clone_config(cfg)
    positions = dict(updated.get("positions") or {})

    for key, message in STEPS:
        input(f"\n[{key}] {message} ... ")
        x, y = pyautogui.position()
        positions[key] = [int(x), int(y)]
        print(f"  ذخیره شد: {key} = ({x}, {y})")
        time.sleep(0.2)

    updated["positions"] = positions
    # اگر کاربر کالیبره دستی کرد، مختصات ثابت اولویت دارد مگر قالب‌ها موجود باشند
    save_config(updated)
    print("\nconfig.json ذخیره شد.")
    return updated


def capture_templates(cfg: dict[str, Any], size: int = 48) -> None:
    """
    اختیاری: از اطراف مختصات فعلی اسکرین‌شات قالب می‌گیرد
    تا OpenCV بتواند بعداً خودش پیدا کند.
    """
    from pathlib import Path

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
    cfg["use_opencv"] = True
    save_config(cfg)
    print("قالب‌ها ذخیره شدند.")
