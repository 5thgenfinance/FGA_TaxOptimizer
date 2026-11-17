"""Filing-status normalization driven by tblStatusAliases.csv."""
from __future__ import annotations

from app.calc.common import UnknownStatusError
from app.tables import Tables


def normalize_status(raw: str, tables: Tables) -> str:
    """Return 'Single', 'Jointly' or 'Separate' for any known alias."""
    key = str(raw).strip().lower()
    for row in tables.rows("tblStatusAliases"):
        if row.Alias.lower() == key:
            return row.Canonical
    raise UnknownStatusError(f"Unknown filing status: {raw!r}")
