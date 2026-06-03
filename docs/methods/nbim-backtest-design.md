## NBIM Backtest Design

### Objective

Test whether public `NBIM` equity disclosures contain investable signal once the disclosure lag is respected. The design separates:

- `direct mirroring` of a small, investable subset of disclosed holdings
- `industry-following` strategies using liquid sector ETF proxies

This is intentionally narrower than the `NBIM` holdings dataset itself. The official dataset contains more than `16,000` unique issuer-country observations across snapshots, which is too broad to price honestly with a free single-name API. The backtest therefore focuses on:

- a `core US mirror sleeve` of the largest recurring US-listed holdings
- `industry ETF` expressions of `NBIM`’s slow-moving sector allocation

### Source Data

- Holdings panel: `data/processed/nbim/nbim_public_equity_holdings.csv`
- Transition events: `data/processed/nbim/nbim_transition_events.csv`
- Snapshot industry summary: `data/processed/nbim/nbim_snapshot_industry_summary.csv`
- Transition industry summary: `data/processed/nbim/nbim_transition_industry_summary.csv`
- Public date map: `data/processed/nbim/nbim_public_date_map.csv`

### Disclosure Timing Rule

`NBIM` holdings are not traded on the `as_of_date`. They become usable only after public release.

Because the selected price source is monthly adjusted data from Alpha Vantage, the execution convention is:

- `signal_date = public_date`
- `trade_date = first available month-end strictly after signal_date`

This is conservative. For example, a report published on `27 February 2024` is first tradable in the backtest at the next month-end observation, `29 February 2024` if the monthly series includes it, otherwise the next monthly bar after publication.

### Benchmark

Use `VT` (`Vanguard Total World Stock ETF`) as the primary benchmark because:

- `NBIM` is a global equity owner
- `SPY` is too US-centric for this dataset

### Price Frequency

Use `TIME_SERIES_MONTHLY_ADJUSTED` from Alpha Vantage.

Rationale:

- the free Alpha Vantage key supports monthly adjusted history
- the free key does not provide a practical daily adjusted route for this universe
- `NBIM` itself is disclosed at annual and half-year intervals, so monthly frequency is sufficiently aligned for a first-pass lagged backtest

### Direct Mirror Universe

The direct mirror backtests use a manually bounded `core US mirror universe` in:

- `data/processed/nbim/nbim_core_us_mirror_universe.csv`

This universe captures the largest recurring US-listed holdings and approximates the part of the portfolio that can be mirrored most cleanly with free API coverage. It is not a claim to fully reproduce the `NBIM` book.

Important validation note:

- the direct mirror sleeve is useful as an exploratory reference case
- it is not clean alpha evidence because the bounded universe itself is biased toward recurring secular winners
- later reporting should treat the direct mirror family as exploratory, and focus the main alpha discussion on the industry-based strategies

### Industry Proxy Map

`NBIM` industries are mapped to liquid US sector ETFs in:

- `data/processed/nbim/nbim_industry_etf_map.csv`

These ETFs are implementation proxies, not one-for-one representations of `NBIM`’s global industry book.

### Strategies

#### N1: Core US Mirror Equal Weight

- Universe: `core US mirror universe`
- At each public disclosure, select names present in the current snapshot
- Weight selected names equally
- Rebalance on the first tradable month-end after public release
- Hold until the next rebalance

Purpose:

- test whether a simple lagged mirror of `NBIM`’s disclosed US mega-cap exposure carries alpha

#### N2: Core US Mirror NBIM Weight

- Universe: `core US mirror universe`
- At each public disclosure, select names present in the current snapshot
- Weight by normalized `NBIM` market value within the selected universe
- Rebalance on the first tradable month-end after public release

Purpose:

- test whether preserving the disclosed relative sizing of the mirror sleeve performs better than equal-weighting it

#### N3: Industry Weight Mirror

- Universe: mapped sector ETFs
- Convert each snapshot’s industry weights into ETF weights
- Aggregate multiple `NBIM` industry labels onto the same ETF where needed
- Normalize ETF weights to `100%`
- Rebalance on the first tradable month-end after public release

Purpose:

- test whether `NBIM`’s broad industry posture contains investable information even when single-name mirroring does not

#### N4: Industry Weight-Change Tilt

- Universe: mapped sector ETFs
- Compare each snapshot’s industry weight to the previous snapshot
- Keep only industries with positive weight delta
- Allocate across the positive-delta industries proportional to weight increase
- If no industry has positive delta, hold cash until the next signal

Purpose:

- test whether following `NBIM`’s disclosed industry rotation is more informative than copying the full industry book

#### N5: Industry Accumulation Tilt

- Universe: mapped sector ETFs
- Use transition summary by industry
- Score each industry by `likely_accumulation - likely_reduction`
- Keep only positive-score industries
- Allocate proportionally to positive scores
- If no industry has positive score, hold cash until the next signal

Purpose:

- test whether ownership-based transition signals are stronger than level-based industry weights

#### N6: Top-3 Industry Leaders

- Universe: mapped sector ETFs
- At each snapshot, select the three largest disclosed `NBIM` industries after ETF aggregation
- Weight the selected ETFs equally

Purpose:

- test whether a concentrated version of `NBIM`'s broad industry posture is more investable than the full mirror

#### N7: Top-3 Industry Increases

- Universe: mapped sector ETFs
- At each snapshot, compare industry weights to the prior snapshot
- Select the three largest positive industry weight changes
- Weight the selected ETFs equally

Purpose:

- test whether a simpler and more focused version of the industry-rotation idea works better than weighting every positive sector

#### N8: Consensus Rotation Tilt

- Universe: mapped sector ETFs
- Require both:
  - positive disclosed industry weight change
  - positive accumulation-minus-reduction transition score
- Select up to the top three confirmed sectors and weight them by combined signal strength

Purpose:

- test a higher-conviction version of the sector rotation thesis that only acts when level and transition signals agree

### Output Structure

The `NBIM` backtests follow the same pattern as the `PIF` work:

- detailed per-strategy backtest folders
- benchmark-relative analysis tables
- SVG chart pack
- HTML and Markdown research reports

### Known Limitations

- direct mirroring is only for a bounded, investable subset of the full `NBIM` book
- ETF proxies are US-sector implementations of a global portfolio
- the monthly trade convention introduces additional lag relative to an ideal daily execution framework
- the `NBIM` taxonomy changes slightly across time, so some legacy industry labels are merged to modern sector proxies
