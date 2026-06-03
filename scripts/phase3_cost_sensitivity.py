from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pif_backtest_p5_cash_aware_copy_engine as p5_runner


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
DETAIL_ROOT = ROBUSTNESS_ROOT / "cost_sensitivity_detail"
SUMMARY_PATH = ROBUSTNESS_ROOT / "cost_sensitivity_summary.csv"
DAILY_PATH = ROBUSTNESS_ROOT / "cost_sensitivity_daily.csv"
AUDIT_PATH = ROBUSTNESS_ROOT / "cost_sensitivity_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-cost-sensitivity.md"

PIF_BENCHMARK_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"

P5_SIGNAL_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_signal_eligibility.csv"
P5_BASELINE_PORTFOLIO_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv"
P5_BASELINE_SUMMARY_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_summary.json"

NBIM_STRATEGIES = [
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "holdings_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_holdings_timeline.csv",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_portfolio_timeline.csv",
        "summary_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_summary.json",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "holdings_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_holdings_timeline.csv",
        "portfolio_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_portfolio_timeline.csv",
        "summary_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_summary.json",
        "benchmark_key": "VT",
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "holdings_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_holdings_daily.csv",
        "portfolio_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_portfolio_daily.csv",
        "summary_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_summary.json",
        "benchmark_key": "VT",
        "secondary_benchmark_key": "SPY",
    },
]

COST_VARIANTS = [
    {"variant_key": "c0", "label": "0 bps", "bps": 0.0},
    {"variant_key": "c10", "label": "10 bps", "bps": 10.0},
    {"variant_key": "c25", "label": "25 bps", "bps": 25.0},
    {"variant_key": "c50", "label": "50 bps", "bps": 50.0},
]

INITIAL_NAV = 1.0


@dataclass
class Position:
    key: str
    symbol: str
    name: str
    shares: float
    entry_date: str


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
    import json

    return json.loads(path.read_text(encoding="utf-8"))


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
        "benchmark_total_return": benchmark_total_return,
        "total_return": total_return,
        "excess_total_return": total_return - benchmark_total_return,
        "avg_cash_weight": avg_cash_weight,
        "max_drawdown": max_drawdown,
    }


def load_pif_price_lookups() -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float], list[str]]:
    rows = p5_runner.read_csv(p5_runner.PRICE_PATH)
    exec_lookup = {}
    mark_lookup = {}
    for row in rows:
        key = (row["security_key"], row["date"])
        if row["adjust_mode"] == "none":
            exec_lookup[key] = to_float(row["close"])
        elif row["adjust_mode"] == "all":
            mark_lookup[key] = to_float(row["close"])
    calendar = sorted({row["date"] for row in rows if row["adjust_mode"] == "all"})
    return exec_lookup, mark_lookup, calendar


def previous_price(
    key: str,
    current_date: str,
    calendar: list[str],
    date_to_index: dict[str, int],
    price_lookup: dict[tuple[str, str], float],
) -> float:
    current_index = date_to_index[current_date]
    for index in range(current_index - 1, -1, -1):
        lookup_key = (key, calendar[index])
        if lookup_key in price_lookup:
            return price_lookup[lookup_key]
    return 0.0


