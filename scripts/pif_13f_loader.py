from __future__ import annotations

import csv
import statistics
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "pif" / "13f"
OUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings.csv"
ALL_OUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_holdings_all_filings.csv"
FILING_INDEX_PATH = ROOT / "data" / "processed" / "pif" / "pif_13f_filing_index.csv"


ACCESSION_RE = re.compile(r"^\d{18}$")

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
    "accession_number",
    "submission_type",
    "filer_cik",
    "filer_name",
    "title_of_class",
    "value_thousands_usd",
    "value_scale_factor",
    "share_type",
    "put_call",
    "investment_discretion",
    "other_manager",
    "voting_authority_sole",
    "voting_authority_shared",
    "voting_authority_none",
]


@dataclass(frozen=True)
class FilingMeta:
    accession_number: str
    filing_date: str
    period_of_report: str
    filer_name: str
    filer_cik: str
    submission_type: str
    source_url: str
    table_entry_total: str
    table_value_total_thousands: str


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def parse_date_token(text: str) -> str:
    token = clean_text(text)
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", token):
        month, day, year = token.split("-")
        return f"{year}-{month}-{day}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token
    return token


def strip_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def xml_text_lookup(root: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for element in root.iter():
        key = strip_tag(element.tag)
        text = clean_text(element.text)
        if text and key not in values:
            values[key] = text
    return values


def load_primary_doc(path: Path, accession_number: str) -> FilingMeta:
    root = ET.parse(path).getroot()
    values = xml_text_lookup(root)

    filing_date = parse_date_token(values.get("signatureDate") or values.get("periodOfReport"))
    period_of_report = parse_date_token(
        values.get("reportCalendarOrQuarter") or values.get("periodOfReport")
    )
    filer_name = values.get("name", "")
    filer_cik = values.get("cik", "")
    submission_type = values.get("submissionType", "13F-HR")
    table_entry_total = values.get("tableEntryTotal", "")
    table_value_total_thousands = values.get("tableValueTotal", "")

    if not period_of_report:
        raise ValueError(f"Could not find period of report in {path}")

    source_url = f"https://www.sec.gov/Archives/edgar/data/1767640/{accession_number}/"
    return FilingMeta(
        accession_number=accession_number,
        filing_date=filing_date,
        period_of_report=period_of_report,
        filer_name=filer_name or "PUBLIC INVESTMENT FUND",
        filer_cik=filer_cik or "0001767640",
        submission_type=submission_type,
        source_url=source_url,
        table_entry_total=table_entry_total,
        table_value_total_thousands=table_value_total_thousands,
    )


def iter_info_tables(root: ET.Element) -> list[ET.Element]:
    info_tables = [element for element in root.iter() if strip_tag(element.tag) == "infoTable"]
    if info_tables:
        return info_tables

    if strip_tag(root.tag) == "infoTable":
        return [root]

    raise ValueError("No infoTable elements found")


def child_text(element: ET.Element, child_name: str) -> str:
    for child in element:
        if strip_tag(child.tag) == child_name:
            return clean_text(child.text)
    return ""


def nested_text(element: ET.Element, child_name: str, grandchild_name: str) -> str:
    for child in element:
        if strip_tag(child.tag) == child_name:
            for grandchild in child:
                if strip_tag(grandchild.tag) == grandchild_name:
                    return clean_text(grandchild.text)
    return ""


def load_information_table(path: Path, meta: FilingMeta) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    info_tables = iter_info_tables(root)
    scale_factor = detect_value_scale_factor(info_tables)
    rows: list[dict[str, str]] = []

    for index, info in enumerate(info_tables, start=1):
        shares = nested_text(info, "shrsOrPrnAmt", "sshPrnamt")
        value_thousands = child_text(info, "value")
        share_type = nested_text(info, "shrsOrPrnAmt", "sshPrnamtType")
        voting_sole = nested_text(info, "votingAuthority", "Sole")
        voting_shared = nested_text(info, "votingAuthority", "Shared")
        voting_none = nested_text(info, "votingAuthority", "None")

        row = {column: "" for column in OUTPUT_COLUMNS}
        row["fund"] = "PIF"
        row["issuer_name"] = child_text(info, "nameOfIssuer")
        row["security_name"] = row["issuer_name"]
        row["cusip"] = child_text(info, "cusip")
        row["asset_type"] = "public_equity_13f"
        row["position_type"] = "long_equity_13f"
        row["shares"] = shares
        row["market_value_usd"] = (
            f"{float(value_thousands) * scale_factor:.0f}" if value_thousands else ""
        )
        row["as_of_date"] = meta.period_of_report
        row["public_date"] = meta.filing_date
        row["filing_date"] = meta.filing_date
        row["effective_date"] = meta.period_of_report
        row["disclosure_channel"] = "SEC_13F"
        row["source_name"] = "SEC Form 13F Information Table"
        row["source_url"] = meta.source_url
        row["jurisdiction"] = "United States"
        row["visibility_class"] = "partial"
        row["observability"] = "observed"
        row["confidence_level"] = "high"
        row["event_type"] = "snapshot"
        row["event_notes"] = "PIF US-reportable 13F holding."
        row["source_row_id"] = f"{meta.accession_number}:{index}"
        row["accession_number"] = meta.accession_number
        row["submission_type"] = meta.submission_type
        row["filer_cik"] = meta.filer_cik
        row["filer_name"] = meta.filer_name
        row["title_of_class"] = child_text(info, "titleOfClass")
        row["value_thousands_usd"] = value_thousands
        row["value_scale_factor"] = f"{scale_factor:.0f}"
        row["share_type"] = share_type
        row["put_call"] = child_text(info, "putCall")
        row["investment_discretion"] = child_text(info, "investmentDiscretion")
        row["other_manager"] = child_text(info, "otherManager")
        row["voting_authority_sole"] = voting_sole
        row["voting_authority_shared"] = voting_shared
        row["voting_authority_none"] = voting_none
        rows.append(row)

    return rows


def detect_value_scale_factor(info_tables: list[ET.Element]) -> float:
    implied_prices_direct: list[float] = []
    for info in info_tables:
        shares_text = nested_text(info, "shrsOrPrnAmt", "sshPrnamt")
        value_text = child_text(info, "value")
        if not shares_text or not value_text:
            continue
        shares = float(shares_text)
        value = float(value_text)
        if shares <= 0:
            continue
        implied_prices_direct.append(value / shares)

    if not implied_prices_direct:
        return 1000.0

    median_direct = statistics.median(implied_prices_direct)
    if median_direct < 1.0:
        return 1000.0
    return 1.0


def find_primary_doc(filing_dir: Path) -> Path:
    path = filing_dir / "primary_doc.xml"
    if path.exists():
        return path
    raise FileNotFoundError(f"Missing primary_doc.xml in {filing_dir}")


def find_information_table(filing_dir: Path) -> Path:
    candidates = []
    for path in filing_dir.glob("*.xml"):
        if path.name == "primary_doc.xml":
            continue
        candidates.append(path)

    if len(candidates) == 1:
        return candidates[0]

    for path in candidates:
        if "informationtable" in path.name.lower() or "infotable" in path.name.lower():
            return path

    raise FileNotFoundError(f"Could not uniquely identify information table xml in {filing_dir}")


def filing_dirs() -> list[Path]:
    dirs = [path for path in RAW_DIR.iterdir() if path.is_dir() and ACCESSION_RE.match(path.name)]
    return sorted(dirs)


def filing_sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    return (
        row["filing_date"],
        1 if row["submission_type"].endswith("/A") else 0,
        row["accession_number"],
    )


def canonical_accession_numbers(filing_index_rows: list[dict[str, str]]) -> set[str]:
    chosen: dict[str, dict[str, str]] = {}
    for row in filing_index_rows:
        period = row["period_of_report"]
        current = chosen.get(period)
        if current is None or filing_sort_key(row) > filing_sort_key(current):
            chosen[period] = row
    return {row["accession_number"] for row in chosen.values()}


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw directory not found: {RAW_DIR}")

    dirs = filing_dirs()
    if not dirs:
        raise FileNotFoundError(f"No accession folders found in {RAW_DIR}")

    rows: list[dict[str, str]] = []
    filing_index_rows: list[dict[str, str]] = []
    for filing_dir in dirs:
        accession_number = filing_dir.name
        primary_doc = find_primary_doc(filing_dir)
        info_table = find_information_table(filing_dir)
        meta = load_primary_doc(primary_doc, accession_number)
        filing_rows = load_information_table(info_table, meta)
        rows.extend(filing_rows)
        filing_index_rows.append(
            {
                "period_of_report": meta.period_of_report,
                "filing_date": meta.filing_date,
                "accession_number": meta.accession_number,
                "submission_type": meta.submission_type,
                "is_amendment": "1" if meta.submission_type.endswith("/A") else "0",
                "filer_cik": meta.filer_cik,
                "filer_name": meta.filer_name,
                "row_count": str(len(filing_rows)),
                "table_entry_total": meta.table_entry_total,
                "table_value_total_thousands": meta.table_value_total_thousands,
                "source_url": meta.source_url,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALL_OUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    canonical_accessions = canonical_accession_numbers(filing_index_rows)
    canonical_rows = [row for row in rows if row["accession_number"] in canonical_accessions]

    with OUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(canonical_rows)

    filing_index_rows.sort(
        key=lambda row: (
            row["period_of_report"],
            row["filing_date"],
            row["submission_type"],
            row["accession_number"],
        )
    )
    for row in filing_index_rows:
        row["keep_flag"] = "1" if row["accession_number"] in canonical_accessions else "0"

    with FILING_INDEX_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(filing_index_rows[0].keys()))
        writer.writeheader()
        writer.writerows(filing_index_rows)

    print(f"Wrote {len(rows)} rows from {len(dirs)} filings to {ALL_OUT_PATH}")
    print(f"Wrote {len(canonical_rows)} canonical rows to {OUT_PATH}")
    print(f"Wrote filing index to {FILING_INDEX_PATH}")


if __name__ == "__main__":
    main()
