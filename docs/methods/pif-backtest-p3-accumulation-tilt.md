# PIF Backtest P3 Accumulation Tilt

## Strategy

`P3` starts from the disclosed `PIF` common-equity sleeve and overlays a simple transition-based tilt.

For each filing-date basket:

- `entry_observed` and `likely_accumulation` get a score of `2`
- `continued_holding` gets a score of `1`
- `likely_reduction` gets a score of `0` and is excluded from the investable basket

The portfolio then normalizes the positive scores into target weights and rebalances at the next tradable NYSE close.

## Why This Version

This is an intentionally simple first accumulation overlay:

- easy to audit
- easy to explain in a visualization
- directly tied to the transition dataset we already built

## Inputs

- [`data/processed/pif/pif_backtest_signal_panel.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_panel.csv)
- [`data/processed/pif/pif_trade_calendar.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar.csv)
- [`data/processed/pif/pif_twelvedata_security_map.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_security_map.csv)
- [`data/processed/pif/pif_twelvedata_daily_prices.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_daily_prices.csv)

## Transition Buckets

The current disclosed holding is joined to its same-period transition event.

Buckets:

- `accumulation_like`
  - `entry_observed`
  - `likely_accumulation`
- `neutral`
  - `continued_holding`
- `reduction_like`
  - `likely_reduction`

## Weight Model

Raw score by bucket:

- `accumulation_like = 2.0`
- `neutral = 1.0`
- `reduction_like = 0.0`

Only positive-score names are included in the investable basket.

## Outputs

- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_signal_eligibility.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_signal_eligibility.csv)
- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_rebalance_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_rebalance_events.csv)
- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_orders.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_orders.csv)
- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_holdings_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_holdings_daily.csv)
- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_portfolio_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_portfolio_daily.csv)
- [`data/processed/pif/backtests/p3_accumulation_tilt/p3at_summary.json`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p3_accumulation_tilt/p3at_summary.json)
