"""Streamlit entry point. Community Cloud main file: streamlit_app.py"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape

import streamlit as st

from app import (branding, curves, excel_import, form_state, input_help, pdf_report, report, scenario_io,
                 version as app_version, whatif)
from app.calc.common import CalcError
from app.calc.engine import compute
from app.display import display_records
from app.models import FilerInputs
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
            st.cache_data.clear()
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


def _reset_whatif() -> None:
    for key in whatif.SLIDER_KEYS.values():
        st.session_state[key] = 0


def _change_label(diff: Decimal) -> str | None:
    """A metric delta such as '+$1,200', or None when there is no change."""
    text = whatif.signed_money(diff)
    return None if text == "$0" else text


LEVER_UI = {
    "ltcg": {"title": "Long-term capital gains", "label": "Long-term capital gains: add or remove ($)", "format": "%+d",
             "help": "Added to your long-term capital gains. A negative amount removes gains."},
    "stcg": {"title": "Short-term capital gains", "label": "Short-term capital gains: add or remove ($)", "format": "%+d",
             "help": "Added to your short-term gain or loss, which is taxed as ordinary income. "
                     "A negative amount removes gains."},
    "extra_deductions": {"title": "Schedule A deductions", "label": "Additional Schedule A deductions ($)", "format": "%d",
                         "help": "Added to your Schedule A deductions, for example more charitable gifts. "
                                 "They lower tax only once total itemized deductions exceed the standard deduction."},
    "extra_ira": {"title": "IRA distributions", "label": "Additional IRA distribution ($)", "format": "%d",
                  "help": "Extra taxable money taken from a traditional IRA, or a Roth conversion. It is taxed "
                          "as ordinary income and does not change the required minimum distribution."},
}
SHOW_KEYS = {lever: f"wi_show_{lever}" for lever in curves.LEVERS}
CONTROL_WIDTH = "60%"  # each slider and its curve are 40% narrower than the column


def _whatif_css() -> str:
    """Narrow the four sliders and their curves so the pairs fit comfortably in two columns."""
    selectors = [f".st-key-{key}" for key in whatif.SLIDER_KEYS.values()]
    selectors += [f".st-key-wi_chart_{lever}" for lever in curves.LEVERS]
    return f"{', '.join(selectors)} {{ width: {CONTROL_WIDTH} !important; }}"


def _adjustments(values: dict) -> whatif.Adjustments:
    return whatif.Adjustments(*(Decimal(values[key]) for key in curves.LEVERS))


@st.cache_data(show_spinner="Updating the tax curves...", max_entries=48)
def _lever_analysis(lever: str, inputs_json: str, legacy: bool, others: tuple, cap_percent: int, _tables):
    """Sweep one lever over its range, holding the other sliders where they are (cached)."""
    inputs = FilerInputs.model_validate_json(inputs_json)
    held = dict(zip(curves.LEVERS, others))

    def adjusted(x: int):
        return whatif.adjusted_inputs(inputs, _adjustments({**held, lever: x}))

    def run(x: int):
        try:
            return compute(adjusted(x), _tables, legacy=legacy)
        except (CalcError, ValueError, ArithmeticError):
            return None

    gap = None
    if lever == "extra_deductions":
        start = run(0)
        if start is not None:
            gap = float(report.itemizing_gap(start, adjusted(0)))
    return curves.analyze(run, lever, cap_percent=cap_percent if lever == "extra_ira" else None, gap=gap)


def _curve_chart(analysis: dict, current: int, current_tax) -> None:
    """Total tax across the lever's range, with the tax on the next dollar underneath."""
    import altair as alt
    import pandas as pd

    navy, bronze = BRAND["colors"]["navy"], BRAND["colors"]["bronze"]
    data = pd.DataFrame(analysis["points"], columns=["amount", "tax", "marginal", "ss"])
    x = alt.X("amount:Q", title=None, axis=alt.Axis(format="$,.0f"), scale=alt.Scale(nice=False))
    tips = [alt.Tooltip("amount:Q", format="$,.0f", title="Amount"), alt.Tooltip("tax:Q", format="$,.0f", title="Total tax"),
            alt.Tooltip("marginal:Q", format=".1%", title="Tax on the next dollar")]
    line = alt.Chart(data).mark_line(color=navy).encode(
        x=x, y=alt.Y("tax:Q", title="Total tax", axis=alt.Axis(format="$,.0f"), scale=alt.Scale(zero=False)), tooltip=tips)
    here = pd.DataFrame({"amount": [current], "tax": [float(current_tax)]})
    rule = alt.Chart(here).mark_rule(color=bronze, strokeDash=[4, 3]).encode(x="amount:Q")
    dot = alt.Chart(here).mark_point(color=bronze, filled=True, size=110).encode(x="amount:Q", y="tax:Q")
    top = alt.layer(line, rule, dot).properties(height=150)
    rates = data.dropna(subset=["marginal"])
    ceiling = max(0.1, float(rates["marginal"].max()) * 1.1) if len(rates) else 0.4
    bottom = alt.Chart(rates).mark_line(color=bronze, interpolate="step-after").encode(
        x=alt.X("amount:Q", title="Amount added (+) or removed (-)", axis=alt.Axis(format="$,.0f"), scale=alt.Scale(nice=False)),
        y=alt.Y("marginal:Q", title="Tax on next $", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, ceiling])),
        tooltip=tips).properties(height=80)
    st.altair_chart(alt.vconcat(top, bottom).configure_view(strokeWidth=0), use_container_width=True)


