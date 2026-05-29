# Backtest Plan

## Objective

Proceed to the first quantitative testing phase using the datasets that are sufficiently structured and observable:

- `PIF` `13F`
- `NBIM` public equity holdings

`GIC` remains outside the initial backtest panel because available public disclosures are too sparse and uneven to support a comparable holdings history.

## Backtest Streams

### Stream 1: `PIF` Lagged Mirroring

Best use case:

- quarterly, security-level, filing-based public disclosures

Core idea:

- simulate a portfolio formed from `PIF` `13F` disclosures only after the filing becomes public

Candidate signals:

- new positions
- continued holdings
- likely accumulations
- full exits
- likely reductions

Suggested first tests:

1. `new-positions portfolio`
2. `hold-all-disclosed positions`
3. `top-N by market value`
4. `exclude options` version and `include options` diagnostic version

Timing rule:

- rebalance on `public_date`, not `as_of_date`

### Stream 2: `NBIM` Slow-Moving Sector and Ownership Signals

Best use case:

- broad but slower disclosure
- better for structural concentration and sector rotation than for high-frequency mirroring

Core idea:

- test whether sectors and industries with repeated `NBIM` observable accumulation signals outperform after public disclosure

Candidate signals:

- sector weight increases
- repeated `likely_accumulation` events by industry
- concentration changes
- entry and exit counts by industry

Suggested first tests:

1. `industry tilt from net accumulation counts`
2. `industry tilt from portfolio-weight increases`
3. `avoidance screen` for sectors with repeated reductions

Timing rule:

- use the first public availability date of each snapshot, not the economic date

## Data Needed Before Running

### `PIF`

- final `public_date` field validated from filing dates
- choice of whether to exclude option rows from the baseline test
- benchmark selection for the US sleeve

### `NBIM`

- publication-date mapping for each snapshot
- sector or industry taxonomy frozen for tilt construction
- benchmark selection for broad market and sector-relative tests

## Immediate Next Build Tasks

1. create a `PIF` backtest-ready event panel keyed by `public_date`
2. create an `NBIM` sector-signal panel keyed by first public date
3. define benchmark series and holding-window rules
4. choose evaluation metrics

## Recommended Default Choices

- `PIF` baseline: common-equity rows only, equal-weight new-positions portfolio, rebalance each filing date
- `PIF` robustness checks: value-weight, hold-until-next-filing, hold for fixed windows
- `NBIM` baseline: industry-level tilt, not single-name mirroring
- compare against simple public benchmarks before adding more complex risk adjustment

## Why `GIC` Is Not In The First Backtest

- no comparable recurring holdings panel
- sparse threshold-event visibility
- severe selection bias toward only reportable large stakes
- high risk of false precision if pooled beside `PIF` and `NBIM`

`GIC` should still appear in the memo as evidence that disclosure asymmetry is itself part of the sovereign-wealth-fund alpha question.
