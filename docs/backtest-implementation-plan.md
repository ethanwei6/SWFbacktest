# Backtest Implementation Plan

## Purpose

Define the exact logic for translating sovereign wealth fund disclosure data into investable signals, simulated portfolios, trades, and performance measurement.

This document exists to prevent three common mistakes:

- trading on `as_of_date` instead of the first public date
- treating partial disclosure as a full portfolio
- confusing descriptive ownership changes with executable trading instructions

## Backtest Principles

### Principle 1: Trade Only On Public Information

Every strategy must use:

- `public_date` or filing date as the first day the signal can be acted on

Never use:

- `as_of_date`
- report period end
- economic effective date

for trade entry timing unless it is the actual public date.

### Principle 2: Strategy Must Match The Disclosure Regime

- `PIF` supports security-level mirroring because `13F` provides security rows, share counts, and market values
- `NBIM` supports slow-moving sector and concentration tests better than single-name mirroring
- `GIC` is not in the initial quantitative panel

### Principle 3: Simplicity First

The first implementations should be:

- easy to audit
- easy to explain
- robust to missing fields

Only after baseline results exist should we add:

- risk adjustments
- more complex weighting
- sector-neutral overlays
- transaction cost assumptions

## Strategy Families

## `PIF` Strategy Family

### What The Data Gives Us

From canonical `13F` filings we have:

- security-level rows
- `CUSIP`
- share count
- market value
- filing date
- report date
- option flags in later periods

This is the cleanest investable disclosure dataset in the project.

### Data Interpretation

`PIF` `13F` is:

- a recurring snapshot of the reportable US `13F` sleeve
- not a full picture of the fund

So we can simulate:

- mirroring the disclosed sleeve
- mirroring newly added names
- tilting away from names being exited or reduced

But we cannot claim:

- this is the whole `PIF` portfolio
- this is `PIF`’s complete public-equity book

### `PIF` Baseline Strategies

#### Strategy `P1`: New Positions Mirror

Signal definition:

- buy securities classified as `entry_observed` in the transition dataset

Trade timing:

- enter at the first tradable close after `public_date`

Exit timing candidates:

- hold until the next `PIF` filing date
- or hold for a fixed number of trading days

Reason to test:

- strongest expression of “copy the new disclosed moves”

#### Strategy `P2`: Full Disclosed Sleeve Mirror

Signal definition:

- hold every common-equity position disclosed in the canonical `13F` filing

Trade timing:

- rebalance each filing date

Weighting variants:

- equal-weight across names
- value-weight using disclosed market value

Reason to test:

- closest analog to naive mirroring of the public `13F` sleeve

#### Strategy `P3`: Accumulation Overlay

Signal definition:

- overweight names marked `likely_accumulation`
- underweight or exclude names marked `likely_reduction`

Trade timing:

- rebalance on filing date

Reason to test:

- uses share-count changes instead of mere inclusion

#### Strategy `P4`: Exit Avoidance

Signal definition:

- exclude names marked `exit_observed`
- optionally short only in a paper diagnostic, not a production baseline

Reason to test:

- tests whether post-disclosure exits carry negative drift

### `PIF` Security Universe Rules

Baseline recommendation:

- use common-equity rows only
- exclude options from the first baseline

Diagnostic variant:

- run a second version including options to understand how much later filings change the sleeve composition

Reason:

- options change the economic interpretation of “mirroring”
- common-equity-only is cleaner and more comparable

### `PIF` Portfolio Construction

Baseline weighting:

- equal-weight

Why:

- more stable against one-name domination
- easier to compare with entry-driven signals
- less sensitive to disclosed mega-positions like `LUCID` or `UBER`

Secondary weighting:

- value-weight by disclosed market value

Why:

- closer to disclosed portfolio expression
- useful as a robustness check

Position cap:

- include a max single-name weight, for example `10%` or `15%`, as a robustness variant

Cash treatment:

- if there are fewer qualifying names in a period, leave the residual in cash
- measure both raw portfolio return and excess return against benchmark

### `PIF` Trade Simulation Rules

For each filing period:

1. determine the signal using the transition dataset or holdings dataset
2. map the signal to a target portfolio on `public_date`
3. execute at next close or next open, depending on available price convention
4. hold until the next rebalance or fixed-horizon exit

Initial simplifying assumption:

- trade at next-day close after `public_date`

Reason:

- avoids same-day execution assumptions
- easier to reproduce

### `PIF` Performance Questions

We want to know:

- does the disclosed sleeve outperform after publication?
- do new positions outperform existing holdings?
- do accumulation signals outperform flat or reduction signals?
- does any edge survive after disclosure lag?

## `NBIM` Strategy Family

### What The Data Gives Us

From the `NBIM` holdings history we have:

- broad public-equity coverage
- market value
- observable presence and disappearance
- ownership percentages
- voting percentages
- semiannual / year-end style snapshots depending on source history

But we do not have:

