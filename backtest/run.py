"""Run all backtests for the analyzed codes over the last month and write results.

Outputs:
- results/ledger.csv          — one row per code x symbol x tf x risk model
- results/trades/*.csv        — per-trade logs with features (for learning analysis)
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

import engine
import indicators as ind
from data import SYMBOLS, TF_SECONDS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
TRADES_DIR = RESULTS / "trades"

WINDOW_DAYS = 30

CRYPTO_MODELS = [
    ("crypto_sl1_tp2", ("pct", 1.0), ("pct", 2.0)),
    ("crypto_sl1_tp4", ("pct", 1.0), ("pct", 4.0)),
    ("crypto_sl3_tp2", ("pct", 3.0), ("pct", 2.0)),
    ("crypto_sl3_tp4", ("pct", 3.0), ("pct", 4.0)),
]
FX_MODELS = [
    ("fx_sl3_rr1", ("pips", 3), ("rr", 1.0)),
    ("fx_sl3_rr2", ("pips", 3), ("rr", 2.0)),
    ("fx_sl5_rr1", ("pips", 5), ("rr", 1.0)),
    ("fx_sl5_rr2", ("pips", 5), ("rr", 2.0)),
]


def load(symbol: str, tf: str) -> pd.DataFrame | None:
    p = DATA / f"{symbol}_{tf}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    return df if len(df) > 100 else None


def signals_for(code: str, df: pd.DataFrame, market: str) -> pd.DataFrame:
    if code == "001_utbot":
        return ind.ut_bot(df)
    if code == "002_alphatrend":
        return ind.alphatrend(df, use_volume=(market == "crypto"))
    if code == "003_macross":
        return ind.ma_cross(df)
    raise ValueError(code)


def add_features(df: pd.DataFrame, trades: list, market: str) -> pd.DataFrame:
    """Attach context features to each trade for the learning analysis."""
    atr = ind.atr_rma(df, 14)
    atr_pct = (atr / df["close"] * 100).to_numpy()
    ema50 = ind.ema(df["close"], 50)
    ema200 = ind.ema(df["close"], 200)
    trend_up = (df["close"] > ema200).to_numpy()
    ema50_up = (ema50 >= ema50.shift(1)).to_numpy()
    vol = df["volume"].rolling(20).mean()
    rel_vol = (df["volume"] / vol).to_numpy()
    rows = []
    for tr in trades:
        i = max(tr.idx - 1, 0)  # signal bar
        rows.append({
            "time": tr.time,
            "direction": tr.direction,
            "entry": tr.entry,
            "outcome": tr.outcome,
            "pl_pct": round(tr.pl_pct, 4),
            "r": round(tr.r, 3) if not np.isnan(tr.r) else "",
            "bars_held": tr.exit_idx - tr.idx if tr.exit_idx >= 0 else "",
            "atr_pct": round(atr_pct[i], 4) if not np.isnan(atr_pct[i]) else "",
            "htf_trend_up": bool(trend_up[i]),
            "ema50_rising": bool(ema50_up[i]),
            "rel_volume": round(rel_vol[i], 2) if not np.isnan(rel_vol[i]) else "",
            "with_htf_trend": (tr.direction == "long") == bool(trend_up[i]),
        })
    return pd.DataFrame(rows)


def main() -> None:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    end = int(time.time())
    ledger_rows = []
    codes = ["001_utbot", "002_alphatrend", "003_macross"]
    for symbol, (_, _, market) in SYMBOLS.items():
        is_crypto = market == "crypto"
        models = CRYPTO_MODELS if is_crypto else FX_MODELS
        eng_market = "crypto" if is_crypto else market
        for tf in TF_SECONDS:
            df = load(symbol, tf)
            if df is None:
                continue
            window_start = end - WINDOW_DAYS * 86400
            period_start = max(int(df["time"].iloc[0]), window_start)
            for code in codes:
                sig = signals_for(code, df, market)
                # fixed SL/TP models
                for model_name, sl_spec, tp_spec in models:
                    trades = engine.run_fixed(df, sig, eng_market, symbol, sl_spec, tp_spec, window_start)
                    m = engine.metrics(trades)
                    ledger_rows.append(_row(code, symbol, tf, model_name, period_start, end, m))
                    if m.get("trades", 0) > 0:
                        fdf = add_features(df, trades, market)
                        fdf.to_csv(TRADES_DIR / f"{code}_{symbol}_{tf}_{model_name}.csv", index=False)
                # native flip mode
                trades = engine.run_native(df, sig, eng_market, symbol, window_start)
                m = engine.metrics(trades)
                ledger_rows.append(_row(code, symbol, tf, "native_flip", period_start, end, m))
                if m.get("trades", 0) > 0:
                    fdf = add_features(df, trades, market)
                    fdf.to_csv(TRADES_DIR / f"{code}_{symbol}_{tf}_native_flip.csv", index=False)
            print(f"done {symbol} {tf}")
    cols = ["code_id", "code_name", "symbol", "timeframe", "risk_model", "period_start",
            "period_end", "is_oos", "trades", "win_rate_pct", "profit_factor",
            "net_profit_pct", "max_dd_pct", "avg_r", "verdict", "notes"]
    out = pd.DataFrame(ledger_rows)[cols]
    out.to_csv(RESULTS / "ledger.csv", index=False)
    print(f"ledger rows: {len(out)}")


def _row(code: str, symbol: str, tf: str, model: str, start: int, end: int, m: dict) -> dict:
    code_id, code_name = code.split("_", 1)
    return {
        "code_id": code_id, "code_name": code_name, "symbol": symbol, "timeframe": tf,
        "risk_model": model,
        "period_start": time.strftime("%Y-%m-%d", time.gmtime(start)),
        "period_end": time.strftime("%Y-%m-%d", time.gmtime(end)),
        "is_oos": "IS",
        "trades": m.get("trades", 0),
        "win_rate_pct": m.get("win_rate", ""),
        "profit_factor": m.get("profit_factor", ""),
        "net_profit_pct": m.get("net_profit_pct", ""),
        "max_dd_pct": m.get("max_dd_pct", ""),
        "avg_r": m.get("avg_r", ""),
        "verdict": "", "notes": "1-month window, costs included",
    }


if __name__ == "__main__":
    main()
