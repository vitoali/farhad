# Khakster Final Strategy — Structure Mode

استراتژی نهایی: **ساختار HTF + Smart Money + FTC/RTP + الگو در zone**

فایل: `pine/khakster_final_strategy.pine` — **Khakster Final Structure**

راهنمای کامل TradingView: [khakster-tradingview-final.md](./khakster-tradingview-final.md)

## منطق

1. سطوح **Reverse + FTC credible** روی HTF (Mn/W/D/H4/H1)
2. **SM ≥ 2/3** روی zone همان TF (با `request.security`)
3. فیلتر **سشن** (L/NY برای FX، NY برای نزدک)
4. تریگر روی TF پایین: FTC/RTP یا ۶۴ الگوی کندل **داخل zone**
5. `barstate.isconfirmed` + `lookahead_off`

## تنظیمات پیش‌فرض

| پارامتر | مقدار |
|---------|--------|
| SM min | 2/3 |
| Min score | 40 (BTC: 50) |
| Pivot | Reverse فقط |
| Session | FX: L/NY، Index: NY |
| MTF pat+SM | **حذف** |

## نصب

Publish به ترتیب: TrexAtrLib → MSE → EntryLib → SmartMoneyLib → CandleRecognitionLib → Strategy
