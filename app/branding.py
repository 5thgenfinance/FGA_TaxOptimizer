"""Fifth Generation Advisers branding: colors, fonts, logos and CSS.

Reads brand/fga_brand.json and the images in assets/brand/. No Streamlit
import, so everything here is testable.

Logo naming: the *_dark files (shield_navy, ribbon_navy) are drawn for NAVY surfaces and the
*_light files (shield_cream, ribbon_cream) for off-white surfaces; ribbon_white is for paper.
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
PANEL = "#e3e9f4"  # Streamlit secondaryBackgroundColor
LIGHT_BLUE = "#dfe7f3"  # sidebar container fill
MUTED = "#8a93a8"  # placeholder text
DISCLOSURE = "Estimates are for planning purposes only and are not tax, legal or investment advice."
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
    """Content of the navy header band: navy-surface shield, title and tagline."""
    uri = data_uri(logo_file(brand, "shield_dark"))
    image = f'<img src="{uri}" alt="">' if uri else ""
    return (
        '<div class="fga-header">'
        f"{image}<div><div class=\"fga-title\">{escape(title)}</div>"
        f'<div class="fga-tagline">{escape(brand["tagline"])}</div></div></div>'
    )


def footer_html(brand: dict) -> str:
    """Disclosure footer with the off-white-surface shield."""
    uri = data_uri(logo_file(brand, "shield_light"))
    image = f'<img src="{uri}" alt="">' if uri else ""
    firm = f"{brand['firm_name']} \u00b7 {brand['tagline']}"
    return (f'<div class="fga-footer">{image}<div>{escape(DISCLOSURE)}<br>'
            f"<span>{escape(firm)}</span></div></div>")


def css(brand: dict) -> str:
    """Stylesheet that gives Streamlit the Fifth Generation look (navy chrome, off-white page).

    Headings use the heading font; everything else uses the body font. The navy-surface logo
    JPGs carry their own navy background, so no blending is needed.
    """
    colors, fonts = brand["colors"], brand["fonts"]
    navy, bronze, off, char = colors["navy"], colors["bronze"], colors["offwhite"], colors["charcoal"]
    heading, body = fonts["heading"], fonts["body"]
    families = (f"family={heading.replace(' ', '+')}:ital,wght@0,400;0,600;0,700;1,400;1,600"
                f"&family={body.replace(' ', '+')}:wght@400;600;700")
    side = '[data-testid="stSidebar"]'
    return f"""
