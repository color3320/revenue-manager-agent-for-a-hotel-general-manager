"""Optional read-only SQL escape hatch."""

from __future__ import annotations

from langchain_core.tools import tool

from agent.db import ReadOnlySQLError, get_connection, run_readonly_query
from agent.semantic import get_as_of_date, make_envelope


@tool
def run_sql(query: str) -> dict:
    """Execute a read-only SELECT/WITH query. Prefer purpose-built tools when possible."""
    try:
        with get_connection() as conn:
            as_of = get_as_of_date(conn)
            rows = run_readonly_query(conn, query, {"as_of_date": as_of})
    except ReadOnlySQLError as exc:
        return make_envelope(
            headline=f"Query rejected: {exc}",
            key_numbers={"rows": []},
            filters_and_definitions={"query": query},
            caveats=["Only single SELECT or WITH statements are allowed."],
        )
    except Exception as exc:
        return make_envelope(
            headline=f"Query failed: {exc}",
            key_numbers={"rows": []},
            filters_and_definitions={"query": query},
            caveats=["Check SQL syntax and table/column names."],
        )

    serializable = []
    for row in rows[:100]:
        serializable.append({k: (str(v) if v is not None else None) for k, v in row.items()})

    return make_envelope(
        headline=f"Query returned {len(rows)} row(s)" + (" (truncated to 100)" if len(rows) > 100 else ""),
        key_numbers={
            "row_count": len(rows),
            "rows": serializable,
        },
        filters_and_definitions={
            "as_of_date": as_of,
            "query": query,
        },
        caveats=[
            "Secondary escape hatch — prefer purpose-built tools for business metrics.",
            "Results truncated to 100 rows in envelope.",
        ],
    )