- share count
- quarter-by-quarter tradable full-book disclosure like `13F`

So the strategy should be slower and more aggregated.

### Data Interpretation

`NBIM` is better suited to:

- industry and sector tilt signals
- portfolio concentration signals
- broad ownership-presence shifts

It is less suited to:

- fast security-level mirroring
- trade-by-trade entry timing claims

### `NBIM` Baseline Strategies

#### Strategy `N1`: Industry Accumulation Tilt

Signal definition:

- for each snapshot, compute net industry accumulation using:
  - `likely_accumulation` counts
  - minus `likely_reduction` counts

Portfolio rule:

- overweight industries with strongest positive net signal
- underweight or exclude industries with strongest negative signal

Implementation choice:

- translate industry signals into liquid sector/industry ETFs or broad baskets

Reason:

- keeps the strategy aligned with the actual observability of the data

#### Strategy `N2`: Industry Weight Change Tilt

Signal definition:

- compare `NBIM` portfolio-weight shifts by industry between public snapshots

Portfolio rule:

- overweight industries gaining weight
- underweight industries losing weight

Reason:

- uses broad disclosed allocation shifts rather than noisy single-name interpretation

#### Strategy `N3`: Concentration Regime Filter

Signal definition:

- track top-10 concentration and industry leadership concentration

Portfolio rule:

- this may become a contextual filter rather than a standalone strategy

Reason:

- concentration shifts may tell us when `NBIM` is leaning into a narrower set of themes

### `NBIM` Tradable Mapping Problem

Unlike `PIF`, `NBIM` industry signals do not immediately define a tradable portfolio.

So we need a mapping layer:

- `NBIM` industry signal -> public benchmark instrument

Possible implementation approaches:

- sector ETFs
- country-sector ETFs if geography matters
- liquid large-cap industry baskets if accessible

Default recommendation:

- start with sector ETFs or broad industry ETFs

Reason:

- keeps implementation simple and investable

### `NBIM` Portfolio Construction

Baseline:

- equal-weight top `K` positive industries
- equal-weight bottom `K` negative industries as an underweight or exclusion benchmark

Possible first design:

- long-only version: hold top `3` to `5` industries
- relative version: compare against a broad market benchmark rather than running an explicit short book

Trade timing:

- enter after the first public date of the snapshot
- rebalance on each new public snapshot

### `NBIM` Performance Questions

We want to know:

- do industries with repeated net accumulation outperform after disclosure?
- is the sector-level signal stronger than a naive single-name mirror?
- does the slow disclosure cadence still leave a usable edge?

## Shared Simulation Design

## Calendar

All backtests need:

- a signal date
- a trade date
- a hold window
- a rebalance date

Minimum fields in the backtest-ready panel:

- `signal_date`
- `trade_date`
- `exit_date`
- `instrument`
- `signal_type`
- `target_weight`
- `fund`
- `strategy_id`

## Rebalance Conventions

Test at least these:

- rebalance at each new disclosure
- fixed holding windows such as `20`, `60`, and `90` trading days

Why:

- some signals may decay quickly
- others may reflect slower structural themes

## Return Measurement

Measure:

- cumulative return
- annualized return
- volatility
- Sharpe ratio
- max drawdown
- hit rate
- excess return versus benchmark

For event-style tests also measure:

- average forward return by signal type
- median forward return

## Benchmarks

### `PIF`

Primary benchmark:

- broad US equity benchmark such as `SPY` or `IVV`

Useful secondary benchmarks:

- equal-weight US benchmark
- large-cap growth benchmark if the sleeve is growth-heavy

### `NBIM`

Primary benchmark:

- broad global or sector-level benchmark depending on test design

Useful secondary benchmarks:

- sector ETF basket matching the strategy construction universe

## Transaction Assumptions

For the first pass:

- assume zero transaction costs
- assume liquid execution at next-day close

After baseline:

- add simple cost assumptions
- add turnover statistics

## Validation Checks Before Coding

Before implementing returns logic, confirm:

- `PIF public_date` is clean and monotonic
- `PIF` option rows are identified correctly
- `NBIM` public-date mapping is finalized
- benchmark mapping is explicitly chosen
- sector taxonomy is frozen for `NBIM`

## Proposed Build Order

1. create `PIF` backtest-ready event panel
2. create `PIF` strategy definitions and portfolio constructor
3. create `NBIM` industry-signal panel
4. create `NBIM` sector-mapping table
5. add return simulation layer
6. add benchmark comparison layer
7. run baseline and robustness variants

## Recommended First Implementation

If we want the highest-confidence first backtest:

1. `PIF` `new-positions` mirror
2. `PIF` `full disclosed sleeve` mirror
3. `NBIM` `industry accumulation tilt`

This sequence gives:

- one clean single-name mirroring test
- one clean disclosed-sleeve test
- one slower sector-tilt test

That is probably the best first answer to the alpha question with the data we currently have.
