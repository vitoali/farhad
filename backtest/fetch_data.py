"""Fetch OHLCV — Binance first, then other exchanges, then Yahoo Finance."""
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
OKX_TF = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
KUCOIN_TF = {"5m": "5min", "15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}
GATE_TF = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
YF_TF = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}

CRYPTO_SYMBOLS = ["BTCUSDT", "HYPEUSDT", "BEATUSDT"]
FOREX_YF = {"EURUSD": "EURUSD=X", "XAUUSD": "GC=F"}
YF_CRYPTO_FALLBACK = {"BTCUSDT": "BTC-USD", "HYPEUSDT": "HYPE-USD", "BEATUSDT": "BEAT-USD"}


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _finalize_df(rows: list, col_names: list[str], start: datetime) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=col_names)
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(int), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = df[c].astype(float)
    df = df[df["timestamp"] >= start]
    return df[["timestamp", "open", "high", "low", "close", "volume"]].drop_duplicates("timestamp").sort_values("timestamp")


def fetch_binance(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = "https://api.binance.com/api/v3/klines"
    rows: list[list] = []
    start_ms = _ms(start)
    end_ms = _ms(end)
    while start_ms < end_ms:
        r = requests.get(
            url,
            params={"symbol": symbol, "interval": BINANCE_TF[interval], "startTime": start_ms, "endTime": end_ms, "limit": 1000},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        start_ms = batch[-1][0] + 1
        time.sleep(0.12)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        rows,
        columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "qv", "trades", "tb", "tq", "ig"],
    )
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(int), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return df[df["timestamp"] >= start][["timestamp", "open", "high", "low", "close", "volume"]].drop_duplicates("timestamp")


