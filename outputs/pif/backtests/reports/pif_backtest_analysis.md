# PIF Backtest Strategy Analysis

This report is the sanity-check and benchmarked visual layer for the first five `PIF` strategies.

## Immediate Read

- After correcting split distortion, the old positive headlines for `P2` through `P4` should still be discarded, but the new `P5` cash-aware strategy is positive.
- `P5` is the strongest result at `+48.9%`, while `P1` remains the weakest at `-75.8%`.
- The stricter alpha test is benchmark-relative. Against a matched-window `SPY` buy-and-hold, none of the strategies generates positive excess return in this first pass.
- `P1` is structurally fragile because it is highly concentrated: average max weight `59.7%`, average positions `6.47`, and a worst forward cohort name at `-91.9%`.
- `P3` still loses even though `accumulation_like` names have higher simple average forward returns (`12.1%` vs `1.5%`), which points to concentration and tail-risk drag rather than no signal at all.
- `P4` is directionally unhelpful in this sample: avoided likely-reduction names averaged `10.2%` forward return versus `4.8%` for the names it kept.
- `P5` changes the interpretation of the whole project: when sale proceeds are retained as cash instead of being redistributed into remaining names, the `PIF` copycat strategy becomes profitable in absolute terms, but it still fails to beat `SPY`.

## Charts

![Strategy NAV Comparison](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_nav_comparison.svg)
![Strategy Relative to SPY](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_relative_to_spy.svg)
![Strategy Drawdown Comparison](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_drawdown_comparison.svg)
![Strategy Position Count](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_position_count.svg)
![Return vs Drawdown](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_return_vs_drawdown.svg)
![Strategy Concentration](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_concentration.svg)
![Strategy Returns vs SPY](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_vs_spy_total_return.svg)
![Strategy Excess Quality vs SPY](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/strategy_vs_spy_excess_quality.svg)
![P1 Entry Cohort Quality](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/p1_entry_cohort_quality.svg)
![P3 Bucket Forward Returns](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/p3_bucket_forward_returns.svg)
![P4 Avoidance Effect](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/p4_avoidance_effect.svg)
![P4 Top Contributors](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/outputs/pif/backtests/charts/p4_top_contributors.svg)
