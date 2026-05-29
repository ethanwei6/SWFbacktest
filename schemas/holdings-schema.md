# Holdings Schema

Normalized row design for sovereign wealth fund holdings and inferred exposure events.

## Entity Fields

| Field | Type | Description |
| --- | --- | --- |
| `fund` | string | `GPFG`, `PIF`, `GIC` |
| `issuer_name` | string | Parent issuer or operating company |
| `security_name` | string | Listed security name |
| `ticker` | string | Exchange ticker if available |
| `isin` | string | International security identifier |
| `cusip` | string | US security identifier if available |
| `sedol` | string | UK/global security identifier if available |
| `asset_type` | string | Common equity, ADR, preferred, etc. |
| `listing_country` | string | Country of listing venue |
| `issuer_country` | string | Country of issuer domicile |
| `exchange` | string | Trading venue if known |

## Classification Fields

| Field | Type | Description |
| --- | --- | --- |
| `sector` | string | Standardized sector |
| `industry` | string | Standardized industry |
| `theme` | string | Optional strategic theme tag |
| `position_type` | string | Long equity, strategic stake, threshold filing, etc. |

## Position Fields

| Field | Type | Description |
| --- | --- | --- |
| `shares` | number | Shares disclosed if available |
| `market_value_local` | number | Local-currency market value if available |
| `market_value_usd` | number | USD-normalized market value if available |
| `portfolio_weight` | number | Weight in disclosed portfolio if available |
| `ownership_pct` | number | Percent ownership if disclosed |

## Timing Fields

| Field | Type | Description |
| --- | --- | --- |
| `as_of_date` | date | Economic date of the holding snapshot or filing status |
| `public_date` | date | First date the information became public |
| `filing_date` | date | Date the filing or announcement was submitted |
| `effective_date` | date | Event date if separately stated |
| `staleness_days` | integer | `public_date - as_of_date` in days |

## Provenance Fields

| Field | Type | Description |
| --- | --- | --- |
| `disclosure_channel` | string | `NBIM`, `13F`, `13D/G`, `TR-1`, `HK DI`, `EDINET`, press, etc. |
| `source_name` | string | Specific document or page title |
| `source_url` | string | URL or document location |
| `jurisdiction` | string | Filing jurisdiction |
| `visibility_class` | string | `full`, `partial`, `event-driven`, `inferred` |
| `observability` | string | `observed` or `inferred` |
| `confidence_level` | string | `high`, `medium`, `low` |

## Event Fields

| Field | Type | Description |
| --- | --- | --- |
| `event_type` | string | `new`, `increase`, `decrease`, `exit`, `threshold-cross`, `snapshot` |
| `entry_signal` | boolean | Marks first observable appearance under current rules |
| `exit_signal` | boolean | Marks observable disappearance or threshold-based exit event |
| `event_notes` | string | Short explanation of inference or classification |

## Recommended Derived Fields

| Field | Type | Description |
| --- | --- | --- |
| `security_key` | string | Internal unique security key |
| `fund_security_key` | string | Composite key for fund-security history |
| `holding_window_days` | integer | Days between observable entry and exit |
| `source_priority` | integer | Ranking for deduplication and conflict resolution |
| `sample_eligible_flag` | boolean | Whether row is eligible for a given backtest |

## Design Rules

- always retain both `as_of_date` and `public_date`
- never use `as_of_date` alone for investability analysis
- keep `GIC` inferred rows in the same schema, but do not imply they are equivalent to full disclosed holdings
- store source-native detail in notes rather than dropping ambiguity
- deduplicate only after assigning source priority rules
