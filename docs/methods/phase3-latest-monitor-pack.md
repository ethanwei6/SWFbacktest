# Phase 3 Latest Monitor Pack

## Goal

Create a compact set of current-state outputs that surface the latest validated
cross-fund signals without forcing the user to inspect the full historical
signal and state tables.

## Inputs

- `data/processed/signals/swf_signal_states.csv`
- `data/processed/signals/swf_state_model.csv`
- `data/processed/signals/state_forward_return_summary.csv`
- `data/processed/inference/final_model_expression.csv`

## Outputs

- `data/processed/monitoring/signals_latest.csv`
- `data/processed/monitoring/state_latest.csv`
- `data/processed/monitoring/model_targets_latest.csv`
- `data/processed/monitoring/monitoring_latest_audit.csv`

## Construction rules

### `signals_latest.csv`

- use the latest row in `swf_signal_states.csv`
- emit the current `PIF` exposure state
- emit current `PIF` sector states
- emit current `NBIM` sector states
- emit the current `NBIM` top-3 members used by `N6`
- emit any current cross-fund consensus sectors

This file is intentionally long-form so downstream dashboards can filter by
signal group or sector without extra reshaping.

### `state_latest.csv`

- use the latest row in `swf_state_model.csv`
- attach the immediately prior state date
- preserve the current state signature and state-change fields
- expose the current model exposure target and implied cash target
- attach the six-month forward-return context for the current `PIF` risk state
  and current primary sector tilt from `state_forward_return_summary.csv`

### `model_targets_latest.csv`

- expose the current cross-fund state-model targets:
  - gross exposure target
  - residual cash target
  - primary sector tilt target
- expose the current production-sleeve targets from the accepted final model
  expression:
  - the current `N6` top-3 sector members
  - equal sector weights across those three members

## Validation

`monitoring_latest_audit.csv` checks:

- all three outputs share the same `as_of_date`
- production-sleeve target weights sum to `1.0`
- state-model gross exposure plus cash equals `1.0`
- the count of `NBIM` top-3 signal rows matches the state-model `top3` count

## Current interpretation

On the current latest validated date, `2026-05-18`:

- `PIF` is `neutral`
- `NBIM` is `overweight_led`
- the primary state-model tilt is `Technology` via `XLK`
- the model exposure target is `0.75`
- the current production sleeve remains the `N6` top-3 equal-weight basket:
  `Technology`, `Financials`, and `Consumer Discretionary`
