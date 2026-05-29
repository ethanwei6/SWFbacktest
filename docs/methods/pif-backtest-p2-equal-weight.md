# PIF Backtest P2 Equal Weight

## Strategy

`P2` mirrors the full disclosed `PIF` common-equity sleeve.

At each `PIF` public filing date:

- take all disclosed common-equity holdings
- exclude unresolved mappings or missing trade-date prices
- rebalance into an equal-weight basket
- hold until the next `PIF` rebalance close

## Why This Version

This is the cleanest baseline version of `P2` because:

- it is simple to audit
- it is less dominated by mega-positions than disclosed-value weighting
- it makes comparison against `P1` more interpretable

## Inputs

- [`data/processed/pif/pif_backtest_signal_panel.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_panel.csv)
- [`data/processed/pif/pif_trade_calendar.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar.csv)
- [`data/processed/pif/pif_twelvedata_security_map.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_security_map.csv)
- [`data/processed/pif/pif_twelvedata_daily_prices.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_daily_prices.csv)

## Inclusion Rules

Include only rows where:

- `signal_type = full_sleeve_holding`
- `common_equity_baseline_flag = 1`
- mapping status is `approved` or `auto_approved`
- a valid next-trade-date close exists

Exclude:

- unresolved mappings
- options
- warrant-like rows
- holdings missing a trade-date close

## Rebalance Logic

At each rebalance close:

1. mark the old basket to market through that close
2. liquidate the old basket at that close
3. equally weight all eligible disclosed holdings for that filing date
4. buy the new basket at that same close

## Output Design

The output pack is intentionally detailed so later visuals can show:

- what the public filing looked like
- which names were eligible
- which names were excluded and why
- how the basket changed across filings
- what daily PnL and contribution came from each name

## Outputs

- [`data/processed/pif/backtests/p2_equal_weight/p2ew_signal_eligibility.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_signal_eligibility.csv)
- [`data/processed/pif/backtests/p2_equal_weight/p2ew_rebalance_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_rebalance_events.csv)
- [`data/processed/pif/backtests/p2_equal_weight/p2ew_orders.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_orders.csv)
- [`data/processed/pif/backtests/p2_equal_weight/p2ew_holdings_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_holdings_daily.csv)
- [`data/processed/pif/backtests/p2_equal_weight/p2ew_portfolio_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_portfolio_daily.csv)
- [`data/processed/pif/backtests/p2_equal_weight/p2ew_summary.json`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p2_equal_weight/p2ew_summary.json)
