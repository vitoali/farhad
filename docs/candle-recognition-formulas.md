# Candle Recognition Library — Formulas

File: `pine/candle_recognition_lib.pine`  
Publish as: **CandleRecognitionLib**

Based on Steve Nison + common TA-Lib / CandleKit / TradingView implementations.  
No extra proprietary formula beyond industry-standard ratios.

## Core anatomy (per bar)

```
body         = |close - open|
range        = high - low
upperShadow  = high - max(open, close)
lowerShadow  = min(open, close) - low
```

## Size classes (relative to range)

| Class | Default rule | Typical use |
|-------|--------------|-------------|
| Doji | body ≤ 10% × range | indecision |
| Small body | body ≤ 30% × range | star, harami, hammer |
| Long body | body ≥ 60% × range | marubozu, belt hold |

## Hammer / Shooting Star (2× shadow rule)

```
lowerWick ≥ shadowRatio × body     (default shadowRatio = 2.0)
oppositeWick ≤ maxOppWickRatio × body   (default 1.0)
body in upper/lower edge of range  (upper/lower shadow ≤ 25% × range)
```

## Harami

```
2nd body inside 1st body range
2nd body ≤ 60% × 1st body   (haramiMaxBodyRatio)
```

## Engulfing

```
2nd real body fully contains 1st real body (shadows excluded)
Opposite colors OR 1st body doji-like (tiny)
```

## Dark Cloud / Piercing

```
Dark Cloud:  open > prior high, close < midpoint of prior white body
Piercing:    open < prior low,  close > midpoint of prior black body
```

## Trend context

```
Hammer / Inverted Hammer  → requires downtrend (ta.falling close, N bars)
Hanging Man / Shooting Star → requires uptrend (ta.rising close, N bars)
```

## Strategy import

```pine
import YOUR_USER/CandleRecognitionLib/1 as cr

s = cr.defaultSettings()

bool bullReversal = cr.isPatternActive(14, s) and cr.patternKind(14) == 0
bool contUp       = cr.isPatternActive(51, s) and cr.patternKind(51) == 1
```

## References

- Steve Nison — *Japanese Candlestick Charting Techniques*
- TA-Lib / CandleKit body_ratio conventions
- TradingView EVLabs candlestick scanner (wick 2×, doji 10%, harami 60%)
