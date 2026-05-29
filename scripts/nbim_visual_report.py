from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "nbim"
CHARTS_DIR = ROOT / "outputs" / "nbim" / "charts"
REPORTS_DIR = ROOT / "outputs" / "nbim" / "reports"


COLORS = {
    "blue": "#0B5FFF",
    "teal": "#0A7C86",
    "gold": "#D97706",
    "red": "#C2410C",
    "green": "#15803D",
    "slate": "#334155",
    "gray": "#94A3B8",
    "grid": "#E2E8F0",
    "bg": "#F8FAFC",
    "text": "#0F172A",
}

PALETTE = [
    "#0B5FFF",
    "#0A7C86",
    "#15803D",
    "#D97706",
    "#BE185D",
    "#7C3AED",
    "#475569",
    "#C026D3",
    "#2563EB",
    "#CA8A04",
    "#14B8A6",
    "#DC2626",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def parse_float(value: str) -> float:
    if value.strip() == "":
        return 0.0
    return float(value)


def ensure_dirs() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def escape(text: str) -> str:
    return html.escape(text)


def format_billions(value: float) -> str:
    return f"${value / 1_000_000_000:.1f}B"


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def compact_date_label(text: str) -> str:
    if "->" in text:
        left, right = text.split("->", 1)
        return f"{left[2:7]}->{right[2:7]}"
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text[2:7]
    return text


def sparsify_labels(labels: list[str], max_labels: int) -> list[str]:
    if len(labels) <= max_labels:
        return labels
    step = max(1, (len(labels) + max_labels - 1) // max_labels)
    sparse = []
    for i, label in enumerate(labels):
        if i % step == 0 or i == len(labels) - 1:
            sparse.append(label)
        else:
            sparse.append("")
    return sparse


def svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


def wrap_svg(content: str, width: int, height: int) -> str:
    return f"{svg_header(width, height)}{content}</svg>"


def line_chart_svg(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    subtitle: str,
    color: str,
    y_label_formatter,
    width: int = 900,
    height: int = 420,
) -> str:
    left = 72
    right = 20
    top = 56
    bottom = 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v = min_v + 1.0

    points = []
    for i, value in enumerate(values):
        x = left + (plot_w * i / max(1, len(values) - 1))
        y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
        points.append((x, y))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" />'
        f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-size="11" fill="{COLORS["text"]}">{escape(y_label_formatter(values[i]))}</text>'
        for i, (x, y) in enumerate(points)
    )

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_label_formatter(value))}</text>'
        )

    x_labels = "".join(
        f'<text x="{x:.1f}" y="{height - 28}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{escape(label)}</text>'
        for label, (x, _) in zip(labels, points)
        if label
    )

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="28" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="46" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    <polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}" />
    {circles}
    {x_labels}
    """
    return wrap_svg(content, width, height)


def grouped_bar_chart_svg(
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    *,
    title: str,
    subtitle: str,
    width: int = 980,
    height: int = 460,
) -> str:
    left = 72
    right = 20
    top = 64
    bottom = 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_v = max(max(values) for _, _, values in series) if series else 1.0
    if max_v == 0:
        max_v = 1.0

    groups = len(labels)
    bars_per_group = len(series)
    group_w = plot_w / max(1, groups)
    bar_w = min(26, group_w / max(1, bars_per_group + 1))

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = frac * max_v
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{int(value):,}</text>')

    bars = []
    for i, label in enumerate(labels):
        gx = left + i * group_w
        for j, (_, color, values) in enumerate(series):
            value = values[i]
            h = 0 if max_v == 0 else (value / max_v) * plot_h
            x = gx + 12 + j * (bar_w + 4)
            y = top + plot_h - h
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        if label:
            bars.append(f'<text x="{gx + group_w / 2:.1f}" y="{height - 38}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend = []
    legend_x = left
    for name, color, _ in series:
        legend.append(f'<rect x="{legend_x}" y="{height - 22}" width="12" height="12" fill="{color}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{height - 12}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 140

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    {''.join(legend)}
    """
    return wrap_svg(content, width, height)


