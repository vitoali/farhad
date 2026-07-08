# ATR تیرکس در TradingView — راهنمای دقیق

برای **همان اعداد MT5** از اندیکاتور جامعه استفاده کنید، نه پنل تقریبی ما.

## روش پیشنهادی (چک AUDDKK و بقیه نمادها)

### ۱. اندیکاتور جامعه را اضافه کنید

1. چارت **AUDDKK** → تایم‌فریم **1H**
2. پایین صفحه **Indicators**
3. جستجو: `ATR TRex ipooya`
4. انتخاب: **ATR TRex [ipooya]**  
   https://www.tradingview.com/script/MeOUBz32-ATR-TRex-ipooya/
5. **Add to chart**

جایگزین کامل‌تر (پنل شبیه MT5):

- **Trex [MrD3v]** — https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/  
  (سورس بسته؛ فقط Add to chart)

### ۲. مقایسه با MT5

| MT5 TRex | TradingView ipooya |
|----------|-------------------|
| ردیف True Range | اعداد TR + Live |
| توان حرکتی Th | TH |
| Pips(ATR) / TP(Th) | در نسخه ipooya بعد از آپدیت TH |

هر دو را روی **یک نماد و TF** بگذارید و همزمان نگاه کنید.

### ۳. کندل‌شناس و پیوت

- **کندل‌شناس:** `CandleRecognitionLib`
- **پیوت:** `MarketStructureEngine` (بعداً با ATR دقیق)

---

## استفاده در استراتژی (Library)

Pine نمی‌تواند اندیکاتور دیگر را import کند؛ باید **سورس** را Library کنید:

1. ipooya → **Source code** → Open in editor
2. کپی کل کد
3. `indicator(...)` را به `library("CommunityTrexAtr", overlay=true)` تبدیل کنید
4. توابع TR/TH را `export` کنید
5. Publish
6. در استراتژی: `import YOUR_USER/CommunityTrexAtr/1 as trex`

راهنمای vendor: `pine/vendor/README.md`

---

## چرا پنل خودمان را حذف کردیم؟

بک‌تست روی AUDDKK نشان داد اعداد تقریبی ما با MT5 یکی نیست (مثلاً H1: ما ~36، MT5 ~50). اندیکاتورهای ipooya/MrD3v از **فرمول اختصاصی خاکستر** استفاده می‌کنند.

---

## لینک‌های مفید

| اندیکاتور | لینک | سورس |
|-----------|------|------|
| ATR TRex [ipooya] | [MeOUBz32](https://www.tradingview.com/script/MeOUBz32-ATR-TRex-ipooya/) | باز |
| ATR TRex [SHK] | [fYVUKY3q](https://www.tradingview.com/script/fYVUKY3q-ATR-TRex-SHK/) | باز |
| Trex [MrD3v] | [wv9EwdkR](https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/) | بسته |
| ATR TREX (Aminhd) | [KacYDz5P](https://www.tradingview.com/script/KacYDz5P-ATR-TREX/) | باز |
