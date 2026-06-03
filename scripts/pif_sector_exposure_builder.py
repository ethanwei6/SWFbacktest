from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIF_ROOT = ROOT / "data" / "processed" / "pif"
REFERENCE_ROOT = ROOT / "data" / "reference"

HOLDINGS_PATH = PIF_ROOT / "pif_13f_holdings.csv"
TRANSITIONS_PATH = PIF_ROOT / "pif_13f_transition_events.csv"
TRADE_CALENDAR_PATH = PIF_ROOT / "pif_trade_calendar.csv"
CROSSWALK_PATH = REFERENCE_ROOT / "pif_sector_crosswalk.csv"

ENRICHED_HOLDINGS_PATH = PIF_ROOT / "pif_13f_holdings_sector_enriched.csv"
ENRICHED_TRANSITIONS_PATH = PIF_ROOT / "pif_13f_transition_events_sector_enriched.csv"
EXPOSURE_PATH = PIF_ROOT / "pif_sector_exposure_by_filing.csv"
CHANGE_PATH = PIF_ROOT / "pif_sector_change_by_filing.csv"
AUDIT_PATH = PIF_ROOT / "pif_sector_mapping_audit.csv"


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


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def is_sector_eligible_row(row: dict[str, str]) -> bool:
    if row.get("put_call", "").strip():
        return False
    if row.get("share_type", "").strip() != "SH":
        return False
    warrant_text = " ".join(
        [
            row.get("title_of_class", "").upper(),
            row.get("issuer_name", "").upper(),
            row.get("security_name", "").upper(),
        ]
    )
    if "*W EXP" in warrant_text or "WARRANT" in warrant_text:
        return False
    return True


def build_trade_date_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in read_csv(TRADE_CALENDAR_PATH):
        periods = [value.strip() for value in row["published_report_periods"].split("|") if value.strip()]
        for period in periods:
            mapping[period] = row["trade_date"]
    return mapping


def load_crosswalk() -> dict[str, dict[str, str]]:
    return {row["cusip"]: row for row in read_csv(CROSSWALK_PATH)}


