#!/usr/bin/env python3
"""Backtest CM_MACD_Ultimate (Silver/Gold) + HTF fusion from prior analysis."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine import aggregate, simulate_fixed_sl_tp
from extra_indicators import cm_macd_ultimate_signals
from fetch_data import fetch_all
from golden_combo_strategy import macd_cm_states
from indicators import ema
from run_backtest import result_to_dict

RESULTS = Path(__file__).parent / "results"
SYMBOLS = ["BTCUSDT", "SOLUSDT", "EURUSD", "XAUUSD"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]
TF_RANK = {"5m": 0, "15m": 1, "1h": 2, "4h": 3}


def htf_score(data: dict, sym: str, tf: str, ts: pd.Timestamp, direction: str) -> int:
    """Prior analysis: HTF MACD bull/bear confluence."""
    score = 0
    sig_rank = TF_RANK[tf]
    for htf in TIMEFRAMES:
        if TF_RANK[htf] <= sig_rank:
            continue
        df = data.get(sym, {}).get(htf)
        if df is None or df.empty or "timestamp" not in df.columns:
            continue
        mask = df["timestamp"] <= ts
        if not mask.any():
            continue
        sub = df.iloc[: int(mask.values.nonzero()[0][-1]) + 1]
        st = macd_cm_states(sub)
        row = st.iloc[-1]
        macd = ema(sub["close"], 12) - ema(sub["close"], 26)
        if direction == "long":
            if row["macd_bull_above_zero"] or row["macd_hist_aqua"]:
                score += 1
            if row["macd_cross_bull"]:
                score += 2
        else:
            if not row["macd_bull_above_zero"]:
                score += 1
            if row["macd_cross_bear"]:
                score += 2
    return score


def apply_htf_filter(sig: pd.DataFrame, data: dict, sym: str, tf: str, min_score: int, buy_col: str, sell_col: str) -> pd.DataFrame:
    out = sig.copy()
    buy_f = np.zeros(len(out), dtype=bool)
    sell_f = np.zeros(len(out), dtype=bool)
    ts_col = out["timestamp"] if "timestamp" in out.columns else None
    for i in range(len(out)):
        ts = ts_col.iloc[i] if ts_col is not None else None
        if ts is None:
            continue
        if out[buy_col].iloc[i]:
            if htf_score(data, sym, tf, pd.Timestamp(ts), "long") >= min_score:
                buy_f[i] = True
        if out[sell_col].iloc[i]:
            if htf_score(data, sym, tf, pd.Timestamp(ts), "short") >= min_score:
                sell_f[i] = True
    out["buy_htf"] = buy_f
    out["sell_htf"] = sell_f
    return out


def run_variant(df, sym: str, tf: str, market: str, buy_col: str, sell_col: str) -> dict:
    trades = simulate_fixed_sl_tp(df, df[buy_col], df[sell_col], market)
    r = aggregate(trades, f"cm_ultimate_{buy_col}", sym, tf, market)
    d = result_to_dict(r)
    d["signals"] = int(df[buy_col].sum()) + int(df[sell_col].sum())
    d["variant"] = buy_col
    return d


def main():
    print("CM MACD Ultimate backtest (~31 days)...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)

    rows: list[dict] = []
    fusion: dict = {}

    for sym in SYMBOLS:
        market = "crypto" if sym.endswith("USDT") else "forex"
        fusion[sym] = {}
        for tf in TIMEFRAMES:
            df = data.get(sym, {}).get(tf)
            if df is None or len(df) < 150:
                continue
            sig = cm_macd_ultimate_signals(df)
            sig = apply_htf_filter(sig, data, sym, tf, 2, "buy_silver", "sell_silver")
            sig = apply_htf_filter(sig, data, sym, tf, 2, "buy_gold", "sell_gold")

            variants = [
                ("silver", "buy_silver", "sell_silver"),
                ("gold", "buy_gold", "sell_gold"),
                ("silver_htf2", "buy_htf", "sell_htf"),  # only if silver passed HTF — recompute
            ]

            # silver + HTF
            buy_s_htf = np.zeros(len(sig), dtype=bool)
            sell_s_htf = np.zeros(len(sig), dtype=bool)
            buy_g_htf = np.zeros(len(sig), dtype=bool)
            sell_g_htf = np.zeros(len(sig), dtype=bool)
            ts_col = sig["timestamp"] if "timestamp" in sig.columns else None
            for i in range(len(sig)):
                ts = pd.Timestamp(ts_col.iloc[i]) if ts_col is not None else None
                if ts is None:
                    continue
                if sig["buy_silver"].iloc[i] and htf_score(data, sym, tf, ts, "long") >= 2:
                    buy_s_htf[i] = True
                if sig["sell_silver"].iloc[i] and htf_score(data, sym, tf, ts, "short") >= 2:
                    sell_s_htf[i] = True
                if sig["buy_gold"].iloc[i] and htf_score(data, sym, tf, ts, "long") >= 2:
                    buy_g_htf[i] = True
                if sig["sell_gold"].iloc[i] and htf_score(data, sym, tf, ts, "short") >= 2:
                    sell_g_htf[i] = True
            sig["buy_silver_htf"] = buy_s_htf
            sig["sell_silver_htf"] = sell_s_htf
            sig["buy_gold_htf"] = buy_g_htf
            sig["sell_gold_htf"] = sell_g_htf

            tf_res = {}
            for name, bc, sc in [
                ("silver", "buy_silver", "sell_silver"),
                ("gold", "buy_gold", "sell_gold"),
                ("silver+htf>=2", "buy_silver_htf", "sell_silver_htf"),
                ("gold+htf>=2", "buy_gold_htf", "sell_gold_htf"),
                ("gold+htf>=3", "buy_gold_htf", "sell_gold_htf"),
            ]:
                if name == "gold+htf>=3":
                    buy3 = np.zeros(len(sig), dtype=bool)
                    sell3 = np.zeros(len(sig), dtype=bool)
                    for i in range(len(sig)):
                        ts = pd.Timestamp(ts_col.iloc[i]) if ts_col is not None else None
                        if ts is None:
                            continue
                        if sig["buy_gold"].iloc[i] and htf_score(data, sym, tf, ts, "long") >= 3:
                            buy3[i] = True
                        if sig["sell_gold"].iloc[i] and htf_score(data, sym, tf, ts, "short") >= 3:
                            sell3[i] = True
                    d = run_variant(sig.assign(buy_gold_htf3=buy3, sell_gold_htf3=sell3), sym, tf, market, "buy_gold_htf3", "sell_gold_htf3")
                else:
                    d = run_variant(sig, sym, tf, market, bc, sc)
                rows.append(d)
                tf_res[name] = {"trades": d["total_trades"], "wr": d["win_rate"], "pf": d["profit_factor"], "signals": d["signals"]}
                if d["total_trades"] > 0:
                    print(f"  {sym} {tf} {name}: trades={d['total_trades']} WR={d['win_rate']}% PF={d['profit_factor']} sig={d['signals']}")

            fusion[sym][tf] = tf_res

    # best variants
    valid = [r for r in rows if r["total_trades"] >= 3 and r["profit_factor"] < 900]
    best = sorted(valid, key=lambda x: (-x["profit_factor"], -x["win_rate"]))[:10]

    out = {
        "period_days": 31,
        "indicator": "CM_MACD_Ultimate_Position_Fixed",
        "logic": {
            "silver_long": "bullish cross + MACD below -1*stdev(100)",
            "silver_short": "bearish cross + MACD above +1*stdev(100)",
            "gold_long": "silver_long + bullish MACD divergence within 10 bars",
            "gold_short": "silver_short + bearish MACD divergence within 10 bars",
        },
        "fusion_with_prior_analysis": {
            "htf_filter": "Require HTF MACD confluence score >= 2 (from prior CM MACD study)",
            "recommended_combo": "15m GOLD + HTF>=2 for entry; 1h Cardwell MA100 for trend; 4h Elliott for structure",
        },
        "best_variants": best,
        "all_results": rows,
        "by_symbol_tf": fusion,
    }
    path = RESULTS / "backtest_cm_macd_ultimate.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
