#!/usr/bin/env python3
"""Detect truncated/incomplete Pine uploads by size heuristics."""
from __future__ import annotations

import json
import re
from pathlib import Path

UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
OUT = Path(__file__).parent / "results" / "INCOMPLETE_REPORT.json"

# Files under this line count with complex headers are likely truncated
SUSPICIOUS_MAX_LINES = {94, 109, 110, 162, 426}
MIN_LINES_FOR_FULL = {
    "strategy": 150,
    "library": 200,
    "indicator": 80,
}


def detect_truncation(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    issues = []
    n = len(lines)

    if n in SUSPICIOUS_MAX_LINES:
        issues.append(f"تعداد خط مشکوک ({n}) — احتمال قطع شدن هنگام آپلود")

    if lines:
        last = lines[-1].strip()
        if re.search(r":=\s*$|=\s*$|,\s*$|and\s*$|or\s*$|for\s+\w+\s*=\s*$", last):
            issues.append(f"خط آخر ناقص: {last[:70]}")

    if "library(" in text and n < 200:
        issues.append("کتابخانه Pine (library) ناقص — به‌تنهایی اجرا نمی‌شود")

    if n < 30 and ("indicator(" in text or "strategy(" in text):
        issues.append("فایل خیلی کوتاه برای اندیکاتور کامل")

  # Known complete short scripts
    if path.name in ("AUTO_FIBO_ca53.txt", "fib_fib.pine") and n < 30:
        return []  # FibFib is intentionally short

    return issues


def main():
    rows = []
    for path in sorted(UPLOADS.glob("*.txt")):
        issues = detect_truncation(path)
        title_m = re.search(r'indicator\s*\([^)]*["\']([^"\']+)', path.read_text(encoding="utf-8", errors="replace")[:3000])
        rows.append({
            "file": path.name,
            "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines()),
            "incomplete": len(issues) > 0,
            "issues": issues,
        })

    incomplete = [r for r in rows if r["incomplete"]]
    out = {
        "total": len(rows),
        "incomplete_count": len(incomplete),
        "complete_count": len(rows) - len(incomplete),
        "incomplete_files": incomplete,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# گزارش فایل‌های ناقص\n", f"کل: **{len(rows)}** | ناقص: **{len(incomplete)}** | کامل: **{len(rows)-len(incomplete)}**\n"]
    for r in incomplete:
        md.append(f"## `{r['file']}` ({r['lines']} خط)")
        for i in r["issues"]:
            md.append(f"- {i}")
        md.append("")
    (OUT.parent / "INCOMPLETE_REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Incomplete: {len(incomplete)}/{len(rows)}")
    for r in incomplete:
        print(f"  ❌ {r['file']} ({r['lines']} lines)")


if __name__ == "__main__":
    main()
