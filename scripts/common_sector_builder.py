from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "data" / "reference"
PROCESSED_ROOT = ROOT / "data" / "processed"
PIF_ROOT = PROCESSED_ROOT / "pif"
NBIM_ROOT = PROCESSED_ROOT / "nbim"
SIGNALS_ROOT = PROCESSED_ROOT / "signals"

CROSSWALK_PATH = REFERENCE_ROOT / "common_sector_crosswalk.csv"
PIF_EXPOSURE_PATH = PIF_ROOT / "pif_sector_exposure_by_filing.csv"
PIF_CHANGE_PATH = PIF_ROOT / "pif_sector_change_by_filing.csv"
NBIM_SNAPSHOT_PATH = NBIM_ROOT / "nbim_snapshot_industry_summary.csv"
NBIM_TRANSITION_PATH = NBIM_ROOT / "nbim_transition_industry_summary.csv"
NBIM_PUBLIC_DATE_PATH = NBIM_ROOT / "nbim_public_date_map.csv"
NBIM_PRICE_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"

PIF_EXPOSURE_OUT = PIF_ROOT / "pif_sector_exposure_common.csv"
PIF_CHANGE_OUT = PIF_ROOT / "pif_sector_change_common.csv"
NBIM_SNAPSHOT_OUT = NBIM_ROOT / "nbim_snapshot_sector_common.csv"
NBIM_TRANSITION_OUT = NBIM_ROOT / "nbim_transition_sector_common.csv"
AUDIT_OUT = SIGNALS_ROOT / "common_sector_crosswalk_audit.csv"


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


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def load_crosswalk() -> dict[tuple[str, str, str], str]:
    mapping: dict[tuple[str, str, str], str] = {}
    for row in read_csv(CROSSWALK_PATH):
        mapping[(row["source_system"], row["raw_label_type"], row["raw_label"])] = row["common_sector"]
    return mapping


def load_nbim_trade_map() -> dict[str, dict[str, str]]:
    public_rows = read_csv(NBIM_PUBLIC_DATE_PATH)
    price_rows = read_csv(NBIM_PRICE_PATH)
    calendar_dates = sorted(
        {
            row["date"]
            for row in price_rows
            if row["instrument_key"] == "benchmark_vt" and row["adjust_mode"] == "all"
        }
    )
    out: dict[str, dict[str, str]] = {}
    for row in public_rows:
        public_date = row["public_date"]
        trade_date = next((d for d in calendar_dates if d > public_date), "")
        if not trade_date:
            raise RuntimeError(f"No trade date found after NBIM public date {public_date}")
        out[row["as_of_date"]] = {
            "public_date": public_date,
            "trade_date": trade_date,
            "report_type": row["report_type"],
        }
    return out


def aggregate_pif_exposure(crosswalk: dict[tuple[str, str, str], str]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, float | str]] = {}
    for row in read_csv(PIF_EXPOSURE_PATH):
        common_sector = crosswalk[("PIF", "sector", row["sector"])]
        key = (row["as_of_date"], common_sector)
        bucket = grouped.setdefault(
            key,
            {
                "as_of_date": row["as_of_date"],
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
                "common_sector": common_sector,
                "holding_count": 0.0,
                "mapped_holding_count": 0.0,
                "total_market_value_usd": 0.0,
                "portfolio_weight_after": 0.0,
                "raw_sector_count": 0.0,
            },
        )
        bucket["holding_count"] += to_float(row["holding_count"])
        bucket["mapped_holding_count"] += to_float(row["mapped_holding_count"])
        bucket["total_market_value_usd"] += to_float(row["total_market_value_usd"])
        bucket["portfolio_weight_after"] += to_float(row["portfolio_weight_after"])
        bucket["raw_sector_count"] += 1.0

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        row = grouped[key]
        out.append(
            {
                "as_of_date": str(row["as_of_date"]),
                "public_date": str(row["public_date"]),
                "trade_date": str(row["trade_date"]),
                "common_sector": str(row["common_sector"]),
                "holding_count": str(int(row["holding_count"])),
                "mapped_holding_count": str(int(row["mapped_holding_count"])),
                "raw_sector_count": str(int(row["raw_sector_count"])),
                "total_market_value_usd": f"{float(row['total_market_value_usd']):.6f}",
                "portfolio_weight_after": f"{float(row['portfolio_weight_after']):.8f}",
            }
        )
    return out


