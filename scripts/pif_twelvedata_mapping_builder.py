from __future__ import annotations

import csv
import json
import os
import re
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "pif" / "pif_price_security_master.csv"
OUT_CANDIDATES_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_mapping_candidates.csv"
OUT_MAP_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_security_map.csv"

API_BASE = "https://api.twelvedata.com"
OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
DEFAULT_SECONDS_BETWEEN_REQUESTS = 0.5
OUTPUTSIZE = 10
AUTO_APPROVE_SCORE = 13
OPENFIGI_BATCH_SIZE = 5

ALLOWED_TYPES = {
    "Common Stock",
    "American Depositary Receipt",
    "Depositary Receipt",
    "REIT",
    "ETF",
    "Trust",
}

COMMON_SUFFIXES = {
    "INC",
    "INCORPORATED",
    "CORP",
    "CORPORATION",
    "LTD",
    "LIMITED",
    "PLC",
    "NV",
    "N V",
    "SA",
    "S A",
    "HLDG",
    "HLDGS",
    "HOLDING",
    "HOLDINGS",
    "GROUP",
    "CO",
    "COMPANY",
    "NEW",
}


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


def normalize_name(value: str) -> str:
    upper = value.upper()
    upper = upper.replace("&", " AND ")
    upper = re.sub(r"[^A-Z0-9 ]+", " ", upper)
    tokens = [token for token in upper.split() if token and token not in COMMON_SUFFIXES]
    return " ".join(tokens)


def build_query_name(issuer_name: str) -> str:
    normalized = normalize_name(issuer_name)
    return normalized if normalized else issuer_name


def fallback_query_names(issuer_name: str) -> list[str]:
    base = build_query_name(issuer_name)
    queries = [base]
    tokens = base.split()
    if len(tokens) >= 2:
        queries.append(" ".join(tokens[:2]))
    if len(tokens) >= 1:
        queries.append(tokens[0])
    seen: set[str] = set()
    deduped: list[str] = []
    for query in queries:
        query = query.strip()
        if query and query not in seen:
            deduped.append(query)
            seen.add(query)
    return deduped


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: Any) -> Any:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_args() -> Namespace:
    parser = ArgumentParser()
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
        help="Optional limit on number of securities to process.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing candidates file if present.",
    )
    return parser.parse_args()


def score_candidate(master_row: dict[str, str], candidate: dict[str, Any]) -> int:
    score = 0
    master_name = normalize_name(master_row["issuer_name"])
    candidate_name = normalize_name(str(candidate.get("instrument_name", "")))
    candidate_symbol = str(candidate.get("symbol", ""))
    candidate_country = str(candidate.get("country", ""))
    candidate_type = str(candidate.get("instrument_type", candidate.get("type", "")))
    candidate_exchange = str(candidate.get("exchange", ""))

    if candidate_country in {"United States", "US"}:
        score += 3
    if candidate_exchange in {"NASDAQ", "NYSE", "NYSE ARCA", "NYSE AMERICAN"}:
        score += 3
    if candidate_type in ALLOWED_TYPES:
        score += 2
    if master_name and candidate_name == master_name:
        score += 8
    elif master_name and candidate_name.startswith(master_name):
        score += 5
    elif master_name and master_name in candidate_name:
        score += 3

    if master_row["title_of_class"] == "SPONSORED ADS" and "ADR" in candidate_type.upper():
        score += 1
    if master_row["title_of_class"] == "SPONSORED ADS" and "DEPOSITARY" in candidate_type.upper():
        score += 1
    if master_row["title_of_class"] == "COM" and candidate_type == "Common Stock":
        score += 1
    if master_row["title_of_class"] == "CAP STK CL A" and candidate_symbol == "GOOGL":
        score += 3
    if master_row["title_of_class"] == "CAP STK CL A" and candidate_symbol == "GOOG":
        score -= 1
    if "." in candidate_symbol:
        score -= 1
    return score


def fetch_candidates_for_row(master_row: dict[str, str], api_key: str) -> list[dict[str, str]]:
    query_names = fallback_query_names(master_row["issuer_name"])
    data: list[dict[str, Any]] = []
    query_name = query_names[0]
    seen_pairs: set[tuple[str, str]] = set()
    for query_name in query_names:
        query = urlencode(
            {
                "symbol": query_name,
                "outputsize": str(OUTPUTSIZE),
                "apikey": api_key,
            }
        )
        payload = fetch_json(f"{API_BASE}/symbol_search?{query}")
        raw_rows = payload.get("data", [])
        for raw_candidate in raw_rows:
            pair = (
                str(raw_candidate.get("symbol", "")),
                str(raw_candidate.get("exchange", "")),
            )
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            data.append(raw_candidate)
        if data:
            break
    candidates: list[dict[str, str]] = []
    for raw_candidate in data:
        score = score_candidate(master_row, raw_candidate)
        candidates.append(
            {
                "security_key": master_row["security_key"],
                "issuer_name": master_row["issuer_name"],
                "cusip": master_row["cusip"],
                "title_of_class": master_row["title_of_class"],
                "baseline_price_eligible_flag": master_row["baseline_price_eligible_flag"],
                "query_name": query_name,
                "candidate_symbol": str(raw_candidate.get("symbol", "")),
                "candidate_instrument_name": str(raw_candidate.get("instrument_name", "")),
                "candidate_exchange": str(raw_candidate.get("exchange", "")),
                "candidate_mic_code": str(raw_candidate.get("mic_code", "")),
                "candidate_country": str(raw_candidate.get("country", "")),
                "candidate_type": str(raw_candidate.get("instrument_type", raw_candidate.get("type", ""))),
                "candidate_currency": str(raw_candidate.get("currency", "")),
                "candidate_score": str(score),
            }
        )
    candidates.sort(key=lambda row: int(row["candidate_score"]), reverse=True)
    for idx, row in enumerate(candidates, start=1):
        row["candidate_rank"] = str(idx)
    return candidates


