from __future__ import annotations

from collections import defaultdict


def apply_latest_report_period_filter(
    rows: list[dict[str, str]],
    *,
    include_flag_field: str = "include_flag",
    trade_date_field: str = "trade_date",
    report_period_field: str = "report_period",
    same_day_flag_field: str = "same_day_multi_period_flag",
    exclusion_reason_field: str = "exclusion_reason",
    exclusion_reason: str = "same_day_bundle_superseded_by_later_period",
) -> list[dict[str, str]]:
    """For same-day multi-period bundles, keep only the latest report period.

    The sleeve-style PIF strategies should trade once per public bundle, using the
    latest observable holdings state from that publication day rather than the
    union of every delayed period released together.
    """
    latest_period_by_trade_date: dict[str, str] = {}
    periods_by_trade_date: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        if row.get(same_day_flag_field) != "1":
            continue
        trade_date = row[trade_date_field]
        report_period = row[report_period_field]
        periods_by_trade_date[trade_date].add(report_period)
        latest_period_by_trade_date[trade_date] = max(
            latest_period_by_trade_date.get(trade_date, report_period),
            report_period,
        )

    for row in rows:
        if row.get(include_flag_field) != "1":
            continue
        if row.get(same_day_flag_field) != "1":
            continue
        trade_date = row[trade_date_field]
        if len(periods_by_trade_date.get(trade_date, set())) <= 1:
            continue
        if row[report_period_field] != latest_period_by_trade_date[trade_date]:
            row[include_flag_field] = "0"
            row[exclusion_reason_field] = exclusion_reason

    return rows
