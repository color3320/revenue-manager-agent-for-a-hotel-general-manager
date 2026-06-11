"""Core revenue and segment metrics."""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

from agent.db import fetch_all, get_connection
from agent.semantic import (
    CURRENT_LOOKBACK_DAYS,
    DatePurpose,
    FACT_TABLE,
    RevenueMeasure,
    adr_by_room_type,
    date_column,
    fetch_lookup_codes,
    fetch_room_capacity,
    fetch_verify_scalars,
    get_as_of_date,
    make_envelope,
    otb_window_description,
    otb_stay_predicate,
    params,
    quantize_money,
    revenue_column,
    sum_revenue,
    sum_room_nights,
)


def _month_filter(month: str | None) -> tuple[str, dict]:
    if not month:
        return "", {}
    return " AND TO_CHAR(stay_date, 'YYYY-MM') = %(month)s", {"month": month}


@tool
def describe_dataset() -> dict:
    """Report dataset context: as-of date, room capacity, lookup codes, and OTB window definition."""
    with get_connection() as conn:
        as_of = get_as_of_date(conn)
        lookups = fetch_lookup_codes(conn)
        capacity = fetch_room_capacity(conn)
        scalars = fetch_verify_scalars(conn, as_of)

    return make_envelope(
        headline=f"Dataset as of {as_of}: {scalars['total_reservations']} reservations, "
        f"{capacity} physical rooms across {len(lookups['room_types'])} room types.",
        key_numbers={
            "as_of_date": as_of,
            "room_capacity": capacity,
            "total_reservations": scalars["total_reservations"],
            "total_stay_rows": scalars["total_stay_rows"],
            "current_reservations": scalars["current_reservations"],
            "last_year_reservations": scalars["last_year_reservations"],
            "market_codes": lookups["market_codes"],
            "channel_codes": lookups["channel_codes"],
            "room_types": lookups["room_types"],
        },
        filters_and_definitions={
            "as_of_date": as_of,
            "otb_window": otb_window_description(),
            "current_reservation_window": (
                f"arrival_date >= as_of_date - {CURRENT_LOOKBACK_DAYS} days"
            ),
            "last_year_reservation_window": (
                f"arrival_date < as_of_date - {CURRENT_LOOKBACK_DAYS} days"
            ),
            "cancelled_excluded": "By default for OTB/STLY/ADR; use cancellations tool for cancelled business",
        },
        caveats=[
            "Current vs last-year reservation split uses arrival_date with 180-day lookback.",
        ],
    )


@tool
def revenue_on_books(
    group_by: Literal["none", "month"] = "none",
    month: str | None = None,
    revenue_measure: Literal["total", "room"] = "total",
) -> dict:
    """On-the-books room nights and revenue for future stays (Reserved, stay_date >= as_of)."""
    measure = RevenueMeasure.TOTAL if revenue_measure == "total" else RevenueMeasure.ROOM
    with get_connection() as conn:
        as_of = get_as_of_date(conn)
        p = params(as_of)
        where = otb_stay_predicate()
        month_clause, month_params = _month_filter(month)
        full_where = where + month_clause
        p = {**p, **month_params}

        room_nights = sum_room_nights(conn, full_where, as_of)
        revenue = sum_revenue(conn, full_where, measure, as_of)

        breakdown = []
        if group_by == "month":
            col = date_column(DatePurpose.STAY)
            rev_col = revenue_column(measure)
            sql = f"""
            SELECT TO_CHAR({col}, 'YYYY-MM') AS period,
                   COALESCE(SUM(number_of_spaces), 0) AS room_nights,
                   COALESCE(SUM({rev_col}), 0) AS revenue
            FROM {FACT_TABLE}
            WHERE {full_where}
            GROUP BY TO_CHAR({col}, 'YYYY-MM')
            ORDER BY period
            """
            rows = fetch_all(conn, sql, p)
            breakdown = [
                {
                    "month": r["period"],
                    "room_nights": int(r["room_nights"]),
                    "revenue": float(quantize_money(r["revenue"])),
                }
                for r in rows
            ]

    rev_label = "total revenue" if measure == RevenueMeasure.TOTAL else "room revenue"
    headline = (
        f"OTB: {room_nights:,} room nights, "
        f"${revenue:,.2f} {rev_label} (as of {as_of})"
    )
    if month:
        headline += f" for {month}"

    key_numbers: dict = {
        "room_nights": room_nights,
        "revenue": float(revenue),
        "revenue_measure": measure.value,
    }
    if breakdown:
        key_numbers["by_month"] = breakdown

    return make_envelope(
        headline=headline,
        key_numbers=key_numbers,
        filters_and_definitions={
            "as_of_date": as_of,
            "window": "otb",
            "date_field": date_column(DatePurpose.STAY),
            "revenue_field": revenue_column(measure),
            "cancelled_excluded": True,
            "status_filter": "Reserved",
            "month_filter": month,
            "group_by": group_by,
        },
        caveats=[
            "OTB uses stay_date, not arrival_date or create_datetime.",
            "Total revenue includes package effects; use revenue_measure='room' for room-only.",
        ],
    )


