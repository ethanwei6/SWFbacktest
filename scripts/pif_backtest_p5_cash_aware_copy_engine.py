from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIF_ROOT = ROOT / "data" / "processed" / "pif"
BACKTEST_ROOT = PIF_ROOT / "backtests" / "p5_cash_aware_copy"

SIGNAL_PANEL_PATH = PIF_ROOT / "pif_backtest_signal_panel.csv"
TRADE_CALENDAR_PATH = PIF_ROOT / "pif_trade_calendar.csv"
MAP_PATH = PIF_ROOT / "pif_twelvedata_security_map.csv"
PRICE_PATH = PIF_ROOT / "pif_twelvedata_daily_prices.csv"

ELIGIBILITY_PATH = BACKTEST_ROOT / "p5cac_signal_eligibility.csv"
REBALANCES_PATH = BACKTEST_ROOT / "p5cac_rebalance_events.csv"
ORDERS_PATH = BACKTEST_ROOT / "p5cac_orders.csv"
HOLDINGS_DAILY_PATH = BACKTEST_ROOT / "p5cac_holdings_daily.csv"
PORTFOLIO_DAILY_PATH = BACKTEST_ROOT / "p5cac_portfolio_daily.csv"
SUMMARY_PATH = BACKTEST_ROOT / "p5cac_summary.json"

INITIAL_NAV = 1.0


@dataclass
class Position:
    security_key: str
    issuer_name: str
    symbol: str
    shares: float
    entry_trade_date: str
    entry_signal_date: str
    entry_report_period: str
    source_signal_id: str
    source_rebalance_id: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        if not rows:
            return
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def load_price_lookup(price_rows: list[dict[str, str]], adjust_mode: str) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in price_rows:
        if row["adjust_mode"] != adjust_mode:
            continue
        lookup[(row["security_key"], row["date"])] = row
    return lookup


def load_price_calendar(price_rows: list[dict[str, str]], adjust_mode: str) -> list[str]:
    return sorted({row["date"] for row in price_rows if row["adjust_mode"] == adjust_mode})


def load_trade_date_map(calendar_rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["signal_date"]: row["trade_date"] for row in calendar_rows}


def load_symbol_map(map_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        row["security_key"]: row
        for row in map_rows
        if row["mapping_status"] in {"approved", "auto_approved"}
    }


def previous_price(
    security_key: str,
    current_date: str,
    date_to_index: dict[str, int],
    mark_price_lookup: dict[tuple[str, str], dict[str, str]],
    calendar_dates: list[str],
) -> float:
    current_index = date_to_index[current_date]
    for index in range(current_index - 1, -1, -1):
        row = mark_price_lookup.get((security_key, calendar_dates[index]))
        if row is not None:
            return to_float(row["close"])
    return 0.0


