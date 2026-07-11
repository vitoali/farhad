"""Fetch OHLCV data for offline backtesting."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BINANCE_TF = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
BYBIT_TF = {"5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
YF_TF = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}

# symbol_key -> (fetch_type, api_symbol)
SYMBOLS = {
    "BTCUSDT": ("yfinance", "BTC-USD"),
    "HYPEUSDT": ("yfinance", "HYPE-USD"),
    "BEATUSDT": ("yfinance", "BEAT-USD"),
    "EURUSD": ("yfinance", "EURUSD=X"),
    "XAUUSD": ("yfinance", "GC=F"),
}


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_bybit(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = "https://api.bybit.com/v5/market/kline"
    rows: list[list] = []
    end_ms = _ms(end)
    cursor_end = end_ms

    while cursor_end > _ms(start):
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": BYBIT_TF[interval],
            "end": cursor_end,
            "limit": 1000,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("result", {}).get("list", [])
        if not batch:
            break
        rows.extend(batch)
        oldest = int(batch[-1][0])
        if oldest <= _ms(start):
            break
        cursor_end = oldest - 1
        time.sleep(0.1)

    if not rows:
        return pd.DataFrame()

    # bybit returns newest first
    rows = list(reversed(rows))
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "turnover"])
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(int), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    cutoff = start
    df = df[df["timestamp"] >= cutoff]
    return df[["timestamp", "open", "high", "low", "close", "volume"]].drop_duplicates("timestamp")


def fetch_yfinance(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    period = f"{days}d"
    if interval in ("5m", "15m") and days > 60:
        period = "60d"
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    ts_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={ts_col: "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    df = df[df["timestamp"] >= cutoff]
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


def cache_path(name: str, tf: str) -> Path:
    return DATA_DIR / f"{name}_{tf}.parquet"


def load_or_fetch(name: str, tf: str, fetcher, days: int = 31, force: bool = False) -> pd.DataFrame:
    path = cache_path(name, tf)
    if path.exists() and not force:
        return pd.read_parquet(path)
    df = fetcher(tf, days)
    if not df.empty:
        df.to_parquet(path, index=False)
    return df


def fetch_all(days: int = 31, timeframes: list[str] | None = None, force: bool = False) -> dict[str, dict[str, pd.DataFrame]]:
    timeframes = timeframes or ["5m", "15m", "1h", "4h", "1d"]
    out: dict[str, dict[str, pd.DataFrame]] = {}

    for label, (kind, api_sym) in SYMBOLS.items():
        out[label] = {}
        for tf in timeframes:
            try:
                fn = lambda t, d=days, s=api_sym: fetch_yfinance(s, t, d)
                df = load_or_fetch(label, tf, fn, days, force=force)
                out[label][tf] = df
                print(f"  {label} {tf}: {len(df)} bars")
            except Exception as e:
                print(f"  {label} {tf}: FAILED - {e}")
                out[label][tf] = pd.DataFrame()

    return out


if __name__ == "__main__":
    print("Fetching ~31 days of data...")
    fetch_all(force=True)
