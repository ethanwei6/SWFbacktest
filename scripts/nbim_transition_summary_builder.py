from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_transition_events.csv"
SUMMARY_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_transition_summary.csv"
REGION_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_transition_region_summary.csv"
INDUSTRY_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_transition_industry_summary.csv"

TRACKED_EVENTS = [
    "entry_observed",
    "exit_observed",
    "likely_accumulation",
    "likely_reduction",
    "continued_holding",
    "voting_up",
    "voting_down",
]


def parse_float(value: str) -> float:
    text = value.strip()
    if text == "":
        return 0.0
    return float(text)


def load_rows() -> list[dict[str, str]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Processed transition file not found: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def period_label(row: dict[str, str]) -> str:
    return f"{row['prev_as_of_date']}->{row['curr_as_of_date']}"


def build_transition_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[period_label(row)].append(row)

    output: list[dict[str, str]] = []
    for label in sorted(grouped):
        group_rows = grouped[label]
        counts = {event: 0 for event in TRACKED_EVENTS}
        for row in group_rows:
            event = row["primary_event_type"]
            if event in counts:
                counts[event] += 1

        output.append(
            {
                "period": label,
                "prev_as_of_date": group_rows[0]["prev_as_of_date"],
                "curr_as_of_date": group_rows[0]["curr_as_of_date"],
                "transition_count": str(len(group_rows)),
                **{event: str(counts[event]) for event in TRACKED_EVENTS},
            }
        )

    return output


def build_group_summary(
    rows: list[dict[str, str]],
    *,
    group_field: str,
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        group_value = choose_group_value(row, group_field)
        grouped[(period_label(row), group_value)].append(row)

    output: list[dict[str, str]] = []
    for (label, group_value) in sorted(grouped):
        group_rows = grouped[(label, group_value)]
        counts = {event: 0 for event in TRACKED_EVENTS}
        total_delta_usd = 0.0
        total_abs_delta_usd = 0.0

        for row in group_rows:
            event = row["primary_event_type"]
            if event in counts:
                counts[event] += 1

            delta = parse_float(row["delta_market_value_usd"])
            total_delta_usd += delta
            total_abs_delta_usd += abs(delta)

        output.append(
            {
                "period": label,
                "prev_as_of_date": group_rows[0]["prev_as_of_date"],
                "curr_as_of_date": group_rows[0]["curr_as_of_date"],
                group_field: group_value,
                "transition_count": str(len(group_rows)),
                **{event: str(counts[event]) for event in TRACKED_EVENTS},
                "total_delta_market_value_usd": f"{total_delta_usd:.6f}",
                "total_abs_delta_market_value_usd": f"{total_abs_delta_usd:.6f}",
            }
        )

    return output


def choose_group_value(row: dict[str, str], group_field: str) -> str:
    if group_field == "region":
        value = row["curr_region"] or row["prev_region"]
    elif group_field == "industry":
        value = row["curr_industry"] or row["prev_industry"]
    else:
        raise ValueError(f"Unsupported group field: {group_field}")

    return value or "UNKNOWN"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write for {path}")

    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = load_rows()
    summary_rows = build_transition_summary(rows)
    region_rows = build_group_summary(rows, group_field="region")
    industry_rows = build_group_summary(rows, group_field="industry")

    write_csv(SUMMARY_OUT, summary_rows)
    write_csv(REGION_OUT, region_rows)
    write_csv(INDUSTRY_OUT, industry_rows)

    print(f"Wrote {len(summary_rows)} rows to {SUMMARY_OUT}")
    print(f"Wrote {len(region_rows)} rows to {REGION_OUT}")
    print(f"Wrote {len(industry_rows)} rows to {INDUSTRY_OUT}")


if __name__ == "__main__":
    main()
