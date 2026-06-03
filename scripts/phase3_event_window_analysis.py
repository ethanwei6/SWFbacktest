from __future__ import annotations

import csv
import statistics
from bisect import bisect_left
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_ROOT = ROOT / "data" / "processed" / "signals"
ATTRIBUTION_ROOT = ROOT / "data" / "processed" / "attribution"
PIF_ROOT = ROOT / "data" / "processed" / "pif"
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"

STATE_PATH = SIGNALS_ROOT / "swf_signal_states.csv"
PANEL_PATH = SIGNALS_ROOT / "swf_combined_signal_panel.csv"
PIF_BENCHMARK_PATH = PIF_ROOT / "pif_benchmark_daily.csv"
NBIM_PRICE_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"

DETAIL_PATH = ATTRIBUTION_ROOT / "event_window_forward_returns.csv"
SUMMARY_PATH = ATTRIBUTION_ROOT / "event_window_summary.csv"
AUDIT_PATH = ATTRIBUTION_ROOT / "event_window_audit.csv"

WINDOWS = [
    {"months": 1, "label": "1m"},
    {"months": 3, "label": "3m"},
    {"months": 6, "label": "6m"},
]

SECTOR_TO_ETF = {
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}

COMMON_SECTORS = {
    "communication_services": "Communication Services",
    "consumer_discretionary": "Consumer Discretionary",
    "consumer_staples": "Consumer Staples",
    "energy": "Energy",
    "financials": "Financials",
    "health_care": "Health Care",
    "industrials": "Industrials",
    "materials": "Materials",
    "real_estate": "Real Estate",
    "technology": "Technology",
    "utilities": "Utilities",
}


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
    index = bisect_left(sorted_dates_a, target)
    dates_b = set(sorted_dates_b)
    while index < len(sorted_dates_a):
        candidate = sorted_dates_a[index]
        if candidate in dates_b:
            return candidate
        index += 1
    return None


def load_price_series() -> dict[str, dict[str, float]]:
    series: dict[str, dict[str, float]] = defaultdict(dict)

    for row in read_csv(PIF_BENCHMARK_PATH):
        if row["benchmark_key"] == "SPY" and row["adjust_mode"] == "all":
            series["SPY"][row["date"]] = to_float(row["close"])

    for row in read_csv(NBIM_PRICE_PATH):
        if row["adjust_mode"] != "all":
            continue
        instrument_key = row["instrument_key"]
        if instrument_key == "benchmark_vt":
            series["VT"][row["date"]] = to_float(row["close"])
        elif instrument_key.startswith("sector::"):
            symbol = instrument_key.split("::", 1)[1]
            series[symbol][row["date"]] = to_float(row["close"])

    return dict(series)


