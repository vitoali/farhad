#!/usr/bin/env python3
"""Backtest Monster Trex Vol with/without HTF trend filter prerequisite."""
from __future__ import annotations

import json
from pathlib import Path

from engine import aggregate
from fetch_data import fetch_all
from monster_trex_strategy import PAIR_MODES, monster_trex_signals
from run_backtest import SYMBOL_MARKET, result_to_dict
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
PAIR_MODES_LIST = list(PAIR_MODES.keys())


def run_variant(
    data: dict,
    htf_data: dict,
    struct_data: dict,
    use_trend: bool,
    pair_mode: str,
) -> list[dict]:
    rows: list[dict] = []
    cfg = PAIR_MODES[pair_mode]
    trigger_tf = cfg["trigger"]
    struct_tf = cfg["structure"]
    label = f"monster_trex_{pair_mode.lower()}_{'trend' if use_trend else 'notrend'}"

    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        trigger_df = tfs.get(trigger_tf)
        struct_df = struct_data.get(sym, {}).get(struct_tf)
        h1_ref = htf_data.get(sym, {}).get("1h")
        h4_ref = htf_data.get(sym, {}).get("4h")
        if trigger_df is None or len(trigger_df) < 120:
            continue
        sig = monster_trex_signals(
            trigger_df,
            chart_tf=trigger_tf,
            market=market,
            pair_mode=pair_mode,
            use_trend_filter=use_trend,
            struct_df=struct_df,
            h1_df=h1_ref,
            h4_df=h4_ref,
        )
        zlist = extract_zone_signals_from_df(sig)
        trades = simulate_zone_native(trigger_df, zlist, market)
        r = aggregate(trades, label, sym, trigger_tf, market)
        r.notes.append(f"signals={len(zlist)} trend={use_trend} pair={pair_mode}")
        rows.append(result_to_dict(r))
    return rows


def summarize(rows: list[dict], label: str, min_trades: int = 1) -> dict:
    valid = [r for r in rows if r["total_trades"] >= min_trades]
    if not valid:
        return {"label": label, "status": "insufficient", "runs": len(rows), "total_signals": sum(r["total_trades"] for r in rows)}
    pfs = [r["profit_factor"] for r in valid if r["profit_factor"] < 900]
    wrs = [r["win_rate"] for r in valid]
    best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
    by_mkt: dict[str, list] = {"crypto": [], "forex": []}
    for r in valid:
        by_mkt[r["market"]].append(r)
    mkt_pf = {
        k: round(sum(x["profit_factor"] for x in v if x["profit_factor"] < 900) / max(1, len(v)), 3)
        for k, v in by_mkt.items() if v
    }
    return {
        "label": label,
        "avg_pf": round(sum(pfs) / len(pfs), 3) if pfs else 0,
        "avg_wr": round(sum(wrs) / len(wrs), 1),
        "total_trades": sum(r["total_trades"] for r in valid),
        "samples": len(valid),
        "market_pf": mkt_pf,
        "best": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}%",
    }


def main():
    trigger_tfs = sorted({v["trigger"] for v in PAIR_MODES.values()})
    struct_tfs = sorted({v["structure"] for v in PAIR_MODES.values()})
    all_tfs = sorted(set(trigger_tfs + struct_tfs + ["1h", "4h"]))

    print(f"Fetching {all_tfs} (~31 days)...")
    chart_data = fetch_all(days=31, timeframes=trigger_tfs, force=False)
    struct_data = fetch_all(days=31, timeframes=struct_tfs, force=False)
    htf_data = fetch_all(days=31, timeframes=["1h", "4h"], force=False)

    all_results: dict[str, list[dict]] = {}
    for pair_mode in PAIR_MODES_LIST:
        for use_trend in (True, False):
            label = f"monster_trex_{pair_mode.lower()}_{'trend' if use_trend else 'notrend'}"
            print(f"\n=== {label} ===")
            rows = run_variant(chart_data, htf_data, struct_data, use_trend, pair_mode)
            all_results[label] = rows
            for r in rows:
                if r["total_trades"] > 0:
                    print(
                        f"  {r['symbol']:8} {r['timeframe']:4} trades={r['total_trades']:3} "
                        f"WR={r['win_rate']:5.1f}% PF={r['profit_factor']}"
                    )

    summaries = {k: summarize(v, k) for k, v in all_results.items()}
    out = {"period_days": 31, "pair_modes": PAIR_MODES_LIST, "summaries": summaries, "results": all_results}
    path = RESULTS / "backtest_monster_trex_v2.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== COMPARISON ===")
    for k, s in summaries.items():
        if s.get("status"):
            print(f"  {k}: insufficient (total_trades={s.get('total_signals', 0)})")
        else:
            print(
                f"  {k}: avg_PF={s['avg_pf']} WR={s['avg_wr']}% trades={s['total_trades']} "
                f"crypto={s['market_pf'].get('crypto', '—')} forex={s['market_pf'].get('forex', '—')} | {s['best']}"
            )


if __name__ == "__main__":
    main()
