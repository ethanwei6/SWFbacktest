from __future__ import annotations

import csv
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = ROOT / "data" / "processed" / "robustness"
ATTRIBUTION_ROOT = ROOT / "data" / "processed" / "attribution"
METHOD_PATH = ROOT / "docs" / "methods" / "phase3-window-hit-rate.md"

BENCHMARK_DAILY_PATH = ROBUSTNESS_ROOT / "benchmark_comparison_daily.csv"
SUMMARY_PATH = ATTRIBUTION_ROOT / "window_hit_rate_summary.csv"
WINDOWS_PATH = ATTRIBUTION_ROOT / "top_bottom_windows.csv"
AUDIT_PATH = ATTRIBUTION_ROOT / "window_hit_rate_audit.csv"

FOCUS_SET = [
    {
        "strategy_key": "p5",
        "strategy_name": "P5 Cash-Aware Copy",
        "benchmark_key": "SPY",
        "rebalance_path": ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_rebalance_events.csv",
        "metadata_fields": ["report_periods", "signal_dates", "raw_signal_count"],
    },
    {
        "strategy_key": "n4",
        "strategy_name": "N4 Industry Weight-Change Tilt",
        "benchmark_key": "VT",
        "rebalance_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n4_industry_weight_change_tilt" / "n4iwc_rebalance_events.csv",
        "metadata_fields": ["as_of_date", "included_count", "included_signal_ids"],
    },
    {
        "strategy_key": "n6",
        "strategy_name": "N6 Top-3 Industry Leaders",
        "benchmark_key": "VT",
        "rebalance_path": ROOT / "data" / "processed" / "nbim" / "backtests" / "n6_top3_industry_leaders" / "n6t3l_rebalance_events.csv",
        "metadata_fields": ["as_of_date", "included_count", "included_signal_ids"],
    },
    {
        "strategy_key": "s1",
        "strategy_name": "S1 Exposure Regime Overlay",
        "benchmark_key": "VT",
        "rebalance_path": ROOT / "data" / "processed" / "combined" / "backtests" / "s1_exposure_regime_overlay" / "s1ero_rebalance_events.csv",
        "metadata_fields": ["signal_count", "rationale_text"],
    },
]


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


def load_daily_lookup() -> dict[tuple[str, str, str], dict[str, str]]:
    rows = read_csv(BENCHMARK_DAILY_PATH)
    return {(row["strategy_key"], row["benchmark_key"], row["date"]): row for row in rows}


def metadata_text(row: dict[str, str], fields: list[str]) -> str:
    parts = []
    for field in fields:
        value = row.get(field, "")
        if value:
            parts.append(f"{field}={value}")
    return "; ".join(parts)


