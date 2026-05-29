# PIF Twelve Data Price Layer

## Decision

Use `Twelve Data` as the free API-backed price source for the first `PIF` backtest build.

We considered `Massive` (formerly `Polygon.io`), but its free stock tier currently provides only `2 years` of historical stock data, which is not enough for a `PIF` history that begins in `2019`.

## Why Twelve Data

`Twelve Data` is the best free fit for this stage because:

- the free plan supports API access
- daily historical prices are available through `/time_series`
- the API supports explicit price adjustment modes:
  - `none`
  - `splits`
  - `dividends`
  - `all`
- US equities are included on the free plan

## What We Need From It

For `PIF`, we need two things:

1. a reliable symbol map from our `13F` securities into tradeable US tickers
2. daily price history covering each legal `trade_date`

## Build Order

### Step 3A: Candidate Mapping

Generate ticker candidates from `Twelve Data` symbol search using the `PIF` security master.

Outputs:

- [`data/processed/pif/pif_twelvedata_mapping_candidates.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_mapping_candidates.csv)
- [`data/processed/pif/pif_twelvedata_security_map.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_security_map.csv)

This step does not assume the top search result is always correct.

### Step 3B: Price Fetch

Fetch daily prices from `/time_series` for every approved mapped symbol.

Baseline recommendation:

- first fetch `adjust=none` for trade-date execution accuracy
- optionally fetch `adjust=all` as a second pass for total-return analysis

Outputs:

- [`data/processed/pif/pif_twelvedata_daily_prices.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_daily_prices.csv)
- [`data/processed/pif/pif_twelvedata_price_coverage_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_twelvedata_price_coverage_audit.csv)

## Mapping Philosophy

We should not trust name matching blindly.

The mapping workflow therefore:

- preserves `security_key`
- keeps `CUSIP`
- stores the chosen `Twelve Data` symbol
- records whether the mapping was auto-suggested or manually approved

This matters because:

- ADR / ADS names can be tricky
- company names change over time
- class-share issues can produce multiple valid-looking candidates

## Execution-Price Principle

For the first backtest, we care most about getting the execution date and daily close correct.

So the first required series is:

- `interval=1day`
- `adjust=none`

We can layer in adjusted-return logic after the raw trade-date coverage is verified.

## Rate-Limit Reality

`Twelve Data` free usage is credit-limited, so the scripts are written conservatively and may take time to run.

That is acceptable.

For this project, slower and auditable is better than fast and sloppy.
