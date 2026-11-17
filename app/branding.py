"""Fifth Generation Advisers branding: colors, fonts, logos and CSS.

Reads brand/fga_brand.json and the images in assets/brand/. No Streamlit
import, so everything here is testable.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path

from app.config import REPO_ROOT

BRAND_JSON = REPO_ROOT / "brand" / "fga_brand.json"
ASSET_DIR = REPO_ROOT / "assets" / "brand"
PANEL = "#e3e9f4"  # expander and sidebar panel fill
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

DEFAULT_BRAND = {
    "firm_name": "Fifth Generation Advisers",
    "tagline": "Registered Investment Adviser",
    "colors": {"navy": "#1a2744", "bronze": "#c49a4a", "offwhite": "#f7f4ef", "charcoal": "#2c2c2c"},
    "fonts": {"heading": "Playfair Display", "body": "Source Sans 3"},
    "logos": {
        "shield_light": "assets/brand/shield_cream.jpg",
        "shield_dark": "assets/brand/shield_navy.jpg",
        "ribbon_light": "assets/brand/ribbon_cream.jpg",
        "ribbon_dark": "assets/brand/ribbon_navy.jpg",
    },
}


@lru_cache(maxsize=4)
def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def load_brand(path: Path | str = BRAND_JSON) -> dict:
    """Brand settings from the JSON file, filled in with defaults for anything missing."""
    brand = {key: (dict(value) if isinstance(value, dict) else value) for key, value in DEFAULT_BRAND.items()}
    try:
        data = json.loads(_load(str(path)))
    except (OSError, ValueError):
        return brand
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(brand.get(key), dict):
            brand[key].update(value)
        else:
            brand[key] = value
    return brand


def asset(name: str) -> Path:
    """A file in assets/brand/."""
    return ASSET_DIR / name


def logo_file(brand: dict, key: str) -> Path | None:
    """Path of a logo listed in the brand file, or None if it is missing."""
    relative = brand.get("logos", {}).get(key)
    path = REPO_ROOT / relative if relative else None
    return path if path and path.is_file() else None


def data_uri(path: Path | None) -> str | None:
    """Embed an image in HTML; None if the file is missing or not an image."""
    if path is None or not Path(path).is_file():
        return None
    mime = MIME.get(Path(path).suffix.lower())
    if mime is None:
        return None
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def format_updated(iso_timestamp: str) -> str:
    """'2026-11-17T09:05:00' -> 'November 17, 2026'; unparseable text is returned as is."""
    try:
        moment = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return iso_timestamp
    return f"{moment:%B} {moment.day}, {moment.year}"


def header_html(brand: dict, title: str) -> str:
    """The navy header band: shield, title and tagline."""
    uri = data_uri(logo_file(brand, "shield_light"))
    image = f'<img src="{uri}" alt="">' if uri else ""
    return (
        '<div class="fga-header">'
        f"{image}<div><div class=\"fga-title\">{escape(title)}</div>"
        f'<div class="fga-tagline">{escape(brand["tagline"])}</div></div></div>'
    )


def css(brand: dict) -> str:
    """Stylesheet that gives Streamlit the Fifth Generation look."""
    colors, fonts = brand["colors"], brand["fonts"]
    navy, bronze, off, char = colors["navy"], colors["bronze"], colors["offwhite"], colors["charcoal"]
    heading, body = fonts["heading"], fonts["body"]
    families = (f"family={heading.replace(' ', '+')}:ital,wght@0,400;0,600;0,700;1,400;1,600"
                f"&family={body.replace(' ', '+')}:wght@400;600;700")
    return f"""
@import url('https://fonts.googleapis.com/css2?{families}&display=swap');
.stApp {{ background: {off}; color: {navy}; font-family: '{body}', sans-serif; }}
h1, h2, h3, h4 {{ font-family: '{heading}', serif; color: {navy}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; }}

.fga-header {{ display: flex; align-items: center; gap: 14px; background: {navy};
  border-bottom: 2px solid {bronze}; padding: 14px 22px; margin-bottom: 1.2rem; }}
.fga-header img {{ height: 46px; mix-blend-mode: lighten; }}
.fga-title {{ font-family: '{heading}', serif; color: {off}; font-size: 1.6rem; font-weight: 700; line-height: 1.1; }}
.fga-tagline {{ color: {bronze}; letter-spacing: .22em; font-size: .62rem; text-transform: uppercase; margin-top: 4px; }}
.fga-meta {{ color: {char}; font-size: .9rem; margin: -.4rem 0 1rem 0; }}

.st-key-report_title input {{ font-family: '{heading}', serif; font-style: italic; font-size: 2.1rem;
  font-weight: 600; color: {navy}; background: transparent; border: none;
  border-bottom: 1px solid #cfc9bd; border-radius: 0; padding-left: 0; }}
.st-key-report_title label {{ display: none; }}

[data-testid="stMetricValue"] {{ font-family: '{heading}', serif; color: {navy}; font-size: 2rem; }}
[data-testid="stMetricLabel"] p {{ font-size: .78rem; color: {char}; }}

[data-testid="stSidebar"] {{ background: {navy}; }}
[data-testid="stSidebar"] [data-testid="stLogo"] {{ mix-blend-mode: lighten; }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .fga-side-title {{ font-family: '{heading}', serif; color: {off}; }}
.fga-side-title {{ font-size: 1.5rem; font-weight: 700; margin: .4rem 0 .6rem 0; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{ color: {off}; }}
[data-testid="stSidebar"] [data-testid="stExpander"] details {{ background: {PANEL};
  border: 1px solid #c9d3e6; border-radius: 4px; margin-bottom: .5rem; }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ color: {navy}; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stExpander"] p,
[data-testid="stSidebar"] [data-testid="stExpander"] label,
[data-testid="stSidebar"] [data-testid="stExpander"] span {{ color: {navy}; }}

.stButton > button, .stDownloadButton > button {{ border: 1px solid {bronze}; color: {navy}; background: #ffffff; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: {navy}; color: {navy}; background: {PANEL}; }}
"""
