# Phase 3 C3: Forward Return by State

This layer evaluates the compact state model directly rather than only through the full portfolio backtests.

## Inputs

- `data/processed/signals/swf_state_model.csv`
- `data/processed/pif/pif_benchmark_daily.csv`
- `data/processed/nbim/nbim_twelvedata_daily_prices.csv`

## Method

For each state date, the analysis measures forward returns over `1`, `3`, and `6` calendar months.

### Market-state view

- `SPY` forward return
- `SPY` forward return minus unconditional average `SPY` drift for the same horizon
- `VT` forward return

### Sector-state view

If a primary sector tilt proxy exists, the analysis also measures:

- primary sector ETF forward return
- primary sector excess return versus `VT`
- primary sector excess return minus the unconditional average excess for that same ETF and horizon

## Outputs

- `data/processed/signals/state_forward_returns.csv`
- `data/processed/signals/state_forward_return_summary.csv`
- `data/processed/signals/state_forward_return_audit.csv`
