# PIF 13F Dataset Method

## Objective

Build a clean, research-ready `PIF` public-equity dataset from `SEC Form 13F` filings.

This is the strongest quantitative public dataset for `PIF` because:

- it is structured
- it is recurring
- it has a standard disclosure lag
- it includes both market value and share count

## Source of Truth

Primary source:

- `SEC EDGAR` filings for `PUBLIC INVESTMENT FUND`
- filer `CIK = 0001767640`
- form types: `13F-HR` and, where relevant, `13F-HR/A`

Based on the SEC filing pages and the SEC Form 13F dataset documentation:

- the filing cover page gives `PERIODOFREPORT`, `FILING_DATE`, and manager metadata
- the information table gives one row per security holding
- standard fields include issuer, class, `CUSIP`, value, share count, discretion, and voting authority

## What This Dataset Represents

This dataset captures only:

- reportable `Section 13(f)` securities
- the disclosed US-reportable long book
- positions visible at the `13F` reporting cadence

It does not capture:

- non-US listed holdings outside `13F`
- private assets
- derivatives not represented in the filing
- the full `PIF` portfolio

## Raw File Contract

Store raw filing files in:

- [`data/raw/pif/13f/`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/raw/pif/13f/)

Recommended layout:

- one folder per filing accession number
- each folder should contain:
  - `primary_doc.xml`
  - `informationtable.xml`

Example:

- `data/raw/pif/13f/000101143824000215/primary_doc.xml`
- `data/raw/pif/13f/000101143824000215/informationtable.xml`

If EDGAR serves a different information-table filename for a filing, keep the original filename and do not rename it manually.

## Manual Download Procedure

For each `PIF` filing in EDGAR:

1. open the filing detail page
2. download the `primary_doc.xml`
3. download the XML version of the information table
4. save both inside a folder named with the accession number without dashes

Examples of `PIF` filing pages located during setup:

- `2023-12-31` report, filed `2024-02-14`: accession `0001011438-24-000215`
- `2024-03-31` report, filed `2024-05-15`: accession `0001011438-24-000359`

## Normalized Output

Primary output:

- [`data/processed/pif/pif_13f_holdings.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_13f_holdings.csv)

This should be one row per reported security per filing.

## Core Fields To Capture

From the SEC 13F documentation and XML structure:

- accession number
- filing date
- period of report
- filer `CIK`
- filer name
- issuer name
- title of class
- `CUSIP`
- value
- share count
- share/principal type
- put/call
- investment discretion
- other manager
- voting authority sole
- voting authority shared
- voting authority none

## Interpretation Rules

- use `filing_date` or first public date for investability timing, not `period_of_report`
- treat `13F-HR/A` carefully and prefer the amended filing when it supersedes an earlier filing
- because share count is present, period-to-period changes are much more informative here than in `NBIM`
- even here, filing lag still matters, so mirroring tests must trade after the filing became public

## Recommended Next Layers

After the holdings dataset is built:

1. transition dataset using share and value changes
2. filing-level summary
3. visual report similar to `NBIM`
4. lag-aware mirroring test
