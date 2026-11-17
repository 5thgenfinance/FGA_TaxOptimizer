import json
import tomllib
from pathlib import Path

import pytest

from app import branding
from app.config import REPO_ROOT


def test_load_brand_falls_back_to_defaults_when_file_is_missing(tmp_path):
    brand = branding.load_brand(tmp_path / "missing.json")
    assert brand["colors"]["navy"] == "#1a2744"
    assert brand["fonts"]["heading"] == "Playfair Display"


def test_load_brand_merges_partial_files(tmp_path):
    path = tmp_path / "brand.json"
    path.write_text(json.dumps({"tagline": "Custom", "colors": {"navy": "#000000"}}), encoding="utf-8")
    brand = branding.load_brand(path)
    assert brand["tagline"] == "Custom"
    assert brand["colors"]["navy"] == "#000000" and brand["colors"]["bronze"] == "#c49a4a"
    assert branding.DEFAULT_BRAND["colors"]["navy"] == "#1a2744"  # defaults are not modified


def test_load_brand_ignores_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert branding.load_brand(path)["firm_name"] == "Fifth Generation Advisers"


def test_css_uses_brand_colors_fonts_and_selectors():
    css = branding.css(branding.load_brand(Path("does-not-exist.json")))
    for expected in ["#1a2744", "#c49a4a", "#f7f4ef", "Playfair Display", "Source Sans 3",
                     "Playfair+Display", ".st-key-report_title", '[data-testid="stSidebar"]',
                     '[data-testid="stExpander"]', ".fga-header", "mix-blend-mode"]:
        assert expected in css, expected


def test_header_without_logo_has_title_and_tagline_but_no_image():
    brand = branding.load_brand(Path("does-not-exist.json"))
    brand["logos"] = {"shield_light": "assets/brand/nope.jpg"}
    html = branding.header_html(brand, "Smith & <Co>")
    assert "Smith &amp; &lt;Co&gt;" in html and "Registered Investment Adviser" in html
    assert "<img" not in html


def test_header_embeds_logo_when_present(tmp_path, monkeypatch):
    image = tmp_path / "logo.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    monkeypatch.setattr(branding, "REPO_ROOT", tmp_path)
    brand = branding.load_brand(Path("does-not-exist.json"))
    brand["logos"] = {"shield_light": "logo.png"}
    assert 'src="data:image/png;base64,' in branding.header_html(brand, "T")


def test_data_uri(tmp_path):
    png = tmp_path / "a.png"
    png.write_bytes(b"abc")
    assert branding.data_uri(png) == "data:image/png;base64,YWJj"
    text = tmp_path / "a.txt"
    text.write_text("x")
    assert branding.data_uri(text) is None
    assert branding.data_uri(tmp_path / "missing.png") is None
    assert branding.data_uri(None) is None


@pytest.mark.parametrize("raw,expected", [
    ("2026-11-17T09:05:00", "November 17, 2026"),
    ("2026-01-05T00:00:00", "January 5, 2026"),
    ("not a date", "not a date"),
])
def test_format_updated(raw, expected):
    assert branding.format_updated(raw) == expected


def test_streamlit_theme_matches_brand_file():
    config = tomllib.loads((REPO_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    colors = branding.load_brand()["colors"]
    assert config["primaryColor"] == colors["bronze"]
    assert config["backgroundColor"] == colors["offwhite"]
    assert config["textColor"] == colors["navy"]
    assert config["secondaryBackgroundColor"] == branding.PANEL


def test_brand_images_exist_in_the_repository():
    brand = branding.load_brand()
    missing = [rel for rel in brand["logos"].values() if not (REPO_ROOT / rel).is_file()]
    if len(missing) == len(brand["logos"]):
        pytest.skip("brand images are not present in this checkout")
    assert missing == []
    assert branding.asset("favicon.png").is_file()
