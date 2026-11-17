"""Streamlit entry point. Community Cloud main file: streamlit_app.py"""
from __future__ import annotations

import streamlit as st

from app.display import display_records
from app.models import FilerInputs
from app.tables import SPECS, TableValidationError, load_all

st.set_page_config(page_title="FGA Tax Optimizer", layout="wide")


@st.cache_resource(show_spinner=False)
def _load():
    """Return (tables, errors). Errors are shown instead of crashing the app."""
    try:
        return load_all(), []
    except TableValidationError as exc:
        return None, exc.errors


def main() -> None:
    tables, errors = _load()

    st.title("FGA Tax Optimizer")
    st.text_input("Report title", value="Tax Retirement Optimizer Scenario", key="report_title")

    with st.sidebar:
        st.header("Data")
        if st.button("Reload tables"):
            st.cache_resource.clear()
            st.rerun()

    status_tab, tables_tab, scenario_tab = st.tabs(["Status", "Tables", "Scenario"])

    with status_tab:
        if errors:
            st.error("Table validation failed. Fix the CSV files in data/ and reload.")
            for err in errors:
                st.write(f"- {err}")
            return
        st.success("All tables loaded and validated.")
        years = tables.supported_years()
        col1, col2 = st.columns(2)
        col1.metric("Tables loaded", len(SPECS))
        col2.metric("Supported tax years", ", ".join(str(y) for y in years) or "none")
        for warning in tables.warnings:
            st.warning(warning)

    with tables_tab:
        if errors:
            st.info("Tables are unavailable until validation passes.")
        else:
            name = st.selectbox("Table", list(SPECS))
            st.dataframe(display_records(name, tables.rows(name)), hide_index=True, use_container_width=True)

    with scenario_tab:
        st.info("The inputs form, tax calculation and scenario JSON import/export arrive in Phase 2.")
        if not errors:
            st.caption(f"Scenario inputs defined in tblInputMap.csv ({len(tables.rows('tblInputMap'))} fields):")
            st.dataframe(display_records("tblInputMap", tables.rows("tblInputMap")), hide_index=True)
            st.caption(f"Model fields available: {len(FilerInputs.model_fields)}")


main()
