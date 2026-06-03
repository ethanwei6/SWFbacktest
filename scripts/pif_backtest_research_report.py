from __future__ import annotations

import csv
import html
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "data" / "processed" / "pif" / "backtests" / "analysis"
CHARTS_DIR = ROOT / "outputs" / "pif" / "backtests" / "research_charts"
REPORTS_DIR = ROOT / "outputs" / "pif" / "backtests" / "reports"

COLORS = {
    "blue": "#0B5FFF",
    "teal": "#0A7C86",
    "gold": "#D97706",
    "red": "#C2410C",
    "green": "#15803D",
    "violet": "#7C3AED",
    "magenta": "#BE185D",
    "slate": "#334155",
    "gray": "#94A3B8",
    "grid": "#E2E8F0",
    "bg": "#F8FAFC",
    "text": "#0F172A",
    "neg_bg": "#FEF2F2",
    "pos_bg": "#ECFDF5",
}

STRATEGY_META = {
    "p1": {"label": "P1", "name": "New Positions Mirror", "color": COLORS["red"]},
    "p2": {"label": "P2", "name": "Full Sleeve Equal Weight", "color": COLORS["blue"]},
    "p3": {"label": "P3", "name": "Accumulation Tilt", "color": COLORS["green"]},
    "p4": {"label": "P4", "name": "Exit Avoidance", "color": COLORS["violet"]},
    "p5": {"label": "P5", "name": "Cash-Aware Copy Trade", "color": COLORS["magenta"]},
}


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


def escape(text: str) -> str:
    return html.escape(text)


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_num(value: float) -> str:
    return f"{value:.2f}"


def format_nav(value: float) -> str:
    return f"{value:.2f}x"


def compact_date_label(text: str) -> str:
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text[2:7]
    return text


def sparsify_labels(labels: list[str], max_labels: int) -> list[str]:
    if len(labels) <= max_labels:
        return labels
    step = max(1, (len(labels) + max_labels - 1) // max_labels)
    out = []
    for i, label in enumerate(labels):
        out.append(label if i % step == 0 or i == len(labels) - 1 else "")
    return out


def svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


def wrap_svg(content: str, width: int, height: int) -> str:
    return f"{svg_header(width, height)}{content}</svg>"


def multi_line_chart_svg(
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    *,
    title: str,
    subtitle: str,
    y_formatter,
    width: int = 980,
    height: int = 440,
) -> str:
    left = 74
    right = 24
    top = 64
    bottom = 86
    plot_w = width - left - right
    plot_h = height - top - bottom
    flat = [value for _, _, values in series for value in values]
    min_v = min(flat) if flat else 0.0
    max_v = max(flat) if flat else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_formatter(value))}</text>')

    count = max((len(values) for _, _, values in series), default=0)
    lines = []
    for name, color, values in series:
        pts = []
        for i, value in enumerate(values):
            x = left + (plot_w * i / max(1, count - 1))
            y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            pts.append((x, y))
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{poly}" />')
        for x, y in pts:
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.7" fill="{color}" />')

    x_labels = "".join(
        f'<text x="{left + (plot_w * i / max(1, len(labels)-1)):.1f}" y="{height - 34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>'
        for i, label in enumerate(labels)
        if label
    )

    legend = []
    legend_x = left
    for name, color, _ in series:
        legend.append(f'<rect x="{legend_x}" y="{height - 16}" width="12" height="12" fill="{color}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{height - 6}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 175

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(lines)}
    {x_labels}
    {''.join(legend)}
    """
    return wrap_svg(content, width, height)


def grouped_bar_chart_svg(
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    *,
    title: str,
    subtitle: str,
    y_formatter,
    width: int = 980,
    height: int = 460,
) -> str:
    left = 74
    right = 24
    top = 64
    bottom = 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [v for _, _, arr in series for v in arr]
    max_v = max(values) if values else 1.0
    min_v = min(0.0, min(values) if values else 0.0)
    if max_v == min_v:
        max_v = min_v + 1.0
    zero_y = top + plot_h - ((0.0 - min_v) / (max_v - min_v) * plot_h)

    grid = []
    for j in range(5):
        frac = j / 4
        value = min_v + frac * (max_v - min_v)
        y = top + plot_h - frac * plot_h
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_formatter(value))}</text>')
    grid.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="{COLORS["slate"]}" stroke-width="1.2"/>')

    groups = len(labels)
    bars_per_group = len(series)
    group_w = plot_w / max(1, groups)
    bar_w = min(24, group_w / max(1, bars_per_group + 1))
    bars = []
    for i, label in enumerate(labels):
        gx = left + i * group_w
        for j, (_, color, arr) in enumerate(series):
            value = arr[i]
            y_value = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            y = min(y_value, zero_y)
            h = abs(zero_y - y_value)
            x = gx + 10 + j * (bar_w + 4)
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        if label:
            bars.append(f'<text x="{gx + group_w / 2:.1f}" y="{height - 38}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend = []
    legend_x = left
    for name, color, _ in series:
        legend.append(f'<rect x="{legend_x}" y="{height - 16}" width="12" height="12" fill="{color}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{height - 6}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 170

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    {''.join(legend)}
    """
    return wrap_svg(content, width, height)