def fetch_bybit(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = "https://api.bybit.com/v5/market/kline"
    rows = []
    cursor_end = _ms(end)
    while cursor_end > _ms(start):
        r = requests.get(
            url,
            params={"category": "linear", "symbol": symbol, "interval": BYBIT_TF[interval], "end": cursor_end, "limit": 1000},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        batch = r.json().get("result", {}).get("list", [])
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
    rows = list(reversed(rows))
    return _finalize_df(rows, ["open_time", "open", "high", "low", "close", "volume", "turnover"], start)


def fetch_okx(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    inst = symbol.replace("USDT", "-USDT")
    url = "https://www.okx.com/api/v5/market/candles"
    rows = []
    after = str(_ms(end))
    while True:
        r = requests.get(
            url,
            params={"instId": inst, "bar": OKX_TF[interval], "after": after, "limit": "300"},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        batch = r.json().get("data", [])
        if not batch:
            break
        rows.extend(batch)
        oldest = int(batch[-1][0])
        if oldest <= _ms(start):
            break
        after = batch[-1][0]
        time.sleep(0.1)
        if len(batch) < 300:
            break
    if not rows:
        return pd.DataFrame()
    rows = list(reversed([[int(x[0]), x[1], x[2], x[3], x[4], x[5]] for x in rows]))
    return _finalize_df(rows, ["open_time", "open", "high", "low", "close", "volume"], start)


def fetch_kucoin(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    inst = symbol.replace("USDT", "-USDT")
    url = "https://api.kucoin.com/api/v1/market/candles"
    rows = []
    cursor = int(end.timestamp())
    while cursor > int(start.timestamp()):
        r = requests.get(
            url,
            params={"symbol": inst, "type": KUCOIN_TF[interval], "endAt": cursor, "startAt": int(start.timestamp())},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        batch = r.json().get("data", [])
        if not batch:
            break
        parsed = [[int(x[0]) * 1000, x[1], x[3], x[4], x[2], x[5]] for x in batch]
        rows.extend(parsed)
        oldest = int(batch[-1][0])
        if oldest <= int(start.timestamp()):
            break
        cursor = oldest - 1
        time.sleep(0.1)
    if not rows:
        return pd.DataFrame()
    rows = list(reversed(rows))
    return _finalize_df(rows, ["open_time", "open", "high", "low", "close", "volume"], start)


def fetch_gate(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    pair = symbol.replace("USDT", "_USDT")
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    r = requests.get(
        url,
        params={"currency_pair": pair, "interval": GATE_TF[interval], "from": int(start.timestamp()), "to": int(end.timestamp())},
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    r.raise_for_status()
    batch = r.json()
    if not batch:
        return pd.DataFrame()
    rows = [[int(x[0]) * 1000, x[5], x[3], x[4], x[2], x[1]] for x in batch]
    return _finalize_df(rows, ["open_time", "open", "high", "low", "close", "volume"], start)


def fetch_yfinance(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    period = f"{days}d" if interval not in ("5m", "15m") or days <= 60 else "60d"
    df = yf.Ticker(symbol).history(period=period, interval=YF_TF[interval], auto_adjust=True)
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
    return df[df["timestamp"] >= cutoff][["timestamp", "open", "high", "low", "close", "volume"]]


CRYPTO_FETCHERS = [
    ("binance", fetch_binance),
    ("bybit", fetch_bybit),
    ("okx", fetch_okx),
    ("kucoin", fetch_kucoin),
    ("gate", fetch_gate),
]


def fetch_crypto(symbol: str, interval: str, days: int = 31) -> tuple[pd.DataFrame, str]:
    """Try exchanges in order; return (df, source_name)."""
    errors = []
    for name, fn in CRYPTO_FETCHERS:
        try:
            df = fn(symbol, interval, days)
            if df is not None and len(df) > 50:
                return df, name
            errors.append(f"{name}: empty")
        except Exception as e:
            errors.append(f"{name}: {e}")
    yf_sym = YF_CRYPTO_FALLBACK.get(symbol)
    if yf_sym:
        try:
            df = fetch_yfinance(yf_sym, interval, days)
            if len(df) > 50:
                return df, "yfinance"
            errors.append("yfinance: empty")
        except Exception as e:
            errors.append(f"yfinance: {e}")
    print(f"    all sources failed: {'; '.join(errors[:3])}")
    return pd.DataFrame(), "none"


def cache_path(name: str, tf: str) -> Path:
    return DATA_DIR / f"{name}_{tf}.parquet"


def meta_path(name: str, tf: str) -> Path:
    return DATA_DIR / f"{name}_{tf}.source"


def load_or_fetch_crypto(name: str, tf: str, days: int = 31, force: bool = False) -> tuple[pd.DataFrame, str]:
    path = cache_path(name, tf)
    meta = meta_path(name, tf)
    if path.exists() and meta.exists() and not force:
        return pd.read_parquet(path), meta.read_text().strip()
    df, source = fetch_crypto(name, tf, days)
    if not df.empty:
        df.to_parquet(path, index=False)
        meta.write_text(source)
    return df, source


def fetch_all(days: int = 31, timeframes: list[str] | None = None, force: bool = False) -> dict[str, dict[str, pd.DataFrame]]:
    timeframes = timeframes or ["5m", "15m", "1h", "4h", "1d"]
    out: dict[str, dict[str, pd.DataFrame]] = {}

    for sym in CRYPTO_SYMBOLS:
        out[sym] = {}
        for tf in timeframes:
            try:
                df, src = load_or_fetch_crypto(sym, tf, days, force=force)
                out[sym][tf] = df
                print(f"  {sym} {tf}: {len(df)} bars [{src}]")
            except Exception as e:
                print(f"  {sym} {tf}: FAILED - {e}")
                out[sym][tf] = pd.DataFrame()

    for label, yf_sym in FOREX_YF.items():
        out[label] = {}
        for tf in timeframes:
            path = cache_path(label, tf)
            try:
                if path.exists() and not force:
                    df = pd.read_parquet(path)
                else:
                    df = fetch_yfinance(yf_sym, tf, days)
                    if not df.empty:
                        df.to_parquet(path, index=False)
                out[label][tf] = df
                print(f"  {label} {tf}: {len(df)} bars [yfinance]")
            except Exception as e:
                print(f"  {label} {tf}: FAILED - {e}")
                out[label][tf] = pd.DataFrame()

    return out


if __name__ == "__main__":
    print("Fetching ~31 days — Binance first, then fallbacks...")
    fetch_all(force=True)
