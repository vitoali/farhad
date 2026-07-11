# دفتر یادگیری بک‌تست — اندیکاتورها

دوره: ~۳۱ روز گذشته

## منبع داده

- **اول بایننس** → OKX / KuCoin / Gate / Bybit → Yahoo
- BTC/HYPE: OKX | BEAT: KuCoin | EUR/XAU: Yahoo

## مدل ریسک در بک‌تست

| بازار | SL | TP | هزینه |
|-------|----|----|-------|
| **کریپتو** | **5%** | **5%** (RR 1:1) | ~0.1% RT |
| فارکس | 3 pip | RR 1:1 | ~1 pip |
| Bj Bot (فارکس) | swing+ATR native | R:R=1 | — |

---

## #1 UT Bot v2

### نتایج یک ماه

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 15m | 380 | 21.3 | 0.39 |
| BTCUSDT | 1h | 82 | 31.7 | 0.59 |
| BTCUSDT | 4h | 24 | 37.5 | **0.83** |
| EURUSD | 15m | 309 | 45.3 | 0.16 |
| EURUSD | 1h | 73 | 45.2 | 0.16 |
| EURUSD | 4h | 17 | 29.4 | 0.09 |
| XAUUSD | 15m | 198 | 30.8 | 0.11 |
| XAUUSD | 1h | 56 | 23.2 | 0.06 |
| XAUUSD | 4h | 14 | 0.0 | 0.00 |

### نقاط قوت (چرا گاهی درست بود)
- در **روند EURUSD 15m/1h** WR ~45% — بهتر از random
- منطق TSL با ATR نویز را فیلتر می‌کند
- `barstate.isconfirmed` — بدون repaint

### نقاط ضعف
- **PF < 1** همه جا — هزینه + SL تنگ‌تر از TP در عمل
- **XAU 1h/4h** شکست سنگین — طلا نوسان زیاد، TSL 1×ATR کافی نیست
- سیگنال زیاد در 15m → overtrading

### دلیل موفقیت سیگنال‌های درست
- انبساط ATR بعد از فشردگی + ادامه روند در جهت crossover

### نگه داریم / حذف / بهبود
- **نگه:** لایه فیلتر روند
- **بهبود:** mult بالاتر روی XAU، فیلتر ADX، TF 1h+
- **ترکیب:** با Bj Bot به‌عنوان تأیید ورود

---

## #2 AlphaTrend

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 15m | 70 | 22.9 | 0.48 |
| BTCUSDT | 1h | 12 | 50.0 | **1.50** |
| BTCUSDT | 4h | 4 | 50.0 | **1.50** |
| EURUSD | 15m | 71 | 52.1 | 0.22 |
| EURUSD | 1h | 20 | 45.0 | 0.16 |
| XAUUSD | 15m | 41 | 43.9 | 0.16 |
| XAUUSD | 1h | 9 | 22.2 | 0.06 |

### نقاط قوت
- **WR بالاتر از UT Bot** روی EURUSD 15m (52%)
- فیلتر MFI/RSI سیگنال‌های تکراری را کم می‌کند (71 vs 309 trade)
- تأخیر [2] + alternation → کیفیت بهتر

### نقاط ضعف
- هنوز PF < 1
- XAU 1h ضعیف — MFI روی CFD طلا گمراه‌کننده
- نسخه confirmed بهتر از خام (در کد پیاده شد)

### دلیل موفقیت
- MFI > 50 + شیب AlphaTrend مثبت = فشار خرید واقعی قبل از crossover

### نگه داریم / حذف / بهبود
- **نگه:** فیلتر مومنتوم، سیگنال کمتر و تمیزتر
- **بهبود:** novolumedata=true برای XAU، بافر MFI 55/45
- **ترکیب:** AND با UT Bot long/short

---

## #3 Bj Bot / 3Commas

### نتایج (خروج native swing+ATR)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 15m | 24 | 54.2 | **1.22** |
| BTCUSDT | 1h | 8 | 62.5 | **1.50** |
| EURUSD | 15m | 20 | 55.0 | 0.78 |
| EURUSD | 1h | 3 | 66.7 | 1.19 |
| XAUUSD | 15m | 19 | 47.4 | 0.99 |
| XAUUSD | 1h | 7 | 71.4 | **2.61** |

