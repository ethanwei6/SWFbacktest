# Phase 3 Workstream C: State Model

This layer converts the validated cross-fund signal table into a compact state machine suitable for persistence and forward-return analysis.

## Inputs

- `data/processed/signals/swf_signal_states.csv`
- `data/processed/signals/swf_combined_signal_panel.csv` (indirectly via the validated state inputs)

## C1 Formal State Table

The compact model is built from the already validated forward-filled signal state table.

### Core fields

- `state_date`
- `pif_risk_state`
- `nbim_sector_state`
- `cross_fund_confirmation_count`
- `model_exposure_target`
- `model_sector_tilt_primary`
- `state_change_flag`
- `state_change_reason`

### Mapping rules

- `PIF initial` and `PIF expanding` map to `risk_on` with target exposure `1.00`
- `PIF stable` maps to `neutral` with target exposure `0.75`
- `PIF contracting` maps to `risk_off` with target exposure `0.50`
- if any cross-fund consensus sectors exist, the model becomes `consensus_led` and the highest-weight consensus sector becomes the primary tilt
- otherwise, if any `NBIM overweight` sectors exist, the model becomes `overweight_led` and the highest-weight overweight sector becomes the primary tilt
- otherwise, the model becomes `top3_led` and the highest-weight current `NBIM` top-3 sector becomes the primary tilt

## C2 Persistence Analysis

State segments are formed by contiguous rows with identical `state_signature`. Segment duration is measured in calendar days from the segment start date to the next state's date.

## Outputs

- `data/processed/signals/swf_state_model.csv`
- `data/processed/signals/state_segments.csv`
- `data/processed/signals/state_duration_summary.csv`
- `data/processed/signals/swf_state_model_audit.csv`
