# Common Sector Taxonomy

Phase 2 uses a shared 11-sector taxonomy so `PIF` and `NBIM` signals can be compared and combined without fund-specific labels leaking into strategy logic.

## Common Sectors

- `Communication Services`
- `Consumer Discretionary`
- `Consumer Staples`
- `Energy`
- `Financials`
- `Health Care`
- `Industrials`
- `Materials`
- `Real Estate`
- `Technology`
- `Utilities`

## Design Rules

- `PIF` sector labels remain preserved in the raw enriched tables.
- `NBIM` industry labels remain preserved in the raw summary tables.
- Combined strategies should use only the normalized `common_sector` field.
- Every many-to-one mapping is documented in `data/reference/common_sector_crosswalk.csv`.

## Important Non-Direct Mappings

### `PIF`

- `CONSUMER CYCLICAL -> Consumer Discretionary`
- `CONSUMER DEFENSIVE -> Consumer Staples`
- `FINANCIAL SERVICES -> Financials`
- `HEALTHCARE -> Health Care`
- `BASIC MATERIALS -> Materials`

### `NBIM`

- `Consumer Goods -> Consumer Staples`
- `Consumer Services -> Consumer Discretionary`
- `Oil & Gas -> Energy`
- `Telecommunications -> Communication Services`

These `NBIM` mappings intentionally follow the same sector-proxy choices already used in the validated `NBIM` ETF backtests.
