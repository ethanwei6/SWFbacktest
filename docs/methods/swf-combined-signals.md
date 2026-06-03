# Combined `PIF + NBIM` Signal Layer

This step converts normalized `PIF` and `NBIM` sector datasets into one dated signal panel plus one forward-filled state table for combined-strategy work.

## Inputs

- `data/processed/pif/pif_sector_exposure_common.csv`
- `data/processed/pif/pif_sector_change_common.csv`
- `data/processed/nbim/nbim_snapshot_sector_common.csv`
- `data/processed/nbim/nbim_transition_sector_common.csv`

## Outputs

Running:

```bash
python3 scripts/swf_combined_signal_builder.py
```

produces:

- `data/processed/signals/swf_combined_signal_panel.csv`
- `data/processed/signals/swf_signal_states.csv`
- `data/processed/signals/signal_construction_audit.csv`
- `data/processed/signals/timing_audit.csv`

## Signal Families

### `pif_exposure`

Purpose:

- classify the disclosed `PIF` common-equity sleeve as `expanding`, `stable`, or `contracting`

Inputs used:

- filing-to-filing common-equity holding-count change
- filing-to-filing sector-level flow score
  - `entries + accumulations - exits - reductions`

Current rule:

- `expanding` if holding-count change is at least `+15%` or total flow score is at least `+5`
- `contracting` if holding-count change is at most `-15%` or total flow score is at most `-5`
- otherwise `stable`

Implementation note:

- the reported exposure-strength metric caps the absolute holding-count-change component at `1.0`
- this avoids denominator artifacts after near-zero sleeves dominating the scale

### `pif_sector_proxy`

Purpose:

- infer which sectors `PIF` is leaning toward or away from

Current rule:

- `positive` if sector flow score is positive or sector weight change exceeds `+2%`
- `negative` if sector flow score is negative or sector weight change is below `-2%`
- otherwise `neutral`

### `nbim_industry_weight_change`

Purpose:

- classify `NBIM` sector posture from public weight changes

Current rule:

- `overweight` if normalized sector weight rises by more than `50 bps`
- `underweight` if it falls by more than `50 bps`
- otherwise `neutral`

### `nbim_industry_concentration`

Purpose:

- identify whether a sector is inside the current `NBIM` top-3 sector weights

Current rule:

- `top3` if the sector ranks inside the current top three
- `not_top3` otherwise

### `cross_fund_consensus`

Purpose:

- identify sectors where both funds are directionally aligned

Current rule:

- `yes` only when:
  - the latest `PIF` exposure state is not `contracting`
  - the latest `PIF` sector state is `positive`
  - and the latest `NBIM` sector state is `overweight` or the sector is `NBIM` top-3
- otherwise `no`

## State Table

`swf_signal_states.csv` is forward-filled on the union of `PIF` and `NBIM` legal trade dates.

Each row represents the latest known state from both funds as of that event date, including:

- latest `PIF` exposure state
- latest `PIF` sector states and sector weights
- latest `NBIM` sector states, sector weights, and top-3 flags
- derived cross-fund consensus flags for all common sectors

This is the intended input for the combined Phase 2 strategy engines.
