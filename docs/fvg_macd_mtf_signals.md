# FVG MTF + MACD Signals

اندیکاتور ترکیبی برای TradingView:

1. **نمایش همه FVGها** روی تایم‌فریم‌های **15m / 1H / 4H / 1D** (منطق تشخیص مثل LuxAlgo Fair Value Gap)
2. **سیگنال MACD** (کراس MACD/Signal مثل CM_MacD_Ult_MTF)
3. فقط وقتی قیمت داخل محدودهٔ معتبر FVG باشد، روی چارت **≥ 15m** نقطه می‌گذارد:
   - **بای** = نقطه سبز زیر کندل
   - **سل** = نقطه قرمز بالای کندل

## منطق محدوده (پیشنهادی پیش‌فرض)

حالت پیش‌فرض: **CE Discount/Premium** (ICT Consequent Encroachment = ۵۰٪ FVG)

| سیگنال | شرط FVG | شرط سطح |
|--------|---------|---------|
| Buy | داخل Bullish FVG (پرنشده) | `close ≤ CE` (نیمهٔ پایین = تخفیف) |
| Sell | داخل Bearish FVG (پرنشده) | `close ≥ CE` (نیمهٔ بالا = پریمیوم) |

حالت‌های دیگر در تنظیمات:

- **Full FVG** — هر جای باکس
- **CE Touch ± ATR** — نزدیک خط ۵۰٪

## نصب

1. فایل `pine/fvg_macd_mtf_signals.pine` را در Pine Editor پیست کنید
2. Add to chart روی تایم‌فریم **۱۵ دقیقه یا بالاتر**
3. (اختیاری) Alert روی `FVG+MACD Buy` / `Sell`

## تنظیمات مهم

- **Require HTF confluence** — سیگنال فقط اگر همزمان داخل FVG چهارساعته یا روزانه هم باشد
- **MACD on Chart TF** — خاموش = MACD روی تایم‌فریم انتخابی
- رنگ باکس‌ها برای هر TF جداست (۱۵ کم‌رنگ‌تر، روزانه پررنگ‌تر)

## منابع

- `pine/sources/luxalgo_fair_value_gap.pine`
- `pine/sources/cm_macd_ult_mtf.pine`
