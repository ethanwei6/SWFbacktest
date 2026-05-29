# PIF 13F Transition Dataset Method

## Purpose

Transform the canonical `PIF` `13F` holdings dataset into a transition dataset across consecutive reporting periods.

Unlike the `NBIM` holdings history, the `13F` data includes share counts, so the transition dataset can support stronger inference.

## What This Dataset Can Support

- observed entries and exits
- share-count increases and decreases
- value changes
- option-versus-common differentiation where present
- later lag-aware mirroring and turnover analysis

## Security Key

Use a security-level key that distinguishes common shares from option positions:

- `cusip`
- `title_of_class`
- `put_call`
- `share_type`
- `issuer_name`

This is stricter than issuer name alone and avoids mixing:

- common equity versus options
- different share classes
- ADR-like variants when they carry different `CUSIP`s

## Event Logic

For each pair of consecutive reporting periods:

- `entry_observed`: security absent previously, present now
- `exit_observed`: security present previously, absent now
- `likely_accumulation`: share count rises materially
- `likely_reduction`: share count falls materially
- `continued_holding`: security present in both periods with flat share count

Supplemental signals:

- `value_up`
- `value_down`
- `value_flat`

The primary event classification should be driven by share count, not by market value.

For entries and exits, use an explicit zero baseline on the missing side:

- `entry_observed`: previous shares = `0`, previous market value = `0`
- `exit_observed`: current shares = `0`, current market value = `0`

This makes deltas much more usable and avoids unnecessary `unknown` classifications for clean 13F additions and removals.

## Why Shares Matter Here

In `13F`, share count is the best available indicator of position change. It is still not perfect:

- stock splits
- mergers
- spin-offs
- corporate actions

can affect counts. But it is much more informative than market value alone.

## Output

- [`data/processed/pif/pif_13f_transition_events.csv`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/data/processed/pif/pif_13f_transition_events.csv)

## Safe Uses

- count additions and removals
- count likely accumulations and reductions
- identify concentrated changes in specific names
- summarize period-level turnover

Important caveat:

- disappearance from `13F` means disappearance from the reported `13F` book
- that is the correct interpretation for this dataset, but it does not prove zero total exposure outside what `13F` captures

## Later Extensions

- filing-level lag-aware event studies
- canonical PIF mirrored portfolio on public filing dates
- top-adds and top-cuts watchlist
