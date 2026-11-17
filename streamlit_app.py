"""Streamlit entry point. Community Cloud main file: streamlit_app.py"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from app import branding, form_state, pdf_report, report, scenario_io, scenario_store
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
    ribbon = branding.logo_file(BRAND, "ribbon_light")
    shield = branding.logo_file(BRAND, "shield_light")
    if ribbon:
        st.logo(str(ribbon), icon_image=str(shield) if shield else None, size="large")
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


def _saved_scenarios(tables, payload: str | None) -> None:
    store = scenario_store.default_store()
    st.markdown("**Saved scenarios**")
    st.caption("Stored on the server that runs this app. On Streamlit Community Cloud they are lost "
               "when the app restarts, so keep an exported copy of anything important.")
    if st.button("Save current scenario", disabled=payload is None):
        try:
            saved = store.save(payload, tables)
        except (scenario_io.ScenarioError, OSError) as exc:
            st.error(f"Could not save: {exc}")
        else:
            st.success(f"Saved \"{saved.title}\".")

    saved_items = store.list(tables)
    if not saved_items:
        st.caption("No saved scenarios yet.")
        return
    labels = {s.name: f"{s.title} ({s.last_updated[:16].replace('T', ' ')})" for s in saved_items}
    choice = st.selectbox("Saved scenario", list(labels), format_func=labels.get, key="saved_choice")
    col_load, col_delete = st.columns(2)
    if col_load.button("Load"):
        try:
            _handle_import(store.load(choice).encode("utf-8"), tables)
        except scenario_io.ScenarioError as exc:
            st.error(str(exc))
        else:
            st.rerun()
    if col_delete.button("Delete"):
        try:
            store.delete(choice)
        except scenario_io.ScenarioError as exc:
            st.error(str(exc))
        else:
            st.session_state.pop("saved_choice", None)
            st.rerun()


def _scenario_tools(tables) -> None:
    """Import, export, saved scenarios and options. Runs before the input widgets are
    created so that an import can set their values."""
    with st.expander("Scenario: import, export, save"):
        uploaded = st.file_uploader("Import scenario (JSON)", type="json", key="scenario_upload")
        if uploaded is not None:
            token = (uploaded.name, uploaded.size)
            if st.session_state.get("_import_token") != token:
                st.session_state["_import_token"] = token
                _handle_import(uploaded.getvalue(), tables)
        for kind, text in st.session_state.get("_import_messages", []):
            getattr(st, kind)(text)

        payload = None
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
        _saved_scenarios(tables, payload)

    with st.expander("Options"):
        st.checkbox("Reproduce workbook (legacy mode)", key="legacy_mode",
                    help="Matches the Excel workbook's quirks instead of applying the planned fixes.")
        if st.button("Reload tables"):
            st.cache_resource.clear()
            st.rerun()


def _value_widget(row, key: str, disabled: bool = False) -> None:
    if row.Type == "date":
        st.date_input(row.Label, min_value=date(1900, 1, 1), max_value=date(2100, 12, 31),
                      key=key, disabled=disabled)
    elif row.Type == "money":
        st.number_input(row.Label, step=100.0, format="%.2f", key=key, disabled=disabled)
    else:
        st.text_input(row.Label, key=key, disabled=disabled)


def _render_field(row, tables) -> None:
    key = form_state.state_key(row.Field)
    if row.Field == "tax_year":
        st.selectbox(row.Label, tables.supported_years(), key=key)
    elif row.Field == "filing_status":
        st.selectbox(row.Label, list(form_state.STATUS_OPTIONS), key=key)
    elif row.Field in form_state.OPTIONAL_FIELDS:
        enabled = st.checkbox(f"Enter: {row.Label}", key=form_state.flag_key(row.Field))
        _value_widget(row, key, disabled=not enabled)
    else:
        _value_widget(row, key)


def _input_sections(tables) -> None:
    """One collapsible container per tblInputMap group; the first group starts open."""
    for index, (group, rows) in enumerate(form_state.groups(tables)):
        with st.expander(group, expanded=index == 0):
            for row in rows:
                _render_field(row, tables)


def _kpi_row(items: list[tuple[str, str]]) -> None:
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(label, value)


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
    col1, col2 = st.columns(2)
    col1.metric("Tables loaded", len(SPECS))
    col2.metric("Supported tax years", ", ".join(str(y) for y in years) or "none")
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


main()
