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

## #17 Machine Learning RSI (Zeiierman)

**فایل:** `machin_rsi_313b.txt` | **نوع:** ML / 8-feature KNN on RSI

### منطق
- ۸ ویژگی RSI (value, slope, accel, mid, percentile, volatility, spread, regime)
- بانک حافظه ۵۰۰ بار + KNN با فاصله Lorentzian فشرده
- Rank ≥60 و Confidence ≥50 + Trend Gate (ML Supertrend) + Vol Band + Chop Filter
- سیگنال روی flip stance با cooldown ۵ بار

### نتایج (~۳۱ روز، SL/TP 5% crypto)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 15m | 12 | 58.3 | **1.81** |
| HYPEUSDT | 1h | 8 | 62.5 | **1.45** |
| BEATUSDT | 15m | 58 | 50.0 | **1.21** |
| BEATUSDT | 1h | 7 | 42.9 | 0.69 |
| BTCUSDT | 15m | 11 | 18.2 | 0.16 |

### نقاط قوت
- **PF>1.4 روی HYPE** — فیلتر rank/confidence کار می‌کند
- **BEAT 15m PF=1.21** با WR 50%
- ML Supertrend + chop filter
- `barstate.isconfirmed` + cooldown

### نقاط ضعف
- BTC ضعیف — فیلترها سخت
- فارکس/طلا با SL 5% نامناسب
- 4h تقریباً بدون سیگنال
- Auto-weight optimizer ساده‌شده

### نگه داریم / حذف / بهبود
- **نگه:** HYPE/BEAT 15m-1h — **بهترین ML تا اینجا**
- **بهبود:** Fisher auto-weights کامل
- **ترکیب:** فیلتر confluence با SMC PRO

---

## #18 Supply and Demand Zones (Flux Charts)

**فایل:** `supply_demand_72be.txt` | **نوع:** Zone retest (bullRetest / bearRetest)

### منطق
- Swing pivot (30) → zone با padding wick میانگین ۵ کندل
- Retest: supply rejection (high≥bottom, close<bottom) / demand bounce
- Pending flip برای breakout ناموفق
- SL زیر/بالای zone + TP 2R

### نتایج (~۳۱ روز، zone-native SL/TP)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 1h | 54 | 59.3 | **2.49** |
| HYPEUSDT | 15m | 230 | 56.1 | **1.74** |
| BEATUSDT | 15m | 482 | 47.5 | **1.47** |
| EURUSD | 15m | 251 | 49.0 | **1.85** |
| XAUUSD | 1h | 10 | 40.0 | **2.86** |

### نقاط قوت
- **BTC 1h PF=2.49** — retest logic قوی روی TF بالاتر
- **HYPE/BEAT 15m PF>1.4** با نمونه زیاد
- **فارکس EURUSD 15m PF=1.85** با zone-native SL
- سیگنال زیاد — مناسب فیلتر confluence

### نقاط ضعف
- 15m BTC PF≈1 — نویز زیاد
- 4h نمونه کم (pivot=30 سنگین)
- بدون فیلتر HTF/trend — همه retestها معامله می‌شوند

### نگه داریم / حذف / بهبود
- **نگه:** BTC/HYPE 1h + EURUSD 15m
- **بهبود:** فیلتر trend + rankBy Strongest
- **ترکیب:** confluence با IFVG / Breaker Blocks

---

## #19 Strong Pullback Signals

**فایل:** `strong_pulback_7019.txt` | **نوع:** Breakout → limit pullback با SL ساختاری

### منطق
- EMA 34/144 trend + breakout از swing 20-bar
- Limit fill روی pullback EMA − 0.4 ATR
- HTF EMA 4h/50 alignment + cooldown 10 bar
- SL: swing extreme ± 0.3 ATR (capped 0.5–2.5 ATR) | TP1: 1R

### نتایج (~۳۱ روز، native SL/TP 1R)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| EURUSD | 15m | 29 | 65.5 | **1.90** |
| BEATUSDT | 1h | 12 | 66.7 | **2.00** |
| BTCUSDT | 1h | 12 | 58.3 | **1.40** |
| HYPEUSDT | 4h | 3 | 66.7 | **2.00** |
| XAUUSD | 15m | 24 | 58.3 | **1.40** |

### نقاط قوت
- **فارکس EURUSD 15m PF=1.9** — HTF filter مؤثر
- **BEAT 1h PF=2.0** با WR 67%
- SL ساختاری + cap ATR — منطق Bj-like
- سیگنال کم ولی کیفیت بالاتر از trend-chasers

### نقاط ضعف
- BTC 15m PF=0.91 — pullback limit در رنج
- نمونه کم روی 4h
- Multi-TP (TP2/TP3) ساده‌شده به TP1 فقط

