"""Static analysis of Pine Script indicator files."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodeAnalysis:
    file: str
    name: str = ""
    pine_version: str = ""
    script_type: str = ""  # indicator, strategy, study
    line_count: int = 0
    complete: bool = True
    completeness_issues: list[str] = field(default_factory=list)
    indicator_category: str = ""  # trend, zone, pattern, strategy, ml, fib, other
    has_buy_sell: bool = False
    has_request_security: bool = False
    has_barstate_confirmed: bool = False
    has_sl_tp: bool = False
    has_order_block: bool = False
    has_fvg: bool = False
    has_fib: bool = False
    has_repaint_risk: bool = False
    backtestable: str = "unknown"  # full, partial, none
    notes: list[str] = field(default_factory=list)


def _extract_title(text: str) -> str:
    for pat in [
        r'indicator\s*\(\s*title\s*=\s*["\']([^"\']+)',
        r'strategy\s*\(\s*["\']([^"\']+)',
        r'study\s*\(\s*["\']([^"\']+)',
        r'study\s*\(\s*title\s*=\s*["\']([^"\']+)',
        r'indicator\s*\(\s*["\']([^"\']+)',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).strip()
    return Path("").stem


def _check_completeness(text: str) -> list[str]:
    issues = []
    if len(text.strip()) < 50:
        issues.append("فایل خیلی کوتاه — احتمالاً ناقص")
    if not re.search(r"//@version|study\s*\(|indicator\s*\(|strategy\s*\(", text, re.I):
        issues.append("هدر Pine (@version / indicator / strategy) پیدا نشد")
    if text.count("{") != text.count("}"):
        issues.append(f"براکت {{}} نامتعادل: {{={text.count('{')} }}={text.count('}')}")
    if text.count("(") - text.count(")") > 5:
        issues.append("پرانتز باز بیش از حد — احتمال قطع شدن انتهای فایل")
    lines = text.strip().splitlines()
    if lines:
        last = lines[-1].strip()
        if last and not last.endswith((")", "}", "//", '"""', "'''", ",")) and "end" not in last.lower():
            if re.search(r":=\s*$|=\s*$|\+\s*$|and\s*$|or\s*$", last):
                issues.append(f"خط آخر ناقص به نظر می‌رسد: {last[:60]}")
    if "..." in text[-200:]:
        issues.append("ممکن است بخشی حذف شده (…)")
    return issues


def _categorize(text: str) -> tuple[str, str]:
    t = text.lower()
    if any(x in t for x in ["order block", "order_block", "ob_", "fvg", "fair value", "imbalance"]):
        if "fvg" in t or "fair value" in t:
            return "zone", "fvg_ob"
        return "zone", "order_block"
    if any(x in t for x in ["double top", "double bottom", "head & shoulder", "patternresult", "head and shoulder"]):
        return "pattern", "chart_pattern"
    if any(x in t for x in ["fibonacci", "fib_", "autoFib", "retracement"]):
        return "zone", "fibonacci"
    if any(x in t for x in ["strategy.entry", "strategy.exit", "3commas"]):
        return "strategy", "full_strategy"
    if any(x in t for x in ["svr", "machine learning", "mlma", "regressor", "kernel"]):
        return "ml", "ml_regression"
    if any(x in t for x in ["crossover", "trailing stop", "tsl", "alphatrend", "ut bot"]):
        return "trend", "trend_signal"
    if any(x in t for x in ["supply", "demand", "liquidity", "sweep"]):
        return "zone", "smc"
    return "other", "uncategorized"


def _backtest_capability(text: str, category: str, issues: list[str]) -> str:
    if issues:
        return "blocked_incomplete"
    if category in ("strategy",):
        return "partial_native"
    if category in ("trend",):
        return "full_simplified"
    if category in ("pattern",):
        return "partial_pattern"
    if category in ("zone",) and "fibonacci" in text.lower():
        return "partial_zone"
    if category == "ml":
        return "partial_core_only"
    if "plot(" in text and "buy" not in text.lower() and "signal" not in text.lower():
        return "none_display_only"
    return "partial_manual"


def analyze_file(path: Path) -> CodeAnalysis:
    text = path.read_text(encoding="utf-8", errors="replace")
    issues = _check_completeness(text)
    cat, sub = _categorize(text)
    vm = re.search(r"//@version\s*=\s*(\d+)", text)
    st = "indicator"
    if re.search(r"\bstrategy\s*\(", text):
        st = "strategy"
    elif re.search(r"\bstudy\s*\(", text):
        st = "study"

    a = CodeAnalysis(
        file=path.name,
        name=_extract_title(text),
        pine_version=vm.group(1) if vm else "?",
        script_type=st,
        line_count=len(text.splitlines()),
        complete=len(issues) == 0,
        completeness_issues=issues,
        indicator_category=f"{cat}/{sub}",
        has_buy_sell=bool(re.search(r"\b(buy|sell|long|short).*(signal|Signal)", text)),
        has_request_security="request.security" in text,
        has_barstate_confirmed="barstate.isconfirmed" in text,
        has_sl_tp=bool(re.search(r"stop|take.?profit|strategy\.exit|sl_|tp_", text, re.I)),
        has_order_block=bool(re.search(r"order.?block|order_block", text, re.I)),
        has_fvg=bool(re.search(r"fvg|fair.?value", text, re.I)),
        has_fib=bool(re.search(r"fibonacci|fib_|retracement", text, re.I)),
        has_repaint_risk="request.security" in text and "lookahead_off" not in text,
        backtestable=_backtest_capability(text, cat.split("/")[0], issues),
    )
    if a.has_repaint_risk:
        a.notes.append("ریسک lookahead در request.security")
    if not a.has_barstate_confirmed and a.has_buy_sell:
        a.notes.append("سیگنال بدون barstate.isconfirmed")
    return a


def analyze_directory(directory: Path) -> list[CodeAnalysis]:
    results = []
    for path in sorted(directory.glob("*.txt")) + sorted(directory.glob("*.pine")):
        if path.is_file():
            results.append(analyze_file(path))
    return results
