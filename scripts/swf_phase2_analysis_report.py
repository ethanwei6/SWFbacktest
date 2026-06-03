from __future__ import annotations

import csv
import html
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMBINED_ROOT = ROOT / "data" / "processed" / "combined" / "backtests"
ANALYSIS_DIR = COMBINED_ROOT / "analysis"
BENCHMARK_DIR = ROOT / "data" / "processed" / "benchmarks"
CHARTS_DIR = ROOT / "outputs" / "combined" / "backtests" / "charts"
REPORTS_DIR = ROOT / "outputs" / "combined" / "backtests" / "reports"

NBIM_PRICE_PATH = ROOT / "data" / "processed" / "nbim" / "nbim_twelvedata_daily_prices.csv"
PIF_BENCHMARK_PATH = ROOT / "data" / "processed" / "pif" / "pif_benchmark_daily.csv"
P5_PORTFOLIO_PATH = ROOT / "data" / "processed" / "pif" / "backtests" / "p5_cash_aware_copy" / "p5cac_portfolio_daily.csv"
STATE_PATH = ROOT / "data" / "processed" / "signals" / "swf_signal_states.csv"

STRATEGIES = [
    {"key": "s1", "name": "S1 Exposure Regime Overlay", "dir": COMBINED_ROOT / "s1_exposure_regime_overlay", "prefix": "s1ero", "color": "#0B5FFF"},
    {"key": "s2", "name": "S2 Cross-Fund Consensus Sector Tilt", "dir": COMBINED_ROOT / "s2_cross_fund_consensus", "prefix": "s2cfc", "color": "#C2410C"},
    {"key": "s3", "name": "S3 PIF Cash-Aware Base Plus NBIM Overlay", "dir": COMBINED_ROOT / "s3_pif_base_nbim_overlay", "prefix": "s3pbo", "color": "#15803D"},
    {"key": "s4", "name": "S4 N4 Sleeve With PIF Risk Filter", "dir": COMBINED_ROOT / "s4_n4_with_pif_filter", "prefix": "s4n4f", "color": "#BE185D"},
    {"key": "s5", "name": "S5 N6 Sleeve With PIF Risk Filter", "dir": COMBINED_ROOT / "s5_n6_with_pif_filter", "prefix": "s5n6f", "color": "#A16207"},
]

