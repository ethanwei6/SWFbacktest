from __future__ import annotations

import argparse
import csv
import json
import os
import time
from urllib.error import HTTPError
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_security_map.csv"
REQUEST_PATH = ROOT / "data" / "processed" / "pif" / "pif_price_request_template.csv"
OUT_PANEL_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_daily_prices.csv"
OUT_AUDIT_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_price_coverage_audit.csv"

API_BASE = "https://api.twelvedata.com"
DEFAULT_SECONDS_BETWEEN_REQUESTS = 0.5
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


def load_api_key() -> str:
    api_key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("Missing TWELVEDATA_API_KEY environment variable.")
    return api_key


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adjust-modes",
        default="none",
        help="Comma-separated Twelve Data adjust modes, e.g. 'none' or 'none,all'.",
    )
    parser.add_argument("--api-key", default="", help="Optional Twelve Data API key override.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SECONDS_BETWEEN_REQUESTS,
        help="Delay between API requests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of approved mappings to fetch.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing panel/audit outputs if present.",
    )
    parser.add_argument(
        "--retry-errors-only",
        action="store_true",
        help="Retry only audit rows with non-ok coverage_status from the existing audit file.",
    )
    return parser.parse_args()


def build_request_lookup(request_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["security_key"]: row for row in request_rows}


def approved_map_rows(map_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved_statuses = {"approved", "auto_approved"}
    return [row for row in map_rows if row["mapping_status"] in approved_statuses]


def existing_completed_pairs() -> tuple[set[tuple[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    completed: set[tuple[str, str]] = set()
    panel_rows: list[dict[str, str]] = read_csv(OUT_PANEL_PATH) if OUT_PANEL_PATH.exists() else []
    audit_rows: list[dict[str, str]] = read_csv(OUT_AUDIT_PATH) if OUT_AUDIT_PATH.exists() else []
    for row in audit_rows:
        completed.add((row["security_key"], row["adjust_mode"]))
    return completed, panel_rows, audit_rows


def retry_error_pairs(audit_rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    return {
        (row["security_key"], row["adjust_mode"])
        for row in audit_rows
        if row.get("coverage_status") != "ok"
    }


def fetch_series(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust_mode: str,
    api_key: str,
) -> dict[str, Any]:
    query = urlencode(
        {
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date,
            "adjust": adjust_mode,
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
    raise RuntimeError(f"Unreachable retry state for symbol {symbol}")


def normalize_price_rows(
    security_key: str,
    selected_symbol: str,
    adjust_mode: str,
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    meta = payload.get("meta", {})
    values = payload.get("values", [])
    rows: list[dict[str, str]] = []
    for value in values:
        rows.append(
            {
                "security_key": security_key,
                "symbol": selected_symbol,
                "adjust_mode": adjust_mode,
                "date": str(value.get("datetime", ""))[:10],
                "open": str(value.get("open", "")),
                "high": str(value.get("high", "")),
                "low": str(value.get("low", "")),
                "close": str(value.get("close", "")),
                "volume": str(value.get("volume", "")),
                "exchange": str(meta.get("exchange", "")),
                "mic_code": str(meta.get("mic_code", "")),
                "currency": str(meta.get("currency", "")),
                "exchange_timezone": str(meta.get("exchange_timezone", "")),
                "instrument_type": str(meta.get("type", "")),
            }
        )
    return rows


def build_coverage_audit(
    map_row: dict[str, str],
    request_row: dict[str, str],
    panel_rows: list[dict[str, str]],
    adjust_mode: str,
    api_error: str,
) -> dict[str, str]:
    dates = sorted(row["date"] for row in panel_rows)
    return {
        "security_key": map_row["security_key"],
        "issuer_name": map_row["issuer_name"],
        "selected_symbol": map_row["selected_symbol"],
        "adjust_mode": adjust_mode,
        "request_start_date": request_row["request_start_date"],
        "request_end_date": request_row["request_end_date"],
        "row_count": str(len(panel_rows)),
        "first_price_date": dates[0] if dates else "",
        "last_price_date": dates[-1] if dates else "",
        "coverage_status": "ok" if panel_rows and not api_error else "error_or_empty",
        "api_error": api_error,
    }


def main() -> None:
    args = parse_args()
    adjust_modes = [mode.strip() for mode in args.adjust_modes.split(",") if mode.strip()]
    api_key = args.api_key.strip() or load_api_key()
    map_rows = read_csv(MAP_PATH)
    request_rows = read_csv(REQUEST_PATH)
    request_lookup = build_request_lookup(request_rows)
    approved_rows = approved_map_rows(map_rows)
    if args.limit > 0:
        approved_rows = approved_rows[: args.limit]
    if not approved_rows:
        raise ValueError(
            "No approved rows found in pif_twelvedata_security_map.csv. "
            "Mark rows as 'approved' after review, then rerun."
        )

    if args.resume:
        completed_pairs, all_panel_rows, all_audit_rows = existing_completed_pairs()
        if args.retry_errors_only:
            error_pairs = retry_error_pairs(all_audit_rows)
            completed_pairs -= error_pairs
            all_audit_rows = [
                row for row in all_audit_rows
                if (row["security_key"], row["adjust_mode"]) not in error_pairs
            ]
    else:
        completed_pairs, all_panel_rows, all_audit_rows = set(), [], []
    total_requests = len(approved_rows) * len(adjust_modes)
    request_index = 0

    for map_row in approved_rows:
        request_row = request_lookup.get(map_row["security_key"])
        if request_row is None:
            raise KeyError(f"Missing request template row for {map_row['security_key']}")

        for adjust_mode in adjust_modes:
            request_index += 1
            pair = (map_row["security_key"], adjust_mode)
            if pair in completed_pairs:
                continue
            api_error = ""
            try:
                payload = fetch_series(
                    symbol=map_row["selected_symbol"],
                    start_date=request_row["request_start_date"],
                    end_date=request_row["request_end_date"],
                    adjust_mode=adjust_mode,
                    api_key=api_key,
                )
            except HTTPError as exc:
                payload = {}
                api_error = f"HTTP {exc.code}"
                panel_rows: list[dict[str, str]] = []
            else:
                if payload.get("status") == "error":
                    api_error = str(payload.get("message", "Unknown Twelve Data API error"))
                    panel_rows = []
                else:
                    panel_rows = normalize_price_rows(
                        security_key=map_row["security_key"],
                        selected_symbol=map_row["selected_symbol"],
                        adjust_mode=adjust_mode,
                        payload=payload,
                    )

            all_panel_rows.extend(panel_rows)
            all_audit_rows.append(
                build_coverage_audit(map_row, request_row, panel_rows, adjust_mode, api_error)
            )
            completed_pairs.add(pair)
            write_csv(OUT_AUDIT_PATH, all_audit_rows)
            if all_panel_rows:
                write_csv(OUT_PANEL_PATH, all_panel_rows)

            if request_index < total_requests and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

    if not all_audit_rows:
        raise ValueError("No coverage audit rows were produced.")
    if not all_panel_rows:
        raise ValueError("No price rows were fetched. Check your API key and mapping file.")

    write_csv(OUT_PANEL_PATH, all_panel_rows)
    write_csv(OUT_AUDIT_PATH, all_audit_rows)
    print(f"Wrote {len(all_panel_rows)} rows to {OUT_PANEL_PATH}")
    print(f"Wrote {len(all_audit_rows)} rows to {OUT_AUDIT_PATH}")


if __name__ == "__main__":
    main()
