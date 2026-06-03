# PIF 13F Mirroring Backtests

Research report on lagged `PIF` 13F mirroring strategies using the disclosed US 13F sleeve.

## Executive Summary

- After the split-adjusted rerun and same-day bundle fix, `P2` through `P5` are positive in absolute terms; only `P1` remains negative.
- `P2` is the strongest absolute result at `122.3%`.
- `P2` is the strongest fully invested variant at `122.3%`.
- `P1` is the weakest at `-75.8%`, driven by high concentration and fragile entry cohorts.
- `P3` finds a stronger accumulation bucket on simple average (`10.5%` vs `1.5%`), but still loses because the tilt adds concentration and tail-risk drag.
- `P4` is directionally unhelpful in this sample: avoided likely-reduction names average `10.2%` forward return versus `3.9%` for the names it keeps.
- `P5` still suggests the most usable information is in exposure contraction and expansion, not just the identity of the disclosed holdings.

## Strategies

- `P1`: buy newly disclosed entry names only.
- `P2`: hold the full disclosed common-equity sleeve equal weight.
- `P3`: overweight entries and likely accumulations, exclude likely reductions.
- `P4`: hold the sleeve but avoid likely reductions.
- `P5`: seed the first disclosed sleeve, then copy later buys and sells while retaining net sale proceeds in cash.

## Results Table

- P1: total return -75.8%, CAGR -20.2%, max drawdown -94.8%, avg positions 6.47, avg max weight 59.7%
- P2: total return 122.3%, CAGR 11.6%, max drawdown -62.2%, avg positions 18.82, avg max weight 23.6%
- P3: total return 68.6%, CAGR 7.5%, max drawdown -65.4%, avg positions 17.82, avg max weight 27.5%
- P4: total return 78.1%, CAGR 8.3%, max drawdown -65.4%, avg positions 17.82, avg max weight 25.9%
- P5: total return 48.9%, CAGR 5.6%, max drawdown -62.6%, avg positions 8.02, avg max weight 61.6%

## Why They Failed Or Worked

- `P1` fails because lagged new-entry mirroring is too concentrated. Average positions are `6.47`, average max weight is `59.7%`, and the worst single forward return in the entry sample is `-91.9%`.
- `P2` is positive because diversification helps, but the lagged equal-weight sleeve still does not produce positive alpha versus `SPY`.
- `P3` identifies a more promising bucket but concentrates too hard into names with worse tail losses.
- `P4` fails because the likely-reduction filter is directionally wrong in this sample.
- `P5` works because it does not force the strategy to stay fully invested when the visible `PIF` sleeve is shrinking. It treats disclosed sells as genuine de-risking and allows cash to accumulate, even though that still does not beat `SPY`.

## Charts

![NAV Comparison](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/nav.svg)
![Drawdown Comparison](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/drawdown.svg)
![Total Return and CAGR](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/total_return.svg)
![Risk Profile](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/risk.svg)
![Position Count](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/positions.svg)
![Concentration](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/concentration.svg)
![Rebalance Heatmap](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/period_heatmap.svg)
![Turnover](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/turnover.svg)
![P1 Entry Cohort Quality](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p1_quality.svg)
![P3 Bucket Forward Returns](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p3_bucket.svg)
![P4 Avoidance Effect](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p4_avoid.svg)
![P1 Contributors](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p1_contributors.svg)
![P2 Contributors](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p2_contributors.svg)
![P4 Contributors](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p4_contributors.svg)
![P5 Contributors](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/research_charts/p5_contributors.svg)
