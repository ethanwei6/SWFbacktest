# Phase 3 Strategy Statistical Tests

This layer performs formal inference on the validated strategy-versus-benchmark comparison timelines in `data/processed/robustness/benchmark_comparison_daily.csv`.

## Inputs

- `data/processed/robustness/benchmark_comparison_daily.csv`
- `data/processed/robustness/benchmark_comparison_summary.csv`

## Method

For each validated strategy-benchmark pair:

1. Reconstruct period returns directly from the rebased strategy and benchmark NAV series.
2. Compute arithmetic excess return as `strategy_return - benchmark_return`.
3. Estimate a parametric mean-excess test using a Newey-West standard error on the period excess-return series.
4. Estimate non-parametric confidence intervals for annualized excess return and information ratio using a circular moving-block bootstrap.
5. Estimate an approximate randomization p-value using a block sign-permutation test.

Annualization uses the realized observation frequency implied by the comparison file rather than assuming a fixed daily or monthly cadence.

## Outputs

- `data/processed/inference/strategy_statistical_tests_series.csv`
- `data/processed/inference/strategy_statistical_tests_summary.csv`
- `data/processed/inference/strategy_statistical_tests_audit.csv`
