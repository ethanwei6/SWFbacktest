# `PIF` Sector Exposure And Change Layer

This method adds sector-aware aggregation on top of the existing `PIF` `13F` holdings and transition datasets so Phase 2 can compare `PIF` and `NBIM` on a shared directional dimension.

## Inputs

- `data/processed/pif/pif_13f_holdings.csv`
- `data/processed/pif/pif_13f_transition_events.csv`
- `data/processed/pif/pif_trade_calendar.csv`
- `data/reference/pif_sector_crosswalk.csv`

## Crosswalk Design

The sector crosswalk is keyed by `CUSIP`, not ticker, because the `PIF` research stack already treats `CUSIP` as the most stable identifier across issuer renames and mapping revisions.

Crosswalk fields:

- `pif_sector`
- `pif_industry`
- `sector_source`
- `confidence`
- `notes`

The current crosswalk is intentionally hybrid:

- `alpha_vantage_overview`
  - used where live `Alpha Vantage OVERVIEW` checks were available before rate limits bound
- `manual_symbol_review`
  - used for high-confidence common names where the sector is economically obvious
- `manual_issuer_review`
  - used for more obscure or delisted names where the mapping required explicit issuer review
- `manual_etf_review`
  - used for sector ETFs already explicit in the instrument identity
- `manual_spac_review`
  - used for shell / SPAC-like names where the underlying operating sector is not a clean economic exposure

## Outputs

Running:

```bash
python3 scripts/pif_sector_exposure_builder.py
```

produces:

- `data/processed/pif/pif_13f_holdings_sector_enriched.csv`
- `data/processed/pif/pif_13f_transition_events_sector_enriched.csv`
- `data/processed/pif/pif_sector_exposure_by_filing.csv`
- `data/processed/pif/pif_sector_change_by_filing.csv`
- `data/processed/pif/pif_sector_mapping_audit.csv`

## Exposure Table

`pif_sector_exposure_by_filing.csv` aggregates holdings within each `13F` report period by `sector` and `industry`.

Important baseline rule:

- sector aggregation is restricted to `sector_eligible_flag = 1`
- this keeps the Phase 2 sector layer aligned with the comparable common-equity sleeve
- excluded rows include calls, notes / `PRN` rows, and warrant-like lines such as `*W EXP ...`

Key fields:

- `as_of_date`
- `public_date`
- `trade_date`
- `sector`
- `industry`
- `holding_count`
- `mapped_holding_count`
- `total_market_value_usd`
- `portfolio_weight_after`

`portfolio_weight_after` is the sector weight inside the disclosed `PIF` `13F` sleeve for that report period.

## Change Table

`pif_sector_change_by_filing.csv` compares consecutive report periods and attaches sector-level event counts derived from the transition dataset.

Key fields:

- `period`
- `prev_as_of_date`
- `curr_as_of_date`
- `public_date`
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

Interpretation:

- `weight_before` / `weight_after` track disclosed sleeve composition
- `net_weight_change` captures slow-moving sector rotation
- event counts provide a second lens on how `PIF` is changing that sleeve internally

## Audit Rules

`pif_sector_mapping_audit.csv` is the validation gate for this step.

For each report period it records:

- row coverage
- market-value coverage
- any unmapped `CUSIP`s
- whether the filing had zero sector-eligible common-equity rows

Coverage is evaluated on the sector-eligible sleeve, not on excluded derivative / warrant / note rows.

Phase 2 should not proceed to combined strategy construction unless the mapping audit is effectively complete on that baseline sleeve.
