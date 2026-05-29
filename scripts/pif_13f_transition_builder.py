from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_transition_events.csv"

SHARE_TOLERANCE = 1.0
VALUE_TOLERANCE = 1.0


@dataclass(frozen=True)
class Holding:
    fund: str
    issuer_name: str
    cusip: str
    title_of_class: str
    put_call: str
    share_type: str
    as_of_date: str
    public_date: str
    filing_date: str
    shares: float | None
    market_value_usd: float | None
    source_row_id: str
    accession_number: str

    @property
    def security_key(self) -> str:
        return "|".join(
            [
                self.cusip,
                self.title_of_class,
                self.put_call,
                self.share_type,
                self.issuer_name,
            ]
        )


OUTPUT_COLUMNS = [
    "fund",
    "security_key",
    "issuer_name",
    "cusip",
    "title_of_class",
    "put_call",
    "share_type",
    "prev_as_of_date",
    "curr_as_of_date",
    "prev_public_date",
    "curr_public_date",
    "period_days",
    "was_present",
    "is_present",
    "presence_transition",
    "primary_event_type",
    "share_signal",
    "value_signal",
    "prev_shares",
    "curr_shares",
    "delta_shares",
    "pct_change_shares",
    "prev_market_value_usd",
    "curr_market_value_usd",
    "delta_market_value_usd",
    "pct_change_market_value_usd",
    "prev_accession_number",
    "curr_accession_number",
    "prev_source_row_id",
    "curr_source_row_id",
    "classification_note",
]


def parse_float(value: str) -> float | None:
    text = value.strip()
    if text == "":
        return None
    return float(text)


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def load_holdings() -> list[Holding]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Processed holdings file not found: {INPUT_PATH}")

    holdings: list[Holding] = []
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as infile:
        for row in csv.DictReader(infile):
            holdings.append(
                Holding(
                    fund=row["fund"],
                    issuer_name=row["issuer_name"],
                    cusip=row["cusip"],
                    title_of_class=row["title_of_class"],
                    put_call=row["put_call"],
                    share_type=row["share_type"],
                    as_of_date=row["as_of_date"],
                    public_date=row["public_date"],
                    filing_date=row["filing_date"],
                    shares=parse_float(row["shares"]),
                    market_value_usd=parse_float(row["market_value_usd"]),
                    source_row_id=row["source_row_id"],
                    accession_number=row["accession_number"],
                )
            )
    return holdings


def unique_sorted_dates(holdings: list[Holding]) -> list[str]:
    return sorted({holding.as_of_date for holding in holdings})


def build_snapshot_index(holdings: list[Holding]) -> dict[str, dict[str, Holding]]:
    index: dict[str, dict[str, Holding]] = {}
    for holding in holdings:
        snapshot = index.setdefault(holding.as_of_date, {})
        if holding.security_key in snapshot:
            raise ValueError(
                f"Duplicate security key within snapshot {holding.as_of_date}: {holding.security_key}"
            )
        snapshot[holding.security_key] = holding
    return index


def compare_metric(
    curr: float | None,
    prev: float | None,
    *,
    up_label: str,
    down_label: str,
    flat_label: str,
    tolerance: float,
) -> str:
    if curr is None or prev is None:
        return "unknown"
    delta = curr - prev
    if delta > tolerance:
        return up_label
    if delta < -tolerance:
        return down_label
    return flat_label


def compare_metric_zero_missing(
    curr: float | None,
    prev: float | None,
    *,
    up_label: str,
    down_label: str,
    flat_label: str,
    tolerance: float,
) -> str:
    curr_value = 0.0 if curr is None else curr
    prev_value = 0.0 if prev is None else prev
    delta = curr_value - prev_value
    if delta > tolerance:
        return up_label
    if delta < -tolerance:
        return down_label
    return flat_label


def diff(curr: float | None, prev: float | None) -> float | None:
    curr_value = 0.0 if curr is None else curr
    prev_value = 0.0 if prev is None else prev
    return curr_value - prev_value


def percent_change(curr: float | None, prev: float | None) -> float | None:
    curr_value = 0.0 if curr is None else curr
    prev_value = 0.0 if prev is None else prev
    if prev_value == 0:
        return None
    return ((curr_value - prev_value) / prev_value) * 100.0


def primary_event_type(presence_transition: str, share_signal: str) -> str:
    if presence_transition != "continued_holding":
        return presence_transition
    if share_signal == "shares_up":
        return "likely_accumulation"
    if share_signal == "shares_down":
        return "likely_reduction"
    return "continued_holding"


def classification_note(presence_transition: str, share_signal: str, value_signal: str) -> str:
    if presence_transition == "entry_observed":
        return "Security appears in the current 13F period but not in the previous one."
    if presence_transition == "exit_observed":
        return "Security appears in the previous 13F period but not in the current one."
    if share_signal == "shares_up":
        return "Security appears in both periods and share count increased."
    if share_signal == "shares_down":
        return "Security appears in both periods and share count decreased."
    if value_signal in {"value_up", "value_down"}:
        return "Security appears in both periods with flat share count but changed market value."
    return "Security appears in both periods with no material share-count or value change."


