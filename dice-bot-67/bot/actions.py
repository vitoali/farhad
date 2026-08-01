"""کلیک با جابه‌جایی تصادفی موس و تأخیر انسانی."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import pyautogui

from bot.finder import find_target

logger = logging.getLogger(__name__)


def configure_pyautogui(cfg: dict[str, Any]) -> None:
    pyautogui.FAILSAFE = bool(cfg.get("failsafe", True))
    pyautogui.PAUSE = float(cfg.get("pyautogui_pause", 0.15))


def click_with_variation(pos: tuple[int, int], cfg: dict[str, Any]) -> tuple[int, int]:
    jitter = int(cfg.get("mouse_jitter_px", 5))
    x = pos[0] + random.randint(-jitter, jitter)
    y = pos[1] + random.randint(-jitter, jitter)

    duration = random.uniform(
        float(cfg.get("mouse_move_min_sec", 0.2)),
        float(cfg.get("mouse_move_max_sec", 0.5)),
    )
    pyautogui.moveTo(x, y, duration=duration)

    pre = random.uniform(
        float(cfg.get("pre_click_delay_min_sec", 1)),
        float(cfg.get("pre_click_delay_max_sec", 3)),
    )
    time.sleep(pre)
    pyautogui.click()
    logger.info("کلیک در (%s, %s)", x, y)
    return x, y


def perform_roll(action: str, cfg: dict[str, Any]) -> None:
    """
    action: 'dice' یا 'slot'
    روی تاس/اسلات کلیک می‌کند، کمی صبر می‌کند، بعد SEND را می‌زند.
    """
    if action not in ("dice", "slot"):
        raise ValueError(f"اکشن نامعتبر: {action}")

    target = find_target(action, cfg)
    logger.info("هدف %s -> %s", action, target)
    click_with_variation(target, cfg)

    send_wait = random.uniform(
        float(cfg.get("send_delay_min_sec", 3)),
        float(cfg.get("send_delay_max_sec", 10)),
    )
    logger.info("صبر قبل از SEND: %.1f ثانیه", send_wait)
    time.sleep(send_wait)

    send_pos = find_target("send", cfg)
    click_with_variation(send_pos, cfg)