### نقاط قوت
- **بهترین PF تا اینجا** — XAU 1h PF=2.61
- SL ساختاری (swing+ATR) بهتر از درصد ثابت روی طلا
- معاملات کمتر، کیفیت بالاتر
- WR 55-71% روی ترکیب‌های خوب

### نقاط ضعف
- نمونه کم (3-20 trade) — اعتبار آماری محدود در ۱ ماه
- EURUSD 15m هنوز PF<1
- باگ lookForExit در Pine (trail) — در بک‌تست trail خاموش بود

### دلیل موفقیت
- کراس EMA21/50 **بعد از pullback به swing** → SL پشت ساختار واقعی
- R:R=1 هدف نزدیک‌تر = احتمال بیشتر رسیدن

### نگه داریم / حذف / بهبود
- **نگه:** قالب SL/TP ساختاری — **بهترین پایه استراتژی نهایی**
- **بهبود:** فیلتر chop، fix trail bug، HTF
- **ترکیب:** ورود اصلی؛ UT+Alpha به‌عنوان فیلتر تأیید

---

## جمع‌بندی اولیه برای استراتژی نهایی

```
ورود:     Bj Bot MA cross (EMA21/50)
فیلتر 1:  UT Bot جهت روند
فیلتر 2:  AlphaTrend مومنتوم هم‌جهت
SL:       swing low/high - ATR × RiskM  (از Bj Bot)
TP:       R:R = 1 (یا 1:2 در روند قوی)
TF اولویت: 1h و 4h
```

---

## #4 AlphaX FORGE — Pattern Forge Engine

**نوع:** اندیکاتور **محدوده/الگو** — اولین کد محدوده‌ای در پروژه ✅  
**بک‌تست:** Double Top/Bottom (زیرمجموعه کامل FORGE) | ~۳۱ روز

### نتایج بک‌تست (الگوی Double Top/Bottom)

| نماد | TF | سیگنال | معاملات | WR% | PF |
|------|-----|--------|---------|-----|-----|
| BTCUSDT | 15m | 83 | 80 | 31.2 | **1.67** |
| BTCUSDT | 1h | 5 | 5 | 0.0 | 0.0 |
| XAUUSD | 15m | 42 | 41 | 31.7 | **1.57** |
| EURUSD | 15m | 0 | 0 | — | — |

### منطق محدوده (مثال Double Bottom)
```
کف ۱ ≈ کف ۲ (تلورانس lvlTol=3%)
قله میانی = neckline
شکست neckline + ATR×breakAtr → ورود Long
TP2 = neckline + ارتفاع الگو (measured move)
SL = 25% فاصله entry→target (پیش‌فرض)
```

### نقاط قوت
- **PF > 1.5** با WR ~31% → R:R بالا (هدف measured move درست کار می‌کند)
- فیلتر confluence (min 5/10) + chop gate + min R:R 1.5
- `barstate.isconfirmed` + `lookahead_off` روی HTF
- SL/TP/Entry شفاف — آماده strategy

### نقاط ضعف
- WR پایین (~31%) — نیاز به صبر و فیلتر grade A
- EURUSD: الگو تشخیص داده نشد (تلورانس/اندازه برای فارکس)
- 1h نمونه کم؛ 4h داده کافی نبود (نیاز 600+ bar)
- پیچیدگی بالا — ریسک overfitting نوع الگو

### دلیل موفقیت سیگنال‌های درست
- شکست neckline با بافر ATR = breakout واقعی نه نویز
- هدف measured move = قیمت به ناحیه عدالت‌جویی می‌رود
- HTF هم‌جهت + chop پایین = فضای روند برای حرکت

### دلیل شکست
- false breakout neckline
- الگو در chop (حتی با gate)
- SL 25% target distance — در نوسان شدید زود می‌خورد

### نقش در استراتژی نهایی
- **ورود ساختاری** بر پایه الگو + **Bj Bot** برای تأیید روند
- فقط grade A/B + HTF هم‌جهت
- TF 1h+ ترجیحاً