def aggregate_pif_change(crosswalk: dict[tuple[str, str, str], str]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, float | str]] = {}
    for row in read_csv(PIF_CHANGE_PATH):
        common_sector = crosswalk[("PIF", "sector", row["sector"])]
        key = (row["period"], common_sector)
        bucket = grouped.setdefault(
            key,
            {
                "period": row["period"],
                "prev_as_of_date": row["prev_as_of_date"],
                "curr_as_of_date": row["curr_as_of_date"],
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
                "common_sector": common_sector,
                "weight_before": 0.0,
                "weight_after": 0.0,
                "net_weight_change": 0.0,
                "entry_count": 0.0,
                "exit_count": 0.0,
                "accumulation_count": 0.0,
                "reduction_count": 0.0,
                "raw_sector_count": 0.0,
            },
        )
        bucket["weight_before"] += to_float(row["weight_before"])
        bucket["weight_after"] += to_float(row["weight_after"])
        bucket["net_weight_change"] += to_float(row["net_weight_change"])
        bucket["entry_count"] += to_float(row["entry_count"])
        bucket["exit_count"] += to_float(row["exit_count"])
        bucket["accumulation_count"] += to_float(row["accumulation_count"])
        bucket["reduction_count"] += to_float(row["reduction_count"])
        bucket["raw_sector_count"] += 1.0

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        row = grouped[key]
        out.append(
            {
                "period": str(row["period"]),
                "prev_as_of_date": str(row["prev_as_of_date"]),
                "curr_as_of_date": str(row["curr_as_of_date"]),
                "public_date": str(row["public_date"]),
                "trade_date": str(row["trade_date"]),
                "common_sector": str(row["common_sector"]),
                "weight_before": f"{float(row['weight_before']):.8f}",
                "weight_after": f"{float(row['weight_after']):.8f}",
                "net_weight_change": f"{float(row['net_weight_change']):.8f}",
                "entry_count": str(int(row["entry_count"])),
                "exit_count": str(int(row["exit_count"])),
                "accumulation_count": str(int(row["accumulation_count"])),
                "reduction_count": str(int(row["reduction_count"])),
                "raw_sector_count": str(int(row["raw_sector_count"])),
            }
        )
    return out


def aggregate_nbim_snapshot(
    crosswalk: dict[tuple[str, str, str], str],
    nbim_trade_map: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, float | str]] = {}
    for row in read_csv(NBIM_SNAPSHOT_PATH):
        common_sector = crosswalk[("NBIM", "industry", row["industry"])]
        meta = nbim_trade_map[row["as_of_date"]]
        key = (row["as_of_date"], common_sector)
        bucket = grouped.setdefault(
            key,
            {
                "as_of_date": row["as_of_date"],
                "public_date": meta["public_date"],
                "trade_date": meta["trade_date"],
                "report_type": meta["report_type"],
                "common_sector": common_sector,
                "holding_count": 0.0,
                "total_market_value_usd": 0.0,
                "portfolio_weight_usd": 0.0,
                "weighted_ownership_sum": 0.0,
                "weighted_voting_sum": 0.0,
                "raw_industry_count": 0.0,
            },
        )
        holding_count = to_float(row["holding_count"])
        weight = to_float(row["portfolio_weight_usd"])
        bucket["holding_count"] += holding_count
        bucket["total_market_value_usd"] += to_float(row["total_market_value_usd"])
        bucket["portfolio_weight_usd"] += weight
        bucket["weighted_ownership_sum"] += to_float(row["avg_ownership_pct"]) * weight
        bucket["weighted_voting_sum"] += to_float(row["avg_voting_pct"]) * weight
        bucket["raw_industry_count"] += 1.0

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        row = grouped[key]
        total_weight = float(row["portfolio_weight_usd"])
        avg_ownership = float(row["weighted_ownership_sum"]) / total_weight if total_weight else 0.0
        avg_voting = float(row["weighted_voting_sum"]) / total_weight if total_weight else 0.0
        out.append(
            {
                "as_of_date": str(row["as_of_date"]),
                "public_date": str(row["public_date"]),
                "trade_date": str(row["trade_date"]),
                "report_type": str(row["report_type"]),
                "common_sector": str(row["common_sector"]),
                "holding_count": str(int(row["holding_count"])),
                "raw_industry_count": str(int(row["raw_industry_count"])),
                "total_market_value_usd": f"{float(row['total_market_value_usd']):.6f}",
                "portfolio_weight_usd": f"{total_weight:.8f}",
                "avg_ownership_pct": f"{avg_ownership:.8f}",
                "avg_voting_pct": f"{avg_voting:.8f}",
            }
        )
    return out


