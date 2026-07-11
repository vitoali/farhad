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
| 4 | AlphaX FORGE | `forge_patterns.py` |
| 5 | FibFib / AutoFib | `indicators.fib_fib_signals` |
| 6 | Quadapt ML Trader | `indicators.quadapt_signals` |

## مدل ریسک

- **کریپتو:** SL **5%**، TP **5%** (RR 1:1)، کارمزد+اسلیپیج ~0.1% round-trip
- **فارکس:** SL 3 pip، TP RR 1:1، اسپرد ~1 pip
- **Bj Bot (فارکس):** خروج native (swing+ATR stop، R:R=1)
- **FORGE (کریپتو):** SL/TP ثابت 5%/10% | **FORGE (فارکس):** SL/TP الگو

## منبع داده

1. **بایننس** (اولویت اول)
2. در صورت خطا: Bybit → OKX → KuCoin → Gate.io → Yahoo Finance
3. فارکس/طلا: Yahoo Finance

## تایم‌فریم‌ها

15m، 1h، 4h، 1d (یک ماه)
