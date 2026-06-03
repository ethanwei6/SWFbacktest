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

### Phase 7: Robustness and Attribution

- stress-test surviving strategies under delayed execution, costs, and caps
- decompose returns into exposure, allocation, and concentration effects
- formalize the cross-fund state model
- upgrade the monitoring and interactive layer around current state changes

Current progress:

- `A1` execution-lag sensitivity is complete for `P5`, `N4`, `N6`, and `S1`
- outputs are in [`data/processed/robustness/execution_lag_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/execution_lag_summary.csv), [`data/processed/robustness/execution_lag_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/execution_lag_daily.csv), and [`data/processed/robustness/execution_lag_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/execution_lag_audit.csv)
- baseline `T+1` reproduces the validated `P5`, `N4`, `N6`, and `S1` final NAVs exactly within floating-point tolerance
- the first robust read is that `S1` loses its modest excess versus `VT` under `T+3` and `T+5`, while `N4` and `N6` remain positive versus `VT`
- `A2` transaction cost sensitivity is complete for the same focus set
- outputs are in [`data/processed/robustness/cost_sensitivity_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/cost_sensitivity_summary.csv), [`data/processed/robustness/cost_sensitivity_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/cost_sensitivity_daily.csv), and [`data/processed/robustness/cost_sensitivity_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/cost_sensitivity_audit.csv)
- zero-cost reruns reproduce `P5`, `N4`, `N6`, and `S1` within floating-point tolerance, and all self-financing cost checks pass
- the current robust read is that `N4` and `N6` remain positive versus `VT` even at `50 bps`, while `S1` is roughly flat versus `VT` at `10 bps` and turns negative by `25 bps`
- `A3` concentration and exposure caps are complete for the same focus set
- outputs are in [`data/processed/robustness/concentration_cap_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/concentration_cap_summary.csv), [`data/processed/robustness/concentration_cap_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/concentration_cap_daily.csv), and [`data/processed/robustness/concentration_cap_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/concentration_cap_audit.csv)
- uncapped reruns reproduce `P5`, `N4`, `N6`, and `S1` within floating-point tolerance, and all rebalance-close cap-compliance checks pass
- the current robust read is that `N6` remains positive versus `VT` even under the tighter cap set, while `N4` and `S1` lose their excess once realistic caps are imposed; capped `P5` remains clearly negative versus `SPY`
- `A4` subperiod stability is complete for the same focus set
- outputs are in [`data/processed/robustness/subperiod_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/subperiod_summary.csv), [`data/processed/robustness/subperiod_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/subperiod_daily.csv), and [`data/processed/robustness/subperiod_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/subperiod_audit.csv)
- all subperiods pass minimum-row-count, date-order, and rebase-anchor checks
- the current stability read is that `N6` is the only focus-set strategy that stays positive versus `VT` in all three subperiods; `N4` is regime-dependent, while `P5` and `S1` are strong early but materially weaker in later windows
- a dedicated cross-step audit of `A1` through `A3` also passes cleanly with zero failed checks in [`data/processed/robustness/phase3_robustness_audit.json`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/phase3_robustness_audit.json) and [`data/processed/robustness/phase3_robustness_audit_checks.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/phase3_robustness_audit_checks.csv)
- `A5` benchmark robustness is complete for the same focus set
- benchmark inputs are in [`data/processed/robustness/benchmark_series_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/benchmark_series_daily.csv) and [`data/processed/robustness/benchmark_series_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/benchmark_series_audit.csv)
- strategy-vs-benchmark outputs are in [`data/processed/robustness/benchmark_comparison_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/benchmark_comparison_summary.csv), [`data/processed/robustness/benchmark_comparison_daily.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/benchmark_comparison_daily.csv), and [`data/processed/robustness/benchmark_comparison_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/robustness/benchmark_comparison_audit.csv)
- all benchmark comparisons pass minimum-row-count, date-order, and rebase-anchor checks
- the current benchmark-robustness read is that `P5` remains clearly negative against both `SPY` and `QQQ`, `N4` and `N6` remain positive against both `VT` and `ACWI`, and `S1` is only positive versus `VT` while remaining negative against both `SPY` and the blended `VT`/`SPY` benchmark
- `B1` return decomposition is complete for the same focus set
- outputs are in [`data/processed/attribution/strategy_return_decomposition.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/strategy_return_decomposition.csv), [`data/processed/attribution/daily_excess_return_decomposition.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/daily_excess_return_decomposition.csv), and [`data/processed/attribution/strategy_decomposition_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/strategy_decomposition_audit.csv)
- all daily and total decomposition reconciliation checks pass with zero failed rows
- the current attribution read is that `N6` is driven mainly by broad allocation rather than concentration, `N4` relies heavily on concentration in the winning sleeves, `S1` gives up much of its edge to cash drag, and `P5` is hurt primarily by concentration rather than by cash alone
- `B2` event-window analysis is complete for the validated signal families
- outputs are in [`data/processed/attribution/event_window_forward_returns.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/event_window_forward_returns.csv), [`data/processed/attribution/event_window_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/event_window_summary.csv), and [`data/processed/attribution/event_window_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/event_window_audit.csv)
- the event-window audit passes cleanly with `592` passes, `0` failures, and only `4` expected end-of-sample skips for incomplete forward horizons
- the event-window layer now includes unconditional proxy baselines for the same horizon, so conditional returns can be compared against ordinary market or sector drift rather than only against cash or `VT`
- the current signal-level read is that `PIF expanding` and `PIF contracting` are both followed by positive absolute `SPY` returns and both also exceed unconditional `SPY` drift, but `expanding` is stronger than `contracting`; this still weakens the idea that `PIF` regime changes are a clean directional market-timing edge on their own
- `NBIM` positive industry-weight-change events are only mildly positive in aggregate, but technology and energy are the strongest six-month sector-level winners, which is directionally consistent with the stronger `N6` and tech-heavy `NBIM` conclusions
- cross-fund consensus gained events are modestly positive at the family level, but consensus lost events are not reliably negative, so the signal appears more useful as a selective confirmation overlay than as a clean short or de-risk trigger
- `B3` window hit-rate and contribution analysis is complete for the same focus set
- outputs are in [`data/processed/attribution/window_hit_rate_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/window_hit_rate_summary.csv), [`data/processed/attribution/top_bottom_windows.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/top_bottom_windows.csv), and [`data/processed/attribution/window_hit_rate_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/attribution/window_hit_rate_audit.csv)
- all rebalance-window checks pass, and the summed window contribution deltas reconcile exactly to the final relative-excess NAV for every focus-set strategy
- the current breadth read is that `N6` is the broadest surviving effect, with a `63.6%` benchmark-beating hit rate and a lower positive-contribution concentration (`HHI 0.189`) than `N4`
- `N4` still works, but the contribution profile is noticeably more concentrated, with the top three positive windows contributing about `82.5%` of total positive contribution
- `P5` is highly concentrated and unstable at the window level, with only a `39.1%` hit rate and a very large share of positive contribution coming from a few windows
- `S1` has a relatively diffuse contribution profile, but too many small losing windows and too little net excess, which fits the earlier cash-drag interpretation
- `C1` through `C3` state-model work are complete on top of the validated combined signal layer
- outputs are in [`data/processed/signals/swf_state_model.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/signals/swf_state_model.csv), [`data/processed/signals/state_segments.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/signals/state_segments.csv), [`data/processed/signals/state_duration_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/signals/state_duration_summary.csv), [`data/processed/signals/state_forward_returns.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/signals/state_forward_returns.csv), [`data/processed/signals/state_forward_return_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/signals/state_forward_return_summary.csv), and their audit files
- the state-model audit passes with `114` rows and `0` failures, while the forward-return audit passes with `105` realized windows, `0` failures, and only `9` expected skips from pre-benchmark or end-of-sample horizons
- the compact state table contains `38` state dates and `27` state changes; `NBIM` sector posture is `consensus_led` on `19` dates, `overweight_led` on `17`, and `top3_led` on only `2`
- `risk_on` states are shorter lived than `neutral` and `risk_off` states, while `Technology` is the dominant primary tilt, appearing on `21` of `38` dates
- the current allocator read from the state-forward layer is that `risk_on` plus technology-led states are the most constructive combination, `risk_off` does not imply weak `SPY` on its own, and communication-services-led states are rare but strongly sector-specific rather than broad market-timing signals
- a formal inference layer is now complete for the focus-set strategy-versus-benchmark timelines
- outputs are in [`data/processed/inference/strategy_statistical_tests_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/strategy_statistical_tests_summary.csv), [`data/processed/inference/strategy_statistical_tests_series.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/strategy_statistical_tests_series.csv), and [`data/processed/inference/strategy_statistical_tests_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/strategy_statistical_tests_audit.csv)
- all statistical-test audit rows pass, and every inference summary row reconciles exactly to the validated benchmark-comparison totals
- the current inference read is that no focus-set strategy clears a strong conventional significance threshold; `N6` remains the best empirical survivor but its annualized-excess bootstrap interval still crosses zero
- event-window confidence intervals are now complete in [`data/processed/inference/event_window_inference_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/event_window_inference_summary.csv) and [`data/processed/inference/event_window_inference_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/event_window_inference_audit.csv)
- the event-window interval read is that family-level six-month effects remain directionally interesting but statistically soft, because all unconditional-adjusted family confidence intervals still overlap zero
- turnover-adjusted Sharpe and information metrics are now complete in [`data/processed/inference/turnover_adjusted_metrics.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/turnover_adjusted_metrics.csv) and [`data/processed/inference/turnover_adjusted_metrics_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/turnover_adjusted_metrics_audit.csv)
- the turnover-adjusted read is that `N6` has the strongest net information ratio and the lowest trading burden among the surviving positive strategies, while `S1` turns slightly negative on a turnover-adjusted information basis even at `10 bps`
- the final model-expression decision is now documented in [`data/processed/inference/final_model_expression.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/inference/final_model_expression.csv) and [`docs/methods/final-model-expression.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/methods/final-model-expression.md)
- no new hybrid production strategy was added; the project now explicitly narrows to `N6` as the strongest residual investable sleeve and the cross-fund state model as the preferred monitoring abstraction
- a full-project code-path audit is now complete in addition to the Phase 3 audits; it rechecked the original processing and baseline backtests from raw inputs forward, found two real historical `PIF` engine bugs (same-day bundle handling in `P2`/`P3`/`P4` and epsilon-scale ghost positions in `P5`), and those fixes are now reflected in the active final outputs
- `Workstream D1` is now complete via [`data/processed/monitoring/signals_latest.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/monitoring/signals_latest.csv), [`state_latest.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/monitoring/state_latest.csv), and [`model_targets_latest.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/monitoring/model_targets_latest.csv)
- the latest validated state is `2026-05-18`: `PIF` is `neutral`, `NBIM` is `overweight_led`, the primary sector tilt is `Technology`, the state-model exposure target is `0.75`, and the accepted production sleeve remains the equal-weight `N6` basket of `Technology`, `Financials`, and `Consumer Discretionary`
- the existing advanced `PIF` interactive explorer has now been upgraded for interpretation rather than monitoring: it includes a strategy rulebook, a clickable filing-step rail, and a filing-by-filing explanation panel, and its initial state plus first-step interaction were verified through headless Chrome renders against the local file

Current next-step plan:

- see [`docs/phase3-plan.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/phase3-plan.md)

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

## Phase 2 Direction

Current recommendation:

- prioritize a combined `PIF + NBIM` signal model before widening to more sovereign funds
- treat `PIF` as the stronger `exposure regime` signal
- treat `NBIM` as the stronger `slow-moving sector posture` signal
- test whether cross-fund confirmation improves results more than either standalone signal

Reference:

- detailed execution plan in [`docs/phase2-plan.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/phase2-plan.md)

Immediate Phase 2 build order:

1. `PIF` sector exposure and sector change tables
2. common `PIF/NBIM` sector taxonomy and crosswalk
3. combined signal panel and signal-state table
4. first three combined strategies:
   - `S1` exposure regime overlay
   - `S2` cross-fund consensus sector tilt
   - `S3` `PIF` cash-aware base plus `NBIM` sector overlay
5. validation gates before interpretation

Extension priority after Phase 2:

- `Mubadala` first if broadening to another SWF
- `Temasek` second only after filing-entity consistency review
- not `ADIA` or `GIC` for the next quantitative expansion
