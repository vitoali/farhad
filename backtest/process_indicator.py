#!/usr/bin/env python3
"""Analyze + backtest one indicator file; append to learning journal."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyze_code import analyze_file
from config import CRYPTO_SL_PCT, CRYPTO_TP_PCT, FOREX_SL_PIPS, FOREX_TP_RR
from engine import aggregate, simulate_fixed_sl_tp
from fetch_data import fetch_all
from run_backtest import SYMBOL_MARKET, TIMEFRAMES, result_to_dict, run_indicator

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
RESULTS = ROOT / "results"
ANALYSES = RESULTS / "analyses"
QUEUE = RESULTS / "ANALYSIS_QUEUE.md"
REGISTRY = RESULTS / "processed_registry.json"

# Maps source filename -> run_backtest indicator key (when ported)
PORT_MAP: dict[str, str] = {
    "AlphaTrend_b53f.txt": "alpha_trend",
    "2_297c.txt": "bj_bot",
    "forg_6b2d.txt": "forge",
    "fib_fib.pine": "fib_fib",
    "quadpad_47cd.txt": "quadapt",
    "SUPER_TREND_ccf2.txt": "supertrend",
    "Chandelier_Exit_a3e4.txt": "chandelier_exit",
    "Machine_Learning_Lorentzian_9f8e.txt": "lorentzian",
    "IFVG_ENGINE_6b53.txt": "ifvg",
    "Breaker_Blocks_with_Signals__LuxAlgo_103c.txt": "breaker_blocks",
    "Money_Concepts_PRO_v2.tiktok0_9e67.txt": "smc_pro",
    "Zero_Lag_Trend_Signals_TIKTOK_8b12.txt": "zero_lag",
    "Trendline_Breakouts_With__df18.txt": "trendline_breakout",
    "rsi_advanced_868b.txt": "rsi_advanced",
    "machin_rsi_313b.txt": "ml_rsi",
    "machin_learning_rsi_217a.txt": "ml_rsi",
}

KNOWN_DONE = {
    "ut_bot_v2": 1,
    "alpha_trend": 2,
    "bj_bot": 3,
    "forge": 4,
    "fib_fib": 5,
    "quadapt": 6,
    "supertrend": 7,
    "chandelier_exit": 8,
    "lorentzian": 9,
    "ifvg": 10,
    "breaker_blocks": 11,
    "smc_pro": 12,
    "zero_lag": 13,
    "trendline_breakout": 14,
    "rsi_advanced": 15,
    "ml_rsi": 17,
}


def load_registry() -> dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"processed": [], "next_id": 10}


def save_registry(reg: dict) -> None:
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def find_source(filename: str) -> Path | None:
    for d in (SOURCES, Path("/home/ubuntu/.cursor/projects/workspace/uploads")):
        p = d / filename
        if p.exists():
            return p
    return None


def write_analysis_md(
    path: Path,
    seq_id: int,
    analysis,
    backtest_rows: list[dict],
    port_key: str | None,
) -> None:
    ANALYSES.mkdir(parents=True, exist_ok=True)
    out = ANALYSES / f"{seq_id:02d}_{path.stem}.md"
    lines = [
        f"# #{seq_id} {analysis.name}",
        "",
        f"**فایل:** `{path.name}`",
        f"**تاریخ:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**نوع:** {analysis.script_type} | Pine v{analysis.pine_version}",
        f"**دسته:** {analysis.indicator_category}",
        f"**کامل:** {'بله' if analysis.complete else 'خیر'}",
        f"**بک‌تست:** {analysis.backtestable}",
        "",
        "## ویژگی‌های فنی",
        "",
        f"- سیگنال buy/sell: {analysis.has_buy_sell}",
        f"- SL/TP در کد: {analysis.has_sl_tp}",
        f"- Order Block: {analysis.has_order_block}",
        f"- FVG: {analysis.has_fvg}",
        f"- Fib: {analysis.has_fib}",
        f"- barstate.isconfirmed: {analysis.has_barstate_confirmed}",
        f"- request.security: {analysis.has_request_security}",
        "",
    ]
    if analysis.completeness_issues:
        lines.extend(["## مشکلات کامل بودن", ""])
        for iss in analysis.completeness_issues:
            lines.append(f"- {iss}")
        lines.append("")

    if analysis.notes:
        lines.extend(["## یادداشت‌های تحلیل استاتیک", ""])
        for n in analysis.notes:
            lines.append(f"- {n}")
        lines.append("")

    if backtest_rows:
        lines.extend(["## نتایج بک‌تست (~۳۱ روز)", "", "| نماد | TF | معاملات | WR% | PF |", "|------|-----|---------|-----|-----|"])
        for r in sorted(backtest_rows, key=lambda x: (x["symbol"], x["timeframe"])):
            lines.append(
                f"| {r['symbol']} | {r['timeframe']} | {r['total_trades']} | {r['win_rate']} | {r['profit_factor']} |"
            )
        valid = [r for r in backtest_rows if r["total_trades"] >= 3]
        if valid:
            best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
            worst = min(valid, key=lambda x: x["profit_factor"])
            lines.extend([
                "",
                f"**بهترین:** {best['symbol']} {best['timeframe']} PF={best['profit_factor']}",
                f"**ضعیف‌ترین:** {worst['symbol']} {worst['timeframe']} PF={worst['profit_factor']}",
            ])
        lines.append("")
    elif port_key:
        lines.extend(["## بک‌تست", "", "پورت Python هنوز پیاده نشده — فقط تحلیل استاتیک.", ""])
    else:
        lines.extend(["## بک‌تست", "", "نیاز به پورت دستی یا بک‌تستر zone/pattern.", ""])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_backtests_for(port_key: str, data: dict | None = None) -> list[dict]:
    if data is None:
        data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    rows: list[dict] = []
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        for tf, df in tfs.items():
            if df is None or len(df) < 50:
                continue
            try:
                r = run_indicator(port_key, df, sym, tf, market)
                rows.append(result_to_dict(r))
            except Exception as e:
                rows.append({
                    "indicator": port_key,
                    "symbol": sym,
                    "timeframe": tf,
                    "market": market,
                    "total_trades": 0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "notes": [str(e)],
                })
    return rows


def process_file(filename: str, skip_backtest: bool = False, data: dict | None = None) -> dict:
    path = find_source(filename)
    if not path:
        raise FileNotFoundError(f"Not found: {filename}")

    reg = load_registry()
    if filename in reg.get("processed", []):
        print(f"Already processed: {filename}")
        return {"file": filename, "status": "skipped"}

    analysis = analyze_file(path)
    port_key = PORT_MAP.get(filename)
    seq_id = KNOWN_DONE.get(port_key) if port_key else reg.get("next_id", 10)

    backtest_rows: list[dict] = []
    if port_key and not skip_backtest and analysis.complete:
        backtest_rows = run_backtests_for(port_key, data=data)

    md_path = write_analysis_md(path, seq_id, analysis, backtest_rows, port_key)

    entry = {
        "id": seq_id,
        "file": filename,
        "name": analysis.name,
        "port": port_key,
        "complete": analysis.complete,
        "category": analysis.indicator_category,
        "backtestable": analysis.backtestable,
        "analysis_md": str(md_path.relative_to(ROOT)),
        "backtest_count": len(backtest_rows),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    processed = reg.setdefault("processed", [])
    processed.append(filename)
    if not port_key or port_key not in KNOWN_DONE:
        reg["next_id"] = max(reg.get("next_id", 10), seq_id + 1)

    save_registry(reg)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return entry


def main():
    parser = argparse.ArgumentParser(description="Process one indicator file")
    parser.add_argument("filename", help="e.g. SUPER_TREND_ccf2.txt")
    parser.add_argument("--skip-backtest", action="store_true")
    parser.add_argument("--next", type=int, default=0, help="Process N next unprocessed complete files")
    args = parser.parse_args()

    if args.next > 0:
        from batch_analyze import collect_files, KNOWN_INDEX

        files = collect_files([SOURCES])
        reg = load_registry()
        done = set(reg.get("processed", [])) | set(KNOWN_INDEX.keys())
        pending = []
        for p in files:
            a = analyze_file(p)
            if a.complete and p.name not in done:
                pending.append(p.name)
        print(f"Pending complete files: {len(pending)}")
        data = None if args.skip_backtest else fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
        for fn in pending[: args.next]:
            process_file(fn, skip_backtest=args.skip_backtest, data=data)
        return

    process_file(args.filename, skip_backtest=args.skip_backtest)


if __name__ == "__main__":
    main()
