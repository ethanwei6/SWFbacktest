# NBIM Public Equity Dataset Method

## Objective

Build the first fund-level dataset for `NBIM` / `GPFG` public equity holdings using the official historical holdings database described by `NBIM`.

## Source of Truth

Primary source:

- `NBIM` historical holdings database exposed through the `GPFG_HOLDINGS_PUBLIC` table described on the official holdings-data terms page

Source characteristics from `NBIM`:

- year-end snapshots
- history since `1998`
- includes equity, fixed income, real estate, and infrastructure in the same table
- equity and fixed income are grouped by issuer and asset class

For this first dataset build, keep only:

- `ASSET_CLASS = 'EQ'`

## First Dataset Scope

### In Scope

- all historical `NBIM` public equity rows from the official holdings database
- one row per issuer-year from the public database
- year-end holdings history from `1998` onward

### Out of Scope

- fixed income
- real estate
- renewable infrastructure
- intra-year updates from the website search view
- security-level reconstruction beyond the issuer-level granularity provided by the official database

## Expected Raw Columns

From the official table description, the usable fields for equity rows are:

- `INT_ID`
- `ASSET_CLASS`
- `DATE`
- `REGION`
- `COUNTRY`
- `COMPANY_NAME_ISSUER_NAME`
- `MARKET_VALUE_NOK`
- `MARKET_VALUE_USD`
- `INDUSTRY`
- `VOTING`
- `OWNERSHIP`
- `INCORPORATION_COUNTRY`

## Raw File Contract

Store the unmodified exports in:

- [`data/raw/nbim/`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/raw/nbim/)

Expected filename pattern:

- `eq_YYYYMMDD.csv`

Example:

- `eq_20241231.csv`
- `eq_20231231.csv`

Requirements:

- direct export from the official source
- no manual edits
- UTF-8 encoding if possible
- semicolon-delimited files are acceptable
- keep original column names
- include all years available
- the date must remain embedded in the filename

Add a sidecar metadata note at:

- [`data/raw/nbim/README.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/raw/nbim/README.md)

## Observed Raw Shape

Based on the current downloaded sample, the raw files contain headers like:

- `Region`
- `Country`
- `Name`
- `Industry`
- `Market Value(NOK)`
- `Market Value(USD)`
- `Voting`
- `Ownership`
- `Incorporation Country`

Notable implications:

- the file does not currently include a `DATE` column, so snapshot date must be inferred from the filename
- the delimiter is `;`
- percentages arrive as strings like `3%` or `1.35%`
- issuer name is in `Name`, not `COMPANY_NAME_ISSUER_NAME`

## Normalized Output

Store the cleaned fund-level dataset as:

- [`data/processed/nbim/nbim_public_equity_holdings.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_public_equity_holdings.csv)

## Field Mapping

| Raw Field | Normalized Field | Notes |
| --- | --- | --- |
| filename date | `as_of_date` | inferred from `eq_YYYYMMDD` |
| filename date | `public_date` | initially same as `as_of_date` only as a placeholder until we map actual publication timing rules per year |
| `Name` | `issuer_name` | issuer-level name from source |
| `COUNTRY` | `issuer_country` | source country field |
| `Country` | `issuer_country` | source country field |
| `Incorporation Country` | `incorporation_country` | preserve separately |
| `Region` | `region` | source region |
| `Industry` | `industry` | source industry |
| `Market Value(NOK)` | `market_value_nok` | numeric |
| `Market Value(USD)` | `market_value_usd` | numeric |
| `Ownership` | `ownership_pct` | strip `%` |
| `Voting` | `voting_pct` | strip `%` |
| synthetic | `source_row_id` | generated from file date plus row number |

Add normalized constants:

- `fund = 'GPFG'`
- `source_name = 'NBIM GPFG_HOLDINGS_PUBLIC'`
- `disclosure_channel = 'NBIM_HOLDINGS_DB'`
- `asset_type = 'public_equity'`
- `position_type = 'long_equity'`
- `visibility_class = 'full'`
- `observability = 'observed'`
- `confidence_level = 'high'`
- `event_type = 'snapshot'`

## Important Caveat On Public Date

The source page clearly says the database provides holdings at year-end from the start of the fund. It does not, on its own, fully specify the historical first-public-availability timestamp for every year.

So for the first build:

- load `as_of_date` exactly from the source
- preserve a nullable or provisional `public_date`
- do not use this dataset for alpha backtesting until the publication-date rule is confirmed

This protects us from overstating investability.

## Initial Quality Checks

After loading, verify:

- all filenames match `eq_YYYYMMDD`
- all inferred dates are valid dates
- year coverage matches the downloaded file set
- no duplicate `source_row_id`
- `market_value_nok` and `market_value_usd` are numeric
- `ownership_pct` and `voting_pct` are parseable percentages
- empty incorporation country values are handled cleanly

## Next Step After Raw Load

Once the raw export is available, build:

1. a small loader to normalize column names and types
2. a year-level coverage summary
3. top-holdings and concentration checks to confirm the dataset looks sane
