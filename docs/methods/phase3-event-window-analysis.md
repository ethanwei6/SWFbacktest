# Phase 3 B2: Event-Window Analysis

This layer moves one level below full strategies and asks which validated signal transitions are actually followed by favorable forward performance.

## Goal

- inspect forward returns after specific `PIF`, `NBIM`, and cross-fund state changes
- separate signal-level evidence from portfolio-construction effects

## Inputs

- `data/processed/signals/swf_signal_states.csv`
- `data/processed/signals/swf_combined_signal_panel.csv`
- `data/processed/pif/pif_benchmark_daily.csv`
- `data/processed/nbim/nbim_twelvedata_daily_prices.csv`

## Event families

### `pif_expanding`

- event date is the trade-date state transition into `PIF expanding`
- proxy asset is `SPY`
- benchmark is `CASH`

Interpretation:

- does a disclosed `PIF` public-equity expansion precede favorable subsequent U.S. equity returns?

### `pif_contracting`

- event date is the trade-date state transition into `PIF contracting`
- proxy asset is `SPY`
- benchmark is `CASH`

Interpretation:

- does a disclosed `PIF` contraction precede weak or negative subsequent U.S. equity returns?

### `nbim_overweight_tech`

- event date comes from `NBIM` `nbim_industry_weight_change` signals where:
  - `sector = Technology`
  - `signal_direction = overweight`
- proxy asset is `XLK`
- benchmark is `VT`

Interpretation:

- do explicit positive `NBIM` technology-weight changes lead to forward outperformance of the technology sleeve against global equities?

### `nbim_positive_industry_weight_change`

- event date comes from every `NBIM` `nbim_industry_weight_change` signal with `signal_direction = overweight`
- proxy asset is the mapped sector ETF:
  - `XLC`, `XLY`, `XLP`, `XLE`, `XLF`, `XLV`, `XLI`, `XLB`, `XLRE`, `XLK`, or `XLU`
- benchmark is `VT`

Interpretation:

- which sector-level positive `NBIM` weight changes are followed by positive forward excess returns?

### `cross_fund_consensus_gained`

- event date is when a common-sector consensus flag changes from `no` to `yes`
- proxy asset is the mapped sector ETF
- benchmark is `VT`

Interpretation:

- does newly gained `PIF + NBIM` directional alignment carry usable forward information?

### `cross_fund_consensus_lost`

- event date is when a common-sector consensus flag changes from `yes` to `no`
- proxy asset is the mapped sector ETF
- benchmark is `VT`

Interpretation:

- does losing cross-fund alignment foreshadow weaker sector-relative performance?

## Window construction

- windows are evaluated at `1`, `3`, and `6` calendar months
- the analysis start date is the first tradable close on or after the legal event date
- the analysis end date is the first common tradable close on or after the target calendar horizon
- benchmark-relative windows always use a common proxy/benchmark end date

This is intentionally conservative:

- it avoids fabricating returns on dates where either the proxy or benchmark is missing
- it keeps the window anchored to the same legal disclosure timing used throughout Phase 3

## Unconditional baseline comparison

To distinguish state-conditioned forward returns from ordinary market drift, each proxy and window pair also gets an unconditional baseline:

- for `SPY`, `VT`, and each sector ETF, compute every available forward window of the same length across the full tradable sample
- use the same end-date logic as the event study itself:
  - first tradable close on or after the target horizon
  - common proxy/benchmark end dates when a benchmark is involved
- attach the unconditional average proxy return, benchmark return, and excess return to every event row that uses that same proxy and horizon

This means `PIF` event families can now be interpreted two ways:

- absolute forward return versus cash
- conditional return versus the unconditional average `SPY` drift for the same horizon

The same comparison is available for the `NBIM` and cross-fund event families.

## Outputs

Running:

```bash
python3 scripts/phase3_event_window_analysis.py
```

produces:

- `data/processed/attribution/event_window_forward_returns.csv`
- `data/processed/attribution/event_window_summary.csv`
- `data/processed/attribution/event_window_audit.csv`

## Validation

- every output row records:
  - legal event date
  - realized analysis start date
  - target end date
  - actual end date
  - actual horizon in days
  - unconditional baseline averages for the same proxy and horizon
- the audit file checks:
  - start dates found
  - end dates found
  - unconditional baseline availability
  - valid date ordering
  - non-empty detail and summary outputs
