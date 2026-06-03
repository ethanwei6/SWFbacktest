from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTION_ROOT = ROOT / "data" / "processed" / "attribution"
SUMMARY_PATH = ATTRIBUTION_ROOT / "strategy_return_decomposition.csv"
DAILY_PATH = ATTRIBUTION_ROOT / "daily_excess_return_decomposition.csv"
AUDIT_PATH = ATTRIBUTION_ROOT / "strategy_decomposition_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-return-decomposition.md"

PIF_PRICE_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_daily_prices.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"
BENCHMARK_COMPARISON_PATH = ROOT / "data" / "processed" / "robustness" / "benchmark_comparison_summary.csv"
EXEC_LAG_PATH = ROOT / "data" / "processed" / "robustness" / "execution_lag_summary.csv"
COST_SENSITIVITY_PATH = ROOT / "data" / "processed" / "robustness" / "cost_sensitivity_summary.csv"
CAP_SENSITIVITY_PATH = ROOT / "data" / "processed" / "robustness" / "concentration_cap_summary.csv"
BENCHMARK_SERIES_PATH = ROOT / "data" / "processed" / "robustness" / "benchmark_series_daily.csv"

FOCUS_SET = [
    {
        "strategy_key": "p5",
        "strategy_name": "P5 Cash-Aware Copy",
        "portfolio_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv",
        "holdings_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_holdings_daily.csv",
        "price_source": "pif",
        "key_field": "security_key",
        "weight_field": "weight_end",
        "price_field": "close_price",
        "return_field": "return_day",
        "benchmark_key": "SPY",
    },
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_portfolio_timeline.csv",
        "holdings_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_holdings_timeline.csv",
        "price_source": "nbim",
        "key_field": "instrument_key",
        "weight_field": "portfolio_weight",
        "price_field": "",
        "return_field": "period_return",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_portfolio_timeline.csv",
        "holdings_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_holdings_timeline.csv",
        "price_source": "nbim",
        "key_field": "instrument_key",
        "weight_field": "portfolio_weight",
        "price_field": "",
        "return_field": "period_return",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "portfolio_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_portfolio_daily.csv",
        "holdings_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_holdings_daily.csv",
        "price_source": "nbim",
        "key_field": "instrument_key",
        "weight_field": "weight_end",
        "price_field": "close_price",
        "return_field": "return_day",
        "benchmark_key": "VT",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str | float | int | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def cash_weight_field(row: dict[str, str]) -> float:
    if "cash_weight_end" in row:
        return to_float(row["cash_weight_end"])
    nav_end = to_float(row.get("nav_end"))
    cash_end = to_float(row.get("cash_end"))
    return cash_end / nav_end if nav_end else 0.0


def gross_exposure_field(row: dict[str, str]) -> float:
    if "gross_exposure_end" in row:
        return to_float(row["gross_exposure_end"])
    return 0.0


def position_count_field(row: dict[str, str], holdings_for_date: list[dict[str, str]]) -> int:
    if "position_count_end" in row:
        return int(float(row["position_count_end"]))
    if "holding_count" in row:
        return int(float(row["holding_count"]))
    return len(holdings_for_date)


def load_price_lookup() -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float]]:
    pif_lookup = {
        (row["security_key"], row["date"]): to_float(row["close"])
        for row in read_csv(PIF_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }
    nbim_lookup = {
        (row["instrument_key"], row["date"]): to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }
    return pif_lookup, nbim_lookup


def load_benchmark_lookup() -> dict[str, dict[str, float]]:
    lookup: dict[str, dict[str, float]] = {}
    for row in read_csv(BENCHMARK_SERIES_PATH):
        lookup.setdefault(row["benchmark_key"], {})[row["date"]] = to_float(row["close"])
    return lookup


def build_benchmark_series(dates: list[str], benchmark_lookup: dict[str, float]) -> list[tuple[str, float]]:
    sorted_dates = sorted(benchmark_lookup)
    latest_price = None
    pointer = 0
    rows: list[tuple[str, float]] = []
    for date in dates:
        while pointer < len(sorted_dates) and sorted_dates[pointer] <= date:
            latest_price = benchmark_lookup[sorted_dates[pointer]]
            pointer += 1
        if latest_price is None:
            continue
        rows.append((date, latest_price))
    return rows


def group_holdings_by_date(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(path):
        grouped[row["date"]].append(row)
    return dict(grouped)


def load_summary_lookup(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    rows = read_csv(path)
    return {tuple(row[field] for field in key_fields): row for row in rows}


def compute_period_components(
    config: dict[str, str],
    portfolio_rows: list[dict[str, str]],
    holdings_by_date: dict[str, list[dict[str, str]]],
    benchmark_lookup: dict[str, float],
    pif_price_lookup: dict[tuple[str, str], float],
    nbim_price_lookup: dict[tuple[str, str], float],
) -> tuple[list[dict[str, str]], dict[str, str], list[dict[str, str]]]:
    dates = [row["date"] for row in portfolio_rows]
    benchmark_series = build_benchmark_series(dates, benchmark_lookup)
    benchmark_by_date = dict(benchmark_series)
    common_dates = [date for date in dates if date in benchmark_by_date]
    if len(common_dates) < 2:
        raise RuntimeError(f"Not enough benchmark-aligned rows for {config['strategy_key']}")
    portfolio_by_date = {row["date"]: row for row in portfolio_rows}
    aligned_rows = [portfolio_by_date[date] for date in common_dates]

    price_lookup = pif_price_lookup if config["price_source"] == "pif" else nbim_price_lookup
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    cumulative_strategy_arith = 0.0
    cumulative_benchmark_arith = 0.0
    cumulative_excess_arith = 0.0
    cumulative_exposure = 0.0
    cumulative_allocation = 0.0
    cumulative_concentration = 0.0
    cumulative_residual = 0.0
    effective_holdings_samples: list[float] = []
    max_weight_samples: list[float] = []
    position_count_samples: list[int] = []

    for index in range(1, len(aligned_rows)):
        prev_row = aligned_rows[index - 1]
        curr_row = aligned_rows[index]
        prev_date = prev_row["date"]
        curr_date = curr_row["date"]
        benchmark_return = benchmark_by_date[curr_date] / benchmark_by_date[prev_date] - 1.0
        strategy_return = to_float(curr_row[config["return_field"]])

        prev_cash = cash_weight_field(prev_row)
        prev_gross = gross_exposure_field(prev_row)
        prev_holdings = holdings_by_date.get(prev_date, [])

        asset_returns: list[float] = []
        weighted_asset_return = 0.0
        weight_sum = 0.0
        price_missing = 0
        for holding in prev_holdings:
            key = holding[config["key_field"]]
            start_weight = to_float(holding[config["weight_field"]])
            if start_weight <= 0:
                continue
            if config["price_field"]:
                start_price = to_float(holding[config["price_field"]])
            else:
                start_price = price_lookup.get((key, prev_date), 0.0)
            end_price = price_lookup.get((key, curr_date), 0.0)
            if start_price <= 0 or end_price <= 0:
                price_missing += 1
                continue
            asset_return = end_price / start_price - 1.0
            asset_returns.append(asset_return)
            weighted_asset_return += start_weight * asset_return
            weight_sum += start_weight

        if asset_returns:
            equal_weight_invested_return = sum(asset_returns) / len(asset_returns)
            concentration_effect = weighted_asset_return - prev_gross * equal_weight_invested_return
            equal_weight_allocation_effect = prev_gross * (equal_weight_invested_return - benchmark_return)
            max_weight = max(to_float(h[config["weight_field"]]) for h in prev_holdings if to_float(h[config["weight_field"]]) > 0)
            normalized_weights = [
                to_float(h[config["weight_field"]]) / prev_gross
                for h in prev_holdings
                if prev_gross > 0 and to_float(h[config["weight_field"]]) > 0
            ]
            effective_holdings = 1.0 / sum(w * w for w in normalized_weights) if normalized_weights else 0.0
        else:
            equal_weight_invested_return = 0.0
            concentration_effect = 0.0
            equal_weight_allocation_effect = 0.0
            max_weight = 0.0
            effective_holdings = 0.0

        exposure_timing_effect = -prev_cash * benchmark_return
        arithmetic_excess_return = strategy_return - benchmark_return
        decomposition_residual = arithmetic_excess_return - (
            exposure_timing_effect + equal_weight_allocation_effect + concentration_effect
        )
        estimated_strategy_return = weighted_asset_return
        return_reconstruction_residual = strategy_return - estimated_strategy_return

        cumulative_strategy_arith += strategy_return
        cumulative_benchmark_arith += benchmark_return
        cumulative_excess_arith += arithmetic_excess_return
        cumulative_exposure += exposure_timing_effect
        cumulative_allocation += equal_weight_allocation_effect
        cumulative_concentration += concentration_effect
        cumulative_residual += decomposition_residual

        if prev_holdings:
            effective_holdings_samples.append(effective_holdings)
            max_weight_samples.append(max_weight)
            position_count_samples.append(position_count_field(prev_row, prev_holdings))

        daily_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "strategy_name": config["strategy_name"],
                "benchmark_key": config["benchmark_key"],
                "prev_date": prev_date,
                "date": curr_date,
                "strategy_return": f"{strategy_return:.12f}",
                "benchmark_return": f"{benchmark_return:.12f}",
                "arithmetic_excess_return": f"{arithmetic_excess_return:.12f}",
                "prev_cash_weight": f"{prev_cash:.12f}",
                "prev_gross_exposure": f"{prev_gross:.12f}",
                "holding_count_prev": str(position_count_field(prev_row, prev_holdings)),
                "effective_holdings_prev": f"{effective_holdings:.12f}",
                "max_weight_prev": f"{max_weight:.12f}",
                "weighted_asset_return": f"{weighted_asset_return:.12f}",
                "equal_weight_invested_return": f"{equal_weight_invested_return:.12f}",
                "exposure_timing_effect": f"{exposure_timing_effect:.12f}",
                "cash_drag_effect": f"{exposure_timing_effect:.12f}",
                "allocation_effect": f"{equal_weight_allocation_effect:.12f}",
                "concentration_effect": f"{concentration_effect:.12f}",
                "decomposition_residual": f"{decomposition_residual:.12f}",
                "return_reconstruction_residual": f"{return_reconstruction_residual:.12f}",
                "price_missing_count": str(price_missing),
                "weight_sum_prev": f"{weight_sum:.12f}",
            }
        )

        audit_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "date": curr_date,
                "check_type": "daily_decomposition_reconciliation",
                "status": "pass" if abs(decomposition_residual) < 1e-9 else "fail",
                "expected_value": "0.000000000000",
                "actual_value": f"{decomposition_residual:.12f}",
                "difference": f"{abs(decomposition_residual):.12f}",
                "note": "Arithmetic excess return should equal exposure plus allocation plus concentration on each period.",
            }
        )
        audit_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "date": curr_date,
                "check_type": "daily_strategy_return_reconstruction",
                "status": "pass" if abs(return_reconstruction_residual) < 1e-8 else "fail",
                "expected_value": "0.000000000000",
                "actual_value": f"{return_reconstruction_residual:.12f}",
                "difference": f"{abs(return_reconstruction_residual):.12f}",
                "note": "Start-of-period holdings and asset returns should reconstruct the recorded strategy return.",
            }
        )

    benchmark_summary_lookup = load_summary_lookup(BENCHMARK_COMPARISON_PATH, ("strategy_key", "benchmark_key"))
    exec_lag_lookup = load_summary_lookup(EXEC_LAG_PATH, ("strategy_key", "execution_variant"))
    cost_lookup = load_summary_lookup(COST_SENSITIVITY_PATH, ("strategy_key", "cost_variant"))
    cap_lookup = load_summary_lookup(CAP_SENSITIVITY_PATH, ("strategy_key", "cap_variant"))

    benchmark_summary = benchmark_summary_lookup[(config["strategy_key"], config["benchmark_key"])]
    lag_drag_total = to_float(exec_lag_lookup[(config["strategy_key"], "t5")]["excess_total_return"]) - to_float(
        exec_lag_lookup[(config["strategy_key"], "t1")]["excess_total_return"]
    )
    cost_drag_total = to_float(cost_lookup[(config["strategy_key"], "c50")]["excess_total_return"]) - to_float(
        cost_lookup[(config["strategy_key"], "c0")]["excess_total_return"]
    )
    cap_drag_total = to_float(cap_lookup[(config["strategy_key"], "t1")]["excess_total_return"]) - to_float(
        cap_lookup[(config["strategy_key"], "u0")]["excess_total_return"]
    )

    summary_row = {
        "strategy_key": config["strategy_key"],
        "strategy_name": config["strategy_name"],
        "benchmark_key": config["benchmark_key"],
        "start_date": common_dates[0],
        "end_date": common_dates[-1],
        "period_count": str(len(daily_rows)),
        "terminal_strategy_total_return": benchmark_summary["strategy_total_return"],
        "terminal_benchmark_total_return": benchmark_summary["benchmark_total_return"],
        "terminal_excess_total_return": benchmark_summary["excess_total_return"],
        "cumulative_strategy_return_arithmetic": f"{cumulative_strategy_arith:.12f}",
        "cumulative_benchmark_return_arithmetic": f"{cumulative_benchmark_arith:.12f}",
        "cumulative_excess_return_arithmetic": f"{cumulative_excess_arith:.12f}",
        "exposure_timing_contribution_arithmetic": f"{cumulative_exposure:.12f}",
        "cash_drag_contribution_arithmetic": f"{cumulative_exposure:.12f}",
        "allocation_contribution_arithmetic": f"{cumulative_allocation:.12f}",
        "concentration_contribution_arithmetic": f"{cumulative_concentration:.12f}",
        "arithmetic_reconstruction_residual": f"{cumulative_residual:.12f}",
        "avg_cash_weight": f"{(sum(cash_weight_field(r) for r in aligned_rows[:-1]) / max(1, len(aligned_rows[:-1]))):.12f}",
        "avg_gross_exposure": f"{(sum(gross_exposure_field(r) for r in aligned_rows[:-1]) / max(1, len(aligned_rows[:-1]))):.12f}",
        "avg_position_count": f"{(sum(position_count_samples) / len(position_count_samples)) if position_count_samples else 0.0:.12f}",
        "avg_effective_holdings": f"{(sum(effective_holdings_samples) / len(effective_holdings_samples)) if effective_holdings_samples else 0.0:.12f}",
        "avg_max_weight": f"{(sum(max_weight_samples) / len(max_weight_samples)) if max_weight_samples else 0.0:.12f}",
        "lag_drag_excess_t5_minus_t1": f"{lag_drag_total:.12f}",
        "cost_drag_excess_50bps_minus_0bps": f"{cost_drag_total:.12f}",
        "cap_drag_excess_tight_minus_uncapped": f"{cap_drag_total:.12f}",
    }
    audit_rows.append(
        {
            "strategy_key": config["strategy_key"],
            "date": "TOTAL",
            "check_type": "arithmetic_total_reconciliation",
            "status": "pass" if abs(cumulative_residual) < 1e-8 else "fail",
            "expected_value": "0.000000000000",
            "actual_value": f"{cumulative_residual:.12f}",
            "difference": f"{abs(cumulative_residual):.12f}",
            "note": "Cumulative arithmetic excess return should equal the sum of the arithmetic components.",
        }
    )
    return daily_rows, summary_row, audit_rows