def run_p5_cost_variant(variant: dict[str, object], audit_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, object]]:
    cost_rate = float(variant["bps"]) / 10000.0
    exec_lookup, mark_lookup, calendar = load_pif_price_lookups()
    date_to_index = {date: idx for idx, date in enumerate(calendar)}
    eligibility = read_csv(P5_SIGNAL_PATH)
    portfolio_baseline = read_csv(P5_BASELINE_PORTFOLIO_PATH)
    active_dates = [row["date"] for row in portfolio_baseline]

    initial_rows = [row for row in eligibility if row["signal_group"] == "initial_seed" and row["include_flag"] == "1"]
    grouped_transitions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligibility:
        if row["signal_group"] == "transition" and row["include_flag"] == "1":
            grouped_transitions[row["trade_date"]].append(row)

    initial_base_value = sum(to_float(row["curr_shares"]) * to_float(row["trade_date_mark_close"]) for row in initial_rows)
    scale_k = INITIAL_NAV / initial_base_value if initial_base_value else 0.0

    positions: dict[str, Position] = {}
    cash = INITIAL_NAV
    peak_nav = INITIAL_NAV
    prev_nav_end = INITIAL_NAV
    last_seen_close: dict[str, float] = {}
    daily_rows: list[dict[str, str]] = []
    order_rows: list[dict[str, str]] = []
    cumulative_cost = 0.0

    for current_date in active_dates:
        nav_start = prev_nav_end
        cash_start = cash
        pnl_day = 0.0
        for key, position in positions.items():
            close_price = mark_lookup.get((key, current_date), last_seen_close.get(key, 0.0))
            prev_close = previous_price(key, current_date, calendar, date_to_index, mark_lookup)
            pnl_day += position.shares * (close_price - prev_close)
            if close_price:
                last_seen_close[key] = close_price
        nav_pre = nav_start + pnl_day
        cash = cash_start
        trade_cost_day = 0.0

        if current_date == initial_rows[0]["trade_date"]:
            for row in sorted(initial_rows, key=lambda r: (r["issuer_name"], r["signal_id"])):
                mark_close = to_float(row["trade_date_mark_close"])
                desired_shares = to_float(row["curr_shares"]) * scale_k
                requested_value = desired_shares * mark_close
                fill_ratio = min(1.0, cash / (requested_value * (1.0 + cost_rate))) if requested_value > 0 else 1.0
                filled_shares = desired_shares * fill_ratio
                execution_value = filled_shares * mark_close
                trade_cost = execution_value * cost_rate
                cash -= execution_value + trade_cost
                trade_cost_day += trade_cost
                cumulative_cost += trade_cost
                if filled_shares > 0:
                    positions[row["security_key"]] = Position(
                        key=row["security_key"],
                        symbol=row["selected_symbol"],
                        name=row["issuer_name"],
                        shares=filled_shares,
                        entry_date=current_date,
                    )
                    order_rows.append(
                        {
                            "execution_date": current_date,
                            "security_key": row["security_key"],
                            "side": "BUY",
                            "execution_value": f"{execution_value:.12f}",
                            "trade_cost": f"{trade_cost:.12f}",
                            "fill_ratio": f"{fill_ratio:.12f}",
                        }
                    )
                    last_seen_close[row["security_key"]] = mark_close
        elif current_date in grouped_transitions:
            report_period_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in grouped_transitions[current_date]:
                report_period_rows[row["report_period"]].append(row)
            for report_period in sorted(report_period_rows):
                rows = sorted(report_period_rows[report_period], key=lambda r: (r["issuer_name"], r["signal_id"]))
                for row in rows:
                    signal_type = row["signal_type"]
                    key = row["security_key"]
                    if key not in positions:
                        continue
                    current_pos = positions[key]
                    mark_close = to_float(row["trade_date_mark_close"])
                    current_shares = current_pos.shares
                    new_target_shares = current_shares
                    if signal_type == "exit_observed":
                        new_target_shares = 0.0
                    elif signal_type == "likely_reduction":
                        prev_shares = to_float(row["prev_shares"])
                        curr_shares = to_float(row["curr_shares"])
                        ratio = (curr_shares / prev_shares) if prev_shares > 0 else 0.0
                        new_target_shares = current_shares * ratio
                    if new_target_shares >= current_shares:
                        continue
                    shares_to_sell = current_shares - new_target_shares
                    execution_value = shares_to_sell * mark_close
                    trade_cost = execution_value * cost_rate
                    cash += execution_value - trade_cost
                    trade_cost_day += trade_cost
                    cumulative_cost += trade_cost
                    order_rows.append(
                        {
                            "execution_date": current_date,
                            "security_key": key,
                            "side": "SELL",
                            "execution_value": f"{execution_value:.12f}",
                            "trade_cost": f"{trade_cost:.12f}",
                            "fill_ratio": "1.000000000000",
                        }
                    )
                    if new_target_shares <= 0:
                        positions.pop(key, None)
                    else:
                        current_pos.shares = new_target_shares

                buy_requests = []
                for row in rows:
                    signal_type = row["signal_type"]
                    key = row["security_key"]
                    mark_close = to_float(row["trade_date_mark_close"])
                    desired_add_shares = 0.0
                    if signal_type == "entry_observed":
                        desired_add_shares = to_float(row["curr_shares"]) * scale_k
                    elif signal_type == "likely_accumulation" and key in positions:
                        prev_shares = to_float(row["prev_shares"])
                        curr_shares = to_float(row["curr_shares"])
                        if prev_shares > 0 and curr_shares > prev_shares:
                            current_shares = positions[key].shares
                            desired_add_shares = current_shares * ((curr_shares / prev_shares) - 1.0)
                    if desired_add_shares <= 0:
                        continue
                    desired_value = desired_add_shares * mark_close
                    buy_requests.append((row, desired_add_shares, desired_value, mark_close))

                requested_cost_inclusive = sum(desired_value * (1.0 + cost_rate) for _, _, desired_value, _ in buy_requests)
                fill_ratio = min(1.0, cash / requested_cost_inclusive) if requested_cost_inclusive > 0 else 1.0
                for row, desired_add_shares, desired_value, mark_close in buy_requests:
                    filled_shares = desired_add_shares * fill_ratio
                    execution_value = filled_shares * mark_close
                    trade_cost = execution_value * cost_rate
                    if execution_value <= 0:
                        continue
                    cash -= execution_value + trade_cost
                    trade_cost_day += trade_cost
                    cumulative_cost += trade_cost
                    key = row["security_key"]
                    if key in positions:
                        positions[key].shares += filled_shares
                    else:
                        positions[key] = Position(
                            key=key,
                            symbol=row["selected_symbol"],
                            name=row["issuer_name"],
                            shares=filled_shares,
                            entry_date=current_date,
                        )
                    order_rows.append(
                        {
                            "execution_date": current_date,
                            "security_key": key,
                            "side": "BUY",
                            "execution_value": f"{execution_value:.12f}",
                            "trade_cost": f"{trade_cost:.12f}",
                            "fill_ratio": f"{fill_ratio:.12f}",
                        }
                    )
                    last_seen_close[key] = mark_close

        holdings_value = 0.0
        for key, position in positions.items():
            close_price = mark_lookup.get((key, current_date), last_seen_close.get(key, 0.0))
            last_seen_close[key] = close_price
            holdings_value += position.shares * close_price

        nav_end = holdings_value + cash
        peak_nav = max(peak_nav, nav_end)
        drawdown = nav_end / peak_nav - 1.0 if peak_nav else 0.0
        daily_rows.append(
            {
                "date": current_date,
                "strategy_key": "p5",
                "strategy_name": "P5 Cash-Aware Copy",
                "cost_variant": str(variant["variant_key"]),
                "cost_label": str(variant["label"]),
                "cost_bps": f"{float(variant['bps']):.1f}",
                "nav_end": f"{nav_end:.12f}",
                "cum_return": f"{nav_end - 1.0:.12f}",
                "cash_weight_end": f"{(cash / nav_end) if nav_end else 0.0:.12f}",
                "trade_cost_day": f"{trade_cost_day:.12f}",
                "cumulative_trade_cost": f"{cumulative_cost:.12f}",
                "drawdown": f"{drawdown:.12f}",
            }
        )
        prev_nav_end = nav_end

    baseline = load_json(P5_BASELINE_SUMMARY_PATH)
    if variant["variant_key"] == "c0":
        delta = abs(to_float(daily_rows[-1]["nav_end"]) - float(baseline["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": "p5",
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline['final_nav']):.12f}",
                "actual_value": daily_rows[-1]["nav_end"],
                "difference": f"{delta:.12f}",
                "note": "Zero-cost rerun should reproduce the validated baseline exactly.",
            }
        )

    return daily_rows, {"final_nav": to_float(daily_rows[-1]["nav_end"])}


