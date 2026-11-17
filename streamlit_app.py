"""Streamlit entry point. Community Cloud main file: streamlit_app.py"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from app import (branding, excel_import, form_state, input_help, pdf_report, report, scenario_io,
                 version as app_version)
from app.calc.common import CalcError
from app.calc.engine import compute
from app.display import display_records
from app.tables import SPECS, TableValidationError, load_all

APP_TITLE = "Fifth Generation Tax Optimizer"
BRAND = branding.load_brand()
FAVICON = branding.asset("favicon.png")

st.set_page_config(page_title=APP_TITLE, page_icon=str(FAVICON) if FAVICON.is_file() else None,
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_resource(show_spinner=False)
def _load():
    """Return (tables, errors). Errors are shown instead of crashing the app."""
    try:
        return load_all(), []
    except TableValidationError as exc:
        return None, exc.errors


def _apply_branding() -> None:
    st.markdown(f"<style>{branding.css(BRAND)}</style>", unsafe_allow_html=True)
    ribbon = branding.logo_file(BRAND, "ribbon_dark")
    shield = branding.logo_file(BRAND, "shield_dark")
    if ribbon:
        st.logo(str(ribbon), icon_image=str(shield) if shield else None, size="large")
    with st.container(key="fga_header"):
        st.markdown(branding.header_html(BRAND, APP_TITLE), unsafe_allow_html=True)


def _handle_import(raw: bytes, tables) -> None:
    messages: list[tuple[str, str]] = []
    try:
        result = scenario_io.import_scenario(raw.decode("utf-8-sig"), tables)
    except UnicodeDecodeError:
        messages.append(("error", "The file is not UTF-8 text."))
    except scenario_io.ScenarioError as exc:
        messages.extend(("error", err) for err in exc.errors)
    else:
        skipped = form_state.apply_import(st.session_state, result.values, tables)
        st.session_state["report_title"] = result.report_title
        st.session_state["last_updated"] = result.last_updated
        messages.append(("success", f"Imported {len(result.values)} inputs from \"{result.report_title}\"."))
        messages.extend(("warning", w) for w in result.warnings + skipped)
    st.session_state["_import_messages"] = messages


def _handle_excel(raw: bytes, filename: str, tables) -> None:
    """Convert an uploaded Excel template to scenario JSON, then load it like any JSON import."""
    try:
        conversion = excel_import.convert_workbook(raw, tables.rows("tblInputMap"), filename)
    except excel_import.WorkbookError as exc:
        st.session_state["_import_messages"] = [("error", str(exc))]
        return
    _handle_import(conversion.json_text.encode("utf-8"), tables)
    messages = st.session_state["_import_messages"]
    messages.insert(0, ("info", f"Converted the Excel workbook \"{filename}\": {conversion.filled} inputs filled, "
                                f"{len(conversion.blank)} blank. Use Export scenario (JSON) to save the JSON file."))
    messages.extend(("warning", w) for w in conversion.warnings)


def _scenario_tools(tables) -> None:
    """Import and export of scenarios, plus options. Runs before the input widgets are
    created so that an import can set their values."""
    with st.expander("Scenario: import / export"):
        uploaded = st.file_uploader("Import scenario (JSON or Excel template)", type=["json", "xlsx", "xlsm"],
                                    key="scenario_upload")
        if uploaded is not None:
            token = (uploaded.name, uploaded.size)
            if st.session_state.get("_import_token") != token:
                st.session_state["_import_token"] = token
                if uploaded.name.lower().endswith((".xlsx", ".xlsm")):
                    _handle_excel(uploaded.getvalue(), uploaded.name, tables)
                else:
                    _handle_import(uploaded.getvalue(), tables)
        for kind, text in st.session_state.get("_import_messages", []):
            getattr(st, kind)(text)

        try:
            inputs = form_state.read_state(st.session_state, tables)
            payload = scenario_io.export_scenario(inputs, st.session_state["report_title"], tables)
        except (ValueError, scenario_io.ScenarioError) as exc:
            st.caption(f"Export unavailable: {exc}")
        else:
            st.download_button(
                "Export scenario (JSON)", payload,
                file_name=scenario_io.safe_filename(st.session_state["report_title"]),
                mime="application/json",
            )

    with st.expander("Options"):
        st.checkbox("Reproduce workbook (legacy mode)", key="legacy_mode",
                    help="Matches the Excel workbook's quirks instead of applying the planned fixes.")
        if st.button("Reload tables"):
            st.cache_resource.clear()
            st.rerun()


def _value_widget(row, key: str, disabled: bool = False) -> None:
    tip = input_help.help_for(row.Field)
    if row.Type == "date":
        st.date_input(row.Label, min_value=date(1900, 1, 1), max_value=date(2100, 12, 31),
                      key=key, disabled=disabled, help=tip)
    elif row.Type == "money":
        st.number_input(row.Label, step=100.0, format="%.2f", key=key, disabled=disabled, help=tip)
    else:
        st.text_input(row.Label, key=key, disabled=disabled, help=tip)


def _render_field(row, tables) -> None:
    key = form_state.state_key(row.Field)
    tip = input_help.help_for(row.Field)
    if row.Field == "tax_year":
        st.selectbox(row.Label, tables.supported_years(), key=key, help=tip)
    elif row.Field == "filing_status":
        st.selectbox(row.Label, list(form_state.STATUS_OPTIONS), key=key, help=tip)
    elif row.Field in form_state.OPTIONAL_FIELDS:
        enabled = st.checkbox(f"Enter: {row.Label}", key=form_state.flag_key(row.Field), help=tip)
        _value_widget(row, key, disabled=not enabled)
    else:
        _value_widget(row, key)


def _input_sections(tables) -> None:
    """One collapsible container per tblInputMap group; the first group starts open."""
    for index, (group, rows) in enumerate(form_state.groups(tables)):
        with st.expander(group, expanded=index == 0):
            for row in rows:
                _render_field(row, tables)


def _kpi_row(items: list[tuple]) -> None:
    """One row of metrics. Each item is (label, value) or (label, value, tooltip)."""
    for column, (label, value, *tip) in zip(st.columns(len(items)), items):
        column.metric(label, value, help=tip[0] if tip else None)


def _planning_row(result, inputs) -> None:
    """Room left in the 0% capital gains bracket and before Schedule A beats the standard deduction."""
    room, zero_top = report.zero_ltcg_room(result)
    if zero_top is None:
        zero_tip = "The 0% long-term capital gains bracket was not found in the tax tables."
    else:
        zero_tip = (
            f"Long-term capital gains you could still realize at the 0% rate. The 0% bracket ends at "
            f"{report.fmt_money(zero_top)} of taxable income for {result.filing_status} in {result.tax_year}; "
            "this is that amount less your taxable ordinary income and the gains already in the bracket. "
            "Realizing more gains also raises AGI, which can increase taxable Social Security and NIIT; "
            "this figure does not allow for that.")
    gap_tip = (
        "More Schedule A deductions (gifts, medical, taxes) you could add before itemizing beats the standard "
        f"deduction of {report.fmt_money(result.standard_deduction)}. Until they do, extra itemized deductions "
        "do not lower regular tax. Itemized deductions are counted up to the AGI limit.")
    _kpi_row([
        ("Additional LTCG at 0%", "n/a" if room is None else report.fmt_money(room), zero_tip),
        ("Left before Schedule A", report.fmt_money(report.itemizing_gap(result, inputs)), gap_tip),
    ])


def _results_tab(tables) -> None:
    try:
        inputs = form_state.read_state(st.session_state, tables)
        result = compute(inputs, tables, legacy=st.session_state.get("legacy_mode", False))
    except (CalcError, ValueError) as exc:
        st.error(f"Cannot calculate: {exc}")
        return

    if result.legacy:
        st.caption("Legacy mode: reproducing the Excel workbook.")
    _kpi_row([
        ("Total tax", report.fmt_money(result.total_tax)),
        (report.due_label(result), report.fmt_money(abs(result.due_or_refund))),
        ("Effective rate (of AGI)", report.fmt_rate(result.effective_rate)),
        ("Marginal ordinary rate", report.fmt_rate(report.marginal_ordinary_rate(result), 0)),
    ])
    _kpi_row([
        ("Adjusted gross income", report.fmt_money(result.agi)),
        ("Taxable ordinary income", report.fmt_money(result.taxable_ordinary)),
        ("Required minimum distribution", report.fmt_money(result.rmd)),
        ("Standard deduction", report.fmt_money(result.standard_deduction)),
    ])
    _planning_row(result, inputs)
    for warning in result.warnings:
        st.warning(warning)

    title = st.session_state["report_title"]
    pdf = pdf_report.build_pdf(result, inputs, tables, title, st.session_state["last_updated"],
                               logo=branding.asset("ribbon_white.jpg"))
    st.download_button("Download PDF report", pdf, file_name=pdf_report.pdf_filename(title),
                       mime="application/pdf")

    for section_title, rows in report.sections(result):
        with st.expander(section_title, expanded=section_title == "Summary"):
            st.dataframe([{"Item": label, "Amount": value} for label, value in rows],
                         hide_index=True, use_container_width=True)
    with st.expander("Ordinary income brackets"):
        st.dataframe(report.allocation_records(result.ordinary_allocations), hide_index=True,
                     use_container_width=True)
    with st.expander("Long-term capital gains brackets"):
        st.dataframe(report.allocation_records(result.ltcg_allocations), hide_index=True,
                     use_container_width=True)


def _status_tab(tables) -> None:
    st.success("All tables loaded and validated.")
    years = tables.supported_years()
    col1, col2, col3 = st.columns(3)
    col1.metric("Application version", app_version.__version__)
    col2.metric("Tables loaded", len(SPECS))
    col3.metric("Supported tax years", ", ".join(str(y) for y in years) or "none")
    st.caption(f"Calculations were built from Excel workbook version {app_version.WORKBOOK_BASELINE}.")
    for warning in tables.warnings:
        st.warning(warning)


def _tables_tab(tables) -> None:
    name = st.selectbox("Table", list(SPECS))
    st.dataframe(display_records(name, tables.rows(name)), hide_index=True, use_container_width=True)


def main() -> None:
    tables, errors = _load()
    _apply_branding()

    if errors:
        st.error("Table validation failed. Fix the CSV files in data/ and reload.")
        for err in errors:
            st.write(f"- {err}")
        if st.button("Reload tables"):
            st.cache_resource.clear()
            st.rerun()
        return

    form_state.init_state(st.session_state, tables)

    with st.sidebar:
        st.markdown('<div class="fga-side-title">Inputs</div>', unsafe_allow_html=True)
        inputs_box = st.container()
        tools_box = st.container()
    with tools_box:          # first, so an import can set the input widgets' values
        _scenario_tools(tables)
    with inputs_box:
        _input_sections(tables)

    st.text_input("Report title", key="report_title", label_visibility="collapsed",
                  placeholder="Add a client name")
    year = escape(str(st.session_state["in_tax_year"]))
    updated = escape(branding.format_updated(st.session_state["last_updated"]))
    st.markdown(f'<div class="fga-meta">Tax year {year} &nbsp;|&nbsp; Last updated {updated}</div>',
                unsafe_allow_html=True)

    results_tab, tables_tab, status_tab = st.tabs(["Results", "Tables", "Status"])
    with results_tab:
        _results_tab(tables)
    with tables_tab:
        _tables_tab(tables)
    with status_tab:
        _status_tab(tables)

    st.markdown(branding.footer_html(BRAND), unsafe_allow_html=True)
    st.caption(f"{app_version.version_line()} \u00b7 Excel workbook baseline {app_version.WORKBOOK_BASELINE}")


main()
