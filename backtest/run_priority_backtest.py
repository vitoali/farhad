#!/usr/bin/env python3
"""Run full backtests for priority indicators #10-#15 and save results."""
from __future__ import annotations

import json
from pathlib import Path

from fetch_data import fetch_all
from run_backtest import SYMBOL_MARKET, TIMEFRAMES, result_to_dict, run_indicator

PRIORITY = [
    "ifvg",
    "breaker_blocks",
    "smc_pro",
    "zero_lag",
    "trendline_breakout",
    "rsi_advanced",
]

RESULTS = Path(__file__).parent / "results"


def main():
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    rows: list[dict] = []
    for ind in PRIORITY:
        for sym, tfs in data.items():
            market = SYMBOL_MARKET.get(sym, "crypto")
            for tf, df in tfs.items():
                if df is None or len(df) < 50:
                    continue
                try:
                    r = run_indicator(ind, df, sym, tf, market)
                    d = result_to_dict(r)
                    rows.append(d)
                    print(f"{ind:18} {sym:8} {tf:4} T={d['total_trades']:3} WR={d['win_rate']:5.1f} PF={d['profit_factor']}")
                except Exception as e:
                    print(f"{ind:18} {sym:8} {tf:4} ERROR {e}")

    out = RESULTS / "backtest_priority_zone.json"
    out.write_text(json.dumps({"indicators": PRIORITY, "results": rows}, indent=2), encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