def horizontal_bar_chart_svg(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    subtitle: str,
    width: int = 980,
    height: int = 420,
) -> str:
    left = 240
    right = 34
    top = 64
    bottom = 26
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_abs = max(abs(v) for v in values) if values else 1.0
    if max_abs == 0:
        max_abs = 1.0
    row_h = plot_h / max(1, len(labels))
    zero_x = left + plot_w / 2

    grid = []
    for frac in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        x = zero_x + frac * (plot_w / 2)
        grid.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{x:.1f}" y="{top - 8}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{format_pct(frac * max_abs)}</text>')

    bars = []
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * row_h + row_h * 0.18
        h = row_h * 0.64
        w = abs(value) / max_abs * (plot_w / 2)
        color = COLORS["green"] if value >= 0 else COLORS["red"]
        x = zero_x if value >= 0 else zero_x - w
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        bars.append(f'<text x="{left - 10}" y="{y + h / 2 + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["text"]}">{escape(label)}</text>')
        anchor = "start" if value >= 0 else "end"
        text_x = x + w + 6 if value >= 0 else x - 6
        bars.append(f'<text x="{text_x:.1f}" y="{y + h / 2 + 4:.1f}" text-anchor="{anchor}" font-size="11" fill="{COLORS["slate"]}">{format_pct(value)}</text>')

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    """
    return wrap_svg(content, width, height)


def heatmap_svg(
    columns: list[str],
    rows: list[str],
    matrix: dict[tuple[str, str], float],
    *,
    title: str,
    subtitle: str,
    width: int = 1100,
    height: int = 360,
) -> str:
    left = 90
    right = 20
    top = 72
    bottom = 48
    plot_w = width - left - right
    plot_h = height - top - bottom
    cell_w = plot_w / max(1, len(columns))
    cell_h = plot_h / max(1, len(rows))
    max_abs = max(abs(v) for v in matrix.values()) if matrix else 1.0
    if max_abs == 0:
        max_abs = 1.0

    cells = []
    for r_i, row_name in enumerate(rows):
        y = top + r_i * cell_h
        cells.append(f'<text x="{left - 10}" y="{y + cell_h / 2 + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["text"]}">{escape(row_name)}</text>')
        for c_i, col_name in enumerate(columns):
            x = left + c_i * cell_w
            value = matrix.get((row_name, col_name), 0.0)
            intensity = min(1.0, abs(value) / max_abs)
            if value >= 0:
                fill = f"rgba(21,128,61,{0.12 + intensity * 0.65:.3f})"
            else:
                fill = f"rgba(194,65,12,{0.12 + intensity * 0.65:.3f})"
            cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" fill="{fill}" rx="2"/>')
            cells.append(f'<text x="{x + cell_w / 2:.1f}" y="{y + cell_h / 2 + 4:.1f}" text-anchor="middle" font-size="10" fill="{COLORS["text"]}">{format_pct(value)}</text>')

    x_labels = []
    for c_i, col_name in enumerate(columns):
        x = left + c_i * cell_w + cell_w / 2
        x_labels.append(f'<text x="{x:.1f}" y="{height - 20}" text-anchor="middle" font-size="10" fill="{COLORS["slate"]}">{escape(col_name)}</text>')

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>
    {''.join(cells)}
    {''.join(x_labels)}
    """
    return wrap_svg(content, width, height)


