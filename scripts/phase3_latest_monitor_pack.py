from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_DIR = ROOT / "data" / "processed" / "signals"
INFERENCE_DIR = ROOT / "data" / "processed" / "inference"
ROBUSTNESS_DIR = ROOT / "data" / "processed" / "robustness"
OUTPUT_DIR = ROOT / "data" / "processed" / "monitoring"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SECTORS = [
    "communication_services",
    "consumer_discretionary",
    "consumer_staples",
    "energy",
    "financials",
    "health_care",
    "industrials",
    "materials",
    "real_estate",
    "technology",
    "utilities",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows provided for {path}")
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pretty_sector(slug: str) -> str:
    return slug.replace("_", " ").title()


def latest_by_key(rows: List[Dict[str, str]], key: str) -> Dict[str, str]:
    ordered = sorted(rows, key=lambda row: row[key])
    return ordered[-1]


def build_signals_latest(
    latest_state_row: Dict[str, str],
    latest_signal_state_row: Dict[str, str],
) -> List[Dict[str, object]]:
    as_of_date = latest_state_row["state_date"]
    rows: List[Dict[str, object]] = []
    rows.append(
        {
            "as_of_date": as_of_date,
            "signal_group": "pif_exposure",
            "sector": "",
            "signal_name": "pif_exposure_state",
            "signal_direction": latest_signal_state_row["pif_exposure_state"],
            "signal_value": latest_signal_state_row["pif_exposure_score"],
            "active_trade_date": latest_signal_state_row["pif_trade_date_active"],
            "notes": f"holding_count={latest_signal_state_row['pif_common_equity_holding_count']}",
        }
    )
    for sector in SECTORS:
        pif_state = latest_signal_state_row[f"pif_sector_state__{sector}"]
        pif_score = latest_signal_state_row[f"pif_sector_score__{sector}"]
        pif_weight = latest_signal_state_row[f"pif_sector_weight__{sector}"]
        nbim_state = latest_signal_state_row[f"nbim_sector_state__{sector}"]
        nbim_score = latest_signal_state_row[f"nbim_sector_score__{sector}"]
        nbim_weight = latest_signal_state_row[f"nbim_sector_weight__{sector}"]
        nbim_top3 = latest_signal_state_row[f"nbim_top3__{sector}"]
        consensus = latest_signal_state_row[f"cross_fund_consensus__{sector}"]
        sector_name = pretty_sector(sector)

        rows.append(
            {
                "as_of_date": as_of_date,
                "signal_group": "pif_sector",
                "sector": sector_name,
                "signal_name": "pif_sector_state",
                "signal_direction": pif_state,
                "signal_value": pif_score,
                "active_trade_date": latest_signal_state_row["pif_trade_date_active"],
                "notes": f"sector_weight={pif_weight}",
            }
        )
        rows.append(
            {
                "as_of_date": as_of_date,
                "signal_group": "nbim_sector",
                "sector": sector_name,
                "signal_name": "nbim_sector_state",
                "signal_direction": nbim_state,
                "signal_value": nbim_score,
                "active_trade_date": latest_signal_state_row["nbim_trade_date_active"],
                "notes": f"sector_weight={nbim_weight};top3={nbim_top3}",
            }
        )
        if nbim_top3 == "1":
            rows.append(
                {
                    "as_of_date": as_of_date,
                    "signal_group": "nbim_top3",
                    "sector": sector_name,
                    "signal_name": "nbim_top3_member",
                    "signal_direction": "included",
                    "signal_value": nbim_weight,
                    "active_trade_date": latest_signal_state_row["nbim_trade_date_active"],
                    "notes": "Current N6 production-sleeve member",
                }
            )
        if consensus == "yes":
            rows.append(
                {
                    "as_of_date": as_of_date,
                    "signal_group": "cross_fund_consensus",
                    "sector": sector_name,
                    "signal_name": "cross_fund_consensus",
                    "signal_direction": "yes",
                    "signal_value": "1.0",
                    "active_trade_date": as_of_date,
                    "notes": "Sector is positive across both funds",
                }
            )
    return rows


def build_state_latest(
    state_rows: List[Dict[str, str]],
    latest_state_row: Dict[str, str],
    state_forward_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    latest_index = next(i for i, row in enumerate(state_rows) if row["state_date"] == latest_state_row["state_date"])
    prior_row = state_rows[latest_index - 1] if latest_index > 0 else None
    state_date = latest_state_row["state_date"]

    pif_6m = next(
        row
        for row in state_forward_rows
        if row["grouping_level"] == "pif_risk_state"
        and row["group_key"] == latest_state_row["pif_risk_state"]
        and row["window_months"] == "6"
    )
    sector_6m = next(
        row
        for row in state_forward_rows
        if row["grouping_level"] == "model_sector_tilt_primary"
        and row["group_key"] == latest_state_row["model_sector_tilt_primary"]
        and row["window_months"] == "6"
    )
    return [
        {
            "as_of_date": state_date,
            "prior_state_date": prior_row["state_date"] if prior_row else "",
            "state_signature": latest_state_row["state_signature"],
            "state_change_flag": latest_state_row["state_change_flag"],
            "state_change_reason": latest_state_row["state_change_reason"],
            "pif_risk_state": latest_state_row["pif_risk_state"],
            "pif_risk_state_source": latest_state_row["pif_risk_state_source"],
            "pif_exposure_score": latest_state_row["pif_exposure_score"],
            "pif_common_equity_holding_count": latest_state_row["pif_common_equity_holding_count"],
            "nbim_sector_state": latest_state_row["nbim_sector_state"],
            "nbim_overweight_count": latest_state_row["nbim_overweight_count"],
            "nbim_top3_count": latest_state_row["nbim_top3_count"],
            "cross_fund_confirmation_count": latest_state_row["cross_fund_confirmation_count"],
            "cross_fund_confirmation_members": latest_state_row["cross_fund_confirmation_members"],
            "model_exposure_target": latest_state_row["model_exposure_target"],
            "model_cash_target": f"{1.0 - float(latest_state_row['model_exposure_target']):.12f}",
            "model_sector_tilt_primary": latest_state_row["model_sector_tilt_primary"],
            "model_sector_tilt_primary_proxy": latest_state_row["model_sector_tilt_primary_proxy"],
            "model_sector_tilt_primary_weight": latest_state_row["model_sector_tilt_primary_weight"],
            "model_sector_tilt_source": latest_state_row["model_sector_tilt_source"],
            "state_forward_6m_spy_minus_unconditional": pif_6m["avg_spy_minus_unconditional_avg"],
            "state_forward_6m_primary_sector_excess_minus_unconditional": sector_6m[
                "avg_primary_sector_excess_minus_unconditional_avg"
            ],
            "state_forward_6m_primary_sector_hit_rate": sector_6m["primary_sector_positive_excess_hit_rate"],
        }
    ]


def build_model_targets_latest(
    latest_state_row: Dict[str, str],
    latest_signal_state_row: Dict[str, str],
    final_model_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    as_of_date = latest_state_row["state_date"]
    rows: List[Dict[str, object]] = []
    production_meta = next(row for row in final_model_rows if row["model_role"] == "production_sleeve")
    monitoring_meta = next(row for row in final_model_rows if row["model_role"] == "monitoring_abstraction")

    top3_members = []
    for sector in SECTORS:
        if latest_signal_state_row[f"nbim_top3__{sector}"] == "1":
            top3_members.append(
                (
                    pretty_sector(sector),
                    latest_signal_state_row[f"nbim_sector_weight__{sector}"],
                )
            )
    equal_weight = 1.0 / len(top3_members) if top3_members else 0.0

    rows.append(
        {
            "as_of_date": as_of_date,
            "target_family": "cross_fund_state_model",
            "target_role": "gross_exposure",
            "target_name": "Model Gross Exposure",
            "target_proxy": "cash_plus_overlay",
            "target_weight": latest_state_row["model_exposure_target"],
            "target_direction": latest_state_row["pif_risk_state"],
            "source_model": monitoring_meta["candidate_label"],
            "source_signal": latest_state_row["pif_risk_state_source"],
            "implementation_note": monitoring_meta["implementation_expression"],
        }
    )
    rows.append(
        {
            "as_of_date": as_of_date,
            "target_family": "cross_fund_state_model",
            "target_role": "cash",
            "target_name": "Residual Cash",
            "target_proxy": "cash",
            "target_weight": f"{1.0 - float(latest_state_row['model_exposure_target']):.12f}",
            "target_direction": "reserve",
            "source_model": monitoring_meta["candidate_label"],
            "source_signal": latest_state_row["pif_risk_state_source"],
            "implementation_note": "Residual cash implied by the model exposure target.",
        }
    )
    rows.append(
        {
            "as_of_date": as_of_date,
            "target_family": "cross_fund_state_model",
            "target_role": "primary_tilt",
            "target_name": latest_state_row["model_sector_tilt_primary"],
            "target_proxy": latest_state_row["model_sector_tilt_primary_proxy"],
            "target_weight": latest_state_row["model_sector_tilt_primary_weight"],
            "target_direction": latest_state_row["nbim_sector_state"],
            "source_model": monitoring_meta["candidate_label"],
            "source_signal": latest_state_row["model_sector_tilt_source"],
            "implementation_note": "Primary sector tilt implied by the current cross-fund state.",
        }
    )
    for sector_name, nbim_weight in top3_members:
        rows.append(
            {
                "as_of_date": as_of_date,
                "target_family": "production_sleeve",
                "target_role": "sector_proxy",
                "target_name": sector_name,
                "target_proxy": {
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
                }[sector_name],
                "target_weight": f"{equal_weight:.12f}",
                "target_direction": "long",
                "source_model": production_meta["candidate_label"],
                "source_signal": "nbim_top3_leaders",
                "implementation_note": f"NBIM current sector weight={nbim_weight}; production sleeve holds current top-3 sectors equally.",
            }
        )
    return rows


def build_audit(
    signals_latest: List[Dict[str, object]],
    state_latest: List[Dict[str, object]],
    model_targets_latest: List[Dict[str, object]],
    latest_state_row: Dict[str, str],
) -> List[Dict[str, object]]:
    audit_rows: List[Dict[str, object]] = []
    signal_dates = {row["as_of_date"] for row in signals_latest}
    state_dates = {row["as_of_date"] for row in state_latest}
    target_dates = {row["as_of_date"] for row in model_targets_latest}
    audit_rows.append(
        {
            "check_name": "common_as_of_date_alignment",
            "status": "pass" if signal_dates == state_dates == target_dates == {latest_state_row["state_date"]} else "fail",
            "details": f"signals={sorted(signal_dates)};state={sorted(state_dates)};targets={sorted(target_dates)}",
        }
    )
    top3_rows = [row for row in model_targets_latest if row["target_family"] == "production_sleeve"]
    top3_weight_sum = sum(float(row["target_weight"]) for row in top3_rows)
    audit_rows.append(
        {
            "check_name": "production_sleeve_equal_weight_sum",
            "status": "pass" if abs(top3_weight_sum - 1.0) < 1e-9 else "fail",
            "details": f"count={len(top3_rows)};weight_sum={top3_weight_sum:.12f}",
        }
    )
    exposure_row = next(row for row in model_targets_latest if row["target_role"] == "gross_exposure")
    cash_row = next(row for row in model_targets_latest if row["target_role"] == "cash")
    exposure_plus_cash = float(exposure_row["target_weight"]) + float(cash_row["target_weight"])
    audit_rows.append(
        {
            "check_name": "state_model_exposure_plus_cash_equals_one",
            "status": "pass" if abs(exposure_plus_cash - 1.0) < 1e-9 else "fail",
            "details": f"sum={exposure_plus_cash:.12f}",
        }
    )
    top3_signal_rows = [row for row in signals_latest if row["signal_group"] == "nbim_top3"]
    audit_rows.append(
        {
            "check_name": "top3_signal_count_matches_state",
            "status": "pass" if len(top3_signal_rows) == int(latest_state_row["nbim_top3_count"]) else "fail",
            "details": f"signals={len(top3_signal_rows)};state={latest_state_row['nbim_top3_count']}",
        }
    )
    return audit_rows


def main() -> None:
    state_rows = read_csv(SIGNALS_DIR / "swf_state_model.csv")
    signal_state_rows = read_csv(SIGNALS_DIR / "swf_signal_states.csv")
    state_forward_rows = read_csv(SIGNALS_DIR / "state_forward_return_summary.csv")
    final_model_rows = read_csv(INFERENCE_DIR / "final_model_expression.csv")

    latest_state_row = latest_by_key(state_rows, "state_date")
    latest_signal_state_row = latest_by_key(signal_state_rows, "event_date")

    signals_latest = build_signals_latest(latest_state_row, latest_signal_state_row)
    state_latest = build_state_latest(state_rows, latest_state_row, state_forward_rows)
    model_targets_latest = build_model_targets_latest(latest_state_row, latest_signal_state_row, final_model_rows)
    audit_rows = build_audit(signals_latest, state_latest, model_targets_latest, latest_state_row)

    write_csv(OUTPUT_DIR / "signals_latest.csv", signals_latest)
    write_csv(OUTPUT_DIR / "state_latest.csv", state_latest)
    write_csv(OUTPUT_DIR / "model_targets_latest.csv", model_targets_latest)
    write_csv(OUTPUT_DIR / "monitoring_latest_audit.csv", audit_rows)


if __name__ == "__main__":
    main()
