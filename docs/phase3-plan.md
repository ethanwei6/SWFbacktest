# Phase 3 Plan

## Objective

Deepen the project without widening the fund universe.

Phase 1 established the disclosure map and normalized data layers.
Phase 2 established that:

- naive mirroring is weak
- `PIF` is most useful as an exposure / de-risking signal
- `NBIM` is most useful as a slow-moving sector posture signal
- the best combined strategy, `S1`, shows only modest excess return versus `VT`

Phase 3 should answer the harder question:

- are the remaining signals robust, explainable, and operationally useful once we stress them properly?

## Core Recommendation

Do not add more sovereign wealth funds yet.

The highest-value next step is to build a `robustness + attribution + monitoring` layer around the strongest surviving strategies:

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

These four should be treated as the `focus set` for Phase 3.

## Why This Is The Right Next Step

The repo already has enough breadth. What it still needs is:

- stronger evidence that the remaining edges are real
- a cleaner explanation of where returns actually come from
- a better way to observe the signals as a living system rather than just as backtest rows

Adding another fund now would mostly add ingestion and comparability work. It would increase surface area faster than confidence.

## Phase 3 Workstreams

### Workstream A: Robustness Testing

Purpose:

- determine whether the surviving signals persist under more realistic assumptions

This is the top priority.

### Workstream B: Attribution

Purpose:

- explain why each focus strategy performs the way it does

This is the second priority.

### Workstream C: State Model

Purpose:

- convert the project from a collection of backtests into an explicit cross-fund state engine

This is the third priority.

### Workstream D: Monitoring / Interactive Layer

Purpose:

- make the signal stack understandable and usable on an ongoing basis

This is the fourth priority.

## Workstream A: Robustness Testing

### A1. Execution-Lag Sensitivity

Goal:

- test whether the results survive small implementation delays

Required variants:

- baseline `next-trading-day close`
- `T+3` execution
- `T+5` execution

Focus strategies:

- `P5`
- `N4`
- `N6`
- `S1`

Outputs:

- `data/processed/robustness/execution_lag_summary.csv`
- `data/processed/robustness/execution_lag_daily.csv`

Questions answered:

- is the edge real, or is it concentrated in immediate post-disclosure reaction?

### A2. Transaction Cost and Slippage Sensitivity

Goal:

- test whether small frictions erase the surviving edge

Required variants:

- `0 bps`
- `10 bps`
- `25 bps`
- `50 bps`

Apply:

- one-way execution cost at each buy and sell

Outputs:

- `data/processed/robustness/cost_sensitivity_summary.csv`

Questions answered:

- does `S1` still beat `VT` after plausible frictions?

### A3. Concentration and Exposure Caps

Goal:

- test whether the signal works after imposing more realistic portfolio constraints

Required variants:

- max position cap for `P5`
- max sector cap for `N4`, `N6`, `S1`
- max gross exposure cap where relevant

Outputs:

- `data/processed/robustness/concentration_cap_summary.csv`

Questions answered:

- is performance just coming from unconstrained concentration?

### A4. Subperiod Stability

Goal:

- check whether results are stable across market regimes

Suggested splits:

- `2019-2021`
- `2022-2023`
- `2024-2026`

Outputs:

- `data/processed/robustness/subperiod_summary.csv`

Questions answered:

- are the results persistent or regime-specific?

### A5. Benchmark Robustness

Goal:

- ensure conclusions do not depend too heavily on a single benchmark choice

Suggested comparisons:

- `PIF`: `SPY`, `QQQ`, equal-weight broad U.S. benchmark if feasible
- `NBIM`: `VT`, `ACWI` proxy if feasible
- `S1`: `VT`, `SPY`, and a blended benchmark

Outputs:

- `data/processed/robustness/benchmark_comparison_summary.csv`

Questions answered:

- is outperformance still present when measured against slightly different but reasonable passive alternatives?

## Workstream B: Attribution

### B1. Return Decomposition

Goal:

- split strategy performance into understandable drivers

Required decompositions:

- exposure timing effect
- allocation effect
- concentration effect
- cash drag
- lag drag

