# Architecture and Developer Guide

Version 0.5.0. The specification is in PROJECT_PLAN.md; this guide explains how the code fits together and how to change it.

## 1. Design rules
- Tax-table values live in CSV files in `data/`, never in code.
- Calculations are pure functions. `app/calc/engine.compute(inputs, tables, legacy, as_of_year)` returns a `TaxResult` and never touches Streamlit.
- Modules that format or convert data (`report`, `display`, `branding`, `form_state`, `excel_import`, `excel_values`, `scenario_io`, `pdf_report`, `input_help`, `version`) do not import Streamlit, so they are unit-testable. Only `streamlit_app.py` imports it.
- Money and rates use `Decimal`.
- The Excel workbook's outputs are the golden regression test (`tests/test_golden_workbook.py`).

## 2. Data flow
```
sidebar widgets (st.session_state: in_<field>, has_<field>)
      |  form_state.read_state
      v
FilerInputs (Pydantic)  --compute(inputs, tables, legacy)-->  TaxResult
      ^                                                            |
      | form_state.apply_import                                    +--> report.sections -> Results tab
      |                                                            +--> pdf_report.build_pdf -> PDF
scenario_io.import_scenario  <--- JSON text <--- excel_import.convert_workbook <--- uploaded .xlsx
      ^
uploaded .json

FilerInputs --scenario_io.export_scenario--> JSON download
```
The form is generated from `data/tblInputMap.csv` (order, label, group, type, field, Excel cell).

## 3. Module map
| Module | Role |
|---|---|
| `streamlit_app.py` | Entry point: page, sidebar, tabs, imports, downloads |
| `app/tables.py`, `app/models.py`, `app/config.py` | CSV loader and validators, Pydantic models, paths |
| `app/calc/*` | Calculation modules (ordinary, ltcg, rmd, deductions, socialsec, niit, amt) and `engine` |
| `app/form_state.py` | Widget state to `FilerInputs` and back |
| `app/input_help.py` | Tooltip text for every input |
| `app/scenario_io.py` | Scenario JSON export, import and validation |
| `app/excel_import.py`, `app/excel_values.py` | Convert an uploaded workbook to scenario JSON; cell value conversion |
| `app/branding.py` | Brand colours, fonts, logos, CSS, header and footer HTML |
| `app/report.py`, `app/display.py`, `app/pdf_report.py` | Result formatting and the PDF |
| `app/version.py` | `__version__` and the workbook baseline |
| `app/scenario_store.py` | Local-folder saved scenarios. Not used by the UI since 0.5.0 |
| `excel/scenario_xlwings.py` | Local Excel to JSON bridge using xlwings |
| `excel/input_name_aliases.csv` | Old named ranges mapped to current names |
| `scripts/validate_tables.py` | CLI table check, also run in CI |

## 4. Common changes
### Add an input
1. Add a row to `data/tblInputMap.csv` (Order, Name, Cell, Type, Field, Label, Group).
2. Add the field to `FilerInputs` in `app/models.py` and use it in `app/calc/engine.py`.
3. Add tooltip text for the field in `app/input_help.py`.
4. Describe the input in `docs/USER_GUIDE.md` (a test checks the label appears).
5. If the workbook uses an old name for it, add a row to `excel/input_name_aliases.csv`.
6. Update the golden or phase tests as needed and run the tests.

### Add a tax year
Follow PROJECT_PLAN.md section 10. No code change is needed; add the year's tests.

### Change the look
Colours, fonts and logos are in `brand/fga_brand.json` and the CSS in `app/branding.py`. Logo files named `*_navy` are drawn for navy surfaces, `*_cream` for off-white surfaces and `ribbon_white` for paper (the PDF).

## 5. Excel import
`convert_workbook` opens the file with openpyxl in read-only value mode, so it sees the values saved in the file. For each tblInputMap row it finds the cell by: current name (workbook-wide, then sheet-level), then old names from `excel/input_name_aliases.csv` in file order, then the fixed address. Name matching ignores case. Cell values are converted by type in `excel_values.to_json_value`; unusable values become blank and are reported. The result is scenario JSON that goes through the same `import_scenario` validation as an uploaded JSON file.

## 6. Testing
```
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_tables.py
```
Useful groups: golden workbook, one file per calculation module, property tests (hypothesis), scenario JSON, PDF text checks, Excel import and aliases, input help (every input has a tooltip, checked in the running app), version consistency, documentation checks, and Streamlit AppTest smoke tests.

## 7. Branches, versions and releases
- `main` is deployed. Work goes to `test`, and the owner merges a pull request. On a private repository on the free GitHub plan, branch protection and rulesets are not enforced, so this is a working convention.
- Version numbers follow Semantic Versioning. The version appears in four places that tests keep in step: `app/version.py`, `pyproject.toml`, the heading in `CHANGELOG.md` and the header of `PROJECT_PLAN.md`.
- To release: update those four, add the changelog entry, run the tests, merge the pull request, then tag it with `git tag v0.5.0` and `git push origin v0.5.0` (using the new version number).
- PATCH: bug fixes and text. MINOR: features, new tax years, calculation changes (say so in the changelog). MAJOR: a breaking change to the scenario JSON schema or removal of a feature after 1.0.0.

## 8. Deployment
Streamlit Community Cloud deploys `streamlit_app.py` from `main` and installs from `requirements.txt` (pydantic, streamlit, reportlab, openpyxl). xlwings is local only. The Python version is chosen at deploy time and cannot be changed afterwards (3.12). PROJECT_PLAN.md section 13 lists the privacy and storage cautions.