def build_windows_for_strategy(
    config: dict[str, object],
    daily_lookup: dict[tuple[str, str, str], dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, str], list[dict[str, str]]]:
    rebalance_rows = read_csv(Path(config["rebalance_path"]))
    strategy_key = str(config["strategy_key"])
    strategy_name = str(config["strategy_name"])
    benchmark_key = str(config["benchmark_key"])
    metadata_fields = list(config["metadata_fields"])

    strategy_daily = sorted(
        [
            row
            for (key, benchmark, _), row in daily_lookup.items()
            if key == strategy_key and benchmark == benchmark_key
        ],
        key=lambda row: row["date"],
    )
    if len(strategy_daily) < 2:
        raise RuntimeError(f"Not enough daily rows for {strategy_key}")

    daily_by_date = {row["date"]: row for row in strategy_daily}
    last_date = strategy_daily[-1]["date"]

    window_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for index, row in enumerate(rebalance_rows):
        start_date = row["trade_date"]
        end_date = ""
        if "next_rebalance_trade_date" in row and row["next_rebalance_trade_date"]:
            end_date = row["next_rebalance_trade_date"]
        elif index + 1 < len(rebalance_rows):
            end_date = rebalance_rows[index + 1]["trade_date"]
        else:
            end_date = last_date

        start_daily = daily_by_date.get(start_date)
        end_daily = daily_by_date.get(end_date)
        if start_daily is None or end_daily is None:
            audit_rows.append(
                {
                    "strategy_key": strategy_key,
                    "window_start_date": start_date,
                    "window_end_date": end_date,
                    "check_name": "window_dates_found",
                    "status": "fail",
                    "detail": f"Missing start or end daily row for {start_date} -> {end_date}.",
                }
            )
            continue

        strategy_start_nav = to_float(start_daily["strategy_rebased_nav"])
        strategy_end_nav = to_float(end_daily["strategy_rebased_nav"])
        benchmark_start_nav = to_float(start_daily["benchmark_rebased_nav"])
        benchmark_end_nav = to_float(end_daily["benchmark_rebased_nav"])
        relative_start = to_float(start_daily["relative_excess_nav"])
        relative_end = to_float(end_daily["relative_excess_nav"])

        strategy_window_return = strategy_end_nav / strategy_start_nav - 1.0 if strategy_start_nav else 0.0
        benchmark_window_return = benchmark_end_nav / benchmark_start_nav - 1.0 if benchmark_start_nav else 0.0
        excess_window_return = strategy_window_return - benchmark_window_return
        contribution_delta = relative_end - relative_start

        next_rebalance_id = rebalance_rows[index + 1]["rebalance_id"] if index + 1 < len(rebalance_rows) else ""
        window_dates = [d for d in strategy_daily if start_date <= d["date"] <= end_date]
        window_rows.append(
            {
                "strategy_key": strategy_key,
                "strategy_name": strategy_name,
                "benchmark_key": benchmark_key,
                "window_index": str(index + 1),
                "rebalance_id": row["rebalance_id"],
                "next_rebalance_id": next_rebalance_id,
                "window_start_date": start_date,
                "window_end_date": end_date,
                "window_day_count": str(max(0, len(window_dates) - 1)),
                "strategy_start_nav": f"{strategy_start_nav:.12f}",
                "strategy_end_nav": f"{strategy_end_nav:.12f}",
                "benchmark_start_nav": f"{benchmark_start_nav:.12f}",
                "benchmark_end_nav": f"{benchmark_end_nav:.12f}",
                "strategy_window_return": f"{strategy_window_return:.12f}",
                "benchmark_window_return": f"{benchmark_window_return:.12f}",
                "excess_window_return": f"{excess_window_return:.12f}",
                "relative_excess_nav_start": f"{relative_start:.12f}",
                "relative_excess_nav_end": f"{relative_end:.12f}",
                "contribution_delta_relative_excess_nav": f"{contribution_delta:.12f}",
                "cash_weight_start": start_daily["cash_weight_end"],
                "cash_weight_end": end_daily["cash_weight_end"],
                "gross_exposure_start": start_daily["gross_exposure_end"],
                "gross_exposure_end": end_daily["gross_exposure_end"],
                "metadata_text": metadata_text(row, metadata_fields),
            }
        )

        audit_rows.append(
            {
                "strategy_key": strategy_key,
                "window_start_date": start_date,
                "window_end_date": end_date,
                "check_name": "window_dates_found",
                "status": "pass",
                "detail": f"{start_date} -> {end_date}",
            }
        )

    if not window_rows:
        raise RuntimeError(f"No valid window rows for {strategy_key}")

    positive_excess = [to_float(row["excess_window_return"]) for row in window_rows if to_float(row["excess_window_return"]) > 0.0]
    positive_contributions = [to_float(row["contribution_delta_relative_excess_nav"]) for row in window_rows if to_float(row["contribution_delta_relative_excess_nav"]) > 0.0]
    negative_contributions = [to_float(row["contribution_delta_relative_excess_nav"]) for row in window_rows if to_float(row["contribution_delta_relative_excess_nav"]) < 0.0]
    positive_total = sum(positive_contributions)
    absolute_total = sum(abs(value) for value in positive_contributions + negative_contributions)
    sorted_positive = sorted(positive_contributions, reverse=True)
    top3_positive = sum(sorted_positive[:3])
    positive_hhi = sum((value / positive_total) ** 2 for value in positive_contributions) if positive_total else 0.0
    top3_absolute = sum(sorted((abs(value) for value in positive_contributions + negative_contributions), reverse=True)[:3])

    final_relative_excess = to_float(window_rows[-1]["relative_excess_nav_end"])
    summary_row = {
        "strategy_key": strategy_key,
        "strategy_name": strategy_name,
        "benchmark_key": benchmark_key,
        "window_count": str(len(window_rows)),
        "positive_excess_window_count": str(sum(1 for row in window_rows if to_float(row["excess_window_return"]) > 0.0)),
        "negative_excess_window_count": str(sum(1 for row in window_rows if to_float(row["excess_window_return"]) < 0.0)),
        "beat_benchmark_hit_rate": f"{(sum(1 for row in window_rows if to_float(row['excess_window_return']) > 0.0) / len(window_rows)):.12f}",
        "positive_contribution_window_count": str(len(positive_contributions)),
        "negative_contribution_window_count": str(len(negative_contributions)),
        "avg_window_excess_return": f"{statistics.mean(to_float(row['excess_window_return']) for row in window_rows):.12f}",
        "median_window_excess_return": f"{statistics.median(to_float(row['excess_window_return']) for row in window_rows):.12f}",
        "best_window_excess_return": f"{max(to_float(row['excess_window_return']) for row in window_rows):.12f}",
        "worst_window_excess_return": f"{min(to_float(row['excess_window_return']) for row in window_rows):.12f}",
        "final_relative_excess_nav": f"{final_relative_excess:.12f}",
        "top1_positive_contribution_share": f"{((sorted_positive[0] / positive_total) if positive_total and sorted_positive else 0.0):.12f}",
        "top3_positive_contribution_share": f"{((top3_positive / positive_total) if positive_total else 0.0):.12f}",
        "positive_contribution_hhi": f"{positive_hhi:.12f}",
        "top3_absolute_contribution_share": f"{((top3_absolute / absolute_total) if absolute_total else 0.0):.12f}",
        "positive_contribution_total": f"{positive_total:.12f}",
        "negative_contribution_total": f"{sum(negative_contributions):.12f}",
    }

    audit_rows.append(
        {
            "strategy_key": strategy_key,
            "window_start_date": "TOTAL",
            "window_end_date": "TOTAL",
            "check_name": "contribution_reconciliation",
            "status": "pass" if abs(sum(to_float(r["contribution_delta_relative_excess_nav"]) for r in window_rows) - final_relative_excess) < 1e-9 else "fail",
            "detail": f"sum_delta={sum(to_float(r['contribution_delta_relative_excess_nav']) for r in window_rows):.12f} final_relative={final_relative_excess:.12f}",
        }
    )

    return window_rows, summary_row, audit_rows


