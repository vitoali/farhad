"""پیدا کردن هوشمند 🎲 / 🎰 / مثلث ارسال با NumPy (بدون OpenCV)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_REGIONS = {
    "dice": (0.30, 0.30, 1.0, 1.0),
    "slot": (0.30, 0.30, 1.0, 1.0),
    "send": (0.50, 0.65, 1.0, 1.0),
}


def find_target(name: str, cfg: dict[str, Any]) -> tuple[int, int]:
    """
    برای یکی‌درمیان قابل اعتماد: اول مختصات Teach.
    جستجوی تصویری فقط اگر prefer_positions خاموش باشد.
    """
    positions = cfg.get("positions") or {}
    prefer_positions = bool(cfg.get("prefer_positions", True))

    if prefer_positions and name in positions:
        x, y = int(positions[name][0]), int(positions[name][1])
        # مختصات پیش‌فرض نمونه را قبول نکن
        if not (name in ("dice", "slot", "send") and [x, y] in ([500, 500], [560, 500], [900, 700])):
            logger.info("مختصات Teach برای %s -> (%s,%s)", name, x, y)
            print(f"  → کلیک {name} روی مختصات Teach ({x},{y})")
            return x, y

    if cfg.get("use_opencv", True) or cfg.get("smart_emoji", True):
        found = find_with_opencv(name, cfg)
        if found is not None:
            logger.info("هوشمند پیدا شد %s @ %s", name, found)
            print(f"  ✓ پیدا شد {name}: {found}")
            return found
        logger.warning("هوشمند %s را پیدا نکرد؛ مختصات ثابت...", name)
        print(f"  ! {name} با تصویر پیدا نشد → مختصات ذخیره‌شده")

    if name not in positions:
        raise KeyError(f"'{name}' پیدا نشد. پنل ایموجی را باز کن یا Teach کن.")
    return int(positions[name][0]), int(positions[name][1])


def find_with_opencv(name: str, cfg: dict[str, Any]) -> tuple[int, int] | None:
    """نام تاریخی؛ الان با NumPy کار می‌کند."""
    templates = _template_paths(name, cfg)
    if not templates:
        return None

    conf = float(cfg.get("opencv_confidence", 0.72))
    scales = cfg.get("opencv_scales") or [0.7, 0.85, 1.0, 1.15, 1.3]
    region = SEARCH_REGIONS.get(name)

    best: tuple[float, int, int] | None = None
    for path in templates:
        hit = _match_multiscale(path, conf, scales, region)
        if hit is None:
            continue
        if best is None or hit[0] > best[0]:
            best = hit
    if best is None:
        return None
    return best[1], best[2]


def teach_capture(name: str, cfg: dict[str, Any], size: int = 56) -> Path:
    import pyautogui

    x, y = pyautogui.position()
    half = size // 2
    left = max(0, int(x) - half)
    top = max(0, int(y) - half)
    img = pyautogui.screenshot(region=(left, top, size, size))

    base = Path(cfg.get("_base_dir") or Path.cwd())
    assets = base / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    path = assets / f"{name}.png"
    img.save(path)

    templates = dict(cfg.get("templates") or {})
    templates[name] = str(path)
    cfg["templates"] = templates
    cfg["use_opencv"] = True
    cfg["smart_emoji"] = True
    positions = dict(cfg.get("positions") or {})
    positions[name] = [int(x), int(y)]
    cfg["positions"] = positions
    return path


def ensure_builtin_templates(base_dir: Path) -> dict[str, str]:
    import urllib.request

    assets = Path(base_dir) / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    mapping = {
        "dice": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f3b2.png",
        "slot": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f3b0.png",
    }
    out: dict[str, str] = {}
    for name, url in mapping.items():
        dest = assets / f"{name}_twemoji.png"
        if not dest.exists():
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as exc:
                logger.warning("دانلود %s شکست: %s", name, exc)
                continue
        out[name] = str(dest)
    return out


def _template_paths(name: str, cfg: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        if not p.exists():
            return
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            paths.append(p)

    templates = cfg.get("templates") or {}
    if name in templates:
        add(Path(templates[name]))

    base = Path(cfg.get("_base_dir") or Path.cwd())
    add(base / "assets" / f"{name}.png")
    add(base / "assets" / f"{name}_twemoji.png")

    from bot.config import ROOT

    add(ROOT / "assets" / f"{name}.png")
    add(ROOT / "assets" / f"{name}_twemoji.png")
    return paths


def _match_multiscale(
    template_path: Path,
    confidence: float,
    scales: list[float],
    region: tuple[float, float, float, float] | None,
) -> tuple[float, int, int] | None:
    try:
        import numpy as np
        import pyautogui
        from PIL import Image
    except ImportError as exc:
        logger.error("numpy/PIL/pyautogui نیست: %s", exc)
        return None

    # اگر OpenCV واقعی بود سریع‌تر است
    try:
        import cv2  # type: ignore

        return _match_cv2(template_path, confidence, scales, region)
    except Exception:
        pass

    shot = pyautogui.screenshot().convert("RGB")
    w, h = shot.size
    left = top = 0
    right, bottom = w, h
    if region:
        left = int(w * region[0])
        top = int(h * region[1])
        right = int(w * region[2])
        bottom = int(h * region[3])
        shot = shot.crop((left, top, right, bottom))

    # کوچک‌سازی برای سرعت جستجو
    fast = 0.5
    small = shot.resize(
        (max(40, int(shot.width * fast)), max(40, int(shot.height * fast))),
        Image.Resampling.BILINEAR,
    )
    screen = np.asarray(small.convert("L"), dtype=np.float32)
    template0 = Image.open(template_path).convert("RGBA")
    # پس‌زمینه سفید برای ایموجی‌های شفاف
    bg = Image.new("RGB", template0.size, (255, 255, 255))
    bg.paste(template0, mask=template0.split()[-1] if "A" in template0.getbands() else None)
    template0 = bg.convert("L")

    best_score = -1.0
    best_xy: tuple[int, int] | None = None

    for scale in scales:
        tw = max(10, int(template0.width * scale * fast))
        th = max(10, int(template0.height * scale * fast))
        if th >= screen.shape[0] or tw >= screen.shape[1]:
            continue
        templ = np.asarray(
            template0.resize((tw, th), Image.Resampling.BILINEAR), dtype=np.float32
        )
        score, loc = _ncc_loop(screen, templ, step=2)
        if score > best_score:
            best_score = score
            cx = left + int((loc[0] + tw / 2) / fast)
            cy = top + int((loc[1] + th / 2) / fast)
            best_xy = (cx, cy)

    if best_xy is None or best_score < confidence:
        logger.debug(
            "match fail %s score=%.3f need>=%.3f",
            template_path.name,
            best_score,
            confidence,
        )
        return None
    return best_score, best_xy[0], best_xy[1]


def _match_cv2(
    template_path: Path,
    confidence: float,
    scales: list[float],
    region: tuple[float, float, float, float] | None,
) -> tuple[float, int, int] | None:
    import cv2
    import numpy as np
    import pyautogui

    shot = pyautogui.screenshot()
    screen_full = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
    h, w = screen_full.shape[:2]
    off_x = off_y = 0
    screen = screen_full
    if region:
        x0, y0 = int(w * region[0]), int(h * region[1])
        x1, y1 = int(w * region[2]), int(h * region[3])
        screen = screen_full[y0:y1, x0:x1]
        off_x, off_y = x0, y0
    template0 = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template0 is None:
        return None
    best_score = -1.0
    best_xy = None
    for scale in scales:
        tw = max(10, int(template0.shape[1] * scale))
        th = max(10, int(template0.shape[0] * scale))
        if th >= screen.shape[0] or tw >= screen.shape[1]:
            continue
        templ = cv2.resize(template0, (tw, th), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(screen, templ, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = float(max_val)
            best_xy = (off_x + max_loc[0] + tw // 2, off_y + max_loc[1] + th // 2)
    if best_xy is None or best_score < confidence:
        return None
    return best_score, best_xy[0], best_xy[1]


def _ncc_loop(screen_gray: Any, templ_gray: Any, step: int = 2) -> tuple[float, tuple[int, int]]:
    import numpy as np

    sg = screen_gray
    tg = templ_gray
    th, tw = tg.shape
    sh, sw = sg.shape
    if th >= sh or tw >= sw:
        return -1.0, (0, 0)

    tg_zm = tg - tg.mean()
    tg_norm = float(np.linalg.norm(tg_zm)) + 1e-6
    best = -1.0
    best_loc = (0, 0)
    for y in range(0, sh - th + 1, step):
        for x in range(0, sw - tw + 1, step):
            patch = sg[y : y + th, x : x + tw]
            p_zm = patch - patch.mean()
            denom = (float(np.linalg.norm(p_zm)) + 1e-6) * tg_norm
            score = float(np.dot(p_zm.ravel(), tg_zm.ravel()) / denom)
            if score > best:
                best = score
                best_loc = (x, y)

    # refine locally
    if step > 1 and best > 0:
        x0 = max(0, best_loc[0] - step)
        y0 = max(0, best_loc[1] - step)
        x1 = min(sw - tw, best_loc[0] + step)
        y1 = min(sh - th, best_loc[1] + step)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                patch = sg[y : y + th, x : x + tw]
                p_zm = patch - patch.mean()
                denom = (float(np.linalg.norm(p_zm)) + 1e-6) * tg_norm
                score = float(np.dot(p_zm.ravel(), tg_zm.ravel()) / denom)
                if score > best:
                    best = score
                    best_loc = (x, y)
    return best, best_loc
