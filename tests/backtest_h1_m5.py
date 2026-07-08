#!/usr/bin/env python3
"""Offline backtest: H1 structure levels + M5 FTC/RTP entries (EURUSD)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from mse_engine_py import EntrySettings, MseSettings, run_backtest


def fetch_data(symbol: str = "EURUSD=X", days: int = 59) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit("pip install yfinance pandas numpy") from None

    # yfinance 5m limit ~60 days
    m5 = yf.download(symbol, interval="5m", period=f"{days}d", progress=False, auto_adjust=True)
    if m5.empty:
        raise RuntimeError(f"No data for {symbol}")

    if isinstance(m5.columns, pd.MultiIndex):
        m5.columns = m5.columns.get_level_values(0)
    m5 = m5.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    m5.index = pd.to_datetime(m5.index, utc=True).tz_convert(None)

    h1 = (
        m5.resample("1h", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    return h1, m5


def summarize(trades) -> dict:
    if not trades:
        return {"trades": 0, "win_rate": 0.0, "total_pips": 0.0, "avg_pips": 0.0}
    pnls = [t.pnl_pips for t in trades if t.pnl_pips is not None]
    wins = sum(1 for p in pnls if p > 0)
    return {
        "trades": len(pnls),
        "wins": wins,
        "losses": len(pnls) - wins,
        "win_rate": round(100 * wins / len(pnls), 1) if pnls else 0.0,
        "total_pips": round(sum(pnls), 1),
        "avg_pips": round(sum(pnls) / len(pnls), 1) if pnls else 0.0,
        "ftc_trades": sum(1 for t in trades if t.kind == "FTC"),
        "rtp_trades": sum(1 for t in trades if t.kind == "RTP"),
    }


def main():
    print("=== Khakster H1/M5 Offline Backtest ===\n")
    h1, m5 = fetch_data()
    print(f"Data: EURUSD  M5 bars={len(m5)}  H1 bars={len(h1)}")
    print(f"Range: {m5.index[0]} → {m5.index[-1]}\n")

    s, e = MseSettings(), EntrySettings()
    trades, levels = run_backtest(h1, m5, s, e)
    stats = summarize(trades)

    print(f"H1 pivots detected: {len(levels)} (eligible score≥{e.min_structure_score} & FTC✓)")
    print(json.dumps(stats, indent=2))

    if trades:
        print("\nLast 5 trades:")
        for t in trades[-5:]:
            print(
                f"  {t.entry_time} {t.side:5} {t.kind} entry={t.entry:.5f} "
                f"exit={t.exit_price:.5f} pnl={t.pnl_pips:+.0f}p"
            )

    out = ROOT / "tests" / "backtest_h1_m5_results.json"
    out.write_text(
        json.dumps(
            {
                "symbol": "EURUSD",
                "structure_tf": "H1",
                "trigger_tf": "M5",
                "bars_m5": len(m5),
                "bars_h1": len(h1),
                "pivots": len(levels),
                **stats,
            },
            indent=2,
        )
    )
    print(f"\nResults saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
