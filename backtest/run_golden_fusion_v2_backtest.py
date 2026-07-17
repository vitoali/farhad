#!/usr/bin/env python3
"""Golden Fusion v2 — CM Ultimate + Cardwell + Elliott + EWO/RSI."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from engine import aggregate, simulate_fixed_sl_tp
from fetch_data import fetch_all
from golden_combo_strategy import SCENARIOS, golden_combo_signals
from run_backtest import result_to_dict
from run_forex_three_indicators import simulate_forex
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
CRYPTO = ["BTCUSDT", "SOLUSDT"]
FOREX = ["EURUSD", "XAUUSD", "USDJPY"]
STRUCTURE_MODES = ["4h", "1h"]


def simulate(df, buy, sell, sym: str, market: str):
    z = extract_zone_signals_from_df(df.assign(buy=buy, sell=sell))
    if z:
        return simulate_zone_native(df, z, market)
    if market == "forex":
        return simulate_forex(df, buy, sell, sym)
    return simulate_fixed_sl_tp(df, buy, sell, market)


def run_one(data, sym, market, structure_tf, v2: bool, entry_gold: bool, require_div: bool) -> dict | None:
    e, c, s = data[sym].get("15m"), data[sym].get("1h"), data[sym].get(structure_tf)
    if e is None or c is None or s is None or len(e) < 120:
        return None
    kw = dict(
        structure_tf=structure_tf,
        use_cardwell=True,
        use_cm_ultimate=v2,
        require_macd_div_s1s2=require_div,
        require_entry_ultimate_gold=entry_gold,
    )
    sig = golden_combo_signals(e, c, s, **kw)
    n = int(sig["buy"].sum()) + int(sig["sell"].sum())
    trades = simulate(e, sig["buy"], sig["sell"], sym, market)
    tag = f"fusion_v2_{structure_tf}" if v2 else f"fusion_v1_{structure_tf}"
    if entry_gold:
        tag += "_entry_gold"
    r = aggregate(trades, tag, sym, "15m", market)
    d = result_to_dict(r)
    d["signals"] = n
    d["scenarios"] = {k: int(v) for k, v in sig["scenario"].value_counts().items() if k}
    d["version"] = "v2" if v2 else "v1"
    d["structure_tf"] = structure_tf
    d["entry_gold_required"] = entry_gold
    return d


def scenario_breakdown(data, sym, market, structure_tf, v2, entry_gold) -> list[dict]:
    e, c, s = data[sym]["15m"], data[sym]["1h"], data[sym][structure_tf]
    sig = golden_combo_signals(
        e, c, s,
        structure_tf=structure_tf,
        use_cardwell=True,
        use_cm_ultimate=v2,
        require_macd_div_s1s2=not v2,
        require_entry_ultimate_gold=entry_gold,
    )
    out = []
    for sc in sig["scenario"].unique():
        if not sc:
            continue
        sub = sig.copy()
        sub["buy"] = sig["buy"] & (sig["scenario"] == sc)
        sub["sell"] = sig["sell"] & (sig["scenario"] == sc)
        trades = simulate(e, sub["buy"], sub["sell"], sym, market)
        if trades:
            r = aggregate(trades, sc, sym, "15m", market)
            out.append({"scenario": sc, "trades": r.total_trades, "wr": round(r.win_rate, 1), "pf": round(r.profit_factor, 3)})
    return out


def main():
    tfs = ["15m", "1h", "4h"]
    print("Golden Fusion v2 backtest (~31 days)...")
    data = fetch_all(days=31, timeframes=tfs, force=False)

    configs = [
        ("v1_no_div", False, False, False),
        ("v2_ultimate", True, False, False),
        ("v2_ultimate_entry_gold", True, True, False),
    ]
    all_rows: list[dict] = []
    comparison: dict = {}

    for cfg_name, v2, entry_gold, require_div in configs:
        cfg_rows = []
        for st in STRUCTURE_MODES:
            for sym in CRYPTO + FOREX:
                market = "crypto" if sym in CRYPTO else "forex"
                d = run_one(data, sym, market, st, v2, entry_gold, require_div)
                if d:
                    cfg_rows.append(d)
                    all_rows.append(d)
                    if d["total_trades"] > 0:
                        print(f"  {cfg_name} {sym} {st}: trades={d['total_trades']} WR={d['win_rate']}% PF={d['profit_factor']} {d['scenarios']}")
        valid = [r for r in cfg_rows if r["total_trades"] >= 1]
        comparison[cfg_name] = {
            "total_trades": sum(r["total_trades"] for r in valid),
            "avg_wr": round(sum(r["win_rate"] for r in valid) / len(valid), 1) if valid else 0,
            "avg_pf": round(sum(r["profit_factor"] for r in valid if r["profit_factor"] < 900) / len(valid), 3) if valid else 0,
            "symbols_with_trades": len(valid),
        }

    scenario_stats = {}
    for st in STRUCTURE_MODES:
        scenario_stats[st] = {}
        for sym in CRYPTO + FOREX:
            market = "crypto" if sym in CRYPTO else "forex"
            scenario_stats[st][sym] = scenario_breakdown(data, sym, market, st, v2=True, entry_gold=False)

    out = {
        "period_days": 31,
        "strategy": "Golden Fusion v2 (CM Ultimate + Cardwell MA100 + Elliott + EWO/RSI)",
        "entry_tf": "15m",
        "confirm_tf": "1h",
        "comparison": comparison,
        "scenarios": SCENARIOS,
        "scenario_stats_v2": scenario_stats,
        "results": all_rows,
    }
    path = RESULTS / "backtest_golden_fusion_v2.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== Version comparison ===")
    for k, v in comparison.items():
        print(f"  {k}: trades={v['total_trades']} avg_WR={v['avg_wr']}% avg_PF={v['avg_pf']} symbols={v['symbols_with_trades']}")


if __name__ == "__main__":
    main()