def main() -> None:
    pif_price_lookup, nbim_price_lookup = load_price_lookup()
    benchmark_lookups = load_benchmark_lookup()

    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for config in FOCUS_SET:
        portfolio_rows = read_csv(Path(config["portfolio_path"]))
        holdings_by_date = group_holdings_by_date(Path(config["holdings_path"]))
        part_daily, part_summary, part_audit = compute_period_components(
            config,
            portfolio_rows,
            holdings_by_date,
            benchmark_lookups[config["benchmark_key"]],
            pif_price_lookup,
            nbim_price_lookup,
        )
        summary_rows.append(part_summary)
        daily_rows.extend(part_daily)
        audit_rows.extend(part_audit)

    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(DAILY_PATH, daily_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 B1: Return Decomposition\n\n"
        "This layer explains what drives the surviving Phase 3 focus-set strategies without inventing a false exact terminal-return attribution.\n\n"
        "## Focus set\n\n"
        "- `P5` Cash-Aware Copy versus `SPY`\n"
        "- `N4` Industry Weight-Change Tilt versus `VT`\n"
        "- `N6` Top-3 Industry Leaders versus `VT`\n"
        "- `S1` Exposure Regime Overlay versus `VT`\n\n"
        "## Attribution design\n\n"
        "The decomposition is done in daily or period-by-period arithmetic excess-return space. For each period, excess return is split exactly into:\n\n"
        "1. `exposure_timing_effect`: the effect of holding less than full benchmark exposure, equal to `-cash_weight_prev * benchmark_return` for these unlevered long-only strategies;\n"
        "2. `allocation_effect`: the excess return from the strategy's start-of-period holdings if those holdings were equal-weighted within the invested sleeve;\n"
        "3. `concentration_effect`: the incremental effect of using the actual strategy weights instead of equal weights within that same start-of-period sleeve.\n\n"
        "These components reconcile exactly to the observed arithmetic excess return for each period. They are then summed across time to produce cumulative arithmetic explanatory contributions. Because compounded terminal excess return is not additively decomposable in the same way, the output also keeps the separately reported terminal total-return and excess-return values.\n\n"
        "## Additional robustness drags\n\n"
        "The summary table also imports:\n\n"
        "- `lag_drag_excess_t5_minus_t1` from A1;\n"
        "- `cost_drag_excess_50bps_minus_0bps` from A2;\n"
        "- `cap_drag_excess_tight_minus_uncapped` from A3.\n\n"
        "These are not part of the daily arithmetic decomposition itself; they are reported alongside it to show which strategies are most fragile to realistic implementation stress.\n\n"
        "## Outputs\n\n"
        "- `data/processed/attribution/strategy_return_decomposition.csv`\n"
        "- `data/processed/attribution/daily_excess_return_decomposition.csv`\n"
        "- `data/processed/attribution/strategy_decomposition_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
