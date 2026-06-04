# Phase 4: Institutional Benchmarking

This layer expands the benchmark framework beyond simple market opportunity-cost comparisons.

## Goal

The project already asks whether disclosure-following strategies beat passive market beta. This extension asks a different question: whether any of the surviving strategies deliver a more institutional-style return profile with lower risk, shallower drawdowns, or better downside behavior.

## Benchmark families

- `SPY`, `VT`, and `ACWI` remain the market opportunity-cost benchmarks.
- `BIL` acts as the investable cash hurdle proxy.
- `USMV` is the defensive U.S. equity comparator.
- `ACWV` is the defensive global equity comparator.

## Price source

- Existing validated market benchmarks are reused from `data/processed/robustness/benchmark_series_daily.csv`.
- New benchmarks are fetched as adjusted daily series from Twelve Data.

## Outputs

- `data/processed/inference/institutional_benchmark_series_daily.csv`
- `data/processed/inference/institutional_benchmark_series_audit.csv`
