from __future__ import annotations

import csv
import html
import json
import math
import statistics
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NBIM_ROOT = ROOT / "data" / "processed" / "nbim"
BACKTEST_ROOT = NBIM_ROOT / "backtests"
ANALYSIS_DIR = BACKTEST_ROOT / "analysis"
CHARTS_DIR = ROOT / "outputs" / "nbim" / "backtests" / "charts"
REPORTS_DIR = ROOT / "outputs" / "nbim" / "backtests" / "reports"

PRICE_PATH = NBIM_ROOT / "nbim_twelvedata_daily_prices.csv"

STRATEGIES = [
    {"key": "n1", "name": "N1 Core US Mirror Equal Weight", "dir": BACKTEST_ROOT / "n1_core_equal_weight", "prefix": "n1cew", "color": "#0B5FFF"},
    {"key": "n2", "name": "N2 Core US Mirror NBIM Weight", "dir": BACKTEST_ROOT / "n2_core_nbim_weight", "prefix": "n2cnw", "color": "#15803D"},
    {"key": "n3", "name": "N3 Industry Weight Mirror", "dir": BACKTEST_ROOT / "n3_industry_weight_mirror", "prefix": "n3iwm", "color": "#C2410C"},
    {"key": "n4", "name": "N4 Industry Weight-Change Tilt", "dir": BACKTEST_ROOT / "n4_industry_weight_change_tilt", "prefix": "n4iwc", "color": "#7C3AED"},
    {"key": "n5", "name": "N5 Industry Accumulation Tilt", "dir": BACKTEST_ROOT / "n5_industry_accumulation_tilt", "prefix": "n5iat", "color": "#BE185D"},
    {"key": "n6", "name": "N6 Top-3 Industry Leaders", "dir": BACKTEST_ROOT / "n6_top3_industry_leaders", "prefix": "n6t3l", "color": "#0F766E"},
    {"key": "n7", "name": "N7 Top-3 Industry Increases", "dir": BACKTEST_ROOT / "n7_top3_industry_increases", "prefix": "n7t3i", "color": "#D97706"},
    {"key": "n8", "name": "N8 Consensus Rotation Tilt", "dir": BACKTEST_ROOT / "n8_consensus_rotation_tilt", "prefix": "n8crt", "color": "#334155"},
]

