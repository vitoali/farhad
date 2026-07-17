#!/usr/bin/env python3
"""Backtest Cardwell Range Analyze on BTC/SOL crypto + forex pairs."""
from __future__ import annotations

import json
from pathlib import Path

from engine import aggregate, simulate_fixed_sl_tp
from extra_indicators import cardwell_range_signals
from fetch_data import fetch_all
from run_backtest import result_to_dict
from run_forex_three_indicators import simulate_forex
from zone_engine import extract_zone_signals_from_df, simulate_zone_native

RESULTS = Path(__file__).parent / "results"
CRYPTO_SYMBOLS = ["BTCUSDT", "SOLUSDT"]
FOREX_SYMBOLS = ["EURUSD", "XAUUSD", "USDJPY"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]


def run_cardwell_on_symbol(df, symbol: str, tf: str, market: str) -> dict | None:
    if df is None or len(df) < 120:
        return None
    sig = cardwell_range_signals(df, trend_len=100)
    n_sig = int(sig["buy"].sum()) + int(sig["sell"].sum())
    if n_sig == 0:
        return {
            "indicator": "cardwell_range",
            "symbol": symbol,
            "timeframe": tf,
            "market": market,
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "notes": ["signals=0"],
        }
    zlist = extract_zone_signals_from_df(sig)
    if zlist:
        trades = simulate_zone_native(df, zlist, market)
    elif market == "forex":
        trades = simulate_forex(df, sig["buy"], sig["sell"], symbol)
    else:
        trades = simulate_fixed_sl_tp(df, sig["buy"], sig["sell"], market)
    r = aggregate(trades, "cardwell_range", symbol, tf, market)
    d = result_to_dict(r)
    d["notes"] = [f"signals={n_sig} trend_ma=100"]
    return d


def main():
    print(f"Fetching crypto {CRYPTO_SYMBOLS} + forex {FOREX_SYMBOLS} — {TIMEFRAMES} (~31 days)...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)

    rows: list[dict] = []
    for sym in CRYPTO_SYMBOLS + FOREX_SYMBOLS:
        market = "crypto" if sym in CRYPTO_SYMBOLS else "forex"
        for tf in TIMEFRAMES:
            df = data.get(sym, {}).get(tf)
            row = run_cardwell_on_symbol(df, sym, tf, market)
            if row:
                rows.append(row)
                pf = row.get("profit_factor", 0)
                wr = row.get("win_rate", 0)
                tr = row.get("total_trades", 0)
                print(f"  {sym} {tf}: trades={tr} WR={wr}% PF={pf}")

    valid = [r for r in rows if r["total_trades"] >= 1]
    summaries: dict = {}
    for market in ("crypto", "forex"):
        subset = [r for r in valid if r["market"] == market]
        if subset:
            best = max(subset, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
            summaries[market] = {
                "best": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}%",
                "avg_pf": round(
                    float(sum(r["profit_factor"] for r in subset if r["profit_factor"] < 900) / len(subset)), 3
                ),
                "total_trades": sum(r["total_trades"] for r in subset),
            }
        else:
            summaries[market] = {"status": "no_trades"}

    out = {
        "period_days": 31,
        "indicator": "cardwell_range",
        "trend_ma_len": 100,
        "symbols": {"crypto": CRYPTO_SYMBOLS, "forex": FOREX_SYMBOLS},
        "timeframes": TIMEFRAMES,
        "summaries": summaries,
        "results": rows,
    }
    path = RESULTS / "backtest_cardwell_range.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    print("\n=== Cardwell Range Analyze (MA=100) ===")
    for k, v in summaries.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
