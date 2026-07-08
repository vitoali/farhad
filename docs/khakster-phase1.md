# Market Structure Engine — فاز ۱

## فایل‌ها

| فایل | نقش |
|------|-----|
| `pine/khakster_trex_atr_lib.pine` | ATR (TR / TH) |
| `pine/market_structure_engine.pine` | کتابخانه پیوت + Zone |
| `pine/market_structure_chart.pine` | اندیکاتور رسم سطح روی چارت |

## نصب TradingView

1. Publish `KhaksterTrexAtrLib`
2. Publish `MarketStructureEngine` (import را با نام کاربری خودتان عوض کنید)
3. `market_structure_chart.pine` → import هر دو Library → Add to chart

## تایم‌فریم‌های سطح

فقط سطوح ساختار معتبر:

| TF | کد | رنگ |
|----|-----|-----|
| H1 | 60 | آبی |
| H4 | 240 | نارنجی |
| D1 | D | بنفش |
| W1 | W | قرمز |
| Mn | M | زرد |

## دسته‌بندی کندل (خاکستر)

| کلاس | دامنه نسبت به TR |
|------|------------------|
| Spinning | < 80% |
| Standard (مستر) | 80% – 120% |
| LongBar | 120% – 240% |
| Spike | > 240% |

**مسترکندل:** دامنه 80–120% TR + بدنه یا شدو ≥ 80%

## قواعد پیوت (فاز ۱)

1. حرکت: ۳ مسترکندل هم‌جهت **یا** جمع TR سه کندل ∈ [2.4×TR, 3.6×TR] **یا** اسپایک + خط فرضی
2. برگشت ≥ 1× TR
3. کندل پوشاننده: engulf مسترکندل **یا** بسته زیر/بالای خط فرضی (اسپایک)
4. بسته در ۱/۳ انتهایی (به‌جز مسیر اسپایک)
5. **Zone خارجی:** نوک شدو تا محدوده Open/Close
6. **Zone داخلی:** بدنه مسترکندل (باکس تیره‌تر)

## فاز ۲

- FTC / RTP / امتیاز اعتبار / خط داینامیک — [`khakster-phase2.md`](khakster-phase2.md)

## فاز ۳ (فعلی)

- نوع پیوت / همپوشانی TF / استراتژی FTC — [`khakster-phase3.md`](khakster-phase3.md)
