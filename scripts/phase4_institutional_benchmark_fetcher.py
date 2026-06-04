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
ROBUSTNESS_BENCHMARK_PATH = ROOT / "data" / "processed" / "robustness" / "benchmark_series_daily.csv"
OUT_PATH = ROOT / "data" / "processed" / "inference" / "institutional_benchmark_series_daily.csv"
AUDIT_PATH = ROOT / "data" / "processed" / "inference" / "institutional_benchmark_series_audit.csv"
METHOD_PATH = ROOT / "docs" / "methods" / "phase4-institutional-benchmarking.md"
API_BASE = "https://api.twelvedata.com"
MAX_RETRIES = 5

REMOTE_BENCHMARKS = [
    {
        "benchmark_key": "BIL",
        "symbol": "BIL",
        "benchmark_name": "SPDR Bloomberg 1-3 Month T-Bill ETF",
        "start_date": "2018-02-27",
        "benchmark_family": "cash_hurdle",
    },
    {
        "benchmark_key": "USMV",
        "symbol": "USMV",
        "benchmark_name": "iShares MSCI USA Min Vol Factor ETF",
        "start_date": "2019-01-01",
        "benchmark_family": "defensive_us_equity",
    },
    {
        "benchmark_key": "ACWV",
        "symbol": "ACWV",
        "benchmark_name": "iShares MSCI Global Min Vol Factor ETF",
        "start_date": "2018-02-27",
        "benchmark_family": "defensive_global_equity",
    },
]

REUSED_BENCHMARKS = {
    "SPY": {"benchmark_family": "market_us_equity"},
    "VT": {"benchmark_family": "market_global_equity"},
    "ACWI": {"benchmark_family": "market_global_equity"},
    "QQQ": {"benchmark_family": "market_us_growth"},
}


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


def to_float(value: str | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


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


def normalize_remote_rows(payload: dict[str, Any], benchmark: dict[str, str]) -> list[dict[str, str]]:
    meta = payload.get("meta", {})
    rows: list[dict[str, str]] = []
    for value in payload.get("values", []):
        rows.append(
            {
                "benchmark_key": benchmark["benchmark_key"],
                "symbol": benchmark["symbol"],
                "benchmark_name": benchmark["benchmark_name"],
                "benchmark_family": benchmark["benchmark_family"],
                "source": "twelvedata",
                "adjust_mode": "all",
                "date": str(value.get("datetime", ""))[:10],
                "close": str(value.get("close", "")),
                "exchange": str(meta.get("exchange", "")),
                "currency": str(meta.get("currency", "")),
                "exchange_timezone": str(meta.get("exchange_timezone", "")),
                "instrument_type": str(meta.get("type", "")),
            }
        )
    rows.sort(key=lambda row: row["date"])
    return rows


def load_reused_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in read_csv(ROBUSTNESS_BENCHMARK_PATH):
        benchmark_key = row["benchmark_key"]
        if benchmark_key not in REUSED_BENCHMARKS:
            continue
        rows.append(
            {
                "benchmark_key": benchmark_key,
                "symbol": row["symbol"],
                "benchmark_name": row["benchmark_name"],
                "benchmark_family": REUSED_BENCHMARKS[benchmark_key]["benchmark_family"],
                "source": row["source"],
                "adjust_mode": row["adjust_mode"],
                "date": row["date"],
                "close": row["close"],
                "exchange": row["exchange"],
                "currency": row["currency"],
                "exchange_timezone": row["exchange_timezone"],
                "instrument_type": row["instrument_type"],
            }
        )
    rows.sort(key=lambda row: (row["benchmark_key"], row["date"]))
    return rows


def build_audit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["benchmark_key"], []).append(row)

    audit_rows: list[dict[str, str]] = []
    for benchmark_key, series in sorted(grouped.items()):
        ordered = sorted(series, key=lambda row: row["date"])
        first_close = to_float(ordered[0]["close"])
        last_close = to_float(ordered[-1]["close"])
        audit_rows.append(
            {
                "benchmark_key": benchmark_key,
                "benchmark_name": ordered[0]["benchmark_name"],
                "benchmark_family": ordered[0]["benchmark_family"],
                "row_count": str(len(ordered)),
                "first_date": ordered[0]["date"],
                "last_date": ordered[-1]["date"],
                "first_close": ordered[0]["close"],
                "last_close": ordered[-1]["close"],
                "nonpositive_close_count": str(sum(1 for row in ordered if to_float(row["close"]) <= 0.0)),
                "close_growth_ratio": f"{(last_close / first_close) if first_close else 0.0:.12f}",
                "source": ordered[0]["source"],
                "status": "ok" if len(ordered) >= 2 and first_close > 0 and last_close > 0 else "fail",
            }
        )
    return audit_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="Optional Twelve Data API key override.")
    parser.add_argument("--end-date", default="2026-05-31", help="Inclusive benchmark end date.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = load_api_key(args.api_key)

    all_rows = load_reused_rows()
    for benchmark in REMOTE_BENCHMARKS:
        payload = fetch_series(benchmark["symbol"], benchmark["start_date"], args.end_date, api_key)
        if payload.get("status") == "error":
            raise RuntimeError(
                f"{benchmark['symbol']} benchmark fetch failed: {payload.get('message', 'Unknown error')}"
            )
        all_rows.extend(normalize_remote_rows(payload, benchmark))

    all_rows.sort(key=lambda row: (row["benchmark_key"], row["date"]))
    audit_rows = build_audit_rows(all_rows)

    write_csv(OUT_PATH, all_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 4: Institutional Benchmarking\n\n"
        "This layer expands the benchmark framework beyond simple market opportunity-cost comparisons.\n\n"
        "## Goal\n\n"
        "The project already asks whether disclosure-following strategies beat passive market beta. "
        "This extension asks a different question: whether any of the surviving strategies deliver a more "
        "institutional-style return profile with lower risk, shallower drawdowns, or better downside behavior.\n\n"
        "## Benchmark families\n\n"
        "- `SPY`, `VT`, and `ACWI` remain the market opportunity-cost benchmarks.\n"
        "- `BIL` acts as the investable cash hurdle proxy.\n"
        "- `USMV` is the defensive U.S. equity comparator.\n"
        "- `ACWV` is the defensive global equity comparator.\n\n"
        "## Price source\n\n"
        "- Existing validated market benchmarks are reused from `data/processed/robustness/benchmark_series_daily.csv`.\n"
        "- New benchmarks are fetched as adjusted daily series from Twelve Data.\n\n"
        "## Outputs\n\n"
        "- `data/processed/inference/institutional_benchmark_series_daily.csv`\n"
        "- `data/processed/inference/institutional_benchmark_series_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