### نگه داریم / حذف / بهبود
- **نگه:** EURUSD/BEAT 1h — **بهترین pullback تا اینجا**
- **بهبود:** score filter onlyStrong
- **ترکیب:** entry pullback + Bj Bot structure confirmation

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
| بک‌تست Python | **19** (#1–#15, #17–#19) | ✅ |
| monster (کتابخانه خارجی) | 1 | ⏳ blocked |
| باقی‌مانده zone/trend | ~37 | در صف |

**بک‌تست شده:** `results/backtest_priority_zone.json`, `results/backtest_sd_sp.json`

---

---

## #20 Cardwell RSI Navigator

**فایل:** `Cardwell_RSI_Trade_Navigator__MarkitTick_1c8f.txt` | **کلید:** `cardwell_rsi`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **44.8%** | میانگین PF: **0.982**
- بهترین: HYPEUSDT 1h PF=2.167 WR=68.42%
- ضعیف‌ترین: EURUSD 4h PF=0.26

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 19 | 68.42 | 2.167 |
| BTCUSDT | 1h | 21 | 57.14 | 1.45 |
| BEATUSDT | 15m | 96 | 57.29 | 1.408 |
| XAUUSD | 1h | 20 | 45.0 | 1.321 |
| HYPEUSDT | 4h | 3 | 66.67 | 1.198 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #21 FVG Retest Engine

**فایل:** `fvg_return_faf7.txt` | **کلید:** `fvg_retest`

### وضعیت
- نمونه کافی برای بک‌تست نداشت (کمتر از ۳ معامله در اکثر ترکیب‌ها)
- تحلیل استاتیک در `results/analyses/`


---

## #22 Stop Hunt Radar

**فایل:** `sop_hunt_9b71.txt` | **کلید:** `stop_hunt`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **40.5%** | میانگین PF: **0.933**
- بهترین: BEATUSDT 1h PF=1.515 WR=57.14%
- ضعیف‌ترین: BEATUSDT 4h PF=0.501

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 49 | 57.14 | 1.515 |
| XAUUSD | 1h | 32 | 46.88 | 1.342 |
| HYPEUSDT | 1h | 56 | 46.43 | 1.206 |
| XAUUSD | 4h | 4 | 50.0 | 1.205 |
| EURUSD | 1h | 33 | 48.48 | 1.018 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #23 Smart Money Structure

**فایل:** `Smart_Money_Structure__GainzAlgo_4e52.txt` | **کلید:** `smart_money_structure`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **55.9%** | میانگین PF: **1.477**
- بهترین: HYPEUSDT 4h PF=6.745 WR=66.67%
- ضعیف‌ترین: HYPEUSDT 1h PF=0.618

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 4h | 3 | 66.67 | 6.745 |
| XAUUSD | 15m | 66 | 63.64 | 1.109 |
| XAUUSD | 1h | 14 | 57.14 | 0.912 |
| BTCUSDT | 1h | 31 | 51.61 | 0.906 |
| BEATUSDT | 1h | 23 | 47.83 | 0.789 |

### نگه داریم / حذف / بهبود
- **نگه** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #24 SMC PRO Confluence

**فایل:** `Smart_Money_Concepts_PRO_979a.txt` | **کلید:** `smc_pro_alt`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **40.9%** | میانگین PF: **1.019**
- بهترین: EURUSD 15m PF=1.311 WR=38.58%
- ضعیف‌ترین: XAUUSD 1h PF=0.822

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| EURUSD | 15m | 1003 | 38.58 | 1.311 |
| EURUSD | 4h | 51 | 47.06 | 1.298 |
| EURUSD | 1h | 228 | 44.74 | 1.294 |
| XAUUSD | 15m | 983 | 42.22 | 1.06 |
| BEATUSDT | 15m | 1522 | 39.55 | 1.048 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #25 OrderFlow FVG Matrix

**فایل:** `matrix_d1c3.txt` | **کلید:** `matrix_fvg`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **45.6%** | میانگین PF: **0.988**
- بهترین: BTCUSDT 4h PF=1.303 WR=46.67%
- ضعیف‌ترین: HYPEUSDT 15m PF=0.719

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 4h | 15 | 46.67 | 1.303 |
| HYPEUSDT | 4h | 20 | 45.0 | 1.188 |
| BEATUSDT | 1h | 137 | 51.09 | 1.182 |
| BEATUSDT | 15m | 807 | 48.95 | 1.085 |
| HYPEUSDT | 1h | 86 | 47.67 | 1.045 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #26 PUT/CALL VP Levels

**فایل:** `PUT___CALL_VP_Levels_90f8.txt` | **کلید:** `put_call_vp`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **32.7%** | میانگین PF: **0.465**
- بهترین: HYPEUSDT 1h PF=1.194 WR=42.61%
- ضعیف‌ترین: XAUUSD 1h PF=0.048

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 115 | 42.61 | 1.194 |
| BEATUSDT | 1h | 168 | 48.21 | 0.917 |
| BTCUSDT | 4h | 24 | 41.67 | 0.894 |
| BEATUSDT | 15m | 590 | 44.07 | 0.888 |
| BEATUSDT | 4h | 49 | 40.82 | 0.629 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #27 Ranked Order Blocks

**فایل:** `Ranked_Order_Block_Zones__Zeiierman_9c77.txt` | **کلید:** `ranked_ob`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **40.9%** | میانگین PF: **1.019**
- بهترین: EURUSD 15m PF=1.311 WR=38.58%
- ضعیف‌ترین: XAUUSD 1h PF=0.822

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| EURUSD | 15m | 1003 | 38.58 | 1.311 |
| EURUSD | 4h | 51 | 47.06 | 1.298 |
| EURUSD | 1h | 228 | 44.74 | 1.294 |
| XAUUSD | 15m | 983 | 42.22 | 1.06 |
| BEATUSDT | 15m | 1522 | 39.55 | 1.048 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #28 QQE Signals

**فایل:** `QQE_KHOOB_1aba.txt` | **کلید:** `qqe`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **36.1%** | میانگین PF: **0.732**
- بهترین: BEATUSDT 4h PF=2.769 WR=75.0%
- ضعیف‌ترین: XAUUSD 1h PF=0.046

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 4h | 8 | 75.0 | 2.769 |
| BTCUSDT | 4h | 6 | 50.0 | 1.832 |
| BEATUSDT | 15m | 134 | 48.51 | 1.385 |
| BEATUSDT | 1h | 44 | 52.27 | 1.306 |
| HYPEUSDT | 15m | 64 | 28.12 | 0.933 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #29 MACD MTF

**فایل:** `MACD_30e7.txt` | **کلید:** `macd_mtf`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **33.2%** | میانگین PF: **0.538**
- بهترین: BEATUSDT 1h PF=1.551 WR=58.93%
- ضعیف‌ترین: XAUUSD 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 56 | 58.93 | 1.551 |
| BTCUSDT | 4h | 13 | 38.46 | 1.16 |
| BEATUSDT | 15m | 231 | 45.02 | 1.08 |
| HYPEUSDT | 4h | 14 | 50.0 | 1.024 |
| BEATUSDT | 4h | 13 | 46.15 | 0.874 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #30 Power Order Blocks

**فایل:** `power_order_bloc_151a.txt` | **کلید:** `power_ob`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **38.1%** | میانگین PF: **1.015**
- بهترین: XAUUSD 4h PF=1.78 WR=41.67%
- ضعیف‌ترین: XAUUSD 1h PF=0.565

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 4h | 12 | 41.67 | 1.78 |
| EURUSD | 15m | 614 | 39.58 | 1.292 |
| EURUSD | 1h | 114 | 38.6 | 1.208 |
| BTCUSDT | 4h | 32 | 40.62 | 1.146 |
| XAUUSD | 15m | 594 | 38.72 | 1.035 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #31 SR Breaks LuxAlgo

**فایل:** `Support_and_Resistance_Levels_with_Breaks_9115.txt` | **کلید:** `sr_breaks`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **54.5%** | میانگین PF: **1.441**
- بهترین: XAUUSD 15m PF=3.534 WR=57.14%
- ضعیف‌ترین: XAUUSD 1h PF=0.431

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 15m | 21 | 57.14 | 3.534 |
| HYPEUSDT | 15m | 9 | 55.56 | 2.194 |
| BEATUSDT | 15m | 18 | 66.67 | 1.774 |
| BEATUSDT | 1h | 5 | 60.0 | 1.5 |
| BTCUSDT | 1h | 8 | 50.0 | 0.821 |

### نگه داریم / حذف / بهبود
- **نگه** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #32 Liquidity Pools LuxAlgo

**فایل:** `LIQUDITY_PPOOL_ce94.txt` | **کلید:** `liquidity_pool`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **34.1%** | میانگین PF: **0.865**
- بهترین: BTCUSDT 1h PF=1.038 WR=38.0%
- ضعیف‌ترین: BEATUSDT 4h PF=0.652

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 1h | 200 | 38.0 | 1.038 |
| BEATUSDT | 15m | 651 | 35.94 | 0.974 |
| EURUSD | 15m | 365 | 34.25 | 0.958 |
| XAUUSD | 4h | 8 | 37.5 | 0.926 |
| HYPEUSDT | 4h | 31 | 32.26 | 0.922 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله



---

## فهرست استاتیک (بدون پورت Python)

اندیکاتورهای زیر تحلیل استاتیک شدند. اکثراً visualization-only یا نیاز به پورت دستی دارند.

| # | فایل | نام | دسته | بک‌تست | یادداشت |
|---|------|-----|------|--------|--------|
| 41 | `3_3fa8.txt` | PMax Explorer | other/uncategorized | partial_manual | visualization / manual port |
| 42 | `4_4040.txt` | TrendMaster Pro 2.3 with Alerts | zone/fibonacci | partial_zone | سیگنال بدون barstate.isconfirmed… |
| 43 | `ATR_SL_FINDER_977b.txt` | Average True Range Stop Loss Finder | other/uncategorized | partial_manual | visualization / manual port |
| 44 | `AUTO_FIBO_ca53.txt` | FibFib | other/uncategorized | none_display_only | visualization / manual port |
| 45 | `BREAKOUT_PROBIPILITY_1c91.txt` | Breakout Probability (Expo) | other/uncategorized | partial_manual | visualization / manual port |
| 46 | `Buyside___Sellside_Liquidity_631a.txt` | Buyside & Sellside Liquidity [LuxAl | zone/smc | partial_manual | visualization / manual port |
| 47 | `CANDLE_d8b6.txt` | Candlestick Patterns Identified, up | other/uncategorized | partial_manual | visualization / manual port |
| 48 | `CM_Ultimate_MA_MTF_202b.txt` | CM_Ultimate_MA_MTF | other/uncategorized | none_display_only | visualization / manual port |
| 49 | `Divergence_for_Many_Indicators_2408.txt` | Divergence for Many Indicators v4 | other/uncategorized | partial_manual | visualization / manual port |
| 50 | `Divergence_for_many_indicator_2b36.txt` | Divergence for many indicator v3 | other/uncategorized | partial_manual | visualization / manual port |
| 51 | `FVG___IFVG_ICT_a586.txt` | FVG & IFVG ICT [TradingFinder] Inve | zone/fvg_ob | partial_manual | visualization / manual port |
| 52 | `Fair_Value_Gap_f587.txt` | Fair Value Gap [LuxAlgo] | zone/fvg_ob | none_display_only | ریسک lookahead در request.security… |
| 53 | `FxPipFinder_Engagement_Zone_41e2.txt` | FxPipFinder Engagement Zone | zone/order_block | partial_manual | visualization / manual port |
| 54 | `HISTORICAL_POPTRN_8ffc.txt` | Historical Pattern Projection [Mark | other/uncategorized | partial_manual | visualization / manual port |
| 55 | `Liquidity_Shift_Detection_eaf8.txt` | Liquidity Shift Detection [LSD] (Ze | zone/smc | partial_manual | visualization / manual port |
| 56 | `MACHIN_a826.txt` | Machine Learning Pivot Points (KNN) | ml/ml_regression | partial_core_only | visualization / manual port |
| 57 | `M_Pivot_Points_M_3e8d.txt` | CM_Pivot Points_M-W-D_4H_1H_Filtere | other/uncategorized | none_display_only | visualization / manual port |
| 58 | `New_Text_Document_ee2a.txt` | ICT Immediate Rebalance Toolkit [Lu | zone/order_block | partial_manual | visualization / manual port |
| 59 | `Order-Flow_Detection_d054.txt` | OrderFlow Absorption Matrix | zone/order_block | partial_manual | ریسک lookahead در request.security… |
| 60 | `Pivot_Points_High_Low___Missed__f352.txt` | Pivot Points High Low & Missed Reve | other/uncategorized | partial_manual | visualization / manual port |
| 61 | `QUANTOM_4271.txt` | Quantum Imbalance Trap [MarkitTick] | zone/order_block | partial_manual | ریسک lookahead در request.security… |
| 62 | `Reversal_Signals__TIKTOK_6ff8.txt` | Reversal Signals [LuxAlgo] | other/uncategorized | partial_manual | visualization / manual port |
| 63 | `SMART_MONEY_11c2.txt` | Smart Money Concepts [LuxAlgo] | zone/fvg_ob | partial_manual | ریسک lookahead در request.security… |
| 64 | `SQZMOM_LB_5806.txt` |  | other/uncategorized | none_display_only | visualization / manual port |
| 65 | `STRATGY_b6e6.txt` |  | other/uncategorized | partial_manual | سیگنال بدون barstate.isconfirmed… |
| 66 | `SUPER_TREND_4ed2.txt` | Supertrend Parameter Sensitivity 3D | other/uncategorized | partial_manual | visualization / manual port |
| 67 | `Smart_Money_Renko_Matri_bb35.txt` | Smart Money Renko Matrix [MarkitTic | zone/order_block | partial_manual | ریسک lookahead در request.security… |
| 68 | `Smart_Trader__Episode_03__by_Ata_Sabanc_7446.txt` | Smart Trader, Episode 03, by Ata Sa | zone/order_block | partial_manual | visualization / manual port |
| 69 | `Smart_Trend_Flow_Pro__MarkitTick_613c.txt` | Smart Trend Flow Pro [MarkitTick] | other/uncategorized | partial_manual | visualization / manual port |
| 70 | `Support_Resistance_Interactiv_01cf.txt` | Support Resistance Interactive | other/uncategorized | partial_manual | visualization / manual port |
| 71 | `Support_and_Resistance_Signals__bc86.txt` | Support and Resistance Signals MTF  | zone/smc | partial_manual | visualization / manual port |
| 72 | `Swing_HighsLows___Candle_Patterns__143a.txt` | Swing Highs/Lows & Candle Patterns  | other/uncategorized | partial_manual | visualization / manual port |
| 73 | `TREND_007c.txt` | CM_SlingShotSystem | other/uncategorized | partial_manual | visualization / manual port |
| 74 | `Trendlines_with_Breaks_960f.txt` | Trendlines with Breaks [LuxAlgo] | other/uncategorized | none_display_only | visualization / manual port |
| 75 | `UP_TEND_949b.txt` | CM_Ultimate_MA_MTF_V2 | other/uncategorized | none_display_only | visualization / manual port |
| 76 | `WIN_LOS_fc44.txt` | Monte Carlo CT [SS] | zone/order_block | partial_manual | visualization / manual port |
| 77 | `atomatic_multi_pattern__9980.txt` | [ A L P H A X ] FORGE | pattern/chart_pattern | partial_pattern | visualization / manual port |
| 78 | `auto_pattern_detector_bf37.txt` | Auto Pattern Detector Targets [Mark | pattern/chart_pattern | partial_pattern | visualization / manual port |
| 79 | `cardvel_f64f.txt` | Cardwell Range Analyze [MarkitTick] | other/uncategorized | partial_manual | ریسک lookahead در request.security… |
| 80 | `entrylib_5e01.txt` |  | other/uncategorized | partial_manual | ریسک lookahead در request.security… |
| 81 | `forge_v1.pine` | [ A L P H A X ] FORGE | pattern/chart_pattern | partial_pattern | visualization / manual port |
| 82 | `machin_f3c0.txt` | Machine Learning Smart Money Concep | ml/ml_regression | partial_core_only | visualization / manual port |
| 83 | `mirage_8451.txt` | Mirage Liquidity Sweep Pro [WillyAl | zone/smc | partial_manual | visualization / manual port |
| 84 | `multi_divergence_3058.txt` | Multi-Divergence Strategy | GainzAl | zone/order_block | partial_manual | visualization / manual port |
| 85 | `qt_cx_7542.txt` | cd_new_QT_Cx | zone/fvg_ob | partial_manual | visualization / manual port |
| 86 | `quadapt_ml_trader.pine` | [Quadapt] Machine Learning Trader | zone/order_block | partial_zone | visualization / manual port |
| 87 | `quadpad_9f11.txt` | [Quadapt] Machine Learning Trader | zone/order_block | partial_zone | visualization / manual port |
| 88 | `smart_0f3d.txt` |  | zone/smc | partial_manual | visualization / manual port |
| 89 | `smart_ichimoko_d12e.txt` | Smart Ichimoku | GainzAlgo | zone/order_block | partial_manual | visualization / manual port |
| 90 | `smart_mony_fibo_67b7.txt` | Smart Money Fibonacci OTE Engine [C | zone/fibonacci | partial_zone | visualization / manual port |
| 91 | `strong_reversal_02f0.txt` | Strong Reversal Signals | zone/smc | partial_manual | visualization / manual port |
| 92 | `whale_liquidy_zone_181a.txt` | Whale Liquidity and Absorption Prof | zone/smc | partial_manual | ریسک lookahead در request.security… |


_آخرین به‌روزرسانی استاتیک: 2026-07-11 17:33 UTC_

---

## #33 CM SlingShot

**فایل:** `TREND_007c.txt` | **کلید:** `slingshot`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **34.9%** | میانگین PF: **0.427**
- بهترین: BEATUSDT 1h PF=1.538 WR=62.5%
- ضعیف‌ترین: XAUUSD 1h PF=0.027

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 32 | 62.5 | 1.538 |
| HYPEUSDT | 4h | 5 | 40.0 | 0.785 |
| BEATUSDT | 15m | 59 | 45.76 | 0.769 |
| BTCUSDT | 4h | 4 | 50.0 | 0.653 |
| HYPEUSDT | 1h | 18 | 38.89 | 0.622 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #34 Smart Ichimoku ML

**فایل:** `smart_ichimoko_d12e.txt` | **کلید:** `ichimoku_ml`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **33.0%** | میانگین PF: **0.869**
- بهترین: HYPEUSDT 1h PF=4.343 WR=64.29%
- ضعیف‌ترین: EURUSD 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 14 | 64.29 | 4.343 |
| XAUUSD | 1h | 9 | 33.33 | 2.195 |
| BEATUSDT | 15m | 79 | 50.63 | 1.155 |
| BEATUSDT | 4h | 4 | 50.0 | 0.923 |
| BEATUSDT | 1h | 14 | 50.0 | 0.9 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #35 Liquidity Shift Zeiierman

**فایل:** `Liquidity_Shift_Detection_eaf8.txt` | **کلید:** `liquidity_shift`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **46.7%** | میانگین PF: **2.667**
- بهترین: BEATUSDT 4h PF=15.603 WR=50.0%
- ضعیف‌ترین: EURUSD 4h PF=0.45

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 4h | 8 | 50.0 | 15.603 |
| XAUUSD | 4h | 4 | 75.0 | 4.367 |
| BTCUSDT | 1h | 25 | 60.0 | 2.651 |
| EURUSD | 1h | 18 | 61.11 | 2.335 |
| XAUUSD | 15m | 59 | 57.63 | 2.178 |

### نگه داریم / حذف / بهبود
- **نگه** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #36 CM Ultimate MA MTF

**فایل:** `CM_Ultimate_MA_MTF_202b.txt` | **کلید:** `cm_ma_mtf`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **38.5%** | میانگین PF: **0.866**
- بهترین: BEATUSDT 4h PF=2.769 WR=75.0%
- ضعیف‌ترین: XAUUSD 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 4h | 4 | 75.0 | 2.769 |
| BTCUSDT | 4h | 7 | 57.14 | 2.421 |
| BTCUSDT | 1h | 14 | 35.71 | 1.487 |
| HYPEUSDT | 4h | 6 | 50.0 | 1.473 |
| BEATUSDT | 15m | 61 | 55.74 | 1.456 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #37 FxPipFinder SCOB

**فایل:** `FxPipFinder_Engagement_Zone_41e2.txt` | **کلید:** `fxpip_scob`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **31.6%** | میانگین PF: **0.45**
- بهترین: HYPEUSDT 1h PF=1.217 WR=43.9%
- ضعیف‌ترین: EURUSD 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 41 | 43.9 | 1.217 |
| BEATUSDT | 1h | 46 | 54.35 | 1.114 |
| BEATUSDT | 15m | 138 | 49.28 | 1.005 |
| BTCUSDT | 4h | 6 | 33.33 | 0.64 |
| HYPEUSDT | 15m | 65 | 33.85 | 0.58 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #38 Buyside/Sellside Liquidity

**فایل:** `Buyside___Sellside_Liquidity_631a.txt` | **کلید:** `buyside_liquidity`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **39.2%** | میانگین PF: **0.899**
- بهترین: XAUUSD 1h PF=1.551 WR=50.0%
- ضعیف‌ترین: EURUSD 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 1h | 30 | 50.0 | 1.551 |
| BEATUSDT | 1h | 45 | 55.56 | 1.538 |
| XAUUSD | 4h | 4 | 50.0 | 1.205 |
| HYPEUSDT | 1h | 56 | 44.64 | 1.143 |
| EURUSD | 15m | 134 | 40.3 | 1.118 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #39 SR Signals MTF

**فایل:** `Support_and_Resistance_Signals__bc86.txt` | **کلید:** `sr_signals_mtf`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **42.9%** | میانگین PF: **1.108**
- بهترین: HYPEUSDT 4h PF=1.985 WR=46.03%
- ضعیف‌ترین: BTCUSDT 4h PF=0.567

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 4h | 63 | 46.03 | 1.985 |
| BTCUSDT | 1h | 154 | 53.25 | 1.512 |
| HYPEUSDT | 1h | 186 | 53.23 | 1.426 |
| EURUSD | 1h | 71 | 40.85 | 1.261 |
| EURUSD | 15m | 95 | 41.05 | 1.172 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #40 Divergence Many Indicators

**فایل:** `Divergence_for_Many_Indicators_2408.txt` | **کلید:** `divergence`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **50.9%** | میانگین PF: **0.646**
- بهترین: BTCUSDT 15m PF=1.094 WR=66.67%
- ضعیف‌ترین: EURUSD 15m PF=0.108

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 15m | 9 | 66.67 | 1.094 |
| HYPEUSDT | 1h | 9 | 55.56 | 1.053 |
| HYPEUSDT | 15m | 15 | 60.0 | 0.97 |
| BEATUSDT | 4h | 3 | 33.33 | 0.889 |
| BTCUSDT | 1h | 5 | 80.0 | 0.853 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #41 OrderFlow Absorption

**فایل:** `Order-Flow_Detection_d054.txt` | **کلید:** `orderflow_print`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **32.6%** | میانگین PF: **0.672**
- بهترین: HYPEUSDT 1h PF=1.371 WR=46.67%
- ضعیف‌ترین: BTCUSDT 4h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 45 | 46.67 | 1.371 |
| XAUUSD | 4h | 10 | 30.0 | 1.226 |
| HYPEUSDT | 15m | 52 | 36.54 | 1.027 |
| BEATUSDT | 1h | 57 | 47.37 | 1.004 |
| BTCUSDT | 1h | 48 | 41.67 | 0.796 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #42 Fair Value Gap LuxAlgo

**فایل:** `Fair_Value_Gap_f587.txt` | **کلید:** `fair_value_gap`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **45.8%** | میانگین PF: **1.024**
- بهترین: BTCUSDT 4h PF=1.782 WR=52.38%
- ضعیف‌ترین: HYPEUSDT 15m PF=0.793

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 4h | 21 | 52.38 | 1.782 |
| BEATUSDT | 1h | 153 | 50.98 | 1.194 |
| XAUUSD | 15m | 261 | 47.51 | 1.089 |
| XAUUSD | 1h | 71 | 46.48 | 1.084 |
| BEATUSDT | 15m | 867 | 48.33 | 1.075 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #43 Smart Money Fib OTE

**فایل:** `smart_mony_fibo_67b7.txt` | **کلید:** `fib_ote`

### وضعیت
- نمونه کافی برای بک‌تست نداشت (کمتر از ۳ معامله در اکثر ترکیب‌ها)
- تحلیل استاتیک در `results/analyses/`


---

## #44 Mirage LSP

**فایل:** `mirage_8451.txt` | **کلید:** `mirage_lsp`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **50.3%** | میانگین PF: **1.04**
- بهترین: XAUUSD 4h PF=2.573 WR=75.0%
- ضعیف‌ترین: BEATUSDT 4h PF=0.25

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 4h | 4 | 75.0 | 2.573 |
| EURUSD | 4h | 3 | 66.67 | 2.0 |
| XAUUSD | 15m | 59 | 59.32 | 1.472 |
| EURUSD | 15m | 51 | 60.78 | 1.415 |
| HYPEUSDT | 1h | 26 | 57.69 | 1.324 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #45 TrendMaster Pro 2.3

**فایل:** `4_7c06.txt` | **کلید:** `trendmaster`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **33.3%** | میانگین PF: **0.281**
- بهترین: BEATUSDT 15m PF=0.462 WR=33.33%
- ضعیف‌ترین: XAUUSD 15m PF=0.1

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 15m | 3 | 33.33 | 0.462 |
| XAUUSD | 15m | 3 | 33.33 | 0.1 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #46 PMax Explorer

**فایل:** `3_2c7c.txt` | **کلید:** `pmax`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **39.3%** | میانگین PF: **0.664**
- بهترین: BTCUSDT 1h PF=1.854 WR=66.67%
- ضعیف‌ترین: XAUUSD 1h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BTCUSDT | 1h | 6 | 66.67 | 1.854 |
| BEATUSDT | 1h | 6 | 66.67 | 1.846 |
| BEATUSDT | 15m | 51 | 56.86 | 1.313 |
| HYPEUSDT | 15m | 18 | 38.89 | 0.618 |
| BTCUSDT | 15m | 16 | 25.0 | 0.472 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #47 Volume-Trend OB Retest

**فایل:** `volon_trend_order_block_93f7.txt` | **کلید:** `volume_ob_retest`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **40.6%** | میانگین PF: **1.292**
- بهترین: HYPEUSDT 1h PF=2.658 WR=63.64%
- ضعیف‌ترین: EURUSD 1h PF=0.0

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 1h | 11 | 63.64 | 2.658 |
| XAUUSD | 1h | 3 | 66.67 | 2.547 |
| EURUSD | 15m | 30 | 46.67 | 1.818 |
| BEATUSDT | 15m | 17 | 41.18 | 1.688 |
| XAUUSD | 15m | 15 | 40.0 | 0.996 |

### نگه داریم / حذف / بهبود
- **نگه** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #48 Dynamic Trend Bands

**فایل:** `dynamic_trend_125b.txt` | **کلید:** `dynamic_trend`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **35.9%** | میانگین PF: **0.489**
- بهترین: BEATUSDT 15m PF=1.085 WR=53.76%
- ضعیف‌ترین: XAUUSD 1h PF=0.053

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 15m | 173 | 53.76 | 1.085 |
| BEATUSDT | 1h | 80 | 53.75 | 1.073 |
| HYPEUSDT | 1h | 14 | 42.86 | 0.781 |
| HYPEUSDT | 15m | 17 | 23.53 | 0.593 |
| BTCUSDT | 1h | 9 | 22.22 | 0.502 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #49 Quantum Imbalance Trap

**فایل:** `QUANTOM_4e3d.txt` | **کلید:** `quantum_imbalance`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **23.8%** | میانگین PF: **0.896**
- بهترین: XAUUSD 15m PF=1.388 WR=27.46%
- ضعیف‌ترین: HYPEUSDT 4h PF=0.375

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 15m | 142 | 27.46 | 1.388 |
| XAUUSD | 1h | 40 | 27.5 | 1.387 |
| BEATUSDT | 1h | 50 | 26.0 | 1.156 |
| BTCUSDT | 1h | 52 | 23.08 | 0.938 |
| HYPEUSDT | 15m | 100 | 24.0 | 0.902 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #50 Multi-Divergence GainzAlgo

**فایل:** `multi_divergence_40f7.txt` | **کلید:** `multi_div`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **45.7%** | میانگین PF: **1.166**
- بهترین: HYPEUSDT 4h PF=2.031 WR=50.0%
- ضعیف‌ترین: EURUSD 4h PF=0.623

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| HYPEUSDT | 4h | 32 | 50.0 | 2.031 |
| XAUUSD | 4h | 44 | 59.09 | 1.87 |
| EURUSD | 15m | 240 | 45.0 | 1.488 |
| BTCUSDT | 1h | 228 | 47.37 | 1.242 |
| EURUSD | 1h | 80 | 42.5 | 1.138 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #51 KNN Pivot ML

**فایل:** `MACHIN_6545.txt` | **کلید:** `knn_pivot`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **42.9%** | میانگین PF: **0.484**
- بهترین: BEATUSDT 1h PF=1.072 WR=56.67%
- ضعیف‌ترین: EURUSD 15m PF=0.092

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| BEATUSDT | 1h | 30 | 56.67 | 1.072 |
| BEATUSDT | 15m | 22 | 40.91 | 0.62 |
| XAUUSD | 15m | 7 | 42.86 | 0.15 |
| EURUSD | 15m | 29 | 31.03 | 0.092 |

### نگه داریم / حذف / بهبود
- **ضعیف** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #52 HV Pivot S/R

**فایل:** `high_volom_pivoty_suport_809e.txt` | **کلید:** `hv_pivot_sr`

### خلاصه بک‌تست (~۳۱ روز)
- میانگین WR: **40.3%** | میانگین PF: **0.993**
- بهترین: XAUUSD 1h PF=1.512 WR=49.09%
- ضعیف‌ترین: BTCUSDT 4h PF=0.541

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 1h | 55 | 49.09 | 1.512 |
| BEATUSDT | 4h | 7 | 57.14 | 1.385 |
| BTCUSDT | 1h | 73 | 47.95 | 1.34 |
| XAUUSD | 4h | 5 | 40.0 | 1.24 |
| HYPEUSDT | 1h | 66 | 45.45 | 1.073 |

### نگه داریم / حذف / بهبود
- **فیلتر/ترکیب** — بر اساس PF میانگین روی نمونه‌های ≥۳ معامله


---

## #53 Farhad Combo Strategy

**فایل:** `farhad_strategy.py` + `indicators/Farhad_Combo_Strategy.pine` | **کلید:** `farhad_loose` / `farhad_standard` / `farhad_strict`

### معماری

```
ورود:     Bj Bot EMA21/50 cross
فیلتر 1:  UT Bot — close بالای/زیر TSL
فیلتر 2:  AlphaTrend — مومنتوم هم‌جهت
فیلتر 3:  Zero-Lag trend (فقط strict)
فیلتر 4:  Zone confluence — IFVG + Supply/Demand + RSI Advanced + Liquidity Shift
SL/TP:    Bj Bot structural (swing ± ATR × RiskM, R:R=1)
```

### مقایسه بک‌تست (~۳۱ روز) — Bj structural exit

| حالت | میانگین PF | PF روی 1h/4h | معاملات | بهترین |
|------|-----------|--------------|---------|--------|
| Bj Bot (baseline) | **1.196** | **1.547** | 155 | BEAT 4h PF=2.1 |
| farhad_loose | 0.993 | 1.282 | 141 | BTC 4h PF=1.68 |
| farhad_standard | 1.012 | 1.272 | 71 | **XAU 15m PF=2.56** |
| farhad_strict | 0.677 | 0.595 | 10 | نمونه خیلی کم |

### نتایج برجسته (standard)

| نماد | TF | معاملات | WR% | PF |
|------|-----|---------|-----|-----|
| XAUUSD | 15m | 10 | 70.0 | **2.559** |
| XAUUSD | 1h | 3 | 66.7 | 1.901 |
| HYPEUSDT | 1h | 3 | 66.7 | 1.770 |
| BTCUSDT | 1h | 3 | 100.0 | — |

### نگه داریم / حذف / بهبود
- **نگه:** `farhad_standard` — کیفیت بالا، معاملات کمتر (۷۱ vs ۱۵۵)
- **TF پیشنهادی:** 1h و 4h
- **XAUUSD:** بهترین نماد برای standard mode
- **بهبود:** loosen zone filter روی کریپتو، HTF alignment
- **Pine:** `backtest/indicators/Farhad_Combo_Strategy.pine` آماده TradingView

