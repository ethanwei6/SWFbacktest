from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_public_equity_holdings.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_transition_events.csv"

OWNERSHIP_TOLERANCE = 0.01
VOTING_TOLERANCE = 0.01
VALUE_TOLERANCE = 1.0


@dataclass(frozen=True)
class Holding:
    fund: str
    issuer_name: str
    issuer_country: str
    incorporation_country: str
    region: str
    industry: str
    as_of_date: str
    market_value_nok: float | None
    market_value_usd: float | None
    ownership_pct: float | None
    voting_pct: float | None
    source_row_id: str

    @property
    def entity_key(self) -> str:
        return "|".join(
            [
                self.issuer_name,
                self.issuer_country,
                self.incorporation_country,
            ]
        )


OUTPUT_COLUMNS = [
    "fund",
    "entity_key",
    "issuer_name",
    "issuer_country",
    "incorporation_country",
    "prev_as_of_date",
    "curr_as_of_date",
    "period_days",
    "was_present",
    "is_present",
    "presence_transition",
    "primary_event_type",
    "ownership_signal",
    "voting_signal",
    "value_signal",
    "prev_region",
    "curr_region",
    "prev_industry",
    "curr_industry",
    "region_changed",
    "industry_changed",
    "prev_market_value_nok",
    "curr_market_value_nok",
    "delta_market_value_nok",
    "pct_change_market_value_nok",
    "prev_market_value_usd",
    "curr_market_value_usd",
    "delta_market_value_usd",
    "pct_change_market_value_usd",
    "prev_ownership_pct",
    "curr_ownership_pct",
    "delta_ownership_pct",
    "prev_voting_pct",
    "curr_voting_pct",
    "delta_voting_pct",
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
        reader = csv.DictReader(infile)
        for row in reader:
            holdings.append(
                Holding(
                    fund=row["fund"],
                    issuer_name=row["issuer_name"],
                    issuer_country=row["issuer_country"],
                    incorporation_country=row["incorporation_country"],
                    region=row["region"],
                    industry=row["industry"],
                    as_of_date=row["as_of_date"],
                    market_value_nok=parse_float(row["market_value_nok"]),
                    market_value_usd=parse_float(row["market_value_usd"]),
                    ownership_pct=parse_float(row["ownership_pct"]),
                    voting_pct=parse_float(row["voting_pct"]),
                    source_row_id=row["source_row_id"],
                )
            )

    return holdings


def unique_sorted_dates(holdings: Iterable[Holding]) -> list[str]:
    return sorted({holding.as_of_date for holding in holdings})


def percent_change(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return ((curr - prev) / prev) * 100.0


def diff(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None:
        return None
    return curr - prev


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


def primary_event_type(
    presence_transition: str,
    ownership_signal: str,
    voting_signal: str,
) -> str:
    if presence_transition != "continued_holding":
        return presence_transition
    if ownership_signal == "ownership_up":
        return "likely_accumulation"
    if ownership_signal == "ownership_down":
        return "likely_reduction"
    if voting_signal == "voting_up":
        return "voting_up"
    if voting_signal == "voting_down":
        return "voting_down"
    return "continued_holding"


def classification_note(
    *,
    presence_transition: str,
    ownership_signal: str,
    voting_signal: str,
    value_signal: str,
) -> str:
    if presence_transition == "entry_observed":
        return "Issuer appears in the current snapshot but not in the previous snapshot."
    if presence_transition == "exit_observed":
        return "Issuer appears in the previous snapshot but not in the current snapshot."
    if ownership_signal in {"ownership_up", "ownership_down"}:
        return (
            "Issuer appears in both snapshots and ownership percentage changed beyond the tolerance. "
            "This is the best available indicator of likely position change, but denominator effects can also move ownership percentages."
        )
    if voting_signal in {"voting_up", "voting_down"}:
        return "Issuer appears in both snapshots and voting percentage changed beyond the tolerance while ownership remained flat."
    if value_signal in {"value_up", "value_down"}:
        return (
            "Issuer appears in both snapshots and market value changed, but ownership and voting stayed flat. "
            "This does not by itself imply buying or selling."
        )
    return "Issuer appears in both snapshots with no meaningful ownership, voting, or market value change."


def build_snapshot_index(holdings: Iterable[Holding]) -> dict[str, dict[str, Holding]]:
    index: dict[str, dict[str, Holding]] = {}
    for holding in holdings:
        snapshot = index.setdefault(holding.as_of_date, {})
        if holding.entity_key in snapshot:
            raise ValueError(
                f"Duplicate entity key within snapshot {holding.as_of_date}: {holding.entity_key}"
            )
        snapshot[holding.entity_key] = holding
    return index


def build_transition_row(
    *,
    prev_date: str,
    curr_date: str,
    prev_holding: Holding | None,
    curr_holding: Holding | None,
) -> dict[str, str]:
    if prev_holding is None and curr_holding is None:
        raise ValueError("Transition row requires at least one holding")

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

    ownership_signal = compare_metric(
        curr_holding.ownership_pct if curr_holding else None,
        prev_holding.ownership_pct if prev_holding else None,
        up_label="ownership_up",
        down_label="ownership_down",
        flat_label="ownership_flat",
        tolerance=OWNERSHIP_TOLERANCE,
    )
    voting_signal = compare_metric(
        curr_holding.voting_pct if curr_holding else None,
        prev_holding.voting_pct if prev_holding else None,
        up_label="voting_up",
        down_label="voting_down",
        flat_label="voting_flat",
        tolerance=VOTING_TOLERANCE,
    )
    value_signal = compare_metric(
        curr_holding.market_value_usd if curr_holding else None,
        prev_holding.market_value_usd if prev_holding else None,
        up_label="value_up",
        down_label="value_down",
        flat_label="value_flat",
        tolerance=VALUE_TOLERANCE,
    )
    event_type = primary_event_type(
        presence_transition=presence_transition,
        ownership_signal=ownership_signal,
        voting_signal=voting_signal,
    )

    prev_dt = parse_date(prev_date)
    curr_dt = parse_date(curr_date)

    prev_region = prev_holding.region if prev_holding else ""
    curr_region = curr_holding.region if curr_holding else ""
    prev_industry = prev_holding.industry if prev_holding else ""
    curr_industry = curr_holding.industry if curr_holding else ""

    prev_market_value_nok = prev_holding.market_value_nok if prev_holding else None
    curr_market_value_nok = curr_holding.market_value_nok if curr_holding else None
    prev_market_value_usd = prev_holding.market_value_usd if prev_holding else None
    curr_market_value_usd = curr_holding.market_value_usd if curr_holding else None
    prev_ownership_pct = prev_holding.ownership_pct if prev_holding else None
    curr_ownership_pct = curr_holding.ownership_pct if curr_holding else None
    prev_voting_pct = prev_holding.voting_pct if prev_holding else None
    curr_voting_pct = curr_holding.voting_pct if curr_holding else None

    row: dict[str, str] = {column: "" for column in OUTPUT_COLUMNS}
    row["fund"] = exemplar.fund
    row["entity_key"] = exemplar.entity_key
    row["issuer_name"] = exemplar.issuer_name
    row["issuer_country"] = exemplar.issuer_country
    row["incorporation_country"] = exemplar.incorporation_country
    row["prev_as_of_date"] = prev_date
    row["curr_as_of_date"] = curr_date
    row["period_days"] = str((curr_dt - prev_dt).days)
    row["was_present"] = "1" if was_present else "0"
    row["is_present"] = "1" if is_present else "0"
    row["presence_transition"] = presence_transition
    row["primary_event_type"] = event_type
    row["ownership_signal"] = ownership_signal
    row["voting_signal"] = voting_signal
    row["value_signal"] = value_signal
    row["prev_region"] = prev_region
    row["curr_region"] = curr_region
    row["prev_industry"] = prev_industry
    row["curr_industry"] = curr_industry
    row["region_changed"] = "1" if was_present and is_present and prev_region != curr_region else "0"
    row["industry_changed"] = "1" if was_present and is_present and prev_industry != curr_industry else "0"
    row["prev_market_value_nok"] = "" if prev_market_value_nok is None else f"{prev_market_value_nok}"
    row["curr_market_value_nok"] = "" if curr_market_value_nok is None else f"{curr_market_value_nok}"
    row["delta_market_value_nok"] = format_optional_float(diff(curr_market_value_nok, prev_market_value_nok))
    row["pct_change_market_value_nok"] = format_optional_float(
        percent_change(curr_market_value_nok, prev_market_value_nok)
    )
    row["prev_market_value_usd"] = "" if prev_market_value_usd is None else f"{prev_market_value_usd}"
    row["curr_market_value_usd"] = "" if curr_market_value_usd is None else f"{curr_market_value_usd}"
    row["delta_market_value_usd"] = format_optional_float(diff(curr_market_value_usd, prev_market_value_usd))
    row["pct_change_market_value_usd"] = format_optional_float(
        percent_change(curr_market_value_usd, prev_market_value_usd)
    )
    row["prev_ownership_pct"] = "" if prev_ownership_pct is None else f"{prev_ownership_pct}"
    row["curr_ownership_pct"] = "" if curr_ownership_pct is None else f"{curr_ownership_pct}"
    row["delta_ownership_pct"] = format_optional_float(diff(curr_ownership_pct, prev_ownership_pct))
    row["prev_voting_pct"] = "" if prev_voting_pct is None else f"{prev_voting_pct}"
    row["curr_voting_pct"] = "" if curr_voting_pct is None else f"{curr_voting_pct}"
    row["delta_voting_pct"] = format_optional_float(diff(curr_voting_pct, prev_voting_pct))
    row["prev_source_row_id"] = prev_holding.source_row_id if prev_holding else ""
    row["curr_source_row_id"] = curr_holding.source_row_id if curr_holding else ""
    row["classification_note"] = classification_note(
        presence_transition=presence_transition,
        ownership_signal=ownership_signal,
        voting_signal=voting_signal,
        value_signal=value_signal,
    )

    return row


def format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def build_transitions(holdings: list[Holding]) -> list[dict[str, str]]:
    snapshot_index = build_snapshot_index(holdings)
    dates = unique_sorted_dates(holdings)
    if len(dates) < 2:
        raise ValueError("Need at least two snapshots to build transitions")

    transitions: list[dict[str, str]] = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        prev_snapshot = snapshot_index[prev_date]
        curr_snapshot = snapshot_index[curr_date]
        all_keys = sorted(set(prev_snapshot) | set(curr_snapshot))

        for entity_key in all_keys:
            transitions.append(
                build_transition_row(
                    prev_date=prev_date,
                    curr_date=curr_date,
                    prev_holding=prev_snapshot.get(entity_key),
                    curr_holding=curr_snapshot.get(entity_key),
                )
            )

    return transitions


def write_transitions(rows: list[dict[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        key = row["primary_event_type"]
        counts[key] = counts.get(key, 0) + 1

    print(f"Wrote {len(rows)} transition rows to {OUTPUT_PATH}")
    print("primary event counts:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")


def main() -> None:
    holdings = load_holdings()
    rows = build_transitions(holdings)
    write_transitions(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
