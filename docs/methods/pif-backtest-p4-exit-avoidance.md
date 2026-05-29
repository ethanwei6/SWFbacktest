# PIF Backtest P4 Exit Avoidance

## Strategy

`P4` starts from the disclosed `PIF` common-equity sleeve and removes names flagged as `likely_reduction` in the same report period.

This is an avoidance strategy, not a short strategy.

So the portfolio:

- buys the eligible disclosed sleeve
- excludes names with same-period `likely_reduction`
- rebalances at the next tradable NYSE close after disclosure

## Why This Version

This keeps the logic clean:

- no lookahead
- no shorting
- no need to infer exact future exits from `exit_observed`

It simply asks:

- does excluding the names that appear to be getting reduced improve the mirror basket?

## Inputs

- [`data/processed/pif/pif_backtest_signal_panel.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_panel.csv)
- [`data/processed/pif/pif_trade_calendar.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar.csv)
- [`data/processed/pif/pif_twelvedata_security_map.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_security_map.csv)
- [`data/processed/pif/pif_twelvedata_daily_prices.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_daily_prices.csv)

## Eligibility Rules

Start from:

- `signal_type = full_sleeve_holding`
- `common_equity_baseline_flag = 1`

Exclude if:

- mapping is unresolved
- trade-date close is missing
- same-period transition signal is `likely_reduction`

## Weighting

Equal-weight across the remaining eligible names.

## Outputs

- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_signal_eligibility.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_signal_eligibility.csv)
- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_rebalance_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_rebalance_events.csv)
- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_orders.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_orders.csv)
- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_holdings_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_holdings_daily.csv)
- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_portfolio_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_portfolio_daily.csv)
- [`data/processed/pif/backtests/p4_exit_avoidance/p4ea_summary.json`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p4_exit_avoidance/p4ea_summary.json)
