from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_public_equity_holdings.csv"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Processed file not found: {INPUT_PATH}")

    rows = []
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            rows.append(row)

    by_date = Counter(row["as_of_date"] for row in rows)
    by_region = Counter(row["region"] for row in rows)
    by_industry = Counter(row["industry"] for row in rows)
    max_by_date: dict[str, tuple[str, float]] = {}

    for row in rows:
        value = float(row["market_value_usd"] or 0)
        as_of_date = row["as_of_date"]
        current = max_by_date.get(as_of_date)
        if current is None or value > current[1]:
            max_by_date[as_of_date] = (row["issuer_name"], value)

    print(f"rows: {len(rows)}")
    print(f"dates: {len(by_date)}")
    print("rows by date:")
    for as_of_date, count in sorted(by_date.items()):
        print(f"  {as_of_date}: {count}")

    print("top regions by row count:")
    for region, count in by_region.most_common(10):
        print(f"  {region}: {count}")

    print("top industries by row count:")
    for industry, count in by_industry.most_common(10):
        print(f"  {industry}: {count}")

    print("largest holding by date (USD market value):")
    for as_of_date in sorted(max_by_date):
        issuer, value = max_by_date[as_of_date]
        print(f"  {as_of_date}: {issuer} ({value:,.0f})")


if __name__ == "__main__":
    main()
