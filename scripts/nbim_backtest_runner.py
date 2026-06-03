from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
BACKTEST_ROOT = NBIM_ROOT / "backtests"

HOLDINGS_PATH = NBIM_ROOT / "nbim_public_equity_holdings.csv"
INDUSTRY_SNAPSHOT_PATH = NBIM_ROOT / "nbim_snapshot_industry_summary.csv"
INDUSTRY_TRANSITION_PATH = NBIM_ROOT / "nbim_transition_industry_summary.csv"
PUBLIC_DATE_MAP_PATH = NBIM_ROOT / "nbim_public_date_map.csv"
MIRROR_UNIVERSE_PATH = NBIM_ROOT / "nbim_core_us_mirror_universe.csv"
INDUSTRY_MAP_PATH = NBIM_ROOT / "nbim_industry_etf_map.csv"
PRICE_PATH = NBIM_ROOT / "nbim_alphavantage_monthly_prices.csv"

INITIAL_NAV = 1.0

STRATEGIES = [
    {
        "key": "n1",
        "name": "N1 Core US Mirror Equal Weight",
        "dir": BACKTEST_ROOT / "n1_core_equal_weight",
        "prefix": "n1cew",
        "type": "mirror_equal_weight",
        "description": "Equal-weight the disclosed core US NBIM mirror sleeve at each public snapshot.",
    },
    {
        "key": "n2",
        "name": "N2 Core US Mirror NBIM Weight",
        "dir": BACKTEST_ROOT / "n2_core_nbim_weight",
        "prefix": "n2cnw",
        "type": "mirror_nbim_weight",
        "description": "Preserve disclosed NBIM relative weights within the selected core US mirror sleeve.",
    },
    {
        "key": "n3",
        "name": "N3 Industry Weight Mirror",
        "dir": BACKTEST_ROOT / "n3_industry_weight_mirror",
        "prefix": "n3iwm",
        "type": "industry_weight_mirror",
        "description": "Mirror NBIM industry weights through mapped sector ETFs.",
    },
    {
        "key": "n4",
        "name": "N4 Industry Weight-Change Tilt",
        "dir": BACKTEST_ROOT / "n4_industry_weight_change_tilt",
        "prefix": "n4iwc",
        "type": "industry_weight_change_tilt",
        "description": "Own only industries with positive disclosed weight change versus the prior snapshot.",
    },
    {
        "key": "n5",
        "name": "N5 Industry Accumulation Tilt",
        "dir": BACKTEST_ROOT / "n5_industry_accumulation_tilt",
        "prefix": "n5iat",
        "type": "industry_accumulation_tilt",
        "description": "Own only industries with positive accumulation-minus-reduction transition scores.",
    },
    {
        "key": "n6",
        "name": "N6 Top-3 Industry Leaders",
        "dir": BACKTEST_ROOT / "n6_top3_industry_leaders",
        "prefix": "n6t3l",
        "type": "top3_industry_leaders",
        "description": "Own the three largest disclosed NBIM industry exposures, equally weighted.",
    },
    {
        "key": "n7",
        "name": "N7 Top-3 Industry Increases",
        "dir": BACKTEST_ROOT / "n7_top3_industry_increases",
        "prefix": "n7t3i",
        "type": "top3_industry_increases",
        "description": "Own the three industries with the largest positive disclosed weight changes versus the prior snapshot.",
    },
    {
        "key": "n8",
        "name": "N8 Consensus Rotation Tilt",
        "dir": BACKTEST_ROOT / "n8_consensus_rotation_tilt",
        "prefix": "n8crt",
        "type": "consensus_rotation_tilt",
        "description": "Own sectors confirmed by both positive weight change and positive accumulation-minus-reduction scores.",
    },
]


