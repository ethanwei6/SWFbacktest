from __future__ import annotations

import csv
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "pif"
CHARTS_DIR = ROOT / "outputs" / "pif" / "charts"
REPORTS_DIR = ROOT / "outputs" / "pif" / "reports"


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


def format_billions(value: float) -> str:
    return f"${value / 1_000_000_000:.1f}B"


def format_millions(value: float) -> str:
    return f"{value / 1_000_000:.1f}M"


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
    width: int = 920,
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
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{color}" />'
        for x, y in points
    )

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_label_formatter(value))}</text>')

    x_labels = "".join(
        f'<text x="{x:.1f}" y="{height - 28}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>'
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
    bar_w = min(22, group_w / max(1, bars_per_group + 1))

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
            h = (value / max_v) * plot_h
            x = gx + 10 + j * (bar_w + 3)
            y = top + plot_h - h
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        if label:
            bars.append(f'<text x="{gx + group_w/2:.1f}" y="{height - 38}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>')

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
    height: int = 430,
) -> str:
    left = 72
    right = 20
    top = 64
    bottom = 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    group_w = plot_w / max(1, len(labels))
    bar_w = min(44, group_w * 0.55)

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
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{PALETTE[idx % len(PALETTE)]}" />')
            running += h
        if label:
            bars.append(f'<text x="{x + bar_w/2:.1f}" y="{height - 38}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend = []
    legend_x = left
    legend_y = height - 24
    for idx, category in enumerate(categories):
        legend.append(f'<rect x="{legend_x}" y="{legend_y}" width="12" height="12" fill="{PALETTE[idx % len(PALETTE)]}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{legend_y + 10}" font-size="11" fill="{COLORS["slate"]}">{escape(category)}</text>')
        legend_x += 120

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    {''.join(legend)}
    """
    return wrap_svg(content, width, height)


def latest_snapshot_insights(snapshot_rows: list[dict[str, str]]) -> dict[str, str]:
    latest = max(snapshot_rows, key=lambda row: row["as_of_date"])
    option_rows = int(parse_float(latest["option_row_count"]))
    holding_count = int(parse_float(latest["holding_count"]))
    option_share = option_rows / holding_count if holding_count else 0.0
    return {
        "latest_date": latest["as_of_date"],
        "holding_count": latest["holding_count"],
        "market_value": format_billions(parse_float(latest["total_market_value_usd"])),
        "largest_holding": latest["largest_holding"],
        "option_share": f"{option_share * 100:.1f}%",
    }


def latest_transition_insights(transition_rows: list[dict[str, str]]) -> dict[str, str]:
    latest = max(transition_rows, key=lambda row: row["curr_as_of_date"])
    return {
        "period": latest["period"],
        "entries": latest["entry_observed"],
        "exits": latest["exit_observed"],
        "accumulations": latest["likely_accumulation"],
        "reductions": latest["likely_reduction"],
    }


def build_charts() -> dict[str, Path]:
    snapshot_rows = read_csv(PROCESSED / "pif_13f_snapshot_summary.csv")
    transition_rows = read_csv(PROCESSED / "pif_13f_transition_summary.csv")

    dates = [row["as_of_date"] for row in snapshot_rows]
    compact_dates = sparsify_labels([compact_date_label(d) for d in dates], max_labels=10)

    charts: dict[str, str] = {}
    charts["holdings_count"] = line_chart_svg(
        compact_dates,
        [parse_float(row["holding_count"]) for row in snapshot_rows],
        title="PIF 13F Holdings Count",
        subtitle="Reported 13F positions per reporting period",
        color=COLORS["blue"],
        y_label_formatter=lambda v: f"{int(v):,}",
    )
    charts["market_value"] = line_chart_svg(
        compact_dates,
        [parse_float(row["total_market_value_usd"]) for row in snapshot_rows],
        title="PIF 13F Total Market Value",
        subtitle="Aggregate reported market value of the US-reportable 13F sleeve",
        color=COLORS["teal"],
        y_label_formatter=format_billions,
    )
    charts["total_shares"] = line_chart_svg(
        compact_dates,
        [parse_float(row["total_shares"]) for row in snapshot_rows],
        title="PIF 13F Total Shares",
        subtitle="Aggregate share count across reported 13F positions",
        color=COLORS["gold"],
        y_label_formatter=format_millions,
    )

    categories = ["Common", "Options"]
    option_mix = {
        "Common": [],
        "Options": [],
    }
    for row in snapshot_rows:
        common_count = parse_float(row["common_row_count"])
        option_count = parse_float(row["option_row_count"])
        total = common_count + option_count
        option_mix["Common"].append(common_count / total if total else 0.0)
        option_mix["Options"].append(option_count / total if total else 0.0)
    charts["option_mix"] = stacked_bar_chart_svg(
        compact_dates,
        categories,
        option_mix,
        title="Common vs Option Mix",
        subtitle="Share of reported rows that are common-equity positions versus option rows",
    )

    periods = [row["period"] for row in transition_rows]
    compact_periods = sparsify_labels([compact_date_label(p) for p in periods], max_labels=8)
    charts["transition_events"] = grouped_bar_chart_svg(
        compact_periods,
        [
            ("Entries", COLORS["blue"], [parse_float(row["entry_observed"]) for row in transition_rows]),
            ("Exits", COLORS["red"], [parse_float(row["exit_observed"]) for row in transition_rows]),
            ("Likely Accum.", COLORS["green"], [parse_float(row["likely_accumulation"]) for row in transition_rows]),
            ("Likely Reduct.", COLORS["gold"], [parse_float(row["likely_reduction"]) for row in transition_rows]),
        ],
        title="Transition Event Counts",
        subtitle="Counts derived from security-level share changes across consecutive 13F periods",
    )

    charts["net_share_delta"] = line_chart_svg(
        compact_periods,
        [parse_float(row["net_share_delta"]) for row in transition_rows],
        title="Net Share Delta by Period",
        subtitle="Aggregate change in shares across all reported 13F positions",
        color=COLORS["green"],
        y_label_formatter=format_millions,
        width=980,
    )
    charts["net_value_delta"] = line_chart_svg(
        compact_periods,
        [parse_float(row["net_market_value_delta_usd"]) for row in transition_rows],
        title="Net Market Value Delta by Period",
        subtitle="Aggregate change in reported market value across the disclosed 13F sleeve",
        color=COLORS["red"],
        y_label_formatter=format_billions,
        width=980,
    )

    paths: dict[str, Path] = {}
    for name, svg in charts.items():
        path = CHARTS_DIR / f"{name}.svg"
        write_text(path, svg)
        paths[name] = path
    return paths


def build_report(chart_paths: dict[str, Path]) -> None:
    snapshot_rows = read_csv(PROCESSED / "pif_13f_snapshot_summary.csv")
    transition_rows = read_csv(PROCESSED / "pif_13f_transition_summary.csv")

    snap = latest_snapshot_insights(snapshot_rows)
    trans = latest_transition_insights(transition_rows)

    html_report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PIF 13F Visual Report</title>
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
    <h1>PIF 13F Visual Report</h1>
    <div class="sub">Built from canonical PIF 13F holdings and share-driven transition events.</div>
  </div>
  <div class="grid">
    <div class="card">
      <div class="sub">Latest reporting period</div>
      <div class="metric">{escape(snap["latest_date"])}</div>
      <div class="sub">{escape(snap["holding_count"])} rows, {escape(snap["market_value"])}, largest holding {escape(snap["largest_holding"])}</div>
    </div>
    <div class="card">
      <div class="sub">Latest transition period</div>
      <div class="metric">{escape(trans["period"])}</div>
      <div class="sub">Entries {escape(trans["entries"])}, exits {escape(trans["exits"])}, likely accumulations {escape(trans["accumulations"])}, likely reductions {escape(trans["reductions"])}</div>
    </div>
  </div>
  <div class="card">
    <h2>Immediate Read</h2>
    <ul>
      <li>The disclosed PIF 13F sleeve evolves in bursts, with several periods that look like broad portfolio resets rather than gradual rebalancing.</li>
      <li>Because share counts are available, the transition dataset is much more informative here than in NBIM for spotting likely accumulations and reductions.</li>
      <li>The later filings introduce a meaningful option component: in the latest snapshot, option rows account for {escape(snap["option_share"])} of reported positions.</li>
      <li>The 13F dataset is still only a partial view of PIF, so any eventual mirroring test should be framed as mirroring the reported US 13F sleeve, not the fund as a whole.</li>
    </ul>
  </div>
  <div class="card"><img src="../charts/holdings_count.svg" alt="Holdings count chart"></div>
  <div class="card"><img src="../charts/market_value.svg" alt="Market value chart"></div>
  <div class="card"><img src="../charts/total_shares.svg" alt="Total shares chart"></div>
  <div class="card"><img src="../charts/option_mix.svg" alt="Option mix chart"></div>
  <div class="card"><img src="../charts/transition_events.svg" alt="Transition events chart"></div>
  <div class="card"><img src="../charts/net_share_delta.svg" alt="Net share delta chart"></div>
  <div class="card"><img src="../charts/net_value_delta.svg" alt="Net value delta chart"></div>
</body>
</html>
"""

    md_report = f"""# PIF 13F Visual Report

Latest reporting period: `{snap["latest_date"]}` with `{snap["holding_count"]}` rows, `{snap["market_value"]}` in reported market value, and largest holding `{snap["largest_holding"]}`.

Latest transition period: `{trans["period"]}` with `{trans["entries"]}` entries, `{trans["exits"]}` exits, `{trans["accumulations"]}` likely accumulations, and `{trans["reductions"]}` likely reductions.

## Key Takeaways

- The disclosed PIF 13F sleeve changes in bursts rather than on a smooth path.
- Share counts make the PIF transition dataset much stronger than the NBIM one for turnover inference.
- Option rows become important in later filings; the latest snapshot has `{snap["option_share"]}` option-row share.
- This is still a US 13F sleeve, not a complete picture of PIF.

## Charts

![Holdings Count]({chart_paths["holdings_count"]})
![Market Value]({chart_paths["market_value"]})
![Total Shares]({chart_paths["total_shares"]})
![Option Mix]({chart_paths["option_mix"]})
![Transition Events]({chart_paths["transition_events"]})
![Net Share Delta]({chart_paths["net_share_delta"]})
![Net Value Delta]({chart_paths["net_value_delta"]})
"""

    write_text(REPORTS_DIR / "pif_visual_report.html", html_report)
    write_text(REPORTS_DIR / "pif_visual_report.md", md_report)


def main() -> None:
    ensure_dirs()
    chart_paths = build_charts()
    build_report(chart_paths)
    print(f"Wrote charts to {CHARTS_DIR}")
    print(f"Wrote reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
