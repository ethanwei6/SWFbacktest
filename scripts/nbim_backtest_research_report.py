from __future__ import annotations

import csv
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "data" / "processed" / "nbim" / "backtests" / "analysis"
REPORTS_DIR = ROOT / "outputs" / "nbim" / "backtests" / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def escape(text: str) -> str:
    return html.escape(text)


def main() -> None:
    summary_rows = read_csv(ANALYSIS_DIR / "strategy_summary.csv")
    relative_rows = read_csv(ANALYSIS_DIR / "strategy_vs_benchmark_summary.csv")
    sanity_rows = read_csv(ANALYSIS_DIR / "strategy_sanity_checks.csv")

    summary = {row["strategy_key"]: row for row in summary_rows}
    relative = {row["strategy_key"]: row for row in relative_rows}
    sanity = {row["strategy_key"]: row for row in sanity_rows}

    strategy_order = ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"]
    best_realistic = max([relative["n3"], relative["n4"], relative["n5"], relative["n6"], relative["n7"], relative["n8"]], key=lambda row: to_float(row["excess_total_return"]))
    worst_realistic = min([relative["n3"], relative["n4"], relative["n5"], relative["n6"], relative["n7"], relative["n8"]], key=lambda row: to_float(row["excess_total_return"]))

    lines = [
        "# NBIM Alpha Backtest Report",
        "",
        "## Executive summary",
        "",
        "We tested eight lag-aware `NBIM` strategies using official publication dates, split-adjusted daily prices from Twelve Data for exact post-release execution, and month-end marks derived from the same daily source, with `VT` as the benchmark.",
        "",
        "The key result after checking the construction carefully is that the strongest raw outperformance comes from a **biased exploratory stock sleeve**, not from a clean investable `NBIM` signal. Once we move to more realistic sector-based strategies, the alpha picture becomes much smaller.",
        "",
        "The most credible positive strategies in this first pass are:",
        "",
        f"- `N4 Industry Weight-Change Tilt`: `{fmt_pct(to_float(relative['n4']['excess_total_return']))}` excess return vs `VT`",
        f"- `N6 Top-3 Industry Leaders`: `{fmt_pct(to_float(relative['n6']['excess_total_return']))}` excess return vs `VT`",
        "",
        "That is a useful signal, but it is modest rather than dramatic.",
        "",
        "## Important validation finding",
        "",
        "The original `NBIM` direct-mirror sleeve is **not clean alpha evidence**.",
        "",
        "Why:",
        "",
        "- The mirror universe was bounded to a hand-mapped recurring set of US mega-cap names.",
        "- That sleeve is almost identical across all snapshots and heavily concentrated in secular winners such as `Apple`, `Microsoft`, `Amazon`, `Alphabet`, `Meta`, `NVIDIA`, and `Tesla`.",
        "- This creates a clear survivor-selection / winner-selection bias even though the execution timing and price series themselves are internally correct.",
        "",
        "So `N1` and `N2` should be kept as exploratory reference cases, not as evidence that `NBIM` disclosure alone creates easy copy-trading alpha.",
        "",
        "## Method",
        "",
        "- Signal date: official `NBIM` annual or half-year publication date",
        "- Trade date: first tradable close strictly after public release",
        "- Marking convention: trade on the first post-release daily close, then carry the position at month-end closes until the next report",
        "- Benchmark: `VT`",
        "- Price source: `Twelve Data` adjusted daily history for the investable `NBIM` proxy universe",
        "",
        "## Strategy table",
        "",
        "| Strategy | Type | Total Return | Excess vs VT | Max Drawdown | Avg Cash |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]

    type_labels = {
        "n1": "Exploratory direct mirror",
        "n2": "Exploratory direct mirror",
        "n3": "Broad industry mirror",
        "n4": "Targeted industry rotation",
        "n5": "Targeted transition tilt",
        "n6": "Targeted industry concentration",
        "n7": "Targeted industry rotation",
        "n8": "Targeted consensus rotation",
    }

    for key in strategy_order:
        s = summary[key]
        r = relative[key]
        lines.append(
            f"| {s['strategy_name']} | {type_labels[key]} | {fmt_pct(to_float(s['total_return']))} | {fmt_pct(to_float(r['excess_total_return']))} | {fmt_pct(to_float(s['max_drawdown']))} | {fmt_pct(to_float(s['average_cash_weight']))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation by strategy family",
            "",
            "### Exploratory direct mirrors",
            "",
            f"- `N1` outperformed `VT` by `{fmt_pct(to_float(relative['n1']['excess_total_return']))}`, but this result is not reliable alpha evidence because the sleeve is a bounded basket of recurring US mega-cap winners.",
            f"- `N2` also outperformed by `{fmt_pct(to_float(relative['n2']['excess_total_return']))}` and suffers from the same bias.",
            "",
            "### Broad replication",
            "",
            f"- `N3` was almost benchmark-like, with only `{fmt_pct(to_float(relative['n3']['excess_total_return']))}` excess return. That suggests broad `NBIM` industry posture mostly recreates a high-quality global equity allocation rather than a strong standalone alpha stream.",
            "",
            "### Targeted sector strategies",
            "",
            f"- `N4` is the strongest realistic signal. Following the industries with the largest positive disclosed weight changes produced `{fmt_pct(to_float(relative['n4']['excess_total_return']))}` excess return. This suggests that **changes** in `NBIM`'s sector posture matter more than the level of its broad holdings.",
            f"- `N6` also worked reasonably well, with `{fmt_pct(to_float(relative['n6']['excess_total_return']))}` excess return, by simply concentrating on `NBIM`'s three largest sector exposures. This likely captures persistent quality/growth concentration without the noise of the full book.",
            f"- `N7` underperformed slightly by `{fmt_pct(to_float(relative['n7']['excess_total_return']))}`. Chasing the largest sector increases appears too reactive relative to the slower-moving `NBIM` disclosure cadence.",
            f"- `N8` underperformed by `{fmt_pct(to_float(relative['n8']['excess_total_return']))}` because the consensus filter is sparse and spends a lot of time in cash. It is probably too selective for a slow-moving disclosure dataset.",
            f"- `N5` was the weakest targeted signal, underperforming by `{fmt_pct(to_float(relative['n5']['excess_total_return']))}`. The accumulation-minus-reduction score appears too noisy at the industry level in this implementation.",
            "",
            "## Sanity checks",
            "",
            "The backtests passed the core arithmetic and exposure checks:",
            "",
        ]
    )

    for key in strategy_order:
        s = sanity[key]
        lines.append(
            f"- `{summary[key]['strategy_name']}`: negative cash breaches `{s['negative_cash_breach_count']}`, max gross exposure `{float(s['max_gross_exposure']):.3f}`, weight-integrity gap `{float(s['max_weight_integrity_gap']):.3e}`"
        )

    lines.extend(
        [
            "",
            "## Bottom line",
            "",
            "The current evidence does **not** support a strong claim that public `NBIM` disclosure enables easy copy-trading alpha.",
            "",
            "A more accurate summary is:",
            "",
            "- The eye-catching direct mirror outperformance is heavily biased by the hand-bounded stock universe and should not be treated as robust alpha.",
            f"- The best realistic signals are `N4` and `N6`, and both are only modestly positive at roughly `{fmt_pct(to_float(relative['n4']['excess_total_return']))}` to `{fmt_pct(to_float(relative['n6']['excess_total_return']))}` excess return vs `VT`.",
            "- The broad industry mirror is almost benchmark-like.",
            "- The transition-only and consensus-only sector filters are either weak or too sparse.",
            "",
            f"So the highest-confidence conclusion is that `NBIM` is more useful as a **slow-moving sector allocation / rotation signal** than as a literal copy-trading target. The realistic alpha we found is small, and only present in a narrow subset of targeted industry strategies. The strongest realistic positive strategy was `{best_realistic['strategy_name']}`; the weakest realistic one was `{worst_realistic['strategy_name']}`.",
        ]
    )

    markdown = "\n".join(lines) + "\n"

    html_lines = [
        "<html><body style='font-family: Arial, sans-serif; max-width: 980px; margin: 32px auto; line-height: 1.6;'>",
        "<h1>NBIM Alpha Backtest Report</h1>",
        "<h2>Executive Summary</h2>",
        "<p>We tested eight lag-aware NBIM strategies using official publication dates, split-adjusted daily prices from Twelve Data for exact post-release execution, and month-end marks derived from the same daily source, with VT as the benchmark.</p>",
        "<p>The key result after validation is that the strongest raw outperformance comes from a <strong>biased exploratory stock sleeve</strong>, not from a clean investable NBIM signal. Once we move to more realistic sector-based strategies, the alpha picture becomes much smaller.</p>",
        f"<p>The most credible positive strategies in this first pass are <strong>N4 Industry Weight-Change Tilt</strong> at <strong>{escape(fmt_pct(to_float(relative['n4']['excess_total_return'])))}</strong> excess return and <strong>N6 Top-3 Industry Leaders</strong> at <strong>{escape(fmt_pct(to_float(relative['n6']['excess_total_return'])))}</strong> excess return versus VT.</p>",
        "<h2>Important Validation Finding</h2>",
        "<p>The original NBIM direct-mirror sleeve is <strong>not clean alpha evidence</strong>.</p>",
        "<ul>",
        "<li>The mirror universe was bounded to a hand-mapped recurring set of US mega-cap names.</li>",
        "<li>That sleeve is almost identical across all snapshots and heavily concentrated in secular winners.</li>",
        "<li>This creates a survivor-selection / winner-selection bias even though the execution timing and price series are internally correct.</li>",
        "</ul>",
        "<p>N1 and N2 should therefore be treated as exploratory reference cases, not as evidence that NBIM disclosure alone creates easy copy-trading alpha.</p>",
        "<h2>Method</h2>",
        "<ul>",
        "<li>Signal date: official NBIM annual or half-year publication date</li>",
        "<li>Trade date: first tradable close strictly after public release</li>",
        "<li>Marking convention: trade on the first post-release daily close, then carry the position at month-end closes until the next report</li>",
        "<li>Benchmark: VT</li>",
        "<li>Price source: Twelve Data adjusted daily history for the investable NBIM proxy universe</li>",
        "</ul>",
        "<h2>Strategy Table</h2>",
        "<table border='1' cellpadding='6' cellspacing='0'><tr><th>Strategy</th><th>Type</th><th>Total Return</th><th>Excess vs VT</th><th>Max Drawdown</th><th>Avg Cash</th></tr>",
    ]

    for key in strategy_order:
        s = summary[key]
        r = relative[key]
        html_lines.append(
            f"<tr><td>{escape(s['strategy_name'])}</td><td>{escape(type_labels[key])}</td><td>{escape(fmt_pct(to_float(s['total_return'])))}</td><td>{escape(fmt_pct(to_float(r['excess_total_return'])))}</td><td>{escape(fmt_pct(to_float(s['max_drawdown'])))}</td><td>{escape(fmt_pct(to_float(s['average_cash_weight'])))}</td></tr>"
        )

    html_lines.extend(
        [
            "</table>",
            "<h2>Interpretation by Strategy Family</h2>",
            "<h3>Exploratory direct mirrors</h3>",
            f"<p>N1 outperformed VT by <strong>{escape(fmt_pct(to_float(relative['n1']['excess_total_return'])))}</strong>, but that result is not reliable alpha evidence because the sleeve is a bounded basket of recurring US mega-cap winners. N2 outperformed by <strong>{escape(fmt_pct(to_float(relative['n2']['excess_total_return'])))}</strong> and suffers from the same bias.</p>",
            "<h3>Broad replication</h3>",
            f"<p>N3 was almost benchmark-like, with only <strong>{escape(fmt_pct(to_float(relative['n3']['excess_total_return'])))}</strong> excess return. That suggests broad NBIM industry posture mostly recreates a high-quality global equity allocation rather than a strong standalone alpha stream.</p>",
            "<h3>Targeted sector strategies</h3>",
            f"<p>N4 is the strongest realistic signal. Following the industries with the largest positive disclosed weight changes produced <strong>{escape(fmt_pct(to_float(relative['n4']['excess_total_return'])))}</strong> excess return.</p>",
            f"<p>N6 also worked reasonably well, with <strong>{escape(fmt_pct(to_float(relative['n6']['excess_total_return'])))}</strong> excess return, by concentrating on NBIM's three largest sector exposures.</p>",
            f"<p>N7 underperformed slightly by <strong>{escape(fmt_pct(to_float(relative['n7']['excess_total_return'])))}</strong>. Chasing the largest sector increases appears too reactive relative to the slower-moving NBIM disclosure cadence.</p>",
            f"<p>N8 underperformed by <strong>{escape(fmt_pct(to_float(relative['n8']['excess_total_return'])))}</strong> because the consensus filter is sparse and spends a lot of time in cash.</p>",
            f"<p>N5 underperformed by <strong>{escape(fmt_pct(to_float(relative['n5']['excess_total_return'])))}</strong>. The accumulation-minus-reduction score appears too noisy at the industry level in this implementation.</p>",
            "<h2>Sanity Checks</h2><ul>",
        ]
    )

    for key in strategy_order:
        s = sanity[key]
        html_lines.append(
            f"<li>{escape(summary[key]['strategy_name'])}: negative cash breaches {escape(s['negative_cash_breach_count'])}, max gross exposure {float(s['max_gross_exposure']):.3f}, weight-integrity gap {float(s['max_weight_integrity_gap']):.3e}</li>"
        )

    html_lines.extend(
        [
            "</ul>",
            "<h2>Bottom Line</h2>",
            "<p>The current evidence does <strong>not</strong> support a strong claim that public NBIM disclosure enables easy copy-trading alpha.</p>",
            "<ul>",
            "<li>The eye-catching direct mirror outperformance is heavily biased by the hand-bounded stock universe.</li>",
            f"<li>The best realistic signals are N4 and N6, and both are only modestly positive at roughly {escape(fmt_pct(to_float(relative['n4']['excess_total_return'])))} to {escape(fmt_pct(to_float(relative['n6']['excess_total_return'])))} excess return vs VT.</li>",
            "<li>The broad industry mirror is almost benchmark-like.</li>",
            "<li>The transition-only and consensus-only sector filters are either weak or too sparse.</li>",
            "</ul>",
            f"<p>The highest-confidence conclusion is therefore that NBIM is more useful as a <strong>slow-moving sector allocation / rotation signal</strong> than as a literal copy-trading target. The strongest realistic positive strategy was <strong>{escape(best_realistic['strategy_name'])}</strong>; the weakest realistic one was <strong>{escape(worst_realistic['strategy_name'])}</strong>.</p>",
            "</body></html>",
        ]
    )

    write_text(REPORTS_DIR / "nbim_backtest_research_report.md", markdown)
    write_text(REPORTS_DIR / "nbim_backtest_research_report.html", "".join(html_lines))
    print("Built NBIM research report.")


if __name__ == "__main__":
    main()
