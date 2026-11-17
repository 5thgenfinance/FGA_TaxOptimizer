"""Runtime settings."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("TAXOPT_DATA_DIR", REPO_ROOT / "data"))
