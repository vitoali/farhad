#!/usr/bin/env python3
"""
Backtest user's Golden Strategy (Gemini fusion doc):
- 5 scenarios: Elliott structure (4h/1h) + CM MACD + Cardwell MA100 (1h) + EWO/RSI (15m)
- BTC/SOL crypto, 31 days
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from engine import aggregate, simulate_fixed_sl_tp
from extra_indicators import macd_mtf_signals
from fetch_data import fetch_all
from golden_combo_strategy import SCENARIOS, golden_combo_signals, macd_cm_states
from run_backtest import result_to_dict
from zone_engine import extract_zone_signals_from_df, simulate_zone_native
from zone_indicators import rsi_advanced_signals

RESULTS = Path(__file__).parent / "results"
SYMBOLS = ["BTCUSDT", "SOLUSDT"]
STRUCTURE_MODES = ["4h", "1h"]


def simulate_crypto(df, buy, sell) -> list:
    return simulate_fixed_sl_tp(df, buy, sell, "crypto")


def run_golden_crypto(data: dict, structure_tf: str, use_cardwell: bool, require_div: bool) -> list[dict]:
    rows = []
    tag = f"golden_{structure_tf}"
    if not use_cardwell:
        tag += "_no_cw"
    if not require_div:
        tag += "_no_div"
    for sym in SYMBOLS:
        e, c, s = data[sym].get("15m"), data[sym].get("1h"), data[sym].get(structure_tf)
        if e is None or c is None or s is None or len(e) < 120:
            continue
        sig = golden_combo_signals(e, c, s, structure_tf=structure_tf, use_cardwell=use_cardwell, require_macd_div_s1s2=require_div)
        n = int(sig["buy"].sum()) + int(sig["sell"].sum())
        zlist = extract_zone_signals_from_df(sig)
        trades = simulate_zone_native(e, zlist, "crypto") if zlist else simulate_crypto(e, sig["buy"], sig["sell"])
        r = aggregate(trades, tag, sym, "15m", "crypto")
        d = result_to_dict(r)
        d["scenarios"] = {k: int(v) for k, v in sig["scenario"].value_counts().items() if k}
        d["signal_count"] = n
        d["filters"] = {"cardwell": use_cardwell, "macd_div": require_div, "structure_tf": structure_tf}
        rows.append(d)
    return rows


def run_cm_macd_filtered(data: dict, tf: str) -> dict | None:
    """CM MACD with user's zero-line filter."""
    from golden_combo_strategy import _align_bool  # noqa — use states inline

    rows = []
    for sym in SYMBOLS:
        df = data[sym].get(tf)
        if df is None or len(df) < 100:
            continue
        st = macd_cm_states(df)
        buy = st["macd_cross_bull_below"].fillna(False)
        sell = st["macd_cross_bear_above"].fillna(False)
        trades = simulate_crypto(df, buy, sell)
        r = aggregate(trades, "cm_macd_filtered", sym, tf, "crypto")
        d = result_to_dict(r)
        d["signals"] = int(buy.sum()) + int(sell.sum())
        rows.append(d)
    return rows


def run_components(data: dict) -> dict:
    comp = {}
    for sym in SYMBOLS:
        comp[sym] = {}
        for tf in ["15m", "1h", "4h"]:
            df = data[sym].get(tf)
            if df is None or len(df) < 80:
                continue
            for name, fn in [
                ("ewo_rsi", lambda d: rsi_advanced_signals(d)),
                ("cm_macd_raw", lambda d: macd_mtf_signals(d)),
            ]:
                sig = fn(df)
                tr = simulate_crypto(df, sig["buy"], sig["sell"])
                r = aggregate(tr, name, sym, tf, "crypto")
                comp[sym][f"{tf}_{name}"] = {
                    "trades": r.total_trades,
                    "wr": round(r.win_rate, 1),
                    "pf": round(r.profit_factor, 3) if r.profit_factor < 900 else 999,
                    "signals": int(sig["buy"].sum()) + int(sig["sell"].sum()),
                }
    return comp


