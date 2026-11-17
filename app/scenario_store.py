"""Saved scenarios: a small storage interface with a local-directory backend.

The local backend writes validated scenario JSON files to a directory. On hosts
with an ephemeral disk (Streamlit Community Cloud) those files disappear when
the app restarts, so the Export button remains the durable option until a
persistent backend is added behind the same interface.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import REPO_ROOT
from app.scenario_io import ScenarioError, import_scenario, safe_filename
from app.tables import Tables

DEFAULT_DIR = REPO_ROOT / "saved_scenarios"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


@dataclass(frozen=True)
class SavedScenario:
    name: str
    title: str
    last_updated: str


class LocalScenarioStore:
    """One JSON file per scenario, named after the report title."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def _path(self, name: str) -> Path:
        if not NAME_PATTERN.match(name or ""):
            raise ScenarioError([f"Invalid scenario name: {name!r}"])
        return self.directory / f"{name}.json"

    def save(self, text: str, tables: Tables) -> SavedScenario:
        """Validate and store scenario JSON; a scenario with the same title is replaced."""
        result = import_scenario(text, tables)
        name = Path(safe_filename(result.report_title)).stem
        path = self._path(name)
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(text, encoding="utf-8")
        temp.replace(path)
        return SavedScenario(name, result.report_title, result.last_updated)

    def list(self, tables: Tables) -> list[SavedScenario]:
        """Saved scenarios, newest first; unreadable or invalid files are skipped."""
        if not self.directory.is_dir():
            return []
        found = []
        for path in self.directory.glob("*.json"):
            try:
                result = import_scenario(path.read_text(encoding="utf-8-sig"), tables)
            except (ScenarioError, OSError, UnicodeDecodeError):
                continue
            found.append(SavedScenario(path.stem, result.report_title, result.last_updated))
        return sorted(found, key=lambda s: (s.last_updated, s.name), reverse=True)

    def load(self, name: str) -> str:
        path = self._path(name)
        try:
            return path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as exc:
            raise ScenarioError([f"No saved scenario named {name!r}"]) from exc

    def delete(self, name: str) -> None:
        path = self._path(name)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise ScenarioError([f"No saved scenario named {name!r}"]) from exc


def default_store() -> LocalScenarioStore:
    """Directory from TAXOPT_SCENARIO_DIR, else ./saved_scenarios (never committed)."""
    return LocalScenarioStore(os.environ.get("TAXOPT_SCENARIO_DIR", DEFAULT_DIR))
