"""Display helpers for the Streamlit UI (no Streamlit import, so they are testable)."""
from __future__ import annotations

from decimal import Decimal

from app.tables import is_unbounded

LIMIT_TABLES = {"tblTaxRate", "tblTaxRateLTCG"}
LIMIT_COLUMNS = ("Single", "Jointly")


def format_limit(value: Decimal) -> str:
    return "No limit" if is_unbounded(value) else f"{value:,.0f}"


def display_records(table_name: str, rows) -> list[dict]:
    """Convert validated rows to plain records for st.dataframe.

    Decimals become floats; bracket ceilings that are sentinels show as 'No limit'.
    """
    records = []
    for row in rows:
        rec = {}
        for key, val in row.model_dump().items():
            if table_name in LIMIT_TABLES and key in LIMIT_COLUMNS:
                rec[key] = format_limit(val)
            elif isinstance(val, Decimal):
                rec[key] = float(val)
            else:
                rec[key] = val
        records.append(rec)
    return records