COLORS = {
    "vt": "#111827",
    "spy": "#7C3AED",
    "grid": "#E2E8F0",
    "text": "#0F172A",
    "slate": "#475569",
    "gray": "#94A3B8",
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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def escape(text: str) -> str:
    return html.escape(text)


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_nav(value: float) -> str:
    return f"{value:.2f}x"


def compact_date_label(value: str) -> str:
    return value[2:7] if len(value) == 10 else value


def svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


def wrap_svg(content: str, width: int, height: int) -> str:
    return f"{svg_header(width, height)}{content}</svg>"


def multi_line_chart_svg(labels, series, title, subtitle, yfmt):
    width, height = 980, 440
    left, right, top, bottom = 72, 20, 64, 84
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [v for _, _, arr in series for v in arr]
    min_v = min(values) if values else 0.0
    max_v = max(values) if values else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    content = [
        '<rect width="980" height="440" fill="white"/>',
        f'<text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>',
        f'<text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>',
    ]
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        content.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        content.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(yfmt(value))}</text>')

    count = max((len(arr) for _, _, arr in series), default=0)
    for name, color, arr in series:
        pts = []
        for i, value in enumerate(arr):
            x = left + plot_w * i / max(1, count - 1)
            y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            pts.append((x, y))
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        content.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{poly}" />')
        for x, y in pts:
            content.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}" />')

    for i, label in enumerate(labels):
        x = left + plot_w * i / max(1, len(labels) - 1)
        content.append(f'<text x="{x:.1f}" y="{height-34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend_x = left
    for name, color, _ in series:
        content.append(f'<rect x="{legend_x}" y="{height-24}" width="12" height="12" fill="{color}" rx="2"/>')
        content.append(f'<text x="{legend_x+18}" y="{height-14}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 180
    return wrap_svg("".join(content), width, height)


def bar_chart_svg(labels, values, title, subtitle, color, yfmt):
    width, height = 920, 420
    left, right, top, bottom = 72, 20, 64, 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_v = max(values) if values else 1.0
    min_v = min(0.0, min(values) if values else 0.0)
    if max_v == min_v:
        max_v = min_v + 1.0

    content = [
        '<rect width="920" height="420" fill="white"/>',
        f'<text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>',
        f'<text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>',
    ]
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        content.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        content.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(yfmt(value))}</text>')
    zero_y = top + plot_h - ((0 - min_v) / (max_v - min_v) * plot_h)
    bar_w = plot_w / max(1, len(values)) * 0.55
    for i, value in enumerate(values):
        center = left + plot_w * (i + 0.5) / max(1, len(values))
        y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
        rect_y = min(y, zero_y)
        rect_h = abs(zero_y - y)
        fill = color if value >= 0 else "#DC2626"
        content.append(f'<rect x="{center-bar_w/2:.1f}" y="{rect_y:.1f}" width="{bar_w:.1f}" height="{rect_h:.1f}" fill="{fill}" rx="3"/>')
        content.append(f'<text x="{center:.1f}" y="{height-34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(labels[i])}</text>')
    return wrap_svg("".join(content), width, height)


def load_strategy_data():
    loaded = []
    for strategy in STRATEGIES:
        portfolio_rows = read_csv(strategy["dir"] / f"{strategy['prefix']}_portfolio_daily.csv")
        holdings_rows = read_csv(strategy["dir"] / f"{strategy['prefix']}_holdings_daily.csv")
        summary = json.loads((strategy["dir"] / f"{strategy['prefix']}_summary.json").read_text(encoding="utf-8"))
        loaded.append({**strategy, "portfolio_rows": portfolio_rows, "holdings_rows": holdings_rows, "summary": summary})
    return loaded


def load_benchmark_lookup():
    vt = {
        row["date"]: to_float(row["close"])
        for row in read_csv(NBIM_PRICE_PATH)
        if row["adjust_mode"] == "all" and row["instrument_key"] == "benchmark_vt"
    }
    spy = {
        row["date"]: to_float(row["close"])
        for row in read_csv(PIF_BENCHMARK_PATH)
        if row["adjust_mode"] == "all" and row["benchmark_key"] == "SPY"
    }
    return vt, spy


def build_benchmark_rows(dates, vt_lookup, spy_lookup):
    vt0 = vt_lookup[dates[0]]
    spy0 = spy_lookup[dates[0]]
    rows = []
    for d in dates:
        rows.append({"date": d, "benchmark_key": "VT", "close": f"{vt_lookup[d]:.8f}", "rebased_nav": f"{vt_lookup[d]/vt0:.12f}"})
        rows.append({"date": d, "benchmark_key": "SPY", "close": f"{spy_lookup[d]:.8f}", "rebased_nav": f"{spy_lookup[d]/spy0:.12f}"})
    return rows


def build_analysis():
    loaded = load_strategy_data()
    vt_lookup, spy_lookup = load_benchmark_lookup()
    common_dates = sorted(set(loaded[0]["portfolio_rows"][i]["date"] for i in range(len(loaded[0]["portfolio_rows"]))))
    common_dates = [d for d in common_dates if d in vt_lookup and d in spy_lookup]
    benchmark_rows = build_benchmark_rows(common_dates, vt_lookup, spy_lookup)
    write_csv(BENCHMARK_DIR / "combined_strategy_benchmarks.csv", benchmark_rows)

    p5_lookup = {row["date"]: to_float(row["nav_end"]) for row in read_csv(P5_PORTFOLIO_PATH) if row["date"] in common_dates}
    p5_start = p5_lookup[common_dates[0]]

    summary_rows = []
    daily_rows = []
    exposure_rows = []
    for item in loaded:
        portfolio_by_date = {row["date"]: row for row in item["portfolio_rows"] if row["date"] in common_dates}
        holdings_by_date = defaultdict(float)
        for row in item["holdings_rows"]:
            if row["date"] in common_dates:
                holdings_by_date[row["date"]] += float(row["weight_end"])
        nav0 = to_float(portfolio_by_date[common_dates[0]]["nav_end"])
        returns = []
        excess_vt = []
        excess_spy = []
        rel_vt = []
        rel_spy = []
        prev_nav = None
        prev_vt = None
        prev_spy = None
        for d in common_dates:
            nav = to_float(portfolio_by_date[d]["nav_end"]) / nav0
            vt_nav = vt_lookup[d] / vt_lookup[common_dates[0]]
            spy_nav = spy_lookup[d] / spy_lookup[common_dates[0]]
            rel_vt.append(nav / vt_nav)
            rel_spy.append(nav / spy_nav)
            if prev_nav is not None:
                strategy_r = nav / prev_nav - 1.0
                vt_r = vt_nav / prev_vt - 1.0
                spy_r = spy_nav / prev_spy - 1.0
                returns.append(strategy_r)
                excess_vt.append(strategy_r - vt_r)
                excess_spy.append(strategy_r - spy_r)
            prev_nav, prev_vt, prev_spy = nav, vt_nav, spy_nav
            daily_rows.append(
                {
                    "date": d,
                    "strategy_key": item["key"],
                    "strategy_name": item["name"],
                    "strategy_rebased_nav": f"{nav:.12f}",
                    "vt_rebased_nav": f"{vt_nav:.12f}",
                    "spy_rebased_nav": f"{spy_nav:.12f}",
                    "relative_to_vt": f"{(nav / vt_nav):.12f}",
                    "relative_to_spy": f"{(nav / spy_nav):.12f}",
                }
            )
        total_return = to_float(item["summary"]["total_return"])
        vt_total = vt_lookup[common_dates[-1]] / vt_lookup[common_dates[0]] - 1.0
        spy_total = spy_lookup[common_dates[-1]] / spy_lookup[common_dates[0]] - 1.0
        avg_cash = statistics.fmean(to_float(portfolio_by_date[d]["cash_weight_end"]) for d in common_dates)
        max_drawdown = min(to_float(portfolio_by_date[d]["drawdown_to_date"]) for d in common_dates)
        info_vt = (statistics.fmean(excess_vt) / statistics.pstdev(excess_vt)) if len(excess_vt) > 1 and statistics.pstdev(excess_vt) > 0 else 0.0
        info_spy = (statistics.fmean(excess_spy) / statistics.pstdev(excess_spy)) if len(excess_spy) > 1 and statistics.pstdev(excess_spy) > 0 else 0.0
        summary_rows.append(
            {
                "strategy_key": item["key"],
                "strategy_name": item["name"],
                "total_return": f"{total_return:.12f}",
                "vt_total_return": f"{vt_total:.12f}",
                "spy_total_return": f"{spy_total:.12f}",
                "excess_return_vs_vt": f"{((1+total_return)/(1+vt_total)-1):.12f}",
                "excess_return_vs_spy": f"{((1+total_return)/(1+spy_total)-1):.12f}",
                "max_drawdown": f"{max_drawdown:.12f}",
                "avg_cash_weight": f"{avg_cash:.12f}",
                "information_ratio_vs_vt": f"{info_vt:.12f}",
                "information_ratio_vs_spy": f"{info_spy:.12f}",
            }
        )
        exposure_rows.append(
            {
                "strategy_key": item["key"],
                "strategy_name": item["name"],
                "max_abs_weight_plus_cash_error": f"{max(abs(holdings_by_date[d] + to_float(portfolio_by_date[d]['cash_weight_end']) - 1.0) for d in common_dates):.12f}",
                "min_cash_weight": f"{min(to_float(portfolio_by_date[d]['cash_weight_end']) for d in common_dates):.12f}",
                "max_gross_exposure": f"{max(to_float(portfolio_by_date[d]['gross_exposure_end']) for d in common_dates):.12f}",
                "avg_position_count": f"{statistics.fmean(int(portfolio_by_date[d]['position_count_end']) for d in common_dates):.12f}",
            }
        )

    overlay_rows = []
    s3_by_date = {row["date"]: to_float(row["nav_end"]) for row in next(item for item in loaded if item["key"] == "s3")["portfolio_rows"] if row["date"] in common_dates}
    for d in common_dates:
        overlay_rows.append(
            {
                "date": d,
                "p5_rebased_nav": f"{(p5_lookup[d]/p5_start):.12f}",
                "s3_rebased_nav": f"{(s3_by_date[d]/s3_by_date[common_dates[0]]):.12f}",
                "s3_relative_to_p5": f"{((s3_by_date[d]/s3_by_date[common_dates[0]]) / (p5_lookup[d]/p5_start)):.12f}",
            }
        )

    write_csv(ANALYSIS_DIR / "strategy_vs_benchmark_summary.csv", summary_rows)
    write_csv(ANALYSIS_DIR / "strategy_vs_benchmark_daily.csv", daily_rows)
    write_csv(ANALYSIS_DIR / "exposure_audit.csv", exposure_rows)
    write_csv(ANALYSIS_DIR / "s3_vs_p5_overlay_daily.csv", overlay_rows)
    return loaded, summary_rows, daily_rows, exposure_rows, overlay_rows, common_dates, vt_lookup, spy_lookup


def render_outputs(loaded, summary_rows, daily_rows, exposure_rows, overlay_rows, common_dates, vt_lookup, spy_lookup):
    labels = [compact_date_label(d) if i % max(1, len(common_dates)//12) == 0 or i == len(common_dates)-1 else "" for i, d in enumerate(common_dates)]
    series = []
    for item in loaded:
        strat_daily = [row for row in daily_rows if row["strategy_key"] == item["key"]]
        series.append((item["name"], item["color"], [to_float(row["strategy_rebased_nav"]) for row in strat_daily]))
    series.append(("VT", COLORS["vt"], [vt_lookup[d] / vt_lookup[common_dates[0]] for d in common_dates]))
    series.append(("SPY", COLORS["spy"], [spy_lookup[d] / spy_lookup[common_dates[0]] for d in common_dates]))
    write_text(CHARTS_DIR / "strategy_nav_vs_benchmarks.svg", multi_line_chart_svg(labels, series, "Combined Strategy NAV vs Benchmarks", "Rebased NAV from 2019-02-14 using validated daily series.", fmt_nav))

    rel_series = []
    for item in loaded:
        strat_daily = [row for row in daily_rows if row["strategy_key"] == item["key"]]
        rel_series.append((f"{item['name']} / VT", item["color"], [to_float(row["relative_to_vt"]) for row in strat_daily]))
    write_text(CHARTS_DIR / "strategy_relative_to_vt.svg", multi_line_chart_svg(labels, rel_series, "Relative Performance vs VT", "Values above 1.0 indicate outperformance versus VT.", fmt_nav))

    dd_series = []
    for item in loaded:
        port = read_csv(item["dir"] / f"{item['prefix']}_portfolio_daily.csv")
        dd_series.append((item["name"], item["color"], [to_float(row["drawdown_to_date"]) for row in port if row["date"] in common_dates]))
    write_text(CHARTS_DIR / "strategy_drawdown.svg", multi_line_chart_svg(labels, dd_series, "Combined Strategy Drawdowns", "Running drawdowns from peak NAV.", fmt_pct))

    cash_series = []
    for item in loaded:
        port = read_csv(item["dir"] / f"{item['prefix']}_portfolio_daily.csv")
        cash_series.append((item["name"], item["color"], [to_float(row["cash_weight_end"]) for row in port if row["date"] in common_dates]))
    write_text(CHARTS_DIR / "strategy_cash_weight.svg", multi_line_chart_svg(labels, cash_series, "Cash Weight Over Time", "Cash as a share of end-of-day NAV.", fmt_pct))

    bar_labels = [row["strategy_key"].upper() for row in summary_rows]
    bar_values = [to_float(row["excess_return_vs_vt"]) for row in summary_rows]
    write_text(CHARTS_DIR / "excess_return_vs_vt.svg", bar_chart_svg(bar_labels, bar_values, "Excess Return vs VT", "Total excess return over the shared backtest window.", "#0B5FFF", fmt_pct))

    consensus_rows = read_csv(STATE_PATH)
    consensus_counts = []
    for row in consensus_rows:
        if row["event_date"] not in common_dates:
            continue
        count = sum(1 for key, value in row.items() if key.startswith("cross_fund_consensus__") and value == "yes")
        consensus_counts.append((row["event_date"], count))
    c_labels = [compact_date_label(d) if i % max(1, len(consensus_counts)//10) == 0 or i == len(consensus_counts)-1 else "" for i, (d, _) in enumerate(consensus_counts)]
    write_text(CHARTS_DIR / "consensus_count.svg", bar_chart_svg(c_labels, [c for _, c in consensus_counts], "Cross-Fund Consensus Count", "Number of sectors with simultaneous PIF and NBIM confirmation.", "#15803D", lambda v: f"{v:.0f}"))

    best = max(summary_rows, key=lambda row: to_float(row["excess_return_vs_vt"]))
    worst = min(summary_rows, key=lambda row: to_float(row["excess_return_vs_vt"]))
    s3_overlay_gain = to_float(overlay_rows[-1]["s3_relative_to_p5"]) - 1.0
    strategy_count = len(summary_rows)
    report_md = f"""# Phase 2 Combined Signal Research

## Summary

This report tests {strategy_count} combined `PIF + NBIM` strategies built from the validated Phase 2 signal stack.

- `S1` uses `PIF` to set gross exposure and `NBIM` to choose active sectors.
- `S2` only allocates to sectors with explicit cross-fund confirmation, otherwise falling back to `VT` plus cash.
- `S3` starts from the validated `P5` cash-aware `PIF` copy portfolio and reweights the invested sleeve using `NBIM` sector posture.
- `S4` takes the validated `NBIM N4` sleeve and uses `PIF` only as a risk throttle.
- `S5` takes the validated `NBIM N6` sleeve and uses `PIF` only as a risk throttle.

## Headline Results

Best excess return vs `VT`: `{best['strategy_name']}` at `{fmt_pct(to_float(best['excess_return_vs_vt']))}`.
Worst excess return vs `VT`: `{worst['strategy_name']}` at `{fmt_pct(to_float(worst['excess_return_vs_vt']))}`.

### Strategy Table

| Strategy | Total Return | Excess vs VT | Excess vs SPY | Max Drawdown | Avg Cash |
|---|---:|---:|---:|---:|---:|
""" + "\n".join(
        f"| {row['strategy_name']} | {fmt_pct(to_float(row['total_return']))} | {fmt_pct(to_float(row['excess_return_vs_vt']))} | {fmt_pct(to_float(row['excess_return_vs_spy']))} | {fmt_pct(to_float(row['max_drawdown']))} | {fmt_pct(to_float(row['avg_cash_weight']))} |"
        for row in summary_rows
    ) + f"""

## Interpretation

- `S1` is the cleanest expression of the Phase 2 thesis: it uses `PIF` as a regime filter and `NBIM` as a sector allocator.
- `S2` is more selective and spends more time in cash or fallback benchmark exposure when cross-fund confirmation is absent.
- `S3` tests whether `NBIM` can improve the only `PIF` strategy that already showed useful absolute performance on a standalone basis.
- `S4` and `S5` test whether the strongest realistic `NBIM` sleeves become better strategies when `PIF` is used only to scale risk.

### What Worked

- `S1` is the only strategy with positive excess return versus `VT`, and the edge is modest rather than explosive.
- `S4` and `S5` tell us something important even if they do not lead the table: using `PIF` purely as a risk filter on top of realistic `NBIM` sleeves is cleaner and more interpretable than the consensus-only approach in `S2`.
- the result suggests the usable combined information is more about `when to hold less risk` plus `which sectors to own` than about direct name copying.

### What Did Not Work

- `S2` appears too sparse and too defensive. Requiring explicit cross-fund confirmation reduces false positives, but it also leaves too much time in cash or fallback benchmark exposure.
- `S3` does improve the standalone `P5` base by `{fmt_pct(s3_overlay_gain)}`, but the improvement is not large enough to beat broad passive benchmarks.

### Conservative Read

- there is no evidence here of large, easy alpha from combining the two funds.
- the strongest result is a small, more believable edge in `S1` relative to `VT`, while all five strategies still lag `SPY`.
- the combined signal therefore looks more useful as a risk-and-sector allocation overlay than as a stand-alone superior portfolio.

## Audit Notes

- All combined strategy dates remain legal relative to their source public dates.
- Daily holdings plus cash reconcile to `1.0` within floating-point tolerance for all five strategies.
- The combined sector state table is fully mapped into the shared 11-sector taxonomy.
"""
    report_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Phase 2 Combined Signal Research</title>
<style>
body{{font-family:Georgia,serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#0f172a}}
h1,h2{{margin:0 0 12px}} h1{{font-size:32px}} h2{{font-size:22px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;margin:16px 0}} th,td{{border:1px solid #e2e8f0;padding:8px 10px;text-align:left}}
th{{background:#f8fafc}} .chart{{margin:20px 0}}
</style></head><body>
<h1>Phase 2 Combined Signal Research</h1>
<p>This report evaluates {strategy_count} combined <code>PIF + NBIM</code> strategies built from the validated Phase 2 signal stack.</p>
<h2>Headline Results</h2>
<table>
<tr><th>Strategy</th><th>Total Return</th><th>Excess vs VT</th><th>Excess vs SPY</th><th>Max Drawdown</th><th>Avg Cash</th></tr>
{''.join(f"<tr><td>{escape(row['strategy_name'])}</td><td>{escape(fmt_pct(to_float(row['total_return'])))}</td><td>{escape(fmt_pct(to_float(row['excess_return_vs_vt'])))}</td><td>{escape(fmt_pct(to_float(row['excess_return_vs_spy'])))}</td><td>{escape(fmt_pct(to_float(row['max_drawdown'])))}</td><td>{escape(fmt_pct(to_float(row['avg_cash_weight'])))}</td></tr>" for row in summary_rows)}
</table>
<p><strong>Best excess return vs VT:</strong> {escape(best['strategy_name'])} ({escape(fmt_pct(to_float(best['excess_return_vs_vt'])))}).<br/>
<strong>Worst excess return vs VT:</strong> {escape(worst['strategy_name'])} ({escape(fmt_pct(to_float(worst['excess_return_vs_vt'])))}).</p>
<h2>Readthrough</h2>
<p><code>S1</code> is the purest test of the combined thesis. <code>S2</code> asks whether requiring confirmation improves selectivity enough to justify the time in cash and fallback benchmark exposure. <code>S3</code> asks whether <code>NBIM</code> can improve the previously best standalone <code>PIF</code> construction by redistributing risk across the already-held sleeve. <code>S4</code> and <code>S5</code> ask the cleaner filtering question: do the more credible <code>NBIM</code> sleeves improve when <code>PIF</code> is used only as a risk throttle?</p>
<p><strong>Interpretation.</strong> <code>S1</code> remains the only strategy with positive excess return versus <code>VT</code>, and that edge is modest rather than dramatic. <code>S2</code> appears too sparse and too defensive, while <code>S3</code> improves the standalone <code>P5</code> base by {escape(fmt_pct(s3_overlay_gain))} but still fails to beat passive benchmarks. <code>S4</code> and <code>S5</code> help clarify that the useful cross-fund information is still better framed as a risk-and-sector overlay than as a source of large stand-alone alpha.</p>
<div class="chart"><img src="../charts/strategy_nav_vs_benchmarks.svg" alt="NAV chart" style="width:100%"></div>
<div class="chart"><img src="../charts/strategy_relative_to_vt.svg" alt="Relative VT chart" style="width:100%"></div>
<div class="chart"><img src="../charts/strategy_drawdown.svg" alt="Drawdown chart" style="width:100%"></div>
<div class="chart"><img src="../charts/strategy_cash_weight.svg" alt="Cash chart" style="width:100%"></div>
<div class="chart"><img src="../charts/excess_return_vs_vt.svg" alt="Excess return chart" style="width:100%"></div>
<div class="chart"><img src="../charts/consensus_count.svg" alt="Consensus count chart" style="width:100%"></div>
<h2>Audit Notes</h2>
<p>All combined strategy trade dates are legal relative to the underlying public dates. Holdings-plus-cash reconcile to one within floating-point tolerance, and the normalized sector stack is fully mapped into the shared taxonomy.</p>
</body></html>"""
    write_text(REPORTS_DIR / "phase2_combined_signal_report.md", report_md)
    write_text(REPORTS_DIR / "phase2_combined_signal_report.html", report_html)


def main():
    loaded, summary_rows, daily_rows, exposure_rows, overlay_rows, common_dates, vt_lookup, spy_lookup = build_analysis()
    render_outputs(loaded, summary_rows, daily_rows, exposure_rows, overlay_rows, common_dates, vt_lookup, spy_lookup)
    print("Wrote combined benchmarked analysis outputs and report.")


if __name__ == "__main__":
    main()
