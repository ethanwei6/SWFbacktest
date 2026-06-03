# Phase 3 Event-Window Inference

This layer adds bootstrap confidence intervals to the validated event-window outputs.

## Input

- `data/processed/attribution/event_window_forward_returns.csv`

## Method

For each event family and horizon, and for each sector-level subset where applicable:

1. Use only realized windows from the validated event-window detail file.
2. Compute the mean excess forward return versus the benchmark.
3. Compute the mean excess return relative to the unconditional same-proxy baseline.
4. Compute the mean proxy return relative to its unconditional baseline.
5. Estimate percentile 95 percent confidence intervals for those means using a non-parametric bootstrap across events.

## Outputs

- `data/processed/inference/event_window_inference_summary.csv`
- `data/processed/inference/event_window_inference_audit.csv`
