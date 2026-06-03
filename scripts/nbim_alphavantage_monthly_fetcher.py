from __future__ import annotations

import argparse
import csv
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
UNIVERSE_PATH = NBIM_ROOT / "nbim_core_us_mirror_universe.csv"
ETF_MAP_PATH = NBIM_ROOT / "nbim_industry_etf_map.csv"
MASTER_PATH = NBIM_ROOT / "nbim_price_instrument_master.csv"
PRICE_PATH = NBIM_ROOT / "nbim_alphavantage_monthly_prices.csv"
AUDIT_PATH = NBIM_ROOT / "nbim_alphavantage_monthly_price_audit.csv"
API_BASE = "https://www.alphavantage.co/query"


@dataclass(frozen=True)
class Instrument:
    instrument_key: str
    instrument_type: str
    symbol: str
    alternate_symbol: str
    display_name: str
    source_ref: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        if not rows:
            return
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_api_key(cli_value: str) -> str:
    api_key = cli_value.strip() or os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("Missing Alpha Vantage API key.")
    return api_key


def fetch_json(query: dict[str, str]) -> dict[str, Any]:
    url = f"{API_BASE}?{urlencode(query)}"
    with urlopen(url, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def try_fetch_series(symbol: str, api_key: str, max_retries: int, sleep_seconds: float) -> dict[str, Any]:
    query = {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": symbol,
        "apikey": api_key,
    }
    for attempt in range(1, max_retries + 1):
        try:
            payload = fetch_json(query)
        except (HTTPError, URLError):
            if attempt == max_retries:
                raise
            time.sleep(sleep_seconds)
            continue
        if "Monthly Adjusted Time Series" in payload:
            return payload
        if "Note" in payload or "Information" in payload:
            if attempt == max_retries:
                return payload
            time.sleep(sleep_seconds)
            continue
        return payload
    return {}


def build_instruments() -> list[Instrument]:
    instruments: list[Instrument] = [
        Instrument(
            instrument_key="benchmark_vt",
            instrument_type="benchmark",
            symbol="VT",
            alternate_symbol="",
            display_name="Vanguard Total World Stock ETF",
            source_ref="benchmark",
        )
    ]

    seen_symbols = {"VT"}

    for row in read_csv(UNIVERSE_PATH):
        symbol = row["symbol"].strip()
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        instruments.append(
            Instrument(
                instrument_key=f"mirror::{symbol}",
                instrument_type="mirror_equity",
                symbol=symbol,
                alternate_symbol=row["alternate_symbol"].strip(),
                display_name=row["issuer_name"].strip(),
                source_ref=row["issuer_name"].strip(),
            )
        )

    seen_etf_symbols: set[str] = set()
    for row in read_csv(ETF_MAP_PATH):
        symbol = row["etf_symbol"].strip()
        if symbol in seen_etf_symbols:
            continue
        seen_etf_symbols.add(symbol)
        instruments.append(
            Instrument(
                instrument_key=f"sector::{symbol}",
                instrument_type="industry_etf",
                symbol=symbol,
                alternate_symbol="",
                display_name=row["etf_name"].strip(),
                source_ref=row["mapping_group"].strip(),
            )
        )

    return instruments


def normalize_rows(instrument: Instrument, resolved_symbol: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    meta = payload.get("Meta Data", {})
    series = payload.get("Monthly Adjusted Time Series", {})
    rows: list[dict[str, str]] = []
    for date_key in sorted(series):
        point = series[date_key]
        rows.append(
            {
                "instrument_key": instrument.instrument_key,
                "instrument_type": instrument.instrument_type,
                "display_name": instrument.display_name,
                "source_ref": instrument.source_ref,
                "requested_symbol": instrument.symbol,
                "resolved_symbol": resolved_symbol,
                "date": date_key,
                "open": str(point.get("1. open", "")),
                "high": str(point.get("2. high", "")),
                "low": str(point.get("3. low", "")),
                "close": str(point.get("4. close", "")),
                "adjusted_close": str(point.get("5. adjusted close", "")),
                "volume": str(point.get("6. volume", "")),
                "dividend_amount": str(point.get("7. dividend amount", "")),
                "timezone": str(meta.get("6. Time Zone", "")),
            }
        )
    return rows


def build_audit_rows(master_rows: list[dict[str, str]], price_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_key: dict[str, list[dict[str, str]]] = {}
    for row in price_rows:
        by_key.setdefault(row["instrument_key"], []).append(row)

    audit_rows: list[dict[str, str]] = []
    for row in master_rows:
        series_rows = sorted(by_key.get(row["instrument_key"], []), key=lambda item: item["date"])
        status = "ok" if series_rows else "missing"
        start_date = series_rows[0]["date"] if series_rows else ""
        end_date = series_rows[-1]["date"] if series_rows else ""
        audit_rows.append(
            {
                **row,
                "status": status,
                "row_count": str(len(series_rows)),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return audit_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="Optional Alpha Vantage API key override.")
    parser.add_argument("--sleep-seconds", type=float, default=16.0, help="Pause between API requests.")
    parser.add_argument("--max-retries", type=int, default=4, help="Retries per symbol.")
    parser.add_argument("--resume", action="store_true", help="Resume from an existing price file if present.")
    parser.add_argument("--allow-partial", action="store_true", help="Write a partial master/audit if the daily API limit is reached.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = load_api_key(args.api_key)
    instruments = build_instruments()

    existing_rows: list[dict[str, str]] = read_csv(PRICE_PATH) if args.resume and PRICE_PATH.exists() else []
    completed_keys = {row["instrument_key"] for row in existing_rows}
    all_price_rows = list(existing_rows)

    master_rows: list[dict[str, str]] = []
    failed_rows: list[dict[str, str]] = []

    remaining_after_failure: list[Instrument] = []
    for index, instrument in enumerate(instruments):
        if instrument.instrument_key in completed_keys:
            resolved_symbol = next(
                (
                    row["resolved_symbol"]
                    for row in all_price_rows
                    if row["instrument_key"] == instrument.instrument_key and row["resolved_symbol"]
                ),
                instrument.symbol,
            )
            master_rows.append(
                {
                    "instrument_key": instrument.instrument_key,
                    "instrument_type": instrument.instrument_type,
                    "display_name": instrument.display_name,
                    "source_ref": instrument.source_ref,
                    "requested_symbol": instrument.symbol,
                    "alternate_symbol": instrument.alternate_symbol,
                    "resolved_symbol": resolved_symbol,
                }
            )
            continue

        payload = try_fetch_series(instrument.symbol, api_key, args.max_retries, args.sleep_seconds)
        resolved_symbol = instrument.symbol

        if "Monthly Adjusted Time Series" not in payload and instrument.alternate_symbol:
            alt_payload = try_fetch_series(instrument.alternate_symbol, api_key, args.max_retries, args.sleep_seconds)
            if "Monthly Adjusted Time Series" in alt_payload:
                payload = alt_payload
                resolved_symbol = instrument.alternate_symbol

        if "Monthly Adjusted Time Series" not in payload:
            note = payload.get("Note") or payload.get("Information") or payload.get("Error Message") or "unknown_error"
            if not args.allow_partial:
                raise RuntimeError(f"Price fetch failed for {instrument.instrument_key} ({instrument.symbol}): {note}")
            failed_rows.append(
                {
                    "instrument_key": instrument.instrument_key,
                    "instrument_type": instrument.instrument_type,
                    "display_name": instrument.display_name,
                    "source_ref": instrument.source_ref,
                    "requested_symbol": instrument.symbol,
                    "alternate_symbol": instrument.alternate_symbol,
                    "resolved_symbol": "",
                    "failure_note": note,
                }
            )
            remaining_after_failure = instruments[index + 1 :]
            break

        rows = normalize_rows(instrument, resolved_symbol, payload)
        all_price_rows.extend(rows)
        master_rows.append(
            {
                "instrument_key": instrument.instrument_key,
                "instrument_type": instrument.instrument_type,
                "display_name": instrument.display_name,
                "source_ref": instrument.source_ref,
                "requested_symbol": instrument.symbol,
                "alternate_symbol": instrument.alternate_symbol,
                "resolved_symbol": resolved_symbol,
            }
        )
        all_price_rows.sort(key=lambda row: (row["instrument_key"], row["date"]))
        write_csv(PRICE_PATH, all_price_rows)
        write_csv(MASTER_PATH, master_rows)
        time.sleep(args.sleep_seconds)

    master_rows.sort(key=lambda row: row["instrument_key"])
    all_price_rows.sort(key=lambda row: (row["instrument_key"], row["date"]))
    audit_rows = build_audit_rows(master_rows, all_price_rows)
    audit_lookup = {row["instrument_key"]: row for row in audit_rows}
    for row in failed_rows:
        audit_lookup[row["instrument_key"]] = {
            "instrument_key": row["instrument_key"],
            "instrument_type": row["instrument_type"],
            "display_name": row["display_name"],
            "source_ref": row["source_ref"],
            "requested_symbol": row["requested_symbol"],
            "alternate_symbol": row["alternate_symbol"],
            "resolved_symbol": "",
            "status": "missing_rate_limited",
            "row_count": "0",
            "start_date": "",
            "end_date": "",
        }
        master_rows.append(
            {
                "instrument_key": row["instrument_key"],
                "instrument_type": row["instrument_type"],
                "display_name": row["display_name"],
                "source_ref": row["source_ref"],
                "requested_symbol": row["requested_symbol"],
                "alternate_symbol": row["alternate_symbol"],
                "resolved_symbol": "",
            }
        )
    for instrument in remaining_after_failure:
        if any(row["instrument_key"] == instrument.instrument_key for row in master_rows):
            continue
        master_rows.append(
            {
                "instrument_key": instrument.instrument_key,
                "instrument_type": instrument.instrument_type,
                "display_name": instrument.display_name,
                "source_ref": instrument.source_ref,
                "requested_symbol": instrument.symbol,
                "alternate_symbol": instrument.alternate_symbol,
                "resolved_symbol": "",
            }
        )
        audit_lookup[instrument.instrument_key] = {
            "instrument_key": instrument.instrument_key,
            "instrument_type": instrument.instrument_type,
            "display_name": instrument.display_name,
            "source_ref": instrument.source_ref,
            "requested_symbol": instrument.symbol,
            "alternate_symbol": instrument.alternate_symbol,
            "resolved_symbol": "",
            "status": "missing_unattempted_after_daily_limit",
            "row_count": "0",
            "start_date": "",
            "end_date": "",
        }
    master_rows.sort(key=lambda row: row["instrument_key"])
    audit_rows = sorted(audit_lookup.values(), key=lambda row: row["instrument_key"])

    write_csv(MASTER_PATH, master_rows)
    write_csv(PRICE_PATH, all_price_rows)
    write_csv(AUDIT_PATH, audit_rows)
    print(f"Wrote {len(all_price_rows)} monthly price rows across {len(master_rows)} instruments.")


if __name__ == "__main__":
    main()
