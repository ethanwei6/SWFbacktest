# Phase 2 Plan

## Objective

Move the project from `single-fund disclosure backtests` into a more realistic `multi-signal sovereign wealth fund framework`.

Phase 1 answered the narrow question:

- can we harvest alpha by directly mirroring `PIF` and `NBIM` disclosures?

The answer was:

- `PIF`: no robust alpha from straightforward lagged mirroring; the only materially better result came from treating disclosed sells as real de-risking and allowing cash to accumulate
- `NBIM`: no strong evidence for naive direct mirroring; the most credible signals were modest sector-allocation effects from industry weight changes and concentrated top-industry posture

Phase 2 should therefore stop treating the problem primarily as `copy trading` and instead treat it as `disclosure-derived state estimation`.

## Core Recommendation

The highest-value next project is:

- build a combined `PIF + NBIM` signal model
- test a small family of exposure and sector-rotation strategies that use both funds together
- only after that, consider extending to one more structurally comparable sovereign fund, most likely `Mubadala`

## Why This Is The Right Next Step

### What Phase 1 Established

`PIF` appears most informative as:

- a public-equity `risk posture` signal
- especially when visible sleeve contraction is respected rather than mechanically reinvested

`NBIM` appears most informative as:

- a `slow-moving sector allocation` signal
- especially through industry weight changes and concentration in leading sectors

Those two signals are complementary:

- `PIF` is narrower, more tactical, and filing-based
- `NBIM` is broader, slower, and structural

That makes a combined model more promising than either:

- naive `PIF` mirroring
- naive `NBIM` mirroring
- adding a new opaque fund just to increase surface area

### Why Not Widen Too Early

Adding another SWF now creates three risks:

- more time spent on ingestion and entity mapping rather than signal design
- more disclosure heterogeneity before the current insights are fully harvested
- greater risk of false positive narratives from thin or incomplete disclosure streams

The project already has enough validated data to support a stronger second phase without broadening the scope yet.

## Phase 2 Workstreams

### Workstream A: Combined `PIF + NBIM` Signal Layer

Build one normalized cross-fund signal table.

Suggested output:

- `data/processed/signals/swf_combined_signal_panel.csv`

Suggested fields:

- `signal_date`
- `effective_trade_date`
- `fund`
- `signal_family`
- `signal_name`
- `signal_direction`
- `signal_strength`
- `target_level`
- `source_snapshot`
- `source_public_date`
- `staleness_days`
- `sector`
- `industry`
- `security_key` if applicable
- `confidence_level`
- `notes`

Signal families to include:

- `pif_exposure`
- `pif_single_name`
- `pif_sector_proxy`
- `nbim_industry_weight`
- `nbim_industry_weight_change`
- `nbim_industry_concentration`
- `cross_fund_consensus`

Design rule:

- every row must be tradeable only from a public date forward
- every row must carry enough metadata to explain exactly why it exists

### Workstream B: Combined Strategy Family

Do not start with many strategies.

Start with three to five interpretable strategies.

#### S1: Exposure Regime Overlay

Idea:

- let `PIF` determine overall exposure
- let `NBIM` determine sector allocation only when exposure is on

Rules:

- if `PIF` visible sleeve is shrinking meaningfully, reduce gross exposure and carry more cash
- if `PIF` sleeve is stable or expanding, allow risk-on positioning
- within risk-on windows, overweight sectors supported by `NBIM` weight-change signals

Question answered:

- does `PIF` tell us when to own less risk, while `NBIM` tells us where to place the risk we still want?

#### S2: Cross-Fund Consensus Sector Tilt

Idea:

- only take sector tilts when both funds are directionally aligned

Rules:

- `NBIM` must show positive industry weight change or top-industry concentration
- `PIF` must not be in visible de-risking mode
- if both are constructive, allocate to the confirmed sectors
- otherwise stay benchmark-like or partially in cash

Question answered:

- is the signal stronger when a tactical SWF sleeve and a structural SWF book point the same way?

#### S3: `PIF` Cash-Aware Base Plus `NBIM` Sector Overlay

Idea:

- use the existing best `PIF` result as the base portfolio
- then tilt that portfolio using `NBIM` sector signals

Rules:

- start from `P5` cash-aware copy logic
- map current `PIF` holdings into sectors
- overweight sectors currently favored by `NBIM`
- underweight sectors with weak or negative `NBIM` signals

Question answered:

- can `NBIM` improve the only `PIF` strategy that already showed useful absolute behavior?

#### S4: `NBIM` Sector Sleeve With `PIF` Risk Filter

Idea:

- use `NBIM` sector strategies as the main alpha source
- use `PIF` only as a risk throttle

Rules:

- run `N4` or `N6` as the baseline signal
- when `PIF` contracts sharply, cut exposure by a fixed amount
- when `PIF` expands, restore full exposure

Question answered:

- is `PIF` most useful as a filter rather than a selection engine?

#### S5: Benchmark-Aware Defensive Variant

Idea:

- explicitly test whether the information helps risk-adjusted behavior even if it does not maximize return

Rules:

- same combined signal set as above
- impose lower maximum exposure and sector caps
- compare not only against benchmark return but also drawdown and volatility

Question answered:

- even if alpha is weak, does the signal family improve defense or timing?

### Workstream C: Monitoring Productization

Build the monitoring output in parallel with the strategy work, not after it.

Suggested artifacts:

