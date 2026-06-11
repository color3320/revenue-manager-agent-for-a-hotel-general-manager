"""Business rules and metric helpers — single source of truth for agent tools."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Literal

import psycopg

from agent.db import fetch_all, fetch_scalar
from etl.metric_windows import (
    CURRENT_LOOKBACK_DAYS,
    SQL_ADR_BY_ROOM_TYPE,
    SQL_CANCELLED_RESERVATIONS,
    SQL_CURRENT_RESERVATIONS,
    SQL_DATASET_AS_OF,
    SQL_LAST_YEAR_RESERVATIONS,
    SQL_OTB_NIGHTS_BY_MARKET,
    SQL_OTB_ROOM_NIGHTS,
    SQL_OTB_ROOM_REVENUE,
    SQL_OTB_TOTAL_REVENUE,
    SQL_STLY_ROOM_NIGHTS,
    SQL_STLY_TOTAL_REVENUE,
    SQL_TOTAL_RESERVATIONS,
    SQL_TOTAL_STAY_ROWS,
    STATUS_CANCELLED,
    STATUS_RESERVED,
    adr_reservation_predicate,
    current_reservation_predicate,
    last_year_reservation_predicate,
    otb_stay_predicate,
    parse_as_of,
    stly_stay_predicate,
)

FACT_TABLE = "reservations_hackathon"

# Segment taxonomy
CORPORATE_MACRO_GROUP = "Corporate"
OTA_MARKET_CODE = "OTA"


class DatePurpose(str, Enum):
    STAY = "stay_date"
    PACE = "create_datetime"
    CANCELLATION = "cancellation_datetime"
    ARRIVAL = "arrival_date"


class RevenueMeasure(str, Enum):
    ROOM = "daily_room_revenue_before_tax"
    TOTAL = "daily_total_revenue_before_tax"


def date_column(purpose: DatePurpose) -> str:
    return purpose.value


def revenue_column(measure: RevenueMeasure) -> str:
    return measure.value


def exclude_cancelled_clause() -> str:
    return f"reservation_status = '{STATUS_RESERVED}'"


def cancelled_only_clause() -> str:
    return f"reservation_status = '{STATUS_CANCELLED}'"


def build_stay_filter(
    window: Literal["otb", "stly", "all"],
    as_of_param: str = "%(as_of_date)s",
) -> str:
    if window == "otb":
        return otb_stay_predicate(as_of_param)
    if window == "stly":
        return stly_stay_predicate(as_of_param)
    return "TRUE"


def otb_window_description() -> str:
    return (
        f"On the books: {STATUS_RESERVED}, stay_date >= as_of_date "
        f"(anchor from dataset_metadata)"
    )


def quantize_money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def make_envelope(
    headline: str,
    key_numbers: dict[str, Any],
    filters_and_definitions: dict[str, Any],
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "headline": headline,
        "key_numbers": key_numbers,
        "filters_and_definitions": filters_and_definitions,
        "caveats": caveats or [],
    }


def get_as_of_date(conn: psycopg.Connection) -> str:
    value = fetch_scalar(conn, SQL_DATASET_AS_OF)
    if value is None:
        raise RuntimeError("dataset_metadata.as_of_date not found")
    return str(value)


def params(as_of_date: str) -> dict[str, str]:
    return {"as_of_date": as_of_date}


# --- Trap helpers: correct counting rules ---

def count_reservations(
    conn: psycopg.Connection,
    where: str = "TRUE",
    as_of_date: str | None = None,
) -> int:
    sql = f"""
    SELECT COUNT(DISTINCT reservation_id)
    FROM {FACT_TABLE}
    WHERE {where}
    """
    p = params(as_of_date) if as_of_date else {}
    return int(fetch_scalar(conn, sql, p) or 0)


def count_stay_rows(
    conn: psycopg.Connection,
    where: str = "TRUE",
    as_of_date: str | None = None,
) -> int:
    sql = f"""
    SELECT COUNT(*)
    FROM {FACT_TABLE}
    WHERE {where}
    """
    p = params(as_of_date) if as_of_date else {}
    return int(fetch_scalar(conn, sql, p) or 0)


def sum_room_nights(
    conn: psycopg.Connection,
    where: str,
    as_of_date: str,
) -> int:
    sql = f"""
    SELECT COALESCE(SUM(number_of_spaces), 0)
    FROM {FACT_TABLE}
    WHERE {where}
    """
    return int(fetch_scalar(conn, sql, params(as_of_date)) or 0)


def sum_revenue(
    conn: psycopg.Connection,
    where: str,
    measure: RevenueMeasure,
    as_of_date: str,
) -> Decimal:
    col = revenue_column(measure)
    sql = f"""
    SELECT COALESCE(SUM({col}), 0)
    FROM {FACT_TABLE}
    WHERE {where}
    """
    return quantize_money(fetch_scalar(conn, sql, params(as_of_date)))


def adr_weighted(room_revenue: Decimal, room_nights: int) -> Decimal | None:
    if room_nights == 0:
        return None
    return quantize_money(room_revenue / Decimal(room_nights))


# --- Verify-aligned metric queries ---

def fetch_verify_scalars(conn: psycopg.Connection, as_of_date: str) -> dict[str, Any]:
    p = params(as_of_date)
    return {
        "total_reservations": int(fetch_scalar(conn, SQL_TOTAL_RESERVATIONS, p) or 0),
        "total_stay_rows": int(fetch_scalar(conn, SQL_TOTAL_STAY_ROWS, p) or 0),
        "current_reservations": int(fetch_scalar(conn, SQL_CURRENT_RESERVATIONS, p) or 0),
        "last_year_reservations": int(fetch_scalar(conn, SQL_LAST_YEAR_RESERVATIONS, p) or 0),
        "cancelled_reservations": int(fetch_scalar(conn, SQL_CANCELLED_RESERVATIONS, p) or 0),
        "otb_room_nights": int(fetch_scalar(conn, SQL_OTB_ROOM_NIGHTS, p) or 0),
        "otb_room_revenue_before_tax": quantize_money(
            fetch_scalar(conn, SQL_OTB_ROOM_REVENUE, p)
        ),
        "otb_total_revenue_before_tax": quantize_money(
            fetch_scalar(conn, SQL_OTB_TOTAL_REVENUE, p)
        ),
        "stly_room_nights": int(fetch_scalar(conn, SQL_STLY_ROOM_NIGHTS, p) or 0),
        "stly_total_revenue_before_tax": quantize_money(
            fetch_scalar(conn, SQL_STLY_TOTAL_REVENUE, p)
        ),
    }


def adr_by_room_type(conn: psycopg.Connection, as_of_date: str) -> dict[str, Decimal]:
    rows = fetch_all(conn, SQL_ADR_BY_ROOM_TYPE, params(as_of_date))
    return {row["space_type"]: quantize_money(row["adr"]) for row in rows}


def otb_nights_by_market(conn: psycopg.Connection, as_of_date: str) -> dict[str, int]:
    rows = fetch_all(conn, SQL_OTB_NIGHTS_BY_MARKET, params(as_of_date))
    return {row["market_code"]: int(row["room_nights"]) for row in rows}


def fetch_room_capacity(conn: psycopg.Connection) -> int:
    sql = "SELECT COALESCE(SUM(number_of_rooms), 0) FROM room_type_lookup"
    return int(fetch_scalar(conn, sql) or 0)


def fetch_lookup_codes(
    conn: psycopg.Connection,
) -> dict[str, list[dict[str, str]]]:
    markets = fetch_all(
        conn,
        """
        SELECT market_code, market_name, macro_group
        FROM market_code_lookup
        ORDER BY market_code
        """,
    )
    channels = fetch_all(
        conn,
        """
        SELECT channel_code, channel_name, channel_group
        FROM channel_code_lookup
        ORDER BY channel_code
        """,
    )
    room_types = fetch_all(
        conn,
        """
        SELECT space_type, display_name, number_of_rooms
        FROM room_type_lookup
        ORDER BY space_type
        """,
    )
    return {
        "market_codes": [
            {
                "code": r["market_code"],
                "name": r["market_name"],
                "macro_group": r["macro_group"],
            }
            for r in markets
        ],
        "channel_codes": [
            {
                "code": r["channel_code"],
                "name": r["channel_name"],
                "group": r["channel_group"],
            }
            for r in channels
        ],
        "room_types": [
            {
                "code": r["space_type"],
                "name": r["display_name"],
                "rooms": r["number_of_rooms"],
            }
            for r in room_types
        ],
    }