def build_top_bottom_rows(window_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in window_rows:
        grouped.setdefault(row["strategy_key"], []).append(row)

    out_rows: list[dict[str, str]] = []
    for strategy_key, rows in grouped.items():
        by_contribution = sorted(rows, key=lambda row: to_float(row["contribution_delta_relative_excess_nav"]), reverse=True)
        top = by_contribution[:5]
        bottom = list(reversed(by_contribution[-5:]))
        for rank, row in enumerate(top, start=1):
            enriched = dict(row)
            enriched["rank_group"] = "top"
            enriched["rank_within_group"] = str(rank)
            out_rows.append(enriched)
        for rank, row in enumerate(bottom, start=1):
            enriched = dict(row)
            enriched["rank_group"] = "bottom"
            enriched["rank_within_group"] = str(rank)
            out_rows.append(enriched)
    return out_rows


def main() -> None:
    daily_lookup = load_daily_lookup()
    all_window_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    for config in FOCUS_SET:
        window_rows, summary_row, part_audit = build_windows_for_strategy(config, daily_lookup)
        all_window_rows.extend(window_rows)
        summary_rows.append(summary_row)
        audit_rows.extend(part_audit)

    top_bottom_rows = build_top_bottom_rows(all_window_rows)
    write_csv(SUMMARY_PATH, summary_rows)
    write_csv(WINDOWS_PATH, top_bottom_rows)
    write_csv(AUDIT_PATH, audit_rows)

    METHOD_PATH.write_text(
        "# Phase 3 B3: Window Hit-Rate and Contribution Analysis\n\n"
        "This layer asks whether the surviving results are broad-based across rebalance windows or dominated by a small number of periods.\n\n"
        "## Focus set\n\n"
        "- `P5` Cash-Aware Copy versus `SPY`\n"
        "- `N4` Industry Weight-Change Tilt versus `VT`\n"
        "- `N6` Top-3 Industry Leaders versus `VT`\n"
        "- `S1` Exposure Regime Overlay versus `VT`\n\n"
        "## Method\n\n"
        "B3 uses the already validated `benchmark_comparison_daily.csv` layer so every window starts from aligned strategy and benchmark NAVs. Rebalance windows are formed from each strategy's native rebalance-event file:\n\n"
        "- start at a rebalance trade-date close;\n"
        "- end at the next rebalance trade-date close;\n"
        "- for the final window, end at the last available aligned daily observation.\n\n"
        "For each window we compute:\n\n"
        "- strategy window return;\n"
        "- benchmark window return;\n"
        "- excess window return;\n"
        "- exact additive contribution, defined as the change in `relative_excess_nav` across the window.\n\n"
        "That contribution measure is important because it sums exactly to the final benchmark-relative NAV difference, which makes concentration analysis truthful rather than approximate.\n\n"
        "## Outputs\n\n"
        "- `data/processed/attribution/window_hit_rate_summary.csv`\n"
        "- `data/processed/attribution/top_bottom_windows.csv`\n"
        "- `data/processed/attribution/window_hit_rate_audit.csv`\n\n"
        "## Validation\n\n"
        "The audit checks that each rebalance window can be found in the aligned benchmark-comparison layer and that summed window contributions reconcile to the final relative-excess NAV for each strategy.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
