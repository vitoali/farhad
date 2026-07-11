#!/usr/bin/env python3
"""Backtest Farhad Combo + Master Strategy vs baselines."""
from __future__ import annotations

import json
from pathlib import Path

from engine import aggregate, simulate_bj_native
from farhad_strategy import farhad_combo_signals
from farhad_master_strategy import farhad_master_signals
from fetch_data import fetch_all
from indicators import bj_bot_signals
from run_backtest import SYMBOL_MARKET, TIMEFRAMES, result_to_dict, run_indicator
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
MODES = ["loose", "standard", "strict", "master", "master_strict"]
PRIORITY_TFS = ["1h", "4h"]


def run_mode(mode: str, data: dict) -> list[dict]:
    rows: list[dict] = []
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        novol = market == "forex" or sym == "BEATUSDT"
        for tf, df in tfs.items():
            if df is None or len(df) < 80:
                continue
            if mode.startswith("master"):
                sig = farhad_master_signals(df, mode=mode, novolumedata=novol)
                zlist = extract_zone_signals_from_df(sig)
                trades = simulate_zone_native(df, zlist, market)
                r = aggregate(trades, f"farhad_{mode}", sym, tf, market)
                r.notes.append(f"n={len(zlist)}")
            else:
                sig = farhad_combo_signals(df, mode=mode, novolumedata=novol)
                trades = simulate_bj_native(sig)
                r = aggregate(trades, f"farhad_{mode}", sym, tf, market)
            rows.append(result_to_dict(r))
    return rows


def run_rsi_baseline(data: dict) -> list[dict]:
    rows: list[dict] = []
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        for tf, df in tfs.items():
            if df is None or len(df) < 80:
                continue
            r = run_indicator("rsi_advanced", df, sym, tf, market)
            rows.append(result_to_dict(r))
    return rows


def run_bj_baseline(data: dict) -> list[dict]:
    rows: list[dict] = []
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        for tf, df in tfs.items():
            if df is None or len(df) < 80:
                continue
            sig = bj_bot_signals(df)
            trades = simulate_bj_native(sig)
            r = aggregate(trades, "bj_bot_baseline", sym, tf, market)
            rows.append(result_to_dict(r))
    return rows


def summarize(rows: list[dict], label: str) -> dict:
    valid = [r for r in rows if r["total_trades"] >= 3]
    if not valid:
        return {"label": label, "status": "insufficient", "runs": len(rows)}
    avg_wr = sum(r["win_rate"] for r in valid) / len(valid)
    pfs = [r["profit_factor"] for r in valid if r["profit_factor"] < 900]
    avg_pf = sum(pfs) / max(1, len(pfs))
    best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
    pri = [r for r in valid if r["timeframe"] in PRIORITY_TFS]
    pri_pf = sum(r["profit_factor"] for r in pri if r["profit_factor"] < 900) / max(1, len([r for r in pri if r["profit_factor"] < 900]))
    return {
        "label": label,
        "avg_wr": round(avg_wr, 1),
        "avg_pf": round(avg_pf, 3),
        "priority_tf_pf": round(pri_pf, 3),
        "best": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}%",
        "total_trades": sum(r["total_trades"] for r in valid),
        "samples": len(valid),
    }


def main():
    print("Fetching OHLCV (~31 days)...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)

    all_results: dict[str, list[dict]] = {}
    all_results["rsi_advanced_baseline"] = run_rsi_baseline(data)
    all_results["bj_bot_baseline"] = run_bj_baseline(data)
    for mode in MODES:
        print(f"\n=== farhad_{mode} ===")
        rows = run_mode(mode, data)
        all_results[f"farhad_{mode}"] = rows
        for r in rows:
            if r["total_trades"] > 0:
                print(f"  {r['symbol']:8} {r['timeframe']:4} trades={r['total_trades']:3} WR={r['win_rate']:5.1f}% PF={r['profit_factor']}")

    summaries = {k: summarize(v, k) for k, v in all_results.items()}
    out = {"summaries": summaries, "results": all_results}
    path = RESULTS / "backtest_farhad_combo.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== Comparison ===")
    for k, s in summaries.items():
        if s.get("status"):
            print(f"  {k:22} insufficient")
        else:
            print(f"  {k:22} avg_PF={s['avg_pf']} 1h/4h_PF={s['priority_tf_pf']} trades={s['total_trades']} best={s['best']}")


if __name__ == "__main__":
    main()
