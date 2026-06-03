from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

import nbim_backtest_runner as nbim_runner
import pif_backtest_p5_cash_aware_copy_engine as p5_runner
import swf_phase2_backtest_runner as combined_runner


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
DETAIL_ROOT = ROBUSTNESS_ROOT / "execution_lag_detail"
SUMMARY_PATH = ROBUSTNESS_ROOT / "execution_lag_summary.csv"
DAILY_PATH = ROBUSTNESS_ROOT / "execution_lag_daily.csv"
AUDIT_PATH = ROBUSTNESS_ROOT / "execution_lag_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-execution-lag.md"

PIF_BENCHMARK_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"
PIF_TRADE_CALENDAR_PATH = ROOT / "data" / "processed" / "pif" / "pif_trade_calendar.csv"
S1_BASELINE_PATH = ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_summary.json"
P5_BASELINE_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_summary.json"
N4_BASELINE_PATH = ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_summary.json"
N6_BASELINE_PATH = ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_summary.json"

VARIANTS = [
    {"variant_key": "t1", "label": "T+1", "signal_offset": 1, "event_extra_offset": 0},
    {"variant_key": "t3", "label": "T+3", "signal_offset": 3, "event_extra_offset": 2},
    {"variant_key": "t5", "label": "T+5", "signal_offset": 5, "event_extra_offset": 4},
]

