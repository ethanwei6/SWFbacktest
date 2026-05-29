# Disclosure Map

As of `2026-05-28`.

## Summary View

| Fund | Transparency Profile | Main Public Channels | Best Quantitative Use | Core Limitation |
| --- | --- | --- | --- | --- |
| `GPFG` / `NBIM` | high transparency, low timeliness | `NBIM` all-investments view, `NBIM` historical holdings data, annual report, `SEC 13F` | broad portfolio characterization and long-horizon ownership analysis | full-history public data is not reported on a quarter-end tradable cadence across the full portfolio |
| `PIF` | partial transparency, moderate timeliness in the US sleeve | `SEC 13F`, occasional `SEC 13D/G`, deal and co-investment press | cleanest lagged mirroring test for disclosed US long equity positions | only covers reportable US `13F` securities, not the full portfolio |
| `GIC` | low transparency, mostly inferred | annual report, portfolio mix pages, regulatory large-holder filings, deal press | strategy characterization and best-effort proxy monitoring | no full public holdings list; single-name history is sparse and event-driven |

## `GPFG` / `NBIM`

### Fund Summary

- Fund: Norway Government Pension Fund Global
- Mandate: global long-term reserve fund managed by `NBIM`
- Transparency profile: strongest of the three funds
- Best quantitative use: sector, geography, concentration, and long-horizon holding analysis
- Main blind spots: disclosure timing is still too slow for naive “copy immediately” assumptions

### Source Inventory

| Fund | Source | Channel | Coverage | Geography | Cadence | Lag | Threshold / Trigger | Historical Depth | Quantitative Use | Main Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GPFG` | `All investments` page | `NBIM` website | fund investments searchable by country, asset class, and sector | global | updated twice a year | semiannual public refresh | none; fund-level publication | available since 1998 per `NBIM` | useful for public holdings lookup and monitoring snapshots | not a clean quarter-end research feed; timing weaker than `13F` |
| `GPFG` | historical holdings database | `NBIM` holdings data / Snowflake terms page | equity, fixed income, real estate, renewable infrastructure; grouped by issuer and asset class for equity and fixed income | global | year-end | year-end snapshot | none; fund-level publication | since 1998 | strongest source for normalized long-run holdings history | annual snapshot is slow for trading tests |
| `GPFG` | annual report | `NBIM` annual report | strategy, top positions, listed and unlisted mix, ownership tables | global | annual | annual | none | multi-year | strong qualitative and summary quantitative context | not security-complete in a backtest-ready format by itself |
| `GPFG` | `SEC 13F` | `EDGAR` | `Section 13(f)` securities in the US-reportable sleeve | US-listed/reportable only | quarterly | due within 45 days after quarter-end | institutional manager with `13(f)` reporting obligation | long history; latest located filing was `2026-05-11` for `2026-03-31` | clean lagged test for the US-reportable subset | partial view only; not representative of the full fund |

### Interpretation Notes

- `NBIM`’s own site is more transparent than an annual-report-only framing suggests. Its main public fund page says investors can search all investments and that this information is updated twice a year.
- The holdings database terms page says the historical database provides year-end holdings from the start of the fund in `1998`.
- For alpha testing, treat `NBIM` public holdings history and `Norges Bank` `13F` as separate datasets rather than blending them.
- The best use of the broad `NBIM` disclosure is strategy characterization and slow-moving sector or geography interpretation, not short-horizon mirroring.

## `PIF`

### Fund Summary

- Fund: Public Investment Fund of Saudi Arabia
- Mandate: sovereign investment fund with public and private market activity
- Transparency profile: partial
- Best quantitative use: quarterly lagged mirroring of disclosed US long equities
- Main blind spots: no complete public portfolio disclosure across non-US public assets, private assets, or derivatives

### Source Inventory

| Fund | Source | Channel | Coverage | Geography | Cadence | Lag | Threshold / Trigger | Historical Depth | Quantitative Use | Main Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PIF` | `SEC 13F` | `EDGAR` | `Section 13(f)` securities held in the US-reportable long book | US-listed/reportable only | quarterly | due within 45 days after quarter-end | institutional manager with `13(f)` reporting obligation | filings visible since `2020`; latest located filing was `2026-05-15` for `2026-03-31` | strongest clean mirroring dataset in this project | incomplete fund view; excludes non-`13F` assets and non-US holdings |
| `PIF` | `SEC 13D/G` where applicable | `EDGAR` beneficial ownership | positions above US beneficial ownership reporting thresholds | US issuers | event-driven | filing-based, faster than `13F` when triggered | beneficial ownership above `5%` or amendments | episodic | useful for concentrated strategic stakes and exit/increase events | only appears for threshold-crossing names |
| `PIF` | deal / co-investment announcements | press and transaction disclosures | private, strategic, and consortium activity | global | event-driven | event-driven | announced transaction | episodic | useful for strategy characterization | poor for backtesting public-market alpha |

### Interpretation Notes

- `PIF` is the best candidate for the single-name mirroring test because `13F` gives a quarterly, machine-readable public record with a standard lag.
- The latest `PIF` `13F` located in this initial pass was filed on `May 15, 2026` for holdings as of `March 31, 2026`.
- The `13F` summary for that filing showed only `4` entries, which is a reminder that `PIF`’s disclosed US sleeve can be very narrow and should not be interpreted as the full fund.
- `13D/G` should be mapped separately from `13F` because it captures concentrated, threshold-based ownership rather than a recurring full sleeve snapshot.