- `signals_latest.csv`
- `signals_history.csv`
- one HTML summary report
- one interactive explorer that extends the current `PIF` explorer concept to cross-fund signal states

Must-have monitoring views:

- current `PIF` exposure regime
- latest `NBIM` sector changes
- current cross-fund consensus sectors
- recommended model exposure
- recommended model sector tilts

## Data Build Tasks

### Task 1: Sector Crosswalk For `PIF`

Current `PIF` outputs are mostly security-level.

Build:

- `data/processed/pif/pif_sector_exposure_by_filing.csv`
- `data/processed/pif/pif_sector_change_by_filing.csv`

Fields:

- `trade_date`
- `sector`
- `industry`
- `weight_before`
- `weight_after`
- `net_weight_change`
- `entry_count`
- `exit_count`
- `accumulation_count`
- `reduction_count`

Reason:

- without this, we can’t compare `PIF` and `NBIM` on the same dimension

### Task 2: Freeze Common Sector Taxonomy

Use one sector taxonomy across both funds.

Requirements:

- explicit crosswalk table
- no silent many-to-one mappings without documentation
- every combined strategy should use this shared taxonomy

Suggested output:

- `schemas/common-sector-taxonomy.md`
- `data/reference/common_sector_crosswalk.csv`

### Task 3: Signal State Table

Build a dated table that turns raw observations into model states.

Suggested output:

- `data/processed/signals/swf_signal_states.csv`

Examples:

- `pif_exposure_state = expanding / stable / contracting`
- `nbim_sector_state[Technology] = overweight / neutral / underweight`
- `cross_fund_consensus[Technology] = yes / no`

### Task 4: Benchmark Expansion

Current benchmarking is correct but too simple for combined strategies.

Add:

- `SPY`
- `VT`
- sector ETF benchmarks for sleeve-relative tests
- possibly a blended benchmark for mixed cash-and-sector portfolios

Suggested output:

- `data/processed/benchmarks/combined_strategy_benchmarks.csv`

## Validation Gates

This phase should be validation-heavy.

Do not proceed to interpretation until each gate passes.

### Gate 1: Signal Construction Audit

Check:

- every signal is public-date legal
- every signal maps cleanly into the common sector taxonomy
- every signal has a reproducible source

Artifacts:

- `signal_construction_audit.csv`

### Gate 2: Timing Audit

Check:

- no strategy uses pre-release dates
- all trade dates are first legal market dates after public release
- all rebalance dates match the declared execution convention

Artifacts:

- `timing_audit.csv`

### Gate 3: Holdings And Exposure Audit

Check:

- weights sum correctly
- cash behavior matches the strategy spec
- sector caps and concentration rules are respected

Artifacts:

- `exposure_audit.csv`

### Gate 4: Price And Benchmark Audit

Check:

- source API spot-checks for a sample of instruments and dates
- benchmark rebasing correctness
- adjusted vs raw price usage clearly documented

Artifacts:

- `price_audit.csv`
- `benchmark_audit.csv`

### Gate 5: Interpretation Audit

Check:

- positive results are stress-tested before being highlighted
- every strong result has a mechanism explanation, not just a number
- if the best combined strategy still fails against benchmark, say so clearly

## Recommended Deliverables For Phase 2

### Deliverable 1: Combined Strategy Research Memo

This should answer:

- does combining `PIF` and `NBIM` produce better signals than either alone?
- is the edge in stock selection, sector allocation, exposure timing, or some mixture?

### Deliverable 2: Combined Backtest Pack

Include:

- strategy summaries
- benchmark-relative comparisons
- detailed order and holdings files
- contribution analysis
- overlap and correlation analysis across strategies

### Deliverable 3: Monitoring View

A standing product that says:

- what the SWFs most recently implied
- what the current model would hold
- why the model is holding it

## Extension After Phase 2

Only after the combined-signal phase is complete should the project widen.

### Best Candidate: `Mubadala`

Reason:

- recurring SEC `13F-HR` visibility
- structurally similar enough to `PIF` for a comparable sleeve analysis

Use case:

- extend the `13F` sovereign sleeve universe
- test whether `PIF`-like exposure signals generalize

### Possible Candidate: `Temasek`

Reason:

- potentially usable U.S. filing footprint

Risk:

- entity and filing consistency may be messy
- likely requires a careful entity-structure review before trusting it

### Not Recommended Yet

- `ADIA`: event-driven ownership filings, not a clean recurring holdings panel
- `GIC`: still too opaque for a comparable quantitative sleeve

## Execution Order

### Step 1

Build `PIF` sector exposure and sector change tables.

### Step 2

Freeze a common `PIF/NBIM` sector taxonomy and crosswalk.

### Step 3

Build the combined signal panel and signal-state table.

### Step 4

Implement `S1` through `S3` first.

### Step 5

Run validation gates before interpreting anything.

### Step 6

Only then add `S4` and `S5`.

### Step 7

Package the results into a combined memo and monitoring view.

### Step 8

Only after that, consider `Mubadala`.

## Strong Recommendation

If we want the highest-probability next success:

- do **not** broaden to many new SWFs yet
- do **not** go back to naive copy-trading
- do **build** a combined `PIF + NBIM` model centered on
  - `PIF` exposure state
  - `NBIM` sector posture
  - cross-fund confirmation

That is the most realistic path from this project’s current findings to a stronger, more defensible alpha thesis.
