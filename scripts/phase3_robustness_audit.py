from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
REPORT_PATH = ROBUSTNESS_ROOT / "phase3_robustness_audit.json"
TABLE_PATH = ROBUSTNESS_ROOT / "phase3_robustness_audit_checks.csv"

PIF_PRICE_PATH = ROOT / "data" / "processed" / "pif" / "pif_twelvedata_daily_prices.csv"
NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str | float | int | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_price_lookups() -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float]]:
    pif = {
        (row["security_key"], row["date"]): to_float(row["close"])
        for row in read_csv(PIF_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }
    nbim = {
        (row["instrument_key"], row["date"]): to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all"
    }
    return pif, nbim


def record(
    rows: list[dict[str, str]],
    layer: str,
    check_name: str,
    status: str,
    expected: str,
    actual: str,
    note: str,
) -> None:
    rows.append(
        {
            "layer": layer,
            "check_name": check_name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "note": note,
        }
    )


def main() -> None:
    check_rows: list[dict[str, str]] = []
    pif_prices, nbim_prices = build_price_lookups()

    # A1: audit file clean
    a1_audit = read_csv(ROBUSTNESS_ROOT / "execution_lag_audit.csv")
    fail_count = sum(1 for row in a1_audit if row["status"] != "pass")
    record(
        check_rows,
        "A1",
        "audit_rows_all_pass",
        "pass" if fail_count == 0 else "fail",
        "0",
        str(fail_count),
        "Execution-lag audit file should have no failed checks.",
    )

    # A1: baseline reproduction exact enough
    for row in a1_audit:
        if row["check_type"] == "baseline_reproduction_final_nav":
            diff = abs(to_float(row["difference"]))
            record(
                check_rows,
                "A1",
                f"baseline_reproduction::{row['strategy_key']}::{row['variant_key']}",
                "pass" if diff <= 1e-9 else "fail",
                "<=1e-9",
                f"{diff:.12f}",
                "Baseline T+1 variant must reproduce validated final NAV within tolerance.",
            )

    # A1: sample price checks
    samples = [
        (
            "A1",
            ROBUSTNESS_ROOT / "execution_lag_detail" / "p5" / "t3" / "p5_orders.csv",
            "security_key",
            "execution_date",
            "execution_price",
            pif_prices,
        ),
        (
            "A1",
            ROBUSTNESS_ROOT / "execution_lag_detail" / "n4" / "t3" / "n4_t3_orders.csv",
            "instrument_key",
            "trade_date",
            "price",
            nbim_prices,
        ),
        (
            "A1",
            ROBUSTNESS_ROOT / "execution_lag_detail" / "s1" / "t5" / "s1_t5_orders.csv",
            "instrument_key",
            "execution_date",
            "execution_price",
            nbim_prices,
        ),
    ]
    for layer, path, key_col, date_col, price_col, lookup in samples:
        first = read_csv(path)[0]
        source_price = lookup[(first[key_col], first[date_col])]
        actual_price = to_float(first[price_col])
        record(
            check_rows,
            layer,
            f"source_price_match::{path.stem}",
            "pass" if abs(source_price - actual_price) < 1e-9 else "fail",
            f"{source_price:.8f}",
            f"{actual_price:.8f}",
            "Sample delayed-execution order price should match stored validated source price exactly.",
        )

    # A2
    a2_audit = read_csv(ROBUSTNESS_ROOT / "cost_sensitivity_audit.csv")
    fail_count = sum(1 for row in a2_audit if row["status"] != "pass")
    record(
        check_rows,
        "A2",
        "audit_rows_all_pass",
        "pass" if fail_count == 0 else "fail",
        "0",
        str(fail_count),
        "Cost-sensitivity audit file should have no failed checks.",
    )
    for row in a2_audit:
        if row["check_type"] == "baseline_reproduction_final_nav":
            diff = abs(to_float(row["difference"]))
            record(
                check_rows,
                "A2",
                f"baseline_reproduction::{row['strategy_key']}::{row['variant_key']}",
                "pass" if diff <= 5e-10 else "fail",
                "<=5e-10",
                f"{diff:.12f}",
                "Zero-cost variant must reproduce validated final NAV within tolerance.",
            )
    a2_summary = read_csv(ROBUSTNESS_ROOT / "cost_sensitivity_summary.csv")
    # cost monotonicity: more cost should not increase final nav
    for strategy_key in {"p5", "n4", "n6", "s1"}:
        subset = [row for row in a2_summary if row["strategy_key"] == strategy_key]
        subset.sort(key=lambda row: float(row["cost_bps"]))
        navs = [to_float(row["final_nav"]) for row in subset]
        monotonic = all(navs[i] >= navs[i + 1] - 1e-12 for i in range(len(navs) - 1))
        record(
            check_rows,
            "A2",
            f"cost_monotonicity::{strategy_key}",
            "pass" if monotonic else "fail",
            "non-increasing",
            ",".join(f"{v:.12f}" for v in navs),
            "Higher one-way cost should not improve final NAV for the same strategy.",
        )

    # A3
    a3_audit = read_csv(ROBUSTNESS_ROOT / "concentration_cap_audit.csv")
    fail_count = sum(1 for row in a3_audit if row["status"] != "pass")
    record(
        check_rows,
        "A3",
        "audit_rows_all_pass",
        "pass" if fail_count == 0 else "fail",
        "0",
        str(fail_count),
        "Concentration-cap audit file should have no failed checks.",
    )
    for row in a3_audit:
        if row["check_type"] == "baseline_reproduction_final_nav":
            diff = abs(to_float(row["difference"]))
            record(
                check_rows,
                "A3",
                f"baseline_reproduction::{row['strategy_key']}::{row['variant_key']}",
                "pass" if diff <= 5e-10 or diff <= 1e-9 else "fail",
                "<=1e-9",
                f"{diff:.12f}",
                "Uncapped variant must reproduce validated final NAV within tolerance.",
            )
    a3_summary = read_csv(ROBUSTNESS_ROOT / "concentration_cap_summary.csv")
    # uncapped should match existing baseline summary values closely
    baseline_map = {
        "p5": load_json(ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_summary.json")["final_nav"],
        "n4": load_json(ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_summary.json")["final_nav"],
        "n6": load_json(ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_summary.json")["final_nav"],
        "s1": load_json(ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_summary.json")["final_nav"],
    }
    for key, baseline_nav in baseline_map.items():
        uncapped = next(row for row in a3_summary if row["strategy_key"] == key and row["cap_variant"] == "u0")
        diff = abs(to_float(uncapped["final_nav"]) - float(baseline_nav))
        record(
            check_rows,
            "A3",
            f"summary_matches_baseline::{key}",
            "pass" if diff <= 1e-9 else "fail",
            f"{float(baseline_nav):.12f}",
            uncapped["final_nav"],
            "Uncapped summary should agree with the validated baseline summary.",
        )

    overall_status = "pass" if all(row["status"] == "pass" for row in check_rows) else "fail"
    report = {
        "overall_status": overall_status,
        "check_count": len(check_rows),
        "failed_checks": sum(1 for row in check_rows if row["status"] != "pass"),
        "layers": {
            layer: {
                "check_count": sum(1 for row in check_rows if row["layer"] == layer),
                "failed_checks": sum(1 for row in check_rows if row["layer"] == layer and row["status"] != "pass"),
            }
            for layer in ["A1", "A2", "A3"]
        },
    }

    write_csv(TABLE_PATH, check_rows)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
