# farhad

TradingView Pine Script indicator for detecting common candlestick patterns.

## File

- `candlestick-pattern-detector.pine`

## How to use

1. Open TradingView.
2. Open Pine Editor.
3. Copy the full contents of `candlestick-pattern-detector.pine`.
4. Save and add it to the chart.

## Current coverage

The indicator currently detects common Japanese candlestick patterns, grouped as:

- Bullish patterns: Hammer, Inverted Hammer, Bullish Belt Hold, Bullish Marubozu,
  Bullish Engulfing, Bullish Harami, Bullish Harami Cross, Piercing Line,
  Tweezer Bottom, Matching Low, Homing Pigeon, Bullish Counterattack,
  Bullish Kicking, Morning Star, Morning Doji Star, Bullish Abandoned Baby,
  Three White Soldiers, Three Inside Up, Three Outside Up, Stick Sandwich,
  Unique Three River Bottom, Ladder Bottom.
- Bearish patterns: Hanging Man, Shooting Star, Bearish Belt Hold,
  Bearish Marubozu, Bearish Engulfing, Bearish Harami, Bearish Harami Cross,
  Dark Cloud Cover, Tweezer Top, Bearish Counterattack, Bearish Kicking,
  Evening Star, Evening Doji Star, Bearish Abandoned Baby, Three Black Crows,
  Three Inside Down, Three Outside Down, Upside Gap Two Crows, Advance Block,
  Stalled Pattern, Deliberation, Concealing Baby Swallow.
- Neutral or continuation patterns: Doji, Long-Legged Doji, Dragonfly Doji,
  Gravestone Doji, Spinning Top, Separating Lines, On-Neck Line, In-Neck Line,
  Thrusting Line, Rising Three Methods, Falling Three Methods, Mat Hold,
  Tasuki Gaps, Side-by-Side White Lines.

## Notes

- The book file was not present in this repository, so the current definitions
  use standard candlestick-pattern rules and configurable thresholds.
- When the book/source file is added, the pattern formulas can be adjusted to
  match its exact definitions.
- Alerts are included for bullish, bearish, neutral/continuation, and any
  candlestick pattern.