def _lever_block(lever: str, values: dict, analyses: dict, alt_result) -> int:
    """Title, show/hide switch, chart, slider and planning notes for one lever."""
    ui, (low, high) = LEVER_UI[lever], curves.RANGES[lever]
    st.markdown(f"**{ui['title']}**")
    show = st.checkbox("Show curve and notes", value=True, key=SHOW_KEYS[lever],
                       help="Hide this lever's chart and planning notes. The slider keeps working.")
    analysis = analyses.get(lever) if show else None
    if analysis and analysis["points"]:
        with st.container(key=f"wi_chart_{lever}"):
            _curve_chart(analysis, values[lever], alt_result.total_tax)
    value = st.slider(ui["label"], low, high, 0, 1_000, key=whatif.SLIDER_KEYS[lever], format=ui["format"], help=ui["help"])
    if lever == "extra_ira":
        st.selectbox("Keep the tax on each extra dollar at or below", curves.MARGINAL_CAPS, index=2, key="wi_ira_cap",
                     format_func=lambda cap: f"{cap}%", disabled=not show,
                     help="The notes below show how much IRA income fits before the tax on the next dollar passes this rate.")
    if analysis is not None:
        notes = curves.guidance(analysis, values[lever])
        st.markdown("\n".join("- " + note.replace("$", "\\$") for note in notes))
    return value


def _whatif_tab(tables) -> None:
    """Tax curves and sliders that adjust a copy of the inputs and compare the results with the current ones."""
    try:
        inputs = form_state.read_state(st.session_state, tables)
        legacy = st.session_state.get("legacy_mode", False)
        base = compute(inputs, tables, legacy=legacy)
    except (CalcError, ValueError) as exc:
        st.error(f"Cannot calculate: {exc}")
        return

    # Charts sit above their sliders, so read the slider values saved from the last interaction.
    values = {lever: int(st.session_state.get(key, 0)) for lever, key in whatif.SLIDER_KEYS.items()}
    adjustments = _adjustments(values)
    alt_inputs = whatif.adjusted_inputs(inputs, adjustments)
    try:
        alt = compute(alt_inputs, tables, legacy=legacy)
    except (CalcError, ValueError) as exc:
        st.error(f"Cannot calculate the what-if: {exc}")
        return

    st.markdown(f"<style>{_whatif_css()}</style>", unsafe_allow_html=True)
    st.caption("Each chart sweeps one lever across its range while the other sliders stay where you set them. The top "
               "line is total tax; the lower line is the tax on the next dollar. The dot is your slider setting. A flat "
               "stretch is free, a steep one is expensive, and a step up marks a bracket or other threshold. Use the "
               "checkbox under each title to hide that lever's chart and notes. These sliders only change a copy of "
               "your inputs; the Inputs panel and the Results tab stay as entered.")
    analyses: dict = {}
    inputs_json = inputs.model_dump_json()
    cap_percent = int(st.session_state.get("wi_ira_cap", 22))
    for lever in curves.LEVERS:
        if st.session_state.get(SHOW_KEYS[lever], True):  # a hidden lever costs no calculation
            others = tuple(0 if key == lever else values[key] for key in curves.LEVERS)
            analyses[lever] = _lever_analysis(lever, inputs_json, legacy, others, cap_percent, tables)

    left, right = st.columns(2)
    with left:
        _lever_block("ltcg", values, analyses, alt)
        _lever_block("stcg", values, analyses, alt)
    with right:
        _lever_block("extra_deductions", values, analyses, alt)
        _lever_block("extra_ira", values, analyses, alt)
    st.button("Reset sliders", key="wi_reset", on_click=_reset_whatif)

    effective_change = whatif.signed_points(base.effective_rate, alt.effective_rate)
    columns = st.columns(4)
    columns[0].metric("Total tax", report.fmt_money(alt.total_tax), _change_label(alt.total_tax - base.total_tax),
                      delta_color="inverse")
    columns[1].metric(report.due_label(alt), report.fmt_money(abs(alt.due_or_refund)),
                      _change_label(alt.due_or_refund - base.due_or_refund), delta_color="inverse",
                      help="The delta is the change in the amount due. A negative figure means less owed or a larger refund.")
    columns[2].metric("Effective rate (of AGI)", report.fmt_rate(alt.effective_rate),
                      None if effective_change in ("n/a", "0.00 pts") else effective_change, delta_color="inverse")
    change = whatif.tax_on_the_change(base, alt, adjustments)
    columns[3].metric("Tax on the change", "n/a" if change is None else report.fmt_rate(change),
                      help="The extra (or lower) total tax divided by the net income added or removed by the sliders. "
                           "Deductions are not income, so a deduction-only change shows n/a.")
    st.dataframe(whatif.comparison(base, inputs, alt, alt_inputs), hide_index=True, use_container_width=True)
    for warning in alt.warnings:
        if warning not in base.warnings:
            st.warning(warning)
    st.caption("Realizing more gains or income also raises AGI, which can change taxable Social Security and the "
               "net investment income tax; both are included in the figures above. Medicare premium surcharges "
               "(IRMAA), state taxes, and the Affordable Care Act subsidy cliffs are not modeled. These notes are "
               "planning aids, not tax advice.")


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
            st.cache_data.clear()
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

    results_tab, whatif_tab, tables_tab, status_tab = st.tabs(["Results", "What-if", "Tables", "Status"])
    with results_tab:
        _results_tab(tables)
    with whatif_tab:
        _whatif_tab(tables)
    with tables_tab:
        _tables_tab(tables)
    with status_tab:
        _status_tab(tables)

    st.markdown(branding.footer_html(BRAND), unsafe_allow_html=True)
    st.caption(f"{app_version.version_line()} \u00b7 Excel workbook baseline {app_version.WORKBOOK_BASELINE}")


main()
