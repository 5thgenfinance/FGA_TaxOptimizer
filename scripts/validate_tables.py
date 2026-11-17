#!/usr/bin/env python
"""Validate every CSV in data/. Exit 0 if valid, 1 otherwise."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tables import SPECS, TableValidationError, load_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="directory holding the CSV files (default: ./data)")
    args = parser.parse_args()
    try:
        tables = load_all(args.data_dir)
    except TableValidationError as exc:
        print("TABLE VALIDATION FAILED")
        for e in exc.errors:
            print(f"  - {e}")
        return 1
    for name in SPECS:
        print(f"OK  {name:<24} {len(tables.rows(name)):>3} rows")
    print(f"Supported years: {tables.supported_years()}")
    for w in tables.warnings:
        print(f"WARNING: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
