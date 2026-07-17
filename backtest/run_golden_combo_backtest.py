#!/usr/bin/env python3
"""Backtest Golden Combo MTF strategy on EURUSD / XAUUSD / USDJPY."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from engine import aggregate
from fetch_data import fetch_all
from golden_combo_strategy import SCENARIOS, golden_combo_signals
from run_backtest import result_to_dict
from run_forex_three_indicators import pip_size, simulate_forex
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
SYMBOLS = ["EURUSD", "XAUUSD", "USDJPY"]
STRUCTURE_MODES = ["4h", "1h"]


def run_golden(data: dict, structure_tf: str) -> list[dict]:
    rows: list[dict] = []
    label = f"golden_combo_{structure_tf}"
    for sym in SYMBOLS:
        entry_df = data.get(sym, {}).get("15m")
        confirm_df = data.get(sym, {}).get("1h")
        struct_df = data.get(sym, {}).get(structure_tf)
        if entry_df is None or confirm_df is None or struct_df is None:
            continue
        if len(entry_df) < 120 or len(confirm_df) < 50 or len(struct_df) < 20:
            continue
        sig = golden_combo_signals(entry_df, confirm_df, struct_df, structure_tf=structure_tf)
        zlist = extract_zone_signals_from_df(sig)
        if zlist:
            trades = simulate_zone_native(entry_df, zlist, "forex")
        else:
            trades = simulate_forex(entry_df, sig["buy"], sig["sell"], sym)
        r = aggregate(trades, label, sym, "15m", "forex")
        n_sig = int(sig["buy"].sum()) + int(sig["sell"].sum())
        scenarios = sig["scenario"].value_counts().to_dict() if "scenario" in sig.columns else {}
        r.notes.append(f"signals={n_sig} struct={structure_tf} scenarios={scenarios}")
        rows.append(result_to_dict(r))
    return rows


def scenario_breakdown(data: dict, structure_tf: str) -> dict:
    out: dict[str, list] = defaultdict(list)
    for sym in SYMBOLS:
        entry_df = data[sym]["15m"]
        confirm_df = data[sym]["1h"]
        struct_df = data[sym][structure_tf]
        sig = golden_combo_signals(entry_df, confirm_df, struct_df, structure_tf=structure_tf)
        for sc in sig["scenario"].unique():
            if not sc:
                continue
            mask = sig["scenario"] == sc
            sub = sig.copy()
            sub["buy"] = sig["buy"] & mask
            sub["sell"] = sig["sell"] & mask
            zlist = extract_zone_signals_from_df(sub)
            trades = simulate_zone_native(entry_df, zlist, "forex") if zlist else []
            if trades:
                r = aggregate(trades, sc, sym, "15m", "forex")
                out[sc].append({
                    "symbol": sym,
                    "trades": r.total_trades,
                    "wr": round(r.win_rate, 1),
                    "pf": round(r.profit_factor, 3) if r.profit_factor < 900 else 999,
                })
    return dict(out)


def main():
    tfs = ["15m", "1h", "4h"]
    print(f"Fetching {SYMBOLS} — {tfs} (~31 days)...")
    data = fetch_all(days=31, timeframes=tfs, force=False)

    all_rows: list[dict] = []
    summaries: dict = {}
    scenario_stats: dict = {}

    for st in STRUCTURE_MODES:
        rows = run_golden(data, st)
        all_rows.extend(rows)
        valid = [r for r in rows if r["total_trades"] >= 1]
        if valid:
            best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
            summaries[f"struct_{st}"] = {
                "best": f"{best['symbol']} PF={best['profit_factor']} WR={best['win_rate']}% trades={best['total_trades']}",
                "avg_pf": round(float(sum(r["profit_factor"] for r in valid if r["profit_factor"] < 900) / len(valid)), 3),
                "total_trades": sum(r["total_trades"] for r in valid),
            }
        else:
            summaries[f"struct_{st}"] = {"status": "no_trades"}
        scenario_stats[st] = scenario_breakdown(data, st)

    out = {
        "period_days": 31,
        "entry_tf": "15m",
        "confirm_tf": "1h",
        "structure_modes": STRUCTURE_MODES,
        "scenarios": SCENARIOS,
        "summaries": summaries,
        "scenario_stats": scenario_stats,
        "results": all_rows,
    }
    path = RESULTS / "backtest_golden_combo.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}\n")

    print("=== Golden Combo MTF (15m entry) ===")
    for st, s in summaries.items():
        print(f"  {st}: {s}")

    print("\n=== Per-scenario breakdown ===")
    for st, stats in scenario_stats.items():
        print(f"\n  Structure TF: {st}")
        for sc, items in stats.items():
            desc = SCENARIOS.get(sc, sc)
            for it in items:
                print(f"    {sc} ({desc}): {it['symbol']} trades={it['trades']} WR={it['wr']}% PF={it['pf']}")


if __name__ == "__main__":
    main()
