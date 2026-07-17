#!/usr/bin/env python3
"""Download OHLCV for BTC, Gold, EURUSD across multiple timeframes."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

# Yahoo tickers
SYMBOLS = {
    "BTC": "BTC-USD",
    "XAU": "GC=F",  # Gold futures proxy for XAUUSD
    "EURUSD": "EURUSD=X",
}

# Yahoo interval limits (approx): 5m/15m ~60d, 1h ~730d, 4h via resample
INTERVALS = {
    "5m": "60d",
    "15m": "60d",
    "1h": "90d",
    "1h_for_4h": "90d",
}


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.title)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0 if c == "Volume" else pd.NA
    df = df[cols].dropna(subset=["Open", "High", "Low", "Close"])
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    ohlc = df.resample(rule, label="right", closed="right").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    return ohlc.dropna(subset=["Open", "High", "Low", "Close"])


def main() -> None:
    meta = {}
    for name, ticker in SYMBOLS.items():
        print(f"Downloading {name} ({ticker})...")
        t = yf.Ticker(ticker)

        # 5m
        df5 = normalize(t.history(period="60d", interval="5m", auto_adjust=False))
        path5 = OUT / f"{name}_5m.csv"
        df5.to_csv(path5)
        print(f"  5m: {len(df5)} bars {df5.index.min()} -> {df5.index.max()}")

        # 15m
        df15 = normalize(t.history(period="60d", interval="15m", auto_adjust=False))
        path15 = OUT / f"{name}_15m.csv"
        df15.to_csv(path15)
        print(f"  15m: {len(df15)} bars {df15.index.min()} -> {df15.index.max()}")

        # 1h
        df1h = normalize(t.history(period="90d", interval="1h", auto_adjust=False))
        path1h = OUT / f"{name}_1h.csv"
        df1h.to_csv(path1h)
        print(f"  1h: {len(df1h)} bars {df1h.index.min()} -> {df1h.index.max()}")

        # 4h from 1h
        df4h = resample_ohlcv(df1h, "4h")
        path4h = OUT / f"{name}_4h.csv"
        df4h.to_csv(path4h)
        print(f"  4h: {len(df4h)} bars {df4h.index.min()} -> {df4h.index.max()}")

        meta[name] = {
            "ticker": ticker,
            "bars": {
                "5m": len(df5),
                "15m": len(df15),
                "1h": len(df1h),
                "4h": len(df4h),
            },
            "range": {
                "5m": [str(df5.index.min()), str(df5.index.max())] if len(df5) else None,
                "15m": [str(df15.index.min()), str(df15.index.max())] if len(df15) else None,
                "1h": [str(df1h.index.min()), str(df1h.index.max())] if len(df1h) else None,
                "4h": [str(df4h.index.min()), str(df4h.index.max())] if len(df4h) else None,
            },
        }

    # Try Binance for longer BTC 5m/15m (~90d)
    try:
        import urllib.request

        def binance_klines(symbol: str, interval: str, days: int = 90) -> pd.DataFrame:
            # Binance max 1000 candles per request; paginate
            end_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
            start_ms = int((pd.Timestamp.utcnow() - pd.Timedelta(days=days)).timestamp() * 1000)
            rows = []
            cur = start_ms
            while cur < end_ms:
                url = (
                    f"https://api.binance.com/api/v3/klines?symbol={symbol}"
                    f"&interval={interval}&startTime={cur}&endTime={end_ms}&limit=1000"
                )
                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                if not data:
                    break
                rows.extend(data)
                cur = data[-1][0] + 1
                if len(data) < 1000:
                    break
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows,
                columns=[
                    "OpenTime",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                    "CloseTime",
                    "QuoteVolume",
                    "Trades",
                    "TakerBuyBase",
                    "TakerBuyQuote",
                    "Ignore",
                ],
            )
            df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit="ms", utc=True)
            df = df.set_index("OpenTime")
            for c in ["Open", "High", "Low", "Close", "Volume"]:
                df[c] = df[c].astype(float)
            return df[["Open", "High", "Low", "Close", "Volume"]]

        for tf, iv in [("5m", "5m"), ("15m", "15m"), ("1h", "1h")]:
            btc = binance_klines("BTCUSDT", iv, days=90)
            if len(btc):
                p = OUT / f"BTC_{tf}.csv"
                btc.to_csv(p)
                print(f"Binance BTC {tf}: {len(btc)} bars {btc.index.min()} -> {btc.index.max()}")
                meta.setdefault("BTC", {})["bars"][tf] = len(btc)
                meta["BTC"]["range"][tf] = [str(btc.index.min()), str(btc.index.max())]
                meta["BTC"]["source"] = "binance"
        if "BTC" in meta and meta["BTC"].get("source") == "binance":
            btc1h = pd.read_csv(OUT / "BTC_1h.csv", index_col=0, parse_dates=True)
            btc4h = resample_ohlcv(btc1h, "4h")
            btc4h.to_csv(OUT / "BTC_4h.csv")
            meta["BTC"]["bars"]["4h"] = len(btc4h)
            meta["BTC"]["range"]["4h"] = [str(btc4h.index.min()), str(btc4h.index.max())]
            print(f"Binance BTC 4h: {len(btc4h)} bars")
    except Exception as e:
        print(f"Binance fallback skipped: {e}")

    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()
