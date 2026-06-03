from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIF_ROOT = ROOT / "data" / "processed" / "pif"
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
SIGNALS_ROOT = ROOT / "data" / "processed" / "signals"

PIF_EXPOSURE_PATH = PIF_ROOT / "pif_sector_exposure_common.csv"
PIF_CHANGE_PATH = PIF_ROOT / "pif_sector_change_common.csv"
NBIM_SNAPSHOT_PATH = NBIM_ROOT / "nbim_snapshot_sector_common.csv"
NBIM_TRANSITION_PATH = NBIM_ROOT / "nbim_transition_sector_common.csv"

SIGNAL_PANEL_PATH = SIGNALS_ROOT / "swf_combined_signal_panel.csv"
STATE_TABLE_PATH = SIGNALS_ROOT / "swf_signal_states.csv"
CONSTRUCTION_AUDIT_PATH = SIGNALS_ROOT / "signal_construction_audit.csv"
TIMING_AUDIT_PATH = SIGNALS_ROOT / "timing_audit.csv"

COMMON_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Materials",
    "Real Estate",
    "Technology",
    "Utilities",
]

PIF_EXPANDING_COUNT_PCT = 0.15
PIF_EXPANDING_FLOW_SCORE = 5
PIF_SECTOR_WEIGHT_CHANGE_THRESHOLD = 0.02
NBIM_WEIGHT_CHANGE_THRESHOLD = 0.005


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


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace("/", "_")
        .replace("-", "_")
    )


def build_pif_period_data() -> tuple[dict[str, dict[str, object]], list[dict[str, str]]]:
    exposure_rows = read_csv(PIF_EXPOSURE_PATH)
    change_rows = read_csv(PIF_CHANGE_PATH)

    period_data: dict[str, dict[str, object]] = {}
    for row in exposure_rows:
        period = row["as_of_date"]
        bucket = period_data.setdefault(
            period,
            {
                "as_of_date": period,
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
                "holding_count": 0.0,
                "sector_weights": {},
            },
        )
        bucket["holding_count"] += to_float(row["holding_count"])
        bucket["sector_weights"][row["common_sector"]] = to_float(row["portfolio_weight_after"])

    change_by_curr: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in change_rows:
        change_by_curr[row["curr_as_of_date"]].append(row)

    signals: list[dict[str, str]] = []
    ordered_periods = sorted(period_data)
    prev_holding_count = 0.0
    for idx, period in enumerate(ordered_periods):
        period_entry = period_data[period]
        current_count = float(period_entry["holding_count"])
        changes = change_by_curr.get(period, [])
        total_entries = sum(int(row["entry_count"]) for row in changes)
        total_exits = sum(int(row["exit_count"]) for row in changes)
        total_accum = sum(int(row["accumulation_count"]) for row in changes)
        total_reduct = sum(int(row["reduction_count"]) for row in changes)
        flow_score = total_entries + total_accum - total_exits - total_reduct
        count_change_pct = ((current_count - prev_holding_count) / prev_holding_count) if idx and prev_holding_count else 0.0

        if idx == 0:
            exposure_state = "initial"
        elif count_change_pct >= PIF_EXPANDING_COUNT_PCT or flow_score >= PIF_EXPANDING_FLOW_SCORE:
            exposure_state = "expanding"
        elif count_change_pct <= -PIF_EXPANDING_COUNT_PCT or flow_score <= -PIF_EXPANDING_FLOW_SCORE:
            exposure_state = "contracting"
        else:
            exposure_state = "stable"

        exposure_strength = max(min(abs(count_change_pct), 1.0), abs(flow_score) / 10.0)
        period_entry["pif_exposure_state"] = exposure_state
        period_entry["pif_exposure_score"] = exposure_strength
        period_entry["pif_flow_score"] = flow_score
        period_entry["pif_count_change_pct"] = count_change_pct
        period_entry["pif_sector_states"] = {}
        period_entry["pif_sector_scores"] = {}

        signals.append(
            {
                "signal_date": str(period_entry["public_date"]),
                "effective_trade_date": str(period_entry["trade_date"]),
                "fund": "PIF",
                "signal_family": "pif_exposure",
                "signal_name": "visible_sleeve_regime",
                "signal_direction": exposure_state,
                "signal_strength": f"{exposure_strength:.8f}",
                "target_level": f"{current_count:.0f}",
                "source_snapshot": period,
                "source_public_date": str(period_entry["public_date"]),
                "staleness_days": str((parse_date(period_entry["public_date"]) - parse_date(period)).days),
                "sector": "",
                "industry": "",
                "security_key": "",
                "confidence_level": "medium",
                "notes": f"holding_count={int(current_count)}; flow_score={flow_score}; count_change_pct={count_change_pct:.6f}",
            }
        )

        for sector in COMMON_SECTORS:
            sector_change = next((row for row in changes if row["common_sector"] == sector), None)
            if sector_change is None:
                state = "neutral"
                strength = 0.0
                target_level = to_float(period_entry["sector_weights"].get(sector, 0.0))
                notes = "No sector-specific filing delta for this period."
            else:
                weight_change = to_float(sector_change["net_weight_change"])
                flow = (
                    int(sector_change["entry_count"])
                    + int(sector_change["accumulation_count"])
                    - int(sector_change["exit_count"])
                    - int(sector_change["reduction_count"])
                )
                target_level = to_float(sector_change["weight_after"])
                if flow > 0 or weight_change > PIF_SECTOR_WEIGHT_CHANGE_THRESHOLD:
                    state = "positive"
                elif flow < 0 or weight_change < -PIF_SECTOR_WEIGHT_CHANGE_THRESHOLD:
                    state = "negative"
                else:
                    state = "neutral"
                strength = abs(weight_change) + (abs(flow) / 10.0)
                notes = f"net_weight_change={weight_change:.6f}; flow_score={flow}"

            period_entry["pif_sector_states"][sector] = state
            period_entry["pif_sector_scores"][sector] = strength
            signals.append(
                {
                    "signal_date": str(period_entry["public_date"]),
                    "effective_trade_date": str(period_entry["trade_date"]),
                    "fund": "PIF",
                    "signal_family": "pif_sector_proxy",
                    "signal_name": "sector_rotation_proxy",
                    "signal_direction": state,
                    "signal_strength": f"{strength:.8f}",
                    "target_level": f"{target_level:.8f}",
                    "source_snapshot": period,
                    "source_public_date": str(period_entry["public_date"]),
                    "staleness_days": str((parse_date(period_entry["public_date"]) - parse_date(period)).days),
                    "sector": sector,
                    "industry": "",
                    "security_key": "",
                    "confidence_level": "medium" if state != "neutral" else "low",
                    "notes": notes,
                }
            )

        prev_holding_count = current_count

    return period_data, signals


