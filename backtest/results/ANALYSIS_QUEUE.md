# صف تحلیل اندیکاتورها

آخرین به‌روزرسانی: 2026-07-11 (batch خودکار)

## وضعیت کلی

| وضعیت | تعداد |
|--------|-------|
| فایل‌های کامل در sources | 88 |
| فایل‌های ناقص | 13 |
| **بک‌تست Python (پورت شده)** | **32 کلید** (#1–#32) |
| تحلیل استاتیک batch | 88 |
| ثبت در processed_registry | 80+ |

## بک‌تست شده — کلیدهای Python

| # | اندیکاتور | کلید | وضعیت |
|---|-----------|------|--------|
| 1–9 | UT Bot … Lorentzian | ut_bot … lorentzian | ✅ |
| 10–15 | IFVG … RSI Advanced | ifvg … rsi_advanced | ✅ |
| 16 | Monster Trex | monster | ⏳ blocked |
| 17–19 | ML RSI … Strong Pullback | ml_rsi … strong_pullback | ✅ |
| 20–32 | Cardwell … Liquidity Pools | cardwell_rsi … liquidity_pool | ✅ |

## بهترین PF میانگین (batch ~31 روز)

| کلید | avg PF | بهترین |
|------|--------|--------|
| rsi_advanced | 2.96 | BTC 4h PF=8.27 |
| supply_demand | 1.70 | XAU 1h PF=2.86 |
| ifvg | 1.63 | XAU 15m PF=3.60 |
| smart_money_structure | 1.48 | HYPE 4h PF=6.75 |
| strong_pullback | 1.41 | EURUSD 15m PF=1.90 |
| fvg_retest | ~1.2+ | BTC 15m PF=1.75 |

## فایل‌های ناقص (منتظر آپلود)

- CT_Concepts, ELYOT, FVG_743a, FVGGGG, Market_Structure, Support_and_Resistance_7693
- VOLOM, dynamic_trend, high_volom_pivoty, rb_seteup, volon_trend_order_block
- strong_reversal_02f0 (قطع شده ~110 خط)

## دستور اجرا

```bash
cd backtest
python3 batch_pipeline.py          # بک‌تست همه پورت‌ها
python3 static_journal_all.py      # ثبت استاتیک بقیه
python3 process_indicator.py FILE  # تک‌فایل
```

نتایج: `results/backtest_batch_all.json` | ژورنال: `results/LEARNING_JOURNAL.md`
