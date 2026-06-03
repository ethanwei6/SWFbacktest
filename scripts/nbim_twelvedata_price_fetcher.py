from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
MASTER_PATH = NBIM_ROOT / "nbim_price_instrument_master.csv"
PUBLIC_DATE_MAP_PATH = NBIM_ROOT / "nbim_public_date_map.csv"
OUT_PANEL_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"
OUT_AUDIT_PATH = NBIM_ROOT / "nbim_twelvedata_daily_price_audit.csv"

API_BASE = "https://api.twelvedata.com/time_series"
DEFAULT_SLEEP_SECONDS = 10.0
MAX_RETRIES = 4


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
    api_key = cli_value.strip() or os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("Missing Twelve Data API key.")
    return api_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="Optional Twelve Data API key override.")
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_series(symbol: str, start_date: str, end_date: str, api_key: str) -> dict:
    query = urlencode(
        {
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date,
            "adjust": "all",
            "apikey": api_key,
        }
    )
    url = f"{API_BASE}?{query}"
    retry_delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            payload = fetch_json(url)
        except HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise
        if payload.get("status") == "ok":
            return payload
        if attempt == MAX_RETRIES:
            return payload
        time.sleep(retry_delay)
        retry_delay *= 2
    return {}


def build_date_window() -> tuple[str, str]:
    public_rows = read_csv(PUBLIC_DATE_MAP_PATH)
    start_date = min(row["public_date"] for row in public_rows)
    end_date = "2026-05-31"
    return start_date, end_date


def main() -> None:
    args = parse_args()
    api_key = load_api_key(args.api_key)
    start_date, end_date = build_date_window()
    master_rows = read_csv(MASTER_PATH)

    existing_rows = read_csv(OUT_PANEL_PATH) if args.resume and OUT_PANEL_PATH.exists() else []
    completed = {row["instrument_key"] for row in existing_rows}
    all_rows = list(existing_rows)
    audit_rows: list[dict[str, str]] = []

    for index, row in enumerate(master_rows, start=1):
        instrument_key = row["instrument_key"]
        if instrument_key in completed:
            continue

        requested_symbol = row["resolved_symbol"] or row["requested_symbol"]
        symbols_to_try = [requested_symbol]
        if row["alternate_symbol"] and row["alternate_symbol"] not in symbols_to_try:
            symbols_to_try.append(row["alternate_symbol"])

        payload = {}
        resolved_symbol = requested_symbol
        api_error = ""
        for candidate in symbols_to_try:
            payload = fetch_series(candidate, start_date, end_date, api_key)
            if payload.get("status") == "ok":
                resolved_symbol = candidate
                break
            api_error = str(payload.get("message", payload.get("status", "unknown_error")))

        values = payload.get("values", []) if payload.get("status") == "ok" else []
        normalized = []
        for point in values:
            normalized.append(
                {
                    "instrument_key": instrument_key,
                    "instrument_type": row["instrument_type"],
                    "display_name": row["display_name"],
                    "source_ref": row["source_ref"],
                    "requested_symbol": row["requested_symbol"],
                    "resolved_symbol": resolved_symbol,
                    "date": str(point.get("datetime", ""))[:10],
                    "open": str(point.get("open", "")),
                    "high": str(point.get("high", "")),
                    "low": str(point.get("low", "")),
                    "close": str(point.get("close", "")),
                    "volume": str(point.get("volume", "")),
                    "exchange": str(payload.get("meta", {}).get("exchange", "")),
                    "mic_code": str(payload.get("meta", {}).get("mic_code", "")),
                    "currency": str(payload.get("meta", {}).get("currency", "")),
                    "exchange_timezone": str(payload.get("meta", {}).get("exchange_timezone", "")),
                    "adjust_mode": "all",
                    "source": "twelvedata",
                }
            )
        all_rows.extend(normalized)
        dates = sorted(r["date"] for r in normalized)
        audit_rows.append(
            {
                "instrument_key": instrument_key,
                "instrument_type": row["instrument_type"],
                "display_name": row["display_name"],
                "requested_symbol": row["requested_symbol"],
                "resolved_symbol": resolved_symbol,
                "start_date": start_date,
                "end_date": end_date,
                "row_count": str(len(normalized)),
                "first_price_date": dates[0] if dates else "",
                "last_price_date": dates[-1] if dates else "",
                "coverage_status": "ok" if normalized else "error_or_empty",
                "api_error": api_error,
            }
        )
        write_csv(OUT_PANEL_PATH, sorted(all_rows, key=lambda item: (item["instrument_key"], item["date"])))
        write_csv(OUT_AUDIT_PATH, sorted(audit_rows, key=lambda item: item["instrument_key"]))
        if index < len(master_rows):
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
