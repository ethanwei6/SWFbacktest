# Phase 4: Institutional Benchmark Metrics

This layer asks whether the surviving strategies look useful under a more institutional lens, not just a pure market-beating lens.

## Focus set

- `P2` as the strongest absolute-return PIF sleeve.
- `P5` as the cash-aware PIF copy variant.
- `N4` and `N6` as the strongest realistic NBIM sleeves.
- `S1` as the main combined cross-fund overlay.

## Benchmark families

- Market opportunity cost: `SPY` for PIF, `VT` for NBIM and combined strategies.
- Cash hurdle: `BIL`.
- Defensive equity comparator: `USMV` for PIF, `ACWV` for NBIM and combined.

## Metrics

- Total return and CAGR.
- Annualized volatility and max drawdown.
- Calmar ratio.
- Sortino ratio computed on daily excess return over the cash hurdle.
- Monthly downside and upside capture relative to the market benchmark.
- Positive month rate.
- Worst rolling 3-month, 6-month, and 12-month total returns.
- Maximum recovery duration in days.

## Validation

The market-relative excess return for each strategy is reconciled back to the already validated benchmark summary layer. This ensures the new benchmark expansion is built on the same aligned live windows rather than silently changing the original market comparison.

## Outputs

- `data/processed/inference/institutional_benchmark_daily.csv`
- `data/processed/inference/institutional_benchmark_monthly.csv`
- `data/processed/inference/institutional_benchmark_summary.csv`
- `data/processed/inference/institutional_benchmark_audit.csv`
