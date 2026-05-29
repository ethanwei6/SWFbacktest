# PIF Bloomberg Price Inputs

Drop raw `Bloomberg` price exports for `PIF` here.

## Recommended Files

### 1. Security Mapping File

Suggested filename:

- `pif_bloomberg_security_map.csv`

Suggested columns:

- `security_key`
- `cusip`
- `issuer_name`
- `bbg_ticker`
- `bbg_unique_id`
- `price_identifier_type`
- `price_identifier_value`
- `mapping_status`
- `mapping_notes`

### 2. Daily Historical Price File

Suggested filename:

- `pif_bloomberg_daily_prices.csv`

Required columns:

- `price_identifier_type`
- `price_identifier_value`
- `date`
- `px_open`
- `px_last`
- `currency`
- `bbg_ticker`
- `bbg_security_name`

Optional columns:

- `total_return_index_gross_dvds`
- `total_return_index_net_dvds`

## Notes

- Keep the raw files untouched after export.
- Use one row per security-date.
- Export the baseline common-equity universe first before adding option rows.
