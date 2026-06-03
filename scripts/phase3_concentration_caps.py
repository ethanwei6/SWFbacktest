from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pif_backtest_p5_cash_aware_copy_engine as p5_runner


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
SUMMARY_PATH = ROBUSTNESS_ROOT / "concentration_cap_summary.csv"
DAILY_PATH = ROBUSTNESS_ROOT / "concentration_cap_daily.csv"
AUDIT_PATH = ROBUSTNESS_ROOT / "concentration_cap_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-concentration-caps.md"

PIF_BENCHMARK_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"

P5_HOLDINGS_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_holdings_daily.csv"
P5_BASELINE_PORTFOLIO_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv"
P5_BASELINE_SUMMARY_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_summary.json"

STRATEGY_CONFIGS = [
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

CAP_VARIANTS = [
    {
        "variant_key": "u0",
        "label": "Uncapped",
        "p5_position_cap": 1.0,
        "sector_cap": 1.0,
        "s1_gross_cap": 1.0,
    },
    {
        "variant_key": "m1",
        "label": "Moderate Caps",
        "p5_position_cap": 0.25,
        "sector_cap": 0.35,
        "s1_gross_cap": 0.75,
    },
    {
        "variant_key": "t1",
        "label": "Tight Caps",
        "p5_position_cap": 0.20,
        "sector_cap": 0.30,
        "s1_gross_cap": 0.60,
    },
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
    avg_cash_weight = sum(to_float(row["cash_weight_end"]) for row in portfolio_rows) / len(portfolio_rows)
    max_drawdown = min(to_float(row["drawdown"]) for row in portfolio_rows)
    return {
        "benchmark_total_return": benchmark_total_return,
        "total_return": total_return,
        "excess_total_return": total_return - benchmark_total_return,
        "avg_cash_weight": avg_cash_weight,
        "max_drawdown": max_drawdown,
    }


def load_pif_mark_prices() -> tuple[dict[tuple[str, str], float], list[str], dict[str, int]]:
    rows = p5_runner.read_csv(p5_runner.PRICE_PATH)
    mark_lookup = {(row["security_key"], row["date"]): to_float(row["close"]) for row in rows if row["adjust_mode"] == "all"}
    calendar = sorted({row["date"] for row in rows if row["adjust_mode"] == "all"})
    return mark_lookup, calendar, {date: idx for idx, date in enumerate(calendar)}


def previous_price(
    key: str,
    current_date: str,
    calendar: list[str],
    date_to_index: dict[str, int],
    price_lookup: dict[tuple[str, str], float],
) -> float:
    current_index = date_to_index[current_date]
    for index in range(current_index - 1, -1, -1):
        value = price_lookup.get((key, calendar[index]))
        if value is not None:
            return value
    return 0.0


def load_target_weights_from_holdings(holdings_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv(holdings_path):
        if "portfolio_weight" not in row and "weight_end" in row:
            row = {**row, "portfolio_weight": row["weight_end"]}
        if "display_name" not in row and "issuer_name" in row:
            row = {**row, "display_name": row["issuer_name"]}
        if "instrument_key" not in row and "security_key" in row:
            row = {**row, "instrument_key": row["security_key"]}
        grouped[row["date"]][row["instrument_key"]] = row
    return dict(grouped)


def cap_weights(weights: dict[str, float], cap: float) -> dict[str, float]:
    return {key: min(value, cap) for key, value in weights.items()}


def load_nbim_prices() -> dict[tuple[str, str], float]:
    return {
        (row["instrument_key"], row["date"]): to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }


def run_weight_target_caps(
    config: dict[str, str],
    variant: dict[str, object],
    audit_rows: list[dict[str, str]],
    price_lookup: dict[tuple[str, str], float],
) -> list[dict[str, str]]:
    targets_by_date = load_target_weights_from_holdings(Path(config["holdings_path"]))
    baseline_portfolio = read_csv(Path(config["portfolio_path"]))
    baseline_summary = load_json(Path(config["summary_path"]))
    timeline = [row["date"] for row in baseline_portfolio]
    positions: dict[str, Position] = {}
    cash = INITIAL_NAV
    prev_nav = INITIAL_NAV
    peak_nav = INITIAL_NAV
    daily_rows: list[dict[str, str]] = []

    for current_date in timeline:
        current_values = {key: pos.shares * price_lookup[(key, current_date)] for key, pos in positions.items()}
        nav_pre = cash + sum(current_values.values())
        if current_date in targets_by_date:
            target_rows = targets_by_date[current_date]
            target_weights = {key: to_float(row["portfolio_weight"]) for key, row in target_rows.items()}
            target_cash_weight = max(0.0, 1.0 - sum(target_weights.values()))
            if config["strategy_key"] == "s1":
                gross_cap = float(variant["s1_gross_cap"])
                gross_target = min(sum(target_weights.values()), gross_cap)
                total = sum(target_weights.values())
                if total > 0:
                    target_weights = {key: value * gross_target / total for key, value in target_weights.items()}
                target_cash_weight = 1.0 - gross_target
            target_weights = cap_weights(target_weights, float(variant["sector_cap"]))
            target_cash_weight = 1.0 - sum(target_weights.values())
            new_positions = {}
            for key, row in target_rows.items():
                weight = target_weights.get(key, 0.0)
                if weight <= 1e-12:
                    continue
                price = price_lookup[(key, current_date)]
                shares = nav_pre * weight / price if price else 0.0
                if shares > 1e-12:
                    existing = positions.get(key)
                    new_positions[key] = Position(
                        key=key,
                        symbol=row["symbol"],
                        name=row["display_name"],
                        shares=shares,
                        entry_date=existing.entry_date if existing else current_date,
                    )
            positions = new_positions
            cash = nav_pre * target_cash_weight

        holdings_value = sum(pos.shares * price_lookup[(key, current_date)] for key, pos in positions.items())
        nav_end = cash + holdings_value
        peak_nav = max(peak_nav, nav_end)
        weights = [pos.shares * price_lookup[(key, current_date)] / nav_end for key, pos in positions.items()] if nav_end else []
        max_weight = max(weights) if weights else 0.0
        drawdown = nav_end / peak_nav - 1.0 if peak_nav else 0.0
        daily_rows.append(
            {
                "date": current_date,
                "strategy_key": config["strategy_key"],
                "strategy_name": config["strategy_name"],
                "cap_variant": str(variant["variant_key"]),
                "cap_label": str(variant["label"]),
                "nav_end": f"{nav_end:.12f}",
                "cum_return": f"{nav_end - 1.0:.12f}",
                "cash_weight_end": f"{(cash / nav_end) if nav_end else 0.0:.12f}",
                "gross_exposure_end": f"{(holdings_value / nav_end) if nav_end else 0.0:.12f}",
                "max_position_weight_end": f"{max_weight:.12f}",
                "holding_count_end": str(len(positions)),
                "drawdown": f"{drawdown:.12f}",
            }
        )
        prev_nav = nav_end

    if variant["variant_key"] == "u0":
        delta = abs(to_float(daily_rows[-1]["nav_end"]) - float(baseline_summary["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 5e-11 else "fail",
                "expected_value": f"{float(baseline_summary['final_nav']):.12f}",
                "actual_value": daily_rows[-1]["nav_end"],
                "difference": f"{delta:.12f}",
                "note": "Uncapped rerun should reproduce the validated baseline within floating-point tolerance.",
            }
        )

    rebalance_dates = set(targets_by_date)
    compliance_rows = [row for row in daily_rows if row["date"] in rebalance_dates]
    max_observed = max(to_float(row["max_position_weight_end"]) for row in compliance_rows)
    cap_limit = 1.0 if variant["variant_key"] == "u0" else float(variant["sector_cap"])
    audit_rows.append(
        {
            "strategy_key": config["strategy_key"],
            "variant_key": str(variant["variant_key"]),
            "check_type": "max_position_or_sector_cap_compliance",
            "status": "pass" if max_observed <= cap_limit + 1e-9 else "fail",
            "expected_value": f"{cap_limit:.12f}",
            "actual_value": f"{max_observed:.12f}",
            "difference": f"{max(0.0, max_observed - cap_limit):.12f}",
            "note": "Observed rebalance-close maximum weight should not exceed the configured cap.",
        }
    )
    if config["strategy_key"] == "s1":
        max_gross = max(to_float(row["gross_exposure_end"]) for row in compliance_rows)
        gross_cap = float(variant["s1_gross_cap"])
        audit_rows.append(
            {
                "strategy_key": config["strategy_key"],
                "variant_key": str(variant["variant_key"]),
                "check_type": "gross_exposure_cap_compliance",
                "status": "pass" if max_gross <= gross_cap + 1e-9 else "fail",
                "expected_value": f"{gross_cap:.12f}",
                "actual_value": f"{max_gross:.12f}",
                "difference": f"{max(0.0, max_gross - gross_cap):.12f}",
                "note": "Observed rebalance-close gross exposure should not exceed the configured cap.",
            }
        )
    return daily_rows


def run_p5_caps(variant: dict[str, object], audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    mark_lookup, calendar, date_to_index = load_pif_mark_prices()
    p5_holdings = load_target_weights_from_holdings(P5_HOLDINGS_PATH)
    baseline_portfolio = read_csv(P5_BASELINE_PORTFOLIO_PATH)
    baseline_summary = load_json(P5_BASELINE_SUMMARY_PATH)
    active_dates = [row["date"] for row in baseline_portfolio]
    rebalance_dates = {row["date"] for row in baseline_portfolio if row["rebalance_executed_flag"] == "1"}
    position_cap = float(variant["p5_position_cap"])

    positions: dict[str, Position] = {}
    cash = INITIAL_NAV
    prev_nav = INITIAL_NAV
    peak_nav = INITIAL_NAV
    daily_rows: list[dict[str, str]] = []
    last_seen_close: dict[str, float] = {}

    for current_date in active_dates:
        nav_start = prev_nav
        pnl_day = 0.0
        for key, pos in positions.items():
            close = mark_lookup.get((key, current_date), last_seen_close.get(key, 0.0))
            prev_close = previous_price(key, current_date, calendar, date_to_index, mark_lookup)
            pnl_day += pos.shares * (close - prev_close)
            if close:
                last_seen_close[key] = close
        nav_pre = nav_start + pnl_day

        if current_date in rebalance_dates:
            target_rows = p5_holdings.get(current_date, {})
            target_weights = {key: to_float(row["portfolio_weight"]) for key, row in target_rows.items()}
            target_weights = cap_weights(target_weights, position_cap)
            target_cash_weight = 1.0 - sum(target_weights.values())
            new_positions = {}
            for key, row in target_rows.items():
                weight = target_weights.get(key, 0.0)
                if weight <= 1e-12:
                    continue
                price = mark_lookup[(key, current_date)]
                shares = nav_pre * weight / price if price else 0.0
                if shares > 1e-12:
                    existing = positions.get(key)
                    new_positions[key] = Position(
                        key=key,
                        symbol=row["symbol"],
                        name=row["display_name"],
                        shares=shares,
                        entry_date=existing.entry_date if existing else current_date,
                    )
                    last_seen_close[key] = price
            positions = new_positions
            cash = nav_pre * target_cash_weight

        holdings_value = 0.0
        weights = []
        for key, pos in positions.items():
            price = mark_lookup.get((key, current_date), last_seen_close.get(key, 0.0))
            value = pos.shares * price
            holdings_value += value
        nav_end = cash + holdings_value
        for key, pos in positions.items():
            price = mark_lookup.get((key, current_date), last_seen_close.get(key, 0.0))
            value = pos.shares * price
            if nav_end:
                weights.append(value / nav_end)
        peak_nav = max(peak_nav, nav_end)
        drawdown = nav_end / peak_nav - 1.0 if peak_nav else 0.0
        max_weight = max(weights) if weights else 0.0
        daily_rows.append(
            {
                "date": current_date,
                "strategy_key": "p5",
                "strategy_name": "P5 Cash-Aware Copy",
                "cap_variant": str(variant["variant_key"]),
                "cap_label": str(variant["label"]),
                "nav_end": f"{nav_end:.12f}",
                "cum_return": f"{nav_end - 1.0:.12f}",
                "cash_weight_end": f"{(cash / nav_end) if nav_end else 0.0:.12f}",
                "gross_exposure_end": f"{(holdings_value / nav_end) if nav_end else 0.0:.12f}",
                "max_position_weight_end": f"{max_weight:.12f}",
                "holding_count_end": str(len(positions)),
                "drawdown": f"{drawdown:.12f}",
            }
        )
        prev_nav = nav_end

    if variant["variant_key"] == "u0":
        delta = abs(to_float(daily_rows[-1]["nav_end"]) - float(baseline_summary["final_nav"]))
        audit_rows.append(
            {
                "strategy_key": "p5",
                "variant_key": str(variant["variant_key"]),
                "check_type": "baseline_reproduction_final_nav",
                "status": "pass" if delta < 1e-9 else "fail",
                "expected_value": f"{float(baseline_summary['final_nav']):.12f}",
                "actual_value": daily_rows[-1]["nav_end"],
                "difference": f"{delta:.12f}",
                "note": "Uncapped rerun should reproduce the validated baseline exactly.",
            }
        )
    compliance_rows = [row for row in daily_rows if row["date"] in rebalance_dates]
    max_observed = max(to_float(row["max_position_weight_end"]) for row in compliance_rows)
    audit_rows.append(
        {
            "strategy_key": "p5",
            "variant_key": str(variant["variant_key"]),
            "check_type": "max_position_cap_compliance",
            "status": "pass" if max_observed <= position_cap + 1e-9 else "fail",
            "expected_value": f"{position_cap:.12f}",
            "actual_value": f"{max_observed:.12f}",
            "difference": f"{max(0.0, max_observed - position_cap):.12f}",
            "note": "Observed rebalance-close maximum single-name weight should not exceed the configured cap.",
        }
    )
    return daily_rows


def append_benchmark_rows(
    output_daily: list[dict[str, str]],
    strategy_daily: list[dict[str, str]],
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
        summary["secondary_benchmark_total_return"] = secondary_end_close / secondary_start_close - 1.0
        summary["secondary_excess_total_return"] = float(summary["total_return"]) - float(summary["secondary_benchmark_total_return"])
    return summary


def write_method_note() -> None:
    text = """# Phase 3 A3: Concentration and Exposure Caps

This step tests whether the surviving strategies still look credible after more realistic portfolio constraints.

## Focus Set

- `P5` Cash-Aware Copy
- `N4` Industry Weight-Change Tilt
- `N6` Top-3 Industry Leaders
- `S1` Exposure Regime Overlay

## Cap Variants

- `Uncapped`
- `Moderate Caps`
  - `P5` max position weight: `25%`
  - `N4`, `N6`, `S1` max sector / ETF weight: `35%`
  - `S1` max gross exposure: `75%`
- `Tight Caps`
  - `P5` max position weight: `20%`
  - `N4`, `N6`, `S1` max sector / ETF weight: `30%`
  - `S1` max gross exposure: `60%`

## Implementation

### `P5`

- rerun from the validated baseline signal file
- process sells and buys exactly as in the validated cash-aware logic
- after each rebalance, trim any position above the configured cap and leave the excess in cash
- no redistribution of excess weight is attempted

### `N4`, `N6`, and `S1`

- rerun from the validated stored target weights already present in the holdings files
- apply the cap directly to each stored target weight
- for `S1`, first limit gross exposure, then apply the per-sector cap
- any weight removed by the cap remains in cash

## Validation Rules

- the `Uncapped` variant must reproduce the validated baseline final NAV within floating-point tolerance
- observed end-of-day position weights must not exceed the configured caps
- observed `S1` gross exposure must not exceed its configured cap

## Outputs

- `data/processed/robustness/concentration_cap_summary.csv`
- `data/processed/robustness/concentration_cap_daily.csv`
- `data/processed/robustness/concentration_cap_audit.csv`
"""
    METHOD_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    ROBUSTNESS_ROOT.mkdir(parents=True, exist_ok=True)
    write_method_note()
    spy_lookup = load_spy_lookup()
    vt_lookup = load_vt_lookup()
    nbim_prices = load_nbim_prices()
    summary_rows: list[dict[str, str]] = []
    daily_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for variant in CAP_VARIANTS:
        p5_daily = run_p5_caps(variant, audit_rows)
        p5_metrics = append_benchmark_rows(daily_rows, p5_daily, "SPY", spy_lookup)
        summary_rows.append(
            {
                "strategy_key": "p5",
                "strategy_name": "P5 Cash-Aware Copy",
                "cap_variant": str(variant["variant_key"]),
                "cap_label": str(variant["label"]),
                "start_date": p5_daily[0]["date"],
                "end_date": p5_daily[-1]["date"],
                "final_nav": p5_daily[-1]["nav_end"],
                "total_return": f"{float(p5_metrics['total_return']):.12f}",
                "primary_benchmark_key": "SPY",
                "primary_benchmark_total_return": f"{float(p5_metrics['benchmark_total_return']):.12f}",
                "excess_total_return": f"{float(p5_metrics['excess_total_return']):.12f}",
                "max_drawdown": f"{float(p5_metrics['max_drawdown']):.12f}",
                "avg_cash_weight": f"{float(p5_metrics['avg_cash_weight']):.12f}",
                "cap_limit_primary": f"{float(variant['p5_position_cap']):.12f}",
                "cap_limit_secondary": "",
                "secondary_excess_total_return": "",
            }
        )

        for config in STRATEGY_CONFIGS:
            strategy_daily = run_weight_target_caps(config, variant, audit_rows, nbim_prices)
            metrics = append_benchmark_rows(
                daily_rows,
                strategy_daily,
                config["benchmark_key"],
                vt_lookup if config["benchmark_key"] == "VT" else spy_lookup,
                config.get("secondary_benchmark_key", ""),
                spy_lookup if config.get("secondary_benchmark_key") == "SPY" else None,
            )
            summary_rows.append(
                {
                    "strategy_key": config["strategy_key"],
                    "strategy_name": config["strategy_name"],
                    "cap_variant": str(variant["variant_key"]),
                    "cap_label": str(variant["label"]),
                    "start_date": strategy_daily[0]["date"],
                    "end_date": strategy_daily[-1]["date"],
                    "final_nav": strategy_daily[-1]["nav_end"],
                    "total_return": f"{float(metrics['total_return']):.12f}",
                    "primary_benchmark_key": config["benchmark_key"],
                    "primary_benchmark_total_return": f"{float(metrics['benchmark_total_return']):.12f}",
                    "excess_total_return": f"{float(metrics['excess_total_return']):.12f}",
                    "max_drawdown": f"{float(metrics['max_drawdown']):.12f}",
                    "avg_cash_weight": f"{float(metrics['avg_cash_weight']):.12f}",
                    "cap_limit_primary": f"{float(variant['sector_cap']):.12f}",
                    "cap_limit_secondary": f"{float(variant['s1_gross_cap']):.12f}" if config["strategy_key"] == "s1" else "",
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
