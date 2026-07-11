# صف تحلیل اندیکاتورها

آخرین به‌روزرسانی: 2026-07-11 (ادامه بدون وقفه)

## وضعیت کلی

| وضعیت | تعداد |
|--------|-------|
| فایل‌های کامل | **88** |
| فایل‌های ناقص | **13** |
| **پورت Python + بک‌تست** | **43 کلید** (#1–#43) |
| فایل‌های mapped به پورت | **~55** |
| visualization-only (استاتیک) | **~33** |

## بهترین PF میانگین (batch ~31 روز)

| رتبه | کلید | avg PF | بهترین |
|------|------|--------|--------|
| 1 | rsi_advanced | 2.96 | BTC 4h PF=8.27 |
| 2 | liquidity_shift | 2.67 | BEAT 4h PF=15.6 |
| 3 | supply_demand | 1.70 | XAU 1h PF=2.86 |
| 4 | ifvg | 1.63 | XAU 15m PF=3.60 |
| 5 | smart_money_structure | 1.48 | HYPE 4h PF=6.75 |
| 6 | ichimoku_ml | 0.87 | HYPE 1h PF=4.34 |
| 7 | sr_signals_mtf | 1.11 | HYPE 4h PF=1.99 |

## پورت‌های جدید (#37–#43)

| # | کلید | فایل منبع |
|---|------|-----------|
| 37 | fxpip_scob | FxPipFinder_Engagement_Zone |
| 38 | buyside_liquidity | Buyside/Sellside Liquidity, Mirage |
| 39 | sr_signals_mtf | Support_and_Resistance_Signals MTF |
| 40 | divergence | Divergence for Many Indicators |
| 41 | orderflow_print | OrderFlow Absorption Matrix |
| 42 | fair_value_gap | Fair Value Gap, FVG ICT |
| 43 | fib_ote | Smart Money Fib OTE (نمونه کم) |

## فایل‌های ناقص — منتظر آپلود

strong_reversal_02f0, mirage_8451 (109 خط), smart_mony_fibo (109 خط), 4_4040, CT_Concepts, ELYOT, FVG_743a, ...

## دستور

```bash
python3 batch_pipeline.py
python3 static_journal_all.py
```

نتایج: `results/backtest_batch_all.json`
