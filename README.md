# SWF Monitor: Disclosure-Lag-Aware Sovereign Wealth Fund Research

This repository studies whether public sovereign wealth fund disclosures can be converted into tradable signals once the backtest is forced to respect public availability dates, partial portfolio visibility, implementation frictions, and benchmark-relative evaluation.

The project centers on two funds with very different disclosure regimes:
- `PIF` (Saudi Arabia's Public Investment Fund), observed through U.S. `13F` filings
- `NBIM` (Norway's Norges Bank Investment Management / GPFG), observed through public holdings releases

Rather than stopping at naive “copy the portfolio” backtests, the repo builds a full research stack: normalized holdings panels, transition engines, lag-aware portfolio simulators, benchmark and robustness layers, attribution analysis, formal inference, and a final IEEE-style research paper.

## Research Setting

The core challenge is that sovereign wealth funds do **not** disclose on a uniform basis:
- `PIF` reveals only a narrow U.S.-listed sleeve through `13F`
- `NBIM` reveals a much broader portfolio, but at lower frequency
- `GIC` was evaluated and intentionally excluded from the quantitative panel because the public record was too sparse for a credible holdings-based backtest

That asymmetry forced the project into a more realistic research design:
- trade only after the signal becomes public
- distinguish stock-level mirroring from sector-level posture
- separate exploratory tests from credible tests
- audit the data and code paths instead of trusting attractive early results

## Research Question

Can an outside investor extract alpha from sovereign wealth fund disclosures by:
- mirroring disclosed positions after they become public,
- tilting toward sectors those funds appear to be accumulating, or
- using the disclosures as slow-moving exposure and allocation signals?

## What Was Built

### 1. Fund-Specific Data Pipelines
- `PIF` `13F` XML parsing, amendment resolution, holdings normalization, transition classification, and price mapping
- `NBIM` holdings stacking, issuer-level normalization, industry aggregation, transition building, and sector-proxy construction

### 2. Strategy Libraries
- `PIF`: five strategies ranging from “new positions only” to a cash-aware copycat design
- `NBIM`: eight strategies ranging from exploratory direct mirrors to more realistic sector-rotation and leadership sleeves
- `Combined`: cross-fund overlays that use `PIF` as an exposure signal and `NBIM` as a sector-posture signal

### 3. Validation and Audit Infrastructure
- split-adjusted pricing correction for `PIF`
- same-day filing-bundle correction in the original fully invested `PIF` engines
- bounded-universe bias audit for `NBIM` direct mirrors
- repo-wide logic audits, source-data spot checks, and benchmark reconciliation passes

### 4. Phase 3 / Phase 4 Hardening
- delayed execution sensitivity
- one-way transaction-cost sensitivity
- concentration and exposure caps
- subperiod stability
- alternate benchmark robustness
- attribution decomposition
- event-window analysis with unconditional baselines
- formal statistical tests and bootstrap intervals
- institutional benchmark layer (`cash hurdle`, `defensive equity`, `downside capture`, `Sortino`, `Calmar`)

## Main Findings

### `PIF`
- After correcting implementation issues, several `PIF` strategies generate positive **absolute** returns.
- None of them beat `SPY`.
- The public `13F` sleeve is therefore more useful as a **posture / exposure signal** than as a source of reliable copy-trading alpha.

### `NBIM`
- The strongest raw direct-mirror results were not accepted at face value because they were contaminated by survivor-selection in a bounded U.S. mega-cap universe.
- The more credible evidence comes from **sector posture**, not stock-level imitation.
- The strongest surviving sleeve is `N6`, a concentrated “top-3 industry leaders” strategy.

### `Combined PIF + NBIM`
- Cross-fund strategies are more useful as **allocation overlays** than as standalone alpha engines.
- `S1` is best interpreted as a lower-beta overlay concept rather than a benchmark-beating strategy.

### Final Interpretation
The most defensible conclusion is:

> Public sovereign wealth fund disclosures are more useful as slow-moving allocation and sector-posture signals than as literal stock-by-stock copy-trading instructions.

## Public-Facing Outputs

If you only look at a few artifacts, start here:

- Research paper (PDF): [`paper/build/swf_monitor_ieee.pdf`](paper/build/swf_monitor_ieee.pdf)
- Research paper (LaTeX): [`paper/swf_monitor_ieee.tex`](paper/swf_monitor_ieee.tex)
- Research design: [`docs/research-design.md`](docs/research-design.md)
- PIF research report: [`outputs/pif/backtests/reports/pif_backtest_research_report.html`](outputs/pif/backtests/reports/pif_backtest_research_report.html)
- NBIM research report: [`outputs/nbim/backtests/reports/nbim_backtest_research_report.html`](outputs/nbim/backtests/reports/nbim_backtest_research_report.html)
- Combined-signal report: [`outputs/combined/backtests/reports/phase2_combined_signal_report.html`](outputs/combined/backtests/reports/phase2_combined_signal_report.html)
- Interactive `PIF` explorer: [`outputs/pif/backtests/interactive/pif_strategy_explorer.html`](outputs/pif/backtests/interactive/pif_strategy_explorer.html)

## Repository Structure

```text
data/
  raw/                  Raw filings, holdings exports, and source-level price pulls
  processed/            Normalized holdings, backtests, audits, attribution, inference
docs/                   Research design, phase plans, and methodology notes
outputs/                HTML reports, charts, and interactive artifacts
paper/                  IEEE-style paper source and compiled PDF
schemas/                Shared holdings and sector-taxonomy schemas
scripts/                End-to-end pipeline, backtest, audit, and reporting code
```

## Technical Scope

- event-driven financial data engineering across heterogeneous disclosure regimes
- realistic backtest design with public-date-aware execution
- rigorous debugging and audit discipline rather than result-chasing
- modular research tooling across Python pipelines, reporting, and reproducible artifacts
- careful benchmark design, including opportunity-cost and institutional-style comparators

## Notes on Reproducibility

The repo includes generated outputs and the scripts that produced them. Some price layers were built from third-party APIs (`Twelve Data`, `Alpha Vantage`) and some analyses depend on those cached pulls already stored in the repo. The final validated workflow uses the corrected daily adjusted price layers and the audited benchmark / attribution / inference stacks described in the paper.

## Suggested GitHub Description

**Disclosure-lag-aware sovereign wealth fund research: PIF and NBIM holdings pipelines, realistic backtests, robustness testing, attribution, and an IEEE-style paper on whether public SWF disclosures contain tradable alpha.**