## `GIC`

### Fund Summary

- Fund: Government of Singapore Investment Corporation (`GIC`)
- Mandate: long-horizon reserve manager across public and private markets
- Transparency profile: low for position-level holdings, moderate for high-level portfolio mix and governance
- Best quantitative use: proxy monitoring of disclosed large-shareholder events
- Main blind spots: no public complete portfolio file and no direct public holdings history comparable to `GPFG` or `13F`

### Source Inventory

| Fund | Source | Channel | Coverage | Geography | Cadence | Lag | Threshold / Trigger | Historical Depth | Quantitative Use | Main Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GIC` | report on management of the government’s portfolio | `GIC` annual report | performance, governance, high-level asset mix, geography, and strategy commentary | global | annual | annual; reports available in July / August for prior financial year | none; fund-level publication | public reports listed from `2008` onward; latest report page shows `2024/25` published `2025-07-25` | strong qualitative context | no security-level public portfolio dump |
| `GIC` | portfolio page | `GIC` website | broad asset-group and geography exposures across public and private markets | global | periodic web update | unspecified | none | current web presentation | useful for top-down strategy characterization | not holdings-level |
| `GIC` | `SEC 13D/G` | `EDGAR` beneficial ownership | US names where `GIC` crosses beneficial ownership thresholds | US issuers | event-driven | filing-based | generally threshold crossing above `5%`, amendments, or exit below threshold | episodic | strongest direct single-name evidence in the US | sparse and threshold-biased |
| `GIC` | `HK DI` | `HKEX` disclosure of interests | substantial shareholder notices in Hong Kong-listed issuers | Hong Kong | event-driven | filing-based | reportable interests under Part XV of the `SFO` | searchable public history; electronic notices since `2017-07-03` | strong for large Hong Kong stakes | only threshold events and reportable names |
| `GIC` | `TR-1` major shareholdings | `FCA` `DTR 5` / `ESS` | UK major shareholding notifications | UK | event-driven | filing-based | thresholds reached or crossed under `DTR 5` | public system | useful for UK listed stakes | threshold-only; not a holdings inventory |
| `GIC` | large shareholding reports | `EDINET` / Japan `FSA` | Japanese large shareholding and change reports | Japan | event-driven, with special institutional reporting provisions in some cases | filing-based | large shareholding reporting system; public via `EDINET` | public internet inspection | strong for Japan reportable stakes | reporting mechanics are more complex than a simple one-size-fits-all threshold rule |
| `GIC` | deal and co-investment press | company and market press | private and public strategic activity | global | event-driven | event-driven | announced transaction | episodic | useful for thematic and sector inference | weak for clean entry/exit timing |

### Interpretation Notes

- `GIC` explicitly discloses governance, performance, and portfolio mix publicly, but not a line-by-line holdings book.
- `GIC`’s governance page says annual reports have been published since `2008`, and since `2011` the prior financial year’s report has been available in `July / August`.
- The `GIC` proxy dataset should be defined as a collection of threshold-triggered observable events, not as a reconstructed full portfolio.
- For `GIC`, “no filing found” must never be treated as “no position exists.”

## Cross-Fund Method Implications

### What Is Truly Observable

- `GPFG`: broad holdings, but on a slow public cadence outside the US `13F` subset
- `PIF`: recurring US long-equity sleeve through `13F`
- `GIC`: threshold events, annual top-down reporting, and inferred exposures only

### What Can Support Backtesting

- `PIF` `13F`: yes
- `Norges Bank` `13F`: yes, for the US-reportable subset
- `NBIM` broad holdings history: yes for slow-moving ownership and sector tests, but only if trades are simulated from the first public date
- `GIC` proxy events: limited; better suited to event studies or descriptive work than a standard holdings mirroring backtest

### What Is Qualitative Only

- most `GIC` annual-report content
- co-investment and deal press for all funds
- broad strategy language unless tied to dated, observable positioning changes

### Where False Precision Would Creep In

- treating `NBIM` as “quarterly full-book observable”
- treating `PIF` `13F` as representative of total `PIF` exposure
- treating the absence of a `GIC` threshold filing as absence of exposure
- comparing `GIC` row counts to `GPFG` or `PIF` row counts as though they came from the same disclosure process

## Source Notes

- `NBIM` public fund page: says all investments are searchable and updated twice a year.
- `NBIM` holdings data terms page: says the historical database contains year-end holdings from the start of the fund in `1998`.
- `SEC` Form `13F` FAQ: says filings are due within `45` days after quarter-end and cover `Section 13(f)` securities.
- `Norges Bank` latest located `13F`: filed `2026-05-11` for `2026-03-31`.
- `PIF` latest located `13F`: filed `2026-05-15` for `2026-03-31`.
- `GIC` reports page: shows annual reports through `2024/25`, published `2025-07-25`.
- `GIC` governance page: says annual reports have been published since `2008` and since `2011` are available in `July / August`.
- `HKEX` disclosure of interests page: says notices filed since `2017-07-03` are searchable through the `DION` system and all notices have been required to be filed electronically since that date.
- `FCA` `DTR 5` registration guide: major shareholding notifications are submitted through the electronic `TR-1` process and apply when thresholds are reached or crossed.
- Japan `FSA` large shareholding FAQ: reports are submitted through `EDINET` and made available for public inspection on the internet.
