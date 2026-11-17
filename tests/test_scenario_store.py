from datetime import date, datetime

import pytest

from app import scenario_io as sio
from app.models import FilerInputs
from app.scenario_store import LocalScenarioStore, default_store


@pytest.fixture()
def store(tmp_path):
    return LocalScenarioStore(tmp_path / "saved")


def scenario_text(tables, title="Study A", wages=0, when=datetime(2026, 11, 16, 10, 0, 0)):
    inputs = FilerInputs(tax_year=2026, filing_status="Single", dob=date(1960, 1, 1), wages_and_tips=wages)
    return sio.export_scenario(inputs, title, tables, now=when)


def test_save_list_load_delete(store, tables):
    saved = store.save(scenario_text(tables, "Study A", wages=50_000), tables)
    assert saved.name == "Study_A" and saved.title == "Study A"
    assert [s.title for s in store.list(tables)] == ["Study A"]
    loaded = sio.import_scenario(store.load("Study_A"), tables)
    assert loaded.values["wages_and_tips"] == 50_000
    store.delete("Study_A")
    assert store.list(tables) == []


def test_list_of_missing_directory_is_empty_and_creates_nothing(store, tables):
    assert store.list(tables) == []
    assert not store.directory.exists()


def test_same_title_overwrites(store, tables):
    store.save(scenario_text(tables, "Study A", wages=1), tables)
    store.save(scenario_text(tables, "Study A", wages=2), tables)
    assert len(store.list(tables)) == 1
    assert sio.import_scenario(store.load("Study_A"), tables).values["wages_and_tips"] == 2


def test_invalid_scenario_is_rejected_and_nothing_written(store, tables):
    with pytest.raises(sio.ScenarioError):
        store.save("not json", tables)
    assert not store.directory.exists()


def test_corrupt_files_are_skipped(store, tables):
    store.save(scenario_text(tables, "Good"), tables)
    (store.directory / "broken.json").write_text("{oops", encoding="utf-8")
    (store.directory / "notes.txt").write_text("ignore me", encoding="utf-8")
    assert [s.name for s in store.list(tables)] == ["Good"]


def test_newest_first(store, tables):
    store.save(scenario_text(tables, "Older", when=datetime(2026, 1, 1, 9, 0, 0)), tables)
    store.save(scenario_text(tables, "Newer", when=datetime(2026, 6, 1, 9, 0, 0)), tables)
    assert [s.title for s in store.list(tables)] == ["Newer", "Older"]


@pytest.mark.parametrize("name", ["../secret", "a/b", "", ".hidden", "x" * 90, "a b"])
def test_unsafe_names_are_rejected(store, name):
    with pytest.raises(sio.ScenarioError):
        store.load(name)
    with pytest.raises(sio.ScenarioError):
        store.delete(name)


def test_missing_scenario_errors(store):
    with pytest.raises(sio.ScenarioError):
        store.load("Nope")
    with pytest.raises(sio.ScenarioError):
        store.delete("Nope")


def test_default_store_uses_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("TAXOPT_SCENARIO_DIR", str(tmp_path / "elsewhere"))
    assert default_store().directory == tmp_path / "elsewhere"
    monkeypatch.delenv("TAXOPT_SCENARIO_DIR")
    assert default_store().directory.name == "saved_scenarios"