def build_security_map(master_rows: list[dict[str, str]], candidates_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_security: dict[str, list[dict[str, str]]] = {}
    for row in candidates_rows:
        by_security.setdefault(row["security_key"], []).append(row)

    out: list[dict[str, str]] = []
    for master_row in master_rows:
        security_key = master_row["security_key"]
        candidates = by_security.get(security_key, [])
        top = candidates[0] if candidates else None
        out.append(
            {
                "security_key": security_key,
                "issuer_name": master_row["issuer_name"],
                "cusip": master_row["cusip"],
                "title_of_class": master_row["title_of_class"],
                "baseline_price_eligible_flag": master_row["baseline_price_eligible_flag"],
                "eligibility_note": master_row.get("eligibility_note", ""),
                "selected_symbol": top["candidate_symbol"] if top else "",
                "selected_exchange": top["candidate_exchange"] if top else "",
                "selected_type": top["candidate_type"] if top else "",
                "selected_country": top["candidate_country"] if top else "",
                "selected_score": top["candidate_score"] if top else "",
                "mapping_status": "needs_review" if top else "no_candidate",
                "mapping_notes": "",
            }
        )
    return out


def needs_openfigi_fallback(candidates: list[dict[str, str]]) -> bool:
    if not candidates:
        return True
    top = candidates[0]
    top_score = int(top["candidate_score"]) if top["candidate_score"] else 0
    top_type = top["candidate_type"]
    top_country = top["candidate_country"]
    if top_score < AUTO_APPROVE_SCORE:
        return True
    if top_country not in {"United States", "US"}:
        return True
    if top_type not in {"Common Stock", "American Depositary Receipt", "Depositary Receipt", "REIT"}:
        return True
    return False


def fetch_openfigi_lookup(master_rows: list[dict[str, str]], candidates_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    candidates_by_security: dict[str, list[dict[str, str]]] = {}
    for row in candidates_rows:
        candidates_by_security.setdefault(row["security_key"], []).append(row)

    jobs: list[dict[str, str]] = []
    security_keys: list[str] = []
    for master_row in master_rows:
        security_key = master_row["security_key"]
        if not needs_openfigi_fallback(candidates_by_security.get(security_key, [])):
            continue
        cusip = master_row["cusip"].strip()
        if not cusip:
            continue
        jobs.append({"idType": "ID_CUSIP", "idValue": cusip})
        security_keys.append(security_key)

    if not jobs:
        return {}
    out: dict[str, dict[str, str]] = {}

    for start in range(0, len(jobs), OPENFIGI_BATCH_SIZE):
        batch_jobs = jobs[start : start + OPENFIGI_BATCH_SIZE]
        batch_keys = security_keys[start : start + OPENFIGI_BATCH_SIZE]
        response = post_json(OPENFIGI_URL, batch_jobs)
        for security_key, entry in zip(batch_keys, response):
            rows = entry.get("data", [])
            best = None
            best_score = None
            for row in rows:
                score = 0
                if row.get("marketSector") == "Equity":
                    score += 3
                if row.get("exchCode") == "US":
                    score += 3
                if row.get("securityType") in {"Common Stock", "ADR"}:
                    score += 2
                if row.get("securityType2") in {"Depositary Receipt", "Common Stock"}:
                    score += 1
                if best_score is None or score > best_score:
                    best = row
                    best_score = score
            if best is not None:
                out[security_key] = {
                    "ticker": str(best.get("ticker", "")),
                    "exch_code": str(best.get("exchCode", "")),
                    "name": str(best.get("name", "")),
                    "security_type": str(best.get("securityType", "")),
                    "security_type2": str(best.get("securityType2", "")),
                    "score": str(best_score if best_score is not None else 0),
                }
    return out


def build_final_security_map(
    master_rows: list[dict[str, str]],
    candidates_rows: list[dict[str, str]],
    openfigi_lookup: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    by_security: dict[str, list[dict[str, str]]] = {}
    for row in candidates_rows:
        by_security.setdefault(row["security_key"], []).append(row)

    out: list[dict[str, str]] = []
    for master_row in master_rows:
        security_key = master_row["security_key"]
        candidates = by_security.get(security_key, [])
        top = candidates[0] if candidates else None
        top_score = int(top["candidate_score"]) if top and top["candidate_score"] else 0
        use_openfigi = False
        if security_key in openfigi_lookup:
            if top is None or needs_openfigi_fallback(candidates):
                use_openfigi = True

        if use_openfigi:
            mapped = openfigi_lookup[security_key]
            selected_symbol = mapped["ticker"]
            selected_exchange = mapped["exch_code"]
            selected_type = mapped["security_type"] or mapped["security_type2"]
            selected_country = "United States" if mapped["exch_code"] == "US" else ""
            selected_score = mapped["score"]
            mapping_source = "openfigi_cusip"
            is_clean_us_symbol = (
                selected_symbol.isupper()
                and selected_symbol.replace(".", "").replace("-", "").isalnum()
                and len(selected_symbol) <= 5
                and mapped["exch_code"] == "US"
            )
            mapping_status = (
                "auto_approved" if selected_symbol and is_clean_us_symbol else "needs_review" if selected_symbol else "no_candidate"
            )
            mapping_notes = "Auto-selected from OpenFIGI CUSIP mapping." if selected_symbol else ""
        else:
            selected_symbol = top["candidate_symbol"] if top else ""
            selected_exchange = top["candidate_exchange"] if top else ""
            selected_type = top["candidate_type"] if top else ""
            selected_country = top["candidate_country"] if top else ""
            selected_score = top["candidate_score"] if top else ""
            mapping_source = "twelvedata_search" if top else ""
            mapping_status = (
                "auto_approved"
                if top and top_score >= AUTO_APPROVE_SCORE and selected_country in {"United States", "US"}
                else "needs_review" if top else "no_candidate"
            )
            mapping_notes = ""

        out.append(
            {
                "security_key": security_key,
                "issuer_name": master_row["issuer_name"],
                "cusip": master_row["cusip"],
                "title_of_class": master_row["title_of_class"],
                "baseline_price_eligible_flag": master_row["baseline_price_eligible_flag"],
                "eligibility_note": master_row.get("eligibility_note", ""),
                "selected_symbol": selected_symbol,
                "selected_exchange": selected_exchange,
                "selected_type": selected_type,
                "selected_country": selected_country,
                "selected_score": selected_score,
                "mapping_source": mapping_source,
                "mapping_status": mapping_status,
                "mapping_notes": mapping_notes,
            }
        )
    return out


def existing_candidates_by_security() -> dict[str, list[dict[str, str]]]:
    if not OUT_CANDIDATES_PATH.exists():
        return {}
    rows = read_csv(OUT_CANDIDATES_PATH)
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["security_key"], []).append(row)
    return out


def main() -> None:
    args = parse_args()
    api_key = args.api_key.strip() or load_api_key()
    master_rows = [
        row for row in read_csv(MASTER_PATH) if row["baseline_price_eligible_flag"] == "1"
    ]
    if args.limit > 0:
        master_rows = master_rows[: args.limit]

    resumed = existing_candidates_by_security() if args.resume else {}
    all_candidates: list[dict[str, str]] = []
    for security_key in sorted(resumed):
        all_candidates.extend(resumed[security_key])

    for idx, master_row in enumerate(master_rows, start=1):
        if master_row["security_key"] in resumed:
            continue
        candidates = fetch_candidates_for_row(master_row, api_key)
        if not candidates:
            all_candidates.append(
                {
                    "security_key": master_row["security_key"],
                    "issuer_name": master_row["issuer_name"],
                    "cusip": master_row["cusip"],
                    "title_of_class": master_row["title_of_class"],
                    "baseline_price_eligible_flag": master_row["baseline_price_eligible_flag"],
                    "query_name": build_query_name(master_row["issuer_name"]),
                    "candidate_symbol": "",
                    "candidate_instrument_name": "",
                    "candidate_exchange": "",
                    "candidate_mic_code": "",
                    "candidate_country": "",
                    "candidate_type": "",
                    "candidate_currency": "",
                    "candidate_score": "",
                    "candidate_rank": "",
                }
            )
        else:
            all_candidates.extend(candidates)

        write_csv(OUT_CANDIDATES_PATH, all_candidates)
        map_rows = build_security_map(master_rows, all_candidates)
        write_csv(OUT_MAP_PATH, map_rows)

        if idx < len(master_rows) and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    openfigi_lookup = fetch_openfigi_lookup(master_rows, all_candidates)
    map_rows = build_final_security_map(master_rows, all_candidates, openfigi_lookup)
    write_csv(OUT_CANDIDATES_PATH, all_candidates)
    write_csv(OUT_MAP_PATH, map_rows)
    print(f"Wrote {len(all_candidates)} rows to {OUT_CANDIDATES_PATH}")
    print(f"Wrote {len(map_rows)} rows to {OUT_MAP_PATH}")


if __name__ == "__main__":
    main()