def format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def build_transition_row(
    *,
    prev_date: str,
    curr_date: str,
    prev_holding: Holding | None,
    curr_holding: Holding | None,
) -> dict[str, str]:
    exemplar = curr_holding or prev_holding
    assert exemplar is not None

    was_present = prev_holding is not None
    is_present = curr_holding is not None

    if was_present and is_present:
        presence_transition = "continued_holding"
    elif was_present:
        presence_transition = "exit_observed"
    else:
        presence_transition = "entry_observed"

    share_signal = compare_metric(
        curr_holding.shares if curr_holding else None,
        prev_holding.shares if prev_holding else None,
        up_label="shares_up",
        down_label="shares_down",
        flat_label="shares_flat",
        tolerance=SHARE_TOLERANCE,
    )
    if presence_transition == "entry_observed":
        share_signal = "shares_up"
    elif presence_transition == "exit_observed":
        share_signal = "shares_down"

    value_signal = compare_metric_zero_missing(
        curr_holding.market_value_usd if curr_holding else None,
        prev_holding.market_value_usd if prev_holding else None,
        up_label="value_up",
        down_label="value_down",
        flat_label="value_flat",
        tolerance=VALUE_TOLERANCE,
    )
    event_type = primary_event_type(presence_transition, share_signal)

    row = {column: "" for column in OUTPUT_COLUMNS}
    row["fund"] = exemplar.fund
    row["security_key"] = exemplar.security_key
    row["issuer_name"] = exemplar.issuer_name
    row["cusip"] = exemplar.cusip
    row["title_of_class"] = exemplar.title_of_class
    row["put_call"] = exemplar.put_call
    row["share_type"] = exemplar.share_type
    row["prev_as_of_date"] = prev_date
    row["curr_as_of_date"] = curr_date
    row["prev_public_date"] = prev_holding.public_date if prev_holding else ""
    row["curr_public_date"] = curr_holding.public_date if curr_holding else ""
    row["period_days"] = str((parse_date(curr_date) - parse_date(prev_date)).days)
    row["was_present"] = "1" if was_present else "0"
    row["is_present"] = "1" if is_present else "0"
    row["presence_transition"] = presence_transition
    row["primary_event_type"] = event_type
    row["share_signal"] = share_signal
    row["value_signal"] = value_signal
    row["prev_shares"] = (
        "0" if prev_holding is None or prev_holding.shares is None else f"{prev_holding.shares:.0f}"
    )
    row["curr_shares"] = (
        "0" if curr_holding is None or curr_holding.shares is None else f"{curr_holding.shares:.0f}"
    )
    row["delta_shares"] = format_optional_float(
        diff(curr_holding.shares if curr_holding else None, prev_holding.shares if prev_holding else None)
    )
    row["pct_change_shares"] = format_optional_float(
        percent_change(curr_holding.shares if curr_holding else None, prev_holding.shares if prev_holding else None)
    )
    row["prev_market_value_usd"] = (
        "0"
        if prev_holding is None or prev_holding.market_value_usd is None
        else f"{prev_holding.market_value_usd:.0f}"
    )
    row["curr_market_value_usd"] = (
        "0"
        if curr_holding is None or curr_holding.market_value_usd is None
        else f"{curr_holding.market_value_usd:.0f}"
    )
    row["delta_market_value_usd"] = format_optional_float(
        diff(curr_holding.market_value_usd if curr_holding else None, prev_holding.market_value_usd if prev_holding else None)
    )
    row["pct_change_market_value_usd"] = format_optional_float(
        percent_change(curr_holding.market_value_usd if curr_holding else None, prev_holding.market_value_usd if prev_holding else None)
    )
    row["prev_accession_number"] = prev_holding.accession_number if prev_holding else ""
    row["curr_accession_number"] = curr_holding.accession_number if curr_holding else ""
    row["prev_source_row_id"] = prev_holding.source_row_id if prev_holding else ""
    row["curr_source_row_id"] = curr_holding.source_row_id if curr_holding else ""
    row["classification_note"] = classification_note(presence_transition, share_signal, value_signal)
    return row


def build_transitions(holdings: list[Holding]) -> list[dict[str, str]]:
    dates = unique_sorted_dates(holdings)
    if len(dates) < 2:
        raise ValueError("Need at least two reporting periods to build transitions")
    snapshot_index = build_snapshot_index(holdings)
    rows: list[dict[str, str]] = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        prev_snapshot = snapshot_index[prev_date]
        curr_snapshot = snapshot_index[curr_date]
        for security_key in sorted(set(prev_snapshot) | set(curr_snapshot)):
            rows.append(
                build_transition_row(
                    prev_date=prev_date,
                    curr_date=curr_date,
                    prev_holding=prev_snapshot.get(security_key),
                    curr_holding=curr_snapshot.get(security_key),
                )
            )
    return rows


def write_rows(rows: list[dict[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["primary_event_type"]] = counts.get(row["primary_event_type"], 0) + 1
    print(f"Wrote {len(rows)} transition rows to {OUTPUT_PATH}")
    print("primary event counts:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")


def main() -> None:
    holdings = load_holdings()
    rows = build_transitions(holdings)
    write_rows(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
