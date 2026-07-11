"""Backtest risk and cost defaults."""

# Crypto (ارز دیجیتال) — per user: SL 5%
CRYPTO_SL_PCT = 0.05
CRYPTO_TP_PCT = 0.10  # RR 2:1 vs 5% SL (TP 2%/4% scaled from original framework)

# Forex
FOREX_SL_PIPS = 3.0
FOREX_TP_RR = 1.0

# Costs
CRYPTO_FEE_PCT = 0.05
CRYPTO_SLIPPAGE_PCT = 0.05
FOREX_SPREAD_PIPS = 1.0