def build_event_rows(states: list[dict[str, str]], panel: list[dict[str, str]]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []

    previous_pif_state = ""
    for row in states:
        current_state = row["pif_exposure_state"]
        if current_state and current_state != previous_pif_state:
            if current_state in {"expanding", "contracting"}:
                events.append(
                    {
                        "event_family": f"pif_{current_state}",
                        "event_label": f"PIF {current_state.title()}",
                        "event_date": row["event_date"],
                        "sector": "",
                        "proxy_symbol": "SPY",
                        "benchmark_symbol": "CASH",
                        "signal_strength": row["pif_exposure_score"],
                        "signal_context": f"state_change:{previous_pif_state or 'none'}->{current_state}",
                        "source": "swf_signal_states",
                    }
                )
            previous_pif_state = current_state

    for row in panel:
        if row["fund"] != "NBIM" or row["signal_family"] != "nbim_industry_weight_change":
            continue
        if row["signal_direction"] != "overweight":
            continue
        sector = row["sector"]
        proxy_symbol = SECTOR_TO_ETF.get(sector)
        if not proxy_symbol:
            continue
        events.append(
            {
                "event_family": "nbim_positive_industry_weight_change",
                "event_label": "NBIM Positive Industry Weight Change",
                "event_date": row["effective_trade_date"],
                "sector": sector,
                "proxy_symbol": proxy_symbol,
                "benchmark_symbol": "VT",
                "signal_strength": row["signal_strength"],
                "signal_context": row["signal_name"],
                "source": "swf_combined_signal_panel",
            }
        )
        if sector == "Technology":
            events.append(
                {
                    "event_family": "nbim_overweight_tech",
                    "event_label": "NBIM Overweight Tech",
                    "event_date": row["effective_trade_date"],
                    "sector": sector,
                    "proxy_symbol": proxy_symbol,
                    "benchmark_symbol": "VT",
                    "signal_strength": row["signal_strength"],
                    "signal_context": row["signal_name"],
                    "source": "swf_combined_signal_panel",
                }
            )

    for sector_slug, sector_name in COMMON_SECTORS.items():
        column = f"cross_fund_consensus__{sector_slug}"
        previous_value = ""
        for row in states:
            current_value = row[column]
            if previous_value in {"", "no"} and current_value == "yes":
                events.append(
                    {
                        "event_family": "cross_fund_consensus_gained",
                        "event_label": "Cross-Fund Consensus Gained",
                        "event_date": row["event_date"],
                        "sector": sector_name,
                        "proxy_symbol": SECTOR_TO_ETF[sector_name],
                        "benchmark_symbol": "VT",
                        "signal_strength": f"{(to_float(row[f'pif_sector_score__{sector_slug}']) + to_float(row[f'nbim_sector_score__{sector_slug}'])):.8f}",
                        "signal_context": "consensus:no->yes",
                        "source": "swf_signal_states",
                    }
                )
            elif previous_value == "yes" and current_value == "no":
                events.append(
                    {
                        "event_family": "cross_fund_consensus_lost",
                        "event_label": "Cross-Fund Consensus Lost",
                        "event_date": row["event_date"],
                        "sector": sector_name,
                        "proxy_symbol": SECTOR_TO_ETF[sector_name],
                        "benchmark_symbol": "VT",
                        "signal_strength": f"{(to_float(row[f'pif_sector_score__{sector_slug}']) + to_float(row[f'nbim_sector_score__{sector_slug}'])):.8f}",
                        "signal_context": "consensus:yes->no",
                        "source": "swf_signal_states",
                    }
                )
            if current_value:
                previous_value = current_value

    return sorted(events, key=lambda row: (row["event_date"], row["event_family"], row["sector"], row["proxy_symbol"]))


def build_detail_rows(events: list[dict[str, str]], series: dict[str, dict[str, float]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    detail_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    sorted_dates_by_symbol = {symbol: sorted(prices) for symbol, prices in series.items()}

    for event in events:
        proxy_symbol = event["proxy_symbol"]
        benchmark_symbol = event["benchmark_symbol"]
        proxy_series = series[proxy_symbol]
        proxy_dates = sorted_dates_by_symbol[proxy_symbol]
        benchmark_series = series.get(benchmark_symbol, {})
        benchmark_dates = sorted_dates_by_symbol.get(benchmark_symbol, [])

        start_date = (
            first_on_or_after(event["event_date"], proxy_dates)
            if benchmark_symbol == "CASH"
            else first_common_on_or_after(event["event_date"], proxy_dates, benchmark_dates)
        )

        if start_date is None:
            for window in WINDOWS:
                audit_rows.append(
                    {
                        "event_family": event["event_family"],
                        "event_date": event["event_date"],
                        "sector": event["sector"],
                        "window_months": str(window["months"]),
                        "check_name": "start_date_found",
                        "status": "fail",
                        "detail": f"No common start date for proxy {proxy_symbol} and benchmark {benchmark_symbol}.",
                    }
                )
            continue

        proxy_start_close = proxy_series[start_date]
        benchmark_start_close = benchmark_series.get(start_date, 1.0) if benchmark_symbol != "CASH" else 1.0

        for window in WINDOWS:
            target_end_date = add_months(start_date, window["months"])
            end_date = (
                first_on_or_after(target_end_date, proxy_dates)
                if benchmark_symbol == "CASH"
                else first_common_on_or_after(target_end_date, proxy_dates, benchmark_dates)
            )

            if end_date is None:
                audit_rows.append(
                    {
                        "event_family": event["event_family"],
                        "event_date": event["event_date"],
                        "sector": event["sector"],
                        "window_months": str(window["months"]),
                        "check_name": "end_date_found",
                        "status": "skip",
                        "detail": f"Insufficient forward history for target end date {target_end_date}.",
                    }
                )
                continue

            proxy_end_close = proxy_series[end_date]
            benchmark_end_close = benchmark_series.get(end_date, 1.0) if benchmark_symbol != "CASH" else 1.0
            proxy_return = proxy_end_close / proxy_start_close - 1.0
            benchmark_return = 0.0 if benchmark_symbol == "CASH" else benchmark_end_close / benchmark_start_close - 1.0
            excess_return = proxy_return - benchmark_return
            actual_horizon_days = (parse_date(end_date) - parse_date(start_date)).days

            detail_rows.append(
                {
                    "event_family": event["event_family"],
                    "event_label": event["event_label"],
                    "event_date": event["event_date"],
                    "analysis_start_date": start_date,
                    "target_end_date": target_end_date,
                    "actual_end_date": end_date,
                    "window_months": str(window["months"]),
                    "window_label": window["label"],
                    "actual_horizon_days": str(actual_horizon_days),
                    "sector": event["sector"],
                    "proxy_symbol": proxy_symbol,
                    "benchmark_symbol": benchmark_symbol,
                    "signal_strength": event["signal_strength"],
                    "signal_context": event["signal_context"],
                    "source": event["source"],
                    "proxy_start_close": f"{proxy_start_close:.8f}",
                    "proxy_end_close": f"{proxy_end_close:.8f}",
                    "proxy_forward_return": f"{proxy_return:.12f}",
                    "benchmark_start_close": f"{benchmark_start_close:.8f}",
                    "benchmark_end_close": f"{benchmark_end_close:.8f}",
                    "benchmark_forward_return": f"{benchmark_return:.12f}",
                    "excess_forward_return": f"{excess_return:.12f}",
                }
            )

            audit_rows.append(
                {
                    "event_family": event["event_family"],
                    "event_date": event["event_date"],
                    "sector": event["sector"],
                    "window_months": str(window["months"]),
                    "check_name": "window_built",
                    "status": "pass",
                    "detail": f"{proxy_symbol} vs {benchmark_symbol} from {start_date} to {end_date}.",
                }
            )

    return detail_rows, audit_rows


def summarize(detail_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in detail_rows:
        grouped[("family_total", row["event_family"], "", row["window_months"])].append(row)
        sector = row["sector"]
        if sector:
            grouped[("sector", row["event_family"], sector, row["window_months"])].append(row)

    summary_rows: list[dict[str, str]] = []
    for (aggregation_level, event_family, sector, window_months), rows in sorted(grouped.items()):
        proxy_returns = [to_float(row["proxy_forward_return"]) for row in rows]
        benchmark_returns = [to_float(row["benchmark_forward_return"]) for row in rows]
        excess_returns = [to_float(row["excess_forward_return"]) for row in rows]
        summary_rows.append(
            {
                "aggregation_level": aggregation_level,
                "event_family": event_family,
                "sector": sector,
                "window_months": window_months,
                "event_count": str(len(rows)),
                "avg_proxy_forward_return": f"{statistics.mean(proxy_returns):.12f}",
                "median_proxy_forward_return": f"{statistics.median(proxy_returns):.12f}",
                "avg_benchmark_forward_return": f"{statistics.mean(benchmark_returns):.12f}",
                "avg_excess_forward_return": f"{statistics.mean(excess_returns):.12f}",
                "median_excess_forward_return": f"{statistics.median(excess_returns):.12f}",
                "excess_hit_rate": f"{(sum(1 for value in excess_returns if value > 0.0) / len(excess_returns)):.12f}",
                "positive_proxy_hit_rate": f"{(sum(1 for value in proxy_returns if value > 0.0) / len(proxy_returns)):.12f}",
                "best_excess_forward_return": f"{max(excess_returns):.12f}",
                "worst_excess_forward_return": f"{min(excess_returns):.12f}",
            }
        )
    return summary_rows


def build_audit(detail_rows: list[dict[str, str]], summary_rows: list[dict[str, str]], audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = list(audit_rows)
    expected_detail_rows = len(build_event_rows(read_csv(STATE_PATH), read_csv(PANEL_PATH))) * len(WINDOWS)
    rows.append(
        {
            "event_family": "all",
            "event_date": "",
            "sector": "",
            "window_months": "all",
            "check_name": "detail_row_count_positive",
            "status": "pass" if len(detail_rows) > 0 else "fail",
            "detail": f"Built {len(detail_rows)} detail rows from {expected_detail_rows} potential windows.",
        }
    )
    rows.append(
        {
            "event_family": "all",
            "event_date": "",
            "sector": "",
            "window_months": "all",
            "check_name": "summary_row_count_positive",
            "status": "pass" if len(summary_rows) > 0 else "fail",
            "detail": f"Built {len(summary_rows)} summary rows.",
        }
    )
    summary_count_lookup = {
        (row["aggregation_level"], row["event_family"], row["sector"], row["window_months"]): int(row["event_count"])
        for row in summary_rows
    }
    detail_group_counts: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for row in detail_rows:
        detail_group_counts[("family_total", row["event_family"], "", row["window_months"])] += 1
        if row["sector"]:
            detail_group_counts[("sector", row["event_family"], row["sector"], row["window_months"])] += 1
    for key, expected_count in detail_group_counts.items():
        actual_count = summary_count_lookup.get(key, -1)
        rows.append(
            {
                "event_family": key[1],
                "event_date": "",
                "sector": key[2],
                "window_months": key[3],
                "check_name": "summary_count_matches_detail",
                "status": "pass" if actual_count == expected_count else "fail",
                "detail": f"summary={actual_count} detail={expected_count} aggregation={key[0]}",
            }
        )
    for row in detail_rows:
        valid_order = row["analysis_start_date"] <= row["actual_end_date"]
        rows.append(
            {
                "event_family": row["event_family"],
                "event_date": row["event_date"],
                "sector": row["sector"],
                "window_months": row["window_months"],
                "check_name": "date_order_valid",
                "status": "pass" if valid_order else "fail",
                "detail": f"{row['analysis_start_date']} -> {row['actual_end_date']}",
            }
        )
    return rows


def main() -> None:
    states = read_csv(STATE_PATH)
    panel = read_csv(PANEL_PATH)
    series = load_price_series()
    events = build_event_rows(states, panel)
    detail_rows, audit_seed = build_detail_rows(events, series)
    summary_rows = summarize(detail_rows)
    audit_rows = build_audit(detail_rows, summary_rows, audit_seed)

    write_csv(DETAIL_PATH, detail_rows)
    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(AUDIT_PATH, audit_rows)

    print(f"Built {len(events)} events into {len(detail_rows)} detail rows.")
    print(f"Wrote {len(summary_rows)} summary rows and {len(audit_rows)} audit rows.")


if __name__ == "__main__":
    main()
