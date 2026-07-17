#!/usr/bin/env python3
"""Golden Fusion v3 — high-WR CM MACD patterns + Elliott structure."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cm_macd_htf import build_hw_context
from engine import aggregate, simulate_fixed_sl_tp
from fetch_data import fetch_all
from golden_combo_strategy import golden_combo_signals
from run_backtest import result_to_dict
from run_forex_three_indicators import simulate_forex
from run_golden_fusion_v2_backtest import simulate

RESULTS = Path(__file__).parent / "results"
CRYPTO = ["BTCUSDT", "SOLUSDT"]
FOREX = ["EURUSD", "XAUUSD", "USDJPY"]
STRUCTURE_MODES = ["4h", "1h"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]


def run_hw_standalone(data, sym, market, selective: bool = False) -> dict | None:
    """Raw high-WR patterns without Elliott (baseline from CM MACD study)."""
    e = data[sym].get("15m")
    c = data[sym].get("1h")
    if e is None or c is None or len(e) < 120:
        return None
    hw = build_hw_context(data, sym, e, c, selective=selective)
    buy = pd.Series(hw["hw_long_pattern"], index=e.index)
    sell = pd.Series(hw["hw_short_pattern"], index=e.index)
    trades = simulate(e, buy, sell, sym, market)
    r = aggregate(trades, "hw_pattern_raw", sym, "15m", market)
    d = result_to_dict(r)
    d["signals"] = int(hw["hw_long_pattern"].sum()) + int(hw["hw_short_pattern"].sum())
    d["long_signals"] = int(hw["hw_long_pattern"].sum())
    d["short_signals"] = int(hw["hw_short_pattern"].sum())
    d["long_htf_min"] = hw["long_htf_min"]
    d["short_htf_min"] = hw["short_htf_min"]
    d["selective"] = selective
    return d


def run_fusion(data, sym, market, structure_tf, v2: bool, v3: bool, entry_gold: bool, selective: bool = False) -> dict | None:
    e, c, s = data[sym].get("15m"), data[sym].get("1h"), data[sym].get(structure_tf)
    if e is None or c is None or s is None or len(e) < 120:
        return None
    kw = dict(
        structure_tf=structure_tf,
        use_cardwell=True,
        use_cm_ultimate=v2,
        use_cm_hw_patterns=v3,
        require_macd_div_s1s2=not v2 and not v3,
        require_entry_ultimate_gold=entry_gold,
    )
    if v3:
        kw["hw_context"] = build_hw_context(data, sym, e, c, selective=selective)
    sig = golden_combo_signals(e, c, s, **kw)
    n = int(sig["buy"].sum()) + int(sig["sell"].sum())
    trades = simulate(e, sig["buy"], sig["sell"], sym, market)
    if v3:
        tag = f"fusion_v3{'_sel' if selective else ''}_{structure_tf}"
    elif v2:
        tag = f"fusion_v2_{structure_tf}"
    else:
        tag = f"fusion_v1_{structure_tf}"
    r = aggregate(trades, tag, sym, "15m", market)
    d = result_to_dict(r)
    d["signals"] = n
    d["scenarios"] = {k: int(v) for k, v in sig["scenario"].value_counts().items() if k}
    d["version"] = "v3" if v3 else ("v2" if v2 else "v1")
    d["structure_tf"] = structure_tf
    return d


def summarize(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["total_trades"] >= 1]
    return {
        "total_trades": sum(r["total_trades"] for r in valid),
        "avg_wr": round(sum(r["win_rate"] for r in valid) / len(valid), 1) if valid else 0,
        "avg_pf": round(sum(r["profit_factor"] for r in valid if r["profit_factor"] < 900) / len(valid), 3) if valid else 0,
        "symbols_with_trades": len(valid),
    }


def main():
    print("Golden Fusion v3 — CM MACD high-WR patterns + Elliott...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)

    hw_rows: list[dict] = []
    hw_sel_rows: list[dict] = []
    print("\n=== Standalone HW patterns (no Elliott) ===")
    for sym in CRYPTO + FOREX:
        market = "crypto" if sym in CRYPTO else "forex"
        d = run_hw_standalone(data, sym, market, selective=False)
        if d and d["total_trades"] > 0:
            hw_rows.append(d)
            print(
                f"  {sym}: trades={d['total_trades']} WR={d['win_rate']}% PF={d['profit_factor']} "
                f"(long={d['long_signals']} short={d['short_signals']})"
            )
        ds = run_hw_standalone(data, sym, market, selective=True)
        if ds and ds["total_trades"] > 0:
            hw_sel_rows.append(ds)

    print("\n=== Standalone HW selective (long + BTC 1h red hist only) ===")
    for d in hw_sel_rows:
        print(f"  {d['symbol']}: trades={d['total_trades']} WR={d['win_rate']}% PF={d['profit_factor']} (long={d['long_signals']} short={d['short_signals']})")

    configs = [
        ("v1_baseline", False, False, False),
        ("v2_ultimate", True, False, False),
        ("v3_hw_patterns", False, True, False),
        ("v3_hw_selective", False, True, True),
    ]
    fusion_rows: list[dict] = []
    comparison: dict = {}

    print("\n=== Golden Fusion comparison ===")
    for cfg_name, v2, v3, selective in configs:
        cfg_rows = []
        for st in STRUCTURE_MODES:
            for sym in CRYPTO + FOREX:
                market = "crypto" if sym in CRYPTO else "forex"
                d = run_fusion(data, sym, market, st, v2, v3, False, selective)
                if d:
                    cfg_rows.append(d)
                    fusion_rows.append(d)
                    if d["total_trades"] > 0:
                        print(f"  {cfg_name} {sym} {st}: trades={d['total_trades']} WR={d['win_rate']}% PF={d['profit_factor']} {d['scenarios']}")
        comparison[cfg_name] = summarize(cfg_rows)

    scenario_stats = {}
    for st in STRUCTURE_MODES:
        scenario_stats[st] = {}
        for sym in CRYPTO + FOREX:
            market = "crypto" if sym in CRYPTO else "forex"
            e, c, s = data[sym]["15m"], data[sym]["1h"], data[sym][st]
            hw = build_hw_context(data, sym, e, c)
            sig = golden_combo_signals(
                e, c, s,
                structure_tf=st,
                use_cardwell=True,
                use_cm_hw_patterns=True,
                hw_context=hw,
                require_macd_div_s1s2=False,
            )
            sub_rows = []
            for sc in sig["scenario"].unique():
                if not sc:
                    continue
                sub = sig.copy()
                sub["buy"] = sig["buy"] & (sig["scenario"] == sc)
                sub["sell"] = sig["sell"] & (sig["scenario"] == sc)
                trades = simulate(e, sub["buy"], sub["sell"], sym, market)
                if trades:
                    r = aggregate(trades, sc, sym, "15m", market)
                    sub_rows.append({
                        "scenario": sc,
                        "trades": r.total_trades,
                        "wr": round(r.win_rate, 1),
                        "pf": round(r.profit_factor, 3),
                    })
            scenario_stats[st][sym] = sub_rows

    out = {
        "period_days": 31,
        "strategy": "Golden Fusion v3 (green below zero + HTF≥3, 1h red hist + HTF≥2 + Elliott)",
        "patterns": {
            "long": "15m green dot below zero + HTF≥3 (BTC/EURUSD tuned)",
            "short_btc": "1h red histogram start + HTF≥2",
            "short_other": "15m red dot above zero + HTF≥2",
        },
        "hw_standalone": hw_rows,
        "hw_standalone_summary": summarize(hw_rows),
        "hw_selective_standalone": hw_sel_rows,
        "hw_selective_summary": summarize(hw_sel_rows),
        "comparison": comparison,
        "scenario_stats_v3": scenario_stats,
        "results": fusion_rows,
    }
    path = RESULTS / "backtest_golden_fusion_v3.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== HW standalone (all directions) ===")
    s = out["hw_standalone_summary"]
    print(f"  trades={s['total_trades']} avg_WR={s['avg_wr']}% avg_PF={s['avg_pf']} symbols={s['symbols_with_trades']}")
    print("\n=== HW selective standalone ===")
    s2 = out["hw_selective_summary"]
    print(f"  trades={s2['total_trades']} avg_WR={s2['avg_wr']}% avg_PF={s2['avg_pf']} symbols={s2['symbols_with_trades']}")
    print("\n=== Fusion versions ===")
    for k, v in comparison.items():
        print(f"  {k}: trades={v['total_trades']} avg_WR={v['avg_wr']}% avg_PF={v['avg_pf']} symbols={v['symbols_with_trades']}")


if __name__ == "__main__":
    main()
