"""Application version (Semantic Versioning). Keep in step with pyproject.toml and CHANGELOG.md."""
from __future__ import annotations

__version__ = "1.0.0"
WORKBOOK_BASELINE = "2026.3.0"  # TaxRetirementOptimizer.xlsx version the calculations were built from


def version_line() -> str:
    return f"Version {__version__}"