def enrich_holdings(
    holdings_rows: list[dict[str, str]],
    crosswalk: dict[str, dict[str, str]],
    trade_date_by_period: dict[str, str],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in holdings_rows:
        sector_row = crosswalk.get(row["cusip"], {})
        enriched = dict(row)
        enriched["trade_date"] = trade_date_by_period.get(row["as_of_date"], "")
        enriched["sector_eligible_flag"] = "1" if is_sector_eligible_row(row) else "0"
        enriched["pif_sector"] = sector_row.get("pif_sector", "")
        enriched["pif_industry"] = sector_row.get("pif_industry", "")
        enriched["sector_source"] = sector_row.get("sector_source", "")
        enriched["sector_confidence"] = sector_row.get("confidence", "")
        enriched["sector_notes"] = sector_row.get("notes", "")
        enriched["sector_map_status"] = "mapped" if row["cusip"] in crosswalk else "unmapped"
        out.append(enriched)
    return out


def enrich_transitions(
    transition_rows: list[dict[str, str]],
    crosswalk: dict[str, dict[str, str]],
    trade_date_by_period: dict[str, str],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in transition_rows:
        sector_row = crosswalk.get(row["cusip"], {})
        enriched = dict(row)
        enriched["trade_date"] = trade_date_by_period.get(row["curr_as_of_date"], "")
        enriched["sector_eligible_flag"] = "1" if is_sector_eligible_row(row) else "0"
        enriched["pif_sector"] = sector_row.get("pif_sector", "")
        enriched["pif_industry"] = sector_row.get("pif_industry", "")
        enriched["sector_source"] = sector_row.get("sector_source", "")
        enriched["sector_confidence"] = sector_row.get("confidence", "")
        enriched["sector_notes"] = sector_row.get("notes", "")
        enriched["sector_map_status"] = "mapped" if row["cusip"] in crosswalk else "unmapped"
        out.append(enriched)
    return out


def build_exposure_rows(enriched_holdings: list[dict[str, str]]) -> list[dict[str, str]]:
    totals_by_period: dict[str, float] = defaultdict(float)
    grouped: dict[tuple[str, str, str], dict[str, float | str]] = {}

    for row in enriched_holdings:
        if row["sector_eligible_flag"] != "1":
            continue
        period = row["as_of_date"]
        value = to_float(row["market_value_usd"])
        totals_by_period[period] += value
        key = (period, row["pif_sector"], row["pif_industry"])
        bucket = grouped.setdefault(
            key,
            {
                "as_of_date": row["as_of_date"],
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
                "sector": row["pif_sector"],
                "industry": row["pif_industry"],
                "holding_count": 0.0,
                "total_market_value_usd": 0.0,
                "mapped_holding_count": 0.0,
            },
        )
        bucket["holding_count"] += 1.0
        bucket["total_market_value_usd"] += value
        if row["sector_map_status"] == "mapped":
            bucket["mapped_holding_count"] += 1.0

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        row = grouped[key]
        total_period_value = totals_by_period[row["as_of_date"]]
        portfolio_weight = float(row["total_market_value_usd"]) / total_period_value if total_period_value else 0.0
        out.append(
            {
                "as_of_date": str(row["as_of_date"]),
                "public_date": str(row["public_date"]),
                "trade_date": str(row["trade_date"]),
                "sector": str(row["sector"]),
                "industry": str(row["industry"]),
                "holding_count": str(int(row["holding_count"])),
                "mapped_holding_count": str(int(row["mapped_holding_count"])),
                "total_market_value_usd": f"{float(row['total_market_value_usd']):.6f}",
                "portfolio_weight_after": f"{portfolio_weight:.8f}",
            }
        )
    return out


def build_transition_counts(
    enriched_transitions: list[dict[str, str]],
) -> dict[tuple[str, str, str], dict[str, int]]:
    grouped: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {
            "entry_count": 0,
            "exit_count": 0,
            "accumulation_count": 0,
            "reduction_count": 0,
        }
    )
    for row in enriched_transitions:
        if row["sector_eligible_flag"] != "1":
            continue
        key = (row["curr_as_of_date"], row["pif_sector"], row["pif_industry"])
        if row["primary_event_type"] == "entry_observed":
            grouped[key]["entry_count"] += 1
        elif row["primary_event_type"] == "exit_observed":
            grouped[key]["exit_count"] += 1
        elif row["primary_event_type"] == "likely_accumulation":
            grouped[key]["accumulation_count"] += 1
        elif row["primary_event_type"] == "likely_reduction":
            grouped[key]["reduction_count"] += 1
    return grouped


def build_change_rows(
    exposure_rows: list[dict[str, str]],
    enriched_transitions: list[dict[str, str]],
    enriched_holdings: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_period: dict[str, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    period_meta: dict[str, dict[str, str]] = {}
    for row in exposure_rows:
        period = row["as_of_date"]
        by_period[period][(row["sector"], row["industry"])] = row
    for row in enriched_holdings:
        period_meta.setdefault(
            row["as_of_date"],
            {
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
            },
        )
    ordered_periods = sorted(period_meta)

    transition_counts = build_transition_counts(enriched_transitions)
    out: list[dict[str, str]] = []
    for prev_period, curr_period in zip(ordered_periods, ordered_periods[1:]):
        previous = by_period[prev_period]
        current = by_period[curr_period]
        keys = sorted(set(previous) | set(current))
        for sector, industry in keys:
            prev_weight = to_float(previous.get((sector, industry), {}).get("portfolio_weight_after", "0"))
            curr_weight = to_float(current.get((sector, industry), {}).get("portfolio_weight_after", "0"))
            counts = transition_counts.get(
                (curr_period, sector, industry),
                {"entry_count": 0, "exit_count": 0, "accumulation_count": 0, "reduction_count": 0},
            )
            out.append(
                {
                    "period": f"{prev_period}->{curr_period}",
                    "prev_as_of_date": prev_period,
                    "curr_as_of_date": curr_period,
                    "public_date": period_meta[curr_period]["public_date"],
                    "trade_date": period_meta[curr_period]["trade_date"],
                    "sector": sector,
                    "industry": industry,
                    "weight_before": f"{prev_weight:.8f}",
                    "weight_after": f"{curr_weight:.8f}",
                    "net_weight_change": f"{(curr_weight - prev_weight):.8f}",
                    "entry_count": str(counts["entry_count"]),
                    "exit_count": str(counts["exit_count"]),
                    "accumulation_count": str(counts["accumulation_count"]),
                    "reduction_count": str(counts["reduction_count"]),
                }
            )
    return out


def build_audit_rows(enriched_holdings: list[dict[str, str]]) -> list[dict[str, str]]:
    period_meta: dict[str, dict[str, str]] = {}
    for row in enriched_holdings:
        period_meta.setdefault(
            row["as_of_date"],
            {
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
            },
        )
    by_period: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "public_date": "",
            "trade_date": "",
            "holding_rows": 0,
            "mapped_rows": 0,
            "total_market_value_usd": 0.0,
            "mapped_market_value_usd": 0.0,
            "unmapped_cusips": set(),
        }
    )

    for row in enriched_holdings:
        if row["sector_eligible_flag"] != "1":
            continue
        bucket = by_period[row["as_of_date"]]
        bucket["public_date"] = row["public_date"]
        bucket["trade_date"] = row["trade_date"]
        bucket["holding_rows"] += 1
        value = to_float(row["market_value_usd"])
        bucket["total_market_value_usd"] += value
        if row["sector_map_status"] == "mapped":
            bucket["mapped_rows"] += 1
            bucket["mapped_market_value_usd"] += value
        else:
            bucket["unmapped_cusips"].add(row["cusip"])

    out: list[dict[str, str]] = []
    for period in sorted(period_meta):
        bucket = by_period[period]
        if not bucket["public_date"]:
            bucket["public_date"] = period_meta[period]["public_date"]
            bucket["trade_date"] = period_meta[period]["trade_date"]
        bucket = by_period[period]
        if bucket["holding_rows"]:
            row_coverage = bucket["mapped_rows"] / bucket["holding_rows"]
            value_coverage = (
                bucket["mapped_market_value_usd"] / bucket["total_market_value_usd"]
                if bucket["total_market_value_usd"]
                else 1.0
            )
            no_sector_rows_flag = "0"
        else:
            row_coverage = 1.0
            value_coverage = 1.0
            no_sector_rows_flag = "1"
        out.append(
            {
                "as_of_date": period,
                "public_date": str(bucket["public_date"]),
                "trade_date": str(bucket["trade_date"]),
                "holding_rows": str(bucket["holding_rows"]),
                "mapped_rows": str(bucket["mapped_rows"]),
                "no_sector_eligible_rows_flag": no_sector_rows_flag,
                "row_coverage": f"{row_coverage:.8f}",
                "total_market_value_usd": f"{float(bucket['total_market_value_usd']):.6f}",
                "mapped_market_value_usd": f"{float(bucket['mapped_market_value_usd']):.6f}",
                "value_coverage": f"{value_coverage:.8f}",
                "unmapped_cusips": "|".join(sorted(bucket["unmapped_cusips"])),
            }
        )
    return out


def main() -> None:
    crosswalk = load_crosswalk()
    trade_date_by_period = build_trade_date_map()

    holdings_rows = read_csv(HOLDINGS_PATH)
    transition_rows = read_csv(TRANSITIONS_PATH)

    enriched_holdings = enrich_holdings(holdings_rows, crosswalk, trade_date_by_period)
    enriched_transitions = enrich_transitions(transition_rows, crosswalk, trade_date_by_period)

    exposure_rows = build_exposure_rows(enriched_holdings)
    change_rows = build_change_rows(exposure_rows, enriched_transitions, enriched_holdings)
    audit_rows = build_audit_rows(enriched_holdings)

    write_csv(ENRICHED_HOLDINGS_PATH, enriched_holdings)
    write_csv(ENRICHED_TRANSITIONS_PATH, enriched_transitions)
    write_csv(EXPOSURE_PATH, exposure_rows)
    write_csv(CHANGE_PATH, change_rows)
    write_csv(AUDIT_PATH, audit_rows)

    print(f"Wrote {len(enriched_holdings)} enriched holdings rows to {ENRICHED_HOLDINGS_PATH}")
    print(f"Wrote {len(enriched_transitions)} enriched transition rows to {ENRICHED_TRANSITIONS_PATH}")
    print(f"Wrote {len(exposure_rows)} sector exposure rows to {EXPOSURE_PATH}")
    print(f"Wrote {len(change_rows)} sector change rows to {CHANGE_PATH}")
    print(f"Wrote {len(audit_rows)} audit rows to {AUDIT_PATH}")


if __name__ == "__main__":
    main()
