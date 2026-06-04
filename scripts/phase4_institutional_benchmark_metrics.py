from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "data" / "processed" / "inference" / "institutional_benchmark_series_daily.csv"
OUT_DIR = ROOT / "data" / "processed" / "inference"
SUMMARY_PATH = OUT_DIR / "institutional_benchmark_summary.csv"
DAILY_PATH = OUT_DIR / "institutional_benchmark_daily.csv"
MONTHLY_PATH = OUT_DIR / "institutional_benchmark_monthly.csv"
AUDIT_PATH = OUT_DIR / "institutional_benchmark_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase4-institutional-benchmark-metrics.md"
PIF_DAILY_COMPARISON_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "analysis" / "strategy_vs_benchmark_daily.csv"
ROBUSTNESS_BENCHMARK_SUMMARY_PATH = ROOT / "data" / "processed" / "robustness" / "benchmark_comparison_summary.csv"

STRATEGY_CONFIGS = [
    {
        "strategy_key": "p2",
        "strategy_name": "P2 Full Sleeve Equal Weight",
        "portfolio_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p2_equal_weight" / "p2ew_portfolio_daily.csv",
        "market_benchmark_key": "SPY",
        "cash_benchmark_key": "BIL",
        "defensive_benchmark_key": "USMV",
        "family": "pif",
    },
    {
        "strategy_key": "p5",
        "strategy_name": "P5 Cash-Aware Copy",
        "portfolio_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv",
        "market_benchmark_key": "SPY",
        "cash_benchmark_key": "BIL",
        "defensive_benchmark_key": "USMV",
        "family": "pif",
    },
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_portfolio_timeline.csv",
        "market_benchmark_key": "VT",
        "cash_benchmark_key": "BIL",
        "defensive_benchmark_key": "ACWV",
        "family": "nbim",
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_portfolio_timeline.csv",
        "market_benchmark_key": "VT",
        "cash_benchmark_key": "BIL",
        "defensive_benchmark_key": "ACWV",
        "family": "nbim",
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "portfolio_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_portfolio_daily.csv",
        "market_benchmark_key": "VT",
        "cash_benchmark_key": "BIL",
        "defensive_benchmark_key": "ACWV",
        "family": "combined",
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
    for current_date in dates:
        while pointer < len(sorted_dates) and sorted_dates[pointer] <= current_date:
            latest_price = benchmark_lookup[sorted_dates[pointer]]
            pointer += 1
        if latest_price is None:
            continue
        rows.append((current_date, latest_price))
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


def build_month_end_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_month: dict[str, dict[str, str]] = {}
    for row in rows:
        month_key = row["date"][:7]
        existing = by_month.get(month_key)
        if existing is None or row["date"] > existing["date"]:
            by_month[month_key] = row
    return [by_month[key] for key in sorted(by_month)]


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def annualized_ratio(mean_value: float, std_value: float, periods_per_year: float) -> float:
    if std_value <= 0 or periods_per_year <= 0:
        return 0.0
    return mean_value / std_value * math.sqrt(periods_per_year)


def downside_deviation(values: list[float]) -> float:
    negatives = [min(value, 0.0) for value in values]
    if not negatives:
        return 0.0
    return math.sqrt(sum(value * value for value in negatives) / len(negatives))


def rolling_total_return(nav_series: list[float], horizon_months: int) -> float:
    if len(nav_series) <= horizon_months:
        return 0.0
    worst = math.inf
    for idx in range(horizon_months, len(nav_series)):
        start_nav = nav_series[idx - horizon_months]
        end_nav = nav_series[idx]
        if start_nav <= 0:
            continue
        total_return = end_nav / start_nav - 1.0
        worst = min(worst, total_return)
    return 0.0 if worst is math.inf else worst


def max_recovery_days(dates: list[str], navs: list[float]) -> int:
    peak_nav = -math.inf
    peak_date = None
    in_drawdown = False
    longest = 0
    for current_date_str, nav in zip(dates, navs):
        current_date = date.fromisoformat(current_date_str)
        if nav >= peak_nav:
            if in_drawdown and peak_date is not None:
                longest = max(longest, (current_date - peak_date).days)
            peak_nav = nav
            peak_date = current_date
            in_drawdown = False
        else:
            in_drawdown = True
            if peak_date is not None:
                longest = max(longest, (current_date - peak_date).days)
    return longest


def monthly_capture(strategy_returns: list[float], benchmark_returns: list[float], mode: str) -> float:
    if mode == "down":
        pairs = [(s, b) for s, b in zip(strategy_returns, benchmark_returns) if b < 0]
    elif mode == "up":
        pairs = [(s, b) for s, b in zip(strategy_returns, benchmark_returns) if b > 0]
    else:
        raise ValueError(f"Unsupported capture mode: {mode}")
    if not pairs:
        return 0.0
    benchmark_mean = statistics.fmean(b for _, b in pairs)
    if abs(benchmark_mean) < 1e-12:
        return 0.0
    strategy_mean = statistics.fmean(s for s, _ in pairs)
    return strategy_mean / benchmark_mean


def load_benchmark_lookups() -> dict[str, dict[str, float]]:
    lookups: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv(BENCHMARK_PATH):
        lookups[row["benchmark_key"]][row["date"]] = to_float(row["close"])
    return lookups


def validated_market_totals(config: dict[str, str]) -> tuple[float, float]:
    strategy_key = config["strategy_key"]
    market_key = config["market_benchmark_key"]

    if config["family"] == "pif":
        rows = read_csv(PIF_DAILY_COMPARISON_PATH)
        series = [row for row in rows if row["strategy_key"] == strategy_key and row["benchmark_key"] == market_key]
        if not series:
            raise RuntimeError(f"Missing validated PIF daily comparison for {strategy_key}")
        final_row = series[-1]
        return to_float(final_row["strategy_nav"]) - 1.0, to_float(final_row["benchmark_nav"]) - 1.0

    rows = read_csv(ROBUSTNESS_BENCHMARK_SUMMARY_PATH)
    for row in rows:
        if row["strategy_key"] == strategy_key and row["benchmark_key"] == market_key:
            return to_float(row["strategy_total_return"]), to_float(row["benchmark_total_return"])

    raise RuntimeError(f"Missing validated robustness benchmark summary for {strategy_key} vs {market_key}")


def summarize_strategy(
    config: dict[str, str],
    portfolio_rows: list[dict[str, str]],
    benchmark_lookups: dict[str, dict[str, float]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str], list[dict[str, str]]]:
    market_key = config["market_benchmark_key"]
    cash_key = config["cash_benchmark_key"]
    defensive_key = config["defensive_benchmark_key"]
    dates = [row["date"] for row in portfolio_rows]
    market_series = build_benchmark_series(dates, benchmark_lookups[market_key])
    cash_series = build_benchmark_series(dates, benchmark_lookups[cash_key])
    defensive_series = build_benchmark_series(dates, benchmark_lookups[defensive_key])
    if len(market_series) < 2 or len(cash_series) < 2 or len(defensive_series) < 2:
        raise RuntimeError(f"Not enough benchmark rows for {config['strategy_key']}")

    portfolio_by_date = {row["date"]: row for row in portfolio_rows}
    common_dates = sorted(
        set(date_value for date_value, _ in market_series)
        & set(date_value for date_value, _ in cash_series)
        & set(date_value for date_value, _ in defensive_series)
        & set(portfolio_by_date)
    )
    if len(common_dates) < 2:
        raise RuntimeError(f"Not enough aligned dates for {config['strategy_key']}")

    aligned_rows = [portfolio_by_date[current_date] for current_date in common_dates]
    market_lookup = dict(market_series)
    cash_lookup = dict(cash_series)
    defensive_lookup = dict(defensive_series)

    strategy_start_nav = to_float(aligned_rows[0]["nav_end"])
    market_start_close = market_lookup[common_dates[0]]
    cash_start_close = cash_lookup[common_dates[0]]
    defensive_start_close = defensive_lookup[common_dates[0]]

    daily_rows: list[dict[str, str]] = []
    for row in aligned_rows:
        current_date = row["date"]
        nav_end = to_float(row["nav_end"])
        market_close = market_lookup[current_date]
        cash_close = cash_lookup[current_date]
        defensive_close = defensive_lookup[current_date]
        strategy_rebased = nav_end / strategy_start_nav if strategy_start_nav else 0.0
        market_rebased = market_close / market_start_close if market_start_close else 0.0
        cash_rebased = cash_close / cash_start_close if cash_start_close else 0.0
        defensive_rebased = defensive_close / defensive_start_close if defensive_start_close else 0.0
        daily_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "strategy_name": config["strategy_name"],
                "date": current_date,
                "nav_end": f"{nav_end:.12f}",
                "strategy_rebased_nav": f"{strategy_rebased:.12f}",
                "market_benchmark_key": market_key,
                "market_benchmark_nav": f"{market_rebased:.12f}",
                "cash_benchmark_key": cash_key,
                "cash_benchmark_nav": f"{cash_rebased:.12f}",
                "defensive_benchmark_key": defensive_key,
                "defensive_benchmark_nav": f"{defensive_rebased:.12f}",
                "cash_weight_end": f"{cash_weight_field(row):.12f}",
                "gross_exposure_end": f"{gross_exposure_field(row):.12f}",
                "drawdown_to_date": f"{drawdown_field(row):.12f}",
            }
        )

    prev_row = daily_rows[0]
    daily_excess_vs_cash: list[float] = []
    daily_strategy_returns: list[float] = []
    for row in daily_rows[1:]:
        strategy_return = to_float(row["strategy_rebased_nav"]) / to_float(prev_row["strategy_rebased_nav"]) - 1.0
        cash_return = to_float(row["cash_benchmark_nav"]) / to_float(prev_row["cash_benchmark_nav"]) - 1.0
        daily_strategy_returns.append(strategy_return)
        daily_excess_vs_cash.append(strategy_return - cash_return)
        prev_row = row

    start_dt = date.fromisoformat(common_dates[0])
    end_dt = date.fromisoformat(common_dates[-1])
    years = (end_dt - start_dt).days / 365.25
    periods_per_year = (len(daily_rows) - 1) / years if years > 0 else 0.0

    monthly_rows = build_month_end_rows(daily_rows)
    monthly_out_rows: list[dict[str, str]] = []
    prev_month = monthly_rows[0]
    strategy_monthly_returns: list[float] = []
    market_monthly_returns: list[float] = []
    for row in monthly_rows:
        if row is monthly_rows[0]:
            monthly_out_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "strategy_name": config["strategy_name"],
                    "month_end_date": row["date"],
                    "strategy_month_end_nav": row["strategy_rebased_nav"],
                    "market_month_end_nav": row["market_benchmark_nav"],
                    "cash_month_end_nav": row["cash_benchmark_nav"],
                    "defensive_month_end_nav": row["defensive_benchmark_nav"],
                    "strategy_month_return": "",
                    "market_month_return": "",
                    "cash_month_return": "",
                    "defensive_month_return": "",
                }
            )
            continue
        strategy_month_return = to_float(row["strategy_rebased_nav"]) / to_float(prev_month["strategy_rebased_nav"]) - 1.0
        market_month_return = to_float(row["market_benchmark_nav"]) / to_float(prev_month["market_benchmark_nav"]) - 1.0
        cash_month_return = to_float(row["cash_benchmark_nav"]) / to_float(prev_month["cash_benchmark_nav"]) - 1.0
        defensive_month_return = (
            to_float(row["defensive_benchmark_nav"]) / to_float(prev_month["defensive_benchmark_nav"]) - 1.0
        )
        strategy_monthly_returns.append(strategy_month_return)
        market_monthly_returns.append(market_month_return)
        monthly_out_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "strategy_name": config["strategy_name"],
                "month_end_date": row["date"],
                "strategy_month_end_nav": row["strategy_rebased_nav"],
                "market_month_end_nav": row["market_benchmark_nav"],
                "cash_month_end_nav": row["cash_benchmark_nav"],
                "defensive_month_end_nav": row["defensive_benchmark_nav"],
                "strategy_month_return": f"{strategy_month_return:.12f}",
                "market_month_return": f"{market_month_return:.12f}",
                "cash_month_return": f"{cash_month_return:.12f}",
                "defensive_month_return": f"{defensive_month_return:.12f}",
            }
        )
        prev_month = row

    final_strategy_nav = to_float(daily_rows[-1]["strategy_rebased_nav"])
    final_market_nav = to_float(daily_rows[-1]["market_benchmark_nav"])
    final_cash_nav = to_float(daily_rows[-1]["cash_benchmark_nav"])
    final_defensive_nav = to_float(daily_rows[-1]["defensive_benchmark_nav"])

    downside_dev = downside_deviation(daily_excess_vs_cash)
    mean_excess_vs_cash = statistics.fmean(daily_excess_vs_cash) if daily_excess_vs_cash else 0.0
    sortino_excess_vs_cash = annualized_ratio(mean_excess_vs_cash, downside_dev, periods_per_year)
    strategy_total_return = final_strategy_nav - 1.0
    market_total_return = final_market_nav - 1.0
    cash_total_return = final_cash_nav - 1.0
    defensive_total_return = final_defensive_nav - 1.0
    cagr = final_strategy_nav ** (1.0 / years) - 1.0 if years > 0 and final_strategy_nav > 0 else 0.0
    annualized_volatility = sample_std(daily_strategy_returns) * math.sqrt(periods_per_year) if periods_per_year > 0 else 0.0
    max_drawdown = min(to_float(row["drawdown_to_date"]) for row in daily_rows)
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0
    positive_month_rate = (
        sum(1 for value in strategy_monthly_returns if value > 0) / len(strategy_monthly_returns)
        if strategy_monthly_returns
        else 0.0
    )
    worst_3m = rolling_total_return([to_float(row["strategy_month_end_nav"]) for row in monthly_out_rows], 3)
    worst_6m = rolling_total_return([to_float(row["strategy_month_end_nav"]) for row in monthly_out_rows], 6)
    worst_12m = rolling_total_return([to_float(row["strategy_month_end_nav"]) for row in monthly_out_rows], 12)
    recovery_days = max_recovery_days(
        [row["date"] for row in daily_rows],
        [to_float(row["strategy_rebased_nav"]) for row in daily_rows],
    )

    summary_row = {
        "strategy_key": config["strategy_key"],
        "strategy_name": config["strategy_name"],
        "market_benchmark_key": market_key,
        "cash_benchmark_key": cash_key,
        "defensive_benchmark_key": defensive_key,
        "start_date": common_dates[0],
        "end_date": common_dates[-1],
        "row_count": str(len(daily_rows)),
        "month_count": str(len(strategy_monthly_returns)),
        "strategy_total_return": f"{strategy_total_return:.12f}",
        "market_total_return": f"{market_total_return:.12f}",
        "cash_total_return": f"{cash_total_return:.12f}",
        "defensive_total_return": f"{defensive_total_return:.12f}",
        "excess_total_return_vs_market": f"{(strategy_total_return - market_total_return):.12f}",
        "excess_total_return_vs_cash": f"{(strategy_total_return - cash_total_return):.12f}",
        "excess_total_return_vs_defensive": f"{(strategy_total_return - defensive_total_return):.12f}",
        "cagr": f"{cagr:.12f}",
        "annualized_volatility": f"{annualized_volatility:.12f}",
        "max_drawdown": f"{max_drawdown:.12f}",
        "calmar_ratio": f"{calmar_ratio:.12f}",
        "sortino_excess_vs_cash": f"{sortino_excess_vs_cash:.12f}",
        "downside_capture_vs_market": f"{monthly_capture(strategy_monthly_returns, market_monthly_returns, 'down'):.12f}",
        "upside_capture_vs_market": f"{monthly_capture(strategy_monthly_returns, market_monthly_returns, 'up'):.12f}",
        "positive_month_rate": f"{positive_month_rate:.12f}",
        "worst_3m_total_return": f"{worst_3m:.12f}",
        "worst_6m_total_return": f"{worst_6m:.12f}",
        "worst_12m_total_return": f"{worst_12m:.12f}",
        "max_recovery_days": str(recovery_days),
        "avg_cash_weight": f"{(sum(to_float(row['cash_weight_end']) for row in daily_rows) / len(daily_rows)):.12f}",
        "avg_gross_exposure": f"{(sum(to_float(row['gross_exposure_end']) for row in daily_rows) / len(daily_rows)):.12f}",
    }

    expected_strategy_total, expected_market_total = validated_market_totals(config)
    expected_market_excess = expected_strategy_total - expected_market_total

    audit_rows = [
        {
            "strategy_key": config["strategy_key"],
            "check_name": "strategy_total_matches_validated_source",
            "status": "pass" if abs(strategy_total_return - expected_strategy_total) < 1e-10 else "fail",
            "detail": f"computed={strategy_total_return:.12f} expected={expected_strategy_total:.12f}",
        },
        {
            "strategy_key": config["strategy_key"],
            "check_name": "market_total_matches_validated_source",
            "status": "pass" if abs(market_total_return - expected_market_total) < 1e-10 else "fail",
            "detail": f"computed={market_total_return:.12f} expected={expected_market_total:.12f}",
        },
        {
            "strategy_key": config["strategy_key"],
            "check_name": "market_excess_matches_validated_summary",
            "status": "pass"
            if abs((strategy_total_return - market_total_return) - expected_market_excess) < 1e-10
            else "fail",
            "detail": (
                f"computed={strategy_total_return - market_total_return:.12f} "
                f"expected={expected_market_excess:.12f}"
            ),
        },
        {
            "strategy_key": config["strategy_key"],
            "check_name": "aligned_rebase_anchor",
            "status": "pass"
            if abs(to_float(daily_rows[0]["strategy_rebased_nav"]) - 1.0) < 1e-10
            and abs(to_float(daily_rows[0]["market_benchmark_nav"]) - 1.0) < 1e-10
            and abs(to_float(daily_rows[0]["cash_benchmark_nav"]) - 1.0) < 1e-10
            and abs(to_float(daily_rows[0]["defensive_benchmark_nav"]) - 1.0) < 1e-10
            else "fail",
            "detail": (
                f"strategy={daily_rows[0]['strategy_rebased_nav']} "
                f"market={daily_rows[0]['market_benchmark_nav']} "
                f"cash={daily_rows[0]['cash_benchmark_nav']} "
                f"defensive={daily_rows[0]['defensive_benchmark_nav']}"
            ),
        },
        {
            "strategy_key": config["strategy_key"],
            "check_name": "monthly_series_nonempty",
            "status": "pass" if len(strategy_monthly_returns) >= 12 else "fail",
            "detail": f"month_count={len(strategy_monthly_returns)}",
        },
    ]
    return daily_rows, monthly_out_rows, summary_row, audit_rows


