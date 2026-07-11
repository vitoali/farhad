#!/usr/bin/env python3
"""
Batch analyze all indicator .txt/.pine files in a directory.
Usage: python batch_analyze.py [directory]
Default directory: uploads + backtest/sources + indicators from index
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from analyze_code import CodeAnalysis, analyze_file

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
SOURCES = ROOT / "sources"
UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")

# Already analyzed manually in project journal (from chat + files)
KNOWN_INDEX = {
    "ut_bot_v2": {"id": 1, "name": "UT Bot v2", "source": "chat", "status": "done"},
    "alpha_trend": {"id": 2, "name": "AlphaTrend", "source": "chat", "status": "done"},
    "bj_bot_3commas": {"id": 3, "name": "Bj Bot / 3Commas", "source": "chat", "status": "done"},
    "forge_v1.pine": {"id": 4, "name": "AlphaX FORGE", "source": "file", "status": "done"},
    "forg_6b2d.txt": {"id": 4, "name": "AlphaX FORGE", "source": "file", "status": "done"},
    "fib_fib.pine": {"id": 5, "name": "FibFib / AutoFib", "source": "chat", "status": "done"},
    "quadapt_ml_trader.pine": {"id": 6, "name": "Quadapt ML Trader", "source": "file", "status": "done"},
    "quadpad_47cd.txt": {"id": 6, "name": "Quadapt ML Trader", "source": "file", "status": "done"},
    "quadpad_9f11.txt": {"id": 6, "name": "Quadapt ML Trader", "source": "file", "status": "duplicate"},
}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def analysis_to_dict(a: CodeAnalysis, fh: str) -> dict:
    return {
        "file": a.file,
        "name": a.name,
        "pine_version": a.pine_version,
        "script_type": a.script_type,
        "lines": a.line_count,
        "complete": a.complete,
        "completeness_issues": a.completeness_issues,
        "category": a.indicator_category,
        "has_buy_sell": a.has_buy_sell,
        "has_sl_tp": a.has_sl_tp,
        "has_ob": a.has_order_block,
        "has_fvg": a.has_fvg,
        "has_fib": a.has_fib,
        "has_confirmed": a.has_barstate_confirmed,
        "backtestable": a.backtestable,
        "notes": a.notes,
        "hash": fh,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_files(dirs: list[Path]) -> list[Path]:
    seen_hash: set[str] = set()
    files: list[Path] = []
    for d in dirs:
        if not d.exists():
            continue
        for ext in ("*.txt", "*.pine"):
            for p in sorted(d.glob(ext)):
                h = file_hash(p)
                if h in seen_hash:
                    continue
                seen_hash.add(h)
                files.append(p)
    return files


def main():
    extra = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    dirs = [UPLOADS, SOURCES]
    if extra:
        dirs.insert(0, extra)

    files = collect_files(dirs)
    analyses: list[dict] = []
    incomplete: list[dict] = []
    duplicates: list[str] = []

    print(f"=== Batch analyze: {len(files)} unique files ===\n")

    for path in files:
        a = analyze_file(path)
        fh = file_hash(path)
        d = analysis_to_dict(a, fh)

        known = KNOWN_INDEX.get(path.name)
        if known:
            d["registry_id"] = known["id"]
            d["registry_status"] = known["status"]
            if known.get("status") == "duplicate":
                duplicates.append(path.name)

        analyses.append(d)

        status = "✅" if a.complete else "❌ ناقص"
        print(f"{status} {path.name}")
        print(f"   نام: {a.name} | نوع: {a.indicator_category} | خطوط: {a.line_count}")
        print(f"   بک‌تست: {a.backtestable} | سیگنال: {a.has_buy_sell} | SL/TP: {a.has_sl_tp}")
        if a.completeness_issues:
            for issue in a.completeness_issues:
                print(f"   ⚠ {issue}")
            incomplete.append({"file": path.name, "name": a.name, "issues": a.completeness_issues})
        print()

    out = {
        "total_files": len(files),
        "complete": sum(1 for x in analyses if x["complete"]),
        "incomplete": len(incomplete),
        "known_analyzed": 6,
        "target_total": 60,
        "pending": max(0, 60 - 6 - len([x for x in analyses if x["file"] not in KNOWN_INDEX])),
        "duplicates_skipped": duplicates,
        "incomplete_files": incomplete,
        "analyses": analyses,
    }

    out_path = RESULTS / "INDICATOR_INDEX.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {out_path}")

    # Markdown summary
    md = [
        "# فهرست اندیکاتورها — batch",
        "",
        f"تاریخ: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"فایل‌های اسکن‌شده: **{len(files)}** | کامل: **{out['complete']}** | ناقص: **{out['incomplete']}**",
        f"تحلیل‌شده قبلی: **6** | هدف: **~60**",
        "",
        "## فایل‌های ناقص",
        "",
    ]
    if incomplete:
        for item in incomplete:
            md.append(f"- **{item['file']}** ({item['name']})")
            for iss in item["issues"]:
                md.append(f"  - {iss}")
    else:
        md.append("- (هیچ — در فایل‌های فعلی)")
    md.extend(["", "## همه فایل‌ها", "", "| فایل | نام | کامل | دسته | بک‌تست |", "|------|-----|------|------|--------|"])
    for x in analyses:
        md.append(
            f"| {x['file']} | {x['name'][:40]} | {'✅' if x['complete'] else '❌'} | {x['category']} | {x['backtestable']} |"
        )
    (RESULTS / "INDICATOR_INDEX.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Saved: {RESULTS / 'INDICATOR_INDEX.md'}")


if __name__ == "__main__":
    main()
