from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_ROOT = ROOT / "data" / "processed" / "signals"
PIF_ROOT = ROOT / "data" / "processed" / "pif"
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
OUT_ROOT = ROOT / "data" / "processed" / "combined" / "backtests"

STATE_PATH = SIGNALS_ROOT / "swf_signal_states.csv"
NBIM_PRICE_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"
PIF_PRICE_PATH = PIF_ROOT / "pif_twelvedata_daily_prices.csv"
PIF_BENCHMARK_PATH = PIF_ROOT / "pif_benchmark_daily.csv"
P5_PORTFOLIO_PATH = PIF_ROOT / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv"
P5_HOLDINGS_PATH = PIF_ROOT / "backtests" / "p5_cash_aware_copy" / "p5cac_holdings_daily.csv"
N4_HOLDINGS_PATH = NBIM_ROOT / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_holdings_timeline.csv"
N6_HOLDINGS_PATH = NBIM_ROOT / "backtests" / "n6_top3_industry_leaders" / "n6t3l_holdings_timeline.csv"
SECTOR_CROSSWALK_PATH = ROOT / "data" / "reference" / "pif_sector_crosswalk.csv"
COMMON_CROSSWALK_PATH = ROOT / "data" / "reference" / "common_sector_crosswalk.csv"

INITIAL_NAV = 1.0
SECTOR_TO_ETF = {
    "Communication Services": "sector::XLC",
    "Consumer Discretionary": "sector::XLY",
    "Consumer Staples": "sector::XLP",
    "Energy": "sector::XLE",
    "Financials": "sector::XLF",
    "Health Care": "sector::XLV",
    "Industrials": "sector::XLI",
    "Materials": "sector::XLB",
    "Real Estate": "sector::XLRE",
    "Technology": "sector::XLK",
    "Utilities": "sector::XLU",
}


@dataclass
class Position:
    instrument_key: str
    symbol: str
    issuer_name: str
    shares: float
    rationale: str
    sector: str = ""


