# Phase 3 A3: Concentration and Exposure Caps

This step tests whether the surviving strategies still look credible after more realistic portfolio constraints.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Cap Variants

- `Uncapped`
- `Moderate Caps`
  - `P5` max position weight: `25%`
  - `N4`, `N6`, `S1` max sector / ETF weight: `35%`
  - `S1` max gross exposure: `75%`
- `Tight Caps`
  - `P5` max position weight: `20%`
  - `N4`, `N6`, `S1` max sector / ETF weight: `30%`
  - `S1` max gross exposure: `60%`

## Implementation

### `P5`

- rerun from the validated baseline signal file
- process sells and buys exactly as in the validated cash-aware logic
- after each rebalance, trim any position above the configured cap and leave the excess in cash
- no redistribution of excess weight is attempted

### `N4`, `N6`, and `S1`

- rerun from the validated stored target weights already present in the holdings files
- apply the cap directly to each stored target weight
- for `S1`, first limit gross exposure, then apply the per-sector cap
- any weight removed by the cap remains in cash

## Validation Rules

- the `Uncapped` variant must reproduce the validated baseline final NAV within floating-point tolerance
- observed rebalance-close position weights must not exceed the configured caps
- observed rebalance-close `S1` gross exposure must not exceed its configured cap

## Outputs

- `data/processed/robustness/concentration_cap_summary.csv`
- `data/processed/robustness/concentration_cap_daily.csv`
- `data/processed/robustness/concentration_cap_audit.csv`
