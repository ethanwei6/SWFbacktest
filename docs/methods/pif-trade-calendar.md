# PIF Trade Calendar Method

## Purpose

Convert the `PIF` signal panel into an audited trade calendar that defines:

- the disclosure date
- the next valid NYSE trading date after disclosure
- bundle handling
- stale-filing flags

This is the final step before attaching prices.

## Execution Convention

Baseline convention:

- `signal_date` = first public date of the filing
- `trade_date` = next valid NYSE trading day strictly after `signal_date`

We intentionally use the day after disclosure rather than same-day trading to avoid:

- assuming intraday awareness
- same-day fill ambiguity
- same-day close execution assumptions

## Exchange Calendar

The trade calendar should use NYSE full-day market closures, not just weekdays.

For this project period, that includes:

- standard NYSE holidays
- Good Friday
- Juneteenth where applicable
- observed Independence Day / Christmas rules
- the special NYSE closure on `2025-01-09` for the National Day of Mourning for President Jimmy Carter

## Same-Day Multi-Filing Bundles

When multiple `PIF` report periods become public on the same date:

- all signals share the same `trade_date`
- the bundle is flagged
- no trade should be simulated until the entire bundle is processed together

## Stale-Filing Flags

The trade calendar should classify each signal date into:

- `normal_staleness`
- `stale_bundle`
- `very_stale_bundle`

Suggested cutoffs:

- normal: `<= 60` days
- stale: `61-180` days
- very stale: `> 180` days

These are for robustness analysis, not for deleting data from the baseline by default.

## Outputs

- [`data/processed/pif/pif_trade_calendar.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar.csv)
- [`data/processed/pif/pif_trade_calendar_audit.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_trade_calendar_audit.csv)

## Why This Matters

Once prices are added, any date mistake becomes a return mistake.

So this layer should answer, with no ambiguity:

- what date the market first knew the information
- what date we are allowed to simulate the trade
- whether the signal belongs to a normal filing or a delayed disclosure bundle
