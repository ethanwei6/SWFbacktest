#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "audit"
DETAIL_PATH = OUT_DIR / "deep_logic_audit_checks.csv"
SUMMARY_PATH = OUT_DIR / "deep_logic_audit_summary.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str | None) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def add_check(rows: list[dict[str, str]], check_name: str, status: str, detail: str) -> None:
    rows.append({"check_name": check_name, "status": status, "detail": detail})


def main() -> None:
    checks: list[dict[str, str]] = []

    # 1. P5 initial seed must fully deploy the initial NAV.
    p5_rebalances = read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_rebalance_events.csv")
    p5_orders = read_csv(ROOT / "data/processed/pif/backtests/p5_cash_aware_copy/p5cac_orders.csv")
    r1 = p5_rebalances[0]
    buy_value = sum(
        to_float(row["execution_value"])
        for row in p5_orders
        if row["rebalance_id"] == r1["rebalance_id"] and row["side"] == "BUY"
    )
    expected = to_float(r1["cash_before_rebalance"])
    diff = abs(buy_value - expected)
    add_check(
        checks,
        "p5_initial_seed_full_deployment",
        "pass" if diff < 1e-10 and abs(to_float(r1["cash_after_rebalance"])) < 1e-10 else "fail",
        f"buy_value={buy_value:.12f} expected={expected:.12f} cash_after={to_float(r1['cash_after_rebalance']):.12f}",
    )

    # 2. P5 mixed rebalance cash arithmetic must reconcile.
    sample_rebalance = next(row for row in p5_rebalances if to_float(row["buy_value_filled"]) > 0 and to_float(row["sell_value_filled"]) > 0)
    cash_before = to_float(sample_rebalance["cash_before_rebalance"])
    cash_after = to_float(sample_rebalance["cash_after_rebalance"])
    sell_value = to_float(sample_rebalance["sell_value_filled"])
    buy_value = to_float(sample_rebalance["buy_value_filled"])
    recomputed_cash_after = cash_before + sell_value - buy_value
    add_check(
        checks,
        "p5_cash_rebalance_arithmetic",
        "pass" if abs(recomputed_cash_after - cash_after) < 1e-10 else "fail",
        f"rebalance_id={sample_rebalance['rebalance_id']} recomputed={recomputed_cash_after:.12f} actual={cash_after:.12f}",
    )

    # 3. N6 latest rebalance must match top-3 industry weights from the source snapshot.
    n6_signals = read_csv(ROOT / "data/processed/nbim/backtests/n6_top3_industry_leaders/n6t3l_signal_eligibility.csv")
    latest_snapshot = max(row["as_of_date"] for row in n6_signals)
    latest_rows = [row for row in n6_signals if row["as_of_date"] == latest_snapshot]
    industry_map = {
        row["nbim_industry"]: row["etf_symbol"]
        for row in read_csv(ROOT / "data/processed/nbim/nbim_industry_etf_map.csv")
    }
    snapshot_rows = [
        row for row in read_csv(ROOT / "data/processed/nbim/nbim_snapshot_industry_summary.csv")
        if row["as_of_date"] == latest_snapshot and row["industry"] in industry_map
    ]
    expected_top3 = [
        industry_map[row["industry"]]
        for row in sorted(snapshot_rows, key=lambda row: to_float(row["portfolio_weight_usd"]), reverse=True)[:3]
    ]
    actual_top3 = [row["symbol"] for row in latest_rows]
    add_check(
        checks,
        "n6_latest_top3_selection",
        "pass" if actual_top3 == expected_top3 else "fail",
        f"snapshot={latest_snapshot} expected={expected_top3} actual={actual_top3}",
    )

    # 4. S1 first rebalance should use top-3 fallback when no overweight sectors exist.
    state_rows = {row["event_date"]: row for row in read_csv(ROOT / "data/processed/signals/swf_signal_states.csv")}
    s1_orders = [row for row in read_csv(ROOT / "data/processed/combined/backtests/s1_exposure_regime_overlay/s1ero_orders.csv") if row["rebalance_id"] == "S1ERO-R001"]
    state = state_rows["2019-02-14"]
    top3_sectors = sorted(
        [
            sector.replace("nbim_top3__", "").replace("_", " ").title()
            for sector, value in state.items()
            if sector.startswith("nbim_top3__") and value == "1"
        ]
    )
    actual_sectors = sorted(row["sector"] for row in s1_orders)
    add_check(
        checks,
        "s1_first_rebalance_uses_nbim_top3_fallback",
        "pass" if actual_sectors == top3_sectors else "fail",
        f"expected={top3_sectors} actual={actual_sectors}",
    )

    # 5. Execution lag detail should shift N6 first trade to the third tradable day after the signal.
    n6_t3 = read_csv(ROOT / "data/processed/robustness/execution_lag_detail/n6/t3/n6_t3_rebalance_events.csv")[0]
    benchmark_dates = [
        row["date"]
        for row in read_csv(ROOT / "data/processed/nbim/nbim_twelvedata_daily_prices.csv")
        if row["instrument_key"] == "benchmark_vt" and row["adjust_mode"] == "all"
    ]
    signal_date = n6_t3["signal_date"]
    later = [date for date in benchmark_dates if date > signal_date]
    expected_trade_date = later[2]
    add_check(
        checks,
        "n6_t3_execution_lag_alignment",
        "pass" if n6_t3["trade_date"] == expected_trade_date else "fail",
        f"signal_date={signal_date} expected={expected_trade_date} actual={n6_t3['trade_date']}",
    )

    # 6. Cost sensitivity at 50 bps should reduce fully deployed initial NAV to 1/(1+0.005).
    p5_c50_first = next(
        row
        for row in read_csv(ROOT / "data/processed/robustness/cost_sensitivity_daily.csv")
        if row["strategy_key"] == "p5" and row["cost_variant"] == "c50"
    )
    expected_nav = 1.0 / 1.005
    actual_nav = to_float(p5_c50_first["nav_end"])
    add_check(
        checks,
        "p5_cost_50bps_initial_nav",
        "pass" if abs(actual_nav - expected_nav) < 1e-12 else "fail",
        f"expected={expected_nav:.12f} actual={actual_nav:.12f}",
    )

    # 7. Tight-cap N6 path should respect the stated 30% max position limit.
    n6_tight = [
        row for row in read_csv(ROOT / "data/processed/robustness/concentration_cap_daily.csv")
        if row["strategy_key"] == "n6" and row["cap_variant"] == "t1"
    ]
    max_weight = max(to_float(row["max_position_weight_end"]) for row in n6_tight)
    add_check(
        checks,
        "n6_tight_cap_compliance",
        "pass" if max_weight <= 0.300000000001 else "fail",
        f"max_position_weight_end={max_weight:.12f}",
    )

    # 8. Subperiod summary should match rebased daily endpoints for a representative N6 window.
    subperiod_daily = read_csv(ROOT / "data/processed/robustness/subperiod_daily.csv")
    n6_2426 = [row for row in subperiod_daily if row["strategy_key"] == "n6" and row["subperiod_key"] == "2024_2026"]
    strategy_return = to_float(n6_2426[-1]["strategy_rebased_nav"]) - 1.0
    benchmark_return = to_float(n6_2426[-1]["benchmark_rebased_nav"]) - 1.0
    subperiod_summary = next(
        row for row in read_csv(ROOT / "data/processed/robustness/subperiod_summary.csv")
        if row["strategy_key"] == "n6" and row["subperiod_key"] == "2024_2026"
    )
    add_check(
        checks,
        "n6_subperiod_summary_reconciliation",
        "pass"
        if abs(strategy_return - to_float(subperiod_summary["strategy_total_return"])) < 1e-10
        and abs(benchmark_return - to_float(subperiod_summary["benchmark_total_return"])) < 1e-10
        else "fail",
        f"strategy={strategy_return:.12f}/{to_float(subperiod_summary['strategy_total_return']):.12f} benchmark={benchmark_return:.12f}/{to_float(subperiod_summary['benchmark_total_return']):.12f}",
    )

    # 9. Synthetic benchmark blend for S1 should be an exact 50/50 rebase of VT and SPY.
    benchmark_rows = read_csv(ROOT / "data/processed/robustness/benchmark_series_daily.csv")
    by_key = defaultdict(dict)
    for row in benchmark_rows:
        by_key[row["benchmark_key"]][row["date"]] = to_float(row["close"])
    sample_date = "2024-08-28"
    vt = by_key["VT"][sample_date] / by_key["VT"]["2019-01-02"]
    spy = by_key["SPY"][sample_date] / by_key["SPY"]["2019-01-02"]
    expected_blend = 0.5 * vt + 0.5 * spy
    actual_blend = by_key["BLEND_VT_SPY_50"][sample_date]
    add_check(
        checks,
        "benchmark_blend_construction",
        "pass" if abs(expected_blend - actual_blend) < 1e-10 else "fail",
        f"date={sample_date} expected={expected_blend:.12f} actual={actual_blend:.12f}",
    )

    # 10. N6 decomposition sample should reconstruct arithmetic excess exactly.
    sample = next(
        row for row in read_csv(ROOT / "data/processed/attribution/daily_excess_return_decomposition.csv")
        if row["strategy_key"] == "n6"
    )
    components = (
        to_float(sample["exposure_timing_effect"])
        + to_float(sample["allocation_effect"])
        + to_float(sample["concentration_effect"])
    )
    add_check(
        checks,
        "n6_decomposition_sample_reconstruction",
        "pass" if abs(components - to_float(sample["arithmetic_excess_return"])) < 1e-10 else "fail",
        f"date={sample['date']} expected={to_float(sample['arithmetic_excess_return']):.12f} components={components:.12f}",
    )

    # 11. Event-window sample should match direct price recomputation.
    event_sample = next(
        row
        for row in read_csv(ROOT / "data/processed/attribution/event_window_forward_returns.csv")
        if row["event_family"] == "nbim_overweight_tech" and row["event_date"] == "2024-02-28" and row["window_months"] == "6"
    )
    proxy_ret = to_float(event_sample["proxy_end_close"]) / to_float(event_sample["proxy_start_close"]) - 1.0
    bench_ret = to_float(event_sample["benchmark_end_close"]) / to_float(event_sample["benchmark_start_close"]) - 1.0
    recomputed_excess = proxy_ret - bench_ret
    add_check(
        checks,
        "event_window_sample_reconstruction",
        "pass" if abs(recomputed_excess - to_float(event_sample["excess_forward_return"])) < 1e-10 else "fail",
        f"expected={to_float(event_sample['excess_forward_return']):.12f} recomputed={recomputed_excess:.12f}",
    )

    # 12. N6 window-hit final excess should equal the sum of all window contribution deltas.
    daily = [row for row in read_csv(ROOT / "data/processed/robustness/benchmark_comparison_daily.csv") if row["strategy_key"] == "n6" and row["benchmark_key"] == "VT"]
    final_relative = to_float(daily[-1]["relative_excess_nav"]) - to_float(daily[0]["relative_excess_nav"])
    wh_summary = next(row for row in read_csv(ROOT / "data/processed/attribution/window_hit_rate_summary.csv") if row["strategy_key"] == "n6")
    add_check(
        checks,
        "n6_window_hit_final_relative_excess",
        "pass" if abs(final_relative - to_float(wh_summary["final_relative_excess_nav"])) < 1e-10 else "fail",
        f"recomputed={final_relative:.12f} summary={to_float(wh_summary['final_relative_excess_nav']):.12f}",
    )

    # 13. State-model first PIF-available row should map to full exposure.
    state_model = next(row for row in read_csv(ROOT / "data/processed/signals/swf_state_model.csv") if row["state_date"] == "2019-02-14")
    add_check(
        checks,
        "state_model_initial_pif_exposure_mapping",
        "pass" if state_model["pif_risk_state"] == "risk_on" and abs(to_float(state_model["model_exposure_target"]) - 1.0) < 1e-12 else "fail",
        f"state={state_model['pif_risk_state']} exposure_target={state_model['model_exposure_target']}",
    )

    write_csv(DETAIL_PATH, checks)
    summary = {
        "check_count": len(checks),
        "pass_count": sum(1 for row in checks if row["status"] == "pass"),
        "fail_count": sum(1 for row in checks if row["status"] == "fail"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
