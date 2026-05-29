from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "nbim"
OUT_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_public_equity_holdings.csv"

FILENAME_RE = re.compile(r"^eq_(\d{8})\.csv$", re.IGNORECASE)

FIELD_MAP = {
    "Region": "region",
    "Country": "issuer_country",
    "Name": "issuer_name",
    "Industry": "industry",
    "Market Value(NOK)": "market_value_nok",
    "Market Value(USD)": "market_value_usd",
    "Voting": "voting_pct",
    "Ownership": "ownership_pct",
    "Incorporation Country": "incorporation_country",
}


OUTPUT_COLUMNS = [
    "fund",
    "issuer_name",
    "security_name",
    "ticker",
    "isin",
    "cusip",
    "sedol",
    "asset_type",
    "listing_country",
    "issuer_country",
    "exchange",
    "region",
    "sector",
    "industry",
    "theme",
    "position_type",
    "shares",
    "market_value_local",
    "market_value_nok",
    "market_value_usd",
    "portfolio_weight",
    "ownership_pct",
    "voting_pct",
    "as_of_date",
    "public_date",
    "filing_date",
    "effective_date",
    "staleness_days",
    "disclosure_channel",
    "source_name",
    "source_url",
    "jurisdiction",
    "visibility_class",
    "observability",
    "confidence_level",
    "event_type",
    "entry_signal",
    "exit_signal",
    "event_notes",
    "source_row_id",
    "incorporation_country",
]


def clean_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def clean_percent(value: str | None) -> str:
    return clean_value(value).replace("%", "")


def file_date_from_name(path: Path) -> str:
    match = FILENAME_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected NBIM filename: {path.name}")
    token = match.group(1)
    return f"{token[0:4]}-{token[4:6]}-{token[6:8]}"


def open_nbim_csv(path: Path):
    encodings = ["utf-8-sig", "utf-16", "utf-16le", "latin-1"]
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            handle = path.open("r", encoding=encoding, newline="")
            try:
                sample = handle.read(4096)
                handle.seek(0)
                if sample:
                    return handle
            except Exception:
                handle.close()
                raise
        except UnicodeError as exc:
            last_error = exc

    raise UnicodeError(f"Could not decode {path} with supported encodings") from last_error


def build_row(raw: dict[str, str], *, as_of_date: str, source_row_id: str) -> dict[str, str]:
    out = {column: "" for column in OUTPUT_COLUMNS}

    for raw_key, out_key in FIELD_MAP.items():
        out[out_key] = clean_value(raw.get(raw_key, ""))

    out["market_value_nok"] = out["market_value_nok"].replace(",", "")
    out["market_value_usd"] = out["market_value_usd"].replace(",", "")
    out["ownership_pct"] = clean_percent(out["ownership_pct"])
    out["voting_pct"] = clean_percent(out["voting_pct"])
    out["as_of_date"] = as_of_date

    out["fund"] = "GPFG"
    out["asset_type"] = "public_equity"
    out["position_type"] = "long_equity"
    out["public_date"] = as_of_date
    out["disclosure_channel"] = "NBIM_HOLDINGS_DB"
    out["source_name"] = "NBIM GPFG_HOLDINGS_PUBLIC"
    out["source_url"] = "https://www.nbim.no/en/terms-of-use-holdings-data-in-snowflake-marketplace/"
    out["jurisdiction"] = "Norway"
    out["visibility_class"] = "full"
    out["observability"] = "observed"
    out["confidence_level"] = "high"
    out["event_type"] = "snapshot"
    out["source_row_id"] = source_row_id
    out["event_notes"] = (
        "Issuer-level year-end equity holding from NBIM historical public holdings database. "
        "public_date is provisional and must be replaced before alpha testing."
    )

    return out


def is_effectively_empty_row(raw: dict[str, str | None]) -> bool:
    return all(clean_value(value) == "" for value in raw.values())


def main() -> None:
    raw_paths = sorted(path for path in RAW_DIR.glob("eq_*.csv") if path.is_file())
    if not raw_paths:
        raise FileNotFoundError(f"No raw files found in {RAW_DIR}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    for raw_path in raw_paths:
        as_of_date = file_date_from_name(raw_path)
        with open_nbim_csv(raw_path) as infile:
            reader = csv.DictReader(infile, delimiter=";")
            for index, row in enumerate(reader, start=1):
                if is_effectively_empty_row(row):
                    continue
                rows.append(
                    build_row(
                        row,
                        as_of_date=as_of_date,
                        source_row_id=f"{raw_path.stem}:{index}",
                    )
                )

    with OUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows from {len(raw_paths)} files to {OUT_PATH}")


if __name__ == "__main__":
    main()
