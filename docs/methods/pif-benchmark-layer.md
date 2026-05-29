# PIF Benchmark Layer

## Objective

Measure whether the `PIF` copycat strategies generate **benchmark-relative alpha**, not just positive standalone returns.

## Primary benchmark

- Benchmark: `SPY`
- Rationale: the `PIF` 13F sleeve is a US public-equity disclosure set, so `SPY` is the simplest and most defensible passive comparator for the first pass.

## Price basis

- Source: `Twelve Data`
- File: `data/processed/pif/pif_benchmark_daily.csv`
- Adjustment mode: `all`
- Interpretation: split-adjusted benchmark close series, consistent with the split-adjusted strategy mark-to-market layer.

## Alignment rule

Each strategy is compared to a **matched-window SPY buy-and-hold**:

- strategy start date = benchmark start date
- strategy end date = benchmark end date
- benchmark NAV starts at `1.0` on the strategy inception date
- benchmark total return is measured over the exact same live window as the strategy

This avoids overstating or understating relative performance by comparing different market windows.

## Non-trading-day handling

Most strategy dates line up cleanly with `SPY` trading dates. A small number of strategy dates come from OTC holdings that print on weekend calendar dates.

For those dates:

- strategy portfolio row is retained
- benchmark price is carried forward from the most recent prior `SPY` trading date
- benchmark price status is labeled `carry_forward_close`

This is conservative and preferable to dropping the row or interpolating a synthetic benchmark move.

## Output tables

- `data/processed/pif/backtests/analysis/strategy_vs_benchmark_summary.csv`
- `data/processed/pif/backtests/analysis/strategy_vs_benchmark_daily.csv`

## Core benchmark fields

- `benchmark_total_return`
- `benchmark_cagr`
- `annualized_excess_return`
- `information_ratio`
- `excess_total_return`
- `relative_nav_ratio`

## Interpretation

- Positive absolute return is **not** enough to claim alpha.
- A strategy only clears the first benchmark hurdle if `excess_total_return > 0`.
- In this first pass, `P5` is the strongest absolute-return strategy, but the benchmark layer determines whether that strength survives against passive market beta.