@dataclass
class Position:
    instrument_key: str
    symbol: str
    display_name: str
    shares: float
    entry_date: str
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


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def load_trade_date_map(public_rows: list[dict[str, str]], calendar_dates: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in public_rows:
        public_date = row["public_date"]
        trade_date = next((date for date in calendar_dates if date > public_date), "")
        if not trade_date:
            raise RuntimeError(f"No monthly trade date found after public date {public_date}")
        mapping[row["as_of_date"]] = trade_date
    return mapping


def load_price_lookup(price_rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], list[str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    benchmark_dates: set[str] = set()
    for row in price_rows:
        lookup[(row["instrument_key"], row["date"])] = row
        if row["instrument_key"] == "benchmark_vt":
            benchmark_dates.add(row["date"])
    return lookup, sorted(benchmark_dates)


def load_mirror_symbol_map() -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for row in read_csv(MIRROR_UNIVERSE_PATH):
        mapping[row["issuer_name"]] = row
    return mapping


def load_industry_map() -> dict[str, dict[str, str]]:
    return {row["nbim_industry"]: row for row in read_csv(INDUSTRY_MAP_PATH)}


def build_signal_payloads() -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    mirror_map = load_mirror_symbol_map()
    public_rows = read_csv(PUBLIC_DATE_MAP_PATH)
    public_date_by_snapshot = {row["as_of_date"]: row["public_date"] for row in public_rows}

    holdings_by_snapshot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(HOLDINGS_PATH):
        snapshot = row["as_of_date"]
        if snapshot not in public_date_by_snapshot:
            continue
        if row["issuer_name"] not in mirror_map:
            continue
        mapped = mirror_map[row["issuer_name"]]
        holdings_by_snapshot[snapshot].append(
            {
                "signal_id": f"{snapshot}::{mapped['symbol']}",
                "as_of_date": snapshot,
                "public_date": public_date_by_snapshot[snapshot],
                "issuer_name": row["issuer_name"],
                "symbol": mapped["symbol"],
                "instrument_key": f"mirror::{mapped['symbol']}",
                "market_value_usd": row["market_value_usd"],
                "ownership_pct": row["ownership_pct"],
            }
        )

    snapshot_industry_by_snapshot: dict[str, list[dict[str, str]]] = defaultdict(list)
    industry_map = load_industry_map()
    for row in read_csv(INDUSTRY_SNAPSHOT_PATH):
        snapshot = row["as_of_date"]
        if snapshot not in public_date_by_snapshot:
            continue
        mapped = industry_map.get(row["industry"])
        if mapped is None:
            continue
        snapshot_industry_by_snapshot[snapshot].append(
            {
                "signal_id": f"{snapshot}::{row['industry']}",
                "as_of_date": snapshot,
                "public_date": public_date_by_snapshot[snapshot],
                "industry": row["industry"],
                "etf_symbol": mapped["etf_symbol"],
                "instrument_key": f"sector::{mapped['etf_symbol']}",
                "portfolio_weight_usd": row["portfolio_weight_usd"],
            }
        )

    transition_industry_by_snapshot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(INDUSTRY_TRANSITION_PATH):
        snapshot = row["curr_as_of_date"]
        if snapshot not in public_date_by_snapshot:
            continue
        mapped = industry_map.get(row["industry"])
        if mapped is None:
            continue
        transition_industry_by_snapshot[snapshot].append(
            {
                "signal_id": f"{row['period']}::{row['industry']}",
                "period": row["period"],
                "prev_as_of_date": row["prev_as_of_date"],
                "curr_as_of_date": row["curr_as_of_date"],
                "public_date": public_date_by_snapshot[snapshot],
                "industry": row["industry"],
                "etf_symbol": mapped["etf_symbol"],
                "instrument_key": f"sector::{mapped['etf_symbol']}",
                "transition_count": row["transition_count"],
                "likely_accumulation": row["likely_accumulation"],
                "likely_reduction": row["likely_reduction"],
            }
        )

    return holdings_by_snapshot, snapshot_industry_by_snapshot, transition_industry_by_snapshot


def aggregate_weights(rows: list[dict[str, str]], value_field: str, key_field: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row[key_field]] += to_float(row[value_field])
    total = sum(totals.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in totals.items()}


def build_strategy_targets(
    trade_date_by_snapshot: dict[str, str],
    holdings_by_snapshot: dict[str, list[dict[str, str]]],
    snapshot_industry_by_snapshot: dict[str, list[dict[str, str]]],
    transition_industry_by_snapshot: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, object]]]:
    targets: dict[str, list[dict[str, object]]] = {strategy["key"]: [] for strategy in STRATEGIES}

    for snapshot in sorted(trade_date_by_snapshot):
        trade_date = trade_date_by_snapshot[snapshot]

        mirror_rows = holdings_by_snapshot.get(snapshot, [])
        if mirror_rows:
            selected = sorted(mirror_rows, key=lambda row: to_float(row["market_value_usd"]), reverse=True)
            equal_weight = 1.0 / len(selected)
            value_weights = aggregate_weights(selected, "market_value_usd", "instrument_key")
            targets["n1"].append(
                {
                    "signal_date": selected[0]["public_date"],
                    "trade_date": trade_date,
                    "as_of_date": snapshot,
                    "rows": [
                        {
                            "signal_id": row["signal_id"],
                            "instrument_key": row["instrument_key"],
                            "symbol": row["symbol"],
                            "display_name": row["issuer_name"],
                            "target_weight": equal_weight,
                            "signal_value": row["market_value_usd"],
                            "include_flag": "1",
                            "rationale_text": "Equal-weight the selected core US NBIM holdings visible at this snapshot.",
                        }
                        for row in selected
                    ],
                }
            )
            targets["n2"].append(
                {
                    "signal_date": selected[0]["public_date"],
                    "trade_date": trade_date,
                    "as_of_date": snapshot,
                    "rows": [
                        {
                            "signal_id": row["signal_id"],
                            "instrument_key": row["instrument_key"],
                            "symbol": row["symbol"],
                            "display_name": row["issuer_name"],
                            "target_weight": value_weights[row["instrument_key"]],
                            "signal_value": row["market_value_usd"],
                            "include_flag": "1",
                            "rationale_text": "Preserve NBIM relative market-value weights within the selected core US mirror sleeve.",
                        }
                        for row in selected
                    ],
                }
            )

        industry_rows = snapshot_industry_by_snapshot.get(snapshot, [])
        if industry_rows:
            etf_weights = aggregate_weights(industry_rows, "portfolio_weight_usd", "instrument_key")
            targets["n3"].append(
                {
                    "signal_date": industry_rows[0]["public_date"],
                    "trade_date": trade_date,
                    "as_of_date": snapshot,
                    "rows": [
                        {
                            "signal_id": row["signal_id"],
                            "instrument_key": row["instrument_key"],
                            "symbol": row["etf_symbol"],
                            "display_name": row["industry"],
                            "target_weight": etf_weights[row["instrument_key"]],
                            "signal_value": row["portfolio_weight_usd"],
                            "include_flag": "1",
                            "rationale_text": "Mirror NBIM disclosed industry weights through mapped sector ETFs.",
                        }
                        for row in industry_rows
                    ],
                }
            )

            etf_agg = defaultdict(float)
            etf_name = {}
            for row in industry_rows:
                etf_agg[row["instrument_key"]] += to_float(row["portfolio_weight_usd"])
                etf_name[row["instrument_key"]] = row["etf_symbol"]
            top3 = sorted(etf_agg.items(), key=lambda item: item[1], reverse=True)[:3]
            n6_rows = []
            for instrument_key, value in top3:
                n6_rows.append(
                    {
                        "signal_id": f"{snapshot}::{instrument_key}::top3_leader",
                        "instrument_key": instrument_key,
                        "symbol": etf_name[instrument_key],
                        "display_name": instrument_key.split("::", 1)[1],
                        "target_weight": 1.0 / len(top3) if top3 else 0.0,
                        "signal_value": str(value),
                        "include_flag": "1",
                        "rationale_text": "Own the three largest disclosed NBIM industries rather than the full industry basket.",
                    }
                )
            targets["n6"].append(
                {
                    "signal_date": industry_rows[0]["public_date"],
                    "trade_date": trade_date,
                    "as_of_date": snapshot,
                    "rows": n6_rows,
                }
            )

            if len(targets["n3"]) > 1:
                prev_rows = snapshot_industry_by_snapshot.get(targets["n3"][-2]["as_of_date"], [])
                prev_weights = {row["industry"]: to_float(row["portfolio_weight_usd"]) for row in prev_rows}
                positive_rows = []
                for row in industry_rows:
                    delta = to_float(row["portfolio_weight_usd"]) - prev_weights.get(row["industry"], 0.0)
                    if delta > 0:
                        positive_rows.append({**row, "positive_delta": delta})
                totals = defaultdict(float)
                for row in positive_rows:
                    totals[row["instrument_key"]] += row["positive_delta"]
                denom = sum(totals.values())
                mapped_rows = []
                for row in positive_rows:
                    weight = totals[row["instrument_key"]] / denom if denom > 0 else 0.0
                    mapped_rows.append(
                        {
                            "signal_id": row["signal_id"],
                            "instrument_key": row["instrument_key"],
                            "symbol": row["etf_symbol"],
                            "display_name": row["industry"],
                            "target_weight": weight,
                            "signal_value": str(row["positive_delta"]),
                            "include_flag": "1",
                            "rationale_text": "Own only industries whose disclosed NBIM weight increased versus the prior snapshot.",
                        }
                    )
                targets["n4"].append(
                    {
                        "signal_date": industry_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": mapped_rows,
                    }
                )

                top3_delta = sorted(
                    mapped_rows,
                    key=lambda row: float(row["signal_value"]),
                    reverse=True,
                )[:3]
                n7_rows = []
                for row in top3_delta:
                    n7_rows.append(
                        {
                            **row,
                            "target_weight": 1.0 / len(top3_delta) if top3_delta else 0.0,
                            "rationale_text": "Own the three largest positive disclosed industry weight changes.",
                        }
                    )
                targets["n7"].append(
                    {
                        "signal_date": industry_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": n7_rows,
                    }
                )
            else:
                targets["n4"].append(
                    {
                        "signal_date": industry_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": [],
                    }
                )
                targets["n7"].append(
                    {
                        "signal_date": industry_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": [],
                    }
                )

        transition_rows = transition_industry_by_snapshot.get(snapshot, [])
        if transition_rows:
            scores = defaultdict(float)
            transition_score_by_instrument = defaultdict(float)
            for row in transition_rows:
                score = to_float(row["likely_accumulation"]) - to_float(row["likely_reduction"])
                if score > 0:
                    scores[row["instrument_key"]] += score
                    transition_score_by_instrument[row["instrument_key"]] += score
            denom = sum(scores.values())
            mapped_rows = []
            for row in transition_rows:
                score = to_float(row["likely_accumulation"]) - to_float(row["likely_reduction"])
                if score <= 0 or denom <= 0:
                    continue
                mapped_rows.append(
                    {
                        "signal_id": row["signal_id"],
                        "instrument_key": row["instrument_key"],
                        "symbol": row["etf_symbol"],
                        "display_name": row["industry"],
                        "target_weight": scores[row["instrument_key"]] / denom,
                        "signal_value": str(score),
                        "include_flag": "1",
                        "rationale_text": "Own only industries with positive NBIM accumulation-minus-reduction transition scores.",
                    }
                )
            targets["n5"].append(
                {
                    "signal_date": transition_rows[0]["public_date"],
                    "trade_date": trade_date,
                    "as_of_date": snapshot,
                    "rows": mapped_rows,
                }
            )

            if snapshot in snapshot_industry_by_snapshot and len(targets["n3"]) > 1:
                curr_rows = snapshot_industry_by_snapshot[snapshot]
                prev_snapshot = targets["n3"][-2]["as_of_date"]
                prev_rows = snapshot_industry_by_snapshot.get(prev_snapshot, [])
                prev_weights = {row["industry"]: to_float(row["portfolio_weight_usd"]) for row in prev_rows}
                delta_by_instrument = defaultdict(float)
                symbol_by_instrument = {}
                for row in curr_rows:
                    delta = to_float(row["portfolio_weight_usd"]) - prev_weights.get(row["industry"], 0.0)
                    if delta > 0:
                        delta_by_instrument[row["instrument_key"]] += delta
                    symbol_by_instrument[row["instrument_key"]] = row["etf_symbol"]
                consensus_scores = []
                for instrument_key, delta in delta_by_instrument.items():
                    trans_score = transition_score_by_instrument.get(instrument_key, 0.0)
                    if delta > 0 and trans_score > 0:
                        consensus_scores.append((instrument_key, symbol_by_instrument[instrument_key], delta * trans_score))
                consensus_scores.sort(key=lambda item: item[2], reverse=True)
                consensus_scores = consensus_scores[:3]
                total_score = sum(item[2] for item in consensus_scores)
                n8_rows = []
                for instrument_key, symbol, score in consensus_scores:
                    n8_rows.append(
                        {
                            "signal_id": f"{snapshot}::{instrument_key}::consensus",
                            "instrument_key": instrument_key,
                            "symbol": symbol,
                            "display_name": instrument_key.split('::',1)[1],
                            "target_weight": score / total_score if total_score > 0 else 0.0,
                            "signal_value": str(score),
                            "include_flag": "1",
                            "rationale_text": "Own sectors confirmed by both positive weight change and positive transition accumulation.",
                        }
                    )
                targets["n8"].append(
                    {
                        "signal_date": transition_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": n8_rows,
                    }
                )
            else:
                targets["n8"].append(
                    {
                        "signal_date": transition_rows[0]["public_date"],
                        "trade_date": trade_date,
                        "as_of_date": snapshot,
                        "rows": [],
                    }
                )

    return targets


