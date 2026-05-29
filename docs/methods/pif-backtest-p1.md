# PIF Backtest P1

## Strategy

`P1` tests the simplest mirrorable `PIF` signal:

- buy common-equity names classified as `entry_observed`
- trade only after the filing becomes public
- execute at the next valid NYSE trading-day close
- hold until the next `PIF` rebalance close

## Why P1 Comes First

This is the cleanest first question:

- when `PIF` discloses a new reportable US position, what happens if we buy it on the first legally tradable close?

It avoids:

- value-weighting complexity
- partial accumulation/reduction judgment
- option interpretation

## Inputs

- [`data/processed/pif/pif_backtest_signal_panel.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_panel.csv)
- [`data/processed/pif/pif_trade_calendar.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar.csv)
- [`data/processed/pif/pif_twelvedata_security_map.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_security_map.csv)
- [`data/processed/pif/pif_twelvedata_daily_prices.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_daily_prices.csv)

## Universe Rules

Include only:

- `signal_type = entry_observed`
- `common_equity_baseline_flag = 1`
- securities with `mapping_status in {approved, auto_approved}`
- securities with a trade-date close in the normalized price panel

Exclude:

- unresolved mappings
- warrant-like rows
- options

## Portfolio Construction

At each `trade_date`:

1. liquidate the previous `P1` basket at that day’s close
2. equally weight all eligible new-entry names disclosed for that trade date
3. buy the new basket at the same close

Important note:

- returns for the rebalance date belong to the positions held coming into that day
- the new basket becomes the end-of-day position set after the close execution

## Pricing Convention

Execution uses:

- `Twelve Data` daily `close`
- `adjust_mode = none`

This is deliberate.

The first objective is accurate execution-date pricing.
Adjusted or total-return variants can be layered in later.

## Shares And Cash

Baseline assumptions:

- initial NAV = `1.0`
- fractional shares allowed
- zero commissions
- zero slippage
- zero borrowing costs
- uninvested cash stays in cash at `0%`

## Daily Output Design

The backtest writes multiple datasets so later visualization work is easy.

### Signal Eligibility

One row per candidate `entry_observed` signal:

- included or excluded
- exclusion reason if excluded
- mapped ticker
- trade-date price availability

### Rebalance Events

One row per rebalance close:

- why the rebalance happened
- how many names were bought
- how many names were sold
- raw and eligible signal counts
- pre- and post-trade NAV

### Orders

One row per executed buy or sell:

- execution date
- execution price
- execution shares
- execution value
- originating `PIF` signal

### Holdings Daily

One row per held name per day:

- close price
- shares
- end-of-day market value
- weight
- daily PnL
- daily return contribution
- entry trade date

### Portfolio Daily

One row per backtest day:

- NAV start
- NAV end
- daily return
- daily PnL
- position count
- whether a rebalance occurred

## Outputs

- [`data/processed/pif/backtests/p1/p1_signal_eligibility.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_signal_eligibility.csv)
- [`data/processed/pif/backtests/p1/p1_rebalance_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_rebalance_events.csv)
- [`data/processed/pif/backtests/p1/p1_orders.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_orders.csv)
- [`data/processed/pif/backtests/p1/p1_holdings_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_holdings_daily.csv)
- [`data/processed/pif/backtests/p1/p1_portfolio_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_portfolio_daily.csv)
- [`data/processed/pif/backtests/p1/p1_summary.json`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/backtests/p1/p1_summary.json)

## Known Gaps

This first version intentionally excludes unresolved mapping cases such as:

- `ACTIVISION BLIZZARD INC`
- `HYZON MOTORS INC`

That is preferable to forcing low-confidence prices into the signal set.
