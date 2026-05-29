# SWF Monitor

Research project on sovereign wealth fund holdings, sector tilts, and the viability of lagged mirroring strategies.

## Goal

Assess whether alpha can be captured by:

- mirroring disclosed positions of large sovereign wealth funds on a realistic lag
- tilting toward sectors and industries where those funds are accumulating exposure
- understanding exit timelines and processes well enough to avoid stale or already-distributed positions

## Target Funds

- GIC
- Public Investment Fund (`PIF`)
- Norway Government Pension Fund Global (`GPFG` / `NBIM`)

## Core Constraint

These funds have radically different disclosure regimes:

- `GPFG`: broad public disclosure, but slow
- `PIF`: partial public disclosure through `SEC 13F` for US-listed long positions
- `GIC`: largely opaque; exposure must be inferred from cross-jurisdiction ownership filings and press

The project should not force comparability where the underlying data does not support it.

## Workspace Layout

- [`docs/project-tracker.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/project-tracker.md): milestones, weekly plan, risks, and supervisor questions
- [`docs/research-design.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/research-design.md): methodology, hypotheses, and analysis plan
- [`docs/disclosure-map-template.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/docs/disclosure-map-template.md): template for documenting what is public for each fund
- [`schemas/holdings-schema.md`](/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/schemas/holdings-schema.md): normalized holdings data model

## Immediate Next Steps

1. Complete the disclosure map for `GPFG`, `PIF`, and `GIC`.
2. Freeze the normalized holdings schema before collecting rows.
3. Build `GPFG` and `PIF` history first.
4. Draft the `GIC` proxy methodology before collecting inferred holdings.
5. Run alpha tests only from public availability dates, not economic effective dates.
