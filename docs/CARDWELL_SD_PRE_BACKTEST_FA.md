# بک‌تست: Cardwell + SD Gate + Pre-Buy/Pre-Sell

خروج: ATR High-WR (SL=2× / TP=1×) | دوره ~۲–۳ ماه

## منطق درخواستی
Cardwell فقط وقتی نشان داده می‌شود که **حداقل یکی** از این‌ها برقرار باشد:

| Long | Short |
|------|-------|
| Near Demand | Near Supply |
| یا Magnet ▲ UP | یا Magnet ▼ DOWN |
| یا **Pre-Buy** (RSI&lt;40 و EWO منفی در حال بالا) | یا **Pre-Sell** (RSI&gt;60 و EWO مثبت در حال پایین) |

= حالت **`SD OR Pre`**

## نتایج وین‌ریت ٪ — SD OR Pre

| نماد | 5m | 15m | 1h | 4h |
|------|----|-----|----|----|
| BTC | 51.9 (131) | **65.2** (46) | 62.5 (16) | 75.0 (4) |
| EURUSD | 58.0 (100) | **76.9** (26) | 57.1 (14) | 100 (2) |
| XAU | **72.1** (122) | 71.1 (38) | **66.7** (15) | 100 (6) |

## مقایسه میانگین (نمونه ≥۵ ترید)

| Gate | میانگین WR | توضیح |
|------|------------|--------|
| **SD AND Pre** | **70.1%** | سخت‌گیرتر، ترید خیلی کمتر |
| **SD OR Pre** (درخواستی) | **68.2%** | Near/Magnet **یا** Pre |
| Pre Only | 67.3% | فقط Pre |
| Near OR Magnet | 66.3% | بدون Pre |
| Cardwell alone | 64.0% | بدون گیت |

نسبت به فقط Near/Magnet: میانگین WR حدود **+۱.۵** و چند ترید بیشتر.  
نسبت به Cardwell alone: WR متوسط بالاتر، حدود **۵۳٪** تریدها نگه داشته می‌شوند.

## نکته
روی BTC 5m هنوز گیت WR را نسبت به alone پایین می‌آورد؛ روی EURUSD 15m و XAU 1h بهبود واضح است.

استراتژی: `indicators/Cardwell_SD_Magnet_Gate_Strategy.pine`  
پیش‌فرض Gate Mode = **SD OR Pre**
