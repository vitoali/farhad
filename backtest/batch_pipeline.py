#!/usr/bin/env python3
"""Batch port registry, backtest all indicators, append learning journal."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from analyze_code import analyze_file
from fetch_data import fetch_all
from run_backtest import SYMBOL_MARKET, TIMEFRAMES, result_to_dict, run_indicator

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources"
RESULTS = ROOT / "results"
JOURNAL = RESULTS / "LEARNING_JOURNAL.md"

# filename -> (indicator_key, seq_id, title)
INDICATOR_REGISTRY: dict[str, tuple[str, int, str]] = {
  # Already ported (#1-19)
    "AlphaTrend_b53f.txt": ("alpha_trend", 2, "AlphaTrend"),
    "2_297c.txt": ("bj_bot", 3, "Bj Bot"),
    "forg_6b2d.txt": ("forge", 4, "FORGE"),
    "fib_fib.pine": ("fib_fib", 5, "FibFib"),
    "quadpad_47cd.txt": ("quadapt", 6, "Quadapt ML"),
    "SUPER_TREND_ccf2.txt": ("supertrend", 7, "SuperTrend"),
    "Chandelier_Exit_a3e4.txt": ("chandelier_exit", 8, "Chandelier Exit"),
    "Machine_Learning_Lorentzian_9f8e.txt": ("lorentzian", 9, "Lorentzian ML"),
    "IFVG_ENGINE_6b53.txt": ("ifvg", 10, "IFVG Engine"),
    "Breaker_Blocks_with_Signals__LuxAlgo_103c.txt": ("breaker_blocks", 11, "Breaker Blocks"),
    "Money_Concepts_PRO_v2.tiktok0_9e67.txt": ("smc_pro", 12, "SMC PRO v2"),
    "Zero_Lag_Trend_Signals_TIKTOK_8b12.txt": ("zero_lag", 13, "Zero Lag"),
    "Trendline_Breakouts_With__df18.txt": ("trendline_breakout", 14, "Trendline Breakout"),
    "rsi_advanced_868b.txt": ("rsi_advanced", 15, "RSI Advanced"),
    "monster_e007.txt": ("monster", 16, "Monster Trex"),
    "machin_rsi_313b.txt": ("ml_rsi", 17, "ML RSI Zeiierman"),
    "supply_demand_72be.txt": ("supply_demand", 18, "Supply/Demand Flux"),
    "strong_pulback_7019.txt": ("strong_pullback", 19, "Strong Pullback"),
    # New batch (#20+)
    "Cardwell_RSI_Trade_Navigator__MarkitTick_1c8f.txt": ("cardwell_rsi", 20, "Cardwell RSI Navigator"),
    "fvg_return_faf7.txt": ("fvg_retest", 21, "FVG Retest Engine"),
    "fvg_1bce.txt": ("fvg_retest", 21, "FVG Retest Engine"),
    "sop_hunt_9b71.txt": ("stop_hunt", 22, "Stop Hunt Radar"),
    "STOP_HUNT_e28b.txt": ("stop_hunt", 22, "Stop Hunt Radar"),
    "Smart_Money_Structure__GainzAlgo_4e52.txt": ("smart_money_structure", 23, "Smart Money Structure"),
    "Smart_Money_Concepts_PRO_979a.txt": ("smc_pro_alt", 24, "SMC PRO Confluence"),
    "matrix_d1c3.txt": ("matrix_fvg", 25, "OrderFlow FVG Matrix"),
    "ORDER_5f08.txt": ("matrix_fvg", 25, "OrderFlow FVG Matrix"),
    "PUT___CALL_VP_Levels_90f8.txt": ("put_call_vp", 26, "PUT/CALL VP Levels"),
    "Ranked_Order_Block_Zones__Zeiierman_9c77.txt": ("ranked_ob", 27, "Ranked Order Blocks"),
    "QQE_KHOOB_1aba.txt": ("qqe", 28, "QQE Signals"),
    "MACD_30e7.txt": ("macd_mtf", 29, "MACD MTF"),
    "power_order_bloc_151a.txt": ("power_ob", 30, "Power Order Blocks"),
    "suply_demand_zone_f0e7.txt": ("supply_demand", 18, "Supply/Demand Flux"),
    "LONG_SEL_285e.txt": ("strong_pullback", 19, "Strong Pullback"),
    "Support_and_Resistance_Levels_with_Breaks_9115.txt": ("sr_breaks", 31, "SR Breaks LuxAlgo"),
    "LIQUDITY_PPOOL_ce94.txt": ("liquidity_pool", 32, "Liquidity Pools LuxAlgo"),
    "TREND_007c.txt": ("slingshot", 33, "CM SlingShot"),
    "smart_ichimoko_d12e.txt": ("ichimoku_ml", 34, "Smart Ichimoku ML"),
    "Liquidity_Shift_Detection_eaf8.txt": ("liquidity_shift", 35, "Liquidity Shift Zeiierman"),
    "CM_Ultimate_MA_MTF_202b.txt": ("cm_ma_mtf", 36, "CM Ultimate MA MTF"),
    "UP_TEND_949b.txt": ("cm_ma_mtf", 36, "CM Ultimate MA MTF"),
}

ZONE_NATIVE_KEYS = {
    "ifvg", "breaker_blocks", "smc_pro", "trendline_breakout",
    "supply_demand", "strong_pullback", "fvg_retest", "stop_hunt",
    "smart_money_structure", "smc_pro_alt", "matrix_fvg", "ranked_ob", "power_ob",
    "cardwell_rsi",
}


def collect_complete_files() -> list[Path]:
    files = []
    for p in sorted(SOURCES.glob("*")):
        if p.suffix not in (".txt", ".pine"):
            continue
        a = analyze_file(p)
        if a.complete:
            files.append(p)
    return files


def run_all_backtests(data: dict | None = None) -> dict[str, list[dict]]:
    if data is None:
        print("Fetching OHLCV (~31 days)...")
        data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    # unique indicator keys
    keys = sorted({v[0] for v in INDICATOR_REGISTRY.values() if v[0] != "monster"})
    all_results: dict[str, list[dict]] = {k: [] for k in keys}
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        for tf, df in tfs.items():
            if df is None or len(df) < 50:
                continue
            for key in keys:
                try:
                    r = run_indicator(key, df, sym, tf, market)
                    all_results[key].append(result_to_dict(r))
                except Exception as e:
                    all_results[key].append({
                        "indicator": key, "symbol": sym, "timeframe": tf,
                        "market": market, "total_trades": 0, "win_rate": 0,
                        "profit_factor": 0, "notes": [str(e)],
                    })
    return all_results


def summarize_indicator(rows: list[dict]) -> dict:
    valid = [r for r in rows if r.get("total_trades", 0) >= 3]
    if not valid:
        return {"status": "insufficient", "samples": len(rows)}
    avg_wr = sum(r["win_rate"] for r in valid) / len(valid)
    pfs = [r["profit_factor"] for r in valid if r["profit_factor"] < 900]
    avg_pf = sum(pfs) / max(1, len(pfs))
    best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
    worst = min(valid, key=lambda x: x["profit_factor"])
    return {
        "avg_wr": round(avg_wr, 1),
        "avg_pf": round(avg_pf, 3),
        "best": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}%",
        "worst": f"{worst['symbol']} {worst['timeframe']} PF={worst['profit_factor']}",
        "samples": len(valid),
        "top5": sorted(valid, key=lambda x: -x["profit_factor"] if x["profit_factor"] < 900 else 0)[:5],
    }


def append_journal_entries(summaries: dict[str, dict], file_map: dict[str, tuple]) -> None:
    """Append new #20+ sections if not already present."""
    text = JOURNAL.read_text(encoding="utf-8") if JOURNAL.exists() else ""
    added = []
    seen_ids = set()
    for fname, (key, seq_id, title) in sorted(file_map.items(), key=lambda x: x[1][1]):
        if seq_id < 20 or seq_id in seen_ids:
            continue
        seen_ids.add(seq_id)
        marker = f"## #{seq_id} "
        if marker in text:
            continue
        s = summaries.get(key, {})
        if s.get("status") == "insufficient":
            block = f"""
---

## #{seq_id} {title}

**فایل:** `{fname}` | **کلید:** `{key}`

### وضعیت
- نمونه کافی برای بک‌تست نداشت (کمتر از ۳ معامله در اکثر ترکیب‌ها)
- تحلیل استاتیک در `results/analyses/`

"""
        else:
            rows = "| نماد | TF | معاملات | WR% | PF |\n|------|-----|---------|-----|-----|\n"
            for r in s.get("top5", []):
                rows += f"| {r['symbol']} | {r['timeframe']} | {r['total_trades']} | {r['win_rate']} | {r['profit_factor']} |\n"
            verdict = "نگه" if s.get("avg_pf", 0) >= 1.2 else "فیلتر/ترکیب" if s.get("avg_pf", 0) >= 0.9 else "ضعیف"
            block = f"""
---

## #{seq_id} {title}

**فایل:** `{fname}` | **کلید:** `{key}`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **{s.get('avg_wr', 0)}%** | میانگین PF: **{s.get('avg_pf', 0)}**
- بهترین: {s.get('best', 'n/a')}
- ضعیف‌ترین: {s.get('worst', 'n/a')}

{rows}
### نگه داریم / حذف / بهبود
- **{verdict}** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله

"""
        text += block
        added.append(seq_id)
    if added:
        JOURNAL.write_text(text, encoding="utf-8")
        print(f"Journal updated: added #{added}")


def main():
    files = collect_complete_files()
    print(f"Complete source files: {len(files)}")

    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    results = run_all_backtests(data)

    out_path = RESULTS / "backtest_batch_all.json"
    summaries = {k: summarize_indicator(v) for k, v in results.items()}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indicators": len(results),
        "summaries": summaries,
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {out_path}")

    append_journal_entries(summaries, INDICATOR_REGISTRY)

    print("\n=== Summary ===")
    for k, s in sorted(summaries.items(), key=lambda x: -x[1].get("avg_pf", 0) if isinstance(x[1].get("avg_pf"), (int, float)) else 0):
        if s.get("status"):
            print(f"  {k:22} insufficient")
        else:
            print(f"  {k:22} avg_PF={s['avg_pf']} best={s['best']}")


if __name__ == "__main__":
    main()
