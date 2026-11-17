import re
import tomllib

from app import version
from app.config import REPO_ROOT


def test_version_is_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", version.__version__)


def test_pyproject_version_matches_the_app_version():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == version.__version__


def test_changelog_has_an_entry_for_this_version():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version.__version__}]" in text


def test_plan_states_the_version():
    assert version.__version__ in (REPO_ROOT / "PROJECT_PLAN.md").read_text(encoding="utf-8")


def test_version_line():
    assert version.version_line() == f"Version {version.__version__}"
