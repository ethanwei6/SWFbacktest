from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNAL_PANEL_PATH = ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_panel.csv"
AUDIT_PATH = ROOT / "data" / "processed" / "pif" / "pif_backtest_signal_audit.csv"
OUT_PATH = ROOT / "data" / "processed" / "pif" / "pif_trade_calendar.csv"
OUT_AUDIT_PATH = ROOT / "data" / "processed" / "pif" / "pif_trade_calendar_audit.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def parse_date(text: str) -> date:
    year, month, day = text.split("-")
    return date(int(year), int(month), int(day))


def fmt_date(value: date) -> str:
    return value.isoformat()


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    d += timedelta(days=7 * (n - 1))
    return d


def last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def observed_fixed_holiday(year: int, month: int, day: int) -> date:
    actual = date(year, month, day)
    if actual.weekday() == 5:
        return actual - timedelta(days=1)
    if actual.weekday() == 6:
        return actual + timedelta(days=1)
    return actual


def nyse_holidays(year: int) -> set[date]:
    holidays = set()
    holidays.add(observed_fixed_holiday(year, 1, 1))
    holidays.add(nth_weekday(year, 1, 0, 3))  # MLK
    holidays.add(nth_weekday(year, 2, 0, 3))  # Presidents Day
    holidays.add(easter_sunday(year) - timedelta(days=2))  # Good Friday
    holidays.add(last_weekday(year, 5, 0))  # Memorial Day
    if year >= 2022:
        holidays.add(observed_fixed_holiday(year, 6, 19))  # Juneteenth
    holidays.add(observed_fixed_holiday(year, 7, 4))  # Independence Day
    holidays.add(nth_weekday(year, 9, 0, 1))  # Labor Day
    holidays.add(nth_weekday(year, 11, 3, 4))  # Thanksgiving
    holidays.add(observed_fixed_holiday(year, 12, 25))  # Christmas
    if year == 2025:
        holidays.add(date(2025, 1, 9))  # National Day of Mourning for President Jimmy Carter
    return holidays


def is_nyse_trading_day(value: date) -> bool:
    if value.weekday() >= 5:
        return False
    return value not in nyse_holidays(value.year)


def next_nyse_trading_day(signal_date: date) -> date:
    d = signal_date + timedelta(days=1)
    while not is_nyse_trading_day(d):
        d += timedelta(days=1)
    return d


def stale_bucket(max_staleness_days: int) -> str:
    if max_staleness_days <= 60:
        return "normal_staleness"
    if max_staleness_days <= 180:
        return "stale_bundle"
    return "very_stale_bundle"


def build_trade_calendar(audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in audit_rows:
        signal_date = parse_date(row["signal_date"])
        trade_date = next_nyse_trading_day(signal_date)
        max_staleness = int(row["max_staleness_days"])
        out.append(
            {
                "signal_date": row["signal_date"],
                "trade_date": fmt_date(trade_date),
                "days_to_trade": str((trade_date - signal_date).days),
                "report_period_count_published": row["report_period_count_published"],
                "published_report_periods": row["published_report_periods"],
                "same_day_multi_period_flag": row["same_day_multi_period_flag"],
                "staleness_bucket": stale_bucket(max_staleness),
                "min_staleness_days": row["min_staleness_days"],
                "max_staleness_days": row["max_staleness_days"],
                "signal_row_count": row["signal_row_count"],
                "holdings_row_count": row["holdings_row_count"],
                "transition_row_count": row["transition_row_count"],
                "entry_observed_count": row["entry_observed_count"],
                "exit_observed_count": row["exit_observed_count"],
                "likely_accumulation_count": row["likely_accumulation_count"],
                "likely_reduction_count": row["likely_reduction_count"],
            }
        )
    return out


def build_trade_calendar_audit(calendar_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in calendar_rows:
        signal_date = parse_date(row["signal_date"])
        trade_date = parse_date(row["trade_date"])
        out.append(
            {
                "signal_date": row["signal_date"],
                "trade_date": row["trade_date"],
                "signal_weekday": signal_date.strftime("%A"),
                "trade_weekday": trade_date.strftime("%A"),
                "signal_is_trading_day": "1" if is_nyse_trading_day(signal_date) else "0",
                "trade_is_trading_day": "1" if is_nyse_trading_day(trade_date) else "0",
                "days_to_trade": row["days_to_trade"],
                "same_day_multi_period_flag": row["same_day_multi_period_flag"],
                "staleness_bucket": row["staleness_bucket"],
            }
        )
    return out


def validate_calendar_rows(calendar_rows: list[dict[str, str]]) -> None:
    for row in calendar_rows:
        signal_date = parse_date(row["signal_date"])
        trade_date = parse_date(row["trade_date"])
        if not trade_date > signal_date:
            raise ValueError(f"Trade date must be strictly after signal date: {row}")
        if not is_nyse_trading_day(trade_date):
            raise ValueError(f"Trade date is not a NYSE trading day: {row}")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    _ = read_csv(SIGNAL_PANEL_PATH)  # ensure panel exists before building the calendar
    audit_rows = read_csv(AUDIT_PATH)
    calendar_rows = build_trade_calendar(audit_rows)
    validate_calendar_rows(calendar_rows)
    calendar_audit_rows = build_trade_calendar_audit(calendar_rows)
    write_csv(OUT_PATH, calendar_rows)
    write_csv(OUT_AUDIT_PATH, calendar_audit_rows)
    print(f"Wrote {len(calendar_rows)} rows to {OUT_PATH}")
    print(f"Wrote {len(calendar_audit_rows)} rows to {OUT_AUDIT_PATH}")


if __name__ == "__main__":
    main()
