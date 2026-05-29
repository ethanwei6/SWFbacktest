from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIF_ROOT = ROOT / "data" / "processed" / "pif"
BACKTEST_ROOT = PIF_ROOT / "backtests" / "p1"

SIGNAL_PANEL_PATH = PIF_ROOT / "pif_backtest_signal_panel.csv"
TRADE_CALENDAR_PATH = PIF_ROOT / "pif_trade_calendar.csv"
MAP_PATH = PIF_ROOT / "pif_twelvedata_security_map.csv"
PRICE_PATH = PIF_ROOT / "pif_twelvedata_daily_prices.csv"

ELIGIBILITY_PATH = BACKTEST_ROOT / "p1_signal_eligibility.csv"
REBALANCES_PATH = BACKTEST_ROOT / "p1_rebalance_events.csv"
ORDERS_PATH = BACKTEST_ROOT / "p1_orders.csv"
HOLDINGS_DAILY_PATH = BACKTEST_ROOT / "p1_holdings_daily.csv"
PORTFOLIO_DAILY_PATH = BACKTEST_ROOT / "p1_portfolio_daily.csv"
SUMMARY_PATH = BACKTEST_ROOT / "p1_summary.json"

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


def load_price_lookup(
    price_rows: list[dict[str, str]],
    adjust_mode: str,
) -> dict[tuple[str, str], dict[str, str]]:
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


