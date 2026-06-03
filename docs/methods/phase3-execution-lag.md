# Phase 3 A1: Execution-Lag Sensitivity

This step tests whether the strongest surviving strategies remain credible after small execution delays.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Variants

- `T+1`: first tradable close after the legal source signal
- `T+3`: third tradable close after the legal source signal
- `T+5`: fifth tradable close after the legal source signal

## Source-Specific Handling

### `P5`

- source anchor is `signal_date`
- delayed trade dates are recomputed from the validated `PIF` adjusted daily calendar
- the strategy logic itself is unchanged: sells happen first, buys are funded only from available cash, and residual proceeds remain in cash

### `N4` and `N6`

- source anchor is `NBIM public_date`
- delayed trade dates are recomputed from the validated `NBIM` adjusted daily calendar
- the target sleeves are rebuilt from the original disclosed signals, then traded at the delayed close

### `S1`

- the combined state table already encodes the legal baseline execution close as `event_date`
- `T+3` and `T+5` are therefore implemented as `+2` and `+4` additional shared trading days on the combined calendar
- if multiple delayed states land on the same execution date, the latest cumulative state is retained because all earlier information is also known by that close

## Validation Rules

- baseline `T+1` must reproduce the previously validated strategy NAV exactly within floating-point tolerance
- every delayed execution date must exist in the relevant price calendar
- benchmark comparisons are rebased to each variant's actual live start date
- no new price sources are introduced; only the already-audited stored daily files are used

## Outputs

- `data/processed/robustness/execution_lag_summary.csv`
- `data/processed/robustness/execution_lag_daily.csv`
- `data/processed/robustness/execution_lag_audit.csv`