def run_strategy(
    strategy: dict[str, str],
    rebalances: list[dict[str, object]],
    price_lookup: dict[tuple[str, str], dict[str, str]],
    calendar_dates: list[str],
) -> None:
    strategy_dir: Path = strategy["dir"]
    prefix = strategy["prefix"]
    eligibility_rows: list[dict[str, str]] = []
    rebalance_rows: list[dict[str, str]] = []
    order_rows: list[dict[str, str]] = []
    holdings_rows: list[dict[str, str]] = []
    portfolio_rows: list[dict[str, str]] = []

    rebalances_by_date = {row["trade_date"]: row for row in rebalances}
    calendar = [date for date in calendar_dates if date >= min(row["trade_date"] for row in rebalances)]
    holdings: dict[str, Position] = {}
    cash = INITIAL_NAV
    previous_nav = INITIAL_NAV

    for rebalance_index, rebalance in enumerate(rebalances, start=1):
        for row in rebalance["rows"]:
            eligibility_rows.append(
                {
                    "rebalance_id": f"{strategy['key']}::{rebalance['trade_date']}",
                    "signal_date": str(rebalance["signal_date"]),
                    "trade_date": str(rebalance["trade_date"]),
                    "as_of_date": str(rebalance["as_of_date"]),
                    "signal_id": str(row["signal_id"]),
                    "instrument_key": str(row["instrument_key"]),
                    "symbol": str(row["symbol"]),
                    "display_name": str(row["display_name"]),
                    "target_weight": f"{float(row['target_weight']):.12f}",
                    "signal_value": str(row["signal_value"]),
                    "include_flag": str(row["include_flag"]),
                    "rationale_text": str(row["rationale_text"]),
                }
            )

    for index, current_date in enumerate(calendar):
        current_values: dict[str, float] = {}
        for instrument_key, position in holdings.items():
            price_row = price_lookup.get((instrument_key, current_date))
            if price_row is None:
                continue
            current_values[instrument_key] = position.shares * to_float(price_row["adjusted_close"])

        nav_pre_rebalance = cash + sum(current_values.values())
        rebalance = rebalances_by_date.get(current_date)
        turnover_notional = 0.0
        order_count = 0
        gross_exposure_end = 0.0
        nav_end = nav_pre_rebalance

        if rebalance is not None:
            rebalance_id = f"{strategy['key']}::{current_date}"
            current_weights = {
                instrument_key: (value / nav_pre_rebalance if nav_pre_rebalance > 0 else 0.0)
                for instrument_key, value in current_values.items()
            }
            target_rows = rebalance["rows"]
            target_positions: dict[str, Position] = {}
            total_target_value = 0.0

            for row in target_rows:
                price_row = price_lookup.get((str(row["instrument_key"]), current_date))
                if price_row is None:
                    continue
                price = to_float(price_row["adjusted_close"])
                target_weight = float(row["target_weight"])
                target_value = nav_pre_rebalance * target_weight
                target_shares = target_value / price if price > 0 else 0.0
                total_target_value += target_value
                existing = holdings.get(str(row["instrument_key"]))
                previous_shares = existing.shares if existing is not None else 0.0
                delta_shares = target_shares - previous_shares
                turnover_notional += abs(delta_shares) * price
                if abs(delta_shares) > 1e-12:
                    order_count += 1
                    order_rows.append(
                        {
                            "rebalance_id": rebalance_id,
                            "trade_date": current_date,
                            "signal_date": str(rebalance["signal_date"]),
                            "as_of_date": str(rebalance["as_of_date"]),
                            "instrument_key": str(row["instrument_key"]),
                            "symbol": str(row["symbol"]),
                            "display_name": str(row["display_name"]),
                            "action": "buy" if delta_shares > 0 else "sell",
                            "price": f"{price:.10f}",
                            "shares_before": f"{previous_shares:.12f}",
                            "shares_after": f"{target_shares:.12f}",
                            "delta_shares": f"{delta_shares:.12f}",
                            "target_weight": f"{target_weight:.12f}",
                            "notional": f"{abs(delta_shares) * price:.12f}",
                            "rationale_text": strategy["description"],
                        }
                    )
                if target_shares > 1e-12:
                    target_positions[str(row["instrument_key"])] = Position(
                        instrument_key=str(row["instrument_key"]),
                        symbol=str(row["symbol"]),
                        display_name=str(row["display_name"]),
                        shares=target_shares,
                        entry_date=current_date if existing is None else existing.entry_date,
                        source_signal_id=str(row["signal_id"]),
                        source_rebalance_id=rebalance_id,
                    )

            for instrument_key, existing in holdings.items():
                if instrument_key in target_positions:
                    continue
                price_row = price_lookup.get((instrument_key, current_date))
                if price_row is None:
                    continue
                price = to_float(price_row["adjusted_close"])
                turnover_notional += abs(existing.shares) * price
                if abs(existing.shares) > 1e-12:
                    order_count += 1
                    order_rows.append(
                        {
                            "rebalance_id": rebalance_id,
                            "trade_date": current_date,
                            "signal_date": str(rebalance["signal_date"]),
                            "as_of_date": str(rebalance["as_of_date"]),
                            "instrument_key": instrument_key,
                            "symbol": existing.symbol,
                            "display_name": existing.display_name,
                            "action": "sell",
                            "price": f"{price:.10f}",
                            "shares_before": f"{existing.shares:.12f}",
                            "shares_after": "0.000000000000",
                            "delta_shares": f"{-existing.shares:.12f}",
                            "target_weight": "0.000000000000",
                            "notional": f"{abs(existing.shares) * price:.12f}",
                            "rationale_text": "Remove positions no longer selected by the strategy at this disclosure step.",
                        }
                    )

            holdings = target_positions
            cash = nav_pre_rebalance - total_target_value
            nav_end = cash + total_target_value
            gross_exposure_end = total_target_value / nav_end if nav_end > 0 else 0.0
            rebalance_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "strategy_key": strategy["key"],
                    "strategy_name": strategy["name"],
                    "signal_date": str(rebalance["signal_date"]),
                    "trade_date": current_date,
                    "as_of_date": str(rebalance["as_of_date"]),
                    "included_count": str(len(target_rows)),
                    "order_count": str(order_count),
                    "turnover_notional": f"{turnover_notional:.12f}",
                    "nav_pre_rebalance": f"{nav_pre_rebalance:.12f}",
                    "cash_end": f"{cash:.12f}",
                    "gross_exposure_end": f"{gross_exposure_end:.12f}",
                    "included_signal_ids": "|".join(str(row["signal_id"]) for row in target_rows),
                }
            )
        else:
            gross_exposure_end = (nav_pre_rebalance - cash) / nav_pre_rebalance if nav_pre_rebalance > 0 else 0.0
            nav_end = nav_pre_rebalance

        total_position_value = 0.0
        values_for_rows: dict[str, float] = {}
        for instrument_key, position in holdings.items():
            price_row = price_lookup.get((instrument_key, current_date))
            if price_row is None:
                continue
            market_value = position.shares * to_float(price_row["adjusted_close"])
            values_for_rows[instrument_key] = market_value
            total_position_value += market_value

        for instrument_key, position in holdings.items():
            market_value = values_for_rows.get(instrument_key, 0.0)
            holdings_rows.append(
                {
                    "date": current_date,
                    "strategy_key": strategy["key"],
                    "strategy_name": strategy["name"],
                    "instrument_key": instrument_key,
                    "symbol": position.symbol,
                    "display_name": position.display_name,
                    "shares": f"{position.shares:.12f}",
                    "market_value": f"{market_value:.12f}",
                    "portfolio_weight": f"{(market_value / nav_end if nav_end > 0 else 0.0):.12f}",
                    "entry_date": position.entry_date,
                    "source_signal_id": position.source_signal_id,
                    "source_rebalance_id": position.source_rebalance_id,
                }
            )

        portfolio_return = (nav_end / previous_nav - 1.0) if previous_nav > 0 else 0.0
        drawdown_base = max((to_float(row["nav_end"]) for row in portfolio_rows), default=INITIAL_NAV)
        running_peak = max(drawdown_base, nav_end)
        drawdown = (nav_end / running_peak - 1.0) if running_peak > 0 else 0.0

        portfolio_rows.append(
            {
                "date": current_date,
                "strategy_key": strategy["key"],
                "strategy_name": strategy["name"],
                "nav_start": f"{previous_nav:.12f}",
                "nav_end": f"{nav_end:.12f}",
                "period_return": f"{portfolio_return:.12f}",
                "cash_end": f"{cash:.12f}",
                "gross_exposure_end": f"{gross_exposure_end:.12f}",
                "holding_count": str(len(holdings)),
                "drawdown": f"{drawdown:.12f}",
            }
        )
        previous_nav = nav_end

    summary = {
        "strategy_key": strategy["key"],
        "strategy_name": strategy["name"],
        "initial_nav": INITIAL_NAV,
        "start_date": portfolio_rows[0]["date"],
        "end_date": portfolio_rows[-1]["date"],
        "final_nav": to_float(portfolio_rows[-1]["nav_end"]),
        "total_return": to_float(portfolio_rows[-1]["nav_end"]) / INITIAL_NAV - 1.0,
        "max_drawdown": min(to_float(row["drawdown"]) for row in portfolio_rows),
        "rebalance_count": len(rebalance_rows),
        "eligibility_count": len(eligibility_rows),
        "order_count": len(order_rows),
        "average_holding_count": sum(int(row["holding_count"]) for row in portfolio_rows) / len(portfolio_rows),
        "average_cash_weight": sum(to_float(row["cash_end"]) / to_float(row["nav_end"]) for row in portfolio_rows if to_float(row["nav_end"]) > 0) / len(portfolio_rows),
    }

    write_csv(strategy_dir / f"{prefix}_signal_eligibility.csv", eligibility_rows)
    write_csv(strategy_dir / f"{prefix}_rebalance_events.csv", rebalance_rows)
    write_csv(strategy_dir / f"{prefix}_orders.csv", order_rows)
    write_csv(strategy_dir / f"{prefix}_holdings_monthly.csv", holdings_rows)
    write_csv(strategy_dir / f"{prefix}_portfolio_monthly.csv", portfolio_rows)
    write_json(strategy_dir / f"{prefix}_summary.json", summary)


def main() -> None:
    price_lookup, calendar_dates = load_price_lookup(read_csv(PRICE_PATH))
    public_rows = read_csv(PUBLIC_DATE_MAP_PATH)
    trade_date_by_snapshot = load_trade_date_map(public_rows, calendar_dates)
    holdings_by_snapshot, snapshot_industry_by_snapshot, transition_industry_by_snapshot = build_signal_payloads()
    targets = build_strategy_targets(
        trade_date_by_snapshot,
        holdings_by_snapshot,
        snapshot_industry_by_snapshot,
        transition_industry_by_snapshot,
    )
    for strategy in STRATEGIES:
        rebalances = targets[strategy["key"]]
        if not rebalances:
            raise RuntimeError(f"No rebalances built for {strategy['key']}")
        run_strategy(strategy, rebalances, price_lookup, calendar_dates)
        print(f"Built {strategy['key']} backtest outputs in {strategy['dir']}")


if __name__ == "__main__":
    main()
