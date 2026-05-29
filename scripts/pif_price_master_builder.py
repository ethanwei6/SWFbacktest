from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNAL_PANEL_PATH = ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_panel.csv"
TRADE_CALENDAR_PATH = ROOT / "data" / "processed" / "pif" / "pif_trade_calendar.csv"
OUT_MASTER_PATH = ROOT / "data" / "processed" / "pif" / "pif_price_security_master.csv"
OUT_REQUEST_PATH = ROOT / "data" / "processed" / "pif" / "pif_price_request_template.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def parse_date(text: str) -> date:
    year, month, day = text.split("-")
    return date(int(year), int(month), int(day))


def fmt_date(value: date) -> str:
    return value.isoformat()


def shift_calendar_days(value: date, days: int) -> date:
    from datetime import timedelta

    return value + timedelta(days=days)


def classify_security(title_of_class: str) -> str:
    upper = title_of_class.upper()
    if "W EXP" in upper or upper.startswith("*W") or "WARRANT" in upper:
        return "warrant_like"
    if "ADR" in upper or "ADS" in upper or "SPONSORED" in upper:
        return "adr_or_ads"
    if "CL A" in upper or "CLASS A" in upper:
        return "class_a_common"
    if "CL B" in upper or "CLASS B" in upper:
        return "class_b_common"
    if upper == "COM":
        return "common_stock"
    return "other_common_equity"


def build_security_master(
    signal_rows: list[dict[str, str]],
    calendar_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    trade_date_by_signal_date = {
        row["signal_date"]: row["trade_date"] for row in calendar_rows
    }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in signal_rows:
        if row["common_equity_baseline_flag"] != "1":
            continue
        grouped[row["security_key"]].append(row)

    out: list[dict[str, str]] = []
    for security_key in sorted(grouped):
        rows = sorted(grouped[security_key], key=lambda row: (row["signal_date"], row["signal_id"]))
        first_signal_date = parse_date(rows[0]["signal_date"])
        last_signal_date = parse_date(rows[-1]["signal_date"])
        trade_dates = [
            parse_date(trade_date_by_signal_date[row["signal_date"]])
            for row in rows
            if row["signal_date"] in trade_date_by_signal_date
        ]
        event_counts = Counter(row["signal_type"] for row in rows)
        issuer_name = rows[0]["issuer_name"]
        cusip = rows[0]["cusip"]
        title_of_class = rows[0]["title_of_class"]
        security_kind = classify_security(title_of_class)
        baseline_price_eligible_flag = "0" if security_kind == "warrant_like" else "1"
        eligibility_note = (
            "Exclude from baseline common-equity backtests; title of class appears warrant-like."
            if baseline_price_eligible_flag == "0"
            else ""
        )
        first_report_period = min(row["report_period"] for row in rows if row["report_period"])
        last_report_period = max(row["report_period"] for row in rows if row["report_period"])
        out.append(
            {
                "security_key": security_key,
                "issuer_name": issuer_name,
                "cusip": cusip,
                "title_of_class": title_of_class,
                "share_type": rows[0]["share_type"],
                "security_kind": security_kind,
                "baseline_price_eligible_flag": baseline_price_eligible_flag,
                "eligibility_note": eligibility_note,
                "first_signal_date": fmt_date(first_signal_date),
                "last_signal_date": fmt_date(last_signal_date),
                "first_trade_date": fmt_date(min(trade_dates)),
                "last_trade_date": fmt_date(max(trade_dates)),
                "first_report_period": first_report_period,
                "last_report_period": last_report_period,
                "signal_row_count": str(len(rows)),
                "holding_signal_count": str(event_counts.get("full_sleeve_holding", 0)),
                "continued_holding_count": str(event_counts.get("continued_holding", 0)),
                "entry_observed_count": str(event_counts.get("entry_observed", 0)),
                "exit_observed_count": str(event_counts.get("exit_observed", 0)),
                "likely_accumulation_count": str(event_counts.get("likely_accumulation", 0)),
                "likely_reduction_count": str(event_counts.get("likely_reduction", 0)),
                "price_identifier_type": "CUSIP",
                "price_identifier_value": cusip,
                "bbg_ticker": "",
                "bbg_unique_id": "",
                "mapping_status": "pending_bloomberg_map",
                "mapping_notes": "",
            }
        )
    return out


def build_request_template(master_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in master_rows:
        if row["baseline_price_eligible_flag"] != "1":
            continue
        first_trade_date = parse_date(row["first_trade_date"])
        last_trade_date = parse_date(row["last_trade_date"])
        out.append(
            {
                "security_key": row["security_key"],
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "title_of_class": row["title_of_class"],
                "security_kind": row["security_kind"],
                "price_identifier_type": row["price_identifier_type"],
                "price_identifier_value": row["price_identifier_value"],
                "bbg_ticker": row["bbg_ticker"],
                "bbg_unique_id": row["bbg_unique_id"],
                "request_start_date": fmt_date(shift_calendar_days(first_trade_date, -7)),
                "request_end_date": fmt_date(shift_calendar_days(last_trade_date, 120)),
                "required_fields": "PX_OPEN|PX_LAST|CURRENCY",
                "optional_fields": "TOT_RETURN_INDEX_GROSS_DVDS|TOT_RETURN_INDEX_NET_DVDS|ID_BB_GLOBAL",
                "mapping_status": row["mapping_status"],
                "mapping_notes": row["mapping_notes"],
                "eligibility_note": row["eligibility_note"],
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    signal_rows = read_csv(SIGNAL_PANEL_PATH)
    calendar_rows = read_csv(TRADE_CALENDAR_PATH)
    master_rows = build_security_master(signal_rows, calendar_rows)
    request_rows = build_request_template(master_rows)
    write_csv(OUT_MASTER_PATH, master_rows)
    write_csv(OUT_REQUEST_PATH, request_rows)
    print(f"Wrote {len(master_rows)} rows to {OUT_MASTER_PATH}")
    print(f"Wrote {len(request_rows)} rows to {OUT_REQUEST_PATH}")


if __name__ == "__main__":
    main()
