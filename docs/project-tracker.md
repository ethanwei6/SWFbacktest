# Project Tracker

## Objective

Build a research process and monitoring framework for large sovereign wealth funds that answers two questions:

- does lagged mirroring of disclosed sovereign wealth fund positions generate investable alpha?
- do sector and industry tilts implied by sovereign wealth fund accumulation carry more durable signal than single-name mirroring?

## Deliverables

- disclosure map for `GPFG`, `PIF`, and `GIC`
- normalized holdings dataset with visibility and confidence flags
- strategy and exit-timeline write-up per fund
- backtest report for mirroring and sector-tilt hypotheses
- live monitoring view for new disclosed moves
- final memo on whether the alpha thesis holds after disclosure lag

## Milestones

### `M1` Disclosure Map

Status: `in progress`

Definition of done:

- each fund has a source inventory
- each source has cadence, lag, coverage, and limitations documented
- each source is tagged as quantitative, qualitative, or unusable for alpha testing

Progress notes:

- initial disclosure map drafted in [`docs/disclosure-map.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/disclosure-map.md)
- key correction captured: `NBIM` public holdings visibility is broader than an annual-report-only framing and should be split into semiannual web visibility versus year-end historical holdings data

### `M2` Holdings Dataset

Status: `not started`

Definition of done:

- normalized schema is fixed
- historical `GPFG` holdings are loaded
- historical `PIF` `13F` holdings are loaded
- `GIC` proxy methodology is documented
- `GIC` proxy rows are loaded with confidence and source attribution

### `M3` Strategy and Exit Characterization

Status: `not started`

Definition of done:

- sector and geography concentration summary for each fund
- stated mandate vs revealed behavior section for each fund
- observable holding-period and exit-pattern analysis completed
- key comparability caveats written clearly

### `M4` Alpha Backtest

Status: `not started`

Definition of done:

- lagged mirroring test run from public availability dates
- sector-tilt test run from public availability dates
- benchmark, rebalance, and holding-window assumptions documented
- sensitivity checks complete for lag and weighting choices

### `M5` Monitoring View and Final Memo

Status: `not started`

Definition of done:

- monitoring table or dashboard spec exists
- new disclosed moves can be classified as new, increase, decrease, or exit
- sector implications are summarized per update cycle
- final memo states clearly whether the alpha thesis survives disclosure lag

## Recommended Sequencing

### Phase 1: Research Design

- finalize scope assumptions
- define what counts as observed versus inferred exposure
- define entry, exit, and disclosure lag consistently

### Phase 2: Disclosure Mapping

- `GPFG`: `NBIM` holdings and any supplemental public channels
- `PIF`: `SEC 13F` history and any public ownership disclosures outside `13F`
- `GIC`: `SEC 13D/G`, `FCA TR-1`, `HK DI`, `EDINET`, deal press, co-investment announcements

### Phase 3: Data Build

- build `GPFG` and `PIF` first
- freeze schema before adding `GIC`
- document `GIC` proxy inclusion rules before entering rows

### Phase 4: Descriptive Analysis

- sector, geography, concentration, turnover
- public vs private emphasis
- mandate versus observable behavior

### Phase 5: Exit and Alpha Analysis

- reconstruct first observable appearances and disappearances
- characterize exit process types
- test lagged mirroring
- test sector accumulation signals

### Phase 6: Monitoring Layer

- define update pipeline
- specify alert fields
- connect new filings to sector implications

## Working Assumptions

- the main quantitative analysis should be public-markets only
- private and co-investment activity should be included mainly for qualitative context
- `GIC` should be treated as a best-effort proxy, not as a directly comparable fully observed portfolio
- results should be reported separately by fund before any pooled conclusion
- the first backtests should use `PIF` and `NBIM` only, with `GIC` treated as qualitative-only unless a later proxy dataset proves strong enough

## Key Risks

- overstating investability by using period-end dates instead of public dates
- implying comparability between `GIC` and `GPFG` or `PIF` where none exists
- confusing first disclosure with true entry
- building sector signals from too-thin `GIC` observations
- spending disproportionate time on exhaustive `GIC` reconstruction

## Decision Log

### Decisions to Confirm Early

- whether the deliverable prioritizes research memo, monitoring tool, or both equally
- whether public equities are the core investable scope
- whether `GIC` remains in-scope under a best-effort proxy approach
- whether private-market activity is qualitative-only

### Default Recommendation

- keep the core deliverable as both memo plus monitoring view
- run the main backtests on public equities only
- keep `GIC` in scope as a separate proxy module
- emphasize sector-tilt testing alongside single-name mirroring
- do not force `GIC` into the main backtest panel if only sparse threshold-event data is available

### Current Decision

- `GIC` remains in scope for the research memo and disclosure-asymmetry discussion
- `GIC` is out of scope for the initial quantitative backtests
- initial backtests should proceed with `PIF` and `NBIM`

## Suggested Weekly Plan

### Week 1

- finish disclosure map
- finalize schema
- draft `GIC` proxy methodology

### Week 2

- collect and normalize `GPFG` holdings
- collect and normalize `PIF` `13F` holdings

### Week 3

- collect best-effort `GIC` proxy rows
- write strategy characterization drafts

### Week 4

- run exit-pattern analysis
- implement lagged mirroring backtest
- implement sector-tilt backtest

### Week 5

- draft alpha-thesis memo
- define live monitoring view and update logic

## Immediate Task List

- [ ] Fill in disclosure map template for all three funds
- [ ] Freeze sector and industry taxonomy
- [ ] Decide benchmark set for each test
- [ ] Decide whether mirroring portfolios are equal-weight or value-weight
- [ ] Define confidence tiers for inferred `GIC` rows
- [ ] Define how to represent partial exits and threshold crossings
