# PIF Backtest Analysis Report

This layer sits on top of the completed `P1` through `P4` backtest engines and does two jobs:

1. sanity-check that the realized strategy results are mechanically coherent
2. turn the backtests into standard charts, tables, and narrative findings before building an interactive app

## Inputs

- `data/processed/pif/backtests/p1/*`
- `data/processed/pif/backtests/p2_equal_weight/*`
- `data/processed/pif/backtests/p3_accumulation_tilt/*`
- `data/processed/pif/backtests/p4_exit_avoidance/*`
- `data/processed/pif/pif_twelvedata_daily_prices.csv`

## Main outputs

Structured analysis tables:

- `data/processed/pif/backtests/analysis/strategy_summary.csv`
- `data/processed/pif/backtests/analysis/strategy_sanity_checks.csv`
- `data/processed/pif/backtests/analysis/strategy_top_contributors.csv`
- `data/processed/pif/backtests/analysis/strategy_rebalance_period_returns.csv`
- `data/processed/pif/backtests/analysis/p1_entry_forward_returns.csv`
- `data/processed/pif/backtests/analysis/p3_bucket_forward_returns.csv`
- `data/processed/pif/backtests/analysis/p4_avoidance_forward_returns.csv`

Visual/report layer:

- `outputs/pif/backtests/charts/*`
- `outputs/pif/backtests/reports/pif_backtest_analysis.html`
- `outputs/pif/backtests/reports/pif_backtest_analysis.md`

## Sanity checks

For each strategy, the analysis script verifies:

- daily portfolio arithmetic: `nav_start + pnl_day == nav_pre_rebalance`, and daily return matches `nav_end / nav_start - 1`
- gross exposure range
- holdings weight sums by day
- entry-day PnL leakage
- daily position-count consistency between holdings and portfolio tables
- non-exact price row counts

These checks are intended to catch implementation issues before we interpret relative performance.

## Interpretation layer

The script also creates a first-pass explanation layer for the strategy spread:

- `P1`: forward returns of newly disclosed entry cohorts
- `P3`: forward returns of `accumulation_like` versus `neutral` names
- `P4`: forward returns of names avoided by the `likely_reduction` filter versus names retained in the sleeve

This makes the report useful not just as a performance dashboard, but as an explanation of why a strategy worked or failed.