---

## #7 SuperTrend

**فایل:** `SUPER_TREND_ccf2.txt` | **نوع:** روند (ATR trailing)

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 15m | 103 | 56.3 | **1.56** |
| BEATUSDT | 1h | 21 | 57.1 | **1.38** |
| BTCUSDT | 1h | 18 | 38.9 | 0.61 |
| BTCUSDT | 15m | 31 | 25.8 | 0.54 |
| XAUUSD | 15m | 47 | 38.3 | 0.12 |

### نقاط قوت
- **BEAT 15m/1h PF>1.3** — روی آلت‌کوین پرنوسان بهتر از BTC
- منطق ساده و قابل فهم — ATR×3 + HL2
- سیگنال کمتر از UT Bot

### نقاط ضعف
- فارکس/طلا با SL 5% ثابت شکست می‌خورد (PF<0.2)
- بدون `barstate.isconfirmed` — ریسک repaint جزئی
- BTC 15m ضعیف

### نگه داریم / حذف / بهبود
- **نگه:** فیلتر روند روی BEAT/crypto
- **بهبود:** confirmed close، mult بالاتر روی XAU
- **ترکیب:** با Bj Bot به‌عنوان تأیید جهت

---

## #8 Chandelier Exit

**فایل:** `Chandelier_Exit_a3e4.txt` | **نوع:** روند (highest/lowest − ATR)

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 4h | 4 | 75.0 | **3.77** |
| BEATUSDT | 15m | 135 | 46.7 | **1.37** |
| BTCUSDT | 1h | 30 | 33.3 | 0.50 |
| XAUUSD | 15m | 60 | 28.3 | 0.07 |

### نقاط قوت
- **BTC 4h PF=3.77** (نمونه کم)
- `barstate.isconfirmed` در آلرت‌ها
- SL ساختاری داخل خود اندیکاتور (longStop/shortStop)

### نقاط ضعف
- overtrading در 15m (135 trade روی BEAT)
- فارکس/طلا با مدل 5% SL نامناسب
- شبیه SuperTrend ولی سیگنال بیشتر

### نگه داریم / حذف / بهبود
- **نگه:** TF 4h برای crypto
- **بهبود:** فیلتر ADX، کاهش سیگنال 15m
- **ترکیب:** لایه خروج/تریلینگ در استراتژی نهایی

---

## #9 Lorentzian Classification

**فایل:** `Machine_Learning_Lorentzian_9f8e.txt` | **نوع:** ML/KNN

### نتایج (پورت ساده‌شده — بدون kernel filter)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 15m | 160 | 46.9 | **0.86** |
| HYPEUSDT | 15m | 87 | 34.5 | **0.85** |
| BTCUSDT | 1h | 72 | 23.6 | 0.39 |
| BTCUSDT | 15m | 75 | 26.7 | 0.49 |

### نقاط قوت
- پیش‌بینی ۴ کندل آینده با KNN Lorentzian — منطق نوآورانه
- فیلترهای volatility/regime/ADX در Pine (در پورت خاموش)
- نزدیک به breakeven روی BEAT/HYPE 15m

### نقاط ضعف
- **هنوز PF<1** با مدل 5%/5% — نیاز به فیلتر kernel+EMA
- محاسبه سنگین — وابسته به MLExtensions
- early signal flip در رنج

### نگه داریم / حذف / بهبود
- **نگه:** ایده feature engineering (RSI/WT/CCI/ADX)
- **بهبود:** پورت کامل kernel filter + worst-case mode
- **ترکیب:** فیلتر confluence، نه ورود مستقل

---

## #10 IFVG Sniper Entry Engine

**فایل:** `IFVG_ENGINE_6b53.txt` | **نوع:** zone/FVG inversion

### منطق
- FVG مخفی ذخیره می‌شود → وقتی قیمت FVG را invert کند (شکست با بافر ATR) → ورود
- SL = ATR×1.5 | TP = 3R (پیش‌فرض Pine)
- فیلتر Balanced: gap≥0.25 ATR، body≥50%، range≥0.6 ATR

