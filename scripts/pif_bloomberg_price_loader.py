from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "pif" / "prices"
SECURITY_MASTER_PATH = ROOT / "data" / "processed" / "pif" / "pif_price_security_master.csv"
RAW_PRICE_PATH = RAW_DIR / "pif_bloomberg_daily_prices.csv"
RAW_MAP_PATH = RAW_DIR / "pif_bloomberg_security_map.csv"
OUT_PRICE_PANEL_PATH = ROOT / "data" / "processed" / "pif" / "pif_daily_price_panel.csv"
OUT_PRICE_AUDIT_PATH = ROOT / "data" / "processed" / "pif" / "pif_daily_price_audit.csv"

REQUIRED_PRICE_COLUMNS = {
    "price_identifier_type",
    "price_identifier_value",
    "date",
    "px_open",
    "px_last",
    "currency",
    "bbg_ticker",
    "bbg_security_name",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def normalize_text(value: str) -> str:
    return value.strip()


def build_master_lookup(master_rows: list[dict[str, str]], map_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in master_rows:
        identifier_type = normalize_text(row["price_identifier_type"]).upper()
        identifier_value = normalize_text(row["price_identifier_value"])
        if identifier_type and identifier_value:
            by_key[(identifier_type, identifier_value)] = row

    for row in map_rows:
        identifier_type = normalize_text(row.get("price_identifier_type", "")).upper()
        identifier_value = normalize_text(row.get("price_identifier_value", ""))
        security_key = normalize_text(row.get("security_key", ""))
        if not (identifier_type and identifier_value and security_key):
            continue
        for master_row in master_rows:
            if master_row["security_key"] == security_key:
                by_key[(identifier_type, identifier_value)] = master_row
                break
    return by_key


def validate_price_columns(price_rows: list[dict[str, str]]) -> None:
    if not price_rows:
        raise ValueError("Raw price file is empty.")
    missing = REQUIRED_PRICE_COLUMNS - set(price_rows[0].keys())
    if missing:
        raise ValueError(f"Raw price file is missing required columns: {sorted(missing)}")


def build_price_panel(
    master_rows: list[dict[str, str]],
    map_rows: list[dict[str, str]],
    price_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    master_lookup = build_master_lookup(master_rows, map_rows)
    out_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for row in price_rows:
        identifier_type = normalize_text(row["price_identifier_type"]).upper()
        identifier_value = normalize_text(row["price_identifier_value"])
        trade_date = normalize_text(row["date"])
        pair = (identifier_type, identifier_value, trade_date)
        if pair in seen_pairs:
            raise ValueError(f"Duplicate price row detected for {pair}")
        seen_pairs.add(pair)

        master_row = master_lookup.get((identifier_type, identifier_value))
        if master_row is None:
            audit_rows.append(
                {
                    "security_key": "",
                    "price_identifier_type": identifier_type,
                    "price_identifier_value": identifier_value,
                    "audit_status": "unmapped_price_row",
                    "audit_note": "Raw price row did not match any security in the PIF price master.",
                }
            )
            continue

        out_rows.append(
            {
                "security_key": master_row["security_key"],
                "issuer_name": master_row["issuer_name"],
                "cusip": master_row["cusip"],
                "price_identifier_type": identifier_type,
                "price_identifier_value": identifier_value,
                "date": trade_date,
                "px_open": normalize_text(row["px_open"]),
                "px_last": normalize_text(row["px_last"]),
                "currency": normalize_text(row["currency"]),
                "bbg_ticker": normalize_text(row["bbg_ticker"]),
                "bbg_security_name": normalize_text(row["bbg_security_name"]),
                "total_return_index_gross_dvds": normalize_text(row.get("total_return_index_gross_dvds", "")),
                "total_return_index_net_dvds": normalize_text(row.get("total_return_index_net_dvds", "")),
            }
        )

    mapped_security_keys = {row["security_key"] for row in out_rows}
    for row in master_rows:
        audit_rows.append(
            {
                "security_key": row["security_key"],
                "price_identifier_type": row["price_identifier_type"],
                "price_identifier_value": row["price_identifier_value"],
                "audit_status": "mapped" if row["security_key"] in mapped_security_keys else "missing_prices",
                "audit_note": "" if row["security_key"] in mapped_security_keys else "No daily price rows matched this security.",
            }
        )

    return out_rows, audit_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not RAW_PRICE_PATH.exists():
        raise FileNotFoundError(f"Raw Bloomberg price file not found: {RAW_PRICE_PATH}")

    master_rows = read_csv(SECURITY_MASTER_PATH)
    map_rows = read_csv(RAW_MAP_PATH) if RAW_MAP_PATH.exists() else []
    price_rows = read_csv(RAW_PRICE_PATH)
    validate_price_columns(price_rows)
    out_rows, audit_rows = build_price_panel(master_rows, map_rows, price_rows)
    if not out_rows:
        raise ValueError("No price rows were mapped into the normalized PIF daily price panel.")
    write_csv(OUT_PRICE_PANEL_PATH, out_rows)
    write_csv(OUT_PRICE_AUDIT_PATH, audit_rows)
    print(f"Wrote {len(out_rows)} rows to {OUT_PRICE_PANEL_PATH}")
    print(f"Wrote {len(audit_rows)} rows to {OUT_PRICE_AUDIT_PATH}")


if __name__ == "__main__":
    main()