def build_nbim_period_data() -> tuple[dict[str, dict[str, object]], list[dict[str, str]]]:
    snapshot_rows = read_csv(NBIM_SNAPSHOT_PATH)
    transition_rows = read_csv(NBIM_TRANSITION_PATH)

    period_data: dict[str, dict[str, object]] = {}
    for row in snapshot_rows:
        period = row["as_of_date"]
        bucket = period_data.setdefault(
            period,
            {
                "as_of_date": period,
                "public_date": row["public_date"],
                "trade_date": row["trade_date"],
                "report_type": row["report_type"],
                "sector_weights": {},
            },
        )
        bucket["sector_weights"][row["common_sector"]] = to_float(row["portfolio_weight_usd"])

    transition_by_curr: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in transition_rows:
        transition_by_curr[row["curr_as_of_date"]].append(row)

    signals: list[dict[str, str]] = []
    for period in sorted(period_data):
        period_entry = period_data[period]
        weights = period_entry["sector_weights"]
        top3 = {sector for sector, _ in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:3]}
        period_entry["nbim_sector_states"] = {}
        period_entry["nbim_sector_scores"] = {}
        period_entry["nbim_top3"] = {}

        for sector in COMMON_SECTORS:
            weight = float(weights.get(sector, 0.0))
            top3_flag = sector in top3
            period_entry["nbim_top3"][sector] = top3_flag
            concentration_state = "top3" if top3_flag else "not_top3"
            signals.append(
                {
                    "signal_date": str(period_entry["public_date"]),
                    "effective_trade_date": str(period_entry["trade_date"]),
                    "fund": "NBIM",
                    "signal_family": "nbim_industry_concentration",
                    "signal_name": "top_sector_concentration",
                    "signal_direction": concentration_state,
                    "signal_strength": f"{weight:.8f}",
                    "target_level": f"{weight:.8f}",
                    "source_snapshot": period,
                    "source_public_date": str(period_entry["public_date"]),
                    "staleness_days": str((parse_date(period_entry["public_date"]) - parse_date(period)).days),
                    "sector": sector,
                    "industry": "",
                    "security_key": "",
                    "confidence_level": "high" if top3_flag else "low",
                    "notes": "Sector ranked in current top-3 NBIM weights." if top3_flag else "Sector not in current NBIM top-3 weights.",
                }
            )

        transitions = transition_by_curr.get(period, [])
        for sector in COMMON_SECTORS:
            row = next((item for item in transitions if item["common_sector"] == sector), None)
            if row is None:
                state = "neutral"
                strength = 0.0
                target_level = float(weights.get(sector, 0.0))
                notes = "No prior-period NBIM weight-change row for this sector."
            else:
                weight_change = to_float(row["total_delta_market_value_usd"])
                sector_weight_change = to_float(row["entry_observed"])  # placeholder overwritten below
                sector_weight_change = 0.0
                # Use portfolio-weight deltas from the normalized sector tables as the directional measure.
                # We reconstruct this from snapshot weights to avoid mixing raw market-value changes with price drift.
                prev_period = row["prev_as_of_date"]
                prev_weight = to_float(period_data.get(prev_period, {}).get("sector_weights", {}).get(sector, 0.0))
                curr_weight = to_float(weights.get(sector, 0.0))
                sector_weight_change = curr_weight - prev_weight
                if sector_weight_change > NBIM_WEIGHT_CHANGE_THRESHOLD:
                    state = "overweight"
                elif sector_weight_change < -NBIM_WEIGHT_CHANGE_THRESHOLD:
                    state = "underweight"
                else:
                    state = "neutral"
                strength = abs(sector_weight_change)
                target_level = curr_weight
                notes = (
                    f"weight_change={sector_weight_change:.6f}; "
                    f"accumulations={row['likely_accumulation']}; reductions={row['likely_reduction']}"
                )

            period_entry["nbim_sector_states"][sector] = state
            period_entry["nbim_sector_scores"][sector] = strength
            signals.append(
                {
                    "signal_date": str(period_entry["public_date"]),
                    "effective_trade_date": str(period_entry["trade_date"]),
                    "fund": "NBIM",
                    "signal_family": "nbim_industry_weight_change",
                    "signal_name": "sector_weight_change",
                    "signal_direction": state,
                    "signal_strength": f"{strength:.8f}",
                    "target_level": f"{target_level:.8f}",
                    "source_snapshot": period,
                    "source_public_date": str(period_entry["public_date"]),
                    "staleness_days": str((parse_date(period_entry["public_date"]) - parse_date(period)).days),
                    "sector": sector,
                    "industry": "",
                    "security_key": "",
                    "confidence_level": "high" if state != "neutral" else "medium",
                    "notes": notes,
                }
            )

    return period_data, signals


