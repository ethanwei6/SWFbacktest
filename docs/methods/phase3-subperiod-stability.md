# Phase 3 A4: Subperiod Stability

This layer tests whether the validated focus-set strategies behave consistently across distinct market regimes.

## Focus set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Method

A4 does not re-run the strategies. It uses the validated baseline portfolio timelines already stored in the repo and slices them into the planned subperiods:

- `2019-2021`
- `2022-2023`
- `2024-2026`

For each strategy and subperiod:

1. keep only baseline portfolio rows whose dates fall inside the subperiod;
2. align the benchmark using the same carry-forward benchmark-series logic used in prior robustness steps;
3. rebase both strategy NAV and benchmark NAV to `1.0` on the first aligned subperiod date;
4. compute subperiod total return, benchmark total return, excess total return, max drawdown, average cash weight, and average gross exposure.

## Outputs

- `data/processed/robustness/subperiod_summary.csv`
- `data/processed/robustness/subperiod_daily.csv`
- `data/processed/robustness/subperiod_audit.csv`

## Validation

The audit checks that each strategy/subperiod combination has at least two aligned rows, that aligned dates remain ordered, and that both strategy and benchmark rebase to `1.0` on the first aligned date.
