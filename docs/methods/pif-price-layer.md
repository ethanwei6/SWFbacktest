# PIF Price Layer Method

## Purpose

Build the audited price-input layer for `PIF` backtests.

This layer exists before portfolio simulation for one reason:

- a backtest is only as trustworthy as its identifier mapping and trade-date prices

So we separate the work into:

1. security master construction
2. price-request specification
3. raw price ingestion
4. price coverage audit

## Why Bloomberg-First

For this project, `PIF` prices should be sourced from `Bloomberg`, not a free web API.

Reason:

- `PIF` is a real-money mirroring test
- the portfolio contains common shares, ADRs, ADSs, and class-specific listings
- execution dates must line up exactly with valid market sessions
- identifier mapping errors would contaminate returns immediately

Free sources are useful for quick prototypes, but they are not the right baseline for this workflow.

## Step 3 Outputs

This step produces:

- a security master for every common-equity `PIF` name used in the baseline
- a Bloomberg request template
- a loader for normalized daily price history

Files:

- [`data/processed/pif/pif_price_security_master.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_price_security_master.csv)
- [`data/processed/pif/pif_price_request_template.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_price_request_template.csv)
- [`scripts/pif_price_master_builder.py`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/scripts/pif_price_master_builder.py)
- [`scripts/pif_bloomberg_price_loader.py`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/scripts/pif_bloomberg_price_loader.py)

## Baseline Security Universe

The price layer should start from:

- `PIF`
- common-equity baseline only
- rows where `common_equity_baseline_flag = 1`

This excludes:

- options
- diagnostic rows outside the baseline sleeve

## Security Mapping Rules

Each security should carry:

- `security_key`
- `issuer_name`
- `CUSIP`
- `title_of_class`
- `share_type`
- first and last signal dates
- first and last legal trade dates

Mapping priority:

1. `CUSIP`
2. Bloomberg ticker plus exchange, if needed
3. manual review notes for ambiguous ADR / ADS / class-share cases

## Raw Bloomberg Export Expectation

The preferred raw price file is a single CSV with one row per security-date and these columns:

- `price_identifier_type`
- `price_identifier_value`
- `date`
- `px_open`
- `px_last`
- `currency`
- `bbg_ticker`
- `bbg_security_name`

Recommended optional columns:

- `total_return_index_gross_dvds`
- `total_return_index_net_dvds`

## Validation Requirements

Before prices are used in a backtest:

- every mapped baseline security must have a price identifier
- every `trade_date` must have a valid close
- no security should have duplicate rows for the same date
- the price panel should surface any missing trade-date prices explicitly

## Important Modeling Choice

For the first `PIF` backtest:

- execution price should be next-trading-day `px_last`

This matches the current execution convention in the trade calendar:

- `signal_date` = filing/public date
- `trade_date` = next valid NYSE trading day strictly after the signal

## What This Step Does Not Do

This step does not yet:

- simulate trades
- compute returns
- decide weighting rules

It only prepares the exact price inputs needed to do those things correctly.
