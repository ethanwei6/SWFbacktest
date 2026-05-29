# PIF Backtest Research Report

This report layer packages the corrected `P1` through `P4` `PIF` backtests into a deliverable research memo plus a larger chart pack.

## Inputs

- `data/processed/pif/backtests/analysis/strategy_summary.csv`
- `data/processed/pif/backtests/analysis/strategy_sanity_checks.csv`
- `data/processed/pif/backtests/analysis/strategy_top_contributors.csv`
- `data/processed/pif/backtests/analysis/strategy_rebalance_period_returns.csv`
- `data/processed/pif/backtests/analysis/p1_entry_forward_returns.csv`
- `data/processed/pif/backtests/analysis/p3_bucket_forward_returns.csv`
- `data/processed/pif/backtests/analysis/p4_avoidance_forward_returns.csv`
- the underlying daily portfolio files for `P1` through `P4`

## Output goals

1. produce a research-style memo that explains the tested strategies, the corrected results, and the likely reasons they failed
2. produce a broader visual pack than the analysis report, suitable for external discussion and later interactive expansion

## Main outputs

- `outputs/pif/backtests/reports/pif_backtest_research_report.html`
- `outputs/pif/backtests/reports/pif_backtest_research_report.md`
- `outputs/pif/backtests/research_charts/*`

## Report focus

The report is intentionally interpretive, not just descriptive. It emphasizes:

- why the earlier raw-price results were not trustworthy
- what changes after the split-adjusted rerun
- which strategies fail because of lag, concentration, or wrong-direction signal logic
- what the current `PIF` data is still good for, even if the tested mirroring strategies are unattractive