### نتایج (zone native SL/TP)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 1h | 8 | 50.0 | **2.60** |
| BTCUSDT | 4h | 2 | 50.0 | **2.79** |
| BEATUSDT | 15m | 30 | 30.0 | **0.97** |
| BTCUSDT | 15m | 21 | 23.8 | 0.67 |

### نقاط قوت
- **PF>2.5 روی BTC 1h/4h** — inversion + فیلتر کیفیت کار می‌کند
- SL/TP ساختاری داخل اندیکاتور (ATR-based)
- سیگنال کم → overtrading ندارد

### نقاط ضعف
- WR پایین (~24-30%) روی 15m
- BEAT 1h ضعیف — نمونه کم
- وابسته به حافظه FVG و پارامتر filter mode

### نگه داریم / حذف / بهبود
- **نگه:** ورود zone-based برای استراتژی نهایی — **اولویت بالا**
- **بهبود:** TF 1h+، ترکیب با HTF bias
- **ترکیب:** تأیید با Bj Bot + SMC PRO zone

---

## #11 Breaker Blocks [LuxAlgo]

**فایل:** `Breaker_Blocks_with_Signals__LuxAlgo_103c.txt` | **نوع:** zone/OB breaker

### منطق (پورت ساده‌شده)
- شکست ساختار (MSS) + آخرین کندل مخالف = zone breaker
- ورود: تشکیل BB (+BB/-BB) + retest (signUP/signDN)
- SL/TP: ATR×2 / R:R 2:1

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 18 | 38.9 | **1.36** |
| BEATUSDT | 15m | 87 | 40.2 | **1.13** |
| BTCUSDT | 15m | 56 | 37.5 | 0.84 |
| BTCUSDT | 1h | 24 | 29.2 | 0.57 |

### نقاط قوت
- **PF>1 روی BEAT** — breaker retest روی آلت‌کوین پرنوسان
- منطق SMC شناخته‌شده — BOS + opposing candle
- چند نوع سیگنال (formation + retest)

### نقاط ضعف
- پیچیدگی zigzag کامل Pine پورت نشده — ساده‌سازی
- BTC 1h PF<1
- سیگنال زیاد در 15m (87 trade)

### نگه داریم / حذف / بهبود
- **نگه:** لایه ساختار برای استراتژی نهایی
- **بهبود:** پورت کامل zigzag/MSS، فیلتر PD array
- **ترکیب:** فقط signUP/signDN + HTF هم‌جهت

---

## #12 Smart Money Concepts PRO v2

**فایل:** `Money_Concepts_PRO_v2.tiktok0_9e67.txt` | **نوع:** zone/SMC confluence

### منطق
- BOS/CHoCH → OB جدید → retest OB در Discount (long) / Premium (short)
- فیلتر HTF EMA21/50 + zone P/D

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 1h | 1 | 100 | — |
| BTCUSDT | 15m | 4 | 50.0 | 1.0 |
| XAUUSD | 15m | 4 | 50.0 | 0.62 |
| BEATUSDT | 15m | 4 | 25.0 | 0.36 |

### نقاط قوت
- **فیلتر confluence قوی** — کیفیت بالا، کمیت کم
- منطق کامل: OB + P/D + HTF — نزدیک ایده استراتژی نهایی
- barstate + non-repaint HTF در Pine

### نقاط ضعف
- **نمونه بسیار کم** (۱-۴ trade در ماه) — فیلترها سخت‌گیرانه
- BEAT ضعیف در این دوره
- HTF در پورت Python تقریبی (resample)

### نگه داریم / حذف / بهبود
- **نگه:** **بهترین فریمورک فیلتر confluence** برای ترکیب نهایی
- **بهبود:** شل کردن فیلتر zone در crypto، HTF دقیق‌تر
- **ترکیب:** لایه تأیید نهایی روی Bj Bot + IFVG

---

## #13 Zero Lag Trend Signals

**فایل:** `Zero_Lag_Trend_Signals_TIKTOK_8b12.txt` | **نوع:** trend/ZLEMA

