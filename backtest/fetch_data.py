"""Fetch last ~1 month of OHLC data for Gold (GC=F) and Bitcoin (BTC/USD).

Sources:
- Gold:    Yahoo Finance chart API (COMEX front-month futures GC=F), 1h and 15m
- Bitcoin: Coinbase Exchange candles (1h and 15m, paginated)

Output: CSV files in backtest/data/ with columns time,open,high,low,close
"""
import csv
import datetime as dt
import time
import requests

OUT_DIR = "data"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def save_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        w.writerows(rows)
    print(f"{path}: {len(rows)} candles  [{rows[0][0]} .. {rows[-1][0]}]")


def fetch_yahoo(symbol, interval, rng):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?range={rng}&interval={interval}")
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(ts):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        iso = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        rows.append([iso, round(o, 2), round(h, 2), round(l, 2), round(c, 2)])
    return rows


def fetch_coinbase(days, gran):
    """Coinbase returns max 300 candles per request -> paginate backwards."""
    end = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_limit = end - dt.timedelta(days=days)
    all_rows = {}
    cursor_end = end
    while cursor_end > start_limit:
        cursor_start = max(cursor_end - dt.timedelta(seconds=gran * 300), start_limit)
        url = ("https://api.exchange.coinbase.com/products/BTC-USD/candles"
               f"?granularity={gran}&start={cursor_start.isoformat()}&end={cursor_end.isoformat()}")
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        for c in r.json():  # [time, low, high, open, close, volume]
            all_rows[int(c[0])] = [float(c[3]), float(c[2]), float(c[1]), float(c[4])]
        cursor_end = cursor_start
        time.sleep(0.25)
    rows = []
    for t in sorted(all_rows):
        iso = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        o, h, l, c = all_rows[t]
        rows.append([iso, o, h, l, c])
    return rows


if __name__ == "__main__":
    # extra history so EMA/stdev(100) warm up before the evaluation month
    save_csv(f"{OUT_DIR}/gold_1h.csv", fetch_yahoo("GC=F", "1h", "3mo"))
    save_csv(f"{OUT_DIR}/gold_15m.csv", fetch_yahoo("GC=F", "15m", "40d"))
    save_csv(f"{OUT_DIR}/btc_1h.csv", fetch_coinbase(60, 3600))
    save_csv(f"{OUT_DIR}/btc_15m.csv", fetch_coinbase(37, 900))
