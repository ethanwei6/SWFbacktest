#!/usr/bin/env python3
"""Turnover-adjusted Sharpe and information metrics for the focus set."""

from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
INPUT_DAILY = ROOT / "data/processed/robustness/cost_sensitivity_daily.csv"
INPUT_SUMMARY = ROOT / "data/processed/robustness/cost_sensitivity_summary.csv"
OUTPUT_DIR = ROOT / "data/processed/inference"
OUTPUT_SUMMARY = OUTPUT_DIR / "turnover_adjusted_metrics.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "turnover_adjusted_metrics_audit.csv"
METHOD_DOC = ROOT / "docs/methods/phase3-turnover-adjusted-metrics.md"


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def as_float(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def sample_std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1))


def annualized_ratio(mean_value: float, std_value: float, periods_per_year: float) -> float:
    if std_value <= 0 or periods_per_year <= 0:
        return 0.0
    return mean_value / std_value * math.sqrt(periods_per_year)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_csv(INPUT_DAILY)
    summary_rows = load_csv(INPUT_SUMMARY)

    grouped: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["strategy_key"], row["cost_variant"])].append(row)
    for series in grouped.values():
        series.sort(key=lambda r: r["date"])

    summary_lookup = {
        (row["strategy_key"], row["cost_variant"]): row
        for row in summary_rows
    }

    output_rows: List[Dict[str, str]] = []
    audit_rows: List[Dict[str, str]] = []

    focus = [("p5", "SPY"), ("n4", "VT"), ("n6", "VT"), ("s1", "VT")]

    for strategy_key, benchmark_key in focus:
        base_rows = grouped[(strategy_key, "c0")]
        net_rows = grouped[(strategy_key, "c10")]
        if not base_rows or not net_rows:
            continue

        def compute_metrics(series: List[Dict[str, str]]) -> Dict[str, float]:
            dates = [date.fromisoformat(r["date"]) for r in series]
            years = (dates[-1] - dates[0]).days / 365.25
            periods_per_year = (len(series) - 1) / years if years > 0 else 0.0

            strategy_returns: List[float] = []
            benchmark_returns: List[float] = []
            excess_returns: List[float] = []
            prev_nav = as_float(series[0]["nav_end"])
            prev_bench = as_float(series[0]["primary_benchmark_nav"])
            for row in series[1:]:
                nav = as_float(row["nav_end"])
                bench = as_float(row["primary_benchmark_nav"])
                rs = nav / prev_nav - 1.0
                rb = bench / prev_bench - 1.0
                strategy_returns.append(rs)
                benchmark_returns.append(rb)
                excess_returns.append(rs - rb)
                prev_nav = nav
                prev_bench = bench

            mean_strategy = statistics.fmean(strategy_returns)
            mean_excess = statistics.fmean(excess_returns)
            std_strategy = sample_std(strategy_returns)
            std_excess = sample_std(excess_returns)
            sharpe = annualized_ratio(mean_strategy, std_strategy, periods_per_year)
            info_ratio = annualized_ratio(mean_excess, std_excess, periods_per_year)
            cumulative_trade_cost = as_float(series[-1]["cumulative_trade_cost"])
            total_gross_turnover_ratio = cumulative_trade_cost / 0.001 if cumulative_trade_cost else 0.0
            annualized_gross_turnover_ratio = total_gross_turnover_ratio / years if years > 0 else 0.0
            avg_cash_weight = statistics.fmean(as_float(r["cash_weight_end"]) for r in series)

            return {
                "years": years,
                "periods_per_year": periods_per_year,
                "sharpe": sharpe,
                "information_ratio": info_ratio,
                "cumulative_trade_cost": cumulative_trade_cost,
                "annualized_gross_turnover_ratio": annualized_gross_turnover_ratio,
                "avg_cash_weight": avg_cash_weight,
                "final_nav": as_float(series[-1]["nav_end"]),
                "final_benchmark_nav": as_float(series[-1]["primary_benchmark_nav"]),
            }

        base = compute_metrics(base_rows)
        net = compute_metrics(net_rows)

        output_rows.append(
            {
                "strategy_key": strategy_key,
                "strategy_name": base_rows[-1]["strategy_name"],
                "benchmark_key": benchmark_key,
                "start_date": base_rows[0]["date"],
                "end_date": base_rows[-1]["date"],
                "years": f"{base['years']:.6f}",
                "periods_per_year": f"{base['periods_per_year']:.6f}",
                "base_sharpe": f"{base['sharpe']:.12f}",
                "base_information_ratio": f"{base['information_ratio']:.12f}",
                "turnover_adjusted_sharpe_10bps": f"{net['sharpe']:.12f}",
                "turnover_adjusted_information_ratio_10bps": f"{net['information_ratio']:.12f}",
                "annualized_gross_turnover_ratio": f"{net['annualized_gross_turnover_ratio']:.12f}",
                "cumulative_trade_cost_10bps": f"{net['cumulative_trade_cost']:.12f}",
                "avg_cash_weight": f"{net['avg_cash_weight']:.12f}",
                "base_excess_total_return": f"{(base['final_nav'] - base['final_benchmark_nav']):.12f}",
                "turnover_adjusted_excess_total_return_10bps": f"{(net['final_nav'] - net['final_benchmark_nav']):.12f}",
                "sharpe_drag_10bps": f"{(net['sharpe'] - base['sharpe']):.12f}",
                "information_ratio_drag_10bps": f"{(net['information_ratio'] - base['information_ratio']):.12f}",
            }
        )

        expected = summary_lookup[(strategy_key, "c10")]
        expected_relative = as_float(expected["excess_total_return"])
        computed_relative = net["final_nav"] - net["final_benchmark_nav"]
        diff = abs(computed_relative - expected_relative)
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "check_name": "turnover_adjusted_excess_matches_cost_summary",
                "status": "pass" if diff < 1e-10 else "fail",
                "detail": f"computed={computed_relative:.12f} expected={expected_relative:.12f} diff={diff:.12e}",
            }
        )
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "check_name": "turnover_nonnegative",
                "status": "pass" if net["annualized_gross_turnover_ratio"] >= 0 else "fail",
                "detail": f"annualized_gross_turnover_ratio={net['annualized_gross_turnover_ratio']:.12f}",
            }
        )

    with OUTPUT_SUMMARY.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "strategy_key",
                "strategy_name",
                "benchmark_key",
                "start_date",
                "end_date",
                "years",
                "periods_per_year",
                "base_sharpe",
                "base_information_ratio",
                "turnover_adjusted_sharpe_10bps",
                "turnover_adjusted_information_ratio_10bps",
                "annualized_gross_turnover_ratio",
                "cumulative_trade_cost_10bps",
                "avg_cash_weight",
                "base_excess_total_return",
                "turnover_adjusted_excess_total_return_10bps",
                "sharpe_drag_10bps",
                "information_ratio_drag_10bps",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    with OUTPUT_AUDIT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strategy_key", "check_name", "status", "detail"],
        )
        writer.writeheader()
        writer.writerows(audit_rows)

    METHOD_DOC.write_text(
        """# Phase 3 Turnover-Adjusted Metrics

This layer uses the already validated 10 bps cost-sensitivity timelines to compute turnover-adjusted Sharpe and information metrics for the focus set.

## Inputs

- `data/processed/robustness/cost_sensitivity_daily.csv`
- `data/processed/robustness/cost_sensitivity_summary.csv`

## Method

For each focus-set strategy:

1. Use the `0 bps` series as the baseline performance path.
2. Use the `10 bps` series as the turnover-adjusted path.
3. Reconstruct period strategy and benchmark returns directly from those validated time series.
4. Compute annualized Sharpe ratio from strategy returns and annualized information ratio from benchmark-relative excess returns.
5. Recover implied gross turnover from the cumulative 10 bps trade-cost field.

## Outputs

- `data/processed/inference/turnover_adjusted_metrics.csv`
- `data/processed/inference/turnover_adjusted_metrics_audit.csv`
"""
    )


if __name__ == "__main__":
    main()
