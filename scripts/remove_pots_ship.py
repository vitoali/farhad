#!/usr/bin/env python3
"""Remove pots/plants from cream_22-01-35 and cream_22-02-00.

Composites aligned AI fills into original only in plant crop regions.
Outside those crops, output is pixel-identical to the source JPEGs.
"""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

ART = Path("/opt/cursor/artifacts/assets")
OUT = Path("/workspace/no-pots")
ROOT = Path("/workspace")


def load(p):
    return np.array(Image.open(p).convert("RGB"))


def save(arr, p, q=95):
    im = Image.fromarray(arr)
    if str(p).endswith(".jpg"):
        im.save(p, quality=q, subsampling=0)
    else:
        im.save(p)


def align_fill(crop, fill_ai, score_mask):
    ch, cw = crop.shape[:2]
    ah, aw = fill_ai.shape[:2]
    scale = ch / float(ah)
    new_w = max(cw + 120, int(round(aw * scale)))
    resized = cv2.resize(fill_ai, (new_w, ch), interpolation=cv2.INTER_LANCZOS4)
    outside = score_mask == 0
    best, bx = 1e18, 0
    for x in range(0, new_w - cw + 1):
        win = resized[:, x : x + cw]
        s = float(np.mean(np.abs(win.astype(np.float32) - crop.astype(np.float32))[outside]))
        if s < best:
            best, bx = s, x
    return resized[:, bx : bx + cw], best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    orig35 = load(ROOT / "cream_22-01-35.jpg")
    orig00 = load(ROOT / "cream_22-02-00.jpg")
    out35 = orig35.copy()
    out00 = orig00.copy()

    # 35L — left plant near door / curved wall
    y0, y1, x0, x1 = 80, 900, 140, 380
    crop = orig35[y0:y1, x0:x1]
    ignore = np.zeros(crop.shape[:2], np.uint8)
    ignore[:, :150] = 255
    aligned, mad = align_fill(crop, load(ART / "fill9_35L.png"), ignore)
    print("35L MAD", mad)
    diff = np.mean(np.abs(aligned.astype(np.float32) - crop.astype(np.float32)), axis=2)
    pasted = aligned.copy()
    restore = (diff < 6) & (np.arange(crop.shape[1])[None, :] > 160)
    pasted[restore] = crop[restore]
    out35[y0:y1, x0:x1] = pasted

    # 35R — right plant behind glass near panel 4 (tight crop)
    ty0, ty1, tx0, tx1 = 80, 780, 1320, 1520
    tcrop = orig35[ty0:ty1, tx0:tx1]
    ignore = np.zeros(tcrop.shape[:2], np.uint8)
    ignore[:, 40:] = 255
    aligned, mad = align_fill(tcrop, load(ART / "fill9_35R.png"), ignore)
    print("35R MAD", mad)
    pasted = aligned.copy()
    for i, a in enumerate(np.linspace(0, 1, 35)):
        pasted[:, i] = np.clip(tcrop[:, i] * (1 - a) + aligned[:, i] * a, 0, 255).astype(np.uint8)
    pasted[:, 35:] = aligned[:, 35:]
    out35[ty0:ty1, tx0:tx1] = pasted

    # 00L — left plant + ribbed pot; keep lamp/desk via full aligned fill of left crop
    y0, y1, x0, x1 = 40, 1040, 0, 290
    crop = orig00[y0:y1, x0:x1]
    ignore = np.zeros(crop.shape[:2], np.uint8)
    ignore[:, :210] = 255
    aligned, mad = align_fill(crop, load(ART / "fill9_00L.png"), ignore)
    print("00L MAD", mad)
    out00[y0:y1, x0:x1] = aligned

    for stem, arr in [("cream_22-01-35_nopots", out35), ("cream_22-02-00_nopots", out00)]:
        for base in (OUT, ROOT, ART):
            save(arr, base / f"{stem}.png")
            save(arr, base / f"{stem}.jpg")
        print("saved", stem)

    print("done")


if __name__ == "__main__":
    main()