STRATEGIES = [
    {
        "key": "s1",
        "name": "S1 Exposure Regime Overlay",
        "dir": OUT_ROOT / "s1_exposure_regime_overlay",
        "prefix": "s1ero",
        "type": "sector_overlay",
    },
    {
        "key": "s2",
        "name": "S2 Cross-Fund Consensus Sector Tilt",
        "dir": OUT_ROOT / "s2_cross_fund_consensus",
        "prefix": "s2cfc",
        "type": "consensus_sector_tilt",
    },
    {
        "key": "s3",
        "name": "S3 PIF Cash-Aware Base Plus NBIM Overlay",
        "dir": OUT_ROOT / "s3_pif_base_nbim_overlay",
        "prefix": "s3pbo",
        "type": "p5_overlay",
    },
    {
        "key": "s4",
        "name": "S4 N4 Sleeve With PIF Risk Filter",
        "dir": OUT_ROOT / "s4_n4_with_pif_filter",
        "prefix": "s4n4f",
        "type": "nbim_sleeve_with_pif_filter",
        "sleeve_path": N4_HOLDINGS_PATH,
        "sleeve_name": "N4",
    },
    {
        "key": "s5",
        "name": "S5 N6 Sleeve With PIF Risk Filter",
        "dir": OUT_ROOT / "s5_n6_with_pif_filter",
        "prefix": "s5n6f",
        "type": "nbim_sleeve_with_pif_filter",
        "sleeve_path": N6_HOLDINGS_PATH,
        "sleeve_name": "N6",
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


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def load_state_rows() -> list[dict[str, str]]:
    return sorted(read_csv(STATE_PATH), key=lambda row: row["event_date"])


def load_nbim_price_lookup() -> tuple[dict[tuple[str, str], float], list[str]]:
    rows = read_csv(NBIM_PRICE_PATH)
    lookup: dict[tuple[str, str], float] = {}
    calendar_sets: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["adjust_mode"] != "all":
            continue
        lookup[(row["instrument_key"], row["date"])] = to_float(row["close"])
        calendar_sets[row["instrument_key"]].add(row["date"])
    tradable_keys = ["benchmark_vt", *SECTOR_TO_ETF.values()]
    common_calendar = set.intersection(*(calendar_sets[key] for key in tradable_keys))
    return lookup, sorted(common_calendar)


def load_pif_price_lookup() -> dict[tuple[str, str], float]:
    rows = read_csv(PIF_PRICE_PATH)
    lookup: dict[tuple[str, str], float] = {}
    for row in rows:
        if row["adjust_mode"] != "all":
            continue
        lookup[(row["symbol"], row["date"])] = to_float(row["close"])
    return lookup


def load_benchmark_rows() -> list[dict[str, str]]:
    nbim_rows = [
        {
            "date": row["date"],
            "benchmark_key": "VT",
            "close": row["close"],
        }
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all" and row["instrument_key"] == "benchmark_vt"
    ]
    pif_rows = [
        {
            "date": row["date"],
            "benchmark_key": row["benchmark_key"],
            "close": row["close"],
        }
        for row in read_csv(PIF_BENCHMARK_PATH)
        if row["adjust_mode"] == "all"
    ]
    return sorted(nbim_rows + pif_rows, key=lambda row: (row["benchmark_key"], row["date"]))


def load_p5_daily() -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    portfolio_by_date = {row["date"]: row for row in read_csv(P5_PORTFOLIO_PATH)}
    holdings_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(P5_HOLDINGS_PATH):
        holdings_by_date[row["date"]].append(row)
    return portfolio_by_date, holdings_by_date


def load_nbim_sleeve_targets(path: Path) -> tuple[dict[str, dict[str, dict[str, str]]], list[str]]:
    holdings_by_date: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv(path):
        holdings_by_date[row["date"]][row["instrument_key"]] = row
    return dict(holdings_by_date), sorted(holdings_by_date)


def load_pif_sector_by_security() -> dict[str, str]:
    common_map = {
        row["raw_label"]: row["common_sector"]
        for row in read_csv(COMMON_CROSSWALK_PATH)
        if row["source_system"] == "PIF" and row["raw_label_type"] == "sector"
    }
    mapping: dict[str, str] = {}
    for row in read_csv(SECTOR_CROSSWALK_PATH):
        mapping[row["cusip"]] = common_map.get(row["pif_sector"], "")
    return mapping


def sector_from_security_key(security_key: str, sector_by_cusip: dict[str, str]) -> str:
    cusip = security_key.split("|", 1)[0]
    return sector_by_cusip.get(cusip, "")


def get_state_field(row: dict[str, str], prefix: str, sector: str) -> str:
    slug = sector.lower().replace(" ", "_")
    return row[f"{prefix}__{slug}"]


def select_s1_targets(state: dict[str, str]) -> tuple[dict[str, float], float, str]:
    exposure_state = state["pif_exposure_state"] or "initial"
    exposure_map = {"contracting": 0.50, "stable": 0.75, "expanding": 1.00, "initial": 1.00}
    gross_exposure = exposure_map.get(exposure_state, 0.75)
    selected = [
        sector
        for sector in SECTOR_TO_ETF
        if get_state_field(state, "nbim_sector_state", sector) == "overweight"
    ]
    if not selected:
        selected = [
            sector
            for sector in SECTOR_TO_ETF
            if get_state_field(state, "nbim_top3", sector) == "1"
        ]
    weights = {sector: to_float(get_state_field(state, "nbim_sector_weight", sector)) for sector in selected}
    total = sum(weights.values())
    if total == 0:
        weights = {sector: 1.0 / len(selected) for sector in selected} if selected else {}
    else:
        weights = {sector: value / total for sector, value in weights.items()}
    targets = {SECTOR_TO_ETF[sector]: gross_exposure * weight for sector, weight in weights.items()}
    rationale = f"exposure_state={exposure_state}; selected={','.join(selected) if selected else 'none'}"
    return targets, 1.0 - gross_exposure, rationale


def select_s2_targets(state: dict[str, str]) -> tuple[dict[str, float], float, str]:
    exposure_state = state["pif_exposure_state"] or "initial"
    exposure_map = {"contracting": 0.25, "stable": 0.60, "expanding": 1.00, "initial": 1.00}
    gross_exposure = exposure_map.get(exposure_state, 0.60)
    selected = [
        sector
        for sector in SECTOR_TO_ETF
        if get_state_field(state, "cross_fund_consensus", sector) == "yes"
    ]
    if selected:
        weights = {sector: to_float(get_state_field(state, "nbim_sector_weight", sector)) for sector in selected}
        total = sum(weights.values())
        weights = {sector: value / total for sector, value in weights.items()} if total else {
            sector: 1.0 / len(selected) for sector in selected
        }
        targets = {SECTOR_TO_ETF[sector]: gross_exposure * weight for sector, weight in weights.items()}
        rationale = f"consensus_sectors={','.join(selected)}; exposure_state={exposure_state}"
    else:
        targets = {"benchmark_vt": gross_exposure}
        rationale = f"no_consensus; fallback=VT; exposure_state={exposure_state}"
    return targets, 1.0 - gross_exposure, rationale


def build_s3_targets(
    state: dict[str, str],
    holdings_rows: list[dict[str, str]],
    cash_weight: float,
    sector_by_cusip: dict[str, str],
) -> tuple[dict[str, float], float, str]:
    if not holdings_rows:
        return {}, 1.0, "No base P5 holdings; remain in cash."
    invested_weight = 1.0 - cash_weight
    base_values = [to_float(row["market_value_end"]) for row in holdings_rows]
    total_value = sum(base_values)
    if total_value <= 0:
        return {}, 1.0, "Base P5 sleeve has zero value; remain in cash."

    weighted: dict[str, float] = {}
    sector_notes: list[str] = []
    for row in holdings_rows:
        security_key = row["security_key"]
        sector = sector_from_security_key(security_key, sector_by_cusip)
        nbim_state = get_state_field(state, "nbim_sector_state", sector) if sector else ""
        nbim_top3 = get_state_field(state, "nbim_top3", sector) if sector else "0"
        if nbim_state == "overweight":
            multiplier = 1.25
        elif nbim_state == "underweight":
            multiplier = 0.75
        elif nbim_top3 == "1":
            multiplier = 1.10
        else:
            multiplier = 1.0
        base_weight = to_float(row["market_value_end"]) / total_value
        weighted[security_key] = base_weight * multiplier
        sector_notes.append(f"{row['symbol']}:{sector or 'UNKNOWN'}:{multiplier:.2f}")

    total_weighted = sum(weighted.values())
    targets = {
        security_key: invested_weight * value / total_weighted
        for security_key, value in weighted.items()
    }
    rationale = f"cash_weight={cash_weight:.6f}; sector_multipliers={'|'.join(sector_notes[:12])}"
    return targets, cash_weight, rationale


def get_pif_exposure_weight(state: dict[str, str]) -> tuple[float, str]:
    exposure_state = state["pif_exposure_state"] or "initial"
    exposure_map = {"contracting": 0.50, "stable": 0.75, "expanding": 1.00, "initial": 1.00}
    return exposure_map.get(exposure_state, 0.75), exposure_state


def latest_date_on_or_before(sorted_dates: list[str], current_date: str) -> str:
    latest = ""
    for date_value in sorted_dates:
        if date_value > current_date:
            break
        latest = date_value
    return latest


def build_nbim_filtered_sleeve_targets(
    state: dict[str, str],
    sleeve_holdings_by_date: dict[str, dict[str, dict[str, str]]],
    sleeve_dates: list[str],
    current_date: str,
    sleeve_name: str,
) -> tuple[dict[str, float], float, str, dict[str, dict[str, str]]]:
    exposure_weight, exposure_state = get_pif_exposure_weight(state)
    sleeve_date = latest_date_on_or_before(sleeve_dates, current_date)
    if not sleeve_date or sleeve_date not in sleeve_holdings_by_date:
        return {}, 1.0, f"{sleeve_name} sleeve unavailable as of {current_date}; remain in cash.", {}
    sleeve_rows = sleeve_holdings_by_date[sleeve_date]
    targets = {
        instrument_key: exposure_weight * to_float(row["portfolio_weight"])
        for instrument_key, row in sleeve_rows.items()
    }
    cash_weight = 1.0 - exposure_weight
    rationale = (
        f"base_sleeve={sleeve_name}; sleeve_date={sleeve_date}; "
        f"exposure_state={exposure_state}; exposure_weight={exposure_weight:.2f}"
    )
    return targets, cash_weight, rationale, sleeve_rows


def run_strategy(strategy: dict[str, str]) -> None:
    state_rows = load_state_rows()
    nbim_prices, calendar_dates = load_nbim_price_lookup()
    pif_prices = load_pif_price_lookup()
    p5_portfolio_by_date, p5_holdings_by_date = load_p5_daily()
    sector_by_cusip = load_pif_sector_by_security()
    sleeve_holdings_by_date: dict[str, dict[str, dict[str, str]]] = {}
    sleeve_dates: list[str] = []
    if strategy["type"] == "nbim_sleeve_with_pif_filter":
        sleeve_holdings_by_date, sleeve_dates = load_nbim_sleeve_targets(strategy["sleeve_path"])

    start_date = "2019-02-14"
    end_date = "2026-05-18"
    calendar = [d for d in calendar_dates if start_date <= d <= end_date]
    state_rows = [row for row in state_rows if start_date <= row["event_date"] <= end_date]
    rebalance_dates = {row["event_date"]: row for row in state_rows}

    positions: dict[str, Position] = {}
    cash = INITIAL_NAV
    holdings_daily: list[dict[str, str]] = []
    portfolio_daily: list[dict[str, str]] = []
    rebalance_rows: list[dict[str, str]] = []
    order_rows: list[dict[str, str]] = []
    signal_rows: list[dict[str, str]] = []
    peak_nav = INITIAL_NAV
    prev_nav_end = INITIAL_NAV

    for idx, current_date in enumerate(calendar):
        nav_start = prev_nav_end
        cash_start = cash

        pnl_day = 0.0
        current_values: dict[str, float] = {}
        for pos in positions.values():
            if strategy["type"] in {"sector_overlay", "consensus_sector_tilt", "nbim_sleeve_with_pif_filter"}:
                price = nbim_prices[(pos.instrument_key, current_date)]
            else:
                price = pif_prices[(pos.symbol, current_date)]
            current_value = pos.shares * price
            current_values[pos.instrument_key] = current_value
            prev_date = calendar[idx - 1] if idx > 0 else current_date
            if idx > 0:
                if strategy["type"] in {"sector_overlay", "consensus_sector_tilt", "nbim_sleeve_with_pif_filter"}:
                    prev_price = nbim_prices[(pos.instrument_key, prev_date)]
                else:
                    prev_price = pif_prices[(pos.symbol, prev_date)]
                pnl_day += pos.shares * (price - prev_price)
        nav_pre = cash + sum(current_values.values())

        rebalance_flag = "0"
        rebalance_id = ""
        buys_count = 0
        sells_count = 0
        signal_count = 0
        rationale = ""

        if current_date in rebalance_dates:
            state = rebalance_dates[current_date]
            rebalance_flag = "1"
            rebalance_id = f"{strategy['prefix'].upper()}-R{len(rebalance_rows)+1:03d}"

            if strategy["type"] == "sector_overlay":
                target_weights, target_cash_weight, rationale = select_s1_targets(state)
                signal_count = len(target_weights)
                target_nav = nav_pre
                cash = target_nav * target_cash_weight
                desired_positions = {}
                for instrument_key, weight in target_weights.items():
                    price = nbim_prices[(instrument_key, current_date)]
                    desired_positions[instrument_key] = target_nav * weight / price if price else 0.0
                desired_meta = {
                    instrument_key: {
                        "symbol": instrument_key.split("::", 1)[1],
                        "issuer_name": instrument_key.split("::", 1)[1],
                        "sector": next(k for k, v in SECTOR_TO_ETF.items() if v == instrument_key),
                    }
                    for instrument_key in desired_positions
                }
            elif strategy["type"] == "consensus_sector_tilt":
                target_weights, target_cash_weight, rationale = select_s2_targets(state)
                signal_count = len(target_weights)
                target_nav = nav_pre
                cash = target_nav * target_cash_weight
                desired_positions = {}
                for instrument_key, weight in target_weights.items():
                    price = nbim_prices[(instrument_key, current_date)]
                    desired_positions[instrument_key] = target_nav * weight / price if price else 0.0
                desired_meta = {
                    instrument_key: {
                        "symbol": "VT" if instrument_key == "benchmark_vt" else instrument_key.split("::", 1)[1],
                        "issuer_name": "Vanguard Total World Stock ETF" if instrument_key == "benchmark_vt" else instrument_key.split("::", 1)[1],
                        "sector": "" if instrument_key == "benchmark_vt" else next(k for k, v in SECTOR_TO_ETF.items() if v == instrument_key),
                    }
                    for instrument_key in desired_positions
                }
            elif strategy["type"] == "p5_overlay":
                base_port = p5_portfolio_by_date[current_date]
                base_holdings = p5_holdings_by_date[current_date]
                cash_weight = to_float(base_port["cash_weight_end"])
                target_weights, target_cash_weight, rationale = build_s3_targets(state, base_holdings, cash_weight, sector_by_cusip)
                signal_count = len(target_weights)
                target_nav = nav_pre
                cash = target_nav * target_cash_weight
                desired_positions = {}
                desired_meta = {}
                for row in base_holdings:
                    security_key = row["security_key"]
                    if security_key not in target_weights:
                        continue
                    price = pif_prices[(row["symbol"], current_date)]
                    desired_positions[security_key] = target_nav * target_weights[security_key] / price if price else 0.0
                    desired_meta[security_key] = {
                        "symbol": row["symbol"],
                        "issuer_name": row["issuer_name"],
                        "sector": sector_from_security_key(security_key, sector_by_cusip),
                    }
            else:
                target_weights, target_cash_weight, rationale, sleeve_rows = build_nbim_filtered_sleeve_targets(
                    state,
                    sleeve_holdings_by_date,
                    sleeve_dates,
                    current_date,
                    strategy["sleeve_name"],
                )
                signal_count = len(target_weights)
                target_nav = nav_pre
                cash = target_nav * target_cash_weight
                desired_positions = {}
                desired_meta = {}
                for instrument_key, weight in target_weights.items():
                    price = nbim_prices[(instrument_key, current_date)]
                    desired_positions[instrument_key] = target_nav * weight / price if price else 0.0
                    sleeve_row = sleeve_rows[instrument_key]
                    desired_meta[instrument_key] = {
                        "symbol": sleeve_row["symbol"],
                        "issuer_name": sleeve_row["display_name"],
                        "sector": sleeve_row["display_name"],
                    }

            for existing_key, pos in list(positions.items()):
                desired_shares = desired_positions.get(existing_key, 0.0)
                if desired_shares == 0.0 and pos.shares != 0.0:
                    sells_count += 1
                    price = nbim_prices[(existing_key, current_date)] if strategy["type"] in {"sector_overlay", "consensus_sector_tilt", "nbim_sleeve_with_pif_filter"} else pif_prices[(pos.symbol, current_date)]
                    order_rows.append(
                        {
                            "rebalance_id": rebalance_id,
                            "execution_date": current_date,
                            "side": "SELL",
                            "instrument_key": existing_key,
                            "issuer_name": pos.issuer_name,
                            "symbol": pos.symbol,
                            "shares": f"{pos.shares:.12f}",
                            "execution_price": f"{price:.8f}",
                            "execution_value": f"{pos.shares * price:.12f}",
                            "sector": pos.sector,
                            "rationale_text": rationale,
                        }
                    )
                    del positions[existing_key]

            for instrument_key, desired_shares in desired_positions.items():
                meta = desired_meta[instrument_key]
                current_shares = positions[instrument_key].shares if instrument_key in positions else 0.0
                delta = desired_shares - current_shares
                if abs(delta) < 1e-12:
                    continue
                side = "BUY" if delta > 0 else "SELL"
                if side == "BUY":
                    buys_count += 1
                else:
                    sells_count += 1
                price = nbim_prices[(instrument_key, current_date)] if strategy["type"] in {"sector_overlay", "consensus_sector_tilt", "nbim_sleeve_with_pif_filter"} else pif_prices[(meta["symbol"], current_date)]
                order_rows.append(
                    {
                        "rebalance_id": rebalance_id,
                        "execution_date": current_date,
                        "side": side,
                        "instrument_key": instrument_key,
                        "issuer_name": meta["issuer_name"],
                        "symbol": meta["symbol"],
                        "shares": f"{abs(delta):.12f}",
                        "execution_price": f"{price:.8f}",
                        "execution_value": f"{abs(delta) * price:.12f}",
                        "sector": meta["sector"],
                        "rationale_text": rationale,
                    }
                )
                positions[instrument_key] = Position(
                    instrument_key=instrument_key,
                    symbol=meta["symbol"],
                    issuer_name=meta["issuer_name"],
                    shares=desired_shares,
                    rationale=rationale,
                    sector=meta["sector"],
                )

            signal_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "trade_date": current_date,
                    "strategy_id": strategy["name"],
                    "signal_count": str(signal_count),
                    "rationale_text": rationale,
                    "pif_exposure_state": state["pif_exposure_state"],
                }
            )
            rebalance_rows.append(
                {
                    "rebalance_id": rebalance_id,
                    "trade_date": current_date,
                    "signal_count": str(signal_count),
                    "positions_bought_count": str(buys_count),
                    "positions_sold_count": str(sells_count),
                    "cash_after_rebalance": f"{cash:.12f}",
                    "position_count_end": str(len(positions)),
                    "rationale_text": rationale,
                }
            )

        nav_end = cash
        gross_exposure = 0.0
        position_snapshots: list[dict[str, object]] = []
        for pos in positions.values():
            price = nbim_prices[(pos.instrument_key, current_date)] if strategy["type"] in {"sector_overlay", "consensus_sector_tilt", "nbim_sleeve_with_pif_filter"} else pif_prices[(pos.symbol, current_date)]
            market_value = pos.shares * price
            nav_end += market_value
            gross_exposure += market_value
            position_snapshots.append(
                {
                    "date": current_date,
                    "instrument_key": pos.instrument_key,
                    "issuer_name": pos.issuer_name,
                    "symbol": pos.symbol,
                    "sector": pos.sector,
                    "shares_end": pos.shares,
                    "close_price": price,
                    "market_value_end": market_value,
                    "rebalance_id": rebalance_id,
                }
            )

        for snapshot in position_snapshots:
            holdings_daily.append(
                {
                    "date": str(snapshot["date"]),
                    "instrument_key": str(snapshot["instrument_key"]),
                    "issuer_name": str(snapshot["issuer_name"]),
                    "symbol": str(snapshot["symbol"]),
                    "sector": str(snapshot["sector"]),
                    "shares_end": f"{float(snapshot['shares_end']):.12f}",
                    "close_price": f"{float(snapshot['close_price']):.8f}",
                    "market_value_end": f"{float(snapshot['market_value_end']):.12f}",
                    "weight_end": f"{(float(snapshot['market_value_end']) / nav_end if nav_end else 0.0):.12f}",
                    "rebalance_id": str(snapshot["rebalance_id"]),
                }
            )

        return_day = (nav_end / nav_start - 1.0) if nav_start else 0.0
        peak_nav = max(peak_nav, nav_end)
        drawdown = nav_end / peak_nav - 1.0 if peak_nav else 0.0
        portfolio_daily.append(
            {
                "date": current_date,
                "nav_start": f"{nav_start:.12f}",
                "cash_start": f"{cash_start:.12f}",
                "pnl_day": f"{pnl_day:.12f}",
                "nav_pre_rebalance": f"{nav_pre:.12f}",
                "nav_end": f"{nav_end:.12f}",
                "return_day": f"{return_day:.12f}",
                "cum_return": f"{(nav_end / INITIAL_NAV - 1.0):.12f}",
                "cash_end": f"{cash:.12f}",
                "cash_weight_end": f"{(cash / nav_end if nav_end else 0.0):.12f}",
                "gross_exposure_end": f"{(gross_exposure / nav_end if nav_end else 0.0):.12f}",
                "position_count_end": str(len(positions)),
                "rebalance_executed_flag": rebalance_flag,
                "rebalance_id": rebalance_id,
                "buys_count": str(buys_count),
                "sells_count": str(sells_count),
                "peak_nav_to_date": f"{peak_nav:.12f}",
                "drawdown_to_date": f"{drawdown:.12f}",
            }
        )
        prev_nav_end = nav_end

    summary = {
        "strategy_id": strategy["key"].upper(),
        "strategy_name": strategy["name"],
        "initial_nav": INITIAL_NAV,
        "final_nav": prev_nav_end,
        "total_return": prev_nav_end / INITIAL_NAV - 1.0,
        "rebalance_count": len(rebalance_rows),
        "orders_count": len(order_rows),
        "holdings_daily_rows": len(holdings_daily),
        "portfolio_daily_rows": len(portfolio_daily),
        "signal_rows": len(signal_rows),
        "start_date": calendar[0],
        "end_date": calendar[-1],
        "max_drawdown": min(to_float(row["drawdown_to_date"]) for row in portfolio_daily),
        "avg_cash_weight_end": sum(to_float(row["cash_weight_end"]) for row in portfolio_daily) / len(portfolio_daily),
    }

    prefix = strategy["prefix"]
    strategy_dir = strategy["dir"]
    write_csv(strategy_dir / f"{prefix}_signal_eligibility.csv", signal_rows)
    write_csv(strategy_dir / f"{prefix}_rebalance_events.csv", rebalance_rows)
    write_csv(strategy_dir / f"{prefix}_orders.csv", order_rows if order_rows else [
        {
            "rebalance_id": "",
            "execution_date": "",
            "side": "",
            "instrument_key": "",
            "issuer_name": "",
            "symbol": "",
            "shares": "",
            "execution_price": "",
            "execution_value": "",
            "sector": "",
            "rationale_text": "",
        }
    ])
    write_csv(strategy_dir / f"{prefix}_holdings_daily.csv", holdings_daily if holdings_daily else [
        {
            "date": "",
            "instrument_key": "",
            "issuer_name": "",
            "symbol": "",
            "sector": "",
            "shares_end": "",
            "close_price": "",
            "market_value_end": "",
            "weight_end": "",
            "rebalance_id": "",
        }
    ])
    write_csv(strategy_dir / f"{prefix}_portfolio_daily.csv", portfolio_daily)
    write_json(strategy_dir / f"{prefix}_summary.json", summary)


def main() -> None:
    for strategy in STRATEGIES:
        run_strategy(strategy)
        print(f"Completed {strategy['name']}")


if __name__ == "__main__":
    main()
