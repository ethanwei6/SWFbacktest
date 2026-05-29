from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv"


def parse_float(value: str) -> float:
    if value.strip() == "":
        return 0.0
    return float(value)


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Processed file not found: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8", newline="") as infile:
        rows = list(csv.DictReader(infile))

    by_date = Counter(row["as_of_date"] for row in rows)
    by_filing = Counter(row["accession_number"] for row in rows)
    value_by_date = defaultdict(float)
    max_by_date: dict[str, tuple[str, float]] = {}

    for row in rows:
        as_of_date = row["as_of_date"]
        value = parse_float(row["market_value_usd"])
        value_by_date[as_of_date] += value
        current = max_by_date.get(as_of_date)
        if current is None or value > current[1]:
            max_by_date[as_of_date] = (row["issuer_name"], value)

    print(f"rows: {len(rows)}")
    print(f"periods: {len(by_date)}")
    print(f"filings: {len(by_filing)}")
    print("rows by period:")
    for as_of_date, count in sorted(by_date.items()):
        print(f"  {as_of_date}: {count}")
    print("value by period:")
    for as_of_date in sorted(value_by_date):
        print(f"  {as_of_date}: {value_by_date[as_of_date]:,.0f}")
    print("largest holding by period:")
    for as_of_date in sorted(max_by_date):
        issuer, value = max_by_date[as_of_date]
        print(f"  {as_of_date}: {issuer} ({value:,.0f})")


if __name__ == "__main__":
    main()
