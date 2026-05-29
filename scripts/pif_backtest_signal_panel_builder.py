from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOLDINGS_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv"
TRANSITIONS_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_transition_events.csv"
FILING_INDEX_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_filing_index.csv"
OUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_panel.csv"
AUDIT_PATH = ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_audit.csv"


SIGNAL_COLUMNS = [
    "fund",
    "signal_id",
    "signal_source",
    "signal_type",
    "strategy_ids",
    "recommended_action",
    "signal_date",
    "report_period",
    "next_public_date",
    "staleness_days",
    "public_batch_size",
    "same_day_multi_period_flag",
    "security_key",
    "issuer_name",
    "cusip",
    "title_of_class",
    "put_call",
    "share_type",
    "is_option_row",
    "common_equity_baseline_flag",
    "market_value_usd",
    "portfolio_weight_in_filing",
    "prev_shares",
    "curr_shares",
    "delta_shares",
    "prev_market_value_usd",
    "curr_market_value_usd",
    "delta_market_value_usd",
    "accession_number",
    "source_row_id",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def parse_float(value: str) -> float:
    if value.strip() == "":
        return 0.0
    return float(value)


def staleness_days(report_period: str, signal_date: str) -> int:
    return (parse_date(signal_date) - parse_date(report_period)).days


def common_equity_baseline_flag(row: dict[str, str]) -> str:
    is_common = row.get("put_call", "").strip() == "" and row.get("share_type", "").strip() == "SH"
    return "1" if is_common else "0"


def is_option_row(row: dict[str, str]) -> str:
    return "1" if row.get("put_call", "").strip() else "0"


def build_period_metadata(filing_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    kept = [row for row in filing_rows if row["keep_flag"] == "1"]
    kept.sort(key=lambda row: (row["filing_date"], row["period_of_report"]))
    public_batch_sizes = Counter(row["filing_date"] for row in kept)

    next_public_by_period: dict[str, str] = {}
    for i, row in enumerate(kept):
        later_dates = [candidate["filing_date"] for candidate in kept[i + 1 :] if candidate["filing_date"] > row["filing_date"]]
        next_public_by_period[row["period_of_report"]] = later_dates[0] if later_dates else ""

    metadata: dict[str, dict[str, str]] = {}
    for row in kept:
        report_period = row["period_of_report"]
        metadata[report_period] = {
            "signal_date": row["filing_date"],
            "next_public_date": next_public_by_period[report_period],
            "public_batch_size": str(public_batch_sizes[row["filing_date"]]),
            "same_day_multi_period_flag": "1" if public_batch_sizes[row["filing_date"]] > 1 else "0",
            "accession_number": row["accession_number"],
        }
    return metadata


def build_holdings_panel(
    holdings_rows: list[dict[str, str]],
    period_meta: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    totals_by_period: dict[str, float] = defaultdict(float)
    for row in holdings_rows:
        totals_by_period[row["as_of_date"]] += parse_float(row["market_value_usd"])

    out: list[dict[str, str]] = []
    for row in holdings_rows:
        meta = period_meta[row["as_of_date"]]
        total_value = totals_by_period[row["as_of_date"]]
        weight = parse_float(row["market_value_usd"]) / total_value if total_value else 0.0

        out.append(
            {
                "fund": "PIF",
                "signal_id": f"holding:{row['source_row_id']}",
                "signal_source": "holdings",
                "signal_type": "full_sleeve_holding",
                "strategy_ids": "P2",
                "recommended_action": "hold_or_buy",
                "signal_date": meta["signal_date"],
                "report_period": row["as_of_date"],
                "next_public_date": meta["next_public_date"],
                "staleness_days": str(staleness_days(row["as_of_date"], meta["signal_date"])),
                "public_batch_size": meta["public_batch_size"],
                "same_day_multi_period_flag": meta["same_day_multi_period_flag"],
                "security_key": row["security_key"] if "security_key" in row else "|".join(
                    [row["cusip"], row["title_of_class"], row["put_call"], row["share_type"], row["issuer_name"]]
                ),
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "title_of_class": row["title_of_class"],
                "put_call": row["put_call"],
                "share_type": row["share_type"],
                "is_option_row": is_option_row(row),
                "common_equity_baseline_flag": common_equity_baseline_flag(row),
                "market_value_usd": row["market_value_usd"],
                "portfolio_weight_in_filing": f"{weight:.8f}",
                "prev_shares": "",
                "curr_shares": row["shares"],
                "delta_shares": "",
                "prev_market_value_usd": "",
                "curr_market_value_usd": row["market_value_usd"],
                "delta_market_value_usd": "",
                "accession_number": row["accession_number"],
                "source_row_id": row["source_row_id"],
            }
        )
    return out


def strategy_ids_for_transition(signal_type: str) -> str:
    mapping = {
        "entry_observed": "P1",
        "exit_observed": "P4",
        "likely_accumulation": "P3",
        "likely_reduction": "P3,P4",
        "continued_holding": "diagnostic",
    }
    return mapping.get(signal_type, "diagnostic")


def recommended_action_for_transition(signal_type: str) -> str:
    mapping = {
        "entry_observed": "buy_new",
        "exit_observed": "remove",
        "likely_accumulation": "overweight",
        "likely_reduction": "underweight_or_exclude",
        "continued_holding": "hold",
    }
    return mapping.get(signal_type, "observe")


def build_transition_panel(
    transition_rows: list[dict[str, str]],
    period_meta: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in transition_rows:
        report_period = row["curr_as_of_date"]
        meta = period_meta[report_period]
        out.append(
            {
                "fund": "PIF",
                "signal_id": f"transition:{row['curr_source_row_id'] or row['prev_source_row_id']}",
                "signal_source": "transition",
                "signal_type": row["primary_event_type"],
                "strategy_ids": strategy_ids_for_transition(row["primary_event_type"]),
                "recommended_action": recommended_action_for_transition(row["primary_event_type"]),
                "signal_date": meta["signal_date"],
                "report_period": report_period,
                "next_public_date": meta["next_public_date"],
                "staleness_days": str(staleness_days(report_period, meta["signal_date"])),
                "public_batch_size": meta["public_batch_size"],
                "same_day_multi_period_flag": meta["same_day_multi_period_flag"],
                "security_key": row["security_key"],
                "issuer_name": row["issuer_name"],
                "cusip": row["cusip"],
                "title_of_class": row["title_of_class"],
                "put_call": row["put_call"],
                "share_type": row["share_type"],
                "is_option_row": "1" if row["put_call"].strip() else "0",
                "common_equity_baseline_flag": "1" if row["put_call"].strip() == "" and row["share_type"].strip() == "SH" else "0",
                "market_value_usd": row["curr_market_value_usd"],
                "portfolio_weight_in_filing": "",
                "prev_shares": row["prev_shares"],
                "curr_shares": row["curr_shares"],
                "delta_shares": row["delta_shares"],
                "prev_market_value_usd": row["prev_market_value_usd"],
                "curr_market_value_usd": row["curr_market_value_usd"],
                "delta_market_value_usd": row["delta_market_value_usd"],
                "accession_number": row["curr_accession_number"] or meta["accession_number"],
                "source_row_id": row["curr_source_row_id"] or row["prev_source_row_id"],
            }
        )
    return out


def build_audit(
    signal_rows: list[dict[str, str]],
    filing_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in signal_rows:
        rows_by_date[row["signal_date"]].append(row)

    periods_by_date: dict[str, list[str]] = defaultdict(list)
    for row in filing_rows:
        if row["keep_flag"] == "1":
            periods_by_date[row["filing_date"]].append(row["period_of_report"])

    out: list[dict[str, str]] = []
    for signal_date in sorted(rows_by_date):
        rows = rows_by_date[signal_date]
        staleness_values = [int(row["staleness_days"]) for row in rows]
        transition_counts = Counter(row["signal_type"] for row in rows if row["signal_source"] == "transition")
        out.append(
            {
                "signal_date": signal_date,
                "report_period_count_published": str(len(periods_by_date[signal_date])),
                "published_report_periods": "|".join(sorted(periods_by_date[signal_date])),
                "signal_row_count": str(len(rows)),
                "holdings_row_count": str(sum(1 for row in rows if row["signal_source"] == "holdings")),
                "transition_row_count": str(sum(1 for row in rows if row["signal_source"] == "transition")),
                "entry_observed_count": str(transition_counts.get("entry_observed", 0)),
                "exit_observed_count": str(transition_counts.get("exit_observed", 0)),
                "likely_accumulation_count": str(transition_counts.get("likely_accumulation", 0)),
                "likely_reduction_count": str(transition_counts.get("likely_reduction", 0)),
                "same_day_multi_period_flag": "1" if len(periods_by_date[signal_date]) > 1 else "0",
                "min_staleness_days": str(min(staleness_values)),
                "max_staleness_days": str(max(staleness_values)),
            }
        )
    return out


def validate_period_metadata(period_meta: dict[str, dict[str, str]], filing_rows: list[dict[str, str]]) -> None:
    kept_periods = [row["period_of_report"] for row in filing_rows if row["keep_flag"] == "1"]
    if len(kept_periods) != len(set(kept_periods)):
        raise ValueError("Canonical filing index should have only one kept row per report period")
    missing = [period for period in kept_periods if period not in period_meta]
    if missing:
        raise ValueError(f"Missing period metadata for: {missing}")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    holdings_rows = read_csv(HOLDINGS_PATH)
    transition_rows = read_csv(TRANSITIONS_PATH)
    filing_rows = read_csv(FILING_INDEX_PATH)

    period_meta = build_period_metadata(filing_rows)
    validate_period_metadata(period_meta, filing_rows)

    signal_rows = build_holdings_panel(holdings_rows, period_meta)
    signal_rows.extend(build_transition_panel(transition_rows, period_meta))
    signal_rows.sort(key=lambda row: (row["signal_date"], row["report_period"], row["signal_source"], row["signal_type"], row["issuer_name"], row["security_key"]))

    audit_rows = build_audit(signal_rows, filing_rows)

    write_csv(OUT_PATH, signal_rows)
    write_csv(AUDIT_PATH, audit_rows)

    print(f"Wrote {len(signal_rows)} signal rows to {OUT_PATH}")
    print(f"Wrote {len(audit_rows)} audit rows to {AUDIT_PATH}")


if __name__ == "__main__":
    main()
