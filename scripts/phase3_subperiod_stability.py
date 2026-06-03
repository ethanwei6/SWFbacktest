from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
SUMMARY_PATH = ROBUSTNESS_ROOT / "subperiod_summary.csv"
DAILY_PATH = ROBUSTNESS_ROOT / "subperiod_daily.csv"
AUDIT_PATH = ROBUSTNESS_ROOT / "subperiod_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-subperiod-stability.md"

PIF_BENCHMARK_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"

SUBPERIODS = [
    {"subperiod_key": "2019_2021", "label": "2019-2021", "start": "2019-01-01", "end": "2021-12-31"},
    {"subperiod_key": "2022_2023", "label": "2022-2023", "start": "2022-01-01", "end": "2023-12-31"},
    {"subperiod_key": "2024_2026", "label": "2024-2026", "start": "2024-01-01", "end": "2026-12-31"},
]

FOCUS_SET = [
    {
        "strategy_key": "p5",
        "strategy_name": "P5 Cash-Aware Copy",
        "portfolio_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv",
        "benchmark_key": "SPY",
    },
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_portfolio_timeline.csv",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_portfolio_timeline.csv",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "portfolio_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_portfolio_daily.csv",
        "benchmark_key": "VT",
        "secondary_benchmark_key": "SPY",
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


def load_spy_lookup() -> dict[str, float]:
    return {
        row["date"]: to_float(row["close"])
        for row in read_csv(PIF_BENCHMARK_PATH)
        if row["benchmark_key"] == "SPY" and row["adjust_mode"] == "all"
    }


def load_vt_lookup() -> dict[str, float]:
    return {
        row["date"]: to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["instrument_key"] == "benchmark_vt" and row["adjust_mode"] == "all"
    }


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


def select_subperiod_rows(rows: list[dict[str, str]], start: str, end: str) -> list[dict[str, str]]:
    return [row for row in rows if start <= row["date"] <= end]


def drawdown_field(row: dict[str, str]) -> float:
    if "drawdown_to_date" in row:
        return to_float(row["drawdown_to_date"])
    return to_float(row.get("drawdown", 0.0))


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


def build_subperiod_daily_rows(
    strategy_key: str,
    strategy_name: str,
    subperiod: dict[str, str],
    portfolio_rows: list[dict[str, str]],
    benchmark_key: str,
    benchmark_lookup: dict[str, float],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    period_rows = select_subperiod_rows(portfolio_rows, subperiod["start"], subperiod["end"])
    if len(period_rows) < 2:
        raise RuntimeError(
            f"Not enough rows for {strategy_key} in subperiod {subperiod['subperiod_key']}: {len(period_rows)}"
        )
    dates = [row["date"] for row in period_rows]
    benchmark_series = build_benchmark_series(dates, benchmark_lookup)
    benchmark_by_date = dict(benchmark_series)
    common_dates = [date for date in dates if date in benchmark_by_date]
    if len(common_dates) < 2:
        raise RuntimeError(
            f"Not enough benchmark-aligned rows for {strategy_key} in subperiod {subperiod['subperiod_key']}"
        )

    portfolio_by_date = {row["date"]: row for row in period_rows}
    aligned_rows = [portfolio_by_date[date] for date in common_dates]

    strategy_start_nav = to_float(aligned_rows[0]["nav_end"])
    benchmark_start_close = benchmark_by_date[common_dates[0]]
    peak_rebased_nav = 1.0
    peak_rebased_benchmark = 1.0
    daily_rows: list[dict[str, str]] = []

    for row in aligned_rows:
        date = row["date"]
        nav_end = to_float(row["nav_end"])
        benchmark_close = benchmark_by_date[date]
        strategy_rebased_nav = nav_end / strategy_start_nav if strategy_start_nav else 0.0
        benchmark_rebased_nav = benchmark_close / benchmark_start_close if benchmark_start_close else 0.0
        peak_rebased_nav = max(peak_rebased_nav, strategy_rebased_nav)
        peak_rebased_benchmark = max(peak_rebased_benchmark, benchmark_rebased_nav)
        daily_rows.append(
            {
                "strategy_key": strategy_key,
                "strategy_name": strategy_name,
                "subperiod_key": subperiod["subperiod_key"],
                "subperiod_label": subperiod["label"],
                "date": date,
                "nav_end": f"{nav_end:.12f}",
                "strategy_rebased_nav": f"{strategy_rebased_nav:.12f}",
                "benchmark_key": benchmark_key,
                "benchmark_close": f"{benchmark_close:.12f}",
                "benchmark_rebased_nav": f"{benchmark_rebased_nav:.12f}",
                "relative_excess_nav": f"{(strategy_rebased_nav - benchmark_rebased_nav):.12f}",
                "cash_weight_end": f"{cash_weight_field(row):.12f}",
                "gross_exposure_end": f"{gross_exposure_field(row):.12f}",
                "strategy_drawdown_subperiod": f"{(strategy_rebased_nav / peak_rebased_nav - 1.0):.12f}",
                "benchmark_drawdown_subperiod": f"{(benchmark_rebased_nav / peak_rebased_benchmark - 1.0):.12f}",
            }
        )

    final_strategy_nav = to_float(daily_rows[-1]["strategy_rebased_nav"])
    final_benchmark_nav = to_float(daily_rows[-1]["benchmark_rebased_nav"])
    summary_row = {
        "strategy_key": strategy_key,
        "strategy_name": strategy_name,
        "subperiod_key": subperiod["subperiod_key"],
        "subperiod_label": subperiod["label"],
        "subperiod_start_date": common_dates[0],
        "subperiod_end_date": common_dates[-1],
        "row_count": str(len(daily_rows)),
        "benchmark_key": benchmark_key,
        "strategy_total_return": f"{(final_strategy_nav - 1.0):.12f}",
        "benchmark_total_return": f"{(final_benchmark_nav - 1.0):.12f}",
        "excess_total_return": f"{((final_strategy_nav - 1.0) - (final_benchmark_nav - 1.0)):.12f}",
        "strategy_max_drawdown": f"{min(to_float(r['strategy_drawdown_subperiod']) for r in daily_rows):.12f}",
        "benchmark_max_drawdown": f"{min(to_float(r['benchmark_drawdown_subperiod']) for r in daily_rows):.12f}",
        "avg_cash_weight": f"{(sum(to_float(r['cash_weight_end']) for r in daily_rows) / len(daily_rows)):.12f}",
        "avg_gross_exposure": f"{(sum(to_float(r['gross_exposure_end']) for r in daily_rows) / len(daily_rows)):.12f}",
    }
    return daily_rows, summary_row


def build_secondary_summary(
    strategy_key: str,
    subperiod_key: str,
    daily_rows: list[dict[str, str]],
    benchmark_key: str,
    benchmark_lookup: dict[str, float],
) -> dict[tuple[str, str], str]:
    dates = [row["date"] for row in daily_rows]
    benchmark_series = build_benchmark_series(dates, benchmark_lookup)
    benchmark_by_date = dict(benchmark_series)
    common_dates = [date for date in dates if date in benchmark_by_date]
    if len(common_dates) < 2:
        raise RuntimeError(f"Not enough secondary benchmark rows for {strategy_key} in {subperiod_key}")
    start_close = benchmark_by_date[common_dates[0]]
    end_close = benchmark_by_date[common_dates[-1]]
    benchmark_total_return = end_close / start_close - 1.0
    strategy_total_return = to_float(daily_rows[-1]["strategy_rebased_nav"]) - 1.0
    return {
        ("secondary_benchmark_key", ""): benchmark_key,
        ("secondary_benchmark_total_return", ""): f"{benchmark_total_return:.12f}",
        ("secondary_excess_total_return", ""): f"{(strategy_total_return - benchmark_total_return):.12f}",
    }


def main() -> None:
    spy_lookup = load_spy_lookup()
    vt_lookup = load_vt_lookup()

    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for config in FOCUS_SET:
        portfolio_rows = read_csv(Path(config["portfolio_path"]))
        benchmark_lookup = spy_lookup if config["benchmark_key"] == "SPY" else vt_lookup
        for subperiod in SUBPERIODS:
            period_daily, period_summary = build_subperiod_daily_rows(
                config["strategy_key"],
                config["strategy_name"],
                subperiod,
                portfolio_rows,
                config["benchmark_key"],
                benchmark_lookup,
            )
            if "secondary_benchmark_key" in config:
                secondary_lookup = spy_lookup if config["secondary_benchmark_key"] == "SPY" else vt_lookup
                secondary = build_secondary_summary(
                    config["strategy_key"],
                    subperiod["subperiod_key"],
                    period_daily,
                    str(config["secondary_benchmark_key"]),
                    secondary_lookup,
                )
                period_summary["secondary_benchmark_key"] = secondary[("secondary_benchmark_key", "")]
                period_summary["secondary_benchmark_total_return"] = secondary[("secondary_benchmark_total_return", "")]
                period_summary["secondary_excess_total_return"] = secondary[("secondary_excess_total_return", "")]
            else:
                period_summary["secondary_benchmark_key"] = ""
                period_summary["secondary_benchmark_total_return"] = ""
                period_summary["secondary_excess_total_return"] = ""

            summary_rows.append(period_summary)
            daily_rows.extend(period_daily)

            audit_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "subperiod_key": subperiod["subperiod_key"],
                    "check_type": "minimum_row_count",
                    "status": "pass" if int(period_summary["row_count"]) >= 2 else "fail",
                    "expected_value": ">=2",
                    "actual_value": period_summary["row_count"],
                    "difference": "0.000000000000",
                    "note": "Each subperiod needs at least two aligned observations.",
                }
            )
            audit_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "subperiod_key": subperiod["subperiod_key"],
                    "check_type": "date_order",
                    "status": "pass" if period_summary["subperiod_start_date"] <= period_summary["subperiod_end_date"] else "fail",
                    "expected_value": "start<=end",
                    "actual_value": f"{period_summary['subperiod_start_date']}->{period_summary['subperiod_end_date']}",
                    "difference": "0.000000000000",
                    "note": "Aligned subperiod dates must be ordered correctly.",
                }
            )
            first_daily = period_daily[0]
            audit_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "subperiod_key": subperiod["subperiod_key"],
                    "check_type": "rebase_anchor",
                    "status": "pass"
                    if abs(to_float(first_daily["strategy_rebased_nav"]) - 1.0) < 1e-9
                    and abs(to_float(first_daily["benchmark_rebased_nav"]) - 1.0) < 1e-9
                    else "fail",
                    "expected_value": "1.000000000000/1.000000000000",
                    "actual_value": f"{first_daily['strategy_rebased_nav']}/{first_daily['benchmark_rebased_nav']}",
                    "difference": "0.000000000000",
                    "note": "Both strategy and benchmark must rebase to 1.0 on the first aligned subperiod date.",
                }
            )

    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(DAILY_PATH, daily_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 A4: Subperiod Stability\n\n"
        "This layer tests whether the validated focus-set strategies behave consistently across distinct market regimes.\n\n"
        "## Focus set\n\n"
        "- `P5` Cash-Aware Copy\n"
        "- `N4` Industry Weight-Change Tilt\n"
        "- `N6` Top-3 Industry Leaders\n"
        "- `S1` Exposure Regime Overlay\n\n"
        "## Method\n\n"
        "A4 does not re-run the strategies. It uses the validated baseline portfolio timelines already stored in the repo and slices them into the planned subperiods:\n\n"
        "- `2019-2021`\n"
        "- `2022-2023`\n"
        "- `2024-2026`\n\n"
        "For each strategy and subperiod:\n\n"
        "1. keep only baseline portfolio rows whose dates fall inside the subperiod;\n"
        "2. align the benchmark using the same carry-forward benchmark-series logic used in prior robustness steps;\n"
        "3. rebase both strategy NAV and benchmark NAV to `1.0` on the first aligned subperiod date;\n"
        "4. compute subperiod total return, benchmark total return, excess total return, max drawdown, average cash weight, and average gross exposure.\n\n"
        "## Outputs\n\n"
        "- `data/processed/robustness/subperiod_summary.csv`\n"
        "- `data/processed/robustness/subperiod_daily.csv`\n"
        "- `data/processed/robustness/subperiod_audit.csv`\n\n"
        "## Validation\n\n"
        "The audit checks that each strategy/subperiod combination has at least two aligned rows, that aligned dates remain ordered, and that both strategy and benchmark rebase to `1.0` on the first aligned date.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
