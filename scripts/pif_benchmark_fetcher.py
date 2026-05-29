from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
API_BASE = "https://api.twelvedata.com"
MAX_RETRIES = 4

BENCHMARKS = [
    {
        "benchmark_key": "SPY",
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "start_date": "2019-01-01",
    }
]


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


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_series(symbol: str, start_date: str, end_date: str, api_key: str) -> dict[str, Any]:
    query = urlencode(
        {
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date,
            "adjust": "all",
            "outputsize": "5000",
            "apikey": api_key,
        }
    )
    url = f"{API_BASE}/time_series?{query}"
    retry_delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_json(url)
        except HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise
    raise RuntimeError(f"Unreachable retry state for {symbol}")


def normalize_rows(payload: dict[str, Any], benchmark: dict[str, str]) -> list[dict[str, str]]:
    meta = payload.get("meta", {})
    rows: list[dict[str, str]] = []
    for value in payload.get("values", []):
        rows.append(
            {
                "benchmark_key": benchmark["benchmark_key"],
                "symbol": benchmark["symbol"],
                "benchmark_name": benchmark["name"],
                "adjust_mode": "all",
                "date": str(value.get("datetime", ""))[:10],
                "open": str(value.get("open", "")),
                "high": str(value.get("high", "")),
                "low": str(value.get("low", "")),
                "close": str(value.get("close", "")),
                "volume": str(value.get("volume", "")),
                "exchange": str(meta.get("exchange", "")),
                "currency": str(meta.get("currency", "")),
                "exchange_timezone": str(meta.get("exchange_timezone", "")),
                "instrument_type": str(meta.get("type", "")),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="Optional Twelve Data API key override.")
    parser.add_argument("--end-date", default="2026-05-29", help="Inclusive benchmark end date.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = load_api_key(args.api_key)
    all_rows: list[dict[str, str]] = []
    for benchmark in BENCHMARKS:
        payload = fetch_series(benchmark["symbol"], benchmark["start_date"], args.end_date, api_key)
        if payload.get("status") == "error":
            raise RuntimeError(f"{benchmark['symbol']} benchmark fetch failed: {payload.get('message', 'Unknown error')}")
        all_rows.extend(normalize_rows(payload, benchmark))
    all_rows.sort(key=lambda row: (row["benchmark_key"], row["date"]))
    write_csv(OUT_PATH, all_rows)
    print(f"Wrote benchmark rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
