# HTF Liquidity FVG PA Strategy v1

استراتژی کامل Pine Script بر اساس چت «دوره ۹۶ سعید خاکستر» + فیلترهای HTF / Liquidity / FVG / Supply-Demand.

## فایل

`pine/htf_liquidity_fvg_pa_strategy.pine`

## نصب در TradingView

1. Pine Editor → New → Blank strategy (یا هر strategy)
2. کل محتوای فایل را Paste کن
3. **Add to chart**
4. چارت را روی **5m** یا **15m** بگذار (تایم تریگر)
5. Strategy Tester را باز کن

## منطق ورود

```
HTF Trend (EMA50/200)
  → Liquidity Sweep و/یا FVG و/یا Supply-Demand
  → Pin Bar یا Engulfing
  → BOS/CHoCH (اختیاری)
  → Score ≥ 70
  → SL = 1.5 × ATR(55) | TP1 = 2R | TP2 = 3R
```

## امتیازدهی (با Volume)

| شرط | امتیاز |
|---|---:|
| HTF Trend | 25 |
| Liquidity Sweep | 20 |
| FVG | 15 |
| Supply/Demand | 15 |
| Pin / Engulf | 10 |
| Volume | 10 |
| ATR زنده | 5 |
| **جمع** | **100** |

اگر Volume خاموش باشد، امتیازها دوباره نرمال می‌شوند تا سقف ۱۰۰ بماند.

## HTF Mode

- **Single HTF**: فقط تایم انتخابی
- **2 of 3**: حداقل ۲ تایم از تایم‌های تیک‌خورده (1H / 4H / Daily)
- **All HTF**: همه تایم‌های تیک‌خورده هم‌جهت

## پیشنهاد بک‌تست

- BTCUSDT / ETHUSDT
- 5m و 15m جداگانه
- سه حالت HTF را با هم مقایسه کن
- Volume On/Off را جدا تست کن
