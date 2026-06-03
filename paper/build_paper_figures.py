from __future__ import annotations

import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "paper" / "figures"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def to_float(value: str) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def get_font(size: int):
    for candidate in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


FONT_TITLE = get_font(28)
FONT_SUB = get_font(16)
FONT_AXIS = get_font(14)
FONT_LEGEND = get_font(14)


def create_canvas(width: int = 1200, height: int = 760) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_line_chart(
    path: Path,
    title: str,
    subtitle: str,
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    y_label_fmt,
    width: int = 1200,
    height: int = 760,
) -> None:
    img, draw = create_canvas(width, height)
    left, right, top, bottom = 95, 35, 95, 110
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [value for _, _, vals in series for value in vals]
    min_v = min(values) if values else 0.0
    max_v = max(values) if values else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    draw.text((left, 28), title, font=FONT_TITLE, fill="#111827")
    draw.text((left, 62), subtitle, font=FONT_SUB, fill="#4B5563")

    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        draw.line((left, y, width - right, y), fill="#E5E7EB", width=1)
        draw.text((10, y - 8), y_label_fmt(value), font=FONT_AXIS, fill="#374151")

    count = max((len(vals) for _, _, vals in series), default=0)
    for name, color, vals in series:
        pts = []
        for i, value in enumerate(vals):
            x = left + (plot_w * i / max(1, count - 1))
            y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            draw.line((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]), fill=color, width=4)
        for x, y in pts:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color, outline=color)

    for i, label in enumerate(labels):
        if not label:
            continue
        x = left + (plot_w * i / max(1, len(labels) - 1))
        draw.text((x - 18, height - 72), label, font=FONT_AXIS, fill="#374151")

    legend_x = left
    legend_y = height - 30
    for name, color, _ in series:
        draw.rectangle((legend_x, legend_y - 10, legend_x + 16, legend_y + 6), fill=color)
        draw.text((legend_x + 24, legend_y - 14), name, font=FONT_LEGEND, fill="#374151")
        legend_x += 210

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def draw_bar_chart(
    path: Path,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[float],
    colors: list[str],
    y_label_fmt,
    width: int = 1100,
    height: int = 720,
) -> None:
    img, draw = create_canvas(width, height)
    left, right, top, bottom = 95, 35, 95, 110
    plot_w = width - left - right
    plot_h = height - top - bottom
    min_v = min(0.0, min(values) if values else 0.0)
    max_v = max(values) if values else 1.0
    if max_v == min_v:
        max_v = min_v + 1.0

    draw.text((left, 28), title, font=FONT_TITLE, fill="#111827")
    draw.text((left, 62), subtitle, font=FONT_SUB, fill="#4B5563")

    for j in range(5):
        frac = j / 4
        y = top + plot_h - frac * plot_h
        value = min_v + frac * (max_v - min_v)
        draw.line((left, y, width - right, y), fill="#E5E7EB", width=1)
        draw.text((10, y - 8), y_label_fmt(value), font=FONT_AXIS, fill="#374151")

    zero_y = top + plot_h - ((0 - min_v) / (max_v - min_v) * plot_h)
    bar_gap = 18
    bar_w = (plot_w - bar_gap * (len(values) + 1)) / max(1, len(values))
    x = left + bar_gap
    for label, value, color in zip(labels, values, colors):
        y = top + plot_h - ((value - min_v) / (max_v - min_v) * plot_h)
        rect_y = min(y, zero_y)
        rect_h = abs(zero_y - y)
        fill = color if value >= 0 else "#DC2626"
        draw.rounded_rectangle((x, rect_y, x + bar_w, rect_y + rect_h), radius=4, fill=fill)
        draw.text((x + 2, height - 72), label, font=FONT_AXIS, fill="#374151")
        draw.text((x, rect_y - 20 if value >= 0 else rect_y + rect_h + 4), y_label_fmt(value), font=FONT_AXIS, fill="#374151")
        x += bar_w + bar_gap

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def build_pif_nav_figure() -> None:
    rows = read_csv(ROOT / "data" / "processed" / "pif" / "backtests" / "analysis" / "strategy_vs_benchmark_daily.csv")
    keep = {"p2": ("P2", "#2563EB"), "p5": ("P5", "#BE185D")}
    by_key: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["strategy_key"] in keep:
            by_key.setdefault(row["strategy_key"], []).append(row)
    sample = by_key["p2"]
    labels = [row["date"][2:7] if i % 260 == 0 or i == len(sample) - 1 else "" for i, row in enumerate(sample)]
    series = []
    for key in ["p2", "p5"]:
        name, color = keep[key]
        series.append((name, color, [to_float(row["strategy_nav"]) for row in by_key[key]]))
    series.append(("SPY", "#0F766E", [to_float(row["benchmark_nav"]) for row in sample]))
    draw_line_chart(
        FIG_DIR / "pif_nav_vs_spy.png",
        "PIF Strategies Versus SPY",
        "Rebased portfolio paths using validated split-adjusted backtests.",
        labels,
        series,
        lambda v: f"{v:.1f}x",
    )


