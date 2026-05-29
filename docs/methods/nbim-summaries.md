# NBIM Summary Datasets

## Purpose

Create research-ready summary tables from the consolidated holdings dataset and the transition event dataset.

These summary tables are designed to answer:

- what the `NBIM` public equity portfolio looks like at each snapshot
- which regions and industries are gaining or losing observable positions over time
- whether entries, exits, likely accumulations, and likely reductions cluster in specific areas

## Output Tables

### Snapshot Summary

Built from the holdings dataset.

Outputs:

- [`data/processed/nbim/nbim_snapshot_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_snapshot_summary.csv)
- [`data/processed/nbim/nbim_snapshot_region_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_snapshot_region_summary.csv)
- [`data/processed/nbim/nbim_snapshot_industry_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_snapshot_industry_summary.csv)

Core uses:

- holdings count by snapshot
- total market value by snapshot
- region and industry weight trends
- concentration and mix changes over time

### Transition Summary

Built from the transition dataset.

Outputs:

- [`data/processed/nbim/nbim_transition_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_transition_summary.csv)
- [`data/processed/nbim/nbim_transition_region_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_transition_region_summary.csv)
- [`data/processed/nbim/nbim_transition_industry_summary.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_transition_industry_summary.csv)

Core uses:

- event counts by snapshot pair
- region-level and industry-level rotation patterns
- where `entry_observed`, `exit_observed`, `likely_accumulation`, and `likely_reduction` are concentrated

## Interpretation Rules

- snapshot summaries reflect portfolio composition, not trading
- transition summaries reflect observable change types, not exact transaction flows
- ownership-based signals are stronger than value-only changes, but still not perfect proof of trading

## Recommended First Questions

- which industries have the largest weight in each snapshot?
- which industries have the most `likely_accumulation` or `likely_reduction` events?
- are exits clustering in specific regions?
- is portfolio breadth shrinking or expanding across the observed snapshots?
