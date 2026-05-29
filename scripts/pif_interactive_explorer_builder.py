from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKTEST_ROOT = ROOT / "data" / "processed" / "pif" / "backtests"
ANALYSIS_ROOT = BACKTEST_ROOT / "analysis"
OUT_DIR = ROOT / "outputs" / "pif" / "backtests" / "interactive"
OUT_DATA_PATH = OUT_DIR / "pif_strategy_explorer_data.js"

STRATEGIES = [
    {
        "key": "p1",
        "name": "P1 New Positions Mirror",
        "subtitle": "Buy newly disclosed entries only, then rotate at the next filing.",
        "dir": BACKTEST_ROOT / "p1",
        "prefix": "p1",
        "color": "#C2410C",
    },
    {
        "key": "p2",
        "name": "P2 Full Sleeve Equal Weight",
        "subtitle": "Hold every eligible disclosed common-equity name and stay fully invested.",
        "dir": BACKTEST_ROOT / "p2_equal_weight",
        "prefix": "p2ew",
        "color": "#0B5FFF",
    },
    {
        "key": "p3",
        "name": "P3 Accumulation Tilt",
        "subtitle": "Overweight new and accumulating names inside the disclosed sleeve.",
        "dir": BACKTEST_ROOT / "p3_accumulation_tilt",
        "prefix": "p3at",
        "color": "#15803D",
    },
    {
        "key": "p4",
        "name": "P4 Exit Avoidance",
        "subtitle": "Stay in the sleeve but exclude names flagged as likely reductions.",
        "dir": BACKTEST_ROOT / "p4_exit_avoidance",
        "prefix": "p4ea",
        "color": "#7C3AED",
    },
    {
        "key": "p5",
        "name": "P5 Cash-Aware Copy",
        "subtitle": "Copy disclosed buys and sells while keeping net sale proceeds in cash.",
        "dir": BACKTEST_ROOT / "p5_cash_aware_copy",
        "prefix": "p5cac",
        "color": "#BE185D",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def to_float(value: str | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def compact_signal_type(row: dict[str, str]) -> str:
    for key in ["signal_type", "transition_signal_type", "tilt_bucket", "rationale_label"]:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return "signal"


def previous_trading_date(dates: list[str], target: str) -> str:
    previous = dates[0]
    for current in dates:
        if current >= target:
            return previous
        previous = current
    return dates[-1]


def top_holdings_snapshot(rows: list[dict[str, str]], limit: int = 10) -> list[dict[str, object]]:
    ranked = sorted(rows, key=lambda row: to_float(row["weight_end"]), reverse=True)[:limit]
    out = []
    for row in ranked:
        out.append(
            {
                "symbol": row["symbol"],
                "issuerName": row["issuer_name"],
                "weightEnd": round(to_float(row["weight_end"]), 6),
                "marketValueEnd": round(to_float(row["market_value_end"]), 6),
                "sharesEnd": round(to_float(row["shares_end"]), 6),
                "closePrice": round(to_float(row["close_price"]), 6),
                "daysSinceEntry": int(to_float(row["days_since_entry"])),
                "entryTradeDate": row["entry_trade_date"],
                "entryReportPeriod": row["entry_report_period"],
            }
        )
    return out


def normalize_signal(row: dict[str, str]) -> dict[str, object]:
    out = {
        "signalId": row.get("signal_id", ""),
        "symbol": row.get("selected_symbol", ""),
        "issuerName": row.get("issuer_name", ""),
        "reportPeriod": row.get("report_period", ""),
        "signalDate": row.get("signal_date", ""),
        "tradeDate": row.get("trade_date", ""),
        "include": row.get("include_flag", "") == "1",
        "exclusionReason": row.get("exclusion_reason", ""),
        "signalType": compact_signal_type(row),
        "rationaleText": row.get("rationale_text", ""),
        "tradeDateClose": row.get("trade_date_close", ""),
        "tradeDateMarkClose": row.get("trade_date_mark_close", ""),
    }
    for source_key, target_key in [
        ("staleness_days", "stalenessDays"),
        ("same_day_multi_period_flag", "sameDayMultiPeriodFlag"),
        ("disclosed_market_value_usd", "disclosedMarketValueUsd"),
        ("disclosed_portfolio_weight", "disclosedPortfolioWeight"),
        ("tilt_score", "tiltScore"),
        ("prev_shares", "prevShares"),
        ("curr_shares", "currShares"),
        ("delta_shares", "deltaShares"),
    ]:
        value = row.get(source_key, "")
        if value != "":
            out[target_key] = value
    return out


def normalize_order(row: dict[str, str]) -> dict[str, object]:
    return {
        "side": row.get("side", ""),
        "symbol": row.get("symbol", ""),
        "issuerName": row.get("issuer_name", ""),
        "shares": round(to_float(row.get("shares", "")), 6),
        "desiredShares": round(to_float(row.get("desired_shares", "")), 6),
        "fillRatio": round(to_float(row.get("fill_ratio", "")), 6),
        "executionPrice": round(to_float(row.get("execution_price", "")), 6),
        "executionPriceRaw": round(to_float(row.get("execution_price_raw", "")), 6),
        "executionPriceBasis": row.get("execution_price_basis", ""),
        "executionValue": round(to_float(row.get("execution_value", "")), 6),
        "sourceSignalId": row.get("source_signal_id", ""),
        "sourceSignalDate": row.get("source_signal_date", ""),
        "sourceReportPeriod": row.get("source_report_period", ""),
        "rationaleText": row.get("rationale_text", ""),
    }


def normalize_portfolio_row(row: dict[str, str], benchmark_row: dict[str, str] | None) -> dict[str, object]:
    return {
        "date": row["date"],
        "navEnd": round(to_float(row["nav_end"]), 8),
        "cumReturn": round(to_float(row["cum_return"]), 8),
        "returnDay": round(to_float(row["return_day"]), 8),
        "cashEnd": round(to_float(row["cash_end"]), 8),
        "cashWeightEnd": round(to_float(row.get("cash_weight_end", "0")), 8),
        "grossExposureEnd": round(to_float(row["gross_exposure_end"]), 8),
        "positionCountEnd": int(to_float(row["position_count_end"])),
        "drawdownToDate": round(to_float(row["drawdown_to_date"]), 8),
        "rebalanceExecuted": row["rebalance_executed_flag"] == "1",
        "rebalanceId": row.get("rebalance_id", ""),
        "buysCount": int(to_float(row.get("buys_count", "0"))),
        "sellsCount": int(to_float(row.get("sells_count", "0"))),
        "benchmarkNav": round(to_float(benchmark_row["benchmark_nav"]), 8) if benchmark_row else None,
        "benchmarkReturnDay": round(to_float(benchmark_row["benchmark_return_day"]), 8) if benchmark_row else None,
        "excessReturnDay": round(to_float(benchmark_row["excess_return_day"]), 8) if benchmark_row else None,
        "relativeNavRatio": round(to_float(benchmark_row["relative_nav_ratio"]), 8) if benchmark_row else None,
        "benchmarkPriceStatus": benchmark_row.get("benchmark_price_status", "") if benchmark_row else "",
    }


def build_strategy_payload(
    meta: dict[str, object],
    benchmark_summary_lookup: dict[str, dict[str, str]],
    benchmark_daily_lookup: dict[str, dict[str, dict[str, str]]],
) -> dict[str, object]:
    strategy_dir = Path(meta["dir"])
    prefix = str(meta["prefix"])

    with (strategy_dir / f"{prefix}_summary.json").open("r", encoding="utf-8") as infile:
        summary = json.load(infile)

    portfolio_rows = read_csv(strategy_dir / f"{prefix}_portfolio_daily.csv")
    holdings_rows = read_csv(strategy_dir / f"{prefix}_holdings_daily.csv")
    orders_rows = read_csv(strategy_dir / f"{prefix}_orders.csv")
    rebalances = read_csv(strategy_dir / f"{prefix}_rebalance_events.csv")
    eligibility_rows = read_csv(strategy_dir / f"{prefix}_signal_eligibility.csv")
    benchmark_rows_by_date = benchmark_daily_lookup[str(meta["key"])]

    holdings_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in holdings_rows:
        holdings_by_date[row["date"]].append(row)

    orders_by_rebalance: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in orders_rows:
        orders_by_rebalance[row["rebalance_id"]].append(row)

    signals_by_trade_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligibility_rows:
        signals_by_trade_date[row["trade_date"]].append(row)

    portfolio_dates = [row["date"] for row in portfolio_rows]
    portfolio_by_date = {row["date"]: row for row in portfolio_rows}

    daily_rows = [
        normalize_portfolio_row(row, benchmark_rows_by_date.get(row["date"]))
        for row in portfolio_rows
    ]

    segments = []
    for index, rebalance in enumerate(rebalances):
        trade_date = rebalance["trade_date"]
        next_trade_date = rebalance.get("next_rebalance_trade_date", "")
        end_date = previous_trading_date(portfolio_dates, next_trade_date) if next_trade_date else portfolio_dates[-1]
        signal_rows = sorted(
            [normalize_signal(row) for row in signals_by_trade_date.get(trade_date, [])],
            key=lambda row: (not row["include"], row["signalType"], row["symbol"], row["issuerName"]),
        )
        order_rows = [normalize_order(row) for row in orders_by_rebalance.get(rebalance.get("rebalance_id", ""), [])]
        holdings_after = top_holdings_snapshot(holdings_by_date.get(trade_date, []))
        holdings_end = top_holdings_snapshot(holdings_by_date.get(end_date, []))

        trade_portfolio_row = portfolio_by_date[trade_date]
        end_portfolio_row = portfolio_by_date[end_date]
        benchmark_start = benchmark_rows_by_date.get(trade_date, {})
        benchmark_end = benchmark_rows_by_date.get(end_date, {})

        included_signals = sum(1 for row in signal_rows if row["include"])
        excluded_signals = len(signal_rows) - included_signals
        segment_return = (
            to_float(end_portfolio_row["nav_end"]) / to_float(trade_portfolio_row["nav_end"]) - 1.0
            if to_float(trade_portfolio_row["nav_end"]) else 0.0
        )
        benchmark_return = (
            to_float(benchmark_end.get("benchmark_nav", "0")) / to_float(benchmark_start.get("benchmark_nav", "0")) - 1.0
            if to_float(benchmark_start.get("benchmark_nav", "0")) else 0.0
        )
        segments.append(
            {
                "index": index,
                "rebalanceId": rebalance.get("rebalance_id", ""),
                "tradeDate": trade_date,
                "signalDates": [value for value in rebalance.get("signal_dates", "").split("|") if value],
                "reportPeriods": [value for value in rebalance.get("report_periods", "").split("|") if value],
                "nextTradeDate": next_trade_date,
                "windowEndDate": end_date,
                "includedSignalCount": included_signals,
                "excludedSignalCount": excluded_signals,
                "buysCount": int(to_float(trade_portfolio_row.get("buys_count", "0"))),
                "sellsCount": int(to_float(trade_portfolio_row.get("sells_count", "0"))),
                "signalRows": signal_rows,
                "orderRows": order_rows,
                "holdingsAfterTrade": holdings_after,
                "holdingsAtWindowEnd": holdings_end,
                "tradeNav": round(to_float(trade_portfolio_row["nav_end"]), 8),
                "endNav": round(to_float(end_portfolio_row["nav_end"]), 8),
                "tradeBenchmarkNav": round(to_float(benchmark_start.get("benchmark_nav", "0")), 8),
                "endBenchmarkNav": round(to_float(benchmark_end.get("benchmark_nav", "0")), 8),
                "windowReturn": round(segment_return, 8),
                "windowBenchmarkReturn": round(benchmark_return, 8),
                "windowExcessReturn": round(segment_return - benchmark_return, 8),
                "tradeCashWeight": round(to_float(trade_portfolio_row.get("cash_weight_end", "0")), 8),
                "endCashWeight": round(to_float(end_portfolio_row.get("cash_weight_end", "0")), 8),
                "tradePositionCount": int(to_float(trade_portfolio_row.get("position_count_end", "0"))),
                "endPositionCount": int(to_float(end_portfolio_row.get("position_count_end", "0"))),
                "sameDayBundleFlag": rebalance.get("same_day_bundle_flag", "0") == "1",
                "rebalanceRow": rebalance,
            }
        )

    benchmark_summary = benchmark_summary_lookup[str(meta["key"])]
    summary_payload = {
        "startDate": summary["start_date"],
        "endDate": summary["end_date"],
        "finalNav": round(float(summary["final_nav"]), 8),
        "totalReturn": round(float(summary["total_return"]), 8),
        "maxDrawdown": round(float(summary["max_drawdown"]), 8),
        "rebalanceCount": int(summary["rebalance_count"]),
        "ordersCount": int(summary["orders_count"]),
        "benchmarkTotalReturn": round(float(benchmark_summary["benchmark_total_return"]), 8),
        "benchmarkFinalNav": round(float(benchmark_summary["benchmark_final_nav"]), 8),
        "excessTotalReturn": round(float(benchmark_summary["excess_total_return"]), 8),
        "informationRatio": round(float(benchmark_summary["information_ratio"]), 8),
        "annualizedExcessReturn": round(float(benchmark_summary["annualized_excess_return"]), 8),
    }

    return {
        "meta": {
            "key": meta["key"],
            "name": meta["name"],
            "subtitle": meta["subtitle"],
            "color": meta["color"],
        },
        "summary": summary_payload,
        "daily": daily_rows,
        "segments": segments,
    }


def main() -> None:
    benchmark_summary_rows = read_csv(ANALYSIS_ROOT / "strategy_vs_benchmark_summary.csv")
    benchmark_daily_rows = read_csv(ANALYSIS_ROOT / "strategy_vs_benchmark_daily.csv")
    benchmark_summary_lookup = {row["strategy_key"]: row for row in benchmark_summary_rows}

    benchmark_daily_lookup: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in benchmark_daily_rows:
        benchmark_daily_lookup[row["strategy_key"]][row["date"]] = row

    strategies_payload = {}
    for strategy in STRATEGIES:
        strategies_payload[strategy["key"]] = build_strategy_payload(
            strategy,
            benchmark_summary_lookup,
            benchmark_daily_lookup,
        )

    payload = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "defaultFocusStrategy": "p5",
        "defaultOverlayStrategies": ["p5", "p2"],
        "benchmarkMeta": {
            "key": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "color": "#334155",
        },
        "pifProxyStrategyKey": "p2",
        "strategies": strategies_payload,
    }

    js = "window.PIFStrategyExplorerData = " + json.dumps(payload, separators=(",", ":")) + ";\n"
    write_text(OUT_DATA_PATH, js)
    print(f"Wrote interactive explorer data to {OUT_DATA_PATH}")


if __name__ == "__main__":
    main()