def aggregate_nbim_transition(
    crosswalk: dict[tuple[str, str, str], str],
    nbim_trade_map: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, float | str]] = {}
    for row in read_csv(NBIM_TRANSITION_PATH):
        common_sector = crosswalk[("NBIM", "industry", row["industry"])]
        meta = nbim_trade_map[row["curr_as_of_date"]]
        key = (row["period"], common_sector)
        bucket = grouped.setdefault(
            key,
            {
                "period": row["period"],
                "prev_as_of_date": row["prev_as_of_date"],
                "curr_as_of_date": row["curr_as_of_date"],
                "public_date": meta["public_date"],
                "trade_date": meta["trade_date"],
                "common_sector": common_sector,
                "transition_count": 0.0,
                "entry_observed": 0.0,
                "exit_observed": 0.0,
                "likely_accumulation": 0.0,
                "likely_reduction": 0.0,
                "continued_holding": 0.0,
                "voting_up": 0.0,
                "voting_down": 0.0,
                "total_delta_market_value_usd": 0.0,
                "total_abs_delta_market_value_usd": 0.0,
                "raw_industry_count": 0.0,
            },
        )
        for field in [
            "transition_count",
            "entry_observed",
            "exit_observed",
            "likely_accumulation",
            "likely_reduction",
            "continued_holding",
            "voting_up",
            "voting_down",
            "total_delta_market_value_usd",
            "total_abs_delta_market_value_usd",
        ]:
            bucket[field] += to_float(row[field])
        bucket["raw_industry_count"] += 1.0

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        row = grouped[key]
        out.append(
            {
                "period": str(row["period"]),
                "prev_as_of_date": str(row["prev_as_of_date"]),
                "curr_as_of_date": str(row["curr_as_of_date"]),
                "public_date": str(row["public_date"]),
                "trade_date": str(row["trade_date"]),
                "common_sector": str(row["common_sector"]),
                "transition_count": str(int(row["transition_count"])),
                "entry_observed": str(int(row["entry_observed"])),
                "exit_observed": str(int(row["exit_observed"])),
                "likely_accumulation": str(int(row["likely_accumulation"])),
                "likely_reduction": str(int(row["likely_reduction"])),
                "continued_holding": str(int(row["continued_holding"])),
                "voting_up": str(int(row["voting_up"])),
                "voting_down": str(int(row["voting_down"])),
                "total_delta_market_value_usd": f"{float(row['total_delta_market_value_usd']):.6f}",
                "total_abs_delta_market_value_usd": f"{float(row['total_abs_delta_market_value_usd']):.6f}",
                "raw_industry_count": str(int(row["raw_industry_count"])),
            }
        )
    return out


def build_audit_rows(crosswalk: dict[tuple[str, str, str], str]) -> list[dict[str, str]]:
    checks = [
        ("PIF", "sector", {row["sector"] for row in read_csv(PIF_EXPOSURE_PATH)}),
        ("NBIM", "industry", {row["industry"] for row in read_csv(NBIM_SNAPSHOT_PATH)}),
    ]
    rows: list[dict[str, str]] = []
    for source_system, raw_label_type, labels in checks:
        for label in sorted(labels):
            common_sector = crosswalk.get((source_system, raw_label_type, label), "")
            rows.append(
                {
                    "source_system": source_system,
                    "raw_label_type": raw_label_type,
                    "raw_label": label,
                    "common_sector": common_sector,
                    "mapping_status": "mapped" if common_sector else "unmapped",
                }
            )
    return rows


def main() -> None:
    crosswalk = load_crosswalk()
    nbim_trade_map = load_nbim_trade_map()

    pif_exposure_common = aggregate_pif_exposure(crosswalk)
    pif_change_common = aggregate_pif_change(crosswalk)
    nbim_snapshot_common = aggregate_nbim_snapshot(crosswalk, nbim_trade_map)
    nbim_transition_common = aggregate_nbim_transition(crosswalk, nbim_trade_map)
    audit_rows = build_audit_rows(crosswalk)

    if any(row["mapping_status"] != "mapped" for row in audit_rows):
        raise RuntimeError("Common sector crosswalk is incomplete.")

    write_csv(PIF_EXPOSURE_OUT, pif_exposure_common)
    write_csv(PIF_CHANGE_OUT, pif_change_common)
    write_csv(NBIM_SNAPSHOT_OUT, nbim_snapshot_common)
    write_csv(NBIM_TRANSITION_OUT, nbim_transition_common)
    write_csv(AUDIT_OUT, audit_rows)

    print(f"Wrote {len(pif_exposure_common)} PIF common-sector exposure rows to {PIF_EXPOSURE_OUT}")
    print(f"Wrote {len(pif_change_common)} PIF common-sector change rows to {PIF_CHANGE_OUT}")
    print(f"Wrote {len(nbim_snapshot_common)} NBIM common-sector snapshot rows to {NBIM_SNAPSHOT_OUT}")
    print(f"Wrote {len(nbim_transition_common)} NBIM common-sector transition rows to {NBIM_TRANSITION_OUT}")
    print(f"Wrote {len(audit_rows)} crosswalk audit rows to {AUDIT_OUT}")


if __name__ == "__main__":
    main()
