# ICT 2022 / Judas Dual

استراتژی‌های ICT برای TradingView (چارت **M1**، ساعت **America/New_York**).

## فایل‌ها

| فایل | نقش |
|------|-----|
| `pine/ict_judas_dual_m5m1.pine` | **ارتقا:** شکار سشن قبلی (Judas) + ورود دوگانه M5/M1 |
| `pine/ict_2022_reversal_strategy.pine` | نسخه ICT22 (HTF pivot sweep + M1 entry) |
| `pine/ict_killzones_ny.pine` | نمایش Killzone |
| `docs/ict-judas-dual-upgrade.md` | نظر مهندسی + مشخصات ارتقا |
| `docs/ict-2022-reversal-spec.md` | مشخصات نسخه قبلی |

## ساعت و سشن (اگر در ایران هستی)

همهٔ محاسبات با timezone **`America/New_York`** است.  
ساعت لپ‌تاپ/ایران **تأثیری ندارد**. در TradingView هم لازم نیست chart timezone را عوض کنی — کد صریحاً NY را می‌خواند.

| Killzone | ساعت NY |
|----------|---------|
| London Open | 02:00–05:00 |
| New York | 07:00–10:00 |
| Asia (TP1 جایگزین) | 20:00–00:00 |
| ریست روز FX | 17:00 |

پیشنهاد: اول `ict_killzones_ny.pine` را Add کن و ببین سایه‌ها با لندن/نیویورک واقعی هم‌خوان است.

## نصب

1. TradingView → Pine Editor  
2. محتوای `ict_2022_reversal_strategy.pine` را Paste → Add to chart  
3. **چارت را روی M1** بگذار  
4. برای SMT: در تنظیمات، جفت هم‌بسته را درست کن  
   - EURUSD → `FX:GBPUSD`  
   - NAS100 / NQ → معادل S&P (مثلاً `CME_MINI:ES1!`)  
5. اختیاری: `ict_killzones_ny.pine` را هم اضافه کن  

## آلرت‌ها

- `Step1 HTF Sweep`  
- `Step4 M5 CHoCH` — هشدار آماده‌باش  
- `Step6 M1 Entry` — لیمیت ورود  

## Attribution

هستهٔ تشخیص FVG و الگوی پنجره‌های Killzone از آثار LuxAlgo (CC BY-NC-SA 4.0) الهام/اقتباس شده؛ استفادهٔ غیرتجاری با حفظ attribution.
