#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "audit"
DETAIL_PATH = OUT_DIR / "original_pipeline_audit_checks.csv"
SUMMARY_PATH = OUT_DIR / "original_pipeline_audit_summary.json"


def read_csv(path: Path, encoding: str = "utf-8", delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as infile:
        return list(csv.DictReader(infile, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def aggregate_weights(rows: list[dict[str, str]], value_field: str, key_field: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row[key_field]] += to_float(row[value_field])
    total = sum(totals.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in totals.items()}


def add_check(rows: list[dict[str, str]], check_name: str, status: str, detail: str) -> None:
    rows.append({"check_name": check_name, "status": status, "detail": detail})


def strip_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def count_info_tables(path: Path) -> int:
    root = ET.parse(path).getroot()
    count = sum(1 for elem in root.iter() if strip_tag(elem.tag) == "infoTable")
    return count if count else (1 if strip_tag(root.tag) == "infoTable" else 0)


def parse_date(text: str) -> date:
    y, m, d = text.split("-")
    return date(int(y), int(m), int(d))


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    d += timedelta(days=7 * (n - 1))
    return d


def last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def observed_fixed_holiday(year: int, month: int, day: int) -> date:
    actual = date(year, month, day)
    if actual.weekday() == 5:
        return actual - timedelta(days=1)
    if actual.weekday() == 6:
        return actual + timedelta(days=1)
    return actual


def nyse_holidays(year: int) -> set[date]:
    holidays = {
        observed_fixed_holiday(year, 1, 1),
        nth_weekday(year, 1, 0, 3),
        nth_weekday(year, 2, 0, 3),
        easter_sunday(year) - timedelta(days=2),
        last_weekday(year, 5, 0),
        observed_fixed_holiday(year, 7, 4),
        nth_weekday(year, 9, 0, 1),
        nth_weekday(year, 11, 3, 4),
        observed_fixed_holiday(year, 12, 25),
    }
    if year >= 2022:
        holidays.add(observed_fixed_holiday(year, 6, 19))
    if year == 2025:
        holidays.add(date(2025, 1, 9))
    return holidays


def next_nyse_trading_day(signal_date: str) -> str:
    d = parse_date(signal_date) + timedelta(days=1)
    while d.weekday() >= 5 or d in nyse_holidays(d.year):
        d += timedelta(days=1)
    return d.isoformat()


def load_nbim_raw_rows(path: Path) -> list[dict[str, str]]:
    encodings = ["utf-8-sig", "utf-16", "utf-16le", "latin-1"]
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as infile:
                return list(csv.DictReader(infile, delimiter=";"))
        except UnicodeError:
            continue
    raise UnicodeError(f"Could not decode {path}")


def is_effectively_empty_nbim_row(row: dict[str, str | None]) -> bool:
    return all((value or "").strip() == "" for value in row.values())


def main() -> None:
    checks: list[dict[str, str]] = []

    # PIF raw filings -> processed holdings
    raw_pif_dir = ROOT / "data" / "raw" / "pif" / "13f"
    filing_index = read_csv(ROOT / "data" / "processed" / "pif" / "pif_13f_filing_index.csv")
    pif_all = read_csv(ROOT / "data" / "processed" / "pif" / "pif_13f_holdings_all_filings.csv")
    pif_canonical = read_csv(ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv")

    raw_counts = {}
    for filing_dir in sorted(path for path in raw_pif_dir.iterdir() if path.is_dir()):
        xml_paths = [p for p in filing_dir.glob("*.xml") if p.name != "primary_doc.xml"]
        info_path = next((p for p in xml_paths if "informationtable" in p.name.lower() or "infotable" in p.name.lower()), xml_paths[0])
        raw_counts[filing_dir.name] = count_info_tables(info_path)
    index_counts = {row["accession_number"]: int(row["row_count"]) for row in filing_index}
    processed_all_counts = Counter(row["accession_number"] for row in pif_all)
    pif_raw_ok = all(raw_counts[k] == index_counts.get(k, -1) == processed_all_counts.get(k, -2) for k in raw_counts)
    add_check(
        checks,
        "pif_raw_filing_row_counts_match_processed",
        "pass" if pif_raw_ok else "fail",
        f"filings={len(raw_counts)} canonical_periods={len({row['period_of_report'] for row in filing_index})}",
    )

    keep_by_period = defaultdict(list)
    for row in filing_index:
        keep_by_period[row["period_of_report"]].append(row["keep_flag"])
    keep_ok = all(flags.count("1") == 1 for flags in keep_by_period.values())
    canonical_count_expected = sum(int(row["row_count"]) for row in filing_index if row["keep_flag"] == "1")
    add_check(
        checks,
        "pif_canonical_accession_selection",
        "pass" if keep_ok and canonical_count_expected == len(pif_canonical) else "fail",
        f"expected_rows={canonical_count_expected} actual_rows={len(pif_canonical)} periods={len(keep_by_period)}",
    )

    # PIF transition invariants
    pif_transitions = read_csv(ROOT / "data" / "processed" / "pif" / "pif_13f_transition_events.csv")
    pif_index = defaultdict(dict)
    for row in pif_canonical:
        key = "|".join([row["cusip"], row["title_of_class"], row["put_call"], row["share_type"], row["issuer_name"]])
        pif_index[row["as_of_date"]][key] = row
    pif_failures = 0
    for row in pif_transitions:
        prev_present = row["security_key"] in pif_index[row["prev_as_of_date"]]
        curr_present = row["security_key"] in pif_index[row["curr_as_of_date"]]
        expected_transition = "continued_holding" if prev_present and curr_present else ("exit_observed" if prev_present else "entry_observed")
        if row["presence_transition"] != expected_transition:
            pif_failures += 1
    add_check(
        checks,
        "pif_transition_presence_invariants",
        "pass" if pif_failures == 0 else "fail",
        f"rows={len(pif_transitions)} failures={pif_failures}",
    )

    # PIF signal panel and calendar
    pif_signal_panel = read_csv(ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_panel.csv")
    holdings_count = sum(1 for row in pif_signal_panel if row["signal_source"] == "holdings")
    transition_count = sum(1 for row in pif_signal_panel if row["signal_source"] == "transition")
    add_check(
        checks,
        "pif_signal_panel_row_counts",
        "pass" if holdings_count == len(pif_canonical) and transition_count == len(pif_transitions) else "fail",
        f"holdings_panel={holdings_count}/{len(pif_canonical)} transition_panel={transition_count}/{len(pif_transitions)}",
    )

    pif_calendar = read_csv(ROOT / "data" / "processed" / "pif" / "pif_trade_calendar.csv")
    calendar_failures = sum(1 for row in pif_calendar if row["trade_date"] != next_nyse_trading_day(row["signal_date"]))
    add_check(
        checks,
        "pif_trade_calendar_next_day_rule",
        "pass" if calendar_failures == 0 else "fail",
        f"rows={len(pif_calendar)} failures={calendar_failures}",
    )

    # PIF order prices should bind exactly to the stored price layer.
    pif_price_rows = read_csv(ROOT / "data/processed/pif/pif_twelvedata_daily_prices.csv")
    pif_adj_prices = {
        (row["security_key"], row["date"]): to_float(row["close"])
        for row in pif_price_rows if row["adjust_mode"] == "all"
    }
    pif_raw_prices = {
        (row["security_key"], row["date"]): to_float(row["close"])
        for row in pif_price_rows if row["adjust_mode"] == "none"
    }
    pif_order_files = [
        ROOT / "data/processed/pif/backtests/p1/p1_orders.csv",
        ROOT / "data/processed/pif/backtests/p2_equal_weight/p2ew_orders.csv",
        ROOT / "data/processed/pif/backtests/p3_accumulation_tilt/p3at_orders.csv",
        ROOT / "data/processed/pif/backtests/p4_exit_avoidance/p4ea_orders.csv",
        ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_orders.csv",
    ]
    pif_price_ok = True
    pif_price_detail = ""
    checked_rows = 0
    for path in pif_order_files:
        for row in read_csv(path):
            checked_rows += 1
            key = (row["security_key"], row["execution_date"])
            expected_adj = pif_adj_prices.get(key)
            expected_raw = pif_raw_prices.get(key, expected_adj)
            actual_adj = to_float(row["execution_price"])
            actual_raw = to_float(row.get("execution_price_raw"))
            if expected_adj is None or abs(actual_adj - expected_adj) > 1e-8:
                pif_price_ok = False
                pif_price_detail = f"{path.name} {key} adjusted expected={expected_adj} actual={actual_adj}"
                break
            if row.get("execution_price_raw", "") and expected_raw is not None and abs(actual_raw - expected_raw) > 1e-8:
                pif_price_ok = False
                pif_price_detail = f"{path.name} {key} raw expected={expected_raw} actual={actual_raw}"
                break
        if not pif_price_ok:
            break
    add_check(checks, "pif_order_prices_match_price_layer", "pass" if pif_price_ok else "fail", pif_price_detail or f"orders={checked_rows}")

    # PIF P1 / P2 / P3 / P4 portfolio construction
    def check_equal_weight(eligibility_path: str, holdings_path: str, include_field: str = "include_flag") -> tuple[bool, str]:
        elig = read_csv(ROOT / eligibility_path)
        hold = read_csv(ROOT / holdings_path)
        elig_by_date = defaultdict(list)
        for row in elig:
            if row[include_field] == "1":
                elig_by_date[row["trade_date"]].append(row["security_key"])
        hold_by_date = defaultdict(list)
        for row in hold:
            hold_by_date[row["date"]].append(row)
        for trade_date, keys in elig_by_date.items():
            expected_weight = 1.0 / len(keys) if keys else 0.0
            actual_rows = hold_by_date[trade_date]
            if sorted(row["security_key"] for row in actual_rows) != sorted(keys):
                return False, f"{trade_date} holdings set mismatch"
            for row in actual_rows:
                if abs(to_float(row["weight_end"]) - expected_weight) > 1e-10:
                    return False, f"{trade_date} expected={expected_weight:.12f} actual={row['weight_end']}"
        return True, f"rebalances={len(elig_by_date)}"

    ok, detail = check_equal_weight(
        "data/processed/pif/backtests/p1/p1_signal_eligibility.csv",
        "data/processed/pif/backtests/p1/p1_holdings_daily.csv",
    )
    add_check(checks, "p1_rebalance_matches_equal_weight_entry_basket", "pass" if ok else "fail", detail)

    ok, detail = check_equal_weight(
        "data/processed/pif/backtests/p2_equal_weight/p2ew_signal_eligibility.csv",
        "data/processed/pif/backtests/p2_equal_weight/p2ew_holdings_daily.csv",
    )
    add_check(checks, "p2_rebalance_matches_equal_weight_full_sleeve", "pass" if ok else "fail", detail)

    # P3 weights proportional to tilt score.
    p3_elig = read_csv(ROOT / "data/processed/pif/backtests/p3_accumulation_tilt/p3at_signal_eligibility.csv")
    p3_hold = read_csv(ROOT / "data/processed/pif/backtests/p3_accumulation_tilt/p3at_holdings_daily.csv")
    p3_ok = True
    p3_detail = ""
    elig_by_date = defaultdict(list)
    for row in p3_elig:
        if row["include_flag"] == "1":
            elig_by_date[row["trade_date"]].append(row)
    hold_by_date = defaultdict(dict)
    for row in p3_hold:
        hold_by_date[row["date"]][row["security_key"]] = row
    for trade_date, rows in elig_by_date.items():
        total_score = sum(to_float(row["tilt_score"]) for row in rows)
        actual = hold_by_date[trade_date]
        if sorted(actual) != sorted(row["security_key"] for row in rows):
            p3_ok = False
            p3_detail = f"{trade_date} holdings set mismatch"
            break
        for row in rows:
            expected_weight = to_float(row["tilt_score"]) / total_score if total_score else 0.0
            actual_weight = to_float(actual[row["security_key"]]["weight_end"])
            if abs(expected_weight - actual_weight) > 1e-10:
                p3_ok = False
                p3_detail = f"{trade_date} {row['security_key']} expected={expected_weight:.12f} actual={actual_weight:.12f}"
                break
        if not p3_ok:
            break
    add_check(checks, "p3_rebalance_matches_tilt_scores", "pass" if p3_ok else "fail", p3_detail or f"rebalances={len(elig_by_date)}")

    ok, detail = check_equal_weight(
        "data/processed/pif/backtests/p4_exit_avoidance/p4ea_signal_eligibility.csv",
        "data/processed/pif/backtests/p4_exit_avoidance/p4ea_holdings_daily.csv",
    )
    add_check(checks, "p4_rebalance_matches_equal_weight_filtered_sleeve", "pass" if ok else "fail", detail)

    # P5 order replay should exactly reproduce rebalance-date holdings and cash.
    p5_orders = read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_orders.csv")
    p5_holdings = read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_holdings_daily.csv")
    p5_portfolio = {row["date"]: row for row in read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_portfolio_daily.csv")}
    p5_rebalances = read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_rebalance_events.csv")
    orders_by_rebalance = defaultdict(list)
    for row in p5_orders:
        orders_by_rebalance[row["rebalance_id"]].append(row)
    holdings_by_date = defaultdict(dict)
    for row in p5_holdings:
        holdings_by_date[row["date"]][row["security_key"]] = row
    replay_positions: dict[str, float] = {}
    p5_ok = True
    p5_detail = ""
    for rebalance in p5_rebalances:
        rebalance_id = rebalance["rebalance_id"]
        for order in orders_by_rebalance[rebalance_id]:
            shares = to_float(order["shares"])
            security_key = order["security_key"]
            replay_positions.setdefault(security_key, 0.0)
            if order["side"] == "BUY":
                replay_positions[security_key] += shares
            else:
                replay_positions[security_key] -= shares
            if replay_positions[security_key] <= 1e-12:
                replay_positions.pop(security_key, None)
        actual_rows = holdings_by_date[rebalance["trade_date"]]
        if set(replay_positions) != set(actual_rows):
            p5_ok = False
            p5_detail = f"{rebalance_id} holdings keys expected={sorted(replay_positions)} actual={sorted(actual_rows)}"
            break
        for security_key, expected_shares in replay_positions.items():
            actual_shares = to_float(actual_rows[security_key]["shares_end"])
            if abs(expected_shares - actual_shares) > 1e-10:
                p5_ok = False
                p5_detail = f"{rebalance_id} {security_key} expected={expected_shares:.12f} actual={actual_shares:.12f}"
                break
        if not p5_ok:
            break
        actual_cash = to_float(p5_portfolio[rebalance["trade_date"]]["cash_end"])
        expected_cash = to_float(rebalance["cash_after_rebalance"])
        if abs(actual_cash - expected_cash) > 1e-10:
            p5_ok = False
            p5_detail = f"{rebalance_id} cash expected={expected_cash:.12f} actual={actual_cash:.12f}"
            break
    add_check(checks, "p5_order_replay_matches_holdings_and_cash", "pass" if p5_ok else "fail", p5_detail or f"rebalances={len(p5_rebalances)}")

    # NBIM raw loader
    nbim_processed = read_csv(ROOT / "data/processed/nbim/nbim_public_equity_holdings.csv")
    processed_counts = Counter(row["as_of_date"] for row in nbim_processed)
    raw_counts_nbim = {}
    for raw_path in sorted((ROOT / "data" / "raw" / "nbim").glob("eq_*.csv")):
        as_of_date = f"{raw_path.stem[3:7]}-{raw_path.stem[7:9]}-{raw_path.stem[9:11]}"
        raw_rows = load_nbim_raw_rows(raw_path)
        raw_counts_nbim[as_of_date] = sum(1 for row in raw_rows if not is_effectively_empty_nbim_row(row))
    nbim_loader_ok = all(processed_counts[k] == raw_counts_nbim.get(k, -1) for k in processed_counts)
    add_check(
        checks,
        "nbim_raw_snapshot_row_counts_match_processed",
        "pass" if nbim_loader_ok else "fail",
        f"snapshots={len(processed_counts)}",
    )

    # NBIM uniqueness and snapshot summary
    unique_failures = 0
    seen = defaultdict(set)
    for row in nbim_processed:
        entity = "|".join([row["issuer_name"], row["issuer_country"], row["incorporation_country"]])
        if entity in seen[row["as_of_date"]]:
            unique_failures += 1
        seen[row["as_of_date"]].add(entity)
    add_check(checks, "nbim_snapshot_entity_uniqueness", "pass" if unique_failures == 0 else "fail", f"failures={unique_failures}")

    industry_summary = read_csv(ROOT / "data/processed/nbim/nbim_snapshot_industry_summary.csv")
    by_snapshot = defaultdict(float)
    for row in industry_summary:
        by_snapshot[row["as_of_date"]] += to_float(row["portfolio_weight_usd"])
    weight_failures = {k: v for k, v in by_snapshot.items() if abs(v - 1.0) > 5e-6}
    add_check(
        checks,
        "nbim_industry_weights_sum_to_one",
        "pass" if not weight_failures else "fail",
        json.dumps(weight_failures, sort_keys=True),
    )

    # NBIM transitions
    nbim_transitions = read_csv(ROOT / "data/processed/nbim/nbim_transition_events.csv")
    nbim_index = defaultdict(dict)
    for row in nbim_processed:
        entity = "|".join([row["issuer_name"], row["issuer_country"], row["incorporation_country"]])
        nbim_index[row["as_of_date"]][entity] = row
    nbim_failures = 0
    for row in nbim_transitions:
        prev_present = row["entity_key"] in nbim_index[row["prev_as_of_date"]]
        curr_present = row["entity_key"] in nbim_index[row["curr_as_of_date"]]
        expected_transition = "continued_holding" if prev_present and curr_present else ("exit_observed" if prev_present else "entry_observed")
        if row["presence_transition"] != expected_transition:
            nbim_failures += 1
    add_check(
        checks,
        "nbim_transition_presence_invariants",
        "pass" if nbim_failures == 0 else "fail",
        f"rows={len(nbim_transitions)} failures={nbim_failures}",
    )

    # NBIM public date -> first tradable close after release
    nbim_prices = [row["date"] for row in read_csv(ROOT / "data/processed/nbim/nbim_twelvedata_daily_prices.csv") if row["instrument_key"] == "benchmark_vt" and row["adjust_mode"] == "all"]
    public_date_map = {row["as_of_date"]: row["public_date"] for row in read_csv(ROOT / "data/processed/nbim/nbim_public_date_map.csv")}
    n6_rebalances = read_csv(ROOT / "data/processed/nbim/backtests/n6_top3_industry_leaders/n6t3l_rebalance_events.csv")
    nbim_trade_ok = True
    nbim_trade_detail = ""
    for row in n6_rebalances:
        public_date = public_date_map[row["as_of_date"]]
        expected_trade = next(d for d in nbim_prices if d > public_date)
        if row["trade_date"] != expected_trade:
            nbim_trade_ok = False
            nbim_trade_detail = f"{row['as_of_date']} expected={expected_trade} actual={row['trade_date']}"
            break
    add_check(checks, "nbim_rebalances_use_first_post_release_trading_day", "pass" if nbim_trade_ok else "fail", nbim_trade_detail or f"rebalances={len(n6_rebalances)}")

    nbim_price_rows = read_csv(ROOT / "data/processed/nbim/nbim_twelvedata_daily_prices.csv")
    nbim_adj_prices = {
        (row["instrument_key"], row["date"]): to_float(row["close"])
        for row in nbim_price_rows if row["adjust_mode"] == "all"
    }
    nbim_order_paths = [
        ROOT / "data/processed/nbim/backtests/n1_core_equal_weight/n1cew_orders.csv",
        ROOT / "data/processed/nbim/backtests/n2_core_nbim_weight/n2cnw_orders.csv",
        ROOT / "data/processed/nbim/backtests/n3_industry_weight_mirror/n3iwm_orders.csv",
        ROOT / "data/processed/nbim/backtests/n4_industry_weight_change_tilt/n4iwc_orders.csv",
        ROOT / "data/processed/nbim/backtests/n5_industry_accumulation_tilt/n5iat_orders.csv",
        ROOT / "data/processed/nbim/backtests/n6_top3_industry_leaders/n6t3l_orders.csv",
        ROOT / "data/processed/nbim/backtests/n7_top3_industry_increases/n7t3i_orders.csv",
        ROOT / "data/processed/nbim/backtests/n8_consensus_rotation_tilt/n8crt_orders.csv",
    ]
    nbim_price_ok = True
    nbim_price_detail = ""
    checked_rows = 0
    for path in nbim_order_paths:
        for row in read_csv(path):
            checked_rows += 1
            key = (row["instrument_key"], row["trade_date"])
            expected = nbim_adj_prices.get(key)
            actual = to_float(row["price"])
            if expected is None or abs(actual - expected) > 1e-8:
                nbim_price_ok = False
                nbim_price_detail = f"{path.name} {key} expected={expected} actual={actual}"
                break
        if not nbim_price_ok:
            break
    add_check(checks, "nbim_order_prices_match_price_layer", "pass" if nbim_price_ok else "fail", nbim_price_detail or f"orders={checked_rows}")

    # NBIM N1/N2/N3/N4 strategy construction
    n1_elig = read_csv(ROOT / "data/processed/nbim/backtests/n1_core_equal_weight/n1cew_signal_eligibility.csv")
    n1_hold = read_csv(ROOT / "data/processed/nbim/backtests/n1_core_equal_weight/n1cew_holdings_timeline.csv")
    n1_ok = True
    by_date = defaultdict(list)
    for row in n1_elig:
        if row["include_flag"] == "1":
            by_date[row["trade_date"]].append(row)
    hold_by_date = defaultdict(list)
    for row in n1_hold:
        hold_by_date[row["date"]].append(row)
    for trade_date, rows in by_date.items():
        expected = 1.0 / len(rows)
        actual_rows = hold_by_date[trade_date]
        for row in actual_rows:
            if abs(to_float(row["portfolio_weight"]) - expected) > 1e-10:
                n1_ok = False
                n1_detail = f"{trade_date} expected={expected:.12f} actual={row['portfolio_weight']}"
                break
        if not n1_ok:
            break
    add_check(checks, "n1_equal_weight_rebalances", "pass" if n1_ok else "fail", n1_detail if not n1_ok else f"rebalances={len(by_date)}")

    n2_elig = read_csv(ROOT / "data/processed/nbim/backtests/n2_core_nbim_weight/n2cnw_signal_eligibility.csv")
    n2_ok = True
    n2_detail = ""
    by_date = defaultdict(list)
    for row in n2_elig:
        if row["include_flag"] == "1":
            by_date[row["trade_date"]].append(row)
    for trade_date, rows in by_date.items():
        total = sum(to_float(row["signal_value"]) for row in rows)
        for row in rows:
            expected = to_float(row["signal_value"]) / total if total else 0.0
            if abs(expected - to_float(row["target_weight"])) > 1e-10:
                n2_ok = False
                n2_detail = f"{trade_date} {row['symbol']} expected={expected:.12f} actual={row['target_weight']}"
                break
        if not n2_ok:
            break
    add_check(checks, "n2_nbim_weight_targets", "pass" if n2_ok else "fail", n2_detail or f"rebalances={len(by_date)}")

    n3_elig = read_csv(ROOT / "data/processed/nbim/backtests/n3_industry_weight_mirror/n3iwm_signal_eligibility.csv")
    industry_map_rows = read_csv(ROOT / "data/processed/nbim/nbim_industry_etf_map.csv")
    industry_map = {row["nbim_industry"]: row["etf_symbol"] for row in industry_map_rows}
    snapshot_rows_by_date = defaultdict(list)
    for row in industry_summary:
        mapped_symbol = industry_map.get(row["industry"])
        if mapped_symbol is None:
            continue
        snapshot_rows_by_date[row["as_of_date"]].append(
            {
                "instrument_key": f"sector::{mapped_symbol}",
                "portfolio_weight_usd": row["portfolio_weight_usd"],
            }
        )
    n3_ok = True
    n3_detail = ""
    for row in n3_elig:
        expected_map = defaultdict(float)
        raw_expected = aggregate_weights(snapshot_rows_by_date[row["as_of_date"]], "portfolio_weight_usd", "instrument_key")
        expected = raw_expected[row["instrument_key"]]
        if abs(expected - to_float(row["target_weight"])) > 1e-10:
            n3_ok = False
            n3_detail = f"{row['as_of_date']} {row['instrument_key']} expected={expected:.12f} actual={row['target_weight']}"
            break
    add_check(checks, "n3_industry_weight_targets_match_snapshot_summary", "pass" if n3_ok else "fail", n3_detail or f"rows={len(n3_elig)}")

    n4_elig = read_csv(ROOT / "data/processed/nbim/backtests/n4_industry_weight_change_tilt/n4iwc_signal_eligibility.csv")
    n4_ok = True
    n4_detail = ""
    by_trade = defaultdict(list)
    for row in n4_elig:
        by_trade[row["trade_date"]].append(row)
    for trade_date, rows in by_trade.items():
        for row in rows:
            delta = to_float(row["signal_value"])
            if delta <= 0:
                n4_ok = False
                n4_detail = f"{trade_date} {row['display_name']} included with non-positive signal_value {delta:.12f}"
                break
        if not n4_ok:
            break
        total_positive = sum(to_float(row["signal_value"]) for row in rows)
        for row in rows:
            expected = to_float(row["signal_value"]) / total_positive if total_positive else 0.0
            if abs(expected - to_float(row["target_weight"])) > 1e-10:
                n4_ok = False
                n4_detail = f"{trade_date} {row['instrument_key']} expected={expected:.12f} actual={row['target_weight']}"
                break
        if not n4_ok:
            break
    add_check(checks, "n4_positive_delta_filter_and_weighting", "pass" if n4_ok else "fail", n4_detail or f"rebalances={len(by_trade)}")

    n5_elig = read_csv(ROOT / "data/processed/nbim/backtests/n5_industry_accumulation_tilt/n5iat_signal_eligibility.csv")
    n5_ok = True
    n5_detail = ""
    by_trade = defaultdict(list)
    for row in n5_elig:
        by_trade[row["trade_date"]].append(row)
    for trade_date, rows in by_trade.items():
        for row in rows:
            score = to_float(row["signal_value"])
            if score <= 0:
                n5_ok = False
                n5_detail = f"{trade_date} {row['display_name']} included with non-positive score {score:.12f}"
                break
        if not n5_ok:
            break
        total_score = sum(to_float(row["signal_value"]) for row in rows)
        for row in rows:
            expected = to_float(row["signal_value"]) / total_score if total_score else 0.0
            if abs(expected - to_float(row["target_weight"])) > 1e-10:
                n5_ok = False
                n5_detail = f"{trade_date} {row['instrument_key']} expected={expected:.12f} actual={row['target_weight']}"
                break
        if not n5_ok:
            break
    add_check(checks, "n5_positive_transition_score_filter_and_weighting", "pass" if n5_ok else "fail", n5_detail or f"rebalances={len(by_trade)}")

    n6_elig = read_csv(ROOT / "data/processed/nbim/backtests/n6_top3_industry_leaders/n6t3l_signal_eligibility.csv")
    n6_ok = True
    n6_detail = ""
    by_trade = defaultdict(list)
    for row in n6_elig:
        by_trade[row["trade_date"]].append(row)
    for trade_date, rows in by_trade.items():
        as_of_date = rows[0]["as_of_date"]
        weights = aggregate_weights(snapshot_rows_by_date[as_of_date], "portfolio_weight_usd", "instrument_key")
        expected_top3 = {
            instrument_key
            for instrument_key, _ in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:3]
        }
        actual_keys = {row["instrument_key"] for row in rows}
        if actual_keys != expected_top3:
            n6_ok = False
            n6_detail = f"{trade_date} expected={sorted(expected_top3)} actual={sorted(actual_keys)}"
            break
        expected_weight = 1.0 / len(rows) if rows else 0.0
        for row in rows:
            if abs(expected_weight - to_float(row["target_weight"])) > 1e-10:
                n6_ok = False
                n6_detail = f"{trade_date} {row['instrument_key']} expected={expected_weight:.12f} actual={row['target_weight']}"
                break
        if not n6_ok:
            break
    add_check(checks, "n6_top3_industry_leaders_match_snapshot", "pass" if n6_ok else "fail", n6_detail or f"rebalances={len(by_trade)}")

    # Build positive-delta and positive-transition aggregates once for N7/N8.
    snapshot_order = sorted(snapshot_rows_by_date)
    snapshot_raw_by_date = defaultdict(list)
    for row in industry_summary:
        snapshot_raw_by_date[row["as_of_date"]].append(row)

    n7_elig = read_csv(ROOT / "data/processed/nbim/backtests/n7_top3_industry_increases/n7t3i_signal_eligibility.csv")
    n7_ok = True
    n7_detail = ""
    by_trade = defaultdict(list)
    for row in n7_elig:
        by_trade[row["trade_date"]].append(row)
    for trade_date, rows in by_trade.items():
        as_of_date = rows[0]["as_of_date"]
        idx = snapshot_order.index(as_of_date)
        if idx == 0:
            continue
        prev_as_of_date = snapshot_order[idx - 1]
        prev_weights = {row["industry"]: to_float(row["portfolio_weight_usd"]) for row in snapshot_raw_by_date[prev_as_of_date]}
        deltas = defaultdict(float)
        for row in snapshot_raw_by_date[as_of_date]:
            mapped_symbol = industry_map.get(row["industry"])
            if mapped_symbol is None:
                continue
            delta = to_float(row["portfolio_weight_usd"]) - prev_weights.get(row["industry"], 0.0)
            if delta > 0:
                deltas[f"sector::{mapped_symbol}"] += delta
        expected_top3 = {key for key, _ in sorted(deltas.items(), key=lambda item: item[1], reverse=True)[:3]}
        actual_keys = {row["instrument_key"] for row in rows}
        if actual_keys != expected_top3:
            n7_ok = False
            n7_detail = f"{trade_date} expected={sorted(expected_top3)} actual={sorted(actual_keys)}"
            break
        expected_weight = 1.0 / len(rows) if rows else 0.0
        for row in rows:
            if abs(expected_weight - to_float(row["target_weight"])) > 1e-10:
                n7_ok = False
                n7_detail = f"{trade_date} {row['instrument_key']} expected={expected_weight:.12f} actual={row['target_weight']}"
                break
        if not n7_ok:
            break
    add_check(checks, "n7_top3_positive_delta_match_snapshot", "pass" if n7_ok else "fail", n7_detail or f"rebalances={len(by_trade)}")

    n8_elig = read_csv(ROOT / "data/processed/nbim/backtests/n8_consensus_rotation_tilt/n8crt_signal_eligibility.csv")
    n8_ok = True
    n8_detail = ""
    transition_summary = read_csv(ROOT / "data/processed/nbim/nbim_transition_industry_summary.csv")
    transition_by_snapshot = defaultdict(list)
    for row in transition_summary:
        transition_by_snapshot[row["curr_as_of_date"]].append(row)
    by_trade = defaultdict(list)
    for row in n8_elig:
        by_trade[row["trade_date"]].append(row)
    for trade_date, rows in by_trade.items():
        as_of_date = rows[0]["as_of_date"]
        idx = snapshot_order.index(as_of_date)
        if idx == 0:
            continue
        prev_as_of_date = snapshot_order[idx - 1]
        prev_weights = {row["industry"]: to_float(row["portfolio_weight_usd"]) for row in snapshot_raw_by_date[prev_as_of_date]}
        delta_by_instrument = defaultdict(float)
        for row in snapshot_raw_by_date[as_of_date]:
            mapped_symbol = industry_map.get(row["industry"])
            if mapped_symbol is None:
                continue
            delta = to_float(row["portfolio_weight_usd"]) - prev_weights.get(row["industry"], 0.0)
            if delta > 0:
                delta_by_instrument[f"sector::{mapped_symbol}"] += delta
        transition_score_by_instrument = defaultdict(float)
        for row in transition_by_snapshot[as_of_date]:
            mapped_symbol = industry_map.get(row["industry"])
            if mapped_symbol is None:
                continue
            score = to_float(row["likely_accumulation"]) - to_float(row["likely_reduction"])
            if score > 0:
                transition_score_by_instrument[f"sector::{mapped_symbol}"] += score
        consensus = []
        for instrument_key, delta in delta_by_instrument.items():
            trans_score = transition_score_by_instrument.get(instrument_key, 0.0)
            if delta > 0 and trans_score > 0:
                consensus.append((instrument_key, delta * trans_score))
        consensus.sort(key=lambda item: item[1], reverse=True)
        consensus = consensus[:3]
        expected_scores = {key: score for key, score in consensus}
        total_score = sum(expected_scores.values())
        actual_keys = {row["instrument_key"] for row in rows}
        if actual_keys != set(expected_scores):
            n8_ok = False
            n8_detail = f"{trade_date} expected={sorted(expected_scores)} actual={sorted(actual_keys)}"
            break
        for row in rows:
            expected_weight = expected_scores[row["instrument_key"]] / total_score if total_score else 0.0
            if abs(expected_weight - to_float(row["target_weight"])) > 1e-10:
                n8_ok = False
                n8_detail = f"{trade_date} {row['instrument_key']} expected={expected_weight:.12f} actual={row['target_weight']}"
                break
        if not n8_ok:
            break
    add_check(checks, "n8_consensus_rotation_scores_match_snapshot", "pass" if n8_ok else "fail", n8_detail or f"rebalances={len(by_trade)}")

    write_csv(DETAIL_PATH, checks)
    summary = {
        "check_count": len(checks),
        "pass_count": sum(1 for row in checks if row["status"] == "pass"),
        "fail_count": sum(1 for row in checks if row["status"] == "fail"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
