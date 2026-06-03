# Phase 2 Combined Strategy Backtests

Phase 2 tests combined `PIF + NBIM` strategies built on the validated signal layer rather than on naive single-fund mirroring.

## Inputs

- `data/processed/signals/swf_signal_states.csv`
- `data/processed/signals/swf_combined_signal_panel.csv`
- `data/processed/nbim/nbim_twelvedata_daily_prices.csv`
- `data/processed/pif/pif_twelvedata_daily_prices.csv`
- `data/processed/pif/backtests/p5_cash_aware_copy/*`
- `data/reference/pif_sector_crosswalk.csv`

## Strategy Definitions

### `S1` Exposure Regime Overlay

Purpose:

- use `PIF` as the risk-on / risk-off regime signal
- use `NBIM` as the sector allocation engine

Rules:

- `PIF expanding` or `initial`: `100%` gross exposure
- `PIF stable`: `75%` gross exposure
- `PIF contracting`: `50%` gross exposure
- invested sleeve goes to `NBIM` sectors with `overweight` state
- if no `NBIM overweight` sectors exist, fall back to `NBIM` top-3 sectors

### `S2` Cross-Fund Consensus Sector Tilt

Purpose:

- allocate only when both funds are directionally aligned

Rules:

- `PIF expanding` or `initial`: up to `100%` gross exposure
- `PIF stable`: `60%` gross exposure
- `PIF contracting`: `25%` gross exposure
- if cross-fund consensus sectors exist, allocate invested sleeve across them using `NBIM` sector weights
- if no consensus sectors exist, hold `VT` for the invested sleeve and keep the rest in cash

### `S3` `PIF` Cash-Aware Base Plus `NBIM` Overlay

Purpose:

- test whether `NBIM` can improve the validated `P5` cash-aware `PIF` portfolio

Rules:

- inherit the current `P5` cash weight exactly
- inherit the current `P5` held universe exactly
- reweight only the invested sleeve using `NBIM` sector posture:
  - `NBIM overweight`: multiplier `1.25`
  - `NBIM top-3 but not overweight`: multiplier `1.10`
  - `NBIM underweight`: multiplier `0.75`
  - otherwise: multiplier `1.00`

### `S4` `N4` Sleeve With `PIF` Risk Filter

Purpose:

- test whether the most credible realistic `NBIM` sleeve improves when `PIF` is used only as a risk throttle

Rules:

- use the validated `N4 Industry Weight-Change Tilt` sleeve as the base allocation source
- on each combined event date, scale the sleeve by the current `PIF` exposure regime:
  - `PIF expanding` or `initial`: `100%` gross exposure
  - `PIF stable`: `75%` gross exposure
  - `PIF contracting`: `50%` gross exposure
- keep the residual in cash
- if the `N4` sleeve is not yet available, remain fully in cash until the first legal sleeve date

### `S5` `N6` Sleeve With `PIF` Risk Filter

Purpose:

- repeat the same risk-filter test on the validated `N6 Top-3 Industry Leaders` sleeve

Rules:

- use the validated `N6` sleeve as the base allocation source
- scale the sleeve by the same `PIF` regime map used in `S4`
- keep the residual in cash

## Execution Convention

- all rebalances happen at the legal event-date close already encoded in `swf_signal_states.csv`
- daily marks use split-adjusted closes from the validated `PIF` and `NBIM` price layers
- the sector-ETF calendar uses the intersection of all required tradable daily series to avoid fabricated marks on dates where a sleeve instrument is missing

## Outputs

Running:

```bash
python3 scripts/swf_phase2_backtest_runner.py
python3 scripts/swf_phase2_analysis_report.py
```

produces:

- strategy folders under `data/processed/combined/backtests/`
- benchmark layer at `data/processed/benchmarks/combined_strategy_benchmarks.csv`
- benchmark summaries at `data/processed/combined/backtests/analysis/`
- charts at `outputs/combined/backtests/charts/`
- report at `outputs/combined/backtests/reports/phase2_combined_signal_report.html`

## Validation Notes

- holdings plus cash reconcile to `1.0` within floating-point tolerance
- no trade-date violations remain in `data/processed/signals/timing_audit.csv`
- `S3` preserves `P5` cash weights by construction and only redistributes the invested sleeve
- `S4` and `S5` inherit only validated `NBIM` sleeve weights and the public `PIF` exposure regime; they do not introduce any new security-selection layer
