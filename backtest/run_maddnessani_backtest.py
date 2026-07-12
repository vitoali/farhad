#!/usr/bin/env python3
"""Backtest MADDNESSANI v4 with/without HTF trend filter on 5m, 15m, 1h."""
from __future__ import annotations

import json
from pathlib import Path

from engine import aggregate
from fetch_data import fetch_all
from maddnessani_strategy import maddnessani_signals
from run_backtest import SYMBOL_MARKET, result_to_dict
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
CHART_TFS = ["5m", "15m", "1h"]
MODES = ["precision", "balanced"]


def run_variant(data: dict, htf_data: dict, use_htf: bool, mode: str) -> list[dict]:
    rows: list[dict] = []
    label = f"maddnessani_{mode}_{'htf' if use_htf else 'nohtf'}"
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        novol = market == "forex" or sym == "BEATUSDT"
        h1_ref = htf_data.get(sym, {}).get("1h")
        h4_ref = htf_data.get(sym, {}).get("4h")
        for tf in CHART_TFS:
            df = tfs.get(tf)
            if df is None or len(df) < 120:
                continue
            sig = maddnessani_signals(
                df,
                chart_tf=tf,
                market=market,
                mode=mode,
                use_htf_trend=use_htf,
                novolumedata=novol,
                h1_df=h1_ref,
                h4_df=h4_ref,
            )
            zlist = extract_zone_signals_from_df(sig)
            trades = simulate_zone_native(df, zlist, market)
            r = aggregate(trades, label, sym, tf, market)
            r.notes.append(f"signals={len(zlist)} htf={use_htf} mode={mode}")
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
    print("Fetching 5m + 15m + 1h + 4h (~31 days)...")
    chart_data = fetch_all(days=31, timeframes=CHART_TFS, force=False)
    htf_data = fetch_all(days=31, timeframes=["1h", "4h"], force=False)

    all_results: dict[str, list[dict]] = {}
    for mode in MODES:
        for use_htf in (True, False):
            label = f"maddnessani_{mode}_{'htf' if use_htf else 'nohtf'}"
            print(f"\n=== {label} ===")
            rows = run_variant(chart_data, htf_data, use_htf, mode)
            all_results[label] = rows
            for r in rows:
                if r["total_trades"] > 0:
                    print(
                        f"  {r['symbol']:8} {r['timeframe']:4} trades={r['total_trades']:3} "
                        f"WR={r['win_rate']:5.1f}% PF={r['profit_factor']}"
                    )

    summaries = {k: summarize(v, k) for k, v in all_results.items()}
    out = {"period_days": 31, "chart_tfs": CHART_TFS, "summaries": summaries, "results": all_results}
    path = RESULTS / "backtest_maddnessani_v4.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== COMPARISON ===")
    for k, s in summaries.items():
        if s.get("status"):
            print(f"  {k}: insufficient (total_trades={s.get('total_signals',0)})")
        else:
            print(
                f"  {k}: avg_PF={s['avg_pf']} WR={s['avg_wr']}% trades={s['total_trades']} "
                f"crypto={s['market_pf'].get('crypto','—')} forex={s['market_pf'].get('forex','—')} | {s['best']}"
            )


if __name__ == "__main__":
    main()
