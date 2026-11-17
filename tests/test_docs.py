from app.config import REPO_ROOT


def read(*parts):
    return (REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_user_guide_describes_every_input(tables):
    guide = read("docs", "USER_GUIDE.md")
    missing = [row.Label for row in tables.rows("tblInputMap") if row.Label not in guide]
    assert missing == [], f"add these inputs to docs/USER_GUIDE.md: {missing}"


def test_readme_links_the_documents():
    readme = read("README.md")
    for target in ("docs/USER_GUIDE.md", "docs/ARCHITECTURE.md", "PROJECT_PLAN.md", "CHANGELOG.md"):
        assert target in readme, target
        assert (REPO_ROOT / target).is_file(), target