def main():
    tfs = ["5m", "15m", "1h", "4h"]
    print(f"User Golden Strategy backtest — {SYMBOLS} — {tfs} (~31 days)")
    data = fetch_all(days=31, timeframes=tfs, force=False)

    golden_rows: list[dict] = []
    filter_modes = [
        ("full", True, True),
        ("cardwell_only", True, False),
        ("no_extra_filters", False, False),
    ]
    mode_summary = {}
    for mode, cw, div in filter_modes:
        mode_rows = []
        for st in STRUCTURE_MODES:
            mode_rows.extend(run_golden_crypto(data, st, cw, div))
        golden_rows.extend(mode_rows)
        valid = [r for r in mode_rows if r["total_trades"] >= 1]
        mode_summary[mode] = {
            "trades": sum(r["total_trades"] for r in valid),
            "avg_pf": round(sum(r["profit_factor"] for r in valid if r["profit_factor"] < 900) / len(valid), 3) if valid else 0,
            "avg_wr": round(sum(r["win_rate"] for r in valid) / len(valid), 1) if valid else 0,
            "symbols": valid,
        }

    cm_filtered = {}
    for tf in ["15m", "1h", "4h"]:
        cm_filtered[tf] = run_cm_macd_filtered(data, tf)

    components = run_components(data)

    # scenario breakdown
    scenario_stats: dict = defaultdict(list)
    for st in STRUCTURE_MODES:
        for sym in SYMBOLS:
            e, c, s = data[sym]["15m"], data[sym]["1h"], data[sym][st]
            sig = golden_combo_signals(e, c, s, structure_tf=st, use_cardwell=True, require_macd_div_s1s2=False)
            for sc in sig["scenario"].unique():
                if not sc:
                    continue
                mask = sig["scenario"] == sc
                sub = sig.copy()
                sub["buy"] = sig["buy"] & mask
                sub["sell"] = sig["sell"] & mask
                zlist = extract_zone_signals_from_df(sub)
                trades = simulate_zone_native(e, zlist, "crypto") if zlist else []
                if trades:
                    r = aggregate(trades, sc, sym, "15m", "crypto")
                    scenario_stats[sc].append({"symbol": sym, "struct": st, "trades": r.total_trades, "wr": round(r.win_rate, 1), "pf": round(r.profit_factor, 3)})

    out = {
        "period_days": 31,
        "strategy": "User Golden Fusion (EW + CM MACD + Cardwell MA100 + EWO/RSI)",
        "symbols": SYMBOLS,
        "entry_tf": "15m",
        "confirm_tf": "1h",
        "scenarios": SCENARIOS,
        "gemini_claims_vs_reality": {
            "claimed_golden_wr": "90%+",
            "claimed_cardwell_1h_wr": "75-80% (MA100)",
            "claimed_cardwell_4h_wr": "85-90% (MA100)",
            "note": "See actual results below — honest 31-day backtest",
        },
        "golden_combo_modes": mode_summary,
        "golden_results": golden_rows,
        "scenario_stats": dict(scenario_stats),
        "cm_macd_zero_line_filter": cm_filtered,
        "standalone_components": components,
    }

    path = RESULTS / "backtest_user_golden_strategy.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}\n")

    print("=== Golden Combo (BTC/SOL, 15m entry) ===")
    for mode, s in mode_summary.items():
        print(f"  {mode}: trades={s['trades']} avg_WR={s['avg_wr']}% avg_PF={s['avg_pf']}")
        for sym in s.get("symbols", []):
            print(f"    {sym['symbol']} struct={sym['filters']['structure_tf']} WR={sym['win_rate']}% PF={sym['profit_factor']} trades={sym['total_trades']} scenarios={sym.get('scenarios', {})}")

    print("\n=== Per-scenario (cardwell on, no div filter) ===")
    for sc, items in scenario_stats.items():
        print(f"  {sc} ({SCENARIOS.get(sc, sc)}):")
        for it in items:
            print(f"    {it['symbol']} {it['struct']}: trades={it['trades']} WR={it['wr']}% PF={it['pf']}")


if __name__ == "__main__":
    main()
