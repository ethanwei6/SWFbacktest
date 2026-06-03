from __future__ import annotations

import csv
import statistics
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_ROOT = ROOT / "data" / "processed" / "signals"
METHOD_ROOT = ROOT / "docs" / "methods"

STATE_INPUT_PATH = SIGNALS_ROOT / "swf_signal_states.csv"
STATE_MODEL_PATH = SIGNALS_ROOT / "swf_state_model.csv"
STATE_SEGMENTS_PATH = SIGNALS_ROOT / "state_segments.csv"
STATE_DURATION_SUMMARY_PATH = SIGNALS_ROOT / "state_duration_summary.csv"
AUDIT_PATH = SIGNALS_ROOT / "swf_state_model_audit.csv"
METHOD_PATH = METHOD_ROOT / "phase3-state-model.md"

COMMON_SECTORS = [
    ("communication_services", "Communication Services"),
    ("consumer_discretionary", "Consumer Discretionary"),
    ("consumer_staples", "Consumer Staples"),
    ("energy", "Energy"),
    ("financials", "Financials"),
    ("health_care", "Health Care"),
    ("industrials", "Industrials"),
    ("materials", "Materials"),
    ("real_estate", "Real Estate"),
    ("technology", "Technology"),
    ("utilities", "Utilities"),
]

