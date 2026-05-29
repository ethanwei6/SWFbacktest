from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_public_equity_holdings.csv"
SNAPSHOT_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_snapshot_summary.csv"
REGION_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_snapshot_region_summary.csv"
INDUSTRY_OUT = ROOT / "data" / "processed" / "nbim" / "nbim_snapshot_industry_summary.csv"


def parse_float(value: str) -> float:
    text = value.strip()
    if text == "":
        return 0.0
    return float(text)


def compute_hhi(values: list[float], total: float) -> float:
    if total <= 0:
        return 0.0
    return sum((value / total) ** 2 for value in values)


def load_rows() -> list[dict[str, str]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Processed holdings file not found: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def build_snapshot_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row["as_of_date"]].append(row)

    output: list[dict[str, str]] = []
    for as_of_date in sorted(by_date):
        snapshot_rows = by_date[as_of_date]
        market_values = [parse_float(row["market_value_usd"]) for row in snapshot_rows]
        total_market_value_usd = sum(market_values)
        sorted_values = sorted(market_values, reverse=True)
        top_10_market_value_usd = sum(sorted_values[:10])
        top_10_share = (top_10_market_value_usd / total_market_value_usd) if total_market_value_usd else 0.0

        output.append(
            {
                "as_of_date": as_of_date,
                "holding_count": str(len(snapshot_rows)),
                "total_market_value_usd": f"{total_market_value_usd:.6f}",
                "top_10_market_value_usd": f"{top_10_market_value_usd:.6f}",
                "top_10_share": f"{top_10_share:.6f}",
                "hhi_market_value_usd": f"{compute_hhi(market_values, total_market_value_usd):.8f}",
                "unique_regions": str(len({row['region'] for row in snapshot_rows if row['region']})),
                "unique_industries": str(len({row['industry'] for row in snapshot_rows if row['industry']})),
            }
        )

    return output


def build_group_summary(
    rows: list[dict[str, str]],
    *,
    group_field: str,
) -> list[dict[str, str]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row["as_of_date"]].append(row)

    output: list[dict[str, str]] = []
    for as_of_date in sorted(by_date):
        snapshot_rows = by_date[as_of_date]
        total_market_value_usd = sum(parse_float(row["market_value_usd"]) for row in snapshot_rows)
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in snapshot_rows:
            grouped[row[group_field] or "UNKNOWN"].append(row)

        for group_name in sorted(grouped):
            group_rows = grouped[group_name]
            market_value_usd = sum(parse_float(row["market_value_usd"]) for row in group_rows)
            weight = (market_value_usd / total_market_value_usd) if total_market_value_usd else 0.0

            output.append(
                {
                    "as_of_date": as_of_date,
                    group_field: group_name,
                    "holding_count": str(len(group_rows)),
                    "total_market_value_usd": f"{market_value_usd:.6f}",
                    "portfolio_weight_usd": f"{weight:.6f}",
                    "avg_ownership_pct": format_average(group_rows, "ownership_pct"),
                    "avg_voting_pct": format_average(group_rows, "voting_pct"),
                }
            )

    return output


def format_average(rows: list[dict[str, str]], field: str) -> str:
    values = [parse_float(row[field]) for row in rows if row[field].strip() != ""]
    if not values:
        return ""
    return f"{sum(values) / len(values):.6f}"


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
    snapshot_rows = build_snapshot_summary(rows)
    region_rows = build_group_summary(rows, group_field="region")
    industry_rows = build_group_summary(rows, group_field="industry")

    write_csv(SNAPSHOT_OUT, snapshot_rows)
    write_csv(REGION_OUT, region_rows)
    write_csv(INDUSTRY_OUT, industry_rows)

    print(f"Wrote {len(snapshot_rows)} rows to {SNAPSHOT_OUT}")
    print(f"Wrote {len(region_rows)} rows to {REGION_OUT}")
    print(f"Wrote {len(industry_rows)} rows to {INDUSTRY_OUT}")


if __name__ == "__main__":
    main()
