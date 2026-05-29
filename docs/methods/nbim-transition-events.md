# NBIM Transition Event Dataset Method

## Purpose

Transform the consolidated `NBIM` public equity holdings dataset into a conservative transition dataset that compares each issuer across consecutive snapshots.

This dataset is intended to support:

- entry and exit analysis
- ownership-based change detection
- sector and region transition studies
- later event studies and slow-moving signal research

It is not intended to infer precise buy and sell flow from market value alone.

## Why This Needs Care

The `NBIM` equity files do not include share counts. That means:

- an increase in market value can reflect price appreciation, FX, or added position size
- a decrease in market value can reflect price decline, FX, or trimming

So the transition logic should rely on:

- presence versus absence
- changes in `ownership_pct`
- changes in `voting_pct`

and should treat market-value-only changes as ambiguous.

## Dataset Design

Each output row represents one issuer key across one pair of consecutive snapshots.

Example:

- previous snapshot: `2024-06-30`
- current snapshot: `2024-12-31`

For each issuer key, classify the observable transition.

## Entity Key

Use a conservative composite key:

- `issuer_name`
- `issuer_country`
- `incorporation_country`

This is not perfect, but it is more stable than issuer name alone and avoids claiming identifier precision we do not have.

## Transition Types

### Presence-Based Events

- `entry_observed`
- `exit_observed`
- `continued_holding`

### Ownership Signal

For names present in both snapshots:

- `ownership_up`
- `ownership_down`
- `ownership_flat`

### Voting Signal

For names present in both snapshots:

- `voting_up`
- `voting_down`
- `voting_flat`

### Value Movement

For names present in both snapshots:

- `value_up`
- `value_down`
- `value_flat`

## Primary Event Classification

Use a single primary event label with conservative precedence:

1. `entry_observed`
2. `exit_observed`
3. `likely_accumulation`
4. `likely_reduction`
5. `voting_up`
6. `voting_down`
7. `continued_holding`

This ensures that presence changes dominate and ownership changes dominate market-value-only moves.

The key interpretation rule is:

- `likely_accumulation` means ownership percentage increased and is the best available indicator of a position increase
- `likely_reduction` means ownership percentage decreased and is the best available indicator of a position reduction

These are still not proofs of trading, because denominator effects such as issuance or buybacks can also move ownership percentages.

## Ambiguity Rules

For continuing positions:

- if ownership is flat and value changes, classify as `continued_holding`
- attach a note that value change alone does not imply trading

## Output File

- [`data/processed/nbim/nbim_transition_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/nbim/nbim_transition_events.csv)

## Output Fields

- issuer identity fields
- previous and current snapshot dates
- previous and current region and industry
- previous and current market value
- previous and current ownership and voting
- deltas for value, ownership, and voting
- presence flags
- transition labels
- explanatory note

## Interpretation Guidance

Safe uses:

- count entries and exits by period
- count likely accumulations and likely reductions by period, sector, and geography
- identify sectors with repeated observable entries
- identify names with persistent rising or falling ownership

Unsafe uses:

- treating `value_up` as buying
- treating `value_down` as selling
- inferring exact trade size
- running a trade-timing backtest from `as_of_date` without a validated `public_date`