COLORS = {
    "grid": "#E2E8F0",
    "text": "#0F172A",
    "slate": "#475569",
    "gray": "#94A3B8",
    "benchmark": "#111827",
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


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_nav(value: float) -> str:
    return f"{value:.2f}x"


def escape(text: str) -> str:
    return html.escape(text)


def compact_date_label(value: str) -> str:
    return value[2:7] if len(value) >= 7 else value


def svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


def wrap_svg(content: str, width: int, height: int) -> str:
    return f"{svg_header(width, height)}{content}</svg>"


def multi_line_chart_svg(labels: list[str], series: list[tuple[str, str, list[float]]], title: str, subtitle: str, yfmt) -> str:
    width, height = 980, 440
    left, right, top, bottom = 72, 20, 64, 84
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [v for _, _, arr in series for v in arr]
    min_v = min(values) if values else 0.0
    max_v = max(values) if values else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    grid = []
    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        grid.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["slate"]}">{escape(yfmt(value))}</text>')

    content = [
        '<rect width="980" height="440" fill="white"/>',
        f'<text x="{left}" y="30" font-size="22" font-weight="700" fill="{COLORS["text"]}">{escape(title)}</text>',
        f'<text x="{left}" y="50" font-size="12" fill="{COLORS["slate"]}">{escape(subtitle)}</text>',
        "".join(grid),
    ]

    count = max((len(arr) for _, _, arr in series), default=0)
    for name, color, arr in series:
        pts = []
        for i, value in enumerate(arr):
            x = left + (plot_w * i / max(1, count - 1))
            y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            pts.append((x, y))
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        content.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{poly}" />')
        content.extend(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{color}" />' for x, y in pts)

    for i, label in enumerate(labels):
        x = left + (plot_w * i / max(1, len(labels) - 1))
        content.append(f'<text x="{x:.1f}" y="{height-34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(label)}</text>')

    legend_x = left
    for name, color, _ in series:
        content.append(f'<rect x="{legend_x}" y="{height-24}" width="12" height="12" fill="{color}" rx="2"/>')
        content.append(f'<text x="{legend_x+18}" y="{height-14}" font-size="11" fill="{COLORS["slate"]}">{escape(name)}</text>')
        legend_x += 180

    return wrap_svg("".join(content), width, height)


def bar_chart_svg(labels: list[str], values: list[float], title: str, subtitle: str, color: str, yfmt) -> str:
    width, height = 900, 420
    left, right, top, bottom = 72, 20, 64, 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_v = max(values) if values else 1.0
    min_v = min(0.0, min(values) if values else 0.0)
    if max_v == min_v:
        max_v = min_v + 1.0

    content = [
        '<rect width="900" height="420" fill="white"/>',
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
    bar_w = plot_w / max(1, len(values)) * 0.65
    for i, value in enumerate(values):
        center = left + plot_w * (i + 0.5) / max(1, len(values))
        y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
        rect_y = min(y, zero_y)
        rect_h = abs(zero_y - y)
        fill = color if value >= 0 else "#DC2626"
        content.append(f'<rect x="{center-bar_w/2:.1f}" y="{rect_y:.1f}" width="{bar_w:.1f}" height="{rect_h:.1f}" fill="{fill}" rx="3"/>')
        content.append(f'<text x="{center:.1f}" y="{height-34}" text-anchor="middle" font-size="10.5" fill="{COLORS["slate"]}">{escape(labels[i])}</text>')
    return wrap_svg("".join(content), width, height)


def load_strategy_data() -> list[dict[str, object]]:
    loaded = []
    for strategy in STRATEGIES:
        portfolio_path = strategy["dir"] / f"{strategy['prefix']}_portfolio_timeline.csv"
        holdings_path = strategy["dir"] / f"{strategy['prefix']}_holdings_timeline.csv"
        if not portfolio_path.exists():
            portfolio_path = strategy["dir"] / f"{strategy['prefix']}_portfolio_monthly.csv"
        if not holdings_path.exists():
            holdings_path = strategy["dir"] / f"{strategy['prefix']}_holdings_monthly.csv"
        portfolio_rows = read_csv(portfolio_path)
        holdings_rows = read_csv(holdings_path)
        rebalance_rows = read_csv(strategy["dir"] / f"{strategy['prefix']}_rebalance_events.csv")
        summary = json.loads((strategy["dir"] / f"{strategy['prefix']}_summary.json").read_text(encoding="utf-8"))
        loaded.append({**strategy, "portfolio_rows": portfolio_rows, "holdings_rows": holdings_rows, "rebalance_rows": rebalance_rows, "summary": summary})
    return loaded


def build_benchmark_lookup() -> dict[str, float]:
    rows = [row for row in read_csv(PRICE_PATH) if row["instrument_key"] == "benchmark_vt"]
    return {row["date"]: to_float(row["close"]) for row in rows}


def parse_date(value: str) -> date:
    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


def compute_strategy_summary(loaded: list[dict[str, object]]) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    benchmark_lookup = build_benchmark_lookup()
    common_start = max(item["portfolio_rows"][0]["date"] for item in loaded)
    common_dates = [row["date"] for row in loaded[0]["portfolio_rows"] if row["date"] >= common_start]

    strategy_rows: list[dict[str, str]] = []
    relative_rows: list[dict[str, str]] = []
    timeline_rows: list[dict[str, str]] = []

    benchmark_start = benchmark_lookup[common_dates[0]]
    benchmark_series = {date: benchmark_lookup[date] / benchmark_start for date in common_dates}

    for item in loaded:
        portfolio_rows = [row for row in item["portfolio_rows"] if row["date"] >= common_start]
        nav_series = [to_float(row["nav_end"]) for row in portfolio_rows]
        rebased_nav_series = [value / nav_series[0] for value in nav_series]
        returns = [rebased_nav_series[i] / rebased_nav_series[i - 1] - 1.0 for i in range(1, len(rebased_nav_series))]
        interval_days = [
            max(1, (parse_date(portfolio_rows[i]["date"]) - parse_date(portfolio_rows[i - 1]["date"])).days)
            for i in range(1, len(portfolio_rows))
        ]
        vol = statistics.pstdev(returns) if len(returns) > 1 else 0.0
        elapsed_days = max(1, (parse_date(portfolio_rows[-1]["date"]) - parse_date(portfolio_rows[0]["date"])).days)
        elapsed_years = elapsed_days / 365.25
        ann_return = nav_series[-1] ** (1 / elapsed_years) - 1.0 if elapsed_years > 0 else 0.0
        avg_interval_days = statistics.fmean(interval_days) if interval_days else 30.4375
        ann_vol = vol * math.sqrt(365.25 / avg_interval_days)
        avg_cash = statistics.fmean(to_float(row["cash_end"]) / to_float(row["nav_end"]) for row in portfolio_rows if to_float(row["nav_end"]) > 0)
        avg_holdings = statistics.fmean(int(row["holding_count"]) for row in portfolio_rows)
        turnover = statistics.fmean(to_float(row["turnover_notional"]) for row in item["rebalance_rows"]) if item["rebalance_rows"] else 0.0
        benchmark_end = benchmark_series[common_dates[-1]]
        rebased_end = rebased_nav_series[-1]
        excess_total = rebased_end / benchmark_end - 1.0

        strategy_rows.append(
            {
                "strategy_key": item["key"],
                "strategy_name": item["name"],
                "start_date": item["portfolio_rows"][0]["date"],
                "end_date": item["portfolio_rows"][-1]["date"],
                "final_nav": f"{to_float(item['summary']['final_nav']):.12f}",
                "total_return": f"{to_float(item['summary']['total_return']):.12f}",
                "annualized_return": f"{ann_return:.12f}",
                "annualized_volatility": f"{ann_vol:.12f}",
                "max_drawdown": f"{to_float(item['summary']['max_drawdown']):.12f}",
                "average_cash_weight": f"{avg_cash:.12f}",
                "average_holding_count": f"{avg_holdings:.12f}",
                "average_rebalance_turnover": f"{turnover:.12f}",
                "rebalance_count": str(item["summary"]["rebalance_count"]),
            }
        )
        relative_rows.append(
            {
                "strategy_key": item["key"],
                "strategy_name": item["name"],
                "comparison_start_date": common_dates[0],
                "comparison_end_date": common_dates[-1],
                "strategy_total_return": f"{rebased_end - 1.0:.12f}",
                "benchmark_total_return": f"{benchmark_end - 1.0:.12f}",
                "excess_total_return": f"{excess_total:.12f}",
            }
        )

        for idx, (row, rebased_nav) in enumerate(zip(portfolio_rows, rebased_nav_series)):
            date = row["date"]
            benchmark_nav = benchmark_series[date]
            timeline_rows.append(
                {
                    "date": date,
                    "strategy_key": item["key"],
                    "strategy_name": item["name"],
                    "strategy_nav": f"{to_float(row['nav_end']):.12f}",
                    "strategy_nav_rebased": f"{rebased_nav:.12f}",
                    "benchmark_nav": f"{benchmark_nav:.12f}",
                    "relative_nav": f"{(rebased_nav / benchmark_nav if benchmark_nav > 0 else 0.0):.12f}",
                    "strategy_return": f"{(returns[idx - 1] if idx > 0 else 0.0):.12f}",
                }
            )

    write_csv(ANALYSIS_DIR / "strategy_summary.csv", strategy_rows)
    write_csv(ANALYSIS_DIR / "strategy_vs_benchmark_summary.csv", relative_rows)
    write_csv(ANALYSIS_DIR / "strategy_vs_benchmark_timeline.csv", timeline_rows)
    write_csv(ANALYSIS_DIR / "strategy_vs_benchmark_monthly.csv", timeline_rows)
    return strategy_rows, relative_rows, common_start


def build_concentration_rows(loaded: list[dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in loaded:
        by_date: dict[str, list[dict[str, str]]] = {}
        for row in item["holdings_rows"]:
            by_date.setdefault(row["date"], []).append(row)
        for date, holdings in by_date.items():
            weights = [to_float(row["portfolio_weight"]) for row in holdings]
            if not weights:
                continue
            weights.sort(reverse=True)
            rows.append(
                {
                    "date": date,
                    "strategy_key": item["key"],
                    "strategy_name": item["name"],
                    "top_position_weight": f"{weights[0]:.12f}",
                    "top_5_weight": f"{sum(weights[:5]):.12f}",
                    "hhi": f"{sum(weight * weight for weight in weights):.12f}",
                }
            )
    write_csv(ANALYSIS_DIR / "strategy_concentration_timeline.csv", rows)
    write_csv(ANALYSIS_DIR / "strategy_concentration_monthly.csv", rows)
    return rows


def build_sanity_rows(loaded: list[dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in loaded:
        holdings_by_date: dict[str, float] = {}
        for row in item["holdings_rows"]:
            holdings_by_date.setdefault(row["date"], 0.0)
            holdings_by_date[row["date"]] += to_float(row["portfolio_weight"])
        max_weight_gap = 0.0
        for portfolio_row in item["portfolio_rows"]:
            date = portfolio_row["date"]
            holdings_weight = holdings_by_date.get(date, 0.0)
            cash_weight = to_float(portfolio_row["cash_end"]) / to_float(portfolio_row["nav_end"]) if to_float(portfolio_row["nav_end"]) > 0 else 0.0
            max_weight_gap = max(max_weight_gap, abs((holdings_weight + cash_weight) - 1.0))
        rows.append(
            {
                "strategy_key": item["key"],
                "strategy_name": item["name"],
                "start_nav": f"{to_float(item['portfolio_rows'][0]['nav_start']):.12f}",
                "end_nav": f"{to_float(item['portfolio_rows'][-1]['nav_end']):.12f}",
                "negative_cash_breach_count": str(sum(1 for row in item["portfolio_rows"] if to_float(row["cash_end"]) < -1e-6)),
                "max_gross_exposure": f"{max(to_float(row['gross_exposure_end']) for row in item['portfolio_rows']):.12f}",
                "max_weight_integrity_gap": f"{max_weight_gap:.12f}",
            }
        )
    write_csv(ANALYSIS_DIR / "strategy_sanity_checks.csv", rows)
    return rows


def build_charts(loaded: list[dict[str, object]], common_start: str, concentration_rows: list[dict[str, str]]) -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    benchmark_lookup = build_benchmark_lookup()

    common_dates = [row["date"] for row in loaded[0]["portfolio_rows"] if row["date"] >= common_start]
    benchmark_start = benchmark_lookup[common_dates[0]]
    benchmark_nav = [benchmark_lookup[date] / benchmark_start for date in common_dates]
    labels = [compact_date_label(date) if i % 2 == 0 or i == len(common_dates) - 1 else "" for i, date in enumerate(common_dates)]

    nav_series = []
    for item in loaded:
        rows = [row for row in item["portfolio_rows"] if row["date"] >= common_start]
        base = to_float(rows[0]["nav_end"])
        nav_series.append((item["name"], item["color"], [to_float(row["nav_end"]) / base for row in rows]))
    nav_series.append(("VT Benchmark", COLORS["benchmark"], benchmark_nav))
    write_text(CHARTS_DIR / "strategy_nav.svg", multi_line_chart_svg(labels, nav_series, "NBIM Strategy NAV", "Common comparison window aligned to the latest strategy inception.", fmt_nav))

    drawdown_series = [(item["name"], item["color"], [to_float(row["drawdown"]) for row in item["portfolio_rows"] if row["date"] >= common_start]) for item in loaded]
    write_text(CHARTS_DIR / "strategy_drawdown.svg", multi_line_chart_svg(labels, drawdown_series, "NBIM Strategy Drawdowns", "Drawdown paths for each NBIM strategy over the matched comparison window.", fmt_pct))

    relative_series = []
    for item in loaded:
        rows = [row for row in item["portfolio_rows"] if row["date"] >= common_start]
        base = to_float(rows[0]["nav_end"])
        relative_series.append((item["name"], item["color"], [(to_float(row["nav_end"]) / base) / benchmark_nav[i] for i, row in enumerate(rows)]))
    write_text(CHARTS_DIR / "strategy_relative_to_vt.svg", multi_line_chart_svg(labels, relative_series, "NBIM Relative Performance vs VT", "Values above 1.0 indicate outperformance versus the global benchmark.", fmt_nav))

    total_returns = [to_float(item["summary"]["total_return"]) for item in loaded]
    write_text(CHARTS_DIR / "strategy_total_return.svg", bar_chart_svg([item["key"].upper() for item in loaded], total_returns, "Total Return by Strategy", "Full-sample standalone total return for each NBIM strategy.", "#2563EB", fmt_pct))

    excess_returns = []
    for item in loaded:
        rows = [row for row in item["portfolio_rows"] if row["date"] >= common_start]
        excess_returns.append(to_float(rows[-1]["nav_end"]) / benchmark_nav[-1] - 1.0)
    write_text(CHARTS_DIR / "strategy_excess_return.svg", bar_chart_svg([item["key"].upper() for item in loaded], excess_returns, "Excess Return vs VT", "Benchmark-relative total return over the common comparison window.", "#7C3AED", fmt_pct))

    avg_cash = [statistics.fmean(to_float(row["cash_end"]) / to_float(row["nav_end"]) for row in item["portfolio_rows"] if to_float(row["nav_end"]) > 0) for item in loaded]
    write_text(CHARTS_DIR / "strategy_cash_weight.svg", bar_chart_svg([item["key"].upper() for item in loaded], avg_cash, "Average Cash Weight", "Cash usage distinguishes fully invested sleeves from conditional industry-tilt strategies.", "#059669", fmt_pct))

    avg_turnover = [statistics.fmean(to_float(row["turnover_notional"]) for row in item["rebalance_rows"]) if item["rebalance_rows"] else 0.0 for item in loaded]
    write_text(CHARTS_DIR / "strategy_turnover.svg", bar_chart_svg([item["key"].upper() for item in loaded], avg_turnover, "Average Rebalance Turnover", "Average turnover notional per rebalance, scaled to portfolio NAV.", "#D97706", lambda value: f"{value:.2f}x"))

    top5_series = []
    for item in loaded:
        by_date = [row for row in concentration_rows if row["strategy_key"] == item["key"] and row["date"] >= common_start]
        top5_series.append((item["name"], item["color"], [to_float(row["top_5_weight"]) for row in by_date]))
    write_text(CHARTS_DIR / "strategy_concentration.svg", multi_line_chart_svg(labels, top5_series, "NBIM Concentration", "Top-5 portfolio weight over time by strategy.", fmt_pct))


def build_reports(strategy_rows: list[dict[str, str]], relative_rows: list[dict[str, str]], common_start: str) -> None:
    best = max(relative_rows, key=lambda row: to_float(row["excess_total_return"]))
    worst = min(relative_rows, key=lambda row: to_float(row["excess_total_return"]))

    md_lines = [
        "# NBIM Backtest Analysis",
        "",
        f"Common benchmark comparison window starts on `{common_start}` so every strategy is compared over the same live period.",
        "",
        "## Key takeaways",
        "",
        f"- Best benchmark-relative strategy: `{best['strategy_name']}` with excess total return `{fmt_pct(to_float(best['excess_total_return']))}` vs `VT`.",
        f"- Worst benchmark-relative strategy: `{worst['strategy_name']}` with excess total return `{fmt_pct(to_float(worst['excess_total_return']))}` vs `VT`.",
        "- Direct mirror strategies test whether the disclosed core US sleeve can be copied with lag.",
        "- Industry strategies test whether NBIM's slow-moving sector posture contains more persistent signal than single-name mirroring.",
        "",
        "## Strategy summary",
        "",
        "| Strategy | Total Return | Annualized Return | Max Drawdown | Avg Cash | Avg Holdings |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in strategy_rows:
        md_lines.append(
            f"| {row['strategy_name']} | {fmt_pct(to_float(row['total_return']))} | {fmt_pct(to_float(row['annualized_return']))} | {fmt_pct(to_float(row['max_drawdown']))} | {fmt_pct(to_float(row['average_cash_weight']))} | {float(row['average_holding_count']):.1f} |"
        )

    md_lines.extend(
        [
            "",
            "## Benchmark comparison",
            "",
            "| Strategy | Strategy Return | VT Return | Excess Return |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in relative_rows:
        md_lines.append(
            f"| {row['strategy_name']} | {fmt_pct(to_float(row['strategy_total_return']))} | {fmt_pct(to_float(row['benchmark_total_return']))} | {fmt_pct(to_float(row['excess_total_return']))} |"
        )

    markdown = "\n".join(md_lines) + "\n"
    html_body = "<html><body style='font-family: Arial, sans-serif; max-width: 980px; margin: 32px auto; line-height: 1.5;'>" + "".join(
        f"<p>{escape(line)}</p>" if line and not line.startswith("|") and not line.startswith("#") and not line.startswith("- ") else ""
        for line in []
    ) + "</body></html>"

    # Keep the HTML straightforward by embedding the markdown as preformatted sections.
    html_body = (
        "<html><body style='font-family: Arial, sans-serif; max-width: 980px; margin: 32px auto; line-height: 1.5;'>"
        "<h1>NBIM Backtest Analysis</h1>"
        f"<p>Common benchmark comparison window starts on <code>{escape(common_start)}</code> so every strategy is compared over the same live period.</p>"
        "<h2>Key Takeaways</h2><ul>"
        f"<li>Best benchmark-relative strategy: <strong>{escape(best['strategy_name'])}</strong> with excess total return <strong>{escape(fmt_pct(to_float(best['excess_total_return'])))}</strong> vs VT.</li>"
        f"<li>Worst benchmark-relative strategy: <strong>{escape(worst['strategy_name'])}</strong> with excess total return <strong>{escape(fmt_pct(to_float(worst['excess_total_return'])))}</strong> vs VT.</li>"
        "<li>Direct mirror strategies test whether the disclosed core US sleeve can be copied with lag.</li>"
        "<li>Industry strategies test whether NBIM's slow-moving sector posture contains more persistent signal than single-name mirroring.</li>"
        "</ul>"
        "<h2>Strategy Summary</h2><table border='1' cellpadding='6' cellspacing='0'><tr><th>Strategy</th><th>Total Return</th><th>Annualized Return</th><th>Max Drawdown</th><th>Avg Cash</th><th>Avg Holdings</th></tr>"
        + "".join(
            f"<tr><td>{escape(row['strategy_name'])}</td><td>{escape(fmt_pct(to_float(row['total_return'])))}</td><td>{escape(fmt_pct(to_float(row['annualized_return'])))}</td><td>{escape(fmt_pct(to_float(row['max_drawdown'])))}</td><td>{escape(fmt_pct(to_float(row['average_cash_weight'])))}</td><td>{float(row['average_holding_count']):.1f}</td></tr>"
            for row in strategy_rows
        )
        + "</table><h2>Benchmark Comparison</h2><table border='1' cellpadding='6' cellspacing='0'><tr><th>Strategy</th><th>Strategy Return</th><th>VT Return</th><th>Excess Return</th></tr>"
        + "".join(
            f"<tr><td>{escape(row['strategy_name'])}</td><td>{escape(fmt_pct(to_float(row['strategy_total_return'])))}</td><td>{escape(fmt_pct(to_float(row['benchmark_total_return'])))}</td><td>{escape(fmt_pct(to_float(row['excess_total_return'])))}</td></tr>"
            for row in relative_rows
        )
        + "</table></body></html>"
    )

    write_text(REPORTS_DIR / "nbim_backtest_analysis.md", markdown)
    write_text(REPORTS_DIR / "nbim_backtest_analysis.html", html_body)


def main() -> None:
    loaded = load_strategy_data()
    strategy_rows, relative_rows, common_start = compute_strategy_summary(loaded)
    concentration_rows = build_concentration_rows(loaded)
    build_sanity_rows(loaded)
    build_charts(loaded, common_start, concentration_rows)
    build_reports(strategy_rows, relative_rows, common_start)
    print("Built NBIM analysis tables, charts, and summary reports.")


if __name__ == "__main__":
    main()
