# نتایج بک‌تست آفلاین — یک ماه گذشته

این پوشه خروجی بک‌تست اندیکاتورها را نگه می‌دارد.

## اجرا

```bash
cd backtest
pip install -r requirements.txt
python run_backtest.py
```

## اندیکاتورها

| # | نام | فایل منطق |
|---|-----|-----------|
| 1 | UT Bot v2 | `indicators.ut_bot_signals` |
| 2 | AlphaTrend | `indicators.alpha_trend_signals` |
| 3 | Bj Bot / 3Commas | `indicators.bj_bot_signals` |

## مدل ریسک

- **کریپتو:** SL 1%، TP 2%، کارمزد+اسلیپیج ~0.1% round-trip
- **فارکس:** SL 3 pip، TP RR 1:1، اسپرد ~1.5 pip
- **Bj Bot:** خروج native (swing+ATR stop، R:R=1)

## نمادها

BTCUSDT، HYPEUSDT، BEATUSDT، EURUSD، XAUUSD

## تایم‌فریم‌ها

15m، 1h، 4h، 1d (یک ماه)
