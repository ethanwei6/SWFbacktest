# Final Model Expression

This note records the final simplification decision after the statistical hardening layer.

## Goal

Reduce the project to the smallest set of outputs that still represents the strongest evidence honestly.

## Decision

No new production strategy was added.

Instead, the final expression of the project is:

1. `N6 Top-3 Industry Leaders` as the strongest residual investable sleeve
2. the cross-fund `state model` as the best monitoring abstraction

## Why no new strategy was added

The hardening layer weakened, rather than strengthened, the case for inventing another hybrid:

- `P5` is structurally interesting but still clearly negative versus `SPY`
- `N4` is positive economically but loses too much of its case under realistic caps
- `S1` is intuitive but fragile, benchmark-sensitive, and statistically weak
- `N6` is already simpler than the combined models and survives the most checks

Adding another production candidate on top of these results would have increased complexity without adding stronger evidence.

## Final roles

### `N6`

Use as the final candidate sleeve if the project must nominate one investable model.

Operational expression:

- after each `NBIM` release, identify the three largest disclosed industry exposures
- map those industries to liquid sector ETF proxies
- rebalance on the first tradable close after publication
- hold until the next `NBIM` release

### State model

Use as the final monitoring abstraction even if no live strategy is traded from it directly.

Operational expression:

- update the `PIF` risk posture and `NBIM` sector posture after each disclosure cycle
- classify the combined state
- publish the latest state and its recent transition history
- use it as a research and monitoring layer rather than as a fully automated trading engine

## Supporting artifact

- `data/processed/inference/final_model_expression.csv`
