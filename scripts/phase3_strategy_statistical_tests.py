#!/usr/bin/env python3
"""Formal statistical hardening for focus-strategy excess returns.

Builds inference directly from the validated benchmark-comparison timelines.
No prices or strategies are re-derived here.
"""

from __future__ import annotations

import csv
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
INPUT_DAILY = ROOT / "data/processed/robustness/benchmark_comparison_daily.csv"
INPUT_SUMMARY = ROOT / "data/processed/robustness/benchmark_comparison_summary.csv"

OUTPUT_DIR = ROOT / "data/processed/inference"
OUTPUT_SUMMARY = OUTPUT_DIR / "strategy_statistical_tests_summary.csv"
OUTPUT_SERIES = OUTPUT_DIR / "strategy_statistical_tests_series.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "strategy_statistical_tests_audit.csv"
METHOD_DOC = ROOT / "docs/methods/phase3-strategy-statistical-tests.md"

RNG_SEED = 20260603
BOOTSTRAP_REPS = 4000
PERMUTATION_REPS = 4000


@dataclass
class PeriodRow:
    strategy_key: str
    strategy_name: str
    benchmark_key: str
    date: date
    strategy_rebased_nav: float
    benchmark_rebased_nav: float
    relative_excess_nav: float


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def as_float(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty sequence.")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def sample_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1))


def newey_west_se_mean(values: Sequence[float], lag: int) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = statistics.fmean(values)
    centered = [x - mean for x in values]
    gamma0 = sum(x * x for x in centered) / n
    long_run_var = gamma0
    max_lag = min(lag, n - 1)
    for ell in range(1, max_lag + 1):
        cov = sum(centered[t] * centered[t - ell] for t in range(ell, n)) / n
        weight = 1.0 - (ell / (max_lag + 1.0))
        long_run_var += 2.0 * weight * cov
    var_mean = max(long_run_var / n, 0.0)
    return math.sqrt(var_mean)


def circular_block_sample(values: Sequence[float], sample_len: int, block_len: int, rng: random.Random) -> List[float]:
    n = len(values)
    out: List[float] = []
    while len(out) < sample_len:
        start = rng.randrange(n)
        for j in range(block_len):
            out.append(values[(start + j) % n])
            if len(out) >= sample_len:
                break
    return out


def contiguous_blocks(values: Sequence[float], block_len: int) -> List[List[float]]:
    return [list(values[i : i + block_len]) for i in range(0, len(values), block_len)]


def annualized_mean(values: Sequence[float], periods_per_year: float) -> float:
    return statistics.fmean(values) * periods_per_year if values else 0.0


def information_ratio(values: Sequence[float], periods_per_year: float) -> float:
    std = sample_std(values)
    if std <= 0:
        return 0.0
    return statistics.fmean(values) / std * math.sqrt(periods_per_year)


def infer_block_length(series_len: int, periods_per_year: float) -> int:
    if series_len <= 12:
        return max(2, series_len // 3)
    return max(3, min(series_len, round(series_len ** (1.0 / 3.0)), round(periods_per_year ** 0.5)))


def build_period_rows() -> Dict[Tuple[str, str], List[PeriodRow]]:
    grouped: Dict[Tuple[str, str], List[PeriodRow]] = defaultdict(list)
    for row in load_csv(INPUT_DAILY):
        key = (row["strategy_key"], row["benchmark_key"])
        grouped[key].append(
            PeriodRow(
                strategy_key=row["strategy_key"],
                strategy_name=row["strategy_name"],
                benchmark_key=row["benchmark_key"],
                date=date.fromisoformat(row["date"]),
                strategy_rebased_nav=as_float(row["strategy_rebased_nav"]),
                benchmark_rebased_nav=as_float(row["benchmark_rebased_nav"]),
                relative_excess_nav=as_float(row["relative_excess_nav"]),
            )
        )
    for rows in grouped.values():
        rows.sort(key=lambda r: r.date)
    return grouped


def build_summary_lookup() -> Dict[Tuple[str, str], Dict[str, str]]:
    return {
        (row["strategy_key"], row["benchmark_key"]): row
        for row in load_csv(INPUT_SUMMARY)
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    grouped = build_period_rows()
    summary_lookup = build_summary_lookup()
    normal = statistics.NormalDist()

    series_rows: List[Dict[str, str]] = []
    summary_rows: List[Dict[str, str]] = []
    audit_rows: List[Dict[str, str]] = []

    rng = random.Random(RNG_SEED)

    for key in sorted(grouped.keys()):
        strategy_key, benchmark_key = key
        rows = grouped[key]
        if len(rows) < 3:
            continue

        prev = rows[0]
        period_excess: List[float] = []
        period_strategy: List[float] = []
        period_benchmark: List[float] = []

        for row in rows[1:]:
            strategy_return = row.strategy_rebased_nav / prev.strategy_rebased_nav - 1.0
            benchmark_return = row.benchmark_rebased_nav / prev.benchmark_rebased_nav - 1.0
            excess_return = strategy_return - benchmark_return
            period_strategy.append(strategy_return)
            period_benchmark.append(benchmark_return)
            period_excess.append(excess_return)
            series_rows.append(
                {
                    "strategy_key": strategy_key,
                    "strategy_name": row.strategy_name,
                    "benchmark_key": benchmark_key,
                    "period_end_date": row.date.isoformat(),
                    "strategy_return": f"{strategy_return:.12f}",
                    "benchmark_return": f"{benchmark_return:.12f}",
                    "excess_return": f"{excess_return:.12f}",
                }
            )
            prev = row

        years = (rows[-1].date - rows[0].date).days / 365.25
        periods_per_year = len(period_excess) / years if years > 0 else 0.0
        block_len = infer_block_length(len(period_excess), periods_per_year)
        nw_lag = max(1, min(len(period_excess) - 1, round(4 * ((len(period_excess) / 100.0) ** (2.0 / 9.0)))))

        mean_excess = statistics.fmean(period_excess)
        annualized_excess = annualized_mean(period_excess, periods_per_year)
        std_excess = sample_std(period_excess)
        annualized_vol = std_excess * math.sqrt(periods_per_year) if periods_per_year > 0 else 0.0
        ir = information_ratio(period_excess, periods_per_year)

        se_mean_nw = newey_west_se_mean(period_excess, nw_lag)
        t_stat_nw = mean_excess / se_mean_nw if se_mean_nw > 0 else 0.0
        p_value_nw_two_sided = 2.0 * (1.0 - normal.cdf(abs(t_stat_nw)))
        p_value_nw_one_sided_positive = 1.0 - normal.cdf(t_stat_nw)

        bootstrap_annualized: List[float] = []
        bootstrap_ir: List[float] = []
        for _ in range(BOOTSTRAP_REPS):
            sample = circular_block_sample(period_excess, len(period_excess), block_len, rng)
            bootstrap_annualized.append(annualized_mean(sample, periods_per_year))
            bootstrap_ir.append(information_ratio(sample, periods_per_year))
        bootstrap_annualized.sort()
        bootstrap_ir.sort()

        blocks = contiguous_blocks(period_excess, block_len)
        permuted_annualized: List[float] = []
        for _ in range(PERMUTATION_REPS):
            perm_sample: List[float] = []
            for block in blocks:
                sign = -1.0 if rng.random() < 0.5 else 1.0
                perm_sample.extend(sign * value for value in block)
            perm_sample = perm_sample[: len(period_excess)]
            permuted_annualized.append(annualized_mean(perm_sample, periods_per_year))

        observed_abs = abs(annualized_excess)
        perm_abs_ge = sum(1 for value in permuted_annualized if abs(value) >= observed_abs)
        perm_ge = sum(1 for value in permuted_annualized if value >= annualized_excess)
        perm_le = sum(1 for value in permuted_annualized if value <= annualized_excess)
        perm_two_sided = (perm_abs_ge + 1) / (PERMUTATION_REPS + 1)
        perm_one_sided = ((perm_ge if annualized_excess >= 0 else perm_le) + 1) / (PERMUTATION_REPS + 1)

        summary_row = summary_lookup[key]
        stored_excess_total = as_float(summary_row["excess_total_return"])
        computed_excess_total = rows[-1].relative_excess_nav

        summary_rows.append(
            {
                "strategy_key": strategy_key,
                "strategy_name": rows[-1].strategy_name,
                "benchmark_key": benchmark_key,
                "start_date": rows[0].date.isoformat(),
                "end_date": rows[-1].date.isoformat(),
                "observation_count": str(len(period_excess)),
                "years": f"{years:.6f}",
                "periods_per_year": f"{periods_per_year:.6f}",
                "block_length": str(block_len),
                "newey_west_lag": str(nw_lag),
                "excess_total_return": f"{computed_excess_total:.12f}",
                "annualized_excess_mean": f"{annualized_excess:.12f}",
                "annualized_excess_vol": f"{annualized_vol:.12f}",
                "information_ratio": f"{ir:.12f}",
                "newey_west_t_stat_mean_excess": f"{t_stat_nw:.12f}",
                "newey_west_p_value_two_sided": f"{p_value_nw_two_sided:.12f}",
                "newey_west_p_value_one_sided_positive": f"{p_value_nw_one_sided_positive:.12f}",
                "bootstrap_ci95_annualized_excess_low": f"{percentile(bootstrap_annualized, 0.025):.12f}",
                "bootstrap_ci95_annualized_excess_high": f"{percentile(bootstrap_annualized, 0.975):.12f}",
                "bootstrap_ci95_information_ratio_low": f"{percentile(bootstrap_ir, 0.025):.12f}",
                "bootstrap_ci95_information_ratio_high": f"{percentile(bootstrap_ir, 0.975):.12f}",
                "block_sign_permutation_p_value_two_sided": f"{perm_two_sided:.12f}",
                "block_sign_permutation_p_value_one_sided": f"{perm_one_sided:.12f}",
            }
        )

        diff = abs(computed_excess_total - stored_excess_total)
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "benchmark_key": benchmark_key,
                "check_name": "excess_total_matches_validated_summary",
                "status": "pass" if diff < 1e-10 else "fail",
                "detail": f"stored={stored_excess_total:.12f} computed={computed_excess_total:.12f} diff={diff:.12e}",
            }
        )
        low = percentile(bootstrap_annualized, 0.025)
        high = percentile(bootstrap_annualized, 0.975)
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "benchmark_key": benchmark_key,
                "check_name": "bootstrap_ci_ordered",
                "status": "pass" if low <= high else "fail",
                "detail": f"low={low:.12f} high={high:.12f}",
            }
        )
        p_checks = [
            p_value_nw_two_sided,
            p_value_nw_one_sided_positive,
            perm_two_sided,
            perm_one_sided,
        ]
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "benchmark_key": benchmark_key,
                "check_name": "p_values_in_unit_interval",
                "status": "pass" if all(0.0 <= p <= 1.0 for p in p_checks) else "fail",
                "detail": ",".join(f"{p:.12f}" for p in p_checks),
            }
        )

    with OUTPUT_SERIES.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "strategy_key",
                "strategy_name",
                "benchmark_key",
                "period_end_date",
                "strategy_return",
                "benchmark_return",
                "excess_return",
            ],
        )
        writer.writeheader()
        writer.writerows(series_rows)

    with OUTPUT_SUMMARY.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "strategy_key",
                "strategy_name",
                "benchmark_key",
                "start_date",
                "end_date",
                "observation_count",
                "years",
                "periods_per_year",
                "block_length",
                "newey_west_lag",
                "excess_total_return",
                "annualized_excess_mean",
                "annualized_excess_vol",
                "information_ratio",
                "newey_west_t_stat_mean_excess",
                "newey_west_p_value_two_sided",
                "newey_west_p_value_one_sided_positive",
                "bootstrap_ci95_annualized_excess_low",
                "bootstrap_ci95_annualized_excess_high",
                "bootstrap_ci95_information_ratio_low",
                "bootstrap_ci95_information_ratio_high",
                "block_sign_permutation_p_value_two_sided",
                "block_sign_permutation_p_value_one_sided",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    with OUTPUT_AUDIT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strategy_key", "benchmark_key", "check_name", "status", "detail"],
        )
        writer.writeheader()
        writer.writerows(audit_rows)

    METHOD_DOC.write_text(
        """# Phase 3 Strategy Statistical Tests

This layer performs formal inference on the validated strategy-versus-benchmark comparison timelines in `data/processed/robustness/benchmark_comparison_daily.csv`.

## Inputs

- `data/processed/robustness/benchmark_comparison_daily.csv`
- `data/processed/robustness/benchmark_comparison_summary.csv`

## Method

For each validated strategy-benchmark pair:

1. Reconstruct period returns directly from the rebased strategy and benchmark NAV series.
2. Compute arithmetic excess return as `strategy_return - benchmark_return`.
3. Estimate a parametric mean-excess test using a Newey-West standard error on the period excess-return series.
4. Estimate non-parametric confidence intervals for annualized excess return and information ratio using a circular moving-block bootstrap.
5. Estimate an approximate randomization p-value using a block sign-permutation test.

Annualization uses the realized observation frequency implied by the comparison file rather than assuming a fixed daily or monthly cadence.

## Outputs

- `data/processed/inference/strategy_statistical_tests_series.csv`
- `data/processed/inference/strategy_statistical_tests_summary.csv`
- `data/processed/inference/strategy_statistical_tests_audit.csv`
"""
    )


if __name__ == "__main__":
    main()
