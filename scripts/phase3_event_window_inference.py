#!/usr/bin/env python3
"""Bootstrap confidence intervals for event-window effects."""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
INPUT_DETAIL = ROOT / "data/processed/attribution/event_window_forward_returns.csv"
OUTPUT_DIR = ROOT / "data/processed/inference"
OUTPUT_SUMMARY = OUTPUT_DIR / "event_window_inference_summary.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "event_window_inference_audit.csv"
METHOD_DOC = ROOT / "docs/methods/phase3-event-window-inference.md"

BOOTSTRAP_REPS = 4000
RNG_SEED = 20260603


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def as_float(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def percentile(sorted_values: Sequence[float], q: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = int(pos)
    hi = min(len(sorted_values) - 1, lo + 1)
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def bootstrap_ci(values: Sequence[float], reps: int, rng: random.Random) -> Tuple[float, float]:
    samples: List[float] = []
    n = len(values)
    for _ in range(reps):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(mean(sample))
    samples.sort()
    return percentile(samples, 0.025), percentile(samples, 0.975)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_csv(INPUT_DETAIL)

    # Only realized windows should be used for inference.
    realized = [
        row
        for row in rows
        if row["actual_end_date"] and row["analysis_start_date"] and row["window_months"]
    ]

    grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in realized:
        grouped[("family_total", row["event_family"], row["window_months"])].append(row)
        if row["sector"]:
            grouped[("sector", f"{row['event_family']}::{row['sector']}", row["window_months"])].append(row)

    rng = random.Random(RNG_SEED)
    summary_rows: List[Dict[str, str]] = []
    audit_rows: List[Dict[str, str]] = []

    for (aggregation_level, group_key, window_months), group_rows in sorted(grouped.items()):
        event_family = group_rows[0]["event_family"]
        sector = group_rows[0]["sector"] if aggregation_level == "sector" else ""
        excess = [as_float(row["excess_forward_return"]) for row in group_rows]
        excess_minus_uncond = [as_float(row["excess_return_minus_unconditional_avg"]) for row in group_rows]
        proxy_minus_uncond = [as_float(row["proxy_return_minus_unconditional_avg"]) for row in group_rows]

        ci_excess_low, ci_excess_high = bootstrap_ci(excess, BOOTSTRAP_REPS, rng)
        ci_excess_uncond_low, ci_excess_uncond_high = bootstrap_ci(excess_minus_uncond, BOOTSTRAP_REPS, rng)
        ci_proxy_uncond_low, ci_proxy_uncond_high = bootstrap_ci(proxy_minus_uncond, BOOTSTRAP_REPS, rng)

        summary_rows.append(
            {
                "aggregation_level": aggregation_level,
                "event_family": event_family,
                "sector": sector,
                "window_months": window_months,
                "event_count": str(len(group_rows)),
                "avg_excess_forward_return": f"{mean(excess):.12f}",
                "bootstrap_ci95_excess_low": f"{ci_excess_low:.12f}",
                "bootstrap_ci95_excess_high": f"{ci_excess_high:.12f}",
                "avg_excess_minus_unconditional": f"{mean(excess_minus_uncond):.12f}",
                "bootstrap_ci95_excess_minus_unconditional_low": f"{ci_excess_uncond_low:.12f}",
                "bootstrap_ci95_excess_minus_unconditional_high": f"{ci_excess_uncond_high:.12f}",
                "avg_proxy_minus_unconditional": f"{mean(proxy_minus_uncond):.12f}",
                "bootstrap_ci95_proxy_minus_unconditional_low": f"{ci_proxy_uncond_low:.12f}",
                "bootstrap_ci95_proxy_minus_unconditional_high": f"{ci_proxy_uncond_high:.12f}",
            }
        )

        audit_rows.append(
            {
                "aggregation_level": aggregation_level,
                "event_family": event_family,
                "sector": sector,
                "window_months": window_months,
                "check_name": "bootstrap_ci_ordered",
                "status": "pass"
                if ci_excess_low <= ci_excess_high and ci_excess_uncond_low <= ci_excess_uncond_high and ci_proxy_uncond_low <= ci_proxy_uncond_high
                else "fail",
                "detail": (
                    f"excess=({ci_excess_low:.12f},{ci_excess_high:.12f}) "
                    f"excess_u=({ci_excess_uncond_low:.12f},{ci_excess_uncond_high:.12f}) "
                    f"proxy_u=({ci_proxy_uncond_low:.12f},{ci_proxy_uncond_high:.12f})"
                ),
            }
        )
        audit_rows.append(
            {
                "aggregation_level": aggregation_level,
                "event_family": event_family,
                "sector": sector,
                "window_months": window_months,
                "check_name": "event_count_positive",
                "status": "pass" if len(group_rows) > 0 else "fail",
                "detail": f"event_count={len(group_rows)}",
            }
        )

    with OUTPUT_SUMMARY.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "aggregation_level",
                "event_family",
                "sector",
                "window_months",
                "event_count",
                "avg_excess_forward_return",
                "bootstrap_ci95_excess_low",
                "bootstrap_ci95_excess_high",
                "avg_excess_minus_unconditional",
                "bootstrap_ci95_excess_minus_unconditional_low",
                "bootstrap_ci95_excess_minus_unconditional_high",
                "avg_proxy_minus_unconditional",
                "bootstrap_ci95_proxy_minus_unconditional_low",
                "bootstrap_ci95_proxy_minus_unconditional_high",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    with OUTPUT_AUDIT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "aggregation_level",
                "event_family",
                "sector",
                "window_months",
                "check_name",
                "status",
                "detail",
            ],
        )
        writer.writeheader()
        writer.writerows(audit_rows)

    METHOD_DOC.write_text(
        """# Phase 3 Event-Window Inference

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
"""
    )


if __name__ == "__main__":
    main()