def load_nbim_prices() -> dict[tuple[str, str], float]:
    return {
        (row["instrument_key"], row["date"]): to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }


def load_target_weights_from_holdings(holdings_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv(holdings_path):
        if "portfolio_weight" not in row and "weight_end" in row:
            row = {**row, "portfolio_weight": row["weight_end"]}
        if "display_name" not in row and "issuer_name" in row:
            row = {**row, "display_name": row["issuer_name"]}
        grouped[row["date"]][row["instrument_key"]] = row
    return dict(grouped)


def solve_post_cost_nav(
    nav_pre: float,
    current_values: dict[str, float],
    target_weights: dict[str, float],
    cost_rate: float,
) -> tuple[float, float]:
    value = nav_pre
    for _ in range(200):
        turnover = 0.0
        for instrument_key in set(current_values) | set(target_weights):
            current_value = current_values.get(instrument_key, 0.0)
            target_value = target_weights.get(instrument_key, 0.0) * value
            turnover += abs(target_value - current_value)
        new_value = nav_pre - cost_rate * turnover
        if abs(new_value - value) < 1e-12:
            value = new_value
            break
        value = new_value
    turnover = 0.0
    for instrument_key in set(current_values) | set(target_weights):
        current_value = current_values.get(instrument_key, 0.0)
        target_value = target_weights.get(instrument_key, 0.0) * value
        turnover += abs(target_value - current_value)
    return value, turnover * cost_rate


def run_weight_target_cost_variant(
    config: dict[str, str],
    variant: dict[str, object],
    audit_rows: list[dict[str, str]],
    price_lookup: dict[tuple[str, str], float],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    cost_rate = float(variant["bps"]) / 10000.0
    holdings_targets = load_target_weights_from_holdings(Path(config["holdings_path"]))
    baseline_portfolio = read_csv(Path(config["portfolio_path"]))
    baseline_summary = load_json(Path(config["summary_path"]))
    timeline = [row["date"] for row in baseline_portfolio]
    baseline_portfolio_by_date = {row["date"]: row for row in baseline_portfolio}
    positions: dict[str, Position] = {}
    cash = INITIAL_NAV
    prev_nav_end = INITIAL_NAV
    peak_nav = INITIAL_NAV
    daily_rows: list[dict[str, str]] = []
    cumulative_cost = 0.0

    for current_date in timeline:
        nav_start = prev_nav_end
        current_values = {}
        for key, position in positions.items():
            current_values[key] = position.shares * price_lookup[(key, current_date)]
        nav_pre = cash + sum(current_values.values())
        trade_cost_day = 0.0

        if current_date in holdings_targets:
            target_rows = holdings_targets[current_date]
            target_weights = {key: to_float(row["portfolio_weight"]) for key, row in target_rows.items()}
            target_cash_weight = to_float(baseline_portfolio_by_date[current_date].get("cash_weight_end", 0.0))
            post_cost_nav, trade_cost = solve_post_cost_nav(nav_pre, current_values, target_weights, cost_rate)
            desired_values = {key: weight * post_cost_nav for key, weight in target_weights.items()}
            new_positions: dict[str, Position] = {}
            for key, row in target_rows.items():
                price = price_lookup[(key, current_date)]
                target_shares = desired_values[key] / price if price else 0.0
                if target_shares > 1e-12:
                    existing = positions.get(key)
                    new_positions[key] = Position(
                        key=key,
                        symbol=row["symbol"],
                        name=row["display_name"],
                        shares=target_shares,
                        entry_date=existing.entry_date if existing else current_date,
                    )
            positions = new_positions
            cash = post_cost_nav * target_cash_weight
            trade_cost_day = trade_cost
            cumulative_cost += trade_cost

            check_cash = nav_pre - sum(desired_values.values()) - trade_cost
            audit_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "variant_key": str(variant["variant_key"]),
                    "check_type": f"cash_reconciliation::{current_date}",
                    "status": "pass" if abs(check_cash - cash) < 1e-9 else "fail",
                    "expected_value": f"{cash:.12f}",
                    "actual_value": f"{check_cash:.12f}",
                    "difference": f"{abs(check_cash - cash):.12f}",
                    "note": "Self-financing fixed-point solution should reconcile target holdings, cash, and cost exactly.",
                }
            )

        holdings_value = 0.0
        for key, position in positions.items():
            holdings_value += position.shares * price_lookup[(key, current_date)]
        nav_end = holdings_value + cash
        peak_nav = max(peak_nav, nav_end)
        drawdown = nav_end / peak_nav - 1.0 if peak_nav else 0.0
        daily_rows.append(
            {
                "date": current_date,
                "strategy_key": config["strategy_key"],
                "strategy_name": config["strategy_name"],
                "cost_variant": str(variant["variant_key"]),
                "cost_label": str(variant["label"]),
                "cost_bps": f"{float(variant['bps']):.1f}",
                "nav_end": f"{nav_end:.12f}",
                "cum_return": f"{nav_end - 1.0:.12f}",
                "cash_weight_end": f"{(cash / nav_end) if nav_end else 0.0:.12f}",
                "trade_cost_day": f"{trade_cost_day:.12f}",
                "cumulative_trade_cost": f"{cumulative_cost:.12f}",
                "drawdown": f"{drawdown:.12f}",
            }
        )
        prev_nav_end = nav_end

    if variant["variant_key"] == "c0":
        delta = abs(to_float(daily_rows[-1]["nav_end"]) - float(baseline_summary["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline_summary['final_nav']):.12f}",
                "actual_value": daily_rows[-1]["nav_end"],
                "difference": f"{delta:.12f}",
                "note": "Zero-cost rerun should reproduce the validated baseline exactly.",
            }
        )

    return daily_rows, {"final_nav": to_float(daily_rows[-1]["nav_end"])}


def append_benchmark_rows(
    output_daily: list[dict[str, str]],
    strategy_daily: list[dict[str, str]],
    variant: dict[str, object],
    benchmark_key: str,
    benchmark_lookup: dict[str, float],
    secondary_benchmark_key: str = "",
    secondary_lookup: dict[str, float] | None = None,
) -> dict[str, float | str]:
    summary = summarize_against_benchmark(strategy_daily, benchmark_key, benchmark_lookup)
    primary_series = build_benchmark_series([row["date"] for row in strategy_daily], benchmark_lookup)
    primary_by_date = dict(primary_series)
    primary_start = primary_by_date[primary_series[0][0]]
    secondary_by_date: dict[str, float] = {}
    secondary_start = None
    if secondary_benchmark_key and secondary_lookup is not None:
        secondary_series = build_benchmark_series([row["date"] for row in strategy_daily], secondary_lookup)
        secondary_by_date = dict(secondary_series)
        secondary_start = secondary_by_date[secondary_series[0][0]]

    for row in strategy_daily:
        date = row["date"]
        primary_nav = primary_by_date[date] / primary_start
        out = dict(row)
        out["primary_benchmark_key"] = benchmark_key
        out["primary_benchmark_nav"] = f"{primary_nav:.12f}"
        out["relative_to_primary"] = f"{(to_float(row['nav_end']) / primary_nav) if primary_nav else 0.0:.12f}"
        if secondary_by_date and secondary_start is not None and date in secondary_by_date:
            secondary_nav = secondary_by_date[date] / secondary_start
            out["secondary_benchmark_key"] = secondary_benchmark_key
            out["secondary_benchmark_nav"] = f"{secondary_nav:.12f}"
            out["relative_to_secondary"] = f"{(to_float(row['nav_end']) / secondary_nav) if secondary_nav else 0.0:.12f}"
        else:
            out["secondary_benchmark_key"] = ""
            out["secondary_benchmark_nav"] = ""
            out["relative_to_secondary"] = ""
        output_daily.append(out)

    if secondary_benchmark_key and secondary_lookup is not None:
        secondary_series = build_benchmark_series([row["date"] for row in strategy_daily], secondary_lookup)
        secondary_by_date = dict(secondary_series)
        secondary_start_close = secondary_by_date[secondary_series[0][0]]
        secondary_end_close = secondary_by_date[secondary_series[-1][0]]
        summary["secondary_benchmark_key"] = secondary_benchmark_key
        summary["secondary_benchmark_total_return"] = secondary_end_close / secondary_start_close - 1.0
        summary["secondary_excess_total_return"] = float(summary["total_return"]) - float(summary["secondary_benchmark_total_return"])
    return summary


def write_method_note() -> None:
    text = """# Phase 3 A2: Transaction Cost and Slippage Sensitivity

This step tests whether the surviving strategies remain credible after one-way implementation frictions.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Cost Variants

- `0 bps`
- `10 bps`
- `25 bps`
- `50 bps`

Each cost is applied one-way to every buy and sell notional.

## Implementation

### `P5`

- rerun from the validated baseline signal-eligibility file
- sells add `execution_value * (1 - cost_rate)` to cash
- buys consume `execution_value * (1 + cost_rate)` from cash
- buy fill ratios are recomputed so the strategy remains self-financing

### `N4`, `N6`, and `S1`

- rerun from the validated baseline rebalance target weights already expressed in the stored holdings files
- on each rebalance date, solve the post-cost portfolio value `V` from:

`V = nav_pre - cost_rate * sum_i |target_value_i(V) - current_value_i|`

- target holdings are then sized from `V`, which keeps the rebalance self-financing without negative cash

## Validation Rules

- `0 bps` must reproduce each validated baseline final NAV exactly within floating-point tolerance
- cash reconciliation on every rebalance must hold to floating-point tolerance
- no new price sources are introduced; only the already-audited stored daily files are used

## Outputs

- `data/processed/robustness/cost_sensitivity_summary.csv`
- `data/processed/robustness/cost_sensitivity_daily.csv`
- `data/processed/robustness/cost_sensitivity_audit.csv`
"""
    METHOD_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    ROBUSTNESS_ROOT.mkdir(parents=True, exist_ok=True)
    DETAIL_ROOT.mkdir(parents=True, exist_ok=True)
    write_method_note()

    spy_lookup = load_spy_lookup()
    vt_lookup = load_vt_lookup()
    nbim_prices = load_nbim_prices()

    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for variant in COST_VARIANTS:
        p5_daily, _ = run_p5_cost_variant(variant, audit_rows)
        p5_metrics = append_benchmark_rows(daily_rows, p5_daily, variant, "SPY", spy_lookup)
        summary_rows.append(
            {
                "strategy_key": "p5",
                "strategy_name": "P5 Cash-Aware Copy",
                "cost_variant": str(variant["variant_key"]),
                "cost_label": str(variant["label"]),
                "cost_bps": f"{float(variant['bps']):.1f}",
                "start_date": p5_daily[0]["date"],
                "end_date": p5_daily[-1]["date"],
                "final_nav": p5_daily[-1]["nav_end"],
                "total_return": f"{float(p5_metrics['total_return']):.12f}",
                "primary_benchmark_key": "SPY",
                "primary_benchmark_total_return": f"{float(p5_metrics['benchmark_total_return']):.12f}",
                "excess_total_return": f"{float(p5_metrics['excess_total_return']):.12f}",
                "max_drawdown": f"{float(p5_metrics['max_drawdown']):.12f}",
                "avg_cash_weight": f"{float(p5_metrics['avg_cash_weight']):.12f}",
                "secondary_benchmark_key": "",
                "secondary_excess_total_return": "",
            }
        )

        for config in NBIM_STRATEGIES:
            strategy_daily, _ = run_weight_target_cost_variant(config, variant, audit_rows, nbim_prices)
            metrics = append_benchmark_rows(
                daily_rows,
                strategy_daily,
                variant,
                config["benchmark_key"],
                vt_lookup if config["benchmark_key"] == "VT" else spy_lookup,
                config.get("secondary_benchmark_key", ""),
                spy_lookup if config.get("secondary_benchmark_key") == "SPY" else None,
            )
            summary_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "strategy_name": config["strategy_name"],
                    "cost_variant": str(variant["variant_key"]),
                    "cost_label": str(variant["label"]),
                    "cost_bps": f"{float(variant['bps']):.1f}",
                    "start_date": strategy_daily[0]["date"],
                    "end_date": strategy_daily[-1]["date"],
                    "final_nav": strategy_daily[-1]["nav_end"],
                    "total_return": f"{float(metrics['total_return']):.12f}",
                    "primary_benchmark_key": config["benchmark_key"],
                    "primary_benchmark_total_return": f"{float(metrics['benchmark_total_return']):.12f}",
                    "excess_total_return": f"{float(metrics['excess_total_return']):.12f}",
                    "max_drawdown": f"{float(metrics['max_drawdown']):.12f}",
                    "avg_cash_weight": f"{float(metrics['avg_cash_weight']):.12f}",
                    "secondary_benchmark_key": config.get("secondary_benchmark_key", ""),
                    "secondary_excess_total_return": (
                        f"{float(metrics['secondary_excess_total_return']):.12f}"
                        if "secondary_excess_total_return" in metrics else ""
                    ),
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