def build_signal_eligibility(
    signal_rows: list[dict[str, str]],
    trade_date_map: dict[str, str],
    approved_map: dict[str, dict[str, str]],
    execution_price_lookup: dict[tuple[str, str], dict[str, str]],
    mark_price_lookup: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in signal_rows:
        if row["signal_type"] != "entry_observed":
            continue
        if row["common_equity_baseline_flag"] != "1":
            continue

        trade_date = trade_date_map[row["signal_date"]]
        map_row = approved_map.get(row["security_key"])
        inclusion_flag = "1"
        exclusion_reason = ""
        selected_symbol = ""
        selected_exchange = ""
        execution_close = ""

        if map_row is None:
            inclusion_flag = "0"
            exclusion_reason = "unapproved_or_missing_symbol_mapping"
        else:
            selected_symbol = map_row["selected_symbol"]
            selected_exchange = map_row["selected_exchange"]
            raw_price_row = execution_price_lookup.get((row["security_key"], trade_date))
            mark_price_row = mark_price_lookup.get((row["security_key"], trade_date))
            price_row = mark_price_row or raw_price_row
            if price_row is None:
                inclusion_flag = "0"
                exclusion_reason = "missing_trade_date_close"
            else:
                execution_close = raw_price_row["close"] if raw_price_row is not None else price_row["close"]

        out.append(
            {
                "signal_id": row["signal_id"],
                "security_key": row["security_key"],
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "report_period": row["report_period"],
                "signal_date": row["signal_date"],
                "trade_date": trade_date,
                "staleness_days": row["staleness_days"],
                "same_day_multi_period_flag": row["same_day_multi_period_flag"],
                "selected_symbol": selected_symbol,
                "selected_exchange": selected_exchange,
                "include_flag": inclusion_flag,
                "exclusion_reason": exclusion_reason,
                "trade_date_close": execution_close,
                "trade_date_mark_close": price_row["close"] if inclusion_flag == "1" and price_row is not None else "",
                "strategy_id": "P1",
                "rationale_label": "entry_observed",
                "rationale_text": "Buy at the next NYSE close after a newly disclosed PIF entry becomes public.",
            }
        )
    return out


def next_trade_date_lookup(sorted_trade_dates: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for index, trade_date in enumerate(sorted_trade_dates):
        out[trade_date] = sorted_trade_dates[index + 1] if index + 1 < len(sorted_trade_dates) else ""
    return out


def previous_price(
    security_key: str,
    current_date: str,
    date_to_index: dict[str, int],
    price_lookup: dict[tuple[str, str], dict[str, str]],
    calendar_dates: list[str],
) -> tuple[float, str]:
    current_index = date_to_index[current_date]
    for index in range(current_index - 1, -1, -1):
        row = price_lookup.get((security_key, calendar_dates[index]))
        if row is not None:
            return to_float(row["close"]), "exact_previous_close"
    return 0.0, "missing_previous_close"


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

    eligibility_rows = build_signal_eligibility(
        signal_rows,
        trade_date_map,
        approved_map,
        execution_price_lookup,
        mark_price_lookup,
    )
    eligible_rows = [row for row in eligibility_rows if row["include_flag"] == "1"]

    eligible_by_trade_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible_rows:
        eligible_by_trade_date[row["trade_date"]].append(row)

    rebalance_trade_dates = sorted(eligible_by_trade_date)
    next_rebalance_by_trade_date = next_trade_date_lookup(rebalance_trade_dates)
    trade_date_to_signal_dates = {
        trade_date: sorted({row["signal_date"] for row in rows})
        for trade_date, rows in eligible_by_trade_date.items()
    }

    holdings_daily_rows: list[dict[str, str]] = []
    orders_rows: list[dict[str, str]] = []
    rebalance_rows: list[dict[str, str]] = []
    portfolio_daily_rows: list[dict[str, str]] = []

    positions: dict[str, Position] = {}
    nav_end_previous = INITIAL_NAV
    cash_end_previous = INITIAL_NAV
    peak_nav = INITIAL_NAV
    last_seen_close: dict[str, float] = {}
    rebalance_map = {trade_date: idx + 1 for idx, trade_date in enumerate(rebalance_trade_dates)}

    start_date = rebalance_trade_dates[0] if rebalance_trade_dates else ""
    end_date = rebalance_trade_dates[-1] if rebalance_trade_dates else ""
    active_dates = [date for date in calendar_dates if start_date <= date <= end_date] if start_date else []

    for current_date in active_dates:
        nav_start = nav_end_previous
        cash_start = cash_end_previous
        pnl_day = 0.0
        position_records_today: list[tuple[str, Position, float, float, float, str]] = []

        for security_key, position in list(positions.items()):
            price_row = mark_price_lookup.get((security_key, current_date))
            if price_row is not None:
                close_price = to_float(price_row["close"])
                price_status = "exact_adjusted_close"
            else:
                close_price = last_seen_close.get(security_key, 0.0)
                price_status = "carry_forward_adjusted_close"

            prev_close, _ = previous_price(security_key, current_date, date_to_index, mark_price_lookup, calendar_dates)
            market_value = position.shares * close_price
            pnl_security = position.shares * (close_price - prev_close)
            pnl_day += pnl_security
            position_records_today.append(
                (
                    security_key,
                    position,
                    close_price,
                    market_value,
                    pnl_security,
                    price_status,
                )
            )
            if close_price:
                last_seen_close[security_key] = close_price

        nav_pre_rebalance = nav_start + pnl_day
        nav_end = nav_pre_rebalance
        rebalance_id = ""
        rebalance_executed_flag = "0"
        buys_count = 0
        sells_count = 0
        cash_end = cash_start

        if current_date in eligible_by_trade_date:
            rebalance_executed_flag = "1"
            rebalance_id = f"P1-R{rebalance_map[current_date]:03d}"
            current_signals = sorted(
                eligible_by_trade_date[current_date],
                key=lambda row: (row["issuer_name"], row["signal_id"]),
            )

            # Sell current basket at the rebalance close.
            for security_key, position in list(positions.items()):
                close_price = last_seen_close.get(security_key, 0.0)
                raw_price_row = execution_price_lookup.get((security_key, current_date))
                raw_close_price = to_float(raw_price_row["close"]) if raw_price_row is not None else close_price
                execution_value = position.shares * close_price
                orders_rows.append(
                    {
                        "rebalance_id": rebalance_id,
                        "execution_date": current_date,
                        "side": "SELL",
                        "security_key": security_key,
                        "issuer_name": position.issuer_name,
                        "symbol": position.symbol,
                        "shares": f"{position.shares:.12f}",
                        "execution_price": f"{close_price:.8f}",
                        "execution_price_raw": f"{raw_close_price:.8f}",
                        "execution_price_basis": "split_adjusted_close",
                        "execution_value": f"{execution_value:.12f}",
                        "source_signal_id": position.source_signal_id,
                        "source_signal_date": position.entry_signal_date,
                        "source_report_period": position.entry_report_period,
                        "holding_entry_trade_date": position.entry_trade_date,
                        "rationale_text": "Exit previous P1 basket at the next rebalance close.",
                    }
                )
                sells_count += 1

            positions = {}
            cash_end = nav_pre_rebalance

            target_weight = 1.0 / len(current_signals) if current_signals else 0.0

            for signal in current_signals:
                raw_close_price = to_float(signal["trade_date_close"])
                close_price = to_float(signal["trade_date_mark_close"]) or raw_close_price
                target_value = nav_pre_rebalance * target_weight
                shares = target_value / close_price if close_price else 0.0
                symbol = approved_map[signal["security_key"]]["selected_symbol"]
                positions[signal["security_key"]] = Position(
                    security_key=signal["security_key"],
                    issuer_name=signal["issuer_name"],
                    symbol=symbol,
                    shares=shares,
                    entry_trade_date=current_date,
                    entry_signal_date=signal["signal_date"],
                    entry_report_period=signal["report_period"],
                    source_signal_id=signal["signal_id"],
                    source_rebalance_id=rebalance_id,
                )
                orders_rows.append(
                    {
                        "rebalance_id": rebalance_id,
                        "execution_date": current_date,
                        "side": "BUY",
                        "security_key": signal["security_key"],
                        "issuer_name": signal["issuer_name"],
                        "symbol": symbol,
                        "shares": f"{shares:.12f}",
                        "execution_price": f"{close_price:.8f}",
                        "execution_price_raw": f"{raw_close_price:.8f}",
                        "execution_price_basis": "split_adjusted_close",
                        "execution_value": f"{target_value:.12f}",
                        "source_signal_id": signal["signal_id"],
                        "source_signal_date": signal["signal_date"],
                        "source_report_period": signal["report_period"],
                        "holding_entry_trade_date": current_date,
                        "execution_weight": f"{target_weight:.12f}",
                        "rationale_text": "Buy newly disclosed PIF entry at the first tradable NYSE close after publication.",
                    }
                )
                buys_count += 1
                last_seen_close[signal["security_key"]] = close_price

            cash_end = 0.0 if current_signals else nav_pre_rebalance

            next_rebalance_trade_date = next_rebalance_by_trade_date[current_date]
            signal_dates = sorted({row["signal_date"] for row in current_signals})
            report_periods = sorted({row["report_period"] for row in current_signals})
            raw_signal_count = sum(1 for row in eligibility_rows if row["trade_date"] == current_date)
            raw_excluded_count = sum(
                1 for row in eligibility_rows if row["trade_date"] == current_date and row["include_flag"] == "0"
            )
            rebalance_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "trade_date": current_date,
                    "next_rebalance_trade_date": next_rebalance_trade_date,
                    "signal_dates": "|".join(signal_dates),
                    "report_periods": "|".join(report_periods),
                    "included_signal_ids": "|".join(row["signal_id"] for row in current_signals),
                    "raw_entry_signal_count": str(raw_signal_count),
                    "eligible_entry_signal_count": str(len(current_signals)),
                    "excluded_entry_signal_count": str(raw_excluded_count),
                    "positions_sold_count": str(sells_count),
                    "positions_bought_count": str(buys_count),
                    "pre_trade_nav": f"{nav_pre_rebalance:.12f}",
                    "post_trade_nav": f"{nav_pre_rebalance:.12f}",
                    "target_weight_per_new_name": f"{target_weight:.12f}",
                    "same_day_bundle_flag": "1" if len(signal_dates) > 1 else "0",
                }
            )

        holdings_market_value = 0.0
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
                    pnl_security = 0.0
                    for record in position_records_today:
                        if record[0] == security_key:
                            pnl_security = record[4]
                            break

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
        else:
            nav_end = cash_end

        # Update weights and contributions now that nav_end is final.
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
                "gross_exposure_end": f"{(holdings_market_value / nav_end) if nav_end else 0.0:.12f}",
                "position_count_end": str(len(positions)),
                "rebalance_executed_flag": rebalance_executed_flag,
                "rebalance_id": rebalance_id,
                "buys_count": str(buys_count),
                "sells_count": str(sells_count),
                "peak_nav_to_date": "0.000000000000",
                "drawdown_to_date": "0.000000000000",
            }
        )
        peak_nav = max(peak_nav, nav_end)
        portfolio_daily_rows[-1]["peak_nav_to_date"] = f"{peak_nav:.12f}"
        portfolio_daily_rows[-1]["drawdown_to_date"] = f"{((nav_end / peak_nav) - 1.0) if peak_nav else 0.0:.12f}"
        nav_end_previous = nav_end
        cash_end_previous = cash_end

    write_csv(ELIGIBILITY_PATH, eligibility_rows)
    write_csv(REBALANCES_PATH, rebalance_rows)
    write_csv(ORDERS_PATH, orders_rows)
    write_csv(HOLDINGS_DAILY_PATH, holdings_daily_rows)
    write_csv(PORTFOLIO_DAILY_PATH, portfolio_daily_rows)

    summary = {
        "strategy_id": "P1",
        "strategy_name": "PIF New Positions Mirror",
        "initial_nav": INITIAL_NAV,
        "final_nav": nav_end_previous,
        "total_return": (nav_end_previous / INITIAL_NAV) - 1.0 if INITIAL_NAV else 0.0,
        "rebalance_count": len(rebalance_rows),
        "orders_count": len(orders_rows),
        "holdings_daily_rows": len(holdings_daily_rows),
        "portfolio_daily_rows": len(portfolio_daily_rows),
        "eligible_signals": len(eligible_rows),
        "excluded_signals": len([row for row in eligibility_rows if row["include_flag"] == "0"]),
        "start_date": active_dates[0] if active_dates else "",
        "end_date": active_dates[-1] if active_dates else "",
        "max_drawdown": min((to_float(row["drawdown_to_date"]) for row in portfolio_daily_rows), default=0.0),
        "excluded_signal_reasons": {
            reason: sum(1 for row in eligibility_rows if row["exclusion_reason"] == reason)
            for reason in sorted({row["exclusion_reason"] for row in eligibility_rows if row["exclusion_reason"]})
        },
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run_backtest()