@tool
def segment_mix(
    dimension: Literal["market_code", "macro_group", "channel_code"] = "market_code",
    month: str | None = None,
    filter_corporate: bool = False,
    revenue_measure: Literal["total", "room"] = "total",
) -> dict:
    """OTB segment breakdown with room nights, revenue, and share percentages."""
    measure = RevenueMeasure.TOTAL if revenue_measure == "total" else RevenueMeasure.ROOM
    with get_connection() as conn:
        as_of = get_as_of_date(conn)
        p = params(as_of)
        where = otb_stay_predicate()
        month_clause, month_params = _month_filter(month)
        full_where = where + month_clause
        p = {**p, **month_params}

        if dimension == "macro_group":
            dim_expr = "m.macro_group"
            join = f"""
            JOIN market_code_lookup m ON {FACT_TABLE}.market_code = m.market_code
            """
            if filter_corporate:
                full_where += " AND m.macro_group = 'Corporate'"
        elif dimension == "channel_code":
            dim_expr = f"{FACT_TABLE}.channel_code"
            join = ""
        else:
            dim_expr = f"{FACT_TABLE}.market_code"
            join = ""
            if filter_corporate:
                join = f"""
                JOIN market_code_lookup m ON {FACT_TABLE}.market_code = m.market_code
                """
                full_where += " AND m.macro_group = 'Corporate'"

        rev_col = revenue_column(measure)
        sql = f"""
        SELECT {dim_expr} AS segment,
               COALESCE(SUM(number_of_spaces), 0) AS room_nights,
               COALESCE(SUM({rev_col}), 0) AS revenue
        FROM {FACT_TABLE}
        {join}
        WHERE {full_where}
        GROUP BY {dim_expr}
        ORDER BY revenue DESC
        """
        rows = fetch_all(conn, sql, p)
        total_nights = sum(int(r["room_nights"]) for r in rows)
        total_rev = sum(quantize_money(r["revenue"]) for r in rows)

        segments = []
        for r in rows:
            nights = int(r["room_nights"])
            rev = quantize_money(r["revenue"])
            share_nights = round(nights / total_nights * 100, 2) if total_nights else 0.0
            share_rev = (
                round(float(rev / total_rev * 100), 2) if total_rev > 0 else 0.0
            )
            segments.append({
                "segment": r["segment"],
                "room_nights": nights,
                "revenue": float(rev),
                "share_pct_nights": share_nights,
                "share_pct_revenue": share_rev,
                "share_pct": share_rev,
            })

    dim_label = dimension.replace("_", " ")
    headline = f"OTB segment mix by {dim_label}: {len(segments)} segments, {total_nights:,} room nights"
    if month:
        headline += f" in {month}"
    if filter_corporate:
        headline += " (corporate only)"

    return make_envelope(
        headline=headline,
        key_numbers={
            "total_room_nights": total_nights,
            "total_revenue": float(total_rev),
            "segments": segments,
        },
        filters_and_definitions={
            "as_of_date": as_of,
            "window": "otb",
            "date_field": date_column(DatePurpose.STAY),
            "revenue_field": revenue_column(measure),
            "cancelled_excluded": True,
            "dimension": dimension,
            "month_filter": month,
            "filter_corporate": filter_corporate,
        },
        caveats=[
            "share_pct reflects revenue share; share_pct_nights reflects room-night share.",
            "Corporate = macro_group 'Corporate' (CSR, CNR).",
        ],
    )


@tool
def adr_analysis() -> dict:
    """ADR by room type for current Reserved reservations (arrival within 180-day window)."""
    with get_connection() as conn:
        as_of = get_as_of_date(conn)
        adr_map = adr_by_room_type(conn, as_of)

    if not adr_map:
        highest = None
    else:
        highest = max(adr_map, key=lambda k: adr_map[k])

    by_type = {k: float(v) for k, v in sorted(adr_map.items())}

    return make_envelope(
        headline=(
            f"Highest ADR room type: {highest} at ${adr_map[highest]:,.2f}"
            if highest
            else "No ADR data"
        ),
        key_numbers={
            "adr_by_room_type": by_type,
            "highest_adr_type": highest,
            "highest_adr": float(adr_map[highest]) if highest else None,
        },
        filters_and_definitions={
            "as_of_date": as_of,
            "window": "current",
            "date_field": date_column(DatePurpose.ARRIVAL),
            "cancelled_excluded": True,
            "lookback_days": CURRENT_LOOKBACK_DAYS,
            "formula": "AVG(adr_room) at reservation grain (one row per reservation_id)",
        },
        caveats=[
            "Verify ADR uses reservation-level AVG(adr_room), not stay-weighted revenue/nights.",
        ],
    )