@import url('https://fonts.googleapis.com/css2?{families}&display=swap');
[data-testid="stElementContainer"]:has(style) {{ display: none !important; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp [data-baseweb], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"],
.fga-meta, .fga-tagline, .fga-footer {{ font-family: '{body}', sans-serif; }}
.stApp {{ background: {off}; color: {char}; }}
h1, h2, h3, h4, h5, h6, [data-testid="stHeading"], .fga-title, .fga-side-title,
[data-testid="stMetricValue"] {{ font-family: '{heading}', serif; color: {navy}; }}

header[data-testid="stHeader"] {{ background: {navy} !important; }}
header[data-testid="stHeader"] *, [data-testid="stToolbar"] * {{ color: #ffffff !important; }}
header[data-testid="stHeader"] svg {{ fill: #ffffff !important; }}
.block-container {{ padding-top: 3.75rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }}

div:has(> .st-key-fga_header) {{ position: sticky; top: 3.75rem; z-index: 999; background: {off}; padding-bottom: 10px; }}
.st-key-fga_header {{ background: {navy}; width: calc(100% + 4rem) !important; max-width: none !important;
  margin: 0 -2rem; padding: 4px 2rem 18px 2rem; border-bottom: 3px solid {bronze}; box-sizing: border-box; }}
.fga-header {{ display: flex; align-items: center; gap: 12px; position: relative; top: -6px; }}
.fga-header img {{ height: 38px; width: auto; display: block; margin: 0; }}
.fga-title {{ color: #ffffff; font-size: 1.5rem; font-weight: 700; line-height: 1.1; letter-spacing: .03em; }}
.fga-tagline {{ color: {bronze}; letter-spacing: .18em; font-size: 11px; text-transform: uppercase; margin-top: 2px; }}
.fga-meta {{ color: {char}; margin: -.4rem 0 1rem 0; }}

.st-key-report_title input {{ font-family: '{heading}', serif; font-style: italic; font-size: 2.4rem;
  font-weight: 700; color: {navy}; background: transparent; border: none;
  border-bottom: 2px solid #d8dce6; border-radius: 0; padding-left: 0; }}
.st-key-report_title input::placeholder {{ color: {MUTED}; font-weight: 400; opacity: 1; }}
.st-key-report_title label {{ display: none; }}

[data-testid="stMetricValue"] {{ font-size: 2rem; }}
[data-testid="stMetricLabel"] p {{ font-size: .8rem; color: {char}; }}

{side}, {side} > div:first-child {{ background: {navy} !important; }}
{side} {{ border-right: 1px solid {bronze}; }}
{side} h1, {side} h2, {side} h3, {side} label, {side} p, {side} span,
{side} [data-testid="stCaptionContainer"] {{ color: #ffffff; }}
{side} svg {{ fill: #ffffff; }}
{side} .fga-side-title {{ color: #ffffff; font-size: 1.5rem; font-weight: 700; margin: .4rem 0 .6rem 0; }}

{side} [data-testid="stExpander"] details {{ background: {LIGHT_BLUE}; border: 1px solid {bronze};
  border-radius: 8px; margin-bottom: .5rem; }}
{side} [data-testid="stExpander"] summary, {side} [data-testid="stExpander"] label,
{side} [data-testid="stExpander"] p, {side} [data-testid="stExpander"] span,
{side} [data-testid="stExpander"] [data-testid="stCaptionContainer"] {{ color: {navy}; }}
{side} [data-testid="stExpander"] summary p {{ font-weight: 600; }}
{side} [data-testid="stExpander"] svg {{ fill: {navy}; }}

{side} [data-baseweb="input"], {side} [data-baseweb="select"] > div, {side} [data-baseweb="base-input"],
{side} [data-testid="stDateInput"] > div:not([data-testid="stWidgetLabel"]) {{ background: #ffffff !important; }}
{side} [data-baseweb="input"] *, {side} [data-baseweb="base-input"] *, {side} [data-baseweb="select"] *,
{side} input, {side} [data-testid="stDateInput"] * {{ color: {char} !important; -webkit-text-fill-color: {char} !important; }}
{side} [data-baseweb="input"] svg, {side} [data-baseweb="select"] svg,
{side} [data-testid="stDateInput"] svg {{ fill: {char} !important; }}
{side} [data-testid="stDateInput"] [data-testid="stWidgetLabel"] *,
{side} [data-testid="stDateInput"] label * {{ color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }}
{side} [data-testid="stExpander"] [data-testid="stDateInput"] [data-testid="stWidgetLabel"] *,
{side} [data-testid="stExpander"] [data-testid="stDateInput"] label * {{ color: {navy} !important; -webkit-text-fill-color: {navy} !important; }}

{side} button[kind="secondary"] {{ background: {LIGHT_BLUE}; color: {navy}; border: 1px solid {bronze}; }}
{side} button[kind="secondary"] p, {side} button[kind="secondary"] span {{ color: {navy}; }}
[data-testid="stFileUploaderDropzone"] {{ border: 2px dashed {bronze}; background: #ffffff; min-height: 90px; }}
[data-testid="stSidebarHeader"] {{ min-height: 3.5rem; }}

.stButton > button, .stDownloadButton > button {{ border: 1px solid {bronze}; color: {navy}; background: #ffffff; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: {navy}; color: {navy}; background: {LIGHT_BLUE}; }}

.fga-footer {{ display: flex; align-items: center; gap: 14px; border-top: 1px solid {bronze}; margin-top: 32px;
  padding-top: 16px; font-size: 13px; line-height: 1.5; color: {char}; }}
.fga-footer img {{ height: 40px; width: auto; }}
.fga-footer span {{ color: {navy}; font-weight: 600; }}
"""