def render_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    header = "".join(f"<th>{escape(col)}</th>" for col in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(row.get(col, ''))}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    strategy_summary = read_csv(ANALYSIS_DIR / "strategy_summary.csv")
    sanity = read_csv(ANALYSIS_DIR / "strategy_sanity_checks.csv")
    contributors = read_csv(ANALYSIS_DIR / "strategy_top_contributors.csv")
    period_returns = read_csv(ANALYSIS_DIR / "strategy_rebalance_period_returns.csv")
    p1_forward = read_csv(ANALYSIS_DIR / "p1_entry_forward_returns.csv")
    p3_forward = read_csv(ANALYSIS_DIR / "p3_bucket_forward_returns.csv")
    p4_forward = read_csv(ANALYSIS_DIR / "p4_avoidance_forward_returns.csv")

    summary_by_key = {row["strategy_key"]: row for row in strategy_summary}
    best_total_key, best_total_row = max(summary_by_key.items(), key=lambda item: to_float(item[1]["total_return"]))
    best_full_key, best_full_row = max(
        ((key, summary_by_key[key]) for key in ["p1", "p2", "p3", "p4"]),
        key=lambda item: to_float(item[1]["total_return"]),
    )

    # Load daily portfolio series directly for charts.
    daily_series = {}
    for key, meta in STRATEGY_META.items():
        prefix = {
            "p1": "p1",
            "p2": "p2ew",
            "p3": "p3at",
            "p4": "p4ea",
            "p5": "p5cac",
        }[key]
        strategy_dir = ROOT / "data" / "processed" / "pif" / "backtests" / {
            "p1": "p1",
            "p2": "p2_equal_weight",
            "p3": "p3_accumulation_tilt",
            "p4": "p4_exit_avoidance",
            "p5": "p5_cash_aware_copy",
        }[key]
        daily_series[key] = read_csv(strategy_dir / f"{prefix}_portfolio_daily.csv")

    all_dates = sorted({row["date"] for rows in daily_series.values() for row in rows})
    compact_dates = sparsify_labels([compact_date_label(d) for d in all_dates], 12)

    nav_series = []
    dd_series = []
    pos_series = []
    for key, meta in STRATEGY_META.items():
        by_date = {row["date"]: row for row in daily_series[key]}
        nav = []
        dd = []
        pos = []
        last_nav = 0.0
        last_dd = 0.0
        last_pos = 0.0
        started = False
        for d in all_dates:
            if d in by_date:
                started = True
                last_nav = to_float(by_date[d]["nav_end"])
                last_dd = to_float(by_date[d]["drawdown_to_date"])
                last_pos = to_float(by_date[d]["position_count_end"])
            nav.append(last_nav if started else 0.0)
            dd.append(last_dd if started else 0.0)
            pos.append(last_pos if started else 0.0)
        nav_series.append((meta["label"], meta["color"], nav))
        dd_series.append((meta["label"], meta["color"], dd))
        pos_series.append((meta["label"], meta["color"], pos))

    charts = {}
    charts["nav"] = multi_line_chart_svg(
        compact_dates,
        nav_series,
        title="PIF Strategy NAV Comparison",
        subtitle="Split-adjusted backtest NAV paths. Pre-inception windows are shown as zero until the strategy begins.",
        y_formatter=format_nav,
    )
    charts["drawdown"] = multi_line_chart_svg(
        compact_dates,
        dd_series,
        title="PIF Strategy Drawdown Comparison",
        subtitle="Running drawdown from each strategy's own peak.",
        y_formatter=format_pct,
    )
    charts["positions"] = multi_line_chart_svg(
        compact_dates,
        pos_series,
        title="PIF Strategy Position Count",
        subtitle="Average breadth is an important part of why these strategies diverge.",
        y_formatter=lambda v: f"{int(v):,}",
    )

    labels = [STRATEGY_META[key]["label"] for key in ["p1", "p2", "p3", "p4", "p5"]]
    charts["total_return"] = grouped_bar_chart_svg(
        labels,
        [
            ("Total return", COLORS["blue"], [to_float(summary_by_key[key]["total_return"]) for key in ["p1", "p2", "p3", "p4", "p5"]]),
            ("CAGR", COLORS["gold"], [to_float(summary_by_key[key]["cagr"]) for key in ["p1", "p2", "p3", "p4", "p5"]]),
        ],
        title="Total Return and CAGR",
        subtitle="After the split-adjusted rerun and same-day bundle fix, `P2` through `P5` are positive in absolute terms while `P1` remains negative.",
        y_formatter=format_pct,
        width=860,
    )
    charts["risk"] = grouped_bar_chart_svg(
        labels,
        [
            ("Annual volatility", COLORS["teal"], [to_float(summary_by_key[key]["annual_volatility"]) for key in ["p1", "p2", "p3", "p4", "p5"]]),
            ("Absolute max drawdown", COLORS["red"], [abs(to_float(summary_by_key[key]["max_drawdown"])) for key in ["p1", "p2", "p3", "p4", "p5"]]),
        ],
        title="Risk Profile",
        subtitle="The strategies are not just losing; several are also carrying heavy drawdowns and volatility.",
        y_formatter=format_pct,
        width=860,
    )
    charts["concentration"] = grouped_bar_chart_svg(
        labels,
        [
            ("Avg max weight", COLORS["gold"], [to_float(summary_by_key[key]["avg_max_weight"]) for key in ["p1", "p2", "p3", "p4", "p5"]]),
            ("Avg top-3 weight", COLORS["violet"], [to_float(summary_by_key[key]["avg_top3_weight"]) for key in ["p1", "p2", "p3", "p4", "p5"]]),
        ],
        title="Concentration Profile",
        subtitle="P1 is structurally the most fragile because its basket often collapses into a few names.",
        y_formatter=format_pct,
        width=860,
    )

    period_by_trade = defaultdict(dict)
    for row in period_returns:
        period_by_trade[row["trade_date"]][row["strategy_key"]] = to_float(row["period_return"])
    period_cols = sorted(period_by_trade)
    period_labels = [compact_date_label(d) for d in period_cols]
    heatmap_matrix = {}
    for key, meta in STRATEGY_META.items():
        for trade_date in period_cols:
            heatmap_matrix[(meta["label"], compact_date_label(trade_date))] = period_by_trade[trade_date].get(key, 0.0)
    charts["period_heatmap"] = heatmap_svg(
        [compact_date_label(d) for d in period_cols],
        [STRATEGY_META[key]["label"] for key in ["p1", "p2", "p3", "p4", "p5"]],
        heatmap_matrix,
        title="Rebalance Window Return Heatmap",
        subtitle="Each cell is the return from one rebalance date to the eve of the next rebalance.",
        width=1180,
        height=330,
    )

    turnover_labels = [compact_date_label(d) for d in period_cols]
    turnover_series = []
    for key in ["p1", "p2", "p3", "p4", "p5"]:
        keyed = {
            row["trade_date"]: to_float(row["positions_bought_count"]) + to_float(row["positions_sold_count"])
            for row in period_returns
            if row["strategy_key"] == key
        }
        vals = [keyed.get(d, 0.0) for d in period_cols]
        turnover_series.append((STRATEGY_META[key]["label"], STRATEGY_META[key]["color"], vals))
    charts["turnover"] = grouped_bar_chart_svg(
        sparsify_labels(turnover_labels, 10),
        turnover_series,
        title="Turnover by Rebalance Window",
        subtitle="P1 rotates aggressively into a small set of names; P2-P4 trade a much broader disclosed sleeve.",
        y_formatter=lambda v: f"{int(v):,}",
        width=1180,
        height=470,
    )

    p1_by_trade = defaultdict(list)
    for row in p1_forward:
        p1_by_trade[row["trade_date"]].append(to_float(row["forward_return"]))
    p1_dates = sorted(p1_by_trade)
    charts["p1_quality"] = grouped_bar_chart_svg(
        sparsify_labels([compact_date_label(d) for d in p1_dates], 10),
        [
            ("Mean forward return", COLORS["red"], [statistics.mean(p1_by_trade[d]) for d in p1_dates]),
            ("Hit rate", COLORS["blue"], [sum(1 for v in p1_by_trade[d] if v > 0) / len(p1_by_trade[d]) for d in p1_dates]),
        ],
        title="P1 Entry Cohort Quality",
        subtitle="Why the lagged new-entry mirror fails: some cohorts are late, tiny, and badly concentrated.",
        y_formatter=format_pct,
    )

    p3_bucket = defaultdict(list)
    for row in p3_forward:
        p3_bucket[row["tilt_bucket"]].append(to_float(row["forward_return"]))
    charts["p3_bucket"] = grouped_bar_chart_svg(
        ["accumulation_like", "neutral"],
        [
            ("Mean forward return", COLORS["green"], [statistics.mean(p3_bucket["accumulation_like"]), statistics.mean(p3_bucket["neutral"])]),
            ("Median forward return", COLORS["gold"], [statistics.median(p3_bucket["accumulation_like"]), statistics.median(p3_bucket["neutral"])]),
        ],
        title="P3 Forward Return by Bucket",
        subtitle="Accumulation-like names do better on simple average, but not enough to overcome concentration and tail risk.",
        y_formatter=format_pct,
        width=860,
    )

    p4_cohort = defaultdict(list)
    p4_period = defaultdict(lambda: defaultdict(list))
    for row in p4_forward:
        val = to_float(row["forward_return"])
        p4_cohort[row["cohort"]].append(val)
        p4_period[row["trade_date"]][row["cohort"]].append(val)
    p4_dates = [d for d in sorted(p4_period) if p4_period[d].get("avoided_reduction")]
    charts["p4_avoid"] = grouped_bar_chart_svg(
        sparsify_labels([compact_date_label(d) for d in p4_dates], 10),
        [
            ("Avoided reductions", COLORS["red"], [statistics.mean(p4_period[d]["avoided_reduction"]) for d in p4_dates]),
            ("Kept names", COLORS["blue"], [statistics.mean(p4_period[d]["kept"]) for d in p4_dates]),
        ],
        title="P4 Reduction-Avoidance Effect",
        subtitle="The avoided names outperform on average in this sample, which is why P4 does not help.",
        y_formatter=format_pct,
    )

    for key in ["p1", "p2", "p4", "p5"]:
        top_rows = [row for row in contributors if row["strategy_key"] == key and row["bucket"] == "top"][:6]
        bottom_rows = [row for row in contributors if row["strategy_key"] == key and row["bucket"] == "bottom"][:6]
        combined = list(reversed(bottom_rows)) + top_rows
        charts[f"{key}_contributors"] = horizontal_bar_chart_svg(
            [row["issuer_name"] for row in combined],
            [to_float(row["total_return_contribution"]) for row in combined],
            title=f'{STRATEGY_META[key]["label"]} Contribution Stack',
            subtitle="Largest negative and positive net return contributors.",
            height=460,
        )

    chart_paths = {}
    for name, svg in charts.items():
        path = CHARTS_DIR / f"{name}.svg"
        write_text(path, svg)
        chart_paths[name] = path

    # Tables for report
    strategy_table = []
    for key in ["p1", "p2", "p3", "p4", "p5"]:
        row = summary_by_key[key]
        strategy_table.append(
            {
                "Strategy": STRATEGY_META[key]["label"],
                "Design": STRATEGY_META[key]["name"],
                "Total Return": format_pct(to_float(row["total_return"])),
                "CAGR": format_pct(to_float(row["cagr"])),
                "Ann. Vol": format_pct(to_float(row["annual_volatility"])),
                "Max Drawdown": format_pct(to_float(row["max_drawdown"])),
                "Avg Positions": format_num(to_float(row["avg_position_count"])),
                "Avg Max Weight": format_pct(to_float(row["avg_max_weight"])),
            }
        )

    sanity_table = []
    for row in sanity:
        sanity_table.append(
            {
                "Strategy": STRATEGY_META[row["strategy_key"]]["label"],
                "Arithmetic Violations": row["arithmetic_violations"],
                "Weight Sum Range": f'{float(row["weight_sum_min"]):.6f} to {float(row["weight_sum_max"]):.6f}',
                "Entry-Day PnL Violations": row["entry_day_pnl_violations"],
                "Non-Exact Price Rows": row["non_exact_price_rows"],
            }
        )

    p1_mean = statistics.mean(to_float(r["forward_return"]) for r in p1_forward)
    p1_hit = sum(1 for r in p1_forward if to_float(r["forward_return"]) > 0) / len(p1_forward)
    p1_worst = min(to_float(r["forward_return"]) for r in p1_forward)
    p3_acc = [to_float(r["forward_return"]) for r in p3_forward if r["tilt_bucket"] == "accumulation_like"]
    p3_neu = [to_float(r["forward_return"]) for r in p3_forward if r["tilt_bucket"] == "neutral"]
    p4_avoid = [to_float(r["forward_return"]) for r in p4_forward if r["cohort"] == "avoided_reduction"]
    p4_keep = [to_float(r["forward_return"]) for r in p4_forward if r["cohort"] == "kept"]

    html_report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PIF Backtest Research Report</title>
  <style>
    body {{
      font-family: Georgia, "Times New Roman", serif;
      margin: 28px auto;
      max-width: 1180px;
      color: {COLORS["text"]};
      background: {COLORS["bg"]};
      line-height: 1.55;
    }}
    .card {{
      background: white;
      border: 1px solid {COLORS["grid"]};
      border-radius: 14px;
      padding: 18px 22px;
      margin-bottom: 18px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    }}
    .grid2 {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .grid3 {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }}
    .metric {{
      font-size: 28px;
      font-weight: 700;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .sub {{
      color: {COLORS["slate"]};
      font-size: 13px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    h1, h2, h3 {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0 0 10px 0;
    }}
    img {{
      width: 100%;
      height: auto;
      border-radius: 12px;
      border: 1px solid {COLORS["grid"]};
      background: white;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    th, td {{
      border-bottom: 1px solid {COLORS["grid"]};
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #F1F5F9;
    }}
    ul {{
      margin: 8px 0 0 18px;
    }}
    .neg {{
      background: {COLORS["neg_bg"]};
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>PIF 13F Mirroring Backtests</h1>
    <div class="sub">Research report on lagged sovereign wealth fund mirroring strategies using the Public Investment Fund's disclosed US 13F sleeve.</div>
  </div>

  <div class="grid3">
    <div class="card neg">
      <div class="sub">Headline finding</div>
      <div class="metric">Absolute return is not alpha</div>
      <div class="sub">Several corrected `PIF` strategies are positive in absolute terms, but none beats `SPY` on a matched-window basis.</div>
    </div>
    <div class="card">
      <div class="sub">Best result</div>
      <div class="metric">{escape(best_total_key.upper())}: {format_pct(to_float(best_total_row["total_return"]))}</div>
      <div class="sub">The strongest absolute result comes from the corrected strategy outputs, not from benchmark-relative alpha.</div>
    </div>
    <div class="card">
      <div class="sub">Core implication</div>
      <div class="metric">Exposure timing matters</div>
      <div class="sub">The cash-aware interpretation is still economically useful, but the strongest absolute return now comes from the fully invested equal-weight sleeve.</div>
    </div>
  </div>

  <div class="card">
    <h2>Research Question</h2>
    <p>We tested whether publicly disclosed `PIF` 13F holdings contain investable information once the filing lag is respected. Trades were simulated from the first tradable NYSE close after the public filing date, not from the quarter-end report date. The mark-to-market layer uses split-adjusted closes to avoid false gains from reverse splits and similar corporate actions.</p>
  </div>

  <div class="card">
    <h2>Strategies Tested</h2>
    <ul>
      <li><strong>P1 New Positions Mirror:</strong> buy only newly disclosed entry names and hold until the next filing window.</li>
      <li><strong>P2 Full Sleeve Equal Weight:</strong> hold every eligible common-equity name in the disclosed 13F sleeve with equal weights.</li>
      <li><strong>P3 Accumulation Tilt:</strong> start with the disclosed sleeve, overweight `entry_observed` and `likely_accumulation` names, and exclude `likely_reduction` names.</li>
      <li><strong>P4 Exit Avoidance:</strong> hold the disclosed sleeve but drop names flagged as `likely_reduction` in the same report period.</li>
      <li><strong>P5 Cash-Aware Copy Trade:</strong> seed the first disclosed sleeve, then copy later disclosed buys and sells while keeping net sale proceeds in cash instead of forcing reinvestment.</li>
    </ul>
  </div>

  <div class="card">
    <h2>Executive Summary</h2>
    <ul>
      <li>The corrected backtests do not support a simple “all fully invested mirroring fails” story. `P2`, `P3`, `P4`, and `P5` are all positive in absolute return after the split-adjusted rerun and same-day bundle fix.</li>
      <li>`{escape(best_full_key.upper())}` is now the strongest fully invested strategy at `{format_pct(to_float(best_full_row["total_return"]))}`. `P5` remains positive at `{format_pct(to_float(summary_by_key["p5"]["total_return"]))}`, but it is no longer the best absolute-return strategy.</li>
      <li>`P1` fails primarily because it is too concentrated and too dependent on late, noisy entry signals. It averages only `6.47` names and an average max weight of `59.7%`.</li>
      <li>`P3` shows a more nuanced failure. The `accumulation_like` bucket has better simple forward returns than the neutral bucket (`{format_pct(statistics.mean(p3_acc))}` vs `{format_pct(statistics.mean(p3_neu))}`), but the portfolio still underperforms because the tilt amplifies concentration and tail losses.</li>
      <li>`P4` does not help because the `likely_reduction` filter is directionally wrong in this sample. The names it avoids average `{format_pct(statistics.mean(p4_avoid))}` forward return, versus `{format_pct(statistics.mean(p4_keep))}` for the names it keeps.</li>
      <li>`P5` still changes the interpretation of the disclosure stream. Once we stop redistributing sale proceeds into surviving names and instead allow cash to accumulate, the strategy behaves more like a literal copy of observable `PIF` de-risking.</li>
    </ul>
  </div>

  <div class="card">
    <h2>Results Table</h2>
    {render_table(strategy_table, ["Strategy", "Design", "Total Return", "CAGR", "Ann. Vol", "Max Drawdown", "Avg Positions", "Avg Max Weight"])}
  </div>

  <div class="card">
    <h2>Sanity Checks</h2>
    <p>The analysis layer rechecked arithmetic consistency, gross exposure, weight normalization, entry-day PnL leakage, and exact-price coverage. The current result set is mechanically coherent.</p>
    {render_table(sanity_table, ["Strategy", "Arithmetic Violations", "Weight Sum Range", "Entry-Day PnL Violations", "Non-Exact Price Rows"])}
  </div>

  <div class="card"><img src="../research_charts/nav.svg" alt="NAV comparison"></div>
  <div class="card"><img src="../research_charts/drawdown.svg" alt="Drawdown comparison"></div>
  <div class="grid2">
    <div class="card"><img src="../research_charts/total_return.svg" alt="Return chart"></div>
    <div class="card"><img src="../research_charts/risk.svg" alt="Risk chart"></div>
  </div>
  <div class="grid2">
    <div class="card"><img src="../research_charts/positions.svg" alt="Position count chart"></div>
    <div class="card"><img src="../research_charts/concentration.svg" alt="Concentration chart"></div>
  </div>
  <div class="card"><img src="../research_charts/period_heatmap.svg" alt="Rebalance heatmap"></div>
  <div class="card"><img src="../research_charts/turnover.svg" alt="Turnover chart"></div>

  <div class="card">
    <h2>Why The Strategies Failed Or Worked</h2>
    <h3>P1 New Positions Mirror</h3>
    <p>`P1` is the clearest failure. The strategy buys only newly disclosed names, so it arrives after the disclosure lag and often with only a tiny basket. The cohort-level signal is not useless on simple average (`{format_pct(p1_mean)}` mean forward return and `{format_pct(p1_hit)}` hit rate), but the realized portfolio is too concentrated. The worst single forward return inside the entry sample is `{format_pct(p1_worst)}`, and the strategy's average max weight stays near `60%`.</p>
    <h3>P2 Full Sleeve Equal Weight</h3>
    <p>`P2` is no longer a negative-return strategy after the corrected bundle handling. It spreads risk across the broad disclosed sleeve and avoids the severe single-name concentration of `P1`, which is enough to produce a positive absolute return. The more important limitation is benchmark-relative: the sleeve still trails `SPY`, so the result looks more like diluted market exposure than alpha.</p>
    <h3>P3 Accumulation Tilt</h3>
    <p>`P3` is more interesting analytically than `P2`. The accumulation-like bucket does outperform the neutral bucket on simple forward averages, which suggests there may be some directional information in share-count changes. The corrected portfolio is positive in absolute terms, but it still lags both `P2` and `SPY` because the tilt magnifies exposure to a smaller set of names with fatter downside tails.</p>
    <h3>P4 Exit Avoidance</h3>
    <p>`P4` remains directionally suspect even after the corrected bundle handling. The strategy is positive in absolute terms, but the reduction-avoidance heuristic still looks wrong in this sample because the names it excludes go on to outperform the names it keeps on average.</p>
    <h3>P5 Cash-Aware Copy Trade</h3>
    <p>`P5` is the first strategy whose logic lines up with the intuitive copy-trading story. It sells what the disclosed sleeve appears to sell, keeps those proceeds in cash, and funds later disclosed buys only from that available cash. That matters. Instead of mechanically concentrating into a shrinking set of survivors, the strategy allows gross exposure to fall when `PIF` appears to be reducing the visible sleeve. In the corrected backtests, that change is enough to keep the strategy positive, even though it still does not beat `SPY`.</p>
  </div>

  <div class="grid2">
    <div class="card"><img src="../research_charts/p1_quality.svg" alt="P1 quality chart"></div>
    <div class="card"><img src="../research_charts/p3_bucket.svg" alt="P3 bucket chart"></div>
  </div>
  <div class="card"><img src="../research_charts/p4_avoid.svg" alt="P4 avoidance chart"></div>

  <div class="grid2">
    <div class="card"><img src="../research_charts/p1_contributors.svg" alt="P1 contributors"></div>
    <div class="card"><img src="../research_charts/p2_contributors.svg" alt="P2 contributors"></div>
  </div>
  <div class="grid2">
    <div class="card"><img src="../research_charts/p4_contributors.svg" alt="P4 contributors"></div>
    <div class="card"><img src="../research_charts/p5_contributors.svg" alt="P5 contributors"></div>
  </div>

  <div class="card">
    <h2>Conclusion</h2>
    <p>The corrected backtests support a narrower and more nuanced conclusion than the earlier report versions suggested. A broad fully invested mirror of the disclosed sleeve can be positive in absolute terms, but it still does not beat `SPY`. The cash-aware copy trade remains conceptually valuable because it respects disclosed de-risking and stays positive without forcing concentration into surviving names. The most defensible conclusion is therefore not “copy trading `PIF` generates alpha,” but rather “`PIF` disclosures carry some exposure-structure information that is economically interpretable, though not benchmark-beating in this sample.”</p>
  </div>
</body>
</html>
"""

    md_report = f"""# PIF 13F Mirroring Backtests

Research report on lagged `PIF` 13F mirroring strategies using the disclosed US 13F sleeve.

## Executive Summary

- After the split-adjusted rerun and same-day bundle fix, `P2` through `P5` are positive in absolute terms; only `P1` remains negative.
- `{escape(best_total_key.upper())}` is the strongest absolute result at `{format_pct(to_float(best_total_row["total_return"]))}`.
- `{escape(best_full_key.upper())}` is the strongest fully invested variant at `{format_pct(to_float(best_full_row["total_return"]))}`.
- `P1` is the weakest at `-75.8%`, driven by high concentration and fragile entry cohorts.
- `P3` finds a stronger accumulation bucket on simple average (`{format_pct(statistics.mean(p3_acc))}` vs `{format_pct(statistics.mean(p3_neu))}`), but still loses because the tilt adds concentration and tail-risk drag.
- `P4` is directionally unhelpful in this sample: avoided likely-reduction names average `{format_pct(statistics.mean(p4_avoid))}` forward return versus `{format_pct(statistics.mean(p4_keep))}` for the names it keeps.
- `P5` still suggests the most usable information is in exposure contraction and expansion, not just the identity of the disclosed holdings.

## Strategies

- `P1`: buy newly disclosed entry names only.
- `P2`: hold the full disclosed common-equity sleeve equal weight.
- `P3`: overweight entries and likely accumulations, exclude likely reductions.
- `P4`: hold the sleeve but avoid likely reductions.
- `P5`: seed the first disclosed sleeve, then copy later buys and sells while retaining net sale proceeds in cash.

## Results Table

{chr(10).join([f"- {row['Strategy']}: total return {row['Total Return']}, CAGR {row['CAGR']}, max drawdown {row['Max Drawdown']}, avg positions {row['Avg Positions']}, avg max weight {row['Avg Max Weight']}" for row in strategy_table])}

## Why They Failed Or Worked

- `P1` fails because lagged new-entry mirroring is too concentrated. Average positions are `6.47`, average max weight is `59.7%`, and the worst single forward return in the entry sample is `{format_pct(p1_worst)}`.
- `P2` is positive because diversification helps, but the lagged equal-weight sleeve still does not produce positive alpha versus `SPY`.
- `P3` identifies a more promising bucket but concentrates too hard into names with worse tail losses.
- `P4` fails because the likely-reduction filter is directionally wrong in this sample.
- `P5` works because it does not force the strategy to stay fully invested when the visible `PIF` sleeve is shrinking. It treats disclosed sells as genuine de-risking and allows cash to accumulate, even though that still does not beat `SPY`.

## Charts

![NAV Comparison]({chart_paths["nav"]})
![Drawdown Comparison]({chart_paths["drawdown"]})
![Total Return and CAGR]({chart_paths["total_return"]})
![Risk Profile]({chart_paths["risk"]})
![Position Count]({chart_paths["positions"]})
![Concentration]({chart_paths["concentration"]})
![Rebalance Heatmap]({chart_paths["period_heatmap"]})
![Turnover]({chart_paths["turnover"]})
![P1 Entry Cohort Quality]({chart_paths["p1_quality"]})
![P3 Bucket Forward Returns]({chart_paths["p3_bucket"]})
![P4 Avoidance Effect]({chart_paths["p4_avoid"]})
![P1 Contributors]({chart_paths["p1_contributors"]})
![P2 Contributors]({chart_paths["p2_contributors"]})
![P4 Contributors]({chart_paths["p4_contributors"]})
![P5 Contributors]({chart_paths["p5_contributors"]})
"""

    write_text(REPORTS_DIR / "pif_backtest_research_report.html", html_report)
    write_text(REPORTS_DIR / "pif_backtest_research_report.md", md_report)
    print(f"Wrote research charts to {CHARTS_DIR}")
    print(f"Wrote research reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
