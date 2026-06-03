# NBIM Alpha Backtest Report

## Executive summary

We tested eight lag-aware `NBIM` strategies using official publication dates, split-adjusted daily prices from Twelve Data for exact post-release execution, and month-end marks derived from the same daily source, with `VT` as the benchmark.

The key result after checking the construction carefully is that the strongest raw outperformance comes from a **biased exploratory stock sleeve**, not from a clean investable `NBIM` signal. Once we move to more realistic sector-based strategies, the alpha picture becomes much smaller.

The most credible positive strategies in this first pass are:

- `N4 Industry Weight-Change Tilt`: `18.7%` excess return vs `VT`
- `N6 Top-3 Industry Leaders`: `18.2%` excess return vs `VT`

That is a useful signal, but it is modest rather than dramatic.

## Important validation finding

The original `NBIM` direct-mirror sleeve is **not clean alpha evidence**.

Why:

- The mirror universe was bounded to a hand-mapped recurring set of US mega-cap names.
- That sleeve is almost identical across all snapshots and heavily concentrated in secular winners such as `Apple`, `Microsoft`, `Amazon`, `Alphabet`, `Meta`, `NVIDIA`, and `Tesla`.
- This creates a clear survivor-selection / winner-selection bias even though the execution timing and price series themselves are internally correct.

So `N1` and `N2` should be kept as exploratory reference cases, not as evidence that `NBIM` disclosure alone creates easy copy-trading alpha.

## Method

- Signal date: official `NBIM` annual or half-year publication date
- Trade date: first tradable close strictly after public release
- Marking convention: trade on the first post-release daily close, then carry the position at month-end closes until the next report
- Benchmark: `VT`
- Price source: `Twelve Data` adjusted daily history for the investable `NBIM` proxy universe

## Strategy table

| Strategy | Type | Total Return | Excess vs VT | Max Drawdown | Avg Cash |
| --- | --- | ---: | ---: | ---: | ---: |
| N1 Core US Mirror Equal Weight | Exploratory direct mirror | 717.0% | 232.0% | -28.6% | 0.0% |
| N2 Core US Mirror NBIM Weight | Exploratory direct mirror | 466.8% | 120.0% | -34.7% | 0.0% |
| N3 Industry Weight Mirror | Broad industry mirror | 161.1% | 2.2% | -22.2% | 5.3% |
| N4 Industry Weight-Change Tilt | Targeted industry rotation | 199.0% | 18.7% | -24.3% | 3.3% |
| N5 Industry Accumulation Tilt | Targeted transition tilt | 69.2% | -32.8% | -24.3% | 58.7% |
| N6 Top-3 Industry Leaders | Targeted industry concentration | 197.7% | 18.2% | -25.8% | 0.0% |
| N7 Top-3 Industry Increases | Targeted industry rotation | 129.9% | -8.7% | -24.4% | 9.1% |
| N8 Consensus Rotation Tilt | Targeted consensus rotation | 83.3% | -27.2% | -19.2% | 60.7% |

## Interpretation by strategy family

### Exploratory direct mirrors

- `N1` outperformed `VT` by `232.0%`, but this result is not reliable alpha evidence because the sleeve is a bounded basket of recurring US mega-cap winners.
- `N2` also outperformed by `120.0%` and suffers from the same bias.

### Broad replication

- `N3` was almost benchmark-like, with only `2.2%` excess return. That suggests broad `NBIM` industry posture mostly recreates a high-quality global equity allocation rather than a strong standalone alpha stream.

### Targeted sector strategies

- `N4` is the strongest realistic signal. Following the industries with the largest positive disclosed weight changes produced `18.7%` excess return. This suggests that **changes** in `NBIM`'s sector posture matter more than the level of its broad holdings.
- `N6` also worked reasonably well, with `18.2%` excess return, by simply concentrating on `NBIM`'s three largest sector exposures. This likely captures persistent quality/growth concentration without the noise of the full book.
- `N7` underperformed slightly by `-8.7%`. Chasing the largest sector increases appears too reactive relative to the slower-moving `NBIM` disclosure cadence.
- `N8` underperformed by `-27.2%` because the consensus filter is sparse and spends a lot of time in cash. It is probably too selective for a slow-moving disclosure dataset.
- `N5` was the weakest targeted signal, underperforming by `-32.8%`. The accumulation-minus-reduction score appears too noisy at the industry level in this implementation.

## Sanity checks

The backtests passed the core arithmetic and exposure checks:

- `N1 Core US Mirror Equal Weight`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `2.000e-12`
- `N2 Core US Mirror NBIM Weight`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `2.000e-12`
- `N3 Industry Weight Mirror`: negative cash breaches `0`, max gross exposure `0.959`, weight-integrity gap `2.000e-12`
- `N4 Industry Weight-Change Tilt`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `2.000e-12`
- `N5 Industry Accumulation Tilt`: negative cash breaches `0`, max gross exposure `0.962`, weight-integrity gap `2.000e-12`
- `N6 Top-3 Industry Leaders`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `1.000e-12`
- `N7 Top-3 Industry Increases`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `1.000e-12`
- `N8 Consensus Rotation Tilt`: negative cash breaches `0`, max gross exposure `1.000`, weight-integrity gap `1.000e-12`

## Bottom line

The current evidence does **not** support a strong claim that public `NBIM` disclosure enables easy copy-trading alpha.

A more accurate summary is:

- The eye-catching direct mirror outperformance is heavily biased by the hand-bounded stock universe and should not be treated as robust alpha.
- The best realistic signals are `N4` and `N6`, and both are only modestly positive at roughly `18.7%` to `18.2%` excess return vs `VT`.
- The broad industry mirror is almost benchmark-like.
- The transition-only and consensus-only sector filters are either weak or too sparse.

So the highest-confidence conclusion is that `NBIM` is more useful as a **slow-moving sector allocation / rotation signal** than as a literal copy-trading target. The realistic alpha we found is small, and only present in a narrow subset of targeted industry strategies. The strongest realistic positive strategy was `N4 Industry Weight-Change Tilt`; the weakest realistic one was `N5 Industry Accumulation Tilt`.
