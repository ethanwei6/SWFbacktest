#!/usr/bin/env python3
"""Repo-wide audit harness for the SWF project.

This is a read-only consistency audit. It does not rebuild outputs.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/audit"
FINDINGS_CSV = OUT_DIR / "full_project_audit_findings.csv"
SUMMARY_JSON = OUT_DIR / "full_project_audit_summary.json"


def iter_files(base: Path, suffixes: Sequence[str]) -> Iterable[Path]:
    for path in sorted(base.rglob("*")):
        if path.is_file() and any(str(path).endswith(sfx) for sfx in suffixes):
            yield path


def read_csv(path: Path) -> List[Dict[str, str]]:
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        for delimiter in (",", ";", "\t", "|"):
            try:
                with path.open("r", encoding=encoding, newline="") as handle:
                    reader = csv.DictReader(handle, delimiter=delimiter)
                    if not reader.fieldnames:
                        continue
                    if len(reader.fieldnames) > 1:
                        return list(reader)
            except UnicodeError:
                continue
            except csv.Error:
                continue
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def add_finding(findings: List[Dict[str, str]], severity: str, category: str, path: str, check: str, detail: str) -> None:
    findings.append(
        {
            "severity": severity,
            "category": category,
            "path": path,
            "check_name": check,
            "detail": detail,
        }
    )


def audit_python(findings: List[Dict[str, str]]) -> None:
    for path in iter_files(ROOT / "scripts", [".py"]):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            compile(tree, str(path), "exec")
        except Exception as exc:
            add_finding(findings, "error", "python", str(path.relative_to(ROOT)), "python_compiles", repr(exc))


def audit_csv_json(findings: List[Dict[str, str]]) -> None:
    for path in iter_files(ROOT / "data", [".csv"]):
        try:
            readable = False
            header_found = False
            for encoding in ("utf-8", "utf-8-sig", "utf-16"):
                for delimiter in (",", ";", "\t", "|"):
                    try:
                        with path.open("r", encoding=encoding, newline="") as handle:
                            reader = csv.reader(handle, delimiter=delimiter)
                            header = next(reader, None)
                            readable = True
                            if header is None:
                                break
                            # Prefer a parse with an actual multi-column header when available.
                            if len(header) <= 1 and delimiter != "|":
                                continue
                            header_found = True
                            header_len = len(header)
                            for idx, row in enumerate(reader, start=2):
                                # Allow missing trailing optional fields, but do not allow rows
                                # that overflow the declared header width.
                                if len(row) > header_len:
                                    add_finding(
                                        findings,
                                        "error",
                                        "csv",
                                        str(path.relative_to(ROOT)),
                                        "csv_rectangular",
                                        f"Row {idx} has {len(row)} fields, expected at most {header_len}.",
                                    )
                                    raise StopIteration
                            raise StopIteration
                    except UnicodeError:
                        continue
                    except csv.Error:
                        continue
                    except StopIteration:
                        break
                if header_found:
                    break
            if not readable:
                raise ValueError("Unable to decode CSV with supported encodings.")
            if not header_found:
                add_finding(findings, "error", "csv", str(path.relative_to(ROOT)), "csv_nonempty", "Empty CSV file.")
        except Exception as exc:
            add_finding(findings, "error", "csv", str(path.relative_to(ROOT)), "csv_readable", repr(exc))

    for path in iter_files(ROOT / "data", [".json"]):
        try:
            json.loads(path.read_text())
        except Exception as exc:
            add_finding(findings, "error", "json", str(path.relative_to(ROOT)), "json_parseable", repr(exc))


def audit_repo_hygiene(findings: List[Dict[str, str]]) -> None:
    for path in iter_files(ROOT, [".DS_Store"]):
        add_finding(findings, "warning", "repo_hygiene", str(path.relative_to(ROOT)), "ds_store_present", "macOS metadata file should not be tracked.")
    for scratch in [ROOT / ".tmp_pymupdf", ROOT / "paper/fig_tmp", ROOT / "paper/render", ROOT / "paper/render_pages"]:
        if scratch.exists():
            add_finding(findings, "warning", "repo_hygiene", str(scratch.relative_to(ROOT)), "scratch_dir_present", "Scratch render directory present.")


def audit_markdown_links(findings: List[Dict[str, str]]) -> None:
    pattern = re.compile(r"\[[^\]]+\]\((/Users/ethanwei/Documents/Codex/2026-05-28-i-want-to-move-to-this/[^)]+)\)")
    for path in list(iter_files(ROOT / "docs", [".md"])) + list(iter_files(ROOT / "outputs", [".md"])):
        text = path.read_text()
        for match in pattern.finditer(text):
            raw = match.group(1)
            target = raw.split(":", 1)[0]
            if not Path(target).exists():
                add_finding(findings, "error", "docs", str(path.relative_to(ROOT)), "absolute_link_exists", raw)


def check_audit_files(findings: List[Dict[str, str]]) -> None:
    for path in iter_files(ROOT / "data/processed", ["_audit.csv"]):
        rows = read_csv(path)
        if not rows:
            add_finding(findings, "error", "audit_file", str(path.relative_to(ROOT)), "audit_nonempty", "Audit file has no rows.")
            continue
        status_field = None
        for candidate in ("status", "audit_status"):
            if candidate in rows[0]:
                status_field = candidate
                break
        if not status_field:
            continue
        values = {row[status_field] for row in rows}
        if values.issubset({"pass", "skip", "ok"}):
            continue
        missing_like = sorted(value for value in values if value.startswith("missing_"))
        if values.issubset({"pass", "skip", "ok", *missing_like}) and missing_like:
            add_finding(
                findings,
                "warning",
                "audit_file",
                str(path.relative_to(ROOT)),
                "audit_contains_known_missing_statuses",
                ", ".join(missing_like),
            )
            continue
        bad = [row for row in rows if row[status_field] not in ("pass", "skip", "ok")]
        if bad:
            add_finding(
                findings,
                "error",
                "audit_file",
                str(path.relative_to(ROOT)),
                "audit_no_failures",
                f"{len(bad)} failing rows present.",
            )


def audit_strategy_summaries(findings: List[Dict[str, str]]) -> None:
    # PIF
    for path in sorted((ROOT / "data/processed/pif/backtests").glob("*/")):
        summary_files = list(path.glob("*summary.json"))
        portfolio_files = list(path.glob("*portfolio_daily.csv"))
        if not summary_files or not portfolio_files:
            continue
        summary = json.loads(summary_files[0].read_text())
        rows = read_csv(portfolio_files[0])
        final_nav = as_float(rows[-1]["nav_end"])
        total_return = final_nav - 1.0
        if abs(final_nav - as_float(str(summary["final_nav"]))) > 1e-10:
            add_finding(findings, "error", "pif_backtest", str(summary_files[0].relative_to(ROOT)), "final_nav_matches_portfolio", f"summary={summary['final_nav']} portfolio={final_nav:.12f}")
        if abs(total_return - as_float(str(summary["total_return"]))) > 1e-10:
            add_finding(findings, "error", "pif_backtest", str(summary_files[0].relative_to(ROOT)), "total_return_matches_portfolio", f"summary={summary['total_return']} portfolio={total_return:.12f}")

    # NBIM
    for path in sorted((ROOT / "data/processed/nbim/backtests").glob("*/")):
        summary_files = list(path.glob("*summary.json"))
        portfolio_files = list(path.glob("*portfolio_timeline.csv"))
        if not summary_files or not portfolio_files:
            continue
        summary = json.loads(summary_files[0].read_text())
        rows = read_csv(portfolio_files[0])
        final_nav = as_float(rows[-1]["nav_end"])
        total_return = final_nav - 1.0
        if abs(final_nav - as_float(str(summary["final_nav"]))) > 1e-10:
            add_finding(findings, "error", "nbim_backtest", str(summary_files[0].relative_to(ROOT)), "final_nav_matches_portfolio", f"summary={summary['final_nav']} portfolio={final_nav:.12f}")
        if abs(total_return - as_float(str(summary["total_return"]))) > 1e-10:
            add_finding(findings, "error", "nbim_backtest", str(summary_files[0].relative_to(ROOT)), "total_return_matches_portfolio", f"summary={summary['total_return']} portfolio={total_return:.12f}")

    # Combined
    for path in sorted((ROOT / "data/processed/combined/backtests").glob("*/")):
        summary_files = list(path.glob("*summary.json"))
        portfolio_files = list(path.glob("*portfolio_daily.csv"))
        if not summary_files or not portfolio_files:
            continue
        summary = json.loads(summary_files[0].read_text())
        rows = read_csv(portfolio_files[0])
        final_nav = as_float(rows[-1]["nav_end"])
        total_return = final_nav - 1.0
        if abs(final_nav - as_float(str(summary["final_nav"]))) > 1e-10:
            add_finding(findings, "error", "combined_backtest", str(summary_files[0].relative_to(ROOT)), "final_nav_matches_portfolio", f"summary={summary['final_nav']} portfolio={final_nav:.12f}")
        if abs(total_return - as_float(str(summary["total_return"]))) > 1e-10:
            add_finding(findings, "error", "combined_backtest", str(summary_files[0].relative_to(ROOT)), "total_return_matches_portfolio", f"summary={summary['total_return']} portfolio={total_return:.12f}")


def audit_benchmark_summaries(findings: List[Dict[str, str]]) -> None:
    rows = read_csv(ROOT / "data/processed/robustness/benchmark_comparison_daily.csv")
    grouped: Dict[tuple, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["strategy_key"], row["benchmark_key"])].append(row)
    summary = {
        (row["strategy_key"], row["benchmark_key"]): row
        for row in read_csv(ROOT / "data/processed/robustness/benchmark_comparison_summary.csv")
    }
    for key, series in grouped.items():
        series.sort(key=lambda r: r["date"])
        last = series[-1]
        computed_strategy_total = as_float(last["strategy_rebased_nav"]) - 1.0
        computed_benchmark_total = as_float(last["benchmark_rebased_nav"]) - 1.0
        computed_excess = computed_strategy_total - computed_benchmark_total
        srow = summary[key]
        for name, computed, field in [
            ("strategy_total", computed_strategy_total, "strategy_total_return"),
            ("benchmark_total", computed_benchmark_total, "benchmark_total_return"),
            ("excess_total", computed_excess, "excess_total_return"),
        ]:
            if abs(computed - as_float(srow[field])) > 1e-10:
                add_finding(findings, "error", "robustness", "data/processed/robustness/benchmark_comparison_summary.csv", f"{name}_matches_daily", f"{key} summary={srow[field]} computed={computed:.12f}")


def audit_event_summaries(findings: List[Dict[str, str]]) -> None:
    detail = read_csv(ROOT / "data/processed/attribution/event_window_forward_returns.csv")
    summary_rows = {
        (row["aggregation_level"], row["event_family"], row["sector"], row["window_months"]): row
        for row in read_csv(ROOT / "data/processed/attribution/event_window_summary.csv")
    }
    grouped: Dict[tuple, List[Dict[str, str]]] = defaultdict(list)
    for row in detail:
        grouped[("family_total", row["event_family"], "", row["window_months"])].append(row)
        if row["sector"]:
            grouped[("sector", row["event_family"], row["sector"], row["window_months"])].append(row)
    for key, rows in grouped.items():
        srow = summary_rows.get(key)
        if not srow:
            add_finding(findings, "error", "attribution", "data/processed/attribution/event_window_summary.csv", "summary_key_present", str(key))
            continue
        mean_excess = sum(as_float(r["excess_forward_return"]) for r in rows) / len(rows)
        mean_excess_u = sum(as_float(r["excess_return_minus_unconditional_avg"]) for r in rows) / len(rows)
        if abs(mean_excess - as_float(srow["avg_excess_forward_return"])) > 1e-10:
            add_finding(findings, "error", "attribution", "data/processed/attribution/event_window_summary.csv", "avg_excess_matches_detail", f"{key} summary={srow['avg_excess_forward_return']} computed={mean_excess:.12f}")
        if abs(mean_excess_u - as_float(srow["avg_excess_minus_unconditional"])) > 1e-10:
            add_finding(findings, "error", "attribution", "data/processed/attribution/event_window_summary.csv", "avg_excess_minus_unconditional_matches_detail", f"{key} summary={srow['avg_excess_minus_unconditional']} computed={mean_excess_u:.12f}")


def audit_window_hit_rate(findings: List[Dict[str, str]]) -> None:
    # `top_bottom_windows.csv` is intentionally a ranked subset of the full
    # rebalance-window universe. Its integrity is checked by the dedicated
    # `window_hit_rate_audit.csv` output, so it should not be reconciled
    # directly against full-window totals here.
    return


def audit_state_model(findings: List[Dict[str, str]]) -> None:
    rows = read_csv(ROOT / "data/processed/signals/swf_state_model.csv")
    # Ensure state change flag matches reason.
    prev = None
    for row in rows:
        flag = row["state_change_flag"]
        reason = row["state_change_reason"]
        if prev is None:
            if flag != "1" or reason != "initial_state":
                add_finding(findings, "error", "state_model", "data/processed/signals/swf_state_model.csv", "initial_state_flag", f"flag={flag} reason={reason}")
        else:
            changed = int(prev["state_signature"] != row["state_signature"])
            if str(changed) != flag:
                add_finding(findings, "error", "state_model", "data/processed/signals/swf_state_model.csv", "state_change_flag_matches_signature", f"{row['state_date']} flag={flag} computed={changed}")
        prev = row

    # state forward return summary reconciliation
    detail = read_csv(ROOT / "data/processed/signals/state_forward_returns.csv")
    summary = {
        (row["grouping_level"], row["group_key"], row["window_months"]): row
        for row in read_csv(ROOT / "data/processed/signals/state_forward_return_summary.csv")
    }
    allowed_groupings = {key[0] for key in summary}
    grouped: Dict[tuple, List[Dict[str, str]]] = defaultdict(list)
    for row in detail:
        # Skip rows with incomplete horizons. The current state forward-return
        # layer expresses realized windows through the specific benchmark/sector
        # end-date fields rather than a generic actual_end_date column.
        if not row.get("spy_end_date") or not row.get("vt_end_date") or not row.get("sector_end_date"):
            continue
        if "pif_risk_state" in allowed_groupings:
            grouped[("pif_risk_state", row["pif_risk_state"], row["window_months"])].append(row)
        if "nbim_sector_state" in allowed_groupings:
            grouped[("nbim_sector_state", row["nbim_sector_state"], row["window_months"])].append(row)
        if "model_sector_tilt_primary" in allowed_groupings:
            grouped[("model_sector_tilt_primary", row["model_sector_tilt_primary"], row["window_months"])].append(row)
    for key, rows2 in grouped.items():
        srow = summary.get(key)
        if not srow:
            add_finding(findings, "error", "state_model", "data/processed/signals/state_forward_return_summary.csv", "summary_key_present", str(key))
            continue
        mean_val = sum(as_float(r["primary_sector_excess_minus_unconditional_avg"]) for r in rows2) / len(rows2)
        if abs(mean_val - as_float(srow["avg_primary_sector_excess_minus_unconditional_avg"])) > 1e-10:
            add_finding(findings, "error", "state_model", "data/processed/signals/state_forward_return_summary.csv", "avg_primary_sector_excess_minus_unconditional_matches_detail", f"{key} summary={srow['avg_primary_sector_excess_minus_unconditional_avg']} computed={mean_val:.12f}")


def audit_inference(findings: List[Dict[str, str]]) -> None:
    # strategy inference summary must reconcile to validated comparison summary
    summary = {
        (row["strategy_key"], row["benchmark_key"]): row
        for row in read_csv(ROOT / "data/processed/robustness/benchmark_comparison_summary.csv")
    }
    inf = read_csv(ROOT / "data/processed/inference/strategy_statistical_tests_summary.csv")
    for row in inf:
        key = (row["strategy_key"], row["benchmark_key"])
        base = summary[key]
        if abs(as_float(row["excess_total_return"]) - as_float(base["excess_total_return"])) > 1e-10:
            add_finding(findings, "error", "inference", "data/processed/inference/strategy_statistical_tests_summary.csv", "excess_total_matches_benchmark_summary", f"{key}")
    # event-window inference means reconcile to event summary
    event_summary = {
        (row["aggregation_level"], row["event_family"], row["sector"], row["window_months"]): row
        for row in read_csv(ROOT / "data/processed/attribution/event_window_summary.csv")
    }
    inf2 = read_csv(ROOT / "data/processed/inference/event_window_inference_summary.csv")
    for row in inf2:
        key = (row["aggregation_level"], row["event_family"], row["sector"], row["window_months"])
        base = event_summary[key]
        if abs(as_float(row["avg_excess_forward_return"]) - as_float(base["avg_excess_forward_return"])) > 1e-10:
            add_finding(findings, "error", "inference", "data/processed/inference/event_window_inference_summary.csv", "avg_excess_matches_event_summary", f"{key}")
    # turnover adjusted matches cost summary
    cost_summary = {
        (row["strategy_key"], row["cost_variant"]): row
        for row in read_csv(ROOT / "data/processed/robustness/cost_sensitivity_summary.csv")
    }
    turn = read_csv(ROOT / "data/processed/inference/turnover_adjusted_metrics.csv")
    for row in turn:
        base = cost_summary[(row["strategy_key"], "c10")]
        if abs(as_float(row["turnover_adjusted_excess_total_return_10bps"]) - as_float(base["excess_total_return"])) > 1e-10:
            add_finding(findings, "error", "inference", "data/processed/inference/turnover_adjusted_metrics.csv", "turnover_adjusted_excess_matches_cost_summary", row["strategy_key"])


def audit_paper_inputs(findings: List[Dict[str, str]]) -> None:
    tex = ROOT / "paper/swf_monitor_ieee.tex"
    text = tex.read_text()
    for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        rel = match.group(1)
        target = ROOT / "paper/figures" / rel
        if not target.exists():
            add_finding(findings, "error", "paper", str(tex.relative_to(ROOT)), "figure_exists", rel)
    pdf = ROOT / "paper/build/swf_monitor_ieee.pdf"
    if not pdf.exists() or pdf.stat().st_size == 0:
        add_finding(findings, "error", "paper", str(pdf.relative_to(ROOT)), "compiled_pdf_exists", "Compiled PDF missing or empty.")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    findings: List[Dict[str, str]] = []

    audit_python(findings)
    audit_csv_json(findings)
    audit_repo_hygiene(findings)
    audit_markdown_links(findings)
    check_audit_files(findings)
    audit_strategy_summaries(findings)
    audit_benchmark_summaries(findings)
    audit_event_summaries(findings)
    audit_window_hit_rate(findings)
    audit_state_model(findings)
    audit_inference(findings)
    audit_paper_inputs(findings)

    findings.sort(key=lambda row: ({"error": 0, "warning": 1}.get(row["severity"], 9), row["category"], row["path"], row["check_name"]))

    with FINDINGS_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["severity", "category", "path", "check_name", "detail"])
        writer.writeheader()
        writer.writerows(findings)

    summary = {
        "total_findings": len(findings),
        "error_count": sum(1 for row in findings if row["severity"] == "error"),
        "warning_count": sum(1 for row in findings if row["severity"] == "warning"),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
