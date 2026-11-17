"""Load and validate the external CSV tables in data/.

Tables are read once, validated, and cached. ``reload_tables()`` clears the
cache so an edited CSV can be picked up without a redeploy.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ValidationError

from app import models as m
from app.config import DATA_DIR

SENTINEL_MIN = Decimal("9999999")  # ceilings >= this mean "no limit"

SPECS: dict[str, type[BaseModel]] = {
    "tblTaxRate": m.TaxRateRow,
    "tblTaxRateLTCG": m.TaxRateLTCGRow,
    "tblUniformRMDFactors": m.UniformRMDFactorRow,
    "tblStandDeductionBase": m.StandDeductionBaseRow,
    "tblAMT": m.AMTRow,
    "tblNIIT": m.NIITRow,
    "tblStatusAliases": m.StatusAliasRow,
    "tblParameters": m.ParameterRow,
    "tblInputMap": m.InputMapRow,
}

KEYS: dict[str, Callable] = {
    "tblTaxRate": lambda r: (r.Year, r.Bucket),
    "tblTaxRateLTCG": lambda r: (r.Year, r.Bucket),
    "tblUniformRMDFactors": lambda r: r.Age,
    "tblStandDeductionBase": lambda r: (r.FilingYear, r.Status),
    "tblAMT": lambda r: (r.Year, r.Status),
    "tblNIIT": lambda r: (r.Year, r.Status),
    "tblStatusAliases": lambda r: r.Alias.lower(),
    "tblParameters": lambda r: (r.Year, r.Key),
    "tblInputMap": lambda r: r.Name,
}


class TableValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def is_unbounded(limit: Decimal) -> bool:
    """True for the workbook's finite 'no limit' sentinel ceilings."""
    return limit >= SENTINEL_MIN


@dataclass(frozen=True)
class Tables:
    data: dict[str, tuple]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def rows(self, name: str) -> tuple:
        return self.data[name]

    def supported_years(self) -> list[int]:
        """Years present in every table a full calculation needs."""
        sets = [
            {r.Year for r in self.data["tblTaxRate"]},
            {r.Year for r in self.data["tblTaxRateLTCG"]},
            {r.FilingYear for r in self.data["tblStandDeductionBase"]},
            {r.Year for r in self.data["tblAMT"]},
            {r.Year for r in self.data["tblNIIT"]},
            {r.Year for r in self.data["tblParameters"]},
        ]
        return sorted(set.intersection(*sets))


def _read_rows(path: Path, model: type[BaseModel], errors: list[str]) -> list:
    if not path.exists():
        errors.append(f"{path.name}: file not found")
        return []
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        expected = list(model.model_fields)
        if reader.fieldnames != expected:
            errors.append(f"{path.name}: header {reader.fieldnames} != expected {expected}")
            return []
        for n, raw in enumerate(reader, start=2):
            if None in raw or None in raw.values():
                errors.append(f"{path.name} line {n}: wrong number of columns")
                continue
            try:
                rows.append(model(**raw))
            except ValidationError as exc:
                for err in exc.errors():
                    loc = ".".join(str(p) for p in err["loc"]) or "row"
                    errors.append(f"{path.name} line {n}: {loc}: {err['msg']}")
    if not rows and not any(e.startswith(path.name) for e in errors):
        errors.append(f"{path.name}: no data rows")
    return rows


def _check_unique(name: str, rows: list, errors: list[str]) -> bool:
    seen, ok = set(), True
    for r in rows:
        k = KEYS[name](r)
        if k in seen:
            errors.append(f"{name}.csv: duplicate key {k}")
            ok = False
        seen.add(k)
    return ok


def _check_buckets(name: str, rows: list, errors: list[str], warnings: list[str]) -> None:
    by_year: dict[int, list] = defaultdict(list)
    for r in rows:
        by_year[r.Year].append(r)
    for year, rs in sorted(by_year.items()):
        buckets = [r.Bucket for r in rs]
        if buckets != list(range(1, len(rs) + 1)):
            errors.append(f"{name}.csv {year}: buckets must be 1..n in file order, got {buckets}")
            continue
        for col in ("Single", "Jointly"):
            lim = [getattr(r, col) for r in rs]
            if any(b <= a for a, b in zip(lim, lim[1:])):
                errors.append(f"{name}.csv {year}: {col} limits must ascend, got {[str(x) for x in lim]}")
        top = rs[-1]
        if not (is_unbounded(top.Single) and is_unbounded(top.Jointly)):
            warnings.append(
                f"{name}.csv {year}: top bucket {top.Bucket} is not an unbounded sentinel; "
                "income above it is not modeled"
            )


def load_all(data_dir: Path | str | None = None) -> Tables:
    base = Path(data_dir) if data_dir else DATA_DIR
    errors: list[str] = []
    warnings: list[str] = []
    data: dict[str, tuple] = {}

    for name, model in SPECS.items():
        rows = _read_rows(base / f"{name}.csv", model, errors)
        if rows and _check_unique(name, rows, errors) and name in ("tblTaxRate", "tblTaxRateLTCG"):
            _check_buckets(name, rows, errors, warnings)
        data[name] = tuple(rows)

    if data["tblInputMap"]:
        orders = sorted(r.Order for r in data["tblInputMap"])
        if orders != list(range(1, len(orders) + 1)):
            errors.append("tblInputMap.csv: Order must be 1..n with no gaps")
        fields = [r.Field for r in data["tblInputMap"]]
        if len(set(fields)) != len(fields):
            errors.append("tblInputMap.csv: duplicate Field values")
        missing = [f for f in fields if f not in m.FilerInputs.model_fields]
        if missing:
            errors.append(f"tblInputMap.csv: Field not on FilerInputs: {missing}")

    if errors:
        raise TableValidationError(errors)

    ages = sorted(r.Age for r in data["tblUniformRMDFactors"])
    if ages != list(range(ages[0], ages[-1] + 1)):
        raise TableValidationError(["tblUniformRMDFactors.csv: ages must be contiguous"])

    data["tblInputMap"] = tuple(sorted(data["tblInputMap"], key=lambda r: r.Order))
    return Tables(data=data, warnings=tuple(warnings))


@lru_cache(maxsize=1)
def get_tables() -> Tables:
    return load_all()


def reload_tables() -> Tables:
    get_tables.cache_clear()
    return get_tables()