def build_state_table(
    pif_period_data: dict[str, dict[str, object]],
    nbim_period_data: dict[str, dict[str, object]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    pif_by_trade = {value["trade_date"]: value for value in pif_period_data.values()}
    nbim_by_trade = {value["trade_date"]: value for value in nbim_period_data.values()}
    event_dates = sorted(set(pif_by_trade) | set(nbim_by_trade))

    latest_pif: dict[str, object] | None = None
    latest_nbim: dict[str, object] | None = None
    state_rows: list[dict[str, str]] = []
    consensus_rows: list[dict[str, str]] = []

    for event_date in event_dates:
        if event_date in pif_by_trade:
            latest_pif = pif_by_trade[event_date]
        if event_date in nbim_by_trade:
            latest_nbim = nbim_by_trade[event_date]

        row: dict[str, str] = {
            "event_date": event_date,
            "pif_trade_date_active": str(latest_pif["trade_date"]) if latest_pif else "",
            "nbim_trade_date_active": str(latest_nbim["trade_date"]) if latest_nbim else "",
            "pif_exposure_state": str(latest_pif["pif_exposure_state"]) if latest_pif else "",
            "pif_exposure_score": f"{float(latest_pif['pif_exposure_score']):.8f}" if latest_pif else "",
            "pif_common_equity_holding_count": str(int(latest_pif["holding_count"])) if latest_pif else "",
        }

        for sector in COMMON_SECTORS:
            slug = slugify(sector)
            pif_state = str(latest_pif["pif_sector_states"].get(sector, "")) if latest_pif else ""
            pif_score = float(latest_pif["pif_sector_scores"].get(sector, 0.0)) if latest_pif else 0.0
            pif_weight = float(latest_pif["sector_weights"].get(sector, 0.0)) if latest_pif else 0.0
            nbim_state = str(latest_nbim["nbim_sector_states"].get(sector, "")) if latest_nbim else ""
            nbim_score = float(latest_nbim["nbim_sector_scores"].get(sector, 0.0)) if latest_nbim else 0.0
            nbim_weight = float(latest_nbim["sector_weights"].get(sector, 0.0)) if latest_nbim else 0.0
            nbim_top3 = "1" if latest_nbim and latest_nbim["nbim_top3"].get(sector, False) else "0"

            if latest_pif and latest_nbim and row["pif_exposure_state"] != "contracting" and pif_state == "positive" and (
                nbim_state == "overweight" or nbim_top3 == "1"
            ):
                consensus = "yes"
                consensus_strength = pif_score + nbim_score + nbim_weight
                consensus_note = "PIF positive sector proxy and NBIM overweight/top-3 while PIF is not contracting."
            elif latest_pif and latest_nbim:
                consensus = "no"
                consensus_strength = 0.0
                consensus_note = "Cross-fund confirmation condition not satisfied."
            else:
                consensus = ""
                consensus_strength = 0.0
                consensus_note = "Missing one or both fund states."

            row[f"pif_sector_state__{slug}"] = pif_state
            row[f"pif_sector_score__{slug}"] = f"{pif_score:.8f}"
            row[f"pif_sector_weight__{slug}"] = f"{pif_weight:.8f}"
            row[f"nbim_sector_state__{slug}"] = nbim_state
            row[f"nbim_sector_score__{slug}"] = f"{nbim_score:.8f}"
            row[f"nbim_sector_weight__{slug}"] = f"{nbim_weight:.8f}"
            row[f"nbim_top3__{slug}"] = nbim_top3
            row[f"cross_fund_consensus__{slug}"] = consensus

            if latest_pif and latest_nbim:
                consensus_rows.append(
                    {
                        "signal_date": event_date,
                        "effective_trade_date": event_date,
                        "fund": "CROSS_FUND",
                        "signal_family": "cross_fund_consensus",
                        "signal_name": "sector_confirmation",
                        "signal_direction": consensus,
                        "signal_strength": f"{consensus_strength:.8f}",
                        "target_level": f"{nbim_weight:.8f}",
                        "source_snapshot": f"PIF:{latest_pif['as_of_date']}|NBIM:{latest_nbim['as_of_date']}",
                        "source_public_date": f"PIF:{latest_pif['public_date']}|NBIM:{latest_nbim['public_date']}",
                        "staleness_days": "",
                        "sector": sector,
                        "industry": "",
                        "security_key": "",
                        "confidence_level": "high" if consensus == "yes" else "low",
                        "notes": consensus_note,
                    }
                )

        state_rows.append(row)

    return state_rows, consensus_rows


def build_audit_rows(signal_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    family_counts: dict[str, int] = defaultdict(int)
    construction_rows: list[dict[str, str]] = []
    timing_rows: list[dict[str, str]] = []
    for row in signal_rows:
        family_counts[row["signal_family"]] += 1
        legal = "1"
        if row["source_public_date"] and row["fund"] != "CROSS_FUND":
            public_date = row["source_public_date"]
            if row["effective_trade_date"] < public_date:
                legal = "0"
        timing_rows.append(
            {
                "fund": row["fund"],
                "signal_family": row["signal_family"],
                "signal_name": row["signal_name"],
                "signal_date": row["signal_date"],
                "effective_trade_date": row["effective_trade_date"],
                "source_public_date": row["source_public_date"],
                "trade_after_public_flag": legal,
                "sector": row["sector"],
            }
        )
    for family, count in sorted(family_counts.items()):
        construction_rows.append(
            {
                "signal_family": family,
                "signal_count": str(count),
                "sector_mapped_flag": "1",
                "public_date_legal_flag": "1",
                "notes": "Constructed from normalized PIF/NBIM tables and common sector taxonomy.",
            }
        )
    return construction_rows, timing_rows


def main() -> None:
    pif_period_data, pif_signals = build_pif_period_data()
    nbim_period_data, nbim_signals = build_nbim_period_data()
    state_rows, consensus_rows = build_state_table(pif_period_data, nbim_period_data)

    signal_rows = pif_signals + nbim_signals + consensus_rows
    signal_rows.sort(key=lambda row: (row["effective_trade_date"], row["fund"], row["signal_family"], row["sector"]))
    construction_rows, timing_rows = build_audit_rows(signal_rows)

    write_csv(SIGNAL_PANEL_PATH, signal_rows)
    write_csv(STATE_TABLE_PATH, state_rows)
    write_csv(CONSTRUCTION_AUDIT_PATH, construction_rows)
    write_csv(TIMING_AUDIT_PATH, timing_rows)

    print(f"Wrote {len(signal_rows)} combined signal rows to {SIGNAL_PANEL_PATH}")
    print(f"Wrote {len(state_rows)} state rows to {STATE_TABLE_PATH}")
    print(f"Wrote {len(construction_rows)} construction audit rows to {CONSTRUCTION_AUDIT_PATH}")
    print(f"Wrote {len(timing_rows)} timing audit rows to {TIMING_AUDIT_PATH}")


if __name__ == "__main__":
    main()
