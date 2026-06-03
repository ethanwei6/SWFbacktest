# Phase 3 A2: Transaction Cost and Slippage Sensitivity

This step tests whether the surviving strategies remain credible after one-way implementation frictions.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Cost Variants

- `0 bps`
- `10 bps`
- `25 bps`
- `50 bps`

Each cost is applied one-way to every buy and sell notional.

## Implementation

### `P5`

- rerun from the validated baseline signal-eligibility file
- sells add `execution_value * (1 - cost_rate)` to cash
- buys consume `execution_value * (1 + cost_rate)` from cash
- buy fill ratios are recomputed so the strategy remains self-financing

### `N4`, `N6`, and `S1`

- rerun from the validated baseline rebalance target weights already expressed in the stored holdings files
- on each rebalance date, solve the post-cost portfolio value `V` from:

`V = nav_pre - cost_rate * sum_i |target_value_i(V) - current_value_i|`

- target holdings are then sized from `V`, which keeps the rebalance self-financing without negative cash

## Validation Rules

- `0 bps` must reproduce each validated baseline final NAV exactly within floating-point tolerance
- cash reconciliation on every rebalance must hold to floating-point tolerance
- no new price sources are introduced; only the already-audited stored daily files are used

## Outputs

- `data/processed/robustness/cost_sensitivity_summary.csv`
- `data/processed/robustness/cost_sensitivity_daily.csv`
- `data/processed/robustness/cost_sensitivity_audit.csv`