def build_eligibility_rows(
    signal_rows: list[dict[str, str]],
    trade_date_map: dict[str, str],
    approved_map: dict[str, dict[str, str]],
    execution_price_lookup: dict[tuple[str, str], dict[str, str]],
    mark_price_lookup: dict[tuple[str, str], dict[str, str]],
) -> tuple[list[dict[str, str]], str, str]:
    rows: list[dict[str, str]] = []

    holdings_rows = [
        row for row in signal_rows
        if row["signal_source"] == "holdings"
        and row["signal_type"] == "full_sleeve_holding"
        and row["common_equity_baseline_flag"] == "1"
    ]
    initial_trade_date = min(trade_date_map[row["signal_date"]] for row in holdings_rows)
    initial_report_period = min(
        row["report_period"] for row in holdings_rows if trade_date_map[row["signal_date"]] == initial_trade_date
    )

    for row in holdings_rows:
        trade_date = trade_date_map[row["signal_date"]]
        if trade_date != initial_trade_date or row["report_period"] != initial_report_period:
            continue
        map_row = approved_map.get(row["security_key"])
        raw_price_row = execution_price_lookup.get((row["security_key"], trade_date))
        mark_price_row = mark_price_lookup.get((row["security_key"], trade_date)) or raw_price_row
        include_flag = "1"
        exclusion_reason = ""
        selected_symbol = ""
        selected_exchange = ""
        raw_close = ""
        mark_close = ""

        if map_row is None:
            include_flag = "0"
            exclusion_reason = "unapproved_or_missing_symbol_mapping"
        elif mark_price_row is None:
            include_flag = "0"
            exclusion_reason = "missing_trade_date_close"
            selected_symbol = map_row["selected_symbol"]
            selected_exchange = map_row["selected_exchange"]
        else:
            selected_symbol = map_row["selected_symbol"]
            selected_exchange = map_row["selected_exchange"]
            raw_close = raw_price_row["close"] if raw_price_row is not None else mark_price_row["close"]
            mark_close = mark_price_row["close"]

        rows.append(
            {
                "signal_group": "initial_seed",
                "signal_id": row["signal_id"],
                "security_key": row["security_key"],
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "report_period": row["report_period"],
                "signal_date": row["signal_date"],
                "trade_date": trade_date,
                "signal_type": "initial_seed",
                "selected_symbol": selected_symbol,
                "selected_exchange": selected_exchange,
                "prev_shares": "",
                "curr_shares": row["curr_shares"],
                "delta_shares": "",
                "include_flag": include_flag,
                "exclusion_reason": exclusion_reason,
                "trade_date_close": raw_close,
                "trade_date_mark_close": mark_close,
                "rationale_text": "Seed the strategy from the first publicly visible PIF common-equity sleeve.",
            }
        )

    transition_rows = [
        row for row in signal_rows
        if row["signal_source"] == "transition"
        and row["common_equity_baseline_flag"] == "1"
        and row["signal_type"] in {"entry_observed", "exit_observed", "likely_accumulation", "likely_reduction"}
    ]

    for row in transition_rows:
        trade_date = trade_date_map[row["signal_date"]]
        map_row = approved_map.get(row["security_key"])
        raw_price_row = execution_price_lookup.get((row["security_key"], trade_date))
        mark_price_row = mark_price_lookup.get((row["security_key"], trade_date)) or raw_price_row
        include_flag = "1"
        exclusion_reason = ""
        selected_symbol = ""
        selected_exchange = ""
        raw_close = ""
        mark_close = ""

        if map_row is None:
            include_flag = "0"
            exclusion_reason = "unapproved_or_missing_symbol_mapping"
        elif mark_price_row is None:
            include_flag = "0"
            exclusion_reason = "missing_trade_date_close"
            selected_symbol = map_row["selected_symbol"]
            selected_exchange = map_row["selected_exchange"]
        else:
            selected_symbol = map_row["selected_symbol"]
            selected_exchange = map_row["selected_exchange"]
            raw_close = raw_price_row["close"] if raw_price_row is not None else mark_price_row["close"]
            mark_close = mark_price_row["close"]

        rows.append(
            {
                "signal_group": "transition",
                "signal_id": row["signal_id"],
                "security_key": row["security_key"],
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "report_period": row["report_period"],
                "signal_date": row["signal_date"],
                "trade_date": trade_date,
                "signal_type": row["signal_type"],
                "selected_symbol": selected_symbol,
                "selected_exchange": selected_exchange,
                "prev_shares": row["prev_shares"],
                "curr_shares": row["curr_shares"],
                "delta_shares": row["delta_shares"],
                "include_flag": include_flag,
                "exclusion_reason": exclusion_reason,
                "trade_date_close": raw_close,
                "trade_date_mark_close": mark_close,
                "rationale_text": "Copy only the disclosed trade direction and keep residual cash rather than forcing full reinvestment.",
            }
        )

    return rows, initial_trade_date, initial_report_period


