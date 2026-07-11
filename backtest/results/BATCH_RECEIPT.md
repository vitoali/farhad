# گزارش دریافت batch — ۹۲ فایل

**تاریخ:** ۲۰۲۶-۰۷-۱۱

## خلاصه

| مورد | تعداد |
|------|--------|
| فایل دریافت‌شده | **92** |
| کامل (قابل تحلیل) | **~53** |
| ناقص (قطع شده) | **~39** |
| تکراری | **~5** |
| قبلاً تحلیل‌شده (#1–#6) | **6** |

---

## فایل‌های ناقص — باید دوباره بفرستی

این فایل‌ها وسط کد قطع شده‌اند (معمولاً ۹۴، ۱۰۹، ۱۶۲ یا ۴۲۶ خط):

1. `2_297c.txt` — Bj Bot / 3Commas (ناقص؛ نسخه کامل از چت داریم)
2. `3_3fa8.txt` — PMax Explorer
3. `4_4040.txt` — TrendMaster Pro
4. `atomatic_multi_pattern__9980.txt` — FORGE ناقص (نسخه کامل: `forg_6b2d.txt`)
5. `auto_pattern_detector_bf37.txt` — FORGE ناقص
6. `cardvel_f64f.txt` — Cardwell Range
7. `dynamic_trend_8e17.txt`
8. `entrylib_5e01.txt` — کتابخانه Pine (نه اندیکاتور مستقل)
9. `fvg_1bce.txt` — FVG Retest Engine ⚠️ مهم
10. `FVGGGG_f0e2.txt` — تکراری ناقص
11. `FVG_G_74aa.txt` — FVG SpaceMan ناقص
12. `FVG___IFVG_ICT_a586.txt` — ناقص (اگر کامل داری بفرست)
13. `high_volom_pivoty_suport_778c.txt`
14. `machin_f3c0.txt` — ML SMC GainzAlgo
15. `machin_learning_rsi_217a.txt` — ML RSI ⚠️ مهم
16. `mirage_8451.txt` — Liquidity Sweep
17. `multi_divergence_3058.txt`
18. `power_order_bloc_151a.txt`
19. `qt_cx_7542.txt`
20. `rb_seteup_5_algo_7ddb.txt` — Retest & Break
21. `smart_0f3d.txt` — کتابخانه Khakster
22. `smart_mony_fibo_67b7.txt` — OTE Fib
23. `strong_reversal_02f0.txt`
24. `suply_demand_zone_f0e7.txt` — Supply/Demand ⚠️ مهم
25. `volon_trend_order_block_72a5.txt`
26. `whale_liquidy_zone_181a.txt`
27. `ELYOT_dcd0.txt` — Elliott Wave
28. `HISTORICAL_POPTRN_8ffc.txt`
29. `LONG_SEL_285e.txt` — Strong Pullback ⚠️ مهم
30. `MACHIN_a826.txt` — ML Pivot KNN
31. `New_Text_Document_ee2a.txt` — ICT Rebalance
32. `ORDER_5f08.txt` — OrderFlow FVG Matrix
33. `QUANTOM_4271.txt`
34. `STOP_HUNT_e28b.txt`
35. `STRATGY_b6e6.txt`
36. `SUPER_TREND_4ed2.txt`
37. `VOLOM_2fee.txt`
38. `ATR_SL_FINDER_977b.txt` (اگر موجود)
39. `CANDLE_d8b6.txt` (اگر موجود)

---

## تکراری — یکی کافی است

| نگه دار | حذف کن |
|---------|--------|
| `forg_6b2d.txt` | `atomatic_multi_pattern__9980.txt`, `auto_pattern_detector_bf37.txt` |
| `quadpad_47cd.txt` | `quadpad_9f11.txt` |
| `Smart_Money_Concepts_PRO_979a.txt` | `Money_Concepts_PRO_v2.tiktok0_9e67.txt` |
| `Divergence_for_Many_Indicators_2408.txt` | `Divergence_for_many_indicator_2b36.txt` |
| `AlphaTrend` (چت #2) | `AlphaTrend_b53f.txt` (برای تأیید) |

---

## اولویت بک‌تست (کامل + سیگنال)

- Machine_Learning_Lorentzian
- IFVG_ENGINE
- Smart_Money_Concepts_PRO
- Breaker_Blocks_with_Signals
- FVG_743a (IFVG LuxAlgo)
- monster_e007 (strategy)
- rsi_advanced (strategy)
- Chandelier_Exit, SUPER_TREND_ccf2, QQE
- AlphaTrend, forg (FORGE), quadpad

---

## مدل ثابت بک‌تست

- کریپتو: SL **5%** / TP **5%**
- داده: بایننس → OKX → KuCoin
