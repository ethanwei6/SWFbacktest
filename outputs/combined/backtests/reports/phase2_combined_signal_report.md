# Phase 2 Combined Signal Research

## Summary

This report tests 5 combined `PIF + NBIM` strategies built from the validated Phase 2 signal stack.

- `S1` uses `PIF` to set gross exposure and `NBIM` to choose active sectors.
- `S2` only allocates to sectors with explicit cross-fund confirmation, otherwise falling back to `VT` plus cash.
- `S3` starts from the validated `P5` cash-aware `PIF` copy portfolio and reweights the invested sleeve using `NBIM` sector posture.
- `S4` takes the validated `NBIM N4` sleeve and uses `PIF` only as a risk throttle.
- `S5` takes the validated `NBIM N6` sleeve and uses `PIF` only as a risk throttle.

## Headline Results

Best excess return vs `VT`: `S1 Exposure Regime Overlay` at `1.9%`.
Worst excess return vs `VT`: `S3 PIF Cash-Aware Base Plus NBIM Overlay` at `-36.8%`.

### Strategy Table

| Strategy | Total Return | Excess vs VT | Excess vs SPY | Max Drawdown | Avg Cash |
|---|---:|---:|---:|---:|---:|
| S1 Exposure Regime Overlay | 154.7% | 1.9% | -15.1% | -25.1% | 27.0% |
| S2 Cross-Fund Consensus Sector Tilt | 82.3% | -27.1% | -39.2% | -22.1% | 42.4% |
| S3 PIF Cash-Aware Base Plus NBIM Overlay | 58.0% | -36.8% | -47.3% | -60.2% | 7.8% |
| S4 N4 Sleeve With PIF Risk Filter | 134.4% | -6.2% | -21.9% | -24.3% | 27.6% |
| S5 N6 Sleeve With PIF Risk Filter | 133.9% | -6.4% | -22.0% | -29.4% | 27.2% |

## Interpretation

- `S1` is the cleanest expression of the Phase 2 thesis: it uses `PIF` as a regime filter and `NBIM` as a sector allocator.
- `S2` is more selective and spends more time in cash or fallback benchmark exposure when cross-fund confirmation is absent.
- `S3` tests whether `NBIM` can improve the only `PIF` strategy that already showed useful absolute performance on a standalone basis.
- `S4` and `S5` test whether the strongest realistic `NBIM` sleeves become better strategies when `PIF` is used only to scale risk.

### What Worked

- `S1` is the only strategy with positive excess return versus `VT`, and the edge is modest rather than explosive.
- `S4` and `S5` tell us something important even if they do not lead the table: using `PIF` purely as a risk filter on top of realistic `NBIM` sleeves is cleaner and more interpretable than the consensus-only approach in `S2`.
- the result suggests the usable combined information is more about `when to hold less risk` plus `which sectors to own` than about direct name copying.

### What Did Not Work

- `S2` appears too sparse and too defensive. Requiring explicit cross-fund confirmation reduces false positives, but it also leaves too much time in cash or fallback benchmark exposure.
- `S3` does improve the standalone `P5` base by `6.1%`, but the improvement is not large enough to beat broad passive benchmarks.

### Conservative Read

- there is no evidence here of large, easy alpha from combining the two funds.
- the strongest result is a small, more believable edge in `S1` relative to `VT`, while all five strategies still lag `SPY`.
- the combined signal therefore looks more useful as a risk-and-sector allocation overlay than as a stand-alone superior portfolio.

## Audit Notes

- All combined strategy dates remain legal relative to their source public dates.
- Daily holdings plus cash reconcile to `1.0` within floating-point tolerance for all five strategies.
- The combined sector state table is fully mapped into the shared 11-sector taxonomy.
