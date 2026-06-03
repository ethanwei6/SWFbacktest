from __future__ import annotations

import csv
import html
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIF_ROOT = ROOT / "data" / "processed" / "pif"
BACKTEST_ROOT = PIF_ROOT / "backtests"
ANALYSIS_DATA_DIR = BACKTEST_ROOT / "analysis"
CHARTS_DIR = ROOT / "outputs" / "pif" / "backtests" / "charts"
REPORTS_DIR = ROOT / "outputs" / "pif" / "backtests" / "reports"

PRICE_PATH = PIF_ROOT / "pif_twelvedata_daily_prices.csv"
BENCHMARK_PATH = PIF_ROOT / "pif_benchmark_daily.csv"

STRATEGIES = [
    {
        "key": "p1",
        "name": "P1 New Positions Mirror",
        "dir": BACKTEST_ROOT / "p1",
        "prefix": "p1",
        "color": "#C2410C",
    },
    {
        "key": "p2",
        "name": "P2 Full Sleeve Equal Weight",
        "dir": BACKTEST_ROOT / "p2_equal_weight",
        "prefix": "p2ew",
        "color": "#0B5FFF",
    },
    {
        "key": "p3",
        "name": "P3 Accumulation Tilt",
        "dir": BACKTEST_ROOT / "p3_accumulation_tilt",
        "prefix": "p3at",
        "color": "#15803D",
    },
    {
        "key": "p4",
        "name": "P4 Exit Avoidance",
        "dir": BACKTEST_ROOT / "p4_exit_avoidance",
        "prefix": "p4ea",
        "color": "#7C3AED",
    },
    {
        "key": "p5",
        "name": "P5 Cash-Aware Copy",
        "dir": BACKTEST_ROOT / "p5_cash_aware_copy",
        "prefix": "p5cac",
        "color": "#BE185D",
    },
]