def build_pif_excess_figure() -> None:
    rows = read_csv(ROOT / "data" / "processed" / "pif" / "backtests" / "analysis" / "strategy_vs_benchmark_summary.csv")
    labels = [row["strategy_key"].upper() for row in rows]
    values = [to_float(row["excess_total_return"]) for row in rows]
    colors = ["#1D4ED8", "#1D4ED8", "#1D4ED8", "#1D4ED8", "#BE185D"]
    draw_bar_chart(
        FIG_DIR / "pif_excess_return.png",
        "PIF Excess Return Versus SPY",
        "All PIF strategies underperform SPY; P5 is least bad but still negative on an excess basis.",
        labels,
        values,
        colors,
        lambda v: f"{v*100:.0f}%",
    )


def build_nbim_nav_figure() -> None:
    rows = read_csv(ROOT / "data" / "processed" / "nbim" / "backtests" / "analysis" / "strategy_vs_benchmark_monthly.csv")
    keep = {
        "n3": ("N3", "#C2410C"),
        "n4": ("N4", "#7C3AED"),
        "n6": ("N6", "#0F766E"),
        "n8": ("N8", "#334155"),
    }
    by_key: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["strategy_key"] in keep:
            by_key.setdefault(row["strategy_key"], []).append(row)
    sample = by_key["n3"]
    labels = [row["date"][2:7] if i % 6 == 0 or i == len(sample) - 1 else "" for i, row in enumerate(sample)]
    series = []
    for key in ["n3", "n4", "n6", "n8"]:
        name, color = keep[key]
        series.append((name, color, [to_float(row["strategy_nav_rebased"]) for row in by_key[key]]))
    series.append(("VT", "#111827", [to_float(row["benchmark_nav"]) for row in sample]))
    draw_line_chart(
        FIG_DIR / "nbim_realistic_nav_vs_vt.png",
        "NBIM Realistic Strategies Versus VT",
        "Only the sector-based NBIM strategies are shown here; biased exploratory stock mirrors are excluded.",
        labels,
        series,
        lambda v: f"{v:.1f}x",
    )


def build_nbim_excess_figure() -> None:
    rows = read_csv(ROOT / "data" / "processed" / "nbim" / "backtests" / "analysis" / "strategy_vs_benchmark_summary.csv")
    filtered = [row for row in rows if row["strategy_key"] in {"n3", "n4", "n5", "n6", "n7", "n8"}]
    labels = [row["strategy_key"].upper() for row in filtered]
    values = [to_float(row["excess_total_return"]) for row in filtered]
    colors = ["#C2410C", "#7C3AED", "#BE185D", "#0F766E", "#D97706", "#334155"]
    draw_bar_chart(
        FIG_DIR / "nbim_realistic_excess_return.png",
        "NBIM Realistic Excess Return Versus VT",
        "The strongest realistic positive signals come from N4 and N6, not from naive full-book mirroring.",
        labels,
        values,
        colors,
        lambda v: f"{v*100:.0f}%",
    )


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    build_pif_nav_figure()
    build_pif_excess_figure()
    build_nbim_nav_figure()
    build_nbim_excess_figure()
    print(f"Wrote figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