def main() -> None:
    benchmark_lookups = load_benchmark_lookups()

    daily_rows: list[dict[str, str]] = []
    monthly_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for config in STRATEGY_CONFIGS:
        portfolio_rows = read_csv(Path(config["portfolio_path"]))
        strategy_daily, strategy_monthly, summary_row, strategy_audit = summarize_strategy(
            config,
            portfolio_rows,
            benchmark_lookups,
        )
        daily_rows.extend(strategy_daily)
        monthly_rows.extend(strategy_monthly)
        summary_rows.append(summary_row)
        audit_rows.extend(strategy_audit)

    write_csv(DAILY_PATH, daily_rows)
    write_csv(MONTHLY_PATH, monthly_rows)
    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 4: Institutional Benchmark Metrics\n\n"
        "This layer asks whether the surviving strategies look useful under a more institutional lens, not just a pure market-beating lens.\n\n"
        "## Focus set\n\n"
        "- `P2` as the strongest absolute-return PIF sleeve.\n"
        "- `P5` as the cash-aware PIF copy variant.\n"
        "- `N4` and `N6` as the strongest realistic NBIM sleeves.\n"
        "- `S1` as the main combined cross-fund overlay.\n\n"
        "## Benchmark families\n\n"
        "- Market opportunity cost: `SPY` for PIF, `VT` for NBIM and combined strategies.\n"
        "- Cash hurdle: `BIL`.\n"
        "- Defensive equity comparator: `USMV` for PIF, `ACWV` for NBIM and combined.\n\n"
        "## Metrics\n\n"
        "- Total return and CAGR.\n"
        "- Annualized volatility and max drawdown.\n"
        "- Calmar ratio.\n"
        "- Sortino ratio computed on daily excess return over the cash hurdle.\n"
        "- Monthly downside and upside capture relative to the market benchmark.\n"
        "- Positive month rate.\n"
        "- Worst rolling 3-month, 6-month, and 12-month total returns.\n"
        "- Maximum recovery duration in days.\n\n"
        "## Validation\n\n"
        "The market-relative excess return for each strategy is reconciled back to the already validated benchmark summary layer. "
        "This ensures the new benchmark expansion is built on the same aligned live windows rather than silently changing the original market comparison.\n\n"
        "## Outputs\n\n"
        "- `data/processed/inference/institutional_benchmark_daily.csv`\n"
        "- `data/processed/inference/institutional_benchmark_monthly.csv`\n"
        "- `data/processed/inference/institutional_benchmark_summary.csv`\n"
        "- `data/processed/inference/institutional_benchmark_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