COLORS = {
    "blue": "#0B5FFF",
    "teal": "#0A7C86",
    "gold": "#D97706",
    "red": "#C2410C",
    "green": "#15803D",
    "magenta": "#BE185D",
    "violet": "#7C3AED",
    "slate": "#334155",
    "gray": "#94A3B8",
    "grid": "#E2E8F0",
    "bg": "#F8FAFC",
    "text": "#0F172A",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        if not rows:
            return
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


def to_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def escape(text: str) -> str:
    return html.escape(text)


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
    for index, label in enumerate(labels):
        if index % step == 0 or index == len(labels) - 1:
            sparse.append(label)
        else:
            sparse.append("")
    return sparse


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_num(value: float) -> str:
    return f"{value:.2f}"


def format_nav(value: float) -> str:
    return f"{value:.3f}x"


def format_days(value: float) -> str:
    return f"{value:.0f}"


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
    y_label_formatter,
    width: int = 980,
    height: int = 440,
) -> str:
    left = 72
    right = 20
    top = 64
    bottom = 84
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_values = [value for _, _, values in series for value in values]
    min_v = min(all_values) if all_values else 0.0
    max_v = max(all_values) if all_values else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_label_formatter(value))}</text>'
        )

    points_by_series: list[tuple[str, str, list[tuple[float, float]]]] = []
    count = max((len(values) for _, _, values in series), default=0)
    for name, color, values in series:
        points = []
        for i, value in enumerate(values):
            x = left + (plot_w * i / max(1, count - 1))
            y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            points.append((x, y))
        points_by_series.append((name, color, points))

    paths = []
    for _, color, points in points_by_series:
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}" />')
        for x, y in points:
            paths.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{color}" />')

    x_labels = "".join(
        f'<text x="{left + (plot_w * i / max(1, len(labels) - 1)):.1f}" y="{height - 34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>'
        for i, label in enumerate(labels)
        if label
    )

    legend = []
    legend_x = left
    legend_y = height - 16
    for name, color, _ in series:
        legend.append(f'<rect x="{legend_x}" y="{legend_y - 10}" width="12" height="12" fill="{color}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{legend_y}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 170

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(paths)}
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
    y_label_formatter=lambda value: f"{value:.0f}",
    width: int = 980,
    height: int = 460,
) -> str:
    left = 72
    right = 20
    top = 64
    bottom = 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [v for _, _, arr in series for v in arr]
    max_v = max(values) if values else 1.0
    min_v = min(0.0, min(values) if values else 0.0)
    if max_v == min_v:
        max_v = min_v + 1.0

    groups = len(labels)
    bars_per_group = len(series)
    group_w = plot_w / max(1, groups)
    bar_w = min(22, group_w / max(1, bars_per_group + 1))

    grid = []
    zero_y = top + plot_h - ((0.0 - min_v) / (max_v - min_v) * plot_h)
    for j in range(5):
        frac = j / 4
        value = min_v + frac * (max_v - min_v)
        y = top + plot_h - frac * plot_h
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(y_label_formatter(value))}</text>'
        )
    grid.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="{COLORS["slate"]}" stroke-width="1.2"/>')

    bars = []
    for i, label in enumerate(labels):
        gx = left + i * group_w
        for j, (_, color, values_for_series) in enumerate(series):
            value = values_for_series[i]
            y_value = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            y = min(y_value, zero_y)
            h = abs(zero_y - y_value)
            x = gx + 10 + j * (bar_w + 3)
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        if label:
            bars.append(
                f'<text x="{gx + group_w/2:.1f}" y="{height - 38}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>'
            )

    legend = []
    legend_x = left
    legend_y = height - 16
    for name, color, _ in series:
        legend.append(f'<rect x="{legend_x}" y="{legend_y - 10}" width="12" height="12" fill="{color}" rx="2"/>')
        legend.append(f'<text x="{legend_x + 18}" y="{legend_y}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 160

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
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
    color_positive: str = COLORS["green"],
    color_negative: str = COLORS["red"],
    width: int = 980,
    height: int = 420,
) -> str:
    left = 230
    right = 36
    top = 64
    bottom = 28
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
        y = top + i * row_h + row_h * 0.17
        h = row_h * 0.66
        w = abs(value) / max_abs * (plot_w / 2)
        if value >= 0:
            x = zero_x
            color = color_positive
        else:
            x = zero_x - w
            color = color_negative
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}" rx="3"/>')
        bars.append(f'<text x="{left - 10}" y="{y + h/2 + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["text"]}">{escape(label)}</text>')
        anchor = "start" if value >= 0 else "end"
        text_x = x + w + 6 if value >= 0 else x - 6
        bars.append(f'<text x="{text_x:.1f}" y="{y + h/2 + 4:.1f}" text-anchor="{anchor}" font-size="11" fill="{COLORS["slate"]}">{format_pct(value)}</text>')

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(bars)}
    """
    return wrap_svg(content, width, height)


def scatter_chart_svg(
    points: list[dict[str, object]],
    *,
    title: str,
    subtitle: str,
    x_label: str,
    y_label: str,
    width: int = 900,
    height: int = 500,
) -> str:
    left = 86
    right = 30
    top = 64
    bottom = 86
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [float(point["x"]) for point in points] or [0.0]
    ys = [float(point["y"]) for point in points] or [0.0]
    min_x = min(xs) * 0.95
    max_x = max(xs) * 1.05 if max(xs) != 0 else 1.0
    min_y = min(ys) * 1.05
    max_y = max(ys) * 1.15 if max(ys) != 0 else 1.0
    if max_x == min_x:
        max_x = min_x + 1.0
    if max_y == min_y:
        max_y = min_y + 1.0

    grid = []
    for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = left + frac * plot_w
        value = min_x + frac * (max_x - min_x)
        grid.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{x:.1f}" y="{height-bottom+20}" text-anchor="middle" font-size="11" fill="{COLORS["slate"]}">{format_pct(value)}</text>')
        y = top + plot_h - frac * plot_h
        y_value = min_y + frac * (max_y - min_y)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{format_pct(y_value)}</text>')

    marks = []
    for point in points:
        x_v = float(point["x"])
        y_v = float(point["y"])
        x = left + ((x_v - min_x) / (max_x - min_x) * plot_w)
        y = top + plot_h - ((y_v - min_y) / (max_y - min_y) * plot_h)
        color = str(point["color"])
        label = str(point["label"])
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{color}" opacity="0.9"/>')
        marks.append(f'<text x="{x + 12:.1f}" y="{y + 4:.1f}" font-size="12" fill="{COLORS["text"]}">{escape(label)}</text>')

    content = f"""
    <rect width="{width}" height="{height}" fill="white"/>
    <text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS['text']}">{escape(title)}</text>
    <text x="{left}" y="50" font-size="12" fill="{COLORS['slate']}">{escape(subtitle)}</text>
    {''.join(grid)}
    {''.join(marks)}
    <text x="{left + plot_w / 2:.1f}" y="{height - 18}" text-anchor="middle" font-size="12" fill="{COLORS["slate"]}">{escape(x_label)}</text>
    <text x="24" y="{top + plot_h / 2:.1f}" transform="rotate(-90 24,{top + plot_h / 2:.1f})" text-anchor="middle" font-size="12" fill="{COLORS["slate"]}">{escape(y_label)}</text>
    """
    return wrap_svg(content, width, height)


def load_price_lookup(price_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup = {}
    for row in price_rows:
        if row["adjust_mode"] != "all":
            continue
        lookup[(row["security_key"], row["date"])] = row
    if lookup:
        return lookup
    for row in price_rows:
        if row["adjust_mode"] != "none":
            continue
        lookup[(row["security_key"], row["date"])] = row
    return lookup


def load_calendar_dates(price_rows: list[dict[str, str]]) -> list[str]:
    adjusted = sorted({row["date"] for row in price_rows if row["adjust_mode"] == "all"})
    if adjusted:
        return adjusted
    return sorted({row["date"] for row in price_rows if row["adjust_mode"] == "none"})


def load_benchmark_lookup(rows: list[dict[str, str]], benchmark_key: str = "SPY") -> dict[str, dict[str, str]]:
    return {
        row["date"]: row
        for row in rows
        if row.get("benchmark_key") == benchmark_key and row.get("adjust_mode") == "all"
    }


def benchmark_row_on_or_before(
    target_date: str,
    benchmark_dates: list[str],
    benchmark_lookup: dict[str, dict[str, str]],
) -> tuple[dict[str, str] | None, str]:
    last_date = ""
    for candidate in benchmark_dates:
        if candidate > target_date:
            break
        last_date = candidate
    if not last_date:
        return None, ""
    row = benchmark_lookup.get(last_date)
    if row is None:
        return None, last_date
    return row, ("exact_close" if last_date == target_date else "carry_forward_close")


def build_previous_trading_date_map(calendar_dates: list[str]) -> dict[str, str]:
    out = {}
    for index, current in enumerate(calendar_dates):
        out[current] = calendar_dates[index - 1] if index > 0 else current
    return out


def load_strategy_bundle(meta: dict[str, object]) -> dict[str, object]:
    strategy_dir = Path(meta["dir"])
    prefix = str(meta["prefix"])
    with (strategy_dir / f"{prefix}_summary.json").open("r", encoding="utf-8") as infile:
        summary = json.load(infile)
    return {
        "meta": meta,
        "summary": summary,
        "portfolio": read_csv(strategy_dir / f"{prefix}_portfolio_daily.csv"),
        "holdings": read_csv(strategy_dir / f"{prefix}_holdings_daily.csv"),
        "rebalances": read_csv(strategy_dir / f"{prefix}_rebalance_events.csv"),
        "eligibility": read_csv(strategy_dir / f"{prefix}_signal_eligibility.csv"),
        "orders": read_csv(strategy_dir / f"{prefix}_orders.csv"),
    }


def build_eval_end_map(rebalances: list[dict[str, str]], previous_trade_date_map: dict[str, str], final_date: str) -> dict[str, str]:
    out = {}
    for row in rebalances:
        trade_date = row["trade_date"]
        next_trade_date = row["next_rebalance_trade_date"]
        if next_trade_date:
            out[trade_date] = previous_trade_date_map[next_trade_date]
        else:
            out[trade_date] = final_date
    return out


def compute_strategy_metrics(bundle: dict[str, object]) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    meta = bundle["meta"]
    summary = bundle["summary"]
    portfolio_rows = bundle["portfolio"]
    holdings_rows = bundle["holdings"]
    orders_rows = bundle["orders"]
    rebalances = bundle["rebalances"]

    returns = [to_float(row["return_day"]) for row in portfolio_rows[1:]]
    nav_rows = [to_float(row["nav_end"]) for row in portfolio_rows]
    position_counts = [to_float(row["position_count_end"]) for row in portfolio_rows]
    start_d = to_date(summary["start_date"])
    end_d = to_date(summary["end_date"])
    years = max((end_d - start_d).days / 365.25, 1 / 365.25)
    final_nav = float(summary["final_nav"])
    cagr = final_nav ** (1 / years) - 1 if final_nav > 0 else -1.0
    annual_vol = statistics.pstdev(returns) * math.sqrt(252) if len(returns) > 1 else 0.0
    sharpe = statistics.mean(returns) / statistics.pstdev(returns) * math.sqrt(252) if len(returns) > 1 and statistics.pstdev(returns) > 0 else 0.0
    positive_day_ratio = sum(1 for value in returns if value > 0) / len(returns) if returns else 0.0

    holdings_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in holdings_rows:
        holdings_by_date[row["date"]].append(row)

    max_weight_by_date = {}
    top3_weight_by_date = {}
    weight_sum_by_date = {}
    entry_day_pnl_violations = 0
    price_status_counts = Counter()
    contributor_counter = Counter()
    for day, rows in holdings_by_date.items():
        weights = [to_float(row["weight_end"]) for row in rows]
        sorted_weights = sorted(weights, reverse=True)
        max_weight_by_date[day] = sorted_weights[0] if sorted_weights else 0.0
        top3_weight_by_date[day] = sum(sorted_weights[:3])
        weight_sum_by_date[day] = sum(weights)
        for row in rows:
            if row["date"] == row["entry_trade_date"] and abs(to_float(row["pnl_day"])) > 1e-10:
                entry_day_pnl_violations += 1
            price_status_counts[row["price_status"]] += 1
            contributor_counter[row["issuer_name"]] += to_float(row["return_contribution_day"])

    gross_exposures = [to_float(row["gross_exposure_end"]) for row in portfolio_rows]
    cash_values = [to_float(row["cash_end"]) for row in portfolio_rows]
    date_index = {row["date"]: row for row in portfolio_rows}
    position_count_mismatch_days = 0
    for day, rows in holdings_by_date.items():
        expected = int(to_float(date_index[day]["position_count_end"]))
        if expected != len(rows):
            position_count_mismatch_days += 1

    arithmetic_violations = 0
    for row in portfolio_rows:
        nav_start = to_float(row["nav_start"])
        pnl_day = to_float(row["pnl_day"])
        nav_pre = to_float(row["nav_pre_rebalance"])
        nav_end = to_float(row["nav_end"])
        ret = to_float(row["return_day"])
        if abs((nav_start + pnl_day) - nav_pre) > 1e-8:
            arithmetic_violations += 1
        if nav_start > 0 and abs((nav_end / nav_start - 1) - ret) > 1e-8:
            arithmetic_violations += 1

    rebalance_rows = [row for row in portfolio_rows if row["rebalance_executed_flag"] == "1"]
    total_buys = sum(int(to_float(row["buys_count"])) for row in rebalance_rows)
    total_sells = sum(int(to_float(row["sells_count"])) for row in rebalance_rows)

    summary_row = {
        "strategy_key": str(meta["key"]),
        "strategy_name": str(meta["name"]),
        "start_date": summary["start_date"],
        "end_date": summary["end_date"],
        "final_nav": f"{final_nav:.12f}",
        "total_return": f"{float(summary['total_return']):.12f}",
        "cagr": f"{cagr:.12f}",
        "annual_volatility": f"{annual_vol:.12f}",
        "sharpe_zero_rf": f"{sharpe:.12f}",
        "max_drawdown": f"{float(summary['max_drawdown']):.12f}",
        "positive_day_ratio": f"{positive_day_ratio:.12f}",
        "rebalance_count": str(summary["rebalance_count"]),
        "orders_count": str(summary["orders_count"]),
        "avg_position_count": f"{statistics.mean(position_counts):.6f}",
        "median_position_count": f"{statistics.median(position_counts):.6f}",
        "avg_max_weight": f"{statistics.mean(max_weight_by_date.values()):.12f}",
        "avg_top3_weight": f"{statistics.mean(top3_weight_by_date.values()):.12f}",
        "peak_nav": f"{max(nav_rows):.12f}",
        "trough_nav": f"{min(nav_rows):.12f}",
        "best_day_return": f"{max(returns) if returns else 0.0:.12f}",
        "worst_day_return": f"{min(returns) if returns else 0.0:.12f}",
        "total_buys": str(total_buys),
        "total_sells": str(total_sells),
    }

    sanity_row = {
        "strategy_key": str(meta["key"]),
        "strategy_name": str(meta["name"]),
        "portfolio_rows": str(len(portfolio_rows)),
        "holdings_rows": str(len(holdings_rows)),
        "arithmetic_violations": str(arithmetic_violations),
        "gross_exposure_min": f"{min(gross_exposures):.12f}",
        "gross_exposure_max": f"{max(gross_exposures):.12f}",
        "cash_end_min": f"{min(cash_values):.12f}",
        "cash_end_max": f"{max(cash_values):.12f}",
        "weight_sum_min": f"{min(weight_sum_by_date.values()):.12f}",
        "weight_sum_max": f"{max(weight_sum_by_date.values()):.12f}",
        "entry_day_pnl_violations": str(entry_day_pnl_violations),
        "position_count_mismatch_days": str(position_count_mismatch_days),
        "non_exact_price_rows": str(sum(count for key, count in price_status_counts.items() if key not in {'exact_close', 'exact_adjusted_close'})),
        "price_status_breakdown": json.dumps(price_status_counts, sort_keys=True),
    }

    top_contributors = []
    for direction, items in [
        ("top", contributor_counter.most_common(10)),
        ("bottom", list(reversed(contributor_counter.most_common()))[:10],
        ),
    ]:
        for issuer_name, contribution in items:
            top_contributors.append(
                {
                    "strategy_key": str(meta["key"]),
                    "strategy_name": str(meta["name"]),
                    "bucket": direction,
                    "issuer_name": issuer_name,
                    "total_return_contribution": f"{contribution:.12f}",
                }
            )

    period_rows = []
    nav_lookup = {row["date"]: to_float(row["nav_end"]) for row in portfolio_rows}
    for row in rebalances:
        trade_date = row["trade_date"]
        next_trade_date = row["next_rebalance_trade_date"]
        if not next_trade_date:
            continue
        start_nav = nav_lookup[trade_date]
        end_date_for_period = max(day for day in nav_lookup if trade_date <= day < next_trade_date)
        end_nav = nav_lookup[end_date_for_period]
        period_rows.append(
            {
                "strategy_key": str(meta["key"]),
                "strategy_name": str(meta["name"]),
                "rebalance_id": row["rebalance_id"],
                "trade_date": trade_date,
                "next_rebalance_trade_date": next_trade_date,
                "evaluation_end_date": end_date_for_period,
                "period_return": f"{(end_nav / start_nav - 1) if start_nav else 0.0:.12f}",
                "included_count": row.get("eligible_entry_signal_count", row.get("eligible_holding_signal_count", "0")),
                "positions_bought_count": row["positions_bought_count"],
                "positions_sold_count": row["positions_sold_count"],
            }
        )

    return summary_row, sanity_row, top_contributors, period_rows, []


def compute_benchmark_metrics(
    bundle: dict[str, object],
    benchmark_lookup: dict[str, dict[str, str]],
    benchmark_key: str = "SPY",
) -> tuple[dict[str, str], list[dict[str, str]]]:
    portfolio_rows = bundle["portfolio"]
    benchmark_dates = sorted(benchmark_lookup)
    if not portfolio_rows:
        return {
            "strategy_key": str(bundle["meta"]["key"]),
            "strategy_name": str(bundle["meta"]["name"]),
            "benchmark_key": benchmark_key,
            "benchmark_start_date": "",
            "benchmark_end_date": "",
            "benchmark_start_close": "",
            "benchmark_end_close": "",
            "benchmark_final_nav": "",
            "benchmark_total_return": "",
            "benchmark_cagr": "",
            "benchmark_annual_volatility": "",
            "annualized_excess_return": "",
            "information_ratio": "",
            "excess_final_nav_ratio": "",
            "excess_total_return": "",
            "positive_excess_day_ratio": "",
        }, []

    start_date = portfolio_rows[0]["date"]
    end_date = portfolio_rows[-1]["date"]
    start_row, start_status = benchmark_row_on_or_before(start_date, benchmark_dates, benchmark_lookup)
    end_row, end_status = benchmark_row_on_or_before(end_date, benchmark_dates, benchmark_lookup)
    if start_row is None or end_row is None:
        raise KeyError(f"Missing benchmark coverage for {benchmark_key} on {start_date} or {end_date}")

    start_close = to_float(start_row["close"])
    end_close = to_float(end_row["close"])
    benchmark_final_nav = end_close / start_close if start_close else 0.0
    benchmark_total_return = benchmark_final_nav - 1.0

    start_d = to_date(start_date)
    end_d = to_date(end_date)
    years = max((end_d - start_d).days / 365.25, 1 / 365.25)
    benchmark_cagr = benchmark_final_nav ** (1 / years) - 1 if benchmark_final_nav > 0 else -1.0

    benchmark_rows = []
    benchmark_returns = []
    excess_returns = []
    for index, row in enumerate(portfolio_rows):
        date_value = row["date"]
        benchmark_row, benchmark_price_status = benchmark_row_on_or_before(date_value, benchmark_dates, benchmark_lookup)
        if benchmark_row is None:
            raise KeyError(f"Missing benchmark price for {benchmark_key} on {date_value}")
        benchmark_close = to_float(benchmark_row["close"])
        benchmark_nav = benchmark_close / start_close if start_close else 0.0
        if index == 0:
            benchmark_return_day = 0.0
        else:
            prev_row, _ = benchmark_row_on_or_before(portfolio_rows[index - 1]["date"], benchmark_dates, benchmark_lookup)
            prev_close = to_float(prev_row["close"]) if prev_row is not None else 0.0
            benchmark_return_day = benchmark_close / prev_close - 1 if prev_close else 0.0
        strategy_return_day = to_float(row["return_day"])
        benchmark_returns.append(benchmark_return_day)
        excess_return_day = strategy_return_day - benchmark_return_day
        excess_returns.append(excess_return_day)
        benchmark_rows.append(
            {
                "strategy_key": str(bundle["meta"]["key"]),
                "strategy_name": str(bundle["meta"]["name"]),
                "benchmark_key": benchmark_key,
                "date": date_value,
                "strategy_nav": row["nav_end"],
                "benchmark_nav": f"{benchmark_nav:.12f}",
                "strategy_return_day": row["return_day"],
                "benchmark_return_day": f"{benchmark_return_day:.12f}",
                "excess_return_day": f"{excess_return_day:.12f}",
                "relative_nav_ratio": f"{(to_float(row['nav_end']) / benchmark_nav) if benchmark_nav else 0.0:.12f}",
                "benchmark_price_status": benchmark_price_status,
            }
        )

    benchmark_ann_vol = statistics.pstdev(benchmark_returns[1:]) * math.sqrt(252) if len(benchmark_returns) > 2 else 0.0
    annualized_excess_return = statistics.mean(excess_returns[1:]) * 252 if len(excess_returns) > 2 else 0.0
    information_ratio = (
        statistics.mean(excess_returns[1:]) / statistics.pstdev(excess_returns[1:]) * math.sqrt(252)
        if len(excess_returns) > 2 and statistics.pstdev(excess_returns[1:]) > 0
        else 0.0
    )
    positive_excess_day_ratio = (
        sum(1 for value in excess_returns[1:] if value > 0) / len(excess_returns[1:])
        if len(excess_returns) > 1 else 0.0
    )

    summary_row = {
        "strategy_key": str(bundle["meta"]["key"]),
        "strategy_name": str(bundle["meta"]["name"]),
        "benchmark_key": benchmark_key,
        "benchmark_start_date": start_date,
        "benchmark_end_date": end_date,
        "benchmark_start_price_status": start_status,
        "benchmark_end_price_status": end_status,
        "benchmark_start_close": f"{start_close:.12f}",
        "benchmark_end_close": f"{end_close:.12f}",
        "benchmark_final_nav": f"{benchmark_final_nav:.12f}",
        "benchmark_total_return": f"{benchmark_total_return:.12f}",
        "benchmark_cagr": f"{benchmark_cagr:.12f}",
        "benchmark_annual_volatility": f"{benchmark_ann_vol:.12f}",
        "annualized_excess_return": f"{annualized_excess_return:.12f}",
        "information_ratio": f"{information_ratio:.12f}",
        "excess_final_nav_ratio": f"{(to_float(portfolio_rows[-1]['nav_end']) / benchmark_final_nav) if benchmark_final_nav else 0.0:.12f}",
        "excess_total_return": f"{((to_float(portfolio_rows[-1]['nav_end']) / benchmark_final_nav) - 1.0) if benchmark_final_nav else 0.0:.12f}",
        "positive_excess_day_ratio": f"{positive_excess_day_ratio:.12f}",
    }
    return summary_row, benchmark_rows


def compute_signal_forward_return(
    security_key: str,
    trade_date: str,
    end_date: str,
    price_lookup: dict[tuple[str, str], dict[str, str]],
) -> float | None:
    start_row = price_lookup.get((security_key, trade_date))
    end_row = price_lookup.get((security_key, end_date))
    if start_row is None or end_row is None:
        return None
    start_close = to_float(start_row["close"])
    end_close = to_float(end_row["close"])
    if start_close == 0:
        return None
    return end_close / start_close - 1


def compute_forward_signal_analytics(
    bundles: dict[str, dict[str, object]],
    price_lookup: dict[tuple[str, str], dict[str, str]],
    previous_trade_date_map: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    p1_rows = []
    p3_rows = []
    p4_rows = []

    # P1 entry cohorts
    p1_bundle = bundles["p1"]
    p1_eval_map = build_eval_end_map(
        p1_bundle["rebalances"], previous_trade_date_map, p1_bundle["summary"]["end_date"]
    )
    p1_signal_rows = [row for row in p1_bundle["eligibility"] if row["include_flag"] == "1"]
    by_trade_date: dict[str, list[float]] = defaultdict(list)
    for row in p1_signal_rows:
        trade_date = row["trade_date"]
        next_end = p1_eval_map.get(trade_date, "")
        if not next_end or next_end == trade_date:
            continue
        forward_return = compute_signal_forward_return(
            row["security_key"], trade_date, next_end, price_lookup
        )
        if forward_return is None:
            continue
        p1_rows.append(
            {
                "trade_date": trade_date,
                "issuer_name": row["issuer_name"],
                "symbol": row["selected_symbol"],
                "evaluation_end_date": next_end,
                "forward_return": f"{forward_return:.12f}",
            }
        )
        by_trade_date[trade_date].append(forward_return)

    # P3 bucket behavior
    p3_bundle = bundles["p3"]
    p3_eval_map = build_eval_end_map(
        p3_bundle["rebalances"], previous_trade_date_map, p3_bundle["summary"]["end_date"]
    )
    for row in p3_bundle["eligibility"]:
        if row["include_flag"] != "1":
            continue
        trade_date = row["trade_date"]
        next_end = p3_eval_map.get(trade_date, "")
        if not next_end or next_end == trade_date:
            continue
        forward_return = compute_signal_forward_return(
            row["security_key"], trade_date, next_end, price_lookup
        )
        if forward_return is None:
            continue
        p3_rows.append(
            {
                "trade_date": trade_date,
                "issuer_name": row["issuer_name"],
                "symbol": row["selected_symbol"],
                "tilt_bucket": row["tilt_bucket"],
                "transition_signal_type": row["transition_signal_type"],
                "evaluation_end_date": next_end,
                "forward_return": f"{forward_return:.12f}",
            }
        )

    # P4 avoided names vs kept names
    p4_bundle = bundles["p4"]
    p4_eval_map = build_eval_end_map(
        p4_bundle["rebalances"], previous_trade_date_map, p4_bundle["summary"]["end_date"]
    )
    for row in p4_bundle["eligibility"]:
        trade_date = row["trade_date"]
        next_end = p4_eval_map.get(trade_date, "")
        if not next_end or next_end == trade_date:
            continue
        if row["selected_symbol"] == "":
            continue
        forward_return = compute_signal_forward_return(
            row["security_key"], trade_date, next_end, price_lookup
        )
        if forward_return is None:
            continue
        cohort = "kept"
        if row["exclusion_reason"] == "likely_reduction_avoidance":
            cohort = "avoided_reduction"
        elif row["include_flag"] != "1":
            continue
        p4_rows.append(
            {
                "trade_date": trade_date,
                "issuer_name": row["issuer_name"],
                "symbol": row["selected_symbol"],
                "transition_signal_type": row["transition_signal_type"],
                "cohort": cohort,
                "evaluation_end_date": next_end,
                "forward_return": f"{forward_return:.12f}",
            }
        )

    return p1_rows, p3_rows, p4_rows


def build_analysis_tables(
    summary_rows: list[dict[str, str]],
    benchmark_summary_rows: list[dict[str, str]],
    benchmark_daily_rows: list[dict[str, str]],
    sanity_rows: list[dict[str, str]],
    contributor_rows: list[dict[str, str]],
    period_rows: list[dict[str, str]],
    p1_signal_rows: list[dict[str, str]],
    p3_signal_rows: list[dict[str, str]],
    p4_signal_rows: list[dict[str, str]],
) -> None:
    write_csv(ANALYSIS_DATA_DIR / "strategy_summary.csv", summary_rows)
    write_csv(ANALYSIS_DATA_DIR / "strategy_vs_benchmark_summary.csv", benchmark_summary_rows)
    write_csv(ANALYSIS_DATA_DIR / "strategy_vs_benchmark_daily.csv", benchmark_daily_rows)
    write_csv(ANALYSIS_DATA_DIR / "strategy_sanity_checks.csv", sanity_rows)
    write_csv(ANALYSIS_DATA_DIR / "strategy_top_contributors.csv", contributor_rows)
    write_csv(ANALYSIS_DATA_DIR / "strategy_rebalance_period_returns.csv", period_rows)
    write_csv(ANALYSIS_DATA_DIR / "p1_entry_forward_returns.csv", p1_signal_rows)
    write_csv(ANALYSIS_DATA_DIR / "p3_bucket_forward_returns.csv", p3_signal_rows)
    write_csv(ANALYSIS_DATA_DIR / "p4_avoidance_forward_returns.csv", p4_signal_rows)


def build_charts(
    bundles: dict[str, dict[str, object]],
    summary_rows: list[dict[str, str]],
    benchmark_summary_rows: list[dict[str, str]],
    benchmark_daily_rows: list[dict[str, str]],
    p1_signal_rows: list[dict[str, str]],
    p3_signal_rows: list[dict[str, str]],
    p4_signal_rows: list[dict[str, str]],
) -> dict[str, Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # NAV, drawdown, position counts
    all_dates = sorted(
        {
            row["date"]
            for bundle in bundles.values()
            for row in bundle["portfolio"]
        }
    )
    label_dates = sparsify_labels([compact_date_label(d) for d in all_dates], max_labels=12)

    chart_paths: dict[str, Path] = {}

    nav_series = []
    dd_series = []
    pos_series = []
    for strategy in STRATEGIES:
        bundle = bundles[strategy["key"]]
        by_date = {row["date"]: row for row in bundle["portfolio"]}
        nav_values = [to_float(by_date[d]["nav_end"]) if d in by_date else math.nan for d in all_dates]
        dd_values = [to_float(by_date[d]["drawdown_to_date"]) if d in by_date else math.nan for d in all_dates]
        pos_values = [to_float(by_date[d]["position_count_end"]) if d in by_date else math.nan for d in all_dates]
        # forward fill for line charts only after inception
        for values in [nav_values, dd_values, pos_values]:
            last = None
            for i, value in enumerate(values):
                if math.isnan(value):
                    if last is None:
                        values[i] = 0.0
                    else:
                        values[i] = last
                else:
                    last = value
        nav_series.append((strategy["name"], strategy["color"], nav_values))
        dd_series.append((strategy["name"], strategy["color"], dd_values))
        pos_series.append((strategy["name"], strategy["color"], pos_values))

    nav_svg = multi_line_chart_svg(
        label_dates,
        nav_series,
        title="PIF Strategy NAV Comparison",
        subtitle="Daily end-of-day NAV from each strategy's own inception date. Missing pre-inception windows are shown as flat zero placeholders.",
        y_label_formatter=format_nav,
    )
    path = CHARTS_DIR / "strategy_nav_comparison.svg"
    write_text(path, nav_svg)
    chart_paths["strategy_nav_comparison"] = path

    dd_svg = multi_line_chart_svg(
        label_dates,
        dd_series,
        title="PIF Strategy Drawdown Comparison",
        subtitle="Running drawdown from each strategy's own prior peak.",
        y_label_formatter=format_pct,
    )
    path = CHARTS_DIR / "strategy_drawdown_comparison.svg"
    write_text(path, dd_svg)
    chart_paths["strategy_drawdown_comparison"] = path

    pos_svg = multi_line_chart_svg(
        label_dates,
        pos_series,
        title="PIF Strategy Position Count",
        subtitle="How many names each strategy holds through time.",
        y_label_formatter=lambda value: f"{int(value):,}",
    )
    path = CHARTS_DIR / "strategy_position_count.svg"
    write_text(path, pos_svg)
    chart_paths["strategy_position_count"] = path

    scatter_points = []
    for strategy, row in zip(STRATEGIES, summary_rows):
        scatter_points.append(
            {
                "label": strategy["key"].upper(),
                "x": abs(float(row["max_drawdown"])),
                "y": float(row["total_return"]),
                "color": strategy["color"],
            }
        )
    scatter_svg = scatter_chart_svg(
        scatter_points,
        title="Return vs Drawdown",
        subtitle="Simple sanity frame: strong returns are only interesting if they did not require absurdly different drawdown profiles.",
        x_label="Absolute Max Drawdown",
        y_label="Total Return",
    )
    path = CHARTS_DIR / "strategy_return_vs_drawdown.svg"
    write_text(path, scatter_svg)
    chart_paths["strategy_return_vs_drawdown"] = path

    concentration_svg = grouped_bar_chart_svg(
        [strategy["key"].upper() for strategy in STRATEGIES],
        [
            ("Avg max weight", COLORS["gold"], [float(row["avg_max_weight"]) for row in summary_rows]),
            ("Avg top-3 weight", COLORS["violet"], [float(row["avg_top3_weight"]) for row in summary_rows]),
        ],
        title="Concentration by Strategy",
        subtitle="Average single-name concentration and average top-3 concentration across daily holdings snapshots.",
        y_label_formatter=format_pct,
        width=860,
    )
    path = CHARTS_DIR / "strategy_concentration.svg"
    write_text(path, concentration_svg)
    chart_paths["strategy_concentration"] = path

    benchmark_by_strategy = defaultdict(list)
    for row in benchmark_daily_rows:
        benchmark_by_strategy[row["strategy_key"]].append(row)

    rel_series = []
    for strategy in STRATEGIES:
        rows = benchmark_by_strategy[strategy["key"]]
        labels = [row["date"] for row in rows]
        values = [to_float(row["relative_nav_ratio"]) for row in rows]
        rel_series.append((strategy["name"], strategy["color"], values))
    rel_labels = sparsify_labels(
        [compact_date_label(row["date"]) for row in benchmark_by_strategy["p2"]],
        max_labels=12,
    ) if benchmark_by_strategy["p2"] else []
    rel_svg = multi_line_chart_svg(
        rel_labels,
        rel_series,
        title="Strategy NAV Relative to SPY",
        subtitle="Each series is strategy NAV divided by an SPY buy-and-hold NAV that starts on that strategy's own inception date. Above 1.0 means outperformance.",
        y_label_formatter=format_nav,
    )
    path = CHARTS_DIR / "strategy_relative_to_spy.svg"
    write_text(path, rel_svg)
    chart_paths["strategy_relative_to_spy"] = path

    by_key_benchmark = {row["strategy_key"]: row for row in benchmark_summary_rows}
    benchmark_bar_svg = grouped_bar_chart_svg(
        [strategy["key"].upper() for strategy in STRATEGIES],
        [
            ("Strategy total return", COLORS["blue"], [float(row["total_return"]) for row in summary_rows]),
            ("SPY total return", COLORS["gray"], [float(by_key_benchmark[row["strategy_key"]]["benchmark_total_return"]) for row in summary_rows]),
            ("Excess return", COLORS["magenta"], [float(by_key_benchmark[row["strategy_key"]]["excess_total_return"]) for row in summary_rows]),
        ],
        title="Strategy Returns vs SPY",
        subtitle="Absolute total return versus a matched-window SPY buy-and-hold benchmark.",
        y_label_formatter=format_pct,
        width=980,
        height=500,
    )
    path = CHARTS_DIR / "strategy_vs_spy_total_return.svg"
    write_text(path, benchmark_bar_svg)
    chart_paths["strategy_vs_spy_total_return"] = path

    excess_metric_svg = grouped_bar_chart_svg(
        [strategy["key"].upper() for strategy in STRATEGIES],
        [
            ("Annualized excess return", COLORS["teal"], [float(by_key_benchmark[row["strategy_key"]]["annualized_excess_return"]) for row in summary_rows]),
            ("Information ratio", COLORS["gold"], [float(by_key_benchmark[row["strategy_key"]]["information_ratio"]) for row in summary_rows]),
        ],
        title="Excess Return Quality vs SPY",
        subtitle="Annualized daily excess return and information ratio over SPY on matched dates.",
        y_label_formatter=lambda value: f"{value:.2f}" if abs(value) >= 1 else format_pct(value),
        width=920,
    )
    path = CHARTS_DIR / "strategy_vs_spy_excess_quality.svg"
    write_text(path, excess_metric_svg)
    chart_paths["strategy_vs_spy_excess_quality"] = path

    # P1 cohort forward returns
    by_trade_date: dict[str, list[float]] = defaultdict(list)
    for row in p1_signal_rows:
        by_trade_date[row["trade_date"]].append(to_float(row["forward_return"]))
    cohort_dates = sorted(by_trade_date)
    cohort_labels = sparsify_labels([compact_date_label(d) for d in cohort_dates], max_labels=10)
    cohort_mean = [statistics.mean(by_trade_date[d]) for d in cohort_dates]
    cohort_hit = [sum(1 for v in by_trade_date[d] if v > 0) / len(by_trade_date[d]) for d in cohort_dates]
    p1_svg = grouped_bar_chart_svg(
        cohort_labels,
        [
            ("Mean forward return", COLORS["red"], cohort_mean),
            ("Hit rate", COLORS["blue"], cohort_hit),
        ],
        title="P1 Entry Cohort Quality",
        subtitle="Forward return to the next rebalance date for each batch of newly disclosed entries.",
        y_label_formatter=format_pct,
    )
    path = CHARTS_DIR / "p1_entry_cohort_quality.svg"
    write_text(path, p1_svg)
    chart_paths["p1_entry_cohort_quality"] = path

    # P3 bucket effect
    p3_by_bucket: dict[str, list[float]] = defaultdict(list)
    for row in p3_signal_rows:
        p3_by_bucket[row["tilt_bucket"]].append(to_float(row["forward_return"]))
    bucket_labels = ["accumulation_like", "neutral"]
    p3_svg = grouped_bar_chart_svg(
        bucket_labels,
        [
            ("Mean forward return", COLORS["green"], [statistics.mean(p3_by_bucket.get(label, [0.0])) for label in bucket_labels]),
            ("Median forward return", COLORS["gold"], [statistics.median(p3_by_bucket.get(label, [0.0])) for label in bucket_labels]),
        ],
        title="P3 Bucket Forward Returns",
        subtitle="Did the names P3 overweight actually outperform the neutral sleeve names through the next filing window?",
        y_label_formatter=format_pct,
        width=880,
    )
    path = CHARTS_DIR / "p3_bucket_forward_returns.svg"
    write_text(path, p3_svg)
    chart_paths["p3_bucket_forward_returns"] = path

    # P4 avoidance effect by reduction quarter
    p4_period_cohorts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in p4_signal_rows:
        p4_period_cohorts[row["trade_date"]][row["cohort"]].append(to_float(row["forward_return"]))
    avoidance_dates = [d for d in sorted(p4_period_cohorts) if p4_period_cohorts[d].get("avoided_reduction")]
    avoidance_labels = sparsify_labels([compact_date_label(d) for d in avoidance_dates], max_labels=10)
    avoided_means = [statistics.mean(p4_period_cohorts[d]["avoided_reduction"]) for d in avoidance_dates]
    kept_means = [statistics.mean(p4_period_cohorts[d]["kept"]) for d in avoidance_dates]
    p4_svg = grouped_bar_chart_svg(
        avoidance_labels,
        [
            ("Avoided reductions", COLORS["red"], avoided_means),
            ("Kept names", COLORS["blue"], kept_means),
        ],
        title="P4 Reduction-Avoidance Effect",
        subtitle="Forward return comparison for quarters where P4 explicitly excluded likely reductions.",
        y_label_formatter=format_pct,
    )
    path = CHARTS_DIR / "p4_avoidance_effect.svg"
    write_text(path, p4_svg)
    chart_paths["p4_avoidance_effect"] = path

    # Top contributors chart from P4 for an interpretable winner set
    p4_bundle = bundles["p4"]
    contributor_counter = Counter()
    for row in p4_bundle["holdings"]:
        contributor_counter[row["issuer_name"]] += to_float(row["return_contribution_day"])
    top_items = contributor_counter.most_common(8)
    top_svg = horizontal_bar_chart_svg(
        [name for name, _ in top_items],
        [value for _, value in top_items],
        title="P4 Top Contributors",
        subtitle="Net contribution to total return across the full backtest.",
    )
    path = CHARTS_DIR / "p4_top_contributors.svg"
    write_text(path, top_svg)
    chart_paths["p4_top_contributors"] = path

    return chart_paths


def render_html_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    header = "".join(f"<th>{escape(col)}</th>" for col in columns)
    body_parts = []
    for row in rows:
        cells = "".join(f"<td>{escape(row.get(col, ''))}</td>" for col in columns)
        body_parts.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"


def build_report(
    bundles: dict[str, dict[str, object]],
    summary_rows: list[dict[str, str]],
    benchmark_summary_rows: list[dict[str, str]],
    sanity_rows: list[dict[str, str]],
    contributor_rows: list[dict[str, str]],
    p1_signal_rows: list[dict[str, str]],
    p3_signal_rows: list[dict[str, str]],
    p4_signal_rows: list[dict[str, str]],
    chart_paths: dict[str, Path],
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Strategy findings
    p1_mean = statistics.mean([to_float(row["forward_return"]) for row in p1_signal_rows]) if p1_signal_rows else 0.0
    p1_hit = sum(1 for row in p1_signal_rows if to_float(row["forward_return"]) > 0) / len(p1_signal_rows) if p1_signal_rows else 0.0
    p1_worst = min((to_float(row["forward_return"]) for row in p1_signal_rows), default=0.0)

    p3_bucket = defaultdict(list)
    for row in p3_signal_rows:
        p3_bucket[row["tilt_bucket"]].append(to_float(row["forward_return"]))
    p3_acc_mean = statistics.mean(p3_bucket["accumulation_like"]) if p3_bucket["accumulation_like"] else 0.0
    p3_neu_mean = statistics.mean(p3_bucket["neutral"]) if p3_bucket["neutral"] else 0.0
    p3_acc_min = min(p3_bucket["accumulation_like"]) if p3_bucket["accumulation_like"] else 0.0

    p4_by_cohort = defaultdict(list)
    for row in p4_signal_rows:
        p4_by_cohort[row["cohort"]].append(to_float(row["forward_return"]))
    p4_avoid_mean = statistics.mean(p4_by_cohort["avoided_reduction"]) if p4_by_cohort["avoided_reduction"] else 0.0
    p4_kept_mean = statistics.mean(p4_by_cohort["kept"]) if p4_by_cohort["kept"] else 0.0

    benchmark_by_key = {row["strategy_key"]: row for row in benchmark_summary_rows}
    summary_row_by_key = {row["strategy_key"]: row for row in summary_rows}
    p5_excess = float(benchmark_by_key["p5"]["excess_total_return"])
    p5_info_ratio = float(benchmark_by_key["p5"]["information_ratio"])
    best_excess_key, best_excess_row = max(benchmark_by_key.items(), key=lambda item: float(item[1]["excess_total_return"]))
    best_total_key, best_total_row = max(summary_row_by_key.items(), key=lambda item: float(item[1]["total_return"]))
    p2_total = float(summary_row_by_key["p2"]["total_return"])
    p2_excess = float(benchmark_by_key["p2"]["excess_total_return"])
    p5_total = float(summary_row_by_key["p5"]["total_return"])
    alpha_exists = any(float(row["excess_total_return"]) > 0 for row in benchmark_summary_rows)

    summary_display = []
    for row in summary_rows:
        bench = benchmark_by_key[row["strategy_key"]]
        summary_display.append(
            {
                "strategy": row["strategy_name"],
                "start": row["start_date"],
                "end": row["end_date"],
                "total_return": format_pct(float(row["total_return"])),
                "spy_return": format_pct(float(bench["benchmark_total_return"])),
                "excess_return": format_pct(float(bench["excess_total_return"])),
                "cagr": format_pct(float(row["cagr"])),
                "excess_ann": format_pct(float(bench["annualized_excess_return"])),
                "ann_vol": format_pct(float(row["annual_volatility"])),
                "max_drawdown": format_pct(float(row["max_drawdown"])),
                "avg_positions": format_num(float(row["avg_position_count"])),
                "avg_max_weight": format_pct(float(row["avg_max_weight"])),
                "sharpe_0rf": format_num(float(row["sharpe_zero_rf"])),
                "info_ratio": format_num(float(bench["information_ratio"])),
            }
        )

    sanity_display = []
    for row in sanity_rows:
        sanity_display.append(
            {
                "strategy": row["strategy_name"],
                "arith_violations": row["arithmetic_violations"],
                "gross_exposure_range": f"{float(row['gross_exposure_min']):.3f} to {float(row['gross_exposure_max']):.3f}",
                "weight_sum_range": f"{float(row['weight_sum_min']):.6f} to {float(row['weight_sum_max']):.6f}",
                "entry_day_pnl_violations": row["entry_day_pnl_violations"],
                "position_count_mismatch_days": row["position_count_mismatch_days"],
                "non_exact_price_rows": row["non_exact_price_rows"],
            }
        )

    contributor_display = []
    for strategy_key in ["p1", "p2", "p3", "p4", "p5"]:
        rows = [row for row in contributor_rows if row["strategy_key"] == strategy_key and row["bucket"] == "top"][:5]
        for row in rows:
            contributor_display.append(
                {
                    "strategy": row["strategy_name"],
                    "issuer_name": row["issuer_name"],
                    "contribution": format_pct(float(row["total_return_contribution"])),
                }
            )

    html_report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PIF Backtest Strategy Analysis</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 32px auto;
      max-width: 1180px;
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
    .grid3 {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
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
    h1, h2, h3 {{
      margin: 0 0 10px 0;
    }}
    ul {{
      margin: 8px 0 0 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
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
  </style>
</head>
<body>
  <div class="card">
    <h1>PIF Backtest Strategy Analysis</h1>
    <div class="sub">Sanity-checked comparison of the first four PIF strategies before building the interactive experience.</div>
  </div>

  <div class="grid3">
    <div class="card">
      <div class="sub">Best total return after split fix</div>
      <div class="metric">{escape(best_total_key.upper())} {format_pct(float(best_total_row["total_return"]))}</div>
      <div class="sub">Best absolute return after the split-adjusted rerun and same-day bundle fix. Absolute return still needs a benchmark check.</div>
    </div>
    <div class="card">
      <div class="sub">Best excess return vs SPY</div>
      <div class="metric">{escape(best_excess_key.upper())} {format_pct(float(best_excess_row["excess_total_return"]))}</div>
      <div class="sub">This is the strictest quick read on whether the public filings create alpha over a passive benchmark.</div>
    </div>
    <div class="card">
      <div class="sub">Alpha conclusion</div>
      <div class="metric">{'Weak positive evidence' if alpha_exists else 'No alpha vs SPY'}</div>
      <div class="sub">{'At least one strategy outperformed SPY on a matched-window basis.' if alpha_exists else 'All strategies lagged a simple SPY buy-and-hold benchmark over their own live windows.'}</div>
    </div>
  </div>

  <div class="card">
    <h2>Sanity Check Read</h2>
    <ul>
      <li>The mechanical checks are now clean: arithmetic violations are zero across all five strategies. `P1` through `P4` remain fully invested, while `P5` deliberately lets gross exposure fall and cash build when disclosed sells outpace disclosed buys.</li>
      <li>Two corrections matter most for the final `PIF` read. Split-adjusted marking removed false raw-price reverse-split gains, and same-day multi-period filing bundles are now traded as a single latest observable sleeve instead of as a union of stale periods.</li>
      <li>`P1` is weak because it is extremely concentrated. It carries only `{summary_display[0]["avg_positions"]}` names on average, its average max weight is `{summary_display[0]["avg_max_weight"]}`, and it periodically goes all-in on ugly cohorts, including a worst single forward return of `{format_pct(p1_worst)}`.</li>
      <li>`P3` does find stronger simple average forward returns in `accumulation_like` names ({format_pct(p3_acc_mean)} vs {format_pct(p3_neu_mean)} for `neutral`), but the tilted portfolio still loses more because it concentrates into names with deeper tail losses, including a worst accumulation-like forward return of `{format_pct(p3_acc_min)}`.</li>
      <li>`P4` does not rescue the sleeve. The names it avoided under the likely-reduction rule actually averaged `{format_pct(p4_avoid_mean)}` forward return, versus `{format_pct(p4_kept_mean)}` for the names it kept, so the exit-avoidance heuristic was directionally wrong in this sample.</li>
      <li>`P5` remains conceptually important even though it is no longer the top absolute-return strategy. Allowing cash to build keeps it positive at {format_pct(p5_total)}, which is more intuitive than forcing every disclosed sale back into the surviving names.</li>
      <li>The strict alpha question is benchmark-relative. `P2` is now the strongest absolute strategy at {format_pct(p2_total)}, but it still trails `SPY` by {format_pct(p2_excess)}. `P5` lags `SPY` by {format_pct(p5_excess)} with information ratio {format_num(p5_info_ratio)}. The corrected read is therefore “positive absolute results, but still no alpha versus `SPY`.”</li>
    </ul>
  </div>

  <div class="card"><img src="../charts/strategy_nav_comparison.svg" alt="Strategy NAV comparison"></div>
  <div class="card"><img src="../charts/strategy_relative_to_spy.svg" alt="Strategy relative to SPY"></div>
  <div class="card"><img src="../charts/strategy_drawdown_comparison.svg" alt="Strategy drawdown comparison"></div>
  <div class="grid">
    <div class="card"><img src="../charts/strategy_position_count.svg" alt="Strategy position counts"></div>
    <div class="card"><img src="../charts/strategy_return_vs_drawdown.svg" alt="Return vs drawdown"></div>
  </div>
  <div class="card"><img src="../charts/strategy_concentration.svg" alt="Strategy concentration"></div>
  <div class="grid">
    <div class="card"><img src="../charts/strategy_vs_spy_total_return.svg" alt="Strategy returns vs SPY"></div>
    <div class="card"><img src="../charts/strategy_vs_spy_excess_quality.svg" alt="Strategy excess quality vs SPY"></div>
  </div>
  <div class="grid">
    <div class="card"><img src="../charts/p1_entry_cohort_quality.svg" alt="P1 entry cohort quality"></div>
    <div class="card"><img src="../charts/p3_bucket_forward_returns.svg" alt="P3 bucket forward returns"></div>
  </div>
  <div class="grid">
    <div class="card"><img src="../charts/p4_avoidance_effect.svg" alt="P4 avoidance effect"></div>
    <div class="card"><img src="../charts/p4_top_contributors.svg" alt="P4 top contributors"></div>
  </div>

  <div class="card">
    <h2>Strategy Summary</h2>
    {render_html_table(summary_display, ["strategy", "start", "end", "total_return", "spy_return", "excess_return", "cagr", "excess_ann", "ann_vol", "max_drawdown", "avg_positions", "avg_max_weight", "sharpe_0rf", "info_ratio"])}
  </div>

  <div class="card">
    <h2>Sanity Check Table</h2>
    {render_html_table(sanity_display, ["strategy", "arith_violations", "gross_exposure_range", "weight_sum_range", "entry_day_pnl_violations", "position_count_mismatch_days", "non_exact_price_rows"])}
  </div>

  <div class="card">
    <h2>Top Contributors</h2>
    {render_html_table(contributor_display, ["strategy", "issuer_name", "contribution"])}
  </div>
</body>
</html>
"""

    md_report = f"""# PIF Backtest Strategy Analysis

This report is the sanity-check and benchmarked visual layer for the first five `PIF` strategies.

## Immediate Read

- After the split-adjusted rerun and same-day bundle fix, `P2` through `P5` are positive in absolute terms while `P1` remains deeply negative.
- `P2` is now the strongest absolute result at {format_pct(p2_total)}, while `P1` remains the weakest at {summary_display[0]["total_return"]}.
- The stricter alpha test is benchmark-relative. Against a matched-window `SPY` buy-and-hold, none of the strategies generates positive excess return in this first pass.
- `P1` is structurally fragile because it is highly concentrated: average max weight `{summary_display[0]["avg_max_weight"]}`, average positions `{summary_display[0]["avg_positions"]}`, and a worst forward cohort name at `{format_pct(p1_worst)}`.
- `P3` still loses even though `accumulation_like` names have higher simple average forward returns (`{format_pct(p3_acc_mean)}` vs `{format_pct(p3_neu_mean)}`), which points to concentration and tail-risk drag rather than no signal at all.
- `P4` is directionally unhelpful in this sample: avoided likely-reduction names averaged `{format_pct(p4_avoid_mean)}` forward return versus `{format_pct(p4_kept_mean)}` for the names it kept.
- `P5` still changes the interpretation of the whole project: when sale proceeds are retained as cash instead of being redistributed into remaining names, the strategy stays positive in absolute terms at {format_pct(p5_total)}, but it still fails to beat `SPY`.

## Charts

![Strategy NAV Comparison]({chart_paths["strategy_nav_comparison"]})
![Strategy Relative to SPY]({chart_paths["strategy_relative_to_spy"]})
![Strategy Drawdown Comparison]({chart_paths["strategy_drawdown_comparison"]})
![Strategy Position Count]({chart_paths["strategy_position_count"]})
![Return vs Drawdown]({chart_paths["strategy_return_vs_drawdown"]})
![Strategy Concentration]({chart_paths["strategy_concentration"]})
![Strategy Returns vs SPY]({chart_paths["strategy_vs_spy_total_return"]})
![Strategy Excess Quality vs SPY]({chart_paths["strategy_vs_spy_excess_quality"]})
![P1 Entry Cohort Quality]({chart_paths["p1_entry_cohort_quality"]})
![P3 Bucket Forward Returns]({chart_paths["p3_bucket_forward_returns"]})
![P4 Avoidance Effect]({chart_paths["p4_avoidance_effect"]})
![P4 Top Contributors]({chart_paths["p4_top_contributors"]})
"""

    write_text(REPORTS_DIR / "pif_backtest_analysis.html", html_report)
    write_text(REPORTS_DIR / "pif_backtest_analysis.md", md_report)


