# Research Design

## Core Question

Do sovereign wealth fund disclosures contain investable information after accounting for:

- reporting lag
- partial visibility
- disclosure asymmetry across funds
- the long-duration mandate and patient positioning of sovereign investors

## Hypotheses

### `H1` Lagged Mirroring

A portfolio that mirrors newly disclosed sovereign wealth fund positions after they become public outperforms a relevant benchmark on a risk-adjusted basis.

### `H2` Sector Tilt

A portfolio that overweights sectors and industries where sovereign wealth funds are accumulating exposure outperforms a relevant benchmark, even when single-name mirroring does not.

### `H3` Exit Timing

Observable exit patterns are structured enough to help avoid stale mirroring trades or improve timing around disclosure-driven crowding.

## Research Principle

All investability tests must use the first realistic public availability date of the information, not the position's economic effective date.

This is the central protection against overstated results.

## Scope

### In Scope

- `GPFG`, `PIF`, `GIC`
- public equity holdings and large-holder disclosures
- sector and industry concentration analysis
- exit characterization where data allows
- monitoring logic for new public disclosures

### Out of Scope for Main Backtest

- private-market fund investments
- infrastructure and real estate positions lacking tradable public proxies
- undisclosed derivatives exposures
- any assumption that non-disclosure implies no position

Private and co-investment activity can still be used in the qualitative strategy write-up.

## Fund Treatment

### `GPFG`

- treat as high-coverage, low-timeliness
- best for breadth and strategic allocation analysis
- weaker for short-horizon timing tests

### `PIF`

- treat as partial-coverage, moderate-timeliness within the US listed long book
- strongest candidate for single-name lagged mirroring tests
- not representative of total fund positioning

### `GIC`

- treat as event-driven, inferred, and structurally incomplete
- use primarily for sectoral and ownership-pattern observations
- avoid overclaiming in single-name alpha tests unless sample quality is strong
- exclude from the initial backtest panel unless a later proxy build produces sufficient coverage and consistency

## Data Layers

### Layer 1: Observed Holdings

Holdings disclosed directly through fund-level or regulatory filings.

Examples:

- `NBIM` holdings disclosures
- `SEC 13F`
- `SEC 13D/G`

### Layer 2: Inferred Exposure

Exposure reconstructed from threshold filings, co-investment announcements, and deal press.

Examples:

- `FCA TR-1`
- `HK DI`
- `EDINET`
- transaction announcements

### Layer 3: Qualitative Context

Mandates, strategy language, management commentary, and press around strategic themes.

## Disclosure Mapping Framework

For each source, capture:

- source name
- fund
- instrument coverage
- geography coverage
- cadence
- lag
- disclosure threshold
- historical depth
- machine-readability
- quantitative usability
- known blind spots

## Holdings Normalization Rules

- preserve source-native identifiers where possible
- map issuers to a common security master
- store both `as_of_date` and `public_date`
- compute `staleness_days`
- classify rows as `observed` or `inferred`
- classify visibility as `full`, `partial`, `event-driven`, or `inferred`
- assign confidence scores to proxy-based rows

## Exit Analysis Framework

Track separately:

- first observable appearance
- last observable appearance
- increase events
- decrease events
- threshold-crossing events
- disappearance events

Do not equate:

- disappearance from a partial dataset with true exit
- first disclosure with economic initiation

## Backtest Design

### Test A: Lagged Mirroring

Construct portfolios from newly public positions only after disclosure.

Variants:

- equal-weight
- value-weight when position value is available
- fixed holding windows
- rebalance at each disclosure cycle

Benchmarks should match the tradable universe:

- broad US benchmark for `13F`-based tests
- appropriate global or regional benchmark for `GPFG` holdings tests

### Test B: Sector Accumulation

Infer sector signals from:

- rising disclosed weights
- repeated new positions within a sector
- large-holder appearances clustering in a sector

Test whether those sector tilts outperform simple benchmark exposures after disclosure.

## Minimum Reporting Standards

Every result should state:

- underlying source set
- visibility limitations
- effective sample size
- lag assumption
- benchmark used
- whether the result is fund-specific or pooled

## Expected Outcome Shape

Most likely outcomes:

- `PIF` may support a cleaner but narrow lagged mirroring test
- `GPFG` may be more useful for structural sector and geography signals than timing
- `GIC` may be strongest as a qualitative and proxy-monitoring case rather than a clean alpha source

The final answer may be that any edge is stronger at the sector level than at the single-name level.

## Current Backtest Scope Decision

The initial quantitative backtests should use:

- `PIF` for lagged mirroring of the reported `13F` sleeve
- `NBIM` for slow-moving portfolio, concentration, and sector-tilt tests

`GIC` should remain part of the project as a disclosure-asymmetry and qualitative strategy case, but should not be forced into the initial backtest panel without a credible, sufficiently broad public proxy dataset.
