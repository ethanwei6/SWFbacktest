from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
BENCHMARK_SERIES_PATH = ROBUSTNESS_ROOT / "benchmark_series_daily.csv"
SUMMARY_PATH = ROBUSTNESS_ROOT / "benchmark_comparison_summary.csv"
DAILY_PATH = ROBUSTNESS_ROOT / "benchmark_comparison_daily.csv"
AUDIT_PATH = ROBUSTNESS_ROOT / "benchmark_comparison_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-benchmark-robustness.md"

FOCUS_SET = [
    {
        "strategy_key": "p5",
        "strategy_name": "P5 Cash-Aware Copy",
        "portfolio_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv",
        "benchmark_keys": ["SPY", "QQQ"],
    },
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_portfolio_timeline.csv",
        "benchmark_keys": ["VT", "ACWI"],
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_portfolio_timeline.csv",
        "benchmark_keys": ["VT", "ACWI"],
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "portfolio_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_portfolio_daily.csv",
        "benchmark_keys": ["VT", "SPY", "BLEND_VT_SPY_50"],
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


def drawdown_field(row: dict[str, str]) -> float:
    if "drawdown_to_date" in row:
        return to_float(row["drawdown_to_date"])
    return to_float(row.get("drawdown", 0.0))


def load_benchmark_lookups() -> dict[str, dict[str, float]]:
    lookups: dict[str, dict[str, float]] = {}
    for row in read_csv(BENCHMARK_SERIES_PATH):
        lookups.setdefault(row["benchmark_key"], {})[row["date"]] = to_float(row["close"])
    return lookups


def summarize_strategy_vs_benchmark(
    strategy_key: str,
    strategy_name: str,
    portfolio_rows: list[dict[str, str]],
    benchmark_key: str,
    benchmark_lookup: dict[str, float],
) -> tuple[list[dict[str, str]], dict[str, str], list[dict[str, str]]]:
    dates = [row["date"] for row in portfolio_rows]
    benchmark_series = build_benchmark_series(dates, benchmark_lookup)
    if len(benchmark_series) < 2:
        raise RuntimeError(f"Not enough benchmark rows for {strategy_key} vs {benchmark_key}")

    portfolio_by_date = {row["date"]: row for row in portfolio_rows}
    common_dates = [date for date, _ in benchmark_series if date in portfolio_by_date]
    if len(common_dates) < 2:
        raise RuntimeError(f"Not enough aligned rows for {strategy_key} vs {benchmark_key}")

    aligned_rows = [portfolio_by_date[date] for date in common_dates]
    benchmark_by_date = dict(benchmark_series)
    strategy_start_nav = to_float(aligned_rows[0]["nav_end"])
    benchmark_start_close = benchmark_by_date[common_dates[0]]
    peak_strategy = 1.0
    peak_benchmark = 1.0
    daily_rows: list[dict[str, str]] = []

    for row in aligned_rows:
        date = row["date"]
        nav_end = to_float(row["nav_end"])
        benchmark_close = benchmark_by_date[date]
        strategy_rebased = nav_end / strategy_start_nav if strategy_start_nav else 0.0
        benchmark_rebased = benchmark_close / benchmark_start_close if benchmark_start_close else 0.0
        peak_strategy = max(peak_strategy, strategy_rebased)
        peak_benchmark = max(peak_benchmark, benchmark_rebased)
        daily_rows.append(
            {
                "strategy_key": strategy_key,
                "strategy_name": strategy_name,
                "benchmark_key": benchmark_key,
                "date": date,
                "nav_end": f"{nav_end:.12f}",
                "strategy_rebased_nav": f"{strategy_rebased:.12f}",
                "benchmark_close": f"{benchmark_close:.12f}",
                "benchmark_rebased_nav": f"{benchmark_rebased:.12f}",
                "relative_excess_nav": f"{(strategy_rebased - benchmark_rebased):.12f}",
                "cash_weight_end": f"{cash_weight_field(row):.12f}",
                "gross_exposure_end": f"{gross_exposure_field(row):.12f}",
                "strategy_drawdown_relative": f"{(strategy_rebased / peak_strategy - 1.0):.12f}",
                "benchmark_drawdown_relative": f"{(benchmark_rebased / peak_benchmark - 1.0):.12f}",
            }
        )

    final_strategy_rebased = to_float(daily_rows[-1]["strategy_rebased_nav"])
    final_benchmark_rebased = to_float(daily_rows[-1]["benchmark_rebased_nav"])
    summary_row = {
        "strategy_key": strategy_key,
        "strategy_name": strategy_name,
        "benchmark_key": benchmark_key,
        "start_date": common_dates[0],
        "end_date": common_dates[-1],
        "row_count": str(len(daily_rows)),
        "strategy_total_return": f"{(final_strategy_rebased - 1.0):.12f}",
        "benchmark_total_return": f"{(final_benchmark_rebased - 1.0):.12f}",
        "excess_total_return": f"{((final_strategy_rebased - 1.0) - (final_benchmark_rebased - 1.0)):.12f}",
        "strategy_max_drawdown": f"{min(to_float(r['strategy_drawdown_relative']) for r in daily_rows):.12f}",
        "benchmark_max_drawdown": f"{min(to_float(r['benchmark_drawdown_relative']) for r in daily_rows):.12f}",
        "avg_cash_weight": f"{(sum(to_float(r['cash_weight_end']) for r in daily_rows) / len(daily_rows)):.12f}",
        "avg_gross_exposure": f"{(sum(to_float(r['gross_exposure_end']) for r in daily_rows) / len(daily_rows)):.12f}",
    }
    audit_rows = [
        {
            "strategy_key": strategy_key,
            "benchmark_key": benchmark_key,
            "check_type": "minimum_row_count",
            "status": "pass" if len(daily_rows) >= 2 else "fail",
            "expected_value": ">=2",
            "actual_value": str(len(daily_rows)),
            "difference": "0.000000000000",
            "note": "Each strategy-benchmark comparison needs at least two aligned rows.",
        },
        {
            "strategy_key": strategy_key,
            "benchmark_key": benchmark_key,
            "check_type": "rebase_anchor",
            "status": "pass"
            if abs(to_float(daily_rows[0]["strategy_rebased_nav"]) - 1.0) < 1e-9
            and abs(to_float(daily_rows[0]["benchmark_rebased_nav"]) - 1.0) < 1e-9
            else "fail",
            "expected_value": "1.000000000000/1.000000000000",
            "actual_value": f"{daily_rows[0]['strategy_rebased_nav']}/{daily_rows[0]['benchmark_rebased_nav']}",
            "difference": "0.000000000000",
            "note": "Both strategy and benchmark must rebase to 1.0 on the first aligned date.",
        },
        {
            "strategy_key": strategy_key,
            "benchmark_key": benchmark_key,
            "check_type": "date_order",
            "status": "pass" if common_dates[0] <= common_dates[-1] else "fail",
            "expected_value": "start<=end",
            "actual_value": f"{common_dates[0]}->{common_dates[-1]}",
            "difference": "0.000000000000",
            "note": "Aligned benchmark dates must remain ordered.",
        },
    ]
    return daily_rows, summary_row, audit_rows


def main() -> None:
    benchmark_lookups = load_benchmark_lookups()

    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for config in FOCUS_SET:
        portfolio_rows = read_csv(Path(config["portfolio_path"]))
        for benchmark_key in config["benchmark_keys"]:
            if benchmark_key not in benchmark_lookups:
                raise RuntimeError(f"Missing benchmark series for {benchmark_key}")
            part_daily, part_summary, part_audit = summarize_strategy_vs_benchmark(
                config["strategy_key"],
                config["strategy_name"],
                portfolio_rows,
                benchmark_key,
                benchmark_lookups[benchmark_key],
            )
            summary_rows.append(part_summary)
            daily_rows.extend(part_daily)
            audit_rows.extend(part_audit)

    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(DAILY_PATH, daily_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 A5: Benchmark Robustness\n\n"
        "This layer tests whether the focus-set conclusions depend too heavily on a single benchmark choice.\n\n"
        "## Focus set\n\n"
        "- `P5` versus `SPY` and `QQQ`\n"
        "- `N4` versus `VT` and `ACWI`\n"
        "- `N6` versus `VT` and `ACWI`\n"
        "- `S1` versus `VT`, `SPY`, and `BLEND_VT_SPY_50`\n\n"
        "## Benchmark construction\n\n"
        "- `SPY` comes from the validated local PIF benchmark layer.\n"
        "- `VT` comes from the validated local NBIM benchmark layer.\n"
        "- `QQQ` and `ACWI` are fetched as adjusted daily series from Twelve Data.\n"
        "- `BLEND_VT_SPY_50` is a synthetic benchmark formed as a 50/50 blend of rebased `VT` and `SPY` daily NAVs.\n\n"
        "## Method\n\n"
        "A5 does not re-run the strategies. It uses the validated baseline portfolio timelines and aligns each one with each candidate benchmark using the same carry-forward benchmark logic used in earlier robustness steps. Strategy NAV and benchmark NAV are rebased to `1.0` on the first aligned date, and then benchmark-relative excess returns are recomputed over the matched live window.\n\n"
        "## Outputs\n\n"
        "- `data/processed/robustness/benchmark_series_daily.csv`\n"
        "- `data/processed/robustness/benchmark_series_audit.csv`\n"
        "- `data/processed/robustness/benchmark_comparison_summary.csv`\n"
        "- `data/processed/robustness/benchmark_comparison_daily.csv`\n"
        "- `data/processed/robustness/benchmark_comparison_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
