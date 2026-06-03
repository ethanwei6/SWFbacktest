# Phase 3 Turnover-Adjusted Metrics

This layer uses the already validated 10 bps cost-sensitivity timelines to compute turnover-adjusted Sharpe and information metrics for the focus set.

## Inputs

- `data/processed/robustness/cost_sensitivity_daily.csv`
- `data/processed/robustness/cost_sensitivity_summary.csv`

## Method

For each focus-set strategy:

1. Use the `0 bps` series as the baseline performance path.
2. Use the `10 bps` series as the turnover-adjusted path.
3. Reconstruct period strategy and benchmark returns directly from those validated time series.
4. Compute annualized Sharpe ratio from strategy returns and annualized information ratio from benchmark-relative excess returns.
5. Recover implied gross turnover from the cumulative 10 bps trade-cost field.

## Outputs

- `data/processed/inference/turnover_adjusted_metrics.csv`
- `data/processed/inference/turnover_adjusted_metrics_audit.csv`
