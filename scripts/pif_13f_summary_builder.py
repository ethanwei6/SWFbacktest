from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOLDINGS_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv"
TRANSITIONS_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_transition_events.csv"
SNAPSHOT_OUT = ROOT / "data" / "processed" / "pif" / "pif_13f_snapshot_summary.csv"
TRANSITION_OUT = ROOT / "data" / "processed" / "pif" / "pif_13f_transition_summary.csv"


def parse_float(value: str) -> float:
    if value.strip() == "":
        return 0.0
    return float(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def build_snapshot_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row["as_of_date"]].append(row)

    out: list[dict[str, str]] = []
    for as_of_date in sorted(by_date):
        snap = by_date[as_of_date]
        total_value = sum(parse_float(r["market_value_usd"]) for r in snap)
        total_shares = sum(parse_float(r["shares"]) for r in snap)
        out.append(
            {
                "as_of_date": as_of_date,
                "public_date": min(r["public_date"] for r in snap if r["public_date"]),
                "holding_count": str(len(snap)),
                "total_market_value_usd": f"{total_value:.0f}",
                "total_shares": f"{total_shares:.0f}",
                "option_row_count": str(sum(1 for r in snap if r["put_call"])),
                "common_row_count": str(sum(1 for r in snap if not r["put_call"])),
                "largest_holding": max(snap, key=lambda r: parse_float(r["market_value_usd"]))["issuer_name"],
            }
        )
    return out


def build_transition_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_period: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        label = f"{row['prev_as_of_date']}->{row['curr_as_of_date']}"
        by_period[label].append(row)

    tracked = [
        "entry_observed",
        "exit_observed",
        "likely_accumulation",
        "likely_reduction",
        "continued_holding",
    ]
    out: list[dict[str, str]] = []
    for label in sorted(by_period):
        period_rows = by_period[label]
        counts = {key: 0 for key in tracked}
        share_delta_total = 0.0
        value_delta_total = 0.0
        for row in period_rows:
            event = row["primary_event_type"]
            if event in counts:
                counts[event] += 1
            share_delta_total += parse_float(row["delta_shares"])
            value_delta_total += parse_float(row["delta_market_value_usd"])

        out.append(
            {
                "period": label,
                "prev_as_of_date": period_rows[0]["prev_as_of_date"],
                "curr_as_of_date": period_rows[0]["curr_as_of_date"],
                "transition_count": str(len(period_rows)),
                **{key: str(counts[key]) for key in tracked},
                "net_share_delta": f"{share_delta_total:.0f}",
                "net_market_value_delta_usd": f"{value_delta_total:.0f}",
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
    holdings = read_csv(HOLDINGS_PATH)
    transitions = read_csv(TRANSITIONS_PATH)
    snapshot_rows = build_snapshot_summary(holdings)
    transition_rows = build_transition_summary(transitions)
    write_csv(SNAPSHOT_OUT, snapshot_rows)
    write_csv(TRANSITION_OUT, transition_rows)
    print(f"Wrote {len(snapshot_rows)} rows to {SNAPSHOT_OUT}")
    print(f"Wrote {len(transition_rows)} rows to {TRANSITION_OUT}")


if __name__ == "__main__":
    main()
