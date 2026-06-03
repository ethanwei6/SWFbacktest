# Phase 3 B1: Return Decomposition

This layer explains what drives the surviving Phase 3 focus-set strategies without inventing a false exact terminal-return attribution.

## Focus set

- `P5` Cash-Aware Copy versus `SPY`
- `N4` Industry Weight-Change Tilt versus `VT`
- `N6` Top-3 Industry Leaders versus `VT`
- `S1` Exposure Regime Overlay versus `VT`

## Attribution design

The decomposition is done in daily or period-by-period arithmetic excess-return space. For each period, excess return is split exactly into:

1. `exposure_timing_effect`: the effect of holding less than full benchmark exposure, equal to `-cash_weight_prev * benchmark_return` for these unlevered long-only strategies;
2. `allocation_effect`: the excess return from the strategy's start-of-period holdings if those holdings were equal-weighted within the invested sleeve;
3. `concentration_effect`: the incremental effect of using the actual strategy weights instead of equal weights within that same start-of-period sleeve.

These components reconcile exactly to the observed arithmetic excess return for each period. They are then summed across time to produce cumulative arithmetic explanatory contributions. Because compounded terminal excess return is not additively decomposable in the same way, the output also keeps the separately reported terminal total-return and excess-return values.

## Additional robustness drags

The summary table also imports:

- `lag_drag_excess_t5_minus_t1` from A1;
- `cost_drag_excess_50bps_minus_0bps` from A2;
- `cap_drag_excess_tight_minus_uncapped` from A3.

These are not part of the daily arithmetic decomposition itself; they are reported alongside it to show which strategies are most fragile to realistic implementation stress.

## Outputs

- `data/processed/attribution/strategy_return_decomposition.csv`
- `data/processed/attribution/daily_excess_return_decomposition.csv`
- `data/processed/attribution/strategy_decomposition_audit.csv`