def stacked_bar_chart_svg(
    labels: list[str],
    categories: list[str],
    values_by_category: dict[str, list[float]],
    *,
    title: str,
    subtitle: str,
    width: int = 980,
    height: int = 460,
) -> str:
    left = 72
    right = 20
    top = 64
    bottom = 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    group_w = plot_w / max(1, len(labels))
    bar_w = min(80, group_w * 0.65)

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{int(frac * 100)}%</text>')

    bars = []
    for i, label in enumerate(labels):
        x = left + i * group_w + (group_w - bar_w) / 2
        running = 0.0
        for idx, category in enumerate(categories):
            value = values_by_category[category][i]
            h = value * plot_h
            y = top + plot_h - running - h
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{PALETTE[idx % len(PALETTE)]}"/>')
            running += h
        if label:
            bars.append(f'<text x="{x + bar_w/2:.1f}" y="{height - 38}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend = []
    legend_x = left
    legend_y = height - 24
    for idx, category in enumerate(categories):
        legend.append(f'<rect x="{legend_x}" y="{legend_y}" width="12" height="12" fill="{PALETTE[idx % len(PALETTE)]}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{legend_y + 10}" font-size="11" fill="{COLORS["slate"]}">{escape(category)}</text>')
        legend_x += 118
        if legend_x > width - 160:
            legend_x = left
            legend_y += 18

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    {''.join(legend)}
    """
    return wrap_svg(content, width, height)


def heatmap_svg(
    periods: list[str],
    rows: list[str],
    matrix: dict[tuple[str, str], float],
    *,
    title: str,
    subtitle: str,
    width: int = 980,
    height: int = 520,
) -> str:
    left = 180
    right = 24
    top = 80
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    cell_w = plot_w / max(1, len(periods))
    cell_h = plot_h / max(1, len(rows))
    max_abs = max(abs(v) for v in matrix.values()) if matrix else 1.0
    if max_abs == 0:
        max_abs = 1.0

    def color_for(value: float) -> str:
        intensity = min(1.0, abs(value) / max_abs)
        if value >= 0:
            base = (21, 128, 61)
            bg = tuple(int(255 - (255 - channel) * intensity) for channel in base)
        else:
            base = (194, 65, 12)
            bg = tuple(int(255 - (255 - channel) * intensity) for channel in base)
        return "#{:02x}{:02x}{:02x}".format(*bg)

    cells = []
    for r_idx, row_name in enumerate(rows):
        y = top + r_idx * cell_h
        cells.append(f'<text x="{left - 10}" y="{y + cell_h/2 + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(row_name)}</text>')
        for c_idx, period in enumerate(periods):
            x = left + c_idx * cell_w
            value = matrix.get((row_name, period), 0.0)
            cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{color_for(value)}" stroke="white" stroke-width="1"/>')
            cells.append(f'<text x="{x + cell_w/2:.1f}" y="{y + cell_h/2 + 4:.1f}" text-anchor="middle" font-size="10" fill="{COLORS["text"]}">{int(value)}</text>')

    x_labels = "".join(
        f'<text x="{left + i * cell_w + cell_w/2:.1f}" y="{top - 12}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{escape(period)}</text>'
        for i, period in enumerate(periods)
        if period
    )

    legend = (
        f'<text x="{left}" y="{height - 18}" font-size="11" fill="{COLORS["slate"]}">Negative values indicate more likely reductions than likely accumulations. Positive values indicate the opposite.</text>'
    )

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {x_labels}
    {''.join(cells)}
    {legend}
    """
    return wrap_svg(content, width, height)


def latest_snapshot_insights(snapshot_rows: list[dict[str, str]], industry_rows: list[dict[str, str]]) -> dict[str, str]:
    latest = max(snapshot_rows, key=lambda row: row["as_of_date"])
    latest_date = latest["as_of_date"]
    latest_industries = [row for row in industry_rows if row["as_of_date"] == latest_date]
    latest_industries.sort(key=lambda row: parse_float(row["portfolio_weight_usd"]), reverse=True)
    top3 = ", ".join(
        f"{row['industry']} ({format_percent(parse_float(row['portfolio_weight_usd']))})"
        for row in latest_industries[:3]
    )
    return {
        "latest_date": latest_date,
        "holding_count": latest["holding_count"],
        "market_value": format_billions(parse_float(latest["total_market_value_usd"])),
        "top10_share": format_percent(parse_float(latest["top_10_share"])),
        "top3_industries": top3,
    }


def period_rotation_insights(transition_rows: list[dict[str, str]]) -> dict[str, str]:
    latest = max(transition_rows, key=lambda row: row["curr_as_of_date"])
    return {
        "period": latest["period"],
        "entry_observed": latest["entry_observed"],
        "exit_observed": latest["exit_observed"],
        "likely_accumulation": latest["likely_accumulation"],
        "likely_reduction": latest["likely_reduction"],
    }


def build_charts() -> dict[str, Path]:
    snapshot_rows = read_csv(PROCESSED / "nbim_snapshot_summary.csv")
    region_rows = read_csv(PROCESSED / "nbim_snapshot_region_summary.csv")
    industry_rows = read_csv(PROCESSED / "nbim_snapshot_industry_summary.csv")
    transition_rows = read_csv(PROCESSED / "nbim_transition_summary.csv")
    transition_industry_rows = read_csv(PROCESSED / "nbim_transition_industry_summary.csv")

    dates = [row["as_of_date"] for row in snapshot_rows]
    compact_dates = sparsify_labels([compact_date_label(d) for d in dates], max_labels=8)

    charts: dict[str, str] = {}
    charts["holdings_count"] = line_chart_svg(
        compact_dates,
        [parse_float(row["holding_count"]) for row in snapshot_rows],
        title="NBIM Holdings Count",
        subtitle="Observable public-equity positions per snapshot",
        color=COLORS["blue"],
        y_label_formatter=lambda v: f"{int(v):,}",
    )
    charts["market_value"] = line_chart_svg(
        compact_dates,
        [parse_float(row["total_market_value_usd"]) for row in snapshot_rows],
        title="NBIM Total Market Value",
        subtitle="Aggregate USD market value of observable public-equity holdings",
        color=COLORS["teal"],
        y_label_formatter=format_billions,
    )
    charts["concentration"] = line_chart_svg(
        compact_dates,
        [parse_float(row["top_10_share"]) for row in snapshot_rows],
        title="Top-10 Concentration",
        subtitle="Share of total portfolio market value represented by the 10 largest holdings",
        color=COLORS["gold"],
        y_label_formatter=format_percent,
    )

    region_categories = sorted({row["region"] for row in region_rows})
    region_values: dict[str, list[float]] = {name: [] for name in region_categories}
    for date in dates:
        rows_for_date = {row["region"]: row for row in region_rows if row["as_of_date"] == date}
        for name in region_categories:
            region_values[name].append(parse_float(rows_for_date.get(name, {}).get("portfolio_weight_usd", "0")))
    charts["region_weights"] = stacked_bar_chart_svg(
        compact_dates,
        region_categories,
        region_values,
        title="Region Weights Over Time",
        subtitle="Portfolio weight by region using USD market value",
    )

    latest_date = dates[-1]
    latest_industry_sorted = sorted(
        (row for row in industry_rows if row["as_of_date"] == latest_date),
        key=lambda row: parse_float(row["portfolio_weight_usd"]),
        reverse=True,
    )
    industry_focus = [row["industry"] for row in latest_industry_sorted[:6]]
    industry_focus.append("Other")
    industry_values: dict[str, list[float]] = {name: [] for name in industry_focus}
    for date in dates:
        rows_for_date = [row for row in industry_rows if row["as_of_date"] == date]
        weight_map = {row["industry"]: parse_float(row["portfolio_weight_usd"]) for row in rows_for_date}
        other = 1.0 - sum(weight_map.get(name, 0.0) for name in industry_focus if name != "Other")
        for name in industry_focus:
            industry_values[name].append(other if name == "Other" else weight_map.get(name, 0.0))
    charts["industry_weights"] = stacked_bar_chart_svg(
        compact_dates,
        industry_focus,
        industry_values,
        title="Industry Weights Over Time",
        subtitle="Top industries by latest snapshot, plus residual 'Other'",
    )

    periods = [row["period"] for row in transition_rows]
    compact_periods = sparsify_labels([compact_date_label(p) for p in periods], max_labels=6)
    charts["transition_events"] = grouped_bar_chart_svg(
        compact_periods,
        [
            ("Entries", COLORS["blue"], [parse_float(row["entry_observed"]) for row in transition_rows]),
            ("Exits", COLORS["red"], [parse_float(row["exit_observed"]) for row in transition_rows]),
            ("Likely Accum.", COLORS["green"], [parse_float(row["likely_accumulation"]) for row in transition_rows]),
            ("Likely Reduct.", COLORS["gold"], [parse_float(row["likely_reduction"]) for row in transition_rows]),
        ],
        title="Transition Event Counts",
        subtitle="Entries, exits, likely accumulations, and likely reductions by consecutive snapshot pair",
    )

    heatmap_periods = periods
    top_industries = sorted(
        {row["industry"] for row in transition_industry_rows},
        key=lambda name: max(
            abs(parse_float(row["likely_accumulation"]) - parse_float(row["likely_reduction"]))
            for row in transition_industry_rows
            if row["industry"] == name
        ),
        reverse=True,
    )[:10]
    heatmap_matrix: dict[tuple[str, str], float] = {}
    for row in transition_industry_rows:
        industry = row["industry"]
        if industry not in top_industries:
            continue
        period = row["period"]
        net = parse_float(row["likely_accumulation"]) - parse_float(row["likely_reduction"])
        heatmap_matrix[(industry, period)] = net
    charts["industry_heatmap"] = heatmap_svg(
        sparsify_labels([compact_date_label(p) for p in heatmap_periods], max_labels=6),
        top_industries,
        heatmap_matrix,
        title="Net Industry Rotation Signal",
        subtitle="Likely accumulations minus likely reductions by industry and period",
    )

    paths: dict[str, Path] = {}
    for name, svg in charts.items():
        path = CHARTS_DIR / f"{name}.svg"
        write_text(path, svg)
        paths[name] = path

    return paths


def build_report(chart_paths: dict[str, Path]) -> None:
    snapshot_rows = read_csv(PROCESSED / "nbim_snapshot_summary.csv")
    industry_rows = read_csv(PROCESSED / "nbim_snapshot_industry_summary.csv")
    transition_rows = read_csv(PROCESSED / "nbim_transition_summary.csv")

    snap = latest_snapshot_insights(snapshot_rows, industry_rows)
    rot = period_rotation_insights(transition_rows)

    html_report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NBIM Visual Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 32px auto;
      max-width: 1100px;
      color: {COLORS["text"]};
      background: {COLORS["bg"]};
      line-height: 1.45;
    }}
    .card {{
      background: white;
      border: 1px solid {COLORS["grid"]};
      border-radius: 16px;
      padding: 18px 20px;
      margin-bottom: 18px;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .metric {{
      font-size: 28px;
      font-weight: 700;
    }}
    .sub {{
      color: {COLORS["slate"]};
      font-size: 13px;
    }}
    img {{
      width: 100%;
      height: auto;
      border-radius: 12px;
      border: 1px solid {COLORS["grid"]};
      background: white;
    }}
    h1, h2 {{
      margin: 0 0 10px 0;
    }}
    ul {{
      margin: 8px 0 0 18px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>NBIM Public Equity Visual Report</h1>
    <div class="sub">Built from the consolidated holdings and transition datasets in this workspace.</div>
  </div>
  <div class="grid">
    <div class="card">
      <div class="sub">Latest snapshot</div>
      <div class="metric">{escape(snap["latest_date"])}</div>
      <div class="sub">{escape(snap["holding_count"])} holdings, {escape(snap["market_value"])}, top-10 share {escape(snap["top10_share"])}</div>
    </div>
    <div class="card">
      <div class="sub">Latest transition period</div>
      <div class="metric">{escape(rot["period"])}</div>
      <div class="sub">Entries {escape(rot["entry_observed"])}, exits {escape(rot["exit_observed"])}, likely accumulations {escape(rot["likely_accumulation"])}, likely reductions {escape(rot["likely_reduction"])}</div>
    </div>
  </div>
  <div class="card">
    <h2>Immediate Read</h2>
    <ul>
      <li>The observable equity book is shrinking in count but growing in total market value, which points to rising concentration.</li>
      <li>The latest snapshot's three largest industry weights are {escape(snap["top3_industries"])}.</li>
      <li>Likely reductions exceed likely accumulations in every observed transition period, so the event dataset currently reads more as a rebalancing and pruning signal than a broad expansion signal.</li>
      <li>The transition dataset is best used as an observable-ownership-change monitor, not a direct trade-flow reconstruction.</li>
    </ul>
  </div>
  <div class="card"><img src="../charts/holdings_count.svg" alt="Holdings count chart"></div>
  <div class="card"><img src="../charts/market_value.svg" alt="Market value chart"></div>
  <div class="card"><img src="../charts/concentration.svg" alt="Concentration chart"></div>
  <div class="card"><img src="../charts/region_weights.svg" alt="Region weights chart"></div>
  <div class="card"><img src="../charts/industry_weights.svg" alt="Industry weights chart"></div>
  <div class="card"><img src="../charts/transition_events.svg" alt="Transition events chart"></div>
  <div class="card"><img src="../charts/industry_heatmap.svg" alt="Industry heatmap"></div>
</body>
</html>
"""

    md_report = f"""# NBIM Public Equity Visual Report

Latest snapshot: `{snap["latest_date"]}` with `{snap["holding_count"]}` holdings, `{snap["market_value"]}` in total USD market value, and `{snap["top10_share"]}` top-10 concentration.

Latest transition period: `{rot["period"]}` with `{rot["entry_observed"]}` entries, `{rot["exit_observed"]}` exits, `{rot["likely_accumulation"]}` likely accumulations, and `{rot["likely_reduction"]}` likely reductions.

## Key Takeaways

- The observable equity book is shrinking in count but growing in market value, implying rising concentration.
- The latest snapshot's three largest industry weights are {snap["top3_industries"]}.
- Likely reductions exceed likely accumulations in every observed period.
- The event dataset is best used as an ownership-change monitor rather than a literal trading-flow dataset.

## Charts

![Holdings Count]({chart_paths["holdings_count"]})
![Market Value]({chart_paths["market_value"]})
![Top-10 Concentration]({chart_paths["concentration"]})
![Region Weights]({chart_paths["region_weights"]})
![Industry Weights]({chart_paths["industry_weights"]})
![Transition Events]({chart_paths["transition_events"]})
![Industry Heatmap]({chart_paths["industry_heatmap"]})
"""

    write_text(REPORTS_DIR / "nbim_visual_report.html", html_report)
    write_text(REPORTS_DIR / "nbim_visual_report.md", md_report)


def main() -> None:
    ensure_dirs()
    chart_paths = build_charts()
    build_report(chart_paths)
    print(f"Wrote charts to {CHARTS_DIR}")
    print(f"Wrote reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
