"""کالیبره کردن مختصات با موس (حالت دسکتاپ)."""

from __future__ import annotations

import logging
import time
from typing import Any

import pyautogui

from bot.config import clone_config, save_config

logger = logging.getLogger(__name__)


STEPS = (
    (
        "emoji_button",
        "موس را روی دکمه ایموجی (کنار کادر پیام) بگذارید و Enter بزنید",
    ),
    (
        "dice",
        "پنل ایموجی را باز کنید، موس را روی 🎲 بگذارید و Enter بزنید",
    ),
    (
        "slot",
        "موس را روی 🎰 بگذارید و Enter بزنید",
    ),
    (
        "send",
        "باکس سیاه «Send a 🎲 emoji...» را باز کنید و موس را روی کلمه Send بگذارید، Enter",
    ),
)


def run_calibration(cfg: dict[str, Any]) -> dict[str, Any]:
    print("=" * 56)
    print("کالیبره برای Six Seven Chat (تلگرام دسکتاپ)")
    print("گروه Six Seven Chat را جلو بگذارید.")
    print("Send یعنی دکمه داخل باکس سیاه راهنما — نه میکروفون.")
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

    updated["positions"] = positions
    save_config(updated)
    print("\nconfig.json ذخیره شد.")
    return updated


def capture_templates(cfg: dict[str, Any], size: int = 48) -> None:
    from bot.config import ROOT, resolve_path

    print("گرفتن قالب تصویری از مختصات فعلی...")
    templates = dict(cfg.get("templates") or {})
    positions = cfg.get("positions") or {}
    half = size // 2

    for name in ("emoji_button", "dice", "slot", "send"):
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
