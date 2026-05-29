# PIF Backtest Signal Panel Method

## Purpose

Create a backtest-ready `PIF` signal panel keyed to the first public date of the disclosure.

This panel is the bridge between:

- disclosure datasets
- strategy logic
- later price attachment

It should be complete enough to:

- audit what signal was known on each public date
- distinguish strategy families
- preserve staleness information
- avoid mixing same-day multi-filing bundles into a single ambiguous record

## Why This Step Comes Before Prices

Before attaching any market data, we need to know exactly:

- what the signal date was
- which securities were in the signal set
- whether the signal was an entry, exit, accumulation, reduction, or disclosed holding
- whether the signal came from a stale report that happened to be published much later

If the signal calendar is wrong, the backtest will be wrong even with perfect prices.

## Inputs

- canonical holdings dataset
- transition dataset
- filing index

## Output

- [`data/processed/pif/pif_backtest_signal_panel.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_panel.csv)
- [`data/processed/pif/pif_backtest_signal_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_backtest_signal_audit.csv)

## Signal Types

### Holdings-Based

- `full_sleeve_holding`

Used for:

- `P2` full disclosed-sleeve mirror

### Transition-Based

- `entry_observed`
- `exit_observed`
- `likely_accumulation`
- `likely_reduction`
- `continued_holding`

Used for:

- `P1` new-positions mirror
- `P3` accumulation overlay
- `P4` exit avoidance

## Core Fields

- `signal_date`
- `report_period`
- `staleness_days`
- `security_key`
- `issuer_name`
- `cusip`
- `put_call`
- `is_option_row`
- `common_equity_baseline_flag`
- `signal_type`
- `strategy_ids`
- `recommended_action`
- `market_value_usd`
- `portfolio_weight_in_filing`
- `prev_shares`
- `curr_shares`
- `delta_shares`
- `public_batch_size`
- `same_day_multi_period_flag`
- `next_public_date`

## Same-Day Multi-Filing Bundles

Some `PIF` filings were published on the same public date for different report periods.

That means the panel must preserve:

- the actual `report_period`
- the actual `signal_date`
- whether multiple report periods were published on the same day

This should not be silently collapsed.

## Current Trade-Date Convention

This panel should stop at:

- `signal_date = public_date`

It should not hardcode:

- final execution date
- fill price timing

Those come in the next step after the signal calendar is audited.

## Validation Checks

The builder should verify:

- one canonical filing per `report_period`
- non-missing `signal_date`
- monotonic period ordering
- consistent holdings weights within each filing
- correct staleness calculation
- same-day multi-period bundles flagged correctly