def run_backtest() -> None:
    signal_rows = read_csv(SIGNAL_PANEL_PATH)
    calendar_rows = read_csv(TRADE_CALENDAR_PATH)
    map_rows = read_csv(MAP_PATH)
    price_rows = read_csv(PRICE_PATH)

    trade_date_map = load_trade_date_map(calendar_rows)
    approved_map = load_symbol_map(map_rows)
    execution_price_lookup = load_price_lookup(price_rows, "none")
    mark_price_lookup = load_price_lookup(price_rows, "all")
    if not mark_price_lookup:
        mark_price_lookup = execution_price_lookup
        calendar_dates = load_price_calendar(price_rows, "none")
    else:
        calendar_dates = load_price_calendar(price_rows, "all")
    date_to_index = {date: idx for idx, date in enumerate(calendar_dates)}

    eligibility_rows, initial_trade_date, initial_report_period = build_eligibility_rows(
        signal_rows,
        trade_date_map,
        approved_map,
        execution_price_lookup,
        mark_price_lookup,
    )
    write_csv(ELIGIBILITY_PATH, eligibility_rows)

    initial_rows = [
        row for row in eligibility_rows
        if row["signal_group"] == "initial_seed" and row["include_flag"] == "1"
    ]
    initial_base_value = sum(
        to_float(row["curr_shares"]) * to_float(row["trade_date_mark_close"])
        for row in initial_rows
    )
    scale_k = INITIAL_NAV / initial_base_value if initial_base_value else 0.0

    grouped_transitions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligibility_rows:
        if row["signal_group"] == "transition" and row["include_flag"] == "1":
            grouped_transitions[row["trade_date"]].append(row)

    trade_dates = sorted({initial_trade_date} | set(grouped_transitions))
    all_public_trade_dates = sorted(
        {
            trade_date_map[row["signal_date"]]
            for row in signal_rows
            if row["common_equity_baseline_flag"] == "1"
        }
    )
    next_trade_date_map = {
        trade_dates[i]: trade_dates[i + 1] if i + 1 < len(trade_dates) else ""
        for i in range(len(trade_dates))
    }

    positions: dict[str, Position] = {}
    orders_rows: list[dict[str, str]] = []
    rebalance_rows: list[dict[str, str]] = []
    holdings_daily_rows: list[dict[str, str]] = []
    portfolio_daily_rows: list[dict[str, str]] = []

    nav_end_previous = INITIAL_NAV
    cash_end_previous = INITIAL_NAV
    peak_nav = INITIAL_NAV
    last_seen_close: dict[str, float] = {}
    rebalance_index = 0

    end_date = max(all_public_trade_dates) if all_public_trade_dates else ""
    active_dates = [d for d in calendar_dates if initial_trade_date <= d <= end_date] if trade_dates else []

    for current_date in active_dates:
        nav_start = nav_end_previous
        cash_start = cash_end_previous
        pnl_day = 0.0
        holdings_market_value = 0.0
        rebalance_id = ""
        buys_count = 0
        sells_count = 0
        cash_end = cash_start
        rebalance_executed_flag = "0"
        pre_trade_positions = {k: v.shares for k, v in positions.items()}

        for security_key, position in list(positions.items()):
            price_row = mark_price_lookup.get((security_key, current_date))
            if price_row is not None:
                close_price = to_float(price_row["close"])
            else:
                close_price = last_seen_close.get(security_key, 0.0)
            prev_close = previous_price(security_key, current_date, date_to_index, mark_price_lookup, calendar_dates)
            pnl_day += position.shares * (close_price - prev_close)
            if close_price:
                last_seen_close[security_key] = close_price

        nav_pre_rebalance = nav_start + pnl_day

        if current_date == initial_trade_date:
            rebalance_executed_flag = "1"
            rebalance_index += 1
            rebalance_id = f"P5CAC-R{rebalance_index:03d}"
            cash_end = nav_pre_rebalance
            buy_value = 0.0
            for row in sorted(initial_rows, key=lambda r: (r["issuer_name"], r["signal_id"])):
                mark_close = to_float(row["trade_date_mark_close"])
                raw_close = to_float(row["trade_date_close"]) or mark_close
                desired_shares = to_float(row["curr_shares"]) * scale_k
                execution_value = desired_shares * mark_close
                positions[row["security_key"]] = Position(
                    security_key=row["security_key"],
                    issuer_name=row["issuer_name"],
                    symbol=row["selected_symbol"],
                    shares=desired_shares,
                    entry_trade_date=current_date,
                    entry_signal_date=row["signal_date"],
                    entry_report_period=row["report_period"],
                    source_signal_id=row["signal_id"],
                    source_rebalance_id=rebalance_id,
                )
                orders_rows.append(
                    {
                        "rebalance_id": rebalance_id,
                        "execution_date": current_date,
                        "side": "BUY",
                        "security_key": row["security_key"],
                        "issuer_name": row["issuer_name"],
                        "symbol": row["selected_symbol"],
                        "shares": f"{desired_shares:.12f}",
                        "desired_shares": f"{desired_shares:.12f}",
                        "fill_ratio": "1.000000000000",
                        "execution_price": f"{mark_close:.8f}",
                        "execution_price_raw": f"{raw_close:.8f}",
                        "execution_price_basis": "split_adjusted_close",
                        "execution_value": f"{execution_value:.12f}",
                        "source_signal_id": row["signal_id"],
                        "source_signal_date": row["signal_date"],
                        "source_report_period": row["report_period"],
                        "holding_entry_trade_date": current_date,
                        "rationale_text": "Seed initial sleeve from first disclosed common-equity filing.",
                    }
                )
                buys_count += 1
                buy_value += execution_value
                cash_end -= execution_value
                last_seen_close[row["security_key"]] = mark_close

            rebalance_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "trade_date": current_date,
                    "next_rebalance_trade_date": next_trade_date_map[current_date],
                    "report_periods": initial_report_period,
                    "signal_dates": "|".join(sorted({row["signal_date"] for row in initial_rows})),
                    "raw_signal_count": str(len(initial_rows)),
                    "positions_bought_count": str(buys_count),
                    "positions_sold_count": "0",
                    "cash_before_rebalance": f"{nav_pre_rebalance:.12f}",
                    "cash_after_rebalance": f"{cash_end:.12f}",
                    "buy_fill_ratio": "1.000000000000",
                    "buy_value_requested": f"{buy_value:.12f}",
                    "buy_value_filled": f"{buy_value:.12f}",
                    "sell_value_filled": "0.000000000000",
                    "position_count_end": str(len(positions)),
                }
            )

        elif current_date in grouped_transitions:
            rebalance_executed_flag = "1"
            rebalance_index += 1
            rebalance_id = f"P5CAC-R{rebalance_index:03d}"
            report_period_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in grouped_transitions[current_date]:
                report_period_rows[row["report_period"]].append(row)

            cash_end = cash_start
            total_requested_buy = 0.0
            total_filled_buy = 0.0
            total_filled_sell = 0.0
            buy_fill_ratios: list[float] = []

            for report_period in sorted(report_period_rows):
                rows = report_period_rows[report_period]
                # Sells first.
                for row in sorted(rows, key=lambda r: (r["issuer_name"], r["signal_id"])):
                    signal_type = row["signal_type"]
                    security_key = row["security_key"]
                    if security_key not in positions:
                        continue
                    current_position = positions[security_key]
                    mark_close = to_float(row["trade_date_mark_close"])
                    raw_close = to_float(row["trade_date_close"]) or mark_close
                    current_shares = current_position.shares
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
                    cash_end += execution_value
                    total_filled_sell += execution_value
                    sells_count += 1
                    orders_rows.append(
                        {
                            "rebalance_id": rebalance_id,
                            "execution_date": current_date,
                            "side": "SELL",
                            "security_key": security_key,
                            "issuer_name": row["issuer_name"],
                            "symbol": current_position.symbol,
                            "shares": f"{shares_to_sell:.12f}",
                            "desired_shares": f"{shares_to_sell:.12f}",
                            "fill_ratio": "1.000000000000",
                            "execution_price": f"{mark_close:.8f}",
                            "execution_price_raw": f"{raw_close:.8f}",
                            "execution_price_basis": "split_adjusted_close",
                            "execution_value": f"{execution_value:.12f}",
                            "source_signal_id": row["signal_id"],
                            "source_signal_date": row["signal_date"],
                            "source_report_period": row["report_period"],
                            "holding_entry_trade_date": current_position.entry_trade_date,
                            "rationale_text": "Copy disclosed sale or reduction and keep the proceeds in cash.",
                        }
                    )
                    if new_target_shares <= 0:
                        positions.pop(security_key, None)
                    else:
                        current_position.shares = new_target_shares

                # Then buys funded only from available cash.
                buy_requests = []
                for row in sorted(rows, key=lambda r: (r["issuer_name"], r["signal_id"])):
                    signal_type = row["signal_type"]
                    security_key = row["security_key"]
                    mark_close = to_float(row["trade_date_mark_close"])
                    raw_close = to_float(row["trade_date_close"]) or mark_close
                    desired_add_shares = 0.0
                    if signal_type == "entry_observed":
                        desired_add_shares = to_float(row["curr_shares"]) * scale_k
                    elif signal_type == "likely_accumulation" and security_key in positions:
                        prev_shares = to_float(row["prev_shares"])
                        curr_shares = to_float(row["curr_shares"])
                        if prev_shares > 0 and curr_shares > prev_shares:
                            current_shares = positions[security_key].shares
                            ratio = curr_shares / prev_shares
                            desired_add_shares = current_shares * (ratio - 1.0)
                    if desired_add_shares <= 0:
                        continue
                    desired_value = desired_add_shares * mark_close
                    buy_requests.append(
                        {
                            "row": row,
                            "desired_add_shares": desired_add_shares,
                            "desired_value": desired_value,
                            "mark_close": mark_close,
                            "raw_close": raw_close,
                        }
                    )

                requested_buy_value = sum(item["desired_value"] for item in buy_requests)
                total_requested_buy += requested_buy_value
                fill_ratio = min(1.0, cash_end / requested_buy_value) if requested_buy_value > 0 else 1.0
                buy_fill_ratios.append(fill_ratio)

                for item in buy_requests:
                    row = item["row"]
                    filled_shares = item["desired_add_shares"] * fill_ratio
                    execution_value = filled_shares * item["mark_close"]
                    if execution_value <= 0:
                        continue
                    security_key = row["security_key"]
                    total_filled_buy += execution_value
                    buys_count += 1
                    cash_end -= execution_value

                    if security_key in positions:
                        positions[security_key].shares += filled_shares
                    else:
                        positions[security_key] = Position(
                            security_key=security_key,
                            issuer_name=row["issuer_name"],
                            symbol=row["selected_symbol"],
                            shares=filled_shares,
                            entry_trade_date=current_date,
                            entry_signal_date=row["signal_date"],
                            entry_report_period=row["report_period"],
                            source_signal_id=row["signal_id"],
                            source_rebalance_id=rebalance_id,
                        )
                    orders_rows.append(
                        {
                            "rebalance_id": rebalance_id,
                            "execution_date": current_date,
                            "side": "BUY",
                            "security_key": security_key,
                            "issuer_name": row["issuer_name"],
                            "symbol": row["selected_symbol"],
                            "shares": f"{filled_shares:.12f}",
                            "desired_shares": f"{item['desired_add_shares']:.12f}",
                            "fill_ratio": f"{fill_ratio:.12f}",
                            "execution_price": f"{item['mark_close']:.8f}",
                            "execution_price_raw": f"{item['raw_close']:.8f}",
                            "execution_price_basis": "split_adjusted_close",
                            "execution_value": f"{execution_value:.12f}",
                            "source_signal_id": row["signal_id"],
                            "source_signal_date": row["signal_date"],
                            "source_report_period": row["report_period"],
                            "holding_entry_trade_date": positions[security_key].entry_trade_date,
                            "rationale_text": "Copy disclosed buy or accumulation only to the extent funded by available cash.",
                        }
                    )
                    last_seen_close[security_key] = item["mark_close"]

            rebalance_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "trade_date": current_date,
                    "next_rebalance_trade_date": next_trade_date_map[current_date],
                    "report_periods": "|".join(sorted(report_period_rows)),
                    "signal_dates": "|".join(sorted({row["signal_date"] for row in grouped_transitions[current_date]})),
                    "raw_signal_count": str(len(grouped_transitions[current_date])),
                    "positions_bought_count": str(buys_count),
                    "positions_sold_count": str(sells_count),
                    "cash_before_rebalance": f"{cash_start:.12f}",
                    "cash_after_rebalance": f"{cash_end:.12f}",
                    "buy_fill_ratio": f"{(sum(buy_fill_ratios) / len(buy_fill_ratios)) if buy_fill_ratios else 1.0:.12f}",
                    "buy_value_requested": f"{total_requested_buy:.12f}",
                    "buy_value_filled": f"{total_filled_buy:.12f}",
                    "sell_value_filled": f"{total_filled_sell:.12f}",
                    "position_count_end": str(len(positions)),
                }
            )

        if positions:
            for security_key, position in positions.items():
                close_row = mark_price_lookup.get((security_key, current_date))
                if close_row is not None:
                    close_price = to_float(close_row["close"])
                    price_status = "exact_adjusted_close"
                else:
                    close_price = last_seen_close.get(security_key, 0.0)
                    price_status = "carry_forward_adjusted_close"
                last_seen_close[security_key] = close_price
                market_value = position.shares * close_price
                holdings_market_value += market_value
                if position.entry_trade_date == current_date:
                    pnl_security = 0.0
                else:
                    prior_shares = min(pre_trade_positions.get(security_key, position.shares), position.shares)
                    prev_close = previous_price(security_key, current_date, date_to_index, mark_price_lookup, calendar_dates)
                    pnl_security = prior_shares * (close_price - prev_close)
                holdings_daily_rows.append(
                    {
                        "date": current_date,
                        "security_key": security_key,
                        "issuer_name": position.issuer_name,
                        "symbol": position.symbol,
                        "rebalance_id": position.source_rebalance_id,
                        "entry_trade_date": position.entry_trade_date,
                        "entry_signal_date": position.entry_signal_date,
                        "entry_report_period": position.entry_report_period,
                        "source_signal_id": position.source_signal_id,
                        "days_since_entry": str(date_to_index[current_date] - date_to_index[position.entry_trade_date]),
                        "shares_end": f"{position.shares:.12f}",
                        "close_price": f"{close_price:.8f}",
                        "market_value_end": f"{market_value:.12f}",
                        "weight_end": "0.000000000000",
                        "pnl_day": f"{pnl_security:.12f}",
                        "return_contribution_day": "0.000000000000",
                        "price_status": price_status,
                        "price_basis": "split_adjusted_close",
                    }
                )

        nav_end = holdings_market_value + cash_end
        if nav_end != 0:
            start_index = len(holdings_daily_rows)
            while start_index > 0 and holdings_daily_rows[start_index - 1]["date"] == current_date:
                start_index -= 1
            for index in range(start_index, len(holdings_daily_rows)):
                row = holdings_daily_rows[index]
                market_value = to_float(row["market_value_end"])
                pnl_security = to_float(row["pnl_day"])
                row["weight_end"] = f"{(market_value / nav_end):.12f}"
                row["return_contribution_day"] = f"{(pnl_security / nav_start) if nav_start else 0.0:.12f}"

        portfolio_daily_rows.append(
            {
                "date": current_date,
                "nav_start": f"{nav_start:.12f}",
                "cash_start": f"{cash_start:.12f}",
                "pnl_day": f"{pnl_day:.12f}",
                "nav_pre_rebalance": f"{nav_pre_rebalance:.12f}",
                "nav_end": f"{nav_end:.12f}",
                "return_day": f"{((nav_end / nav_start) - 1.0) if nav_start else 0.0:.12f}",
                "cum_return": f"{(nav_end / INITIAL_NAV) - 1.0:.12f}",
                "cash_end": f"{cash_end:.12f}",
                "cash_weight_end": f"{(cash_end / nav_end) if nav_end else 0.0:.12f}",
                "gross_exposure_end": f"{(holdings_market_value / nav_end) if nav_end else 0.0:.12f}",
                "position_count_end": str(len(positions)),
                "rebalance_executed_flag": rebalance_executed_flag,
                "rebalance_id": rebalance_id,
                "buys_count": str(buys_count),
                "sells_count": str(sells_count),
                "peak_nav_to_date": f"{max(peak_nav, nav_end):.12f}",
                "drawdown_to_date": f"{((nav_end / max(peak_nav, nav_end)) - 1.0) if max(peak_nav, nav_end) else 0.0:.12f}",
            }
        )

        peak_nav = max(peak_nav, nav_end)
        nav_end_previous = nav_end
        cash_end_previous = cash_end

    write_csv(REBALANCES_PATH, rebalance_rows)
    write_csv(ORDERS_PATH, orders_rows)
    write_csv(HOLDINGS_DAILY_PATH, holdings_daily_rows)
    write_csv(PORTFOLIO_DAILY_PATH, portfolio_daily_rows)

    excluded_counts = Counter(
        row["exclusion_reason"] for row in eligibility_rows if row["include_flag"] == "0"
    )
    summary = {
        "strategy_id": "P5_CASH_AWARE_COPY",
        "strategy_name": "PIF Cash-Aware Copy Trade",
        "initial_nav": INITIAL_NAV,
        "final_nav": nav_end_previous,
        "total_return": nav_end_previous - INITIAL_NAV,
        "rebalance_count": len(rebalance_rows),
        "orders_count": len(orders_rows),
        "holdings_daily_rows": len(holdings_daily_rows),
        "portfolio_daily_rows": len(portfolio_daily_rows),
        "eligible_signals": sum(1 for row in eligibility_rows if row["include_flag"] == "1"),
        "excluded_signals": sum(1 for row in eligibility_rows if row["include_flag"] == "0"),
        "start_date": initial_trade_date,
        "end_date": portfolio_daily_rows[-1]["date"] if portfolio_daily_rows else "",
        "max_drawdown": min(to_float(row["drawdown_to_date"]) for row in portfolio_daily_rows) if portfolio_daily_rows else 0.0,
        "avg_cash_weight_end": (
            sum(to_float(row["cash_weight_end"]) for row in portfolio_daily_rows) / len(portfolio_daily_rows)
            if portfolio_daily_rows else 0.0
        ),
        "excluded_signal_reasons": dict(sorted(excluded_counts.items())),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run_backtest()