### منطق
- ZLEMA + volatility band → trend
- ورود: pullback به ZLEMA در جهت trend

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 14 | 50.0 | **0.92** |
| BEATUSDT | 15m | 47 | 44.7 | **0.79** |
| BTCUSDT | 1h | 9 | 33.3 | 0.97 |
| BTCUSDT | 15m | 16 | 25.0 | 0.43 |

### نقاط قوت
- نزدیک breakeven روی BEAT/BTC 1h
- سیگنال کمتر از UT Bot
- MTF table در Pine (فیلتر اضافی)

### نقاط ضعف
- فارکس/طلا با SL 5% شکست (PF<0.2)
- 4h تقریباً بدون سیگنال
- request.security MTF در پورت نیست

### نگه داریم / حذف / بهبود
- **نگه:** فیلتر روند جایگزین UT Bot
- **بهبود:** MTF consensus
- **ترکیب:** تأیید pullback در استراتژی نهایی

---

## #14 Trendline Breakouts [ChartPrime]

**فایل:** `Trendline_Breakouts_With__df18.txt` | **نوع:** trend/pattern

### منطق
- pivot high/low → خط روند → شکست + TP/SL بر اساس Zband

### نتایج
- **۱ سیگنال per نماد/TF در ۳۱ روز** — نمونه آماری صفر

### نقاط قوت
- SL/TP داخل اندیکاتور (Zband×20)
- ایده شکست خط روند + هدف مشخص

### نقاط ضعف
- **تقریباً غیرقابل بک‌تست** در ۱ ماه — سیگنال خیلی نادر
- منطق time-based پیچیده — پورت ناقص
- PF غیرقابل اتکا (۱ trade)

### نگه داریم / حذف / بهبود
- **حذف از ورود مستقل** — نمونه کافی نیست
- **بهبود:** دوره بک‌تست طولانی‌تر، پورت کامل trendline
- **ترکیب:** فقط اگر نمونه >20 در ۳ ماه

---

## #15 EWO/RSI Advanced Strategy

**فایل:** `rsi_advanced_868b.txt` | **نوع:** strategy/EWO+RSI

### منطق
- EWO + RSI crossover 40/60 + MFI + volume
- فیلتر exhaustion: breakout بالای highest high یا oversold zone

### نتایج

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 15m | 9 | 88.9 | **7.77** |
| BTCUSDT | 4h | 3 | 66.7 | **8.27** |
| BTCUSDT | 15m | 7 | 57.1 | **1.20** |
| BEATUSDT | 1h | 5 | 60.0 | **1.39** |

### نقاط قوت
- **بهترین PF در گروه trend/strategy** روی HYPE/BTC 4h
- فیلتر exhaustion از false bounce جلوگیری می‌کند
- WR بالا روی HYPE 15m (89%)

### نقاط ضعف
- **نمونه خیلی کم** (۳-۹ trade) — اعتبار آماری محدود
- BEAT 15m ضعیف (PF=0.36)
- فارکس: صفر سیگنال در ۱ ماه

### نگه داریم / حذف / بهبود
- **نگه:** ایده exhaustion filter — ارزشمند برای ترکیب
- **بهبود:** بک‌تست ۳-۶ ماهه
- **ترکیب:** فیلتر مومنتوم روی Bj Bot entry

---

## #16 Monster Trex Vol — BLOCKED

**فایل:** `monster_e007.txt` | **وضعیت:** نیاز به کتابخانه‌های Pine خارجی

کتابخانه‌ها: `KhaksterTrexAtrLib`, `MarketStructureEngine`, `KhaksterEntryLib`, `KhaksterSmartMoneyLib`, `CandleRecognitionLib`

**اقدام:** پورت دستی بعد از دریافت منطق کتابخانه‌ها یا بازنویسی ساده‌شده بر پایه FTC/RTP zones.

---

## پیشرفت batch (فاز ۱ — ۵۳ فایل کامل)

| مرحله | تعداد | وضعیت |
|--------|-------|--------|
| تحلیل استاتیک | 75 | ✅ |
| بک‌تست Python | **15** (#1–#15) | ✅ |
| monster (کتابخانه خارجی) | 1 | ⏳ blocked |
| باقی‌مانده zone/trend | ~37 | در صف |

**بک‌تست شده:** `results/backtest_priority_zone.json`

---
