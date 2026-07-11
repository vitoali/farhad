#!/usr/bin/env python3
"""Append static-analysis journal entries for all complete unported indicator files."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from analyze_code import analyze_file
from batch_pipeline import INDICATOR_REGISTRY

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
JOURNAL = ROOT / "results" / "LEARNING_JOURNAL.md"
REGISTRY = ROOT / "results" / "processed_registry.json"


def main():
    text = JOURNAL.read_text(encoding="utf-8") if JOURNAL.exists() else ""
    if "## فهرست استاتیک" not in text:
        text += "\n\n---\n\n## فهرست استاتیک (بدون پورت Python)\n\n"
        text += "اندیکاتورهای زیر تحلیل استاتیک شدند. اکثراً visualization-only یا نیاز به پورت دستی دارند.\n\n"
        text += "| # | فایل | نام | دسته | بک‌تست | یادداشت |\n"
        text += "|---|------|-----|------|--------|--------|\n"

    ported = set(INDICATOR_REGISTRY.keys())
    seq = 40
    rows = []
    for p in sorted(SOURCES.glob("*")):
        if p.suffix not in (".txt", ".pine"):
            continue
        if p.name in ported:
            continue
        a = analyze_file(p)
        if not a.complete:
            continue
        seq += 1
        note = (a.notes[0][:60] if a.notes else "visualization / manual port") + "…" if a.notes else "visualization / manual port"
        rows.append(f"| {seq} | `{p.name}` | {a.name[:35]} | {a.indicator_category} | {a.backtestable} | {note} |")

    # append only new rows not already in journal by filename
    for row in rows:
        fname = row.split("`")[1]
        if fname in text:
            continue
        text += row + "\n"

    text += f"\n\n_آخرین به‌روزرسانی استاتیک: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n"
    JOURNAL.write_text(text, encoding="utf-8")
    print(f"Static journal: {len(rows)} unported complete files documented")


if __name__ == "__main__":
    main()