def main() -> None:
    ANALYSIS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    price_rows = read_csv(PRICE_PATH)
    benchmark_rows = read_csv(BENCHMARK_PATH)
    price_lookup = load_price_lookup(price_rows)
    benchmark_lookup = load_benchmark_lookup(benchmark_rows)
    calendar_dates = load_calendar_dates(price_rows)
    previous_trade_date_map = build_previous_trading_date_map(calendar_dates)

    bundles = {strategy["key"]: load_strategy_bundle(strategy) for strategy in STRATEGIES}

    summary_rows = []
    benchmark_summary_rows = []
    benchmark_daily_rows = []
    sanity_rows = []
    contributor_rows = []
    period_rows = []

    for strategy in STRATEGIES:
        bundle = bundles[strategy["key"]]
        summary_row, sanity_row, contributor_part, period_part, _ = compute_strategy_metrics(bundle)
        benchmark_summary_row, benchmark_daily_part = compute_benchmark_metrics(bundle, benchmark_lookup)
        summary_rows.append(summary_row)
        benchmark_summary_rows.append(benchmark_summary_row)
        benchmark_daily_rows.extend(benchmark_daily_part)
        sanity_rows.append(sanity_row)
        contributor_rows.extend(contributor_part)
        period_rows.extend(period_part)

    p1_signal_rows, p3_signal_rows, p4_signal_rows = compute_forward_signal_analytics(
        bundles, price_lookup, previous_trade_date_map
    )

    build_analysis_tables(
        summary_rows,
        benchmark_summary_rows,
        benchmark_daily_rows,
        sanity_rows,
        contributor_rows,
        period_rows,
        p1_signal_rows,
        p3_signal_rows,
        p4_signal_rows,
    )
    chart_paths = build_charts(
        bundles,
        summary_rows,
        benchmark_summary_rows,
        benchmark_daily_rows,
        p1_signal_rows,
        p3_signal_rows,
        p4_signal_rows,
    )
    build_report(
        bundles,
        summary_rows,
        benchmark_summary_rows,
        sanity_rows,
        contributor_rows,
        p1_signal_rows,
        p3_signal_rows,
        p4_signal_rows,
        chart_paths,
    )
    print(f"Wrote analysis tables to {ANALYSIS_DATA_DIR}")
    print(f"Wrote charts to {CHARTS_DIR}")
    print(f"Wrote reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