SECTOR_TO_ETF = {
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
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


def to_float(value: str | float | int | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def risk_state_from_pif(exposure_state: str) -> tuple[str, str]:
    mapping = {
        "initial": ("risk_on", "1.000000000000"),
        "expanding": ("risk_on", "1.000000000000"),
        "stable": ("neutral", "0.750000000000"),
        "contracting": ("risk_off", "0.500000000000"),
        "": ("unavailable", ""),
    }
    return mapping.get(exposure_state, ("unavailable", ""))


def build_state_rows(input_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    state_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    prev_row: dict[str, str] | None = None

    for row in input_rows:
        pif_risk_state, exposure_target = risk_state_from_pif(row["pif_exposure_state"])

        consensus_sectors: list[tuple[str, float]] = []
        overweight_sectors: list[tuple[str, float]] = []
        top3_sectors: list[tuple[str, float]] = []
        all_sectors: list[tuple[str, float]] = []

        for sector_slug, sector_name in COMMON_SECTORS:
            nbim_weight = to_float(row[f"nbim_sector_weight__{sector_slug}"])
            all_sectors.append((sector_name, nbim_weight))
            if row[f"cross_fund_consensus__{sector_slug}"] == "yes":
                consensus_sectors.append((sector_name, nbim_weight))
            if row[f"nbim_sector_state__{sector_slug}"] == "overweight":
                overweight_sectors.append((sector_name, nbim_weight))
            if row[f"nbim_top3__{sector_slug}"] == "1":
                top3_sectors.append((sector_name, nbim_weight))

        consensus_sectors.sort(key=lambda item: (-item[1], item[0]))
        overweight_sectors.sort(key=lambda item: (-item[1], item[0]))
        top3_sectors.sort(key=lambda item: (-item[1], item[0]))
        all_sectors.sort(key=lambda item: (-item[1], item[0]))

        cross_count = len(consensus_sectors)
        overweight_count = len(overweight_sectors)
        top3_count = len(top3_sectors)

        if consensus_sectors:
            nbim_sector_state = "consensus_led"
            primary_sector = consensus_sectors[0][0]
            primary_weight = consensus_sectors[0][1]
            primary_source = "cross_fund_consensus"
            members = [name for name, _ in consensus_sectors]
        elif overweight_sectors:
            nbim_sector_state = "overweight_led"
            primary_sector = overweight_sectors[0][0]
            primary_weight = overweight_sectors[0][1]
            primary_source = "nbim_overweight"
            members = [name for name, _ in overweight_sectors]
        else:
            nbim_sector_state = "top3_led"
            primary_sector = top3_sectors[0][0] if top3_sectors else all_sectors[0][0]
            primary_weight = top3_sectors[0][1] if top3_sectors else all_sectors[0][1]
            primary_source = "nbim_top3"
            members = [name for name, _ in (top3_sectors or all_sectors[:3])]

        state_signature = "|".join(
            [
                pif_risk_state,
                nbim_sector_state,
                primary_sector,
                str(cross_count),
                exposure_target or "na",
            ]
        )

        change_fields: list[str] = []
        if prev_row is None:
            state_change_flag = "1"
            change_fields = ["initial_state"]
        else:
            for field in [
                "pif_risk_state",
                "nbim_sector_state",
                "model_sector_tilt_primary",
                "cross_fund_confirmation_count",
                "model_exposure_target",
            ]:
                if field == "cross_fund_confirmation_count":
                    current_value = str(cross_count)
                elif field == "model_exposure_target":
                    current_value = exposure_target
                elif field == "model_sector_tilt_primary":
                    current_value = primary_sector
                elif field == "pif_risk_state":
                    current_value = pif_risk_state
                else:
                    current_value = nbim_sector_state
                if prev_row[field] != current_value:
                    change_fields.append(field)
            state_change_flag = "1" if change_fields else "0"

        state_row = {
            "state_date": row["event_date"],
            "pif_risk_state": pif_risk_state,
            "pif_risk_state_source": row["pif_exposure_state"],
            "pif_exposure_score": row["pif_exposure_score"],
            "pif_common_equity_holding_count": row["pif_common_equity_holding_count"],
            "nbim_sector_state": nbim_sector_state,
            "nbim_overweight_count": str(overweight_count),
            "nbim_top3_count": str(top3_count),
            "cross_fund_confirmation_count": str(cross_count),
            "cross_fund_confirmation_members": "|".join(name for name, _ in consensus_sectors),
            "model_exposure_target": exposure_target,
            "model_sector_tilt_primary": primary_sector,
            "model_sector_tilt_primary_proxy": SECTOR_TO_ETF.get(primary_sector, ""),
            "model_sector_tilt_primary_weight": f"{primary_weight:.12f}",
            "model_sector_tilt_source": primary_source,
            "model_sector_tilt_members": "|".join(members),
            "state_signature": state_signature,
            "state_change_flag": state_change_flag,
            "state_change_reason": "|".join(change_fields),
        }
        state_rows.append(state_row)
        prev_row = state_row

        audit_rows.append(
            {
                "state_date": row["event_date"],
                "check_name": "cross_count_matches_members",
                "status": "pass"
                if cross_count
                == (len(state_row["cross_fund_confirmation_members"].split("|")) if state_row["cross_fund_confirmation_members"] else 0)
                else "fail",
                "detail": f"count={cross_count} members={state_row['cross_fund_confirmation_members']}",
            }
        )
        source_ok = False
        if primary_source == "cross_fund_consensus":
            source_ok = primary_sector in [name for name, _ in consensus_sectors]
        elif primary_source == "nbim_overweight":
            source_ok = primary_sector in [name for name, _ in overweight_sectors]
        elif primary_source == "nbim_top3":
            source_ok = primary_sector in [name for name, _ in (top3_sectors or all_sectors[:3])]
        audit_rows.append(
            {
                "state_date": row["event_date"],
                "check_name": "primary_sector_source_valid",
                "status": "pass" if source_ok else "fail",
                "detail": f"source={primary_source} primary={primary_sector}",
            }
        )
        expected_target = risk_state_from_pif(row["pif_exposure_state"])[1]
        audit_rows.append(
            {
                "state_date": row["event_date"],
                "check_name": "exposure_target_mapping",
                "status": "pass" if exposure_target == expected_target else "fail",
                "detail": f"actual={exposure_target} expected={expected_target}",
            }
        )

    return state_rows, audit_rows


def build_state_segments(state_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    segment_index = 1

    start_index = 0
    while start_index < len(state_rows):
        start_row = state_rows[start_index]
        end_index = start_index
        while end_index + 1 < len(state_rows) and state_rows[end_index + 1]["state_signature"] == start_row["state_signature"]:
            end_index += 1
        end_row = state_rows[end_index]
        next_state_date = state_rows[end_index + 1]["state_date"] if end_index + 1 < len(state_rows) else ""
        duration_days = (
            (parse_date(next_state_date) - parse_date(start_row["state_date"])).days if next_state_date else ""
        )
        segments.append(
            {
                "segment_id": f"SEG-{segment_index:03d}",
                "state_signature": start_row["state_signature"],
                "pif_risk_state": start_row["pif_risk_state"],
                "nbim_sector_state": start_row["nbim_sector_state"],
                "model_sector_tilt_primary": start_row["model_sector_tilt_primary"],
                "model_sector_tilt_source": start_row["model_sector_tilt_source"],
                "cross_fund_confirmation_count": start_row["cross_fund_confirmation_count"],
                "model_exposure_target": start_row["model_exposure_target"],
                "segment_start_date": start_row["state_date"],
                "segment_end_state_date": end_row["state_date"],
                "next_state_date": next_state_date,
                "segment_row_count": str(end_index - start_index + 1),
                "duration_days_to_next_state": str(duration_days) if duration_days != "" else "",
                "open_segment_flag": "0" if next_state_date else "1",
            }
        )
        segment_index += 1
        start_index = end_index + 1

    return segments


def build_duration_summary(segments: list[dict[str, str]]) -> list[dict[str, str]]:
    summary_rows: list[dict[str, str]] = []

    def summarize_group(grouping_level: str, key_name: str) -> None:
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in segments:
            grouped.setdefault(row[key_name], []).append(row)
        for key, rows in sorted(grouped.items()):
            closed = [int(r["duration_days_to_next_state"]) for r in rows if r["duration_days_to_next_state"]]
            summary_rows.append(
                {
                    "grouping_level": grouping_level,
                    "group_key": key,
                    "segment_count": str(len(rows)),
                    "closed_segment_count": str(len(closed)),
                    "open_segment_count": str(sum(1 for r in rows if r["open_segment_flag"] == "1")),
                    "avg_duration_days": f"{statistics.mean(closed):.2f}" if closed else "",
                    "median_duration_days": f"{statistics.median(closed):.2f}" if closed else "",
                    "min_duration_days": str(min(closed)) if closed else "",
                    "max_duration_days": str(max(closed)) if closed else "",
                    "avg_confirmation_count": f"{statistics.mean(int(r['cross_fund_confirmation_count']) for r in rows):.2f}",
                    "avg_exposure_target": f"{statistics.mean(to_float(r['model_exposure_target']) for r in rows if r['model_exposure_target']):.6f}" if any(r["model_exposure_target"] for r in rows) else "",
                }
            )

    summarize_group("state_signature", "state_signature")
    summarize_group("pif_risk_state", "pif_risk_state")
    summarize_group("model_sector_tilt_primary", "model_sector_tilt_primary")
    return summary_rows


def main() -> None:
    input_rows = read_csv(STATE_INPUT_PATH)
    state_rows, audit_rows = build_state_rows(input_rows)
    segments = build_state_segments(state_rows)
    duration_summary = build_duration_summary(segments)

    write_csv(STATE_MODEL_PATH, state_rows)
    write_csv(STATE_SEGMENTS_PATH, segments)
    write_csv(STATE_DURATION_SUMMARY_PATH, duration_summary)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 Workstream C: State Model\n\n"
        "This layer converts the validated cross-fund signal table into a compact state machine suitable for persistence and forward-return analysis.\n\n"
        "## Inputs\n\n"
        "- `data/processed/signals/swf_signal_states.csv`\n"
        "- `data/processed/signals/swf_combined_signal_panel.csv` (indirectly via the validated state inputs)\n\n"
        "## C1 Formal State Table\n\n"
        "The compact model is built from the already validated forward-filled signal state table.\n\n"
        "### Core fields\n\n"
        "- `state_date`\n"
        "- `pif_risk_state`\n"
        "- `nbim_sector_state`\n"
        "- `cross_fund_confirmation_count`\n"
        "- `model_exposure_target`\n"
        "- `model_sector_tilt_primary`\n"
        "- `state_change_flag`\n"
        "- `state_change_reason`\n\n"
        "### Mapping rules\n\n"
        "- `PIF initial` and `PIF expanding` map to `risk_on` with target exposure `1.00`\n"
        "- `PIF stable` maps to `neutral` with target exposure `0.75`\n"
        "- `PIF contracting` maps to `risk_off` with target exposure `0.50`\n"
        "- if any cross-fund consensus sectors exist, the model becomes `consensus_led` and the highest-weight consensus sector becomes the primary tilt\n"
        "- otherwise, if any `NBIM overweight` sectors exist, the model becomes `overweight_led` and the highest-weight overweight sector becomes the primary tilt\n"
        "- otherwise, the model becomes `top3_led` and the highest-weight current `NBIM` top-3 sector becomes the primary tilt\n\n"
        "## C2 Persistence Analysis\n\n"
        "State segments are formed by contiguous rows with identical `state_signature`. Segment duration is measured in calendar days from the segment start date to the next state's date.\n\n"
        "## Outputs\n\n"
        "- `data/processed/signals/swf_state_model.csv`\n"
        "- `data/processed/signals/state_segments.csv`\n"
        "- `data/processed/signals/state_duration_summary.csv`\n"
        "- `data/processed/signals/swf_state_model_audit.csv`\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
