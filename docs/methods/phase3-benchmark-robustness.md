# Phase 3 A5: Benchmark Robustness

This layer tests whether the focus-set conclusions depend too heavily on a single benchmark choice.

## Focus set

- `P5` versus `SPY` and `QQQ`
- `N4` versus `VT` and `ACWI`
- `N6` versus `VT` and `ACWI`
- `S1` versus `VT`, `SPY`, and `BLEND_VT_SPY_50`

## Benchmark construction

- `SPY` comes from the validated local PIF benchmark layer.
- `VT` comes from the validated local NBIM benchmark layer.
- `QQQ` and `ACWI` are fetched as adjusted daily series from Twelve Data.
- `BLEND_VT_SPY_50` is a synthetic benchmark formed as a 50/50 blend of rebased `VT` and `SPY` daily NAVs.

## Method

A5 does not re-run the strategies. It uses the validated baseline portfolio timelines and aligns each one with each candidate benchmark using the same carry-forward benchmark logic used in earlier robustness steps. Strategy NAV and benchmark NAV are rebased to `1.0` on the first aligned date, and then benchmark-relative excess returns are recomputed over the matched live window.

## Outputs

- `data/processed/robustness/benchmark_series_daily.csv`
- `data/processed/robustness/benchmark_series_audit.csv`
- `data/processed/robustness/benchmark_comparison_summary.csv`
- `data/processed/robustness/benchmark_comparison_daily.csv`
- `data/processed/robustness/benchmark_comparison_audit.csv`
