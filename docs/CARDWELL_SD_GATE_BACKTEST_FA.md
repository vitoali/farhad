# بک‌تست Cardwell + SD Magnet Gate

دوره ~۲–۳ ماه | BTC / EURUSD / XAU | 5m–4h  
خروج پیش‌فرض گزارش: **ATR High-WR (SL=2×ATR / TP=1×ATR)**

## حالت‌های Gate
| Gate | معنی |
|------|------|
| cardwell_only | بدون فیلتر SD |
| near | فقط نزدیک Demand/Supply (با حافظه ۲۰ کندل) |
| magnet | فقط جهت Magnet |
| near_or_magnet | یکی کافی (پیشنهادی) |
| near_and_magnet | هر دو لازم |

## وین‌ریت ٪ — near_or_magnet vs فقط Cardwell

| نماد | TF | Cardwell alone | + SD Gate (OR) | تعداد ترید alone→gate |
|------|----|----------------|----------------|------------------------|
| BTC | 5m | 61.9 | 53.5 | 257→114 |
| BTC | 15m | 62.7 | **64.3** | 83→42 |
| BTC | 1h | 69.7 | 58.3 | 33→12 |
| BTC | 4h | 55.6 | **75.0** | 9→4 |
| EURUSD | 5m | 61.1 | 58.5 | 211→94 |
| EURUSD | 15m | 64.6 | **68.4** | 65→19 |
| EURUSD | 1h | 63.0 | 54.6 | 27→11 |
| XAU | 5m | 71.7 | **73.1** | 184→119 |
| XAU | 15m | 75.4 | 71.1 | 61→38 |
| XAU | 1h | 53.6 | **61.5** | 28→13 |
| XAU | 4h | 85.7 | **100** | 7→6 |

## میانگین (نمونه با ≥۵ ترید)
| Gate | میانگین WR | میانگین تعداد ترید |
|------|------------|---------------------|
| **near_or_magnet** | **66.3%** | ~۴۰ |
| near | 64.8% | ~۳۳ |
| cardwell_only | 64.0% | ~۸۱ |
| magnet | 63.0% | ~۲۰ |
| near_and_magnet | 59.0% | ~۱۳ |

## جمع‌بندی
- گیت SD عمدتاً **تعداد ترید را حدود ۵۰٪ کم می‌کند**.
- میانگین WR با `near_or_magnet` کمی بهتر از Cardwell alone است (~۶۶٪ vs ~۶۴٪).
- بهترین بهبودها: BTC 15m/4h، EURUSD 15m، XAU 5m/1h/4h.
- روی بعضی LTFها (مثل BTC 5m) گیت WR را کمی پایین می‌آورد ولی نویز را فیلتر می‌کند.

فایل خام: `backtest/results/cardwell_sd_gate_full.csv`
