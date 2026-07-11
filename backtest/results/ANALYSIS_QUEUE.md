# صف تحلیل اندیکاتورها

آخرین به‌روزرسانی: 2026-07-11

## وضعیت کلی

| وضعیت | تعداد |
|--------|-------|
| تحلیل‌شده قبلی (چت) | 6 |
| بک‌تست Python | 17 | ✅ (#1–#17) |
| تحلیل استاتیک batch | ~75 |
| ناقص (منتظر آپلود) | 12 |
| **هدف نهایی** | ~60 |

## بک‌تست شده (#1–#15)

| # | اندیکاتور | فایل | وضعیت |
|---|-----------|------|--------|
| 1 | UT Bot v2 | chat | ✅ |
| 2 | AlphaTrend | `AlphaTrend_b53f.txt` | ✅ |
| 3 | Bj Bot | `2_297c.txt` | ✅ |
| 4 | AlphaX FORGE | `forg_6b2d.txt` | ✅ |
| 5 | FibFib | `fib_fib.pine` | ✅ |
| 6 | Quadapt ML | `quadpad_47cd.txt` | ✅ |
| 7 | SuperTrend | `SUPER_TREND_ccf2.txt` | ✅ |
| 8 | Chandelier Exit | `Chandelier_Exit_a3e4.txt` | ✅ |
| 9 | Lorentzian ML | `Machine_Learning_Lorentzian_9f8e.txt` | ✅ (ساده‌شده) |
| 10 | IFVG Engine | `IFVG_ENGINE_6b53.txt` | ✅ zone native |
| 11 | Breaker Blocks | `Breaker_Blocks_with_Signals__LuxAlgo_103c.txt` | ✅ simplified |
| 12 | SMC PRO v2 | `Money_Concepts_PRO_v2.tiktok0_9e67.txt` | ✅ confluence |
| 13 | Zero Lag | `Zero_Lag_Trend_Signals_TIKTOK_8b12.txt` | ✅ |
| 14 | Trendline Breakout | `Trendline_Breakouts_With__df18.txt` | ✅ (low sample) |
| 15 | RSI Advanced | `rsi_advanced_868b.txt` | ✅ |
| 17 | ML RSI Zeiierman | `machin_rsi_313b.txt` | ✅ |
| 16 | Monster Trex | `monster_e007.txt` | ⏳ blocked (ext libs) |

## اولویت بعدی برای پورت Python

1. `Ranked_Order_Block_Zones__Zeiierman_9c77.txt`
2. `suply_demand_zone_f0e7.txt`
3. `LIQUDITY_PPOOL_ce94.txt`
4. `Smart_Money_Structure__GainzAlgo_4e52.txt`
5. `Cardwell_RSI_Trade_Navigator__MarkitTick_1c8f.txt`

## فایل‌های ناقص (منتظر آپلود شما)

- `CT_Concepts__LuxAlgo__d0c0.txt`
- `ELYOT_dcd0.txt`
- `FVGGGG_f0e2.txt`
- `FVG_743a.txt`
- `Market_Structure_with_Inducements___Sweeps_244c.txt`
- `Support_and_Resistance_7693.txt`
- `VOLOM_2fee.txt`
- `dynamic_trend_8e17.txt`
- `high_volom_pivoty_suport_778c.txt`
- `machin_learning_rsi_217a.txt`
- `rb_seteup_5_algo_7ddb.txt`
- `volon_trend_order_block_72a5.txt`

## دستور اجرا

```bash
# تحلیل + بک‌تست یک فایل
python3 process_indicator.py SUPER_TREND_ccf2.txt

# تحلیل استاتیک N فایل بعدی
python3 process_indicator.py dummy --next 10 --skip-backtest
```

تحلیل‌های جزئی در `results/analyses/` ذخیره می‌شوند.
