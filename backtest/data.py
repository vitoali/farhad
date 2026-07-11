"""Market data download: Gate.io (crypto spot) and Yahoo Finance (forex/metals).

Saves CSVs to data/<SYMBOL>_<TF>.csv with columns: time, open, high, low, close, volume.
All timestamps are UTC epoch seconds of the bar OPEN.
"""
import json
import time as _time
import urllib.request
import urllib.parse
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TF_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

GATE_INTERVALS = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
YAHOO_INTERVALS = {"5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}  # 4h resampled from 1h


def _http_get(url: str, retries: int = 4) -> bytes:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            _time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def fetch_gate(pair: str, tf: str, start: int, end: int) -> pd.DataFrame:
    """Gate.io spot candlesticks. Row: [t, quote_vol, close, high, low, open, base_vol, closed]."""
    step = TF_SECONDS[tf]
    rows = []
    cur = start
    max_span = step * 900  # keep under the 1000-point request cap
    while cur < end:
        chunk_end = min(cur + max_span, end)
        q = urllib.parse.urlencode({
            "currency_pair": pair, "interval": GATE_INTERVALS[tf],
            "from": cur, "to": chunk_end,
        })
        data = json.loads(_http_get(f"https://api.gateio.ws/api/v4/spot/candlesticks?{q}"))
        rows.extend(data)
        cur = chunk_end + step
        _time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["time", "quote_vol", "close", "high", "low", "open", "volume", "closed"])
    df = df[df["closed"] == "true"]
    df = df[["time", "open", "high", "low", "close", "volume"]].astype(float)
    df["time"] = df["time"].astype(int)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return df


def fetch_yahoo(ticker: str, tf: str, start: int, end: int) -> pd.DataFrame:
    interval = YAHOO_INTERVALS["1h" if tf == "4h" else tf]
    q = urllib.parse.urlencode({
        "interval": interval, "period1": start, "period2": end,
        "includePrePost": "false", "events": "history",
    })
    data = json.loads(_http_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?{q}"))
    res = data["chart"]["result"][0]
    ts = res.get("timestamp", [])
    quote = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "time": ts,
        "open": quote["open"], "high": quote["high"],
        "low": quote["low"], "close": quote["close"],
        "volume": quote["volume"],
    }).dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0.0)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    if tf == "4h":
        df = resample_ohlcv(df, 14400)
    return df


def resample_ohlcv(df: pd.DataFrame, step: int) -> pd.DataFrame:
    d = df.copy()
    d["bucket"] = (d["time"] // step) * step
    out = d.groupby("bucket").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), volume=("volume", "sum"),
    ).reset_index().rename(columns={"bucket": "time"})
    return out


SYMBOLS = {
    # name: (source, source_id, market)
    "BTCUSDT": ("gate", "BTC_USDT", "crypto"),
    "HYPEUSDT": ("gate", "HYPE_USDT", "crypto"),
    "BEATUSDT": ("gate", "BEAT_USDT", "crypto"),
    "EURUSD": ("yahoo", "EURUSD=X", "fx"),
    "XAUUSD": ("yahoo", "GC=F", "gold"),
}

# extra bars fetched before the test window so indicators are warmed up
WARMUP_BARS = 300


def download_all(window_days: int = 30, end_ts: int | None = None) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    end = end_ts or int(_time.time())
    for name, (source, sid, _mkt) in SYMBOLS.items():
        for tf, step in TF_SECONDS.items():
            start = end - window_days * 86400 - WARMUP_BARS * step
            try:
                if source == "gate":
                    df = fetch_gate(sid, tf, start, end)
                else:
                    df = fetch_yahoo(sid, tf, start, end)
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name} {tf}: {e}")
                continue
            path = DATA_DIR / f"{name}_{tf}.csv"
            df.to_csv(path, index=False)
            print(f"{name} {tf}: {len(df)} bars -> {path.name}")


if __name__ == "__main__":
    download_all()
