# Phase 3 B3: Window Hit-Rate and Contribution Analysis

This layer asks whether the surviving results are broad-based across rebalance windows or dominated by a small number of periods.

## Focus set

- `P5` Cash-Aware Copy versus `SPY`
- `N4` Industry Weight-Change Tilt versus `VT`
- `N6` Top-3 Industry Leaders versus `VT`
- `S1` Exposure Regime Overlay versus `VT`

## Method

B3 uses the already validated `benchmark_comparison_daily.csv` layer so every window starts from aligned strategy and benchmark NAVs. Rebalance windows are formed from each strategy's native rebalance-event file:

- start at a rebalance trade-date close;
- end at the next rebalance trade-date close;
- for the final window, end at the last available aligned daily observation.

For each window we compute:

- strategy window return;
- benchmark window return;
- excess window return;
- exact additive contribution, defined as the change in `relative_excess_nav` across the window.

That contribution measure is important because it sums exactly to the final benchmark-relative NAV difference, which makes concentration analysis truthful rather than approximate.

## Outputs

- `data/processed/attribution/window_hit_rate_summary.csv`
- `data/processed/attribution/top_bottom_windows.csv`
- `data/processed/attribution/window_hit_rate_audit.csv`

## Validation

The audit checks that each rebalance window can be found in the aligned benchmark-comparison layer and that summed window contributions reconcile to the final relative-excess NAV for each strategy.
