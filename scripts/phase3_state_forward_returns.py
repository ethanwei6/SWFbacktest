from __future__ import annotations

import csv
import statistics
from bisect import bisect_left
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_ROOT = ROOT / "data" / "processed" / "signals"
PIF_ROOT = ROOT / "data" / "processed" / "pif"
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
METHOD_ROOT = ROOT / "docs" / "methods"

STATE_MODEL_PATH = SIGNALS_ROOT / "swf_state_model.csv"
SPY_PATH = PIF_ROOT / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"

DETAIL_PATH = SIGNALS_ROOT / "state_forward_returns.csv"
SUMMARY_PATH = SIGNALS_ROOT / "state_forward_return_summary.csv"
AUDIT_PATH = SIGNALS_ROOT / "state_forward_return_audit.csv"
METHOD_PATH = METHOD_ROOT / "phase3-state-forward-returns.md"

WINDOWS = [
    {"months": 1, "label": "1m"},
    {"months": 3, "label": "3m"},
    {"months": 6, "label": "6m"},
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


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def add_months(value: str, months: int) -> str:
    original = parse_date(value)
    month_index = original.month - 1 + months
    year = original.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    day = min(original.day, month_lengths[month - 1])
    return date(year, month, day).isoformat()


def first_on_or_after(target: str, sorted_dates: list[str]) -> str | None:
    index = bisect_left(sorted_dates, target)
    if index >= len(sorted_dates):
        return None
    return sorted_dates[index]


def first_common_on_or_after(target: str, sorted_dates_a: list[str], sorted_dates_b: list[str]) -> str | None:
    set_b = set(sorted_dates_b)
    index = bisect_left(sorted_dates_a, target)
    while index < len(sorted_dates_a):
        candidate = sorted_dates_a[index]
        if candidate in set_b:
            return candidate
        index += 1
    return None


def load_series() -> dict[str, dict[str, float]]:
    series: dict[str, dict[str, float]] = {"SPY": {}, "VT": {}}
    for row in read_csv(SPY_PATH):
        if row["benchmark_key"] == "SPY" and row["adjust_mode"] == "all":
            series["SPY"][row["date"]] = to_float(row["close"])
    for row in read_csv(NBIM_PRICE_PATH):
        if row["adjust_mode"] != "all":
            continue
        instrument_key = row["instrument_key"]
        if instrument_key == "benchmark_vt":
            series["VT"][row["date"]] = to_float(row["close"])
        elif instrument_key.startswith("sector::"):
            series[instrument_key.split("::", 1)[1]] = series.get(instrument_key.split("::", 1)[1], {})
            series[instrument_key.split("::", 1)[1]][row["date"]] = to_float(row["close"])
    return series


def build_unconditional_baselines(series: dict[str, dict[str, float]]) -> dict[tuple[str, str, str], float]:
    baselines: dict[tuple[str, str, str], float] = {}
    sorted_dates = {key: sorted(value) for key, value in series.items()}

    for window in WINDOWS:
        months = window["months"]
        # SPY absolute baseline
        spy_returns = []
        for start in sorted_dates["SPY"]:
            end = first_on_or_after(add_months(start, months), sorted_dates["SPY"])
            if end is None:
                continue
            spy_returns.append(series["SPY"][end] / series["SPY"][start] - 1.0)
        baselines[("SPY", "absolute", str(months))] = statistics.mean(spy_returns)

        # sector excess baseline vs VT
        for proxy in [key for key in series if key not in {"SPY", "VT"}]:
            returns = []
            for start in sorted(set(sorted_dates[proxy]) & set(sorted_dates["VT"])):
                end = first_common_on_or_after(add_months(start, months), sorted_dates[proxy], sorted_dates["VT"])
                if end is None:
                    continue
                proxy_ret = series[proxy][end] / series[proxy][start] - 1.0
                vt_ret = series["VT"][end] / series["VT"][start] - 1.0
                returns.append(proxy_ret - vt_ret)
            baselines[(proxy, "excess_vs_vt", str(months))] = statistics.mean(returns) if returns else 0.0
    return baselines


def build_detail_rows(
    state_rows: list[dict[str, str]],
    series: dict[str, dict[str, float]],
    baselines: dict[tuple[str, str, str], float],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    detail_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    sorted_dates = {key: sorted(value) for key, value in series.items()}
    first_spy_date = sorted_dates["SPY"][0]
    first_vt_date = sorted_dates["VT"][0]

    for row in state_rows:
        for window in WINDOWS:
            months = window["months"]
            state_date = row["state_date"]
            target_date = add_months(state_date, months)

            if state_date < first_spy_date or state_date < first_vt_date:
                audit_rows.append(
                    {
                        "state_date": state_date,
                        "window_months": str(months),
                        "check_name": "market_window_found",
                        "status": "skip",
                        "detail": f"State date precedes benchmark coverage ({first_spy_date} / {first_vt_date}).",
                    }
                )
                continue

            spy_start = first_on_or_after(state_date, sorted_dates["SPY"])
            spy_end = first_on_or_after(target_date, sorted_dates["SPY"]) if spy_start else None
            vt_start = first_on_or_after(state_date, sorted_dates["VT"])
            vt_end = first_on_or_after(target_date, sorted_dates["VT"]) if vt_start else None

            if not spy_start or not spy_end or not vt_start or not vt_end:
                audit_rows.append(
                    {
                        "state_date": state_date,
                        "window_months": str(months),
                        "check_name": "market_window_found",
                        "status": "skip",
                        "detail": f"Incomplete forward window for {state_date}.",
                    }
                )
                continue

            spy_return = series["SPY"][spy_end] / series["SPY"][spy_start] - 1.0
            vt_return = series["VT"][vt_end] / series["VT"][vt_start] - 1.0
            spy_minus_uncond = spy_return - baselines[("SPY", "absolute", str(months))]

            primary_proxy = row["model_sector_tilt_primary_proxy"]
            sector_start = ""
            sector_end = ""
            sector_return = ""
            sector_excess_vs_vt = ""
            sector_minus_uncond = ""
            if primary_proxy and primary_proxy in series:
                sector_start = first_common_on_or_after(state_date, sorted_dates[primary_proxy], sorted_dates["VT"]) or ""
                sector_end = first_common_on_or_after(target_date, sorted_dates[primary_proxy], sorted_dates["VT"]) if sector_start else ""
                if sector_start and sector_end:
                    proxy_ret = series[primary_proxy][sector_end] / series[primary_proxy][sector_start] - 1.0
                    vt_sector_ret = series["VT"][sector_end] / series["VT"][sector_start] - 1.0
                    sector_return = f"{proxy_ret:.12f}"
                    sector_excess = proxy_ret - vt_sector_ret
                    sector_excess_vs_vt = f"{sector_excess:.12f}"
                    sector_minus_uncond = f"{(sector_excess - baselines[(primary_proxy, 'excess_vs_vt', str(months))]):.12f}"

            detail_rows.append(
                {
                    "state_date": state_date,
                    "state_signature": row["state_signature"],
                    "pif_risk_state": row["pif_risk_state"],
                    "nbim_sector_state": row["nbim_sector_state"],
                    "model_exposure_target": row["model_exposure_target"],
                    "model_sector_tilt_primary": row["model_sector_tilt_primary"],
                    "model_sector_tilt_primary_proxy": primary_proxy,
                    "cross_fund_confirmation_count": row["cross_fund_confirmation_count"],
                    "window_months": str(months),
                    "window_label": window["label"],
                    "spy_start_date": spy_start,
                    "spy_end_date": spy_end,
                    "spy_forward_return": f"{spy_return:.12f}",
                    "spy_minus_unconditional_avg": f"{spy_minus_uncond:.12f}",
                    "vt_start_date": vt_start,
                    "vt_end_date": vt_end,
                    "vt_forward_return": f"{vt_return:.12f}",
                    "sector_start_date": sector_start,
                    "sector_end_date": sector_end,
                    "primary_sector_forward_return": sector_return,
                    "primary_sector_excess_vs_vt": sector_excess_vs_vt,
                    "primary_sector_excess_minus_unconditional_avg": sector_minus_uncond,
                }
            )
            audit_rows.append(
                {
                    "state_date": state_date,
                    "window_months": str(months),
                    "check_name": "market_window_found",
                    "status": "pass",
                    "detail": f"SPY {spy_start}->{spy_end}; VT {vt_start}->{vt_end}",
                }
            )

    return detail_rows, audit_rows


def summarize(detail_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    summary_rows: list[dict[str, str]] = []
    grouping_specs = [
        ("pif_risk_state", "pif_risk_state"),
        ("model_sector_tilt_primary", "model_sector_tilt_primary"),
        ("state_signature", "state_signature"),
    ]

    for grouping_level, field in grouping_specs:
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in detail_rows:
            grouped.setdefault((row[field], row["window_months"]), []).append(row)
        for (group_key, window_months), rows in sorted(grouped.items()):
            spy_returns = [to_float(row["spy_forward_return"]) for row in rows]
            spy_deltas = [to_float(row["spy_minus_unconditional_avg"]) for row in rows]
            vt_returns = [to_float(row["vt_forward_return"]) for row in rows]
            sector_excess = [to_float(row["primary_sector_excess_vs_vt"]) for row in rows if row["primary_sector_excess_vs_vt"]]
            sector_deltas = [
                to_float(row["primary_sector_excess_minus_unconditional_avg"])
                for row in rows
                if row["primary_sector_excess_minus_unconditional_avg"]
            ]
            summary_rows.append(
                {
                    "grouping_level": grouping_level,
                    "group_key": group_key,
                    "window_months": window_months,
                    "state_count": str(len(rows)),
                    "avg_spy_forward_return": f"{statistics.mean(spy_returns):.12f}",
                    "avg_spy_minus_unconditional_avg": f"{statistics.mean(spy_deltas):.12f}",
                    "avg_vt_forward_return": f"{statistics.mean(vt_returns):.12f}",
                    "avg_primary_sector_excess_vs_vt": f"{statistics.mean(sector_excess):.12f}" if sector_excess else "",
                    "avg_primary_sector_excess_minus_unconditional_avg": f"{statistics.mean(sector_deltas):.12f}" if sector_deltas else "",
                    "spy_positive_hit_rate": f"{(sum(1 for value in spy_returns if value > 0.0) / len(spy_returns)):.12f}",
                    "spy_above_unconditional_hit_rate": f"{(sum(1 for value in spy_deltas if value > 0.0) / len(spy_deltas)):.12f}",
                    "primary_sector_positive_excess_hit_rate": f"{(sum(1 for value in sector_excess if value > 0.0) / len(sector_excess)):.12f}" if sector_excess else "",
                }
            )
    return summary_rows


def main() -> None:
    state_rows = read_csv(STATE_MODEL_PATH)
    series = load_series()
    baselines = build_unconditional_baselines(series)
    detail_rows, audit_rows = build_detail_rows(state_rows, series, baselines)
    summary_rows = summarize(detail_rows)

    write_csv(DETAIL_PATH, detail_rows)
    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 C3: Forward Return by State\n\n"
        "This layer evaluates the compact state model directly rather than only through the full portfolio backtests.\n\n"
        "## Inputs\n\n"
        "- `data/processed/signals/swf_state_model.csv`\n"
        "- `data/processed/pif/pif_benchmark_daily.csv`\n"
        "- `data/processed/nbim/nbim_twelvedata_daily_prices.csv`\n\n"
        "## Method\n\n"
        "For each state date, the analysis measures forward returns over `1`, `3`, and `6` calendar months.\n\n"
        "### Market-state view\n\n"
        "- `SPY` forward return\n"
        "- `SPY` forward return minus unconditional average `SPY` drift for the same horizon\n"
        "- `VT` forward return\n\n"
        "### Sector-state view\n\n"
        "If a primary sector tilt proxy exists, the analysis also measures:\n\n"
        "- primary sector ETF forward return\n"
        "- primary sector excess return versus `VT`\n"
        "- primary sector excess return minus the unconditional average excess for that same ETF and horizon\n\n"
        "## Outputs\n\n"
        "- `data/processed/signals/state_forward_returns.csv`\n"
        "- `data/processed/signals/state_forward_return_summary.csv`\n"
        "- `data/processed/signals/state_forward_return_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
