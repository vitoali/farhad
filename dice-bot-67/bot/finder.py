"""پیدا کردن مختصات با OpenCV یا مختصات ثابت از config."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def find_target(
    name: str,
    cfg: dict[str, Any],
) -> tuple[int, int]:
    """مختصات مرکز هدف را برمی‌گرداند."""
    if cfg.get("use_opencv", True):
        templates = cfg.get("templates") or {}
        rel = templates.get(name)
        if rel:
            from bot.config import resolve_path

            path = resolve_path(rel)
            if path.exists():
                found = _match_template(path, float(cfg.get("opencv_confidence", 0.72)))
                if found is not None:
                    logger.info("OpenCV پیدا کرد %s در %s", name, found)
                    return found
                logger.warning(
                    "OpenCV نتوانست %s را پیدا کند؛ از مختصات ثابت استفاده می‌شود.",
                    name,
                )
            else:
                logger.warning("قالب %s موجود نیست: %s", name, path)

    positions = cfg.get("positions") or {}
    if name not in positions:
        raise KeyError(f"مختصات '{name}' در config تعریف نشده است.")
    x, y = positions[name]
    return int(x), int(y)


def _match_template(template_path: Path, confidence: float) -> tuple[int, int] | None:
    try:
        import cv2
        import numpy as np
        import pyautogui
    except ImportError as exc:
        logger.error("کتابخانه لازم برای OpenCV نصب نیست: %s", exc)
        return None

    screenshot = pyautogui.screenshot()
    screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        logger.error("خواندن قالب شکست خورد: %s", template_path)
        return None

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < confidence:
        logger.debug("confidence کم برای %s: %.3f < %.3f", template_path.name, max_val, confidence)
        return None

    th, tw = template.shape[:2]
    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    return cx, cy
