# استراتژی نقطه کور (Blind Spot)

پکیج آموزشی + اندیکاتور بر اساس:

- ویدیوهای آموزشی استراتژی نقطه کور (کلاسیک Daily + نسخه لایو)
- جزوه پرایس‌اکشن رفتارشناسی حرکت قیمت (سعید خاکستر)
- مفاهیم IDR / ATR / توان حرکتی (TH)

## خروجی‌ها

| فایل | توضیح |
|------|--------|
| `docs/آموزش-استراتژی-نقطه-کور.pdf` | آموزش دقیق فارسی |
| `docs/ANALYSIS.md` | خلاصه تحلیلی قوانین |
| `indicators/NoghteKoor_BlindSpot.pine` | اندیکاتور TradingView (Pine v5) |
| `indicators/NoghteKoor_BlindSpot.mq4` | اندیکاتور MetaTrader 4 |
| `indicators/NoghteKoor_BlindSpot.mq5` | اندیکاتور MetaTrader 5 |
| `assets/` | دیاگرام‌ها و فریم‌های آموزشی |

## خلاصه منطق

1. **کلاسیک:** شکست سطح → فاصله حدود ۱ رنج (TH/ATR/IDR) → فقط کندل بعدی Limit روی ناحیه → اگر نخورد حذف
2. **لایو:** کندل جاری زودتر از کلوز، رنجش را پر کند و زمان باقی مانده باشد → انتظار بازگشت به Open/Close کندل قبلی

## نصب اندیکاتور

### TradingView
1. Pine Editor را باز کنید
2. محتوای `NoghteKoor_BlindSpot.pine` را بچسبانید
3. Add to chart

### MT4
1. فایل `NoghteKoor_BlindSpot.mq4` را در `MQL4/Indicators` کپی کنید
2. Compile در MetaEditor
3. از Navigator روی چارت بیندازید

## بازتولید PDF

```bash
pip install reportlab arabic-reshaper python-bidi pillow
python3 docs/generate_pdf.py
```

> صرفاً آموزشی است؛ توصیه مالی نیست.