FOCUS_SET = [
    {"strategy_key": "p5", "strategy_name": "P5 Cash-Aware Copy", "benchmark_key": "SPY"},
    {"strategy_key": "n4", "strategy_name": "N4 Industry Weight-Change Tilt", "benchmark_key": "VT"},
    {"strategy_key": "n6", "strategy_name": "N6 Top-3 Industry Leaders", "benchmark_key": "VT"},
    {"strategy_key": "s1", "strategy_name": "S1 Exposure Regime Overlay", "benchmark_key": "VT", "secondary_benchmark_key": "SPY"},
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


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def nth_trading_day_after(anchor_date: str, calendar_dates: list[str], count_after: int) -> str:
    future_dates = [date for date in calendar_dates if date > anchor_date]
    if len(future_dates) < count_after:
        raise RuntimeError(f"Not enough dates after {anchor_date} for count {count_after}")
    return future_dates[count_after - 1]


def shift_existing_trade_date(trade_date: str, calendar_dates: list[str], extra_days: int) -> str:
    if extra_days == 0:
        return trade_date
    try:
        index = calendar_dates.index(trade_date)
    except ValueError as exc:
        raise RuntimeError(f"Trade date {trade_date} not in shared calendar") from exc
    shifted_index = index + extra_days
    if shifted_index >= len(calendar_dates):
        raise RuntimeError(f"Cannot shift {trade_date} by {extra_days} days")
    return calendar_dates[shifted_index]


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
    rows: list[tuple[str, float]] = []
    latest_price = None
    pointer = 0
    for date in dates:
        while pointer < len(sorted_dates) and sorted_dates[pointer] <= date:
            latest_price = benchmark_lookup[sorted_dates[pointer]]
            pointer += 1
        if latest_price is None:
            continue
        rows.append((date, latest_price))
    if not rows:
        raise RuntimeError("No benchmark prices available for requested dates")
    return rows


def summarize_against_benchmark(
    portfolio_rows: list[dict[str, str]],
    benchmark_key: str,
    benchmark_lookup: dict[str, float],
) -> dict[str, float | str]:
    dates = [row["date"] for row in portfolio_rows]
    bench_series = build_benchmark_series(dates, benchmark_lookup)
    common_dates = [date for date, _ in bench_series]
    portfolio_by_date = {row["date"]: row for row in portfolio_rows}
    if common_dates != dates:
        portfolio_rows = [portfolio_by_date[date] for date in common_dates]
    benchmark_by_date = dict(bench_series)
    start_price = benchmark_by_date[common_dates[0]]
    end_price = benchmark_by_date[common_dates[-1]]
    benchmark_total_return = end_price / start_price - 1.0
    final_nav = to_float(portfolio_rows[-1]["nav_end"])
    total_return = final_nav - 1.0
    avg_cash_weight = sum(
        to_float(
            row.get(
                "cash_weight_end",
                f"{(to_float(row.get('cash_end', 0.0)) / to_float(row['nav_end'])) if to_float(row['nav_end']) else 0.0:.12f}",
            )
        )
        for row in portfolio_rows
    ) / len(portfolio_rows)
    max_drawdown = min(
        to_float(row.get("drawdown_to_date", row.get("drawdown", 0.0)))
        for row in portfolio_rows
    )
    return {
        "benchmark_key": benchmark_key,
        "benchmark_start_date": common_dates[0],
        "benchmark_end_date": common_dates[-1],
        "benchmark_start_close": start_price,
        "benchmark_end_close": end_price,
        "benchmark_total_return": benchmark_total_return,
        "total_return": total_return,
        "excess_total_return": total_return - benchmark_total_return,
        "avg_cash_weight": avg_cash_weight,
        "max_drawdown": max_drawdown,
    }


def run_p5_variant(variant: dict[str, object], audit_rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    price_rows = p5_runner.read_csv(p5_runner.PRICE_PATH)
    calendar_dates = p5_runner.load_price_calendar(price_rows, "all")
    calendar_rows = p5_runner.read_csv(PIF_TRADE_CALENDAR_PATH)
    lagged_map = {
        row["signal_date"]: nth_trading_day_after(row["signal_date"], calendar_dates, int(variant["signal_offset"]))
        for row in calendar_rows
    }
    collision_count = len(lagged_map.values()) - len(set(lagged_map.values()))
    detail_dir = DETAIL_ROOT / "p5" / str(variant["variant_key"])
    detail_dir.mkdir(parents=True, exist_ok=True)
    old_paths = {
        "ELIGIBILITY_PATH": p5_runner.ELIGIBILITY_PATH,
        "REBALANCES_PATH": p5_runner.REBALANCES_PATH,
        "ORDERS_PATH": p5_runner.ORDERS_PATH,
        "HOLDINGS_DAILY_PATH": p5_runner.HOLDINGS_DAILY_PATH,
        "PORTFOLIO_DAILY_PATH": p5_runner.PORTFOLIO_DAILY_PATH,
        "SUMMARY_PATH": p5_runner.SUMMARY_PATH,
        "load_trade_date_map": p5_runner.load_trade_date_map,
    }
    try:
        p5_runner.ELIGIBILITY_PATH = detail_dir / "p5_signal_eligibility.csv"
        p5_runner.REBALANCES_PATH = detail_dir / "p5_rebalance_events.csv"
        p5_runner.ORDERS_PATH = detail_dir / "p5_orders.csv"
        p5_runner.HOLDINGS_DAILY_PATH = detail_dir / "p5_holdings_daily.csv"
        p5_runner.PORTFOLIO_DAILY_PATH = detail_dir / "p5_portfolio_daily.csv"
        p5_runner.SUMMARY_PATH = detail_dir / "p5_summary.json"
        p5_runner.load_trade_date_map = lambda _rows: lagged_map
        p5_runner.run_backtest()
    finally:
        p5_runner.ELIGIBILITY_PATH = old_paths["ELIGIBILITY_PATH"]
        p5_runner.REBALANCES_PATH = old_paths["REBALANCES_PATH"]
        p5_runner.ORDERS_PATH = old_paths["ORDERS_PATH"]
        p5_runner.HOLDINGS_DAILY_PATH = old_paths["HOLDINGS_DAILY_PATH"]
        p5_runner.PORTFOLIO_DAILY_PATH = old_paths["PORTFOLIO_DAILY_PATH"]
        p5_runner.SUMMARY_PATH = old_paths["SUMMARY_PATH"]
        p5_runner.load_trade_date_map = old_paths["load_trade_date_map"]

    summary = load_json(detail_dir / "p5_summary.json")
    baseline = load_json(P5_BASELINE_PATH)
    if variant["variant_key"] == "t1":
        delta = abs(float(summary["final_nav"]) - float(baseline["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": "p5",
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline['final_nav']):.12f}",
                "actual_value": f"{float(summary['final_nav']):.12f}",
                "difference": f"{delta:.12f}",
                "note": "Baseline T+1 should reproduce the validated P5 run exactly.",
            }
        )
    audit_rows.append(
        {
            "strategy_key": "p5",
            "variant_key": str(variant["variant_key"]),
            "check_type": "shifted_trade_date_collisions",
            "status": "pass",
            "expected_value": "0_or_more",
            "actual_value": str(collision_count),
            "difference": "0.000000000000",
            "note": "Multiple filings can legally collapse onto one delayed execution date; P5 groups by trade date.",
        }
    )
    return detail_dir / "p5_portfolio_daily.csv", detail_dir / "p5_summary.json", detail_dir / "p5_rebalance_events.csv"


def build_nbim_lagged_targets(variant: dict[str, object]) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    price_rows = nbim_runner.read_csv(nbim_runner.PRICE_PATH)
    _, execution_dates = nbim_runner.load_price_lookup(price_rows)
    month_end_dates = nbim_runner.load_month_end_dates(price_rows)
    public_rows = nbim_runner.read_csv(nbim_runner.PUBLIC_DATE_MAP_PATH)
    lagged_map = {
        row["as_of_date"]: nth_trading_day_after(row["public_date"], execution_dates, int(variant["signal_offset"]))
        for row in public_rows
    }
    holdings_by_snapshot, snapshot_industry_by_snapshot, transition_industry_by_snapshot = nbim_runner.build_signal_payloads()
    targets = nbim_runner.build_strategy_targets(
        lagged_map,
        holdings_by_snapshot,
        snapshot_industry_by_snapshot,
        transition_industry_by_snapshot,
    )
    timeline_dates = sorted(set(month_end_dates) | set(lagged_map.values()))
    return targets, timeline_dates


def run_nbim_variant(
    strategy_key: str,
    strategy_name: str,
    variant: dict[str, object],
    audit_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path]:
    targets, timeline_dates = build_nbim_lagged_targets(variant)
    price_rows = nbim_runner.read_csv(nbim_runner.PRICE_PATH)
    price_lookup, _ = nbim_runner.load_price_lookup(price_rows)
    baseline_summary_path = N4_BASELINE_PATH if strategy_key == "n4" else N6_BASELINE_PATH
    baseline = load_json(baseline_summary_path)
    prefix = f"{strategy_key}_{variant['variant_key']}"
    detail_dir = DETAIL_ROOT / strategy_key / str(variant["variant_key"])
    strategy = {
        "key": strategy_key,
        "name": strategy_name,
        "dir": detail_dir,
        "prefix": prefix,
        "description": f"{strategy_name} with {variant['label']} execution lag.",
    }
    nbim_runner.run_strategy(strategy, targets[strategy_key], price_lookup, timeline_dates)
    summary = load_json(detail_dir / f"{prefix}_summary.json")
    if variant["variant_key"] == "t1":
        delta = abs(float(summary["final_nav"]) - float(baseline["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline['final_nav']):.12f}",
                "actual_value": f"{float(summary['final_nav']):.12f}",
                "difference": f"{delta:.12f}",
                "note": "Baseline T+1 should reproduce the validated NBIM run exactly.",
            }
        )
    return detail_dir / f"{prefix}_portfolio_timeline.csv", detail_dir / f"{prefix}_summary.json", detail_dir / f"{prefix}_rebalance_events.csv"


def shifted_state_rows(variant: dict[str, object], audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = combined_runner.read_csv(combined_runner.STATE_PATH)
    _, calendar_dates = combined_runner.load_nbim_price_lookup()
    rows = [row for row in rows if "2019-02-14" <= row["event_date"] <= "2026-05-18"]
    shifted_rows: list[dict[str, str]] = []
    collisions: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        shifted_date = shift_existing_trade_date(row["event_date"], calendar_dates, int(variant["event_extra_offset"]))
        new_row = dict(row)
        new_row["event_date"] = shifted_date
        shifted_rows.append(new_row)
        collisions[shifted_date].append(row["event_date"])
    deduped: list[dict[str, str]] = []
    for date_value in sorted(collisions):
        candidates = [row for row in shifted_rows if row["event_date"] == date_value]
        chosen = sorted(candidates, key=lambda row: (row["pif_trade_date_active"], row["nbim_trade_date_active"]))[-1]
        deduped.append(chosen)
    collision_count = sum(1 for originals in collisions.values() if len(originals) > 1)
    audit_rows.append(
        {
            "strategy_key": "s1",
            "variant_key": str(variant["variant_key"]),
            "check_type": "shifted_event_date_collisions",
            "status": "pass",
            "expected_value": "0_or_more",
            "actual_value": str(collision_count),
            "difference": "0.000000000000",
            "note": "When delayed combined states land on the same close, the latest cumulative state is retained.",
        }
    )
    return deduped


def run_s1_variant(variant: dict[str, object], audit_rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    detail_dir = DETAIL_ROOT / "s1" / str(variant["variant_key"])
    strategy = {
        "key": "s1",
        "name": "S1 Exposure Regime Overlay",
        "dir": detail_dir,
        "prefix": f"s1_{variant['variant_key']}",
        "type": "sector_overlay",
    }
    baseline = load_json(S1_BASELINE_PATH)
    original_loader: Callable[[], list[dict[str, str]]] = combined_runner.load_state_rows
    try:
        combined_runner.load_state_rows = lambda: shifted_state_rows(variant, audit_rows)
        combined_runner.run_strategy(strategy)
    finally:
        combined_runner.load_state_rows = original_loader
    summary = load_json(detail_dir / f"s1_{variant['variant_key']}_summary.json")
    if variant["variant_key"] == "t1":
        delta = abs(float(summary["final_nav"]) - float(baseline["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": "s1",
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline['final_nav']):.12f}",
                "actual_value": f"{float(summary['final_nav']):.12f}",
                "difference": f"{delta:.12f}",
                "note": "Baseline T+1 should reproduce the validated S1 run exactly.",
            }
        )
    return detail_dir / f"s1_{variant['variant_key']}_portfolio_daily.csv", detail_dir / f"s1_{variant['variant_key']}_summary.json", detail_dir / f"s1_{variant['variant_key']}_rebalance_events.csv"


def append_daily_rows(
    daily_rows: list[dict[str, str]],
    portfolio_path: Path,
    strategy_key: str,
    strategy_name: str,
    variant: dict[str, object],
    primary_benchmark_key: str,
    primary_lookup: dict[str, float],
    secondary_benchmark_key: str = "",
    secondary_lookup: dict[str, float] | None = None,
) -> dict[str, float | str]:
    portfolio_rows = read_csv(portfolio_path)
    summary = summarize_against_benchmark(portfolio_rows, primary_benchmark_key, primary_lookup)
    primary_series = build_benchmark_series([row["date"] for row in portfolio_rows], primary_lookup)
    primary_by_date = dict(primary_series)
    primary_start = primary_by_date[primary_series[0][0]]
    secondary_start = None
    if secondary_benchmark_key and secondary_lookup is not None:
        secondary_series = build_benchmark_series([row["date"] for row in portfolio_rows], secondary_lookup)
        secondary_start = dict(secondary_series)[secondary_series[0][0]]
        secondary_by_date = dict(secondary_series)
    else:
        secondary_by_date = {}

    for row in portfolio_rows:
        date = row["date"]
        primary_close = primary_by_date[date]
        primary_nav = primary_close / primary_start
        out_row = {
            "date": date,
            "strategy_key": strategy_key,
            "strategy_name": strategy_name,
            "execution_variant": str(variant["variant_key"]),
            "execution_label": str(variant["label"]),
            "signal_lag_trading_days": str(variant["signal_offset"]),
            "nav_end": row["nav_end"],
            "cum_return": row.get("cum_return", f"{to_float(row['nav_end']) - 1.0:.12f}"),
            "cash_weight_end": row.get("cash_weight_end", f"{(to_float(row.get('cash_end', 0.0)) / to_float(row['nav_end'])) if to_float(row['nav_end']) else 0.0:.12f}"),
            "primary_benchmark_key": primary_benchmark_key,
            "primary_benchmark_nav": f"{primary_nav:.12f}",
            "relative_to_primary": f"{(to_float(row['nav_end']) / primary_nav) if primary_nav else 0.0:.12f}",
        }
        if secondary_by_date and secondary_start is not None and date in secondary_by_date:
            secondary_nav = secondary_by_date[date] / secondary_start
            out_row["secondary_benchmark_key"] = secondary_benchmark_key
            out_row["secondary_benchmark_nav"] = f"{secondary_nav:.12f}"
            out_row["relative_to_secondary"] = f"{(to_float(row['nav_end']) / secondary_nav) if secondary_nav else 0.0:.12f}"
        else:
            out_row["secondary_benchmark_key"] = ""
            out_row["secondary_benchmark_nav"] = ""
            out_row["relative_to_secondary"] = ""
        daily_rows.append(out_row)

    if secondary_benchmark_key and secondary_lookup is not None:
        secondary_series = build_benchmark_series([row["date"] for row in portfolio_rows], secondary_lookup)
        secondary_series_by_date = dict(secondary_series)
        secondary_start_close = secondary_series_by_date[secondary_series[0][0]]
        secondary_end_close = secondary_series_by_date[secondary_series[-1][0]]
        summary["secondary_benchmark_key"] = secondary_benchmark_key
        summary["secondary_benchmark_total_return"] = secondary_end_close / secondary_start_close - 1.0
        summary["secondary_excess_total_return"] = float(summary["total_return"]) - float(summary["secondary_benchmark_total_return"])
    return summary


def write_method_note() -> None:
    text = """# Phase 3 A1: Execution-Lag Sensitivity

This step tests whether the strongest surviving strategies remain credible after small execution delays.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Variants

- `T+1`: first tradable close after the legal source signal
- `T+3`: third tradable close after the legal source signal
- `T+5`: fifth tradable close after the legal source signal

## Source-Specific Handling

### `P5`

- source anchor is `signal_date`
- delayed trade dates are recomputed from the validated `PIF` adjusted daily calendar
- the strategy logic itself is unchanged: sells happen first, buys are funded only from available cash, and residual proceeds remain in cash

### `N4` and `N6`

- source anchor is `NBIM public_date`
- delayed trade dates are recomputed from the validated `NBIM` adjusted daily calendar
- the target sleeves are rebuilt from the original disclosed signals, then traded at the delayed close

### `S1`

- the combined state table already encodes the legal baseline execution close as `event_date`
- `T+3` and `T+5` are therefore implemented as `+2` and `+4` additional shared trading days on the combined calendar
- if multiple delayed states land on the same execution date, the latest cumulative state is retained because all earlier information is also known by that close

## Validation Rules

- baseline `T+1` must reproduce the previously validated strategy NAV exactly within floating-point tolerance
- every delayed execution date must exist in the relevant price calendar
- benchmark comparisons are rebased to each variant's actual live start date
- no new price sources are introduced; only the already-audited stored daily files are used

## Outputs

- `data/processed/robustness/execution_lag_summary.csv`
- `data/processed/robustness/execution_lag_daily.csv`
- `data/processed/robustness/execution_lag_audit.csv`
"""
    METHOD_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    ROBUSTNESS_ROOT.mkdir(parents=True, exist_ok=True)
    DETAIL_ROOT.mkdir(parents=True, exist_ok=True)
    write_method_note()

    spy_lookup = load_spy_lookup()
    vt_lookup = load_vt_lookup()
    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for variant in VARIANTS:
        p5_portfolio_path, p5_summary_path, p5_rebalance_path = run_p5_variant(variant, audit_rows)
        p5_summary = load_json(p5_summary_path)
        p5_metrics = append_daily_rows(
            daily_rows,
            p5_portfolio_path,
            "p5",
            "P5 Cash-Aware Copy",
            variant,
            "SPY",
            spy_lookup,
        )
        summary_rows.append(
            {
                "strategy_key": "p5",
                "strategy_name": "P5 Cash-Aware Copy",
                "execution_variant": str(variant["variant_key"]),
                "execution_label": str(variant["label"]),
                "signal_lag_trading_days": str(variant["signal_offset"]),
                "start_date": str(p5_summary["start_date"]),
                "end_date": str(p5_summary["end_date"]),
                "rebalance_count": str(p5_summary["rebalance_count"]),
                "final_nav": f"{float(p5_summary['final_nav']):.12f}",
                "total_return": f"{float(p5_metrics['total_return']):.12f}",
                "primary_benchmark_key": "SPY",
                "primary_benchmark_total_return": f"{float(p5_metrics['benchmark_total_return']):.12f}",
                "excess_total_return": f"{float(p5_metrics['excess_total_return']):.12f}",
                "max_drawdown": f"{float(p5_metrics['max_drawdown']):.12f}",
                "avg_cash_weight": f"{float(p5_metrics['avg_cash_weight']):.12f}",
                "secondary_benchmark_key": "",
                "secondary_excess_total_return": "",
                "detail_portfolio_path": str(p5_portfolio_path.relative_to(ROOT)),
                "detail_rebalance_path": str(p5_rebalance_path.relative_to(ROOT)),
            }
        )

        for strategy_key, strategy_name in [("n4", "N4 Industry Weight-Change Tilt"), ("n6", "N6 Top-3 Industry Leaders")]:
            portfolio_path, summary_path, rebalance_path = run_nbim_variant(strategy_key, strategy_name, variant, audit_rows)
            strategy_summary = load_json(summary_path)
            metrics = append_daily_rows(
                daily_rows,
                portfolio_path,
                strategy_key,
                strategy_name,
                variant,
                "VT",
                vt_lookup,
            )
            summary_rows.append(
                {
                    "strategy_key": strategy_key,
                    "strategy_name": strategy_name,
                    "execution_variant": str(variant["variant_key"]),
                    "execution_label": str(variant["label"]),
                    "signal_lag_trading_days": str(variant["signal_offset"]),
                    "start_date": str(strategy_summary["start_date"]),
                    "end_date": str(strategy_summary["end_date"]),
                    "rebalance_count": str(strategy_summary["rebalance_count"]),
                    "final_nav": f"{float(strategy_summary['final_nav']):.12f}",
                    "total_return": f"{float(metrics['total_return']):.12f}",
                    "primary_benchmark_key": "VT",
                    "primary_benchmark_total_return": f"{float(metrics['benchmark_total_return']):.12f}",
                    "excess_total_return": f"{float(metrics['excess_total_return']):.12f}",
                    "max_drawdown": f"{float(metrics['max_drawdown']):.12f}",
                    "avg_cash_weight": f"{float(metrics['avg_cash_weight']):.12f}",
                    "secondary_benchmark_key": "",
                    "secondary_excess_total_return": "",
                    "detail_portfolio_path": str(portfolio_path.relative_to(ROOT)),
                    "detail_rebalance_path": str(rebalance_path.relative_to(ROOT)),
                }
            )

        s1_portfolio_path, s1_summary_path, s1_rebalance_path = run_s1_variant(variant, audit_rows)
        s1_summary = load_json(s1_summary_path)
        s1_metrics = append_daily_rows(
            daily_rows,
            s1_portfolio_path,
            "s1",
            "S1 Exposure Regime Overlay",
            variant,
            "VT",
            vt_lookup,
            "SPY",
            spy_lookup,
        )
        summary_rows.append(
            {
                "strategy_key": "s1",
                "strategy_name": "S1 Exposure Regime Overlay",
                "execution_variant": str(variant["variant_key"]),
                "execution_label": str(variant["label"]),
                "signal_lag_trading_days": str(variant["signal_offset"]),
                "start_date": str(s1_summary["start_date"]),
                "end_date": str(s1_summary["end_date"]),
                "rebalance_count": str(s1_summary["rebalance_count"]),
                "final_nav": f"{float(s1_summary['final_nav']):.12f}",
                "total_return": f"{float(s1_metrics['total_return']):.12f}",
                "primary_benchmark_key": "VT",
                "primary_benchmark_total_return": f"{float(s1_metrics['benchmark_total_return']):.12f}",
                "excess_total_return": f"{float(s1_metrics['excess_total_return']):.12f}",
                "max_drawdown": f"{float(s1_metrics['max_drawdown']):.12f}",
                "avg_cash_weight": f"{float(s1_metrics['avg_cash_weight']):.12f}",
                "secondary_benchmark_key": "SPY",
                "secondary_excess_total_return": f"{float(s1_metrics['secondary_excess_total_return']):.12f}",
                "detail_portfolio_path": str(s1_portfolio_path.relative_to(ROOT)),
                "detail_rebalance_path": str(s1_rebalance_path.relative_to(ROOT)),
            }
        )

    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(DAILY_PATH, daily_rows)
    write_csv(AUDIT_PATH, audit_rows)
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {DAILY_PATH}")
    print(f"Wrote {AUDIT_PATH}")


if __name__ == "__main__":
    main()
