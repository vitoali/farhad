# اندیکاتور الگوهای کندلی نیسون — TradingView

شناسایی **۶۴ الگوی کندلی** از کتاب *Japanese Candlestick Charting Techniques* اثر Steve Nison.

## فایل‌ها

| فایل | کاربرد |
|------|--------|
| `pine/candle_recognition_lib.pine` | **کتابخانه کندل‌شناس** — برای استراتژی (Publish as `CandleRecognitionLib`) |
| `pine/nison_candlestick_scanner.pine` | اندیکاتور نمایش (خط + تگ Reversal/Continuation/Context) |

فرمول‌ها: [`docs/candle-recognition-formulas.md`](docs/candle-recognition-formulas.md)

## نصب سریع در TradingView

### روش ۱ — فقط اندیکاتور (پیشنهادی)

1. فایل `pine/nison_candlestick_patterns.pine` را در Pine Editor باز کنید.
2. آن را به‌عنوان **Library** منتشر (Publish) کنید.
3. فایل `pine/nison_candlestick_scanner.pine` را باز کنید.
4. خط import را با مسیر کتابخانه خودتان عوض کنید:

```pine
import YOUR_USERNAME/NisonCandlestickPatterns/1 as nison
```

5. اندیکاتور را Add to Chart کنید.

### روش ۲ — برای استراتژی بعدی

در استراتژی خودتان کتابخانه را import کنید و از توابع زیر استفاده کنید:

```pine
import YOUR_USERNAME/NisonCandlestickPatterns/1 as nison

s = nison.defaultSettings()

// مثال: آیا الگوی Morning Star تشکیل شده؟
morningStar = nison.isPatternActive(37, s)

// مثال: اولین الگوی فعال در این کندل
firstId = nison.firstActivePattern(s)
name = nison.patternName(firstId)
```

## لیست الگوها (۶۴ الگو)

### تک‌کندلی
Doji، Long-legged Doji، Gravestone Doji، Dragonfly Doji، Rickshaw Man، Spinning Top، Hammer، Hanging Man، Shooting Star، Inverted Hammer، Bullish/Bearish Marubozu، Bullish/Bearish Belt Hold

### دو‌کندلی
Bullish/Bearish Engulfing، Dark Cloud Cover، Piercing Pattern، Bullish/Bearish Harami، Harami Cross، Tweezers Top/Bottom، Counterattack Lines، On-neck، In-neck، Thrusting، Separating Lines، Window، Gapping Tasuki، Side-by-side White Lines

### سه‌کندلی و چندکندلی
Morning/Evening Star، Morning/Evening Doji Star، Abandoned Baby، Three Black Crows، Upside Gap Two Crows، Three White Soldiers، Advance Block، Stalled Pattern، Tri-star، Unique Three River Bottom، Rising/Falling Three Methods، Mat-hold، High/Low-price Gapping Play

### بلندمدت
Three Mountain Top، Three River Bottom، Three Buddha Top، Inverted Three Buddha Bottom، Tower Top/Bottom، Dumpling Top، Fry Pan Bottom

## تنظیمات

- **آستانه دوجی**: درصد رنج کندل (پیش‌فرض ۱۰٪)
- **بدنه کوچک/بلند**: برای تشخیص ستاره، هارامی و...
- **نسبت سایه**: برای چکش و ستاره ریزش (پیش‌فرض ۲×)
- **دوره روند**: برای تمایز Hammer از Hanging Man

## مرحله بعد

وقتی استراتژی خودتان را بدهید، این کتابخانه به‌عنوان یکی از شرط‌های ورود/خروج به استراتژی وصل می‌شود.

## منابع (اولویت)

| اولویت | منبع | کاربرد |
|--------|------|--------|
| **۱** | انگلیسی — *Japanese Candlestick Charting Techniques* | **قوانین شناسایی الگو** |
| **۲** | فارسی KohanFx (۱۹۸ صفحه) | نام فارسی روی چارت |
| **۳** | دو‌زبانه خلاصه (۱۲۶ صفحه) | فهم و نکات تکمیلی |

جزئیات: [`docs/book-references.md`](docs/book-references.md)  
واژه‌نامه فارسی: [`docs/pattern-names-fa.md`](docs/pattern-names-fa.md)