Focus set:

- `P5`
- `N4`
- `N6`
- `S1`

Outputs:

- `data/processed/attribution/strategy_return_decomposition.csv`

Questions answered:

- what actually drives `S1`?
- why does `P5` improve on `P2` but still trail `SPY`?

### B2. Event-Window Analysis

Goal:

- inspect forward performance after specific state changes

Event families:

- `PIF expanding`
- `PIF contracting`
- `NBIM overweight tech`
- `NBIM positive industry weight change`
- `cross-fund consensus gained`
- `cross-fund consensus lost`

Window lengths:

- `1 month`
- `3 months`
- `6 months`

Outputs:

- `data/processed/attribution/event_window_forward_returns.csv`

Questions answered:

- which state transitions actually matter most?

### B3. Hit-Rate and Contribution Analysis

Goal:

- move beyond total return and drawdown

Required metrics:

- percent of rebalance windows beating benchmark
- top and bottom contributing periods
- strategy contribution concentration

Outputs:

- `data/processed/attribution/window_hit_rate_summary.csv`
- `data/processed/attribution/top_bottom_windows.csv`

Questions answered:

- are results broad-based or driven by a few windows?

## Workstream C: State Model

### C1. Formal State Table

Goal:

- define a compact state machine from the current signals

Suggested fields:

- `state_date`
- `pif_risk_state`
- `nbim_sector_state`
- `cross_fund_confirmation_count`
- `model_exposure_target`
- `model_sector_tilt_primary`
- `state_change_flag`
- `state_change_reason`

Outputs:

- `data/processed/signals/swf_state_model.csv`

### C2. State Persistence Analysis

Goal:

- understand how long these states actually last

Outputs:

- `data/processed/signals/state_duration_summary.csv`

Questions answered:

- are these noisy triggers or durable conditions?

### C3. Forward Return by State

Goal:

- evaluate states directly, not only through full portfolio backtests

Outputs:

- `data/processed/signals/state_forward_return_summary.csv`

Questions answered:

- which states are most useful as allocators?

## Workstream D: Monitoring and Interactive Layer

### D1. Current Signal Dashboard Inputs

Goal:

- make the current system updateable and human-readable

Required outputs:

- `signals_latest.csv`
- `state_latest.csv`
- `model_targets_latest.csv`

### D2. Interactive Explorer Upgrade

Goal:

- extend the current exploration tooling beyond single-fund filing playback

Required features:

- current state summary
- last state change
- filing that triggered the change
- strategy response
- benchmark-relative outcome since that state

### D3. One-Page Automated Memo

Goal:

- generate a compact recurring research update

Sections:

- current `PIF` risk posture
- current `NBIM` sector posture
- current cross-fund consensus
- current model target exposure
- current model target sectors
- recent changes

Outputs:

- `outputs/monitoring/current_signal_memo.html`
- `outputs/monitoring/current_signal_memo.md`

## Implementation Order

Phase 3 should be built in this exact order:

1. `A1` execution-lag sensitivity
2. `A2` transaction cost and slippage sensitivity
3. `A3` concentration and exposure caps
4. `A4` subperiod stability
5. `B1` return decomposition
6. `B2` event-window analysis
7. `C1` formal state table
8. `C2` state persistence analysis
9. `D1` current dashboard inputs
10. `D2` interactive explorer upgrade

Reason:

- first prove the signal survives pressure
- then explain the signal
- only then productize the signal

## Definition of Done

Phase 3 is complete when:

- the surviving strategies have full robustness tables
- the focus set has attribution and event-window diagnostics
- a formal state model exists
- a current-state monitoring layer exists
- the paper conclusions can be updated from `interesting signal` to either:
  - `credible modest signal`, or
  - `fragile / non-persistent signal`

## Decision Rule

Maintain the same standard as earlier project phases:

- if a result weakens under robustness checks, downgrade it
- if an edge is small but survives the stress tests, keep it
- if a strategy is only interesting under one narrow assumption, do not present it as alpha

The goal of Phase 3 is not to find more attractive stories.
The goal is to determine which of the remaining stories survive careful pressure.
