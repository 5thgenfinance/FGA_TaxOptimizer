# TaxRetirementOptimizer → Python Web App (Streamlit)
Source: TaxRetirementOptimizer.xlsx v2026.3.0 + TaxRetirementOptimizer-Specification.md
Owner: Robert Maxwell
Application version: 0.5.0 (see CHANGELOG.md)
Last updated: 2026-11-17 (Phases 0–4 on `main`; release 0.5.0 is on branch `test`, pending merge to `main`)

Companion documents: `docs/USER_GUIDE.md` (using the app), `docs/ARCHITECTURE.md` (developer guide), `CHANGELOG.md`.

## 0. Status at a glance
| Phase | Scope | Status |
|---|---|---|
| 0 | Repo skeleton, CSV tables, loader/validator, CI, Streamlit skeleton | Done |
| 1 | Calculation modules and engine, golden workbook test | Done. Legacy mode matches the saved workbook to the cent. |
| 2 | Streamlit inputs form, results page, scenario JSON import/export, xlwings script | Committed. Needs the manual golden-case check in the app (section 8) and a first Excel run of the xlwings script. |
| 3 | Data and fixes: 2026 top bracket, RMD ages 72 and 101–120, 2027 tables, stacked AMT capital gains, RMD in Social Security income | Committed |
| 4 | PDF report, saved scenarios (local folder) | Committed. The saved-scenarios UI was removed in 0.5.0 (section 6). |
| 5 | Release 0.5.0: brand layout and category panels, Excel template upload with old-name fallback, tooltips, versioning, documentation | Done on branch `test`; pending merge to `main` |

Open before first real use: merge 0.5.0 to `main`, the first Streamlit Community Cloud deploy, the decisions in section 11 (Separate status, client-data access control), and the manual checks in section 8.

## 1. Goals and non-goals
**Goals**
- Reproduce the `TaxSheetSingle` estimate (ordinary tax, LTCG, NIIT, AMT, RMD, taxable Social Security, standard deduction, due/refund) as a Streamlit web app hosted on Streamlit Community Cloud.
- All tax-table data lives in external CSV files in `data/`. No table values are embedded in code.
- The 17 named LAMBDAs become pure Python functions with unit tests.
- The workbook's current outputs are the golden regression test.
- A scenario JSON file (ordered name/value pairs of the `inp...` named input cells, report title, last-updated date) moves scenarios between Excel and the web app (section 12). The web app can also read the Excel template directly (section 12.8).
- A PDF report for client work.

**Non-goals**
- Validating current tax law beyond the figures cited in section 4. The spec is an as-built description, not a law check.
- Schedule709 (Form 709 gift/GST grid): out of scope, will not be converted, imported or exported.
- Server-side storage of scenarios (removed in 0.5.0; scenarios are exported as JSON files).

## 2. Stack
| Layer | Choice | Reason |
|---|---|---|
| Web | Streamlit (Community Cloud) | Deploys straight from GitHub, no server to manage |
| Validation | Pydantic v2 | Typed input and CSV-row models |
| Math | `decimal.Decimal` for money and rates | Avoid float drift |
| Data | CSV via stdlib `csv` | Tables stay editable in Excel |
| PDF | reportlab | Pure-Python PDF generation, installs on Community Cloud |
| Excel upload | openpyxl | Reads the workbook's saved values and named ranges; no Excel needed; installs on Community Cloud |
| Excel bridge | xlwings (Python, local only) | Reads/writes the named input cells in an open workbook and exchanges scenario JSON; no VBA |
| Tests | pytest, hypothesis, pypdf, Streamlit AppTest | Golden case, edge cases, property tests, PDF text checks, UI smoke tests |
| Packaging | `requirements.txt` for hosting, `pyproject.toml` for dev | Community Cloud installs from `requirements.txt` |

## 3. Repository layout (current)
```
├─ streamlit_app.py              # Streamlit entry point (Community Cloud main file)
├─ requirements.txt              # hosting dependencies (pydantic, streamlit, reportlab, openpyxl)
├─ pyproject.toml                # dev install, version and extras (app, excel, dev)
├─ README.md, CHANGELOG.md, PROJECT_PLAN.md
├─ docs/                         # USER_GUIDE.md, ARCHITECTURE.md
├─ .streamlit/config.toml        # Streamlit theme colours
├─ assets/brand/, brand/         # logos, favicon, fga_brand.json, brand.html style guide
├─ data/                         # EXTERNAL TABLES (edit without touching code)
│  ├─ tblTaxRate.csv, tblTaxRateLTCG.csv
│  ├─ tblUniformRMDFactors.csv, tblRMDStartAge.csv
│  ├─ tblStandDeductionBase.csv, tblAMT.csv, tblNIIT.csv
│  ├─ tblStatusAliases.csv       # status normalization
│  ├─ tblParameters.csv          # constants hard-coded in the LAMBDAs
│  └─ tblInputMap.csv            # input names, cells, types, fields, UI labels and groups
├─ app/
│  ├─ config.py, models.py, tables.py   # settings, Pydantic models, CSV loader and validators
│  ├─ version.py                 # __version__ and the workbook baseline
│  ├─ status.py                  # normalize_status() via tblStatusAliases
│  ├─ scenario_io.py             # scenario JSON export/import and validation
│  ├─ scenario_store.py          # local-folder saved scenarios (not used by the UI since 0.5.0)
│  ├─ excel_import.py            # uploaded workbook -> scenario JSON (openpyxl), old-name aliases
│  ├─ excel_values.py            # Excel cell value -> JSON value, by input type
│  ├─ input_help.py              # tooltip text for every input
│  ├─ branding.py                # brand tokens, CSS, header and footer HTML
│  ├─ form_state.py              # Streamlit widget-state helpers (pure functions)
│  ├─ report.py, display.py      # result and table formatting (no Streamlit import)
│  ├─ pdf_report.py              # PDF report (reportlab)
│  └─ calc/
│     ├─ common.py               # Decimal helpers, errors, parameter lookup
│     ├─ ordinary.py, ltcg.py    # bracket lookup/allocation; stacked LTCG
│     ├─ rmd.py, deductions.py, socialsec.py, niit.py, amt.py
│     └─ engine.py               # compute(inputs, tables, legacy, as_of_year) -> TaxResult
├─ excel/
│  ├─ scenario_xlwings.py        # Excel <-> scenario JSON via xlwings (local)
│  └─ input_name_aliases.csv     # old named ranges -> current names
├─ scripts/validate_tables.py    # CLI check, also run in CI
├─ tests/                        # one test file per module, plus golden, phase 3, Excel import, tooltips, version, docs
└─ .github/workflows/ci.yml      # validate tables, then pytest
```
The repository root also holds the original workbook and its as-built specification.

## 4. External CSV tables
The CSV files in `data/` are the source of truth; this plan does not copy their contents. File name = Excel table name, and column headers are kept verbatim, including `FilingYear` in `tblStandDeductionBase`. Years 2025 and 2026 came from the workbook; the 2026 additions and all of 2027 were added from IRS documents (below), so the CSVs now go beyond the workbook.

**Supported years:** 2026 and 2027 (2025 is partial and not selectable: it has no AMT, NIIT or parameter rows).

**Sources**
- 2026 ordinary brackets, standard deduction, LTCG thresholds: Rev. Proc. 2025-32. The 37% bracket row was added for 2026.
- 2027 figures: Rev. Proc. 2026-35 (ordinary brackets, LTCG thresholds, standard deduction, age add-ons, AMT exemption, breakpoint and phase-out). Checks in `tests/test_phase3.py` reproduce the Rev. Proc.'s tax amounts at each bracket top exactly.
- RMD divisors, ages 72–120: IRS Publication 590-B, Table III (Uniform Lifetime); they also match the workbook's legacy list.
- AMT capital gains treatment: IRS instructions for Form 6251, Part III.
- **2027 SALT cap (40,804; 20,402 separate) is derived from the statute's 1% annual step. It is not read from an IRS document. Verify it.**
- Not indexed, carried forward from 2026: NIIT thresholds and rate, Social Security base amounts, senior-bonus amount and phase-out, medical and cash-contribution limits.

Notes on specific tables:
- `tblUniformRMDFactors.csv` covers ages 72–120. Ages outside it raise a clear error.
- `tblRMDStartAge.csv` holds the RMD start age by birth year (72, 73, 75), replacing the cutoffs hard-coded in the workbook formula.
- `tblStatusAliases.csv` replaces the inconsistent status string checks in the LAMBDAs.
- `tblParameters.csv` holds constants the LAMBDAs hard-code. The Separate column is a placeholder; confirm it.
- `tblInputMap.csv` has columns `Order,Name,Cell,Type,Field,Label,Group` (section 12.3).

### 4.1 Loader and validation rules (`tables.py`)
- Load once and cache. `reload_tables()` clears the cache; in the app this is the sidebar 'Reload tables' button, and a push to GitHub redeploys.
- Each file is validated against a Pydantic row model with exact header matching. Checks:
  - Keys are unique per table.
  - Bucket numbers run 1..n in file order, and bucket limits ascend within each year and status.
  - Rates are in 0–1, and money fields are ≥ 0. `AMT.End > Start`.
  - RMD factor ages are contiguous; `tblRMDStartAge` ascends and starts at 0.
  - Every `tblInputMap` field exists on `FilerInputs`; `Order` and `Field` are unique.
- Sentinel ceilings (≥ 9,999,999) are data. `is_unbounded()` detects them, and the UI shows 'No limit'.
- A top bracket that is not a sentinel produces a warning (none currently).
- Failures raise `TableValidationError`; the app shows the errors instead of crashing.
- `supported_years()` returns the years present in every table a calculation needs.

## 5. Function mapping (Excel → Python, as built)
| Excel | Python | Notes |
|---|---|---|
| `RMD` | `rmd.calc_rmd`, `rmd.start_age` | Uses `tblUniformRMDFactors`, `tblRMDStartAge` |
| `TaxRate` / `TaxRateLTCG` | `ordinary.get_brackets` | Returns brackets with lower bound, limit, rate |
| Ordinary estimator `G12:M18` | `ordinary.allocate`, `ordinary.total_tax` | |
| `IncomeTax` | `ordinary.income_tax` | Year-filtered (spec §7.1 fix) |
| `LTCGTax` | `ltcg.ltcg_tax` | Stand-alone, year-filtered (spec §7.2 fix) |
| `LTCG_Bucket_Amount` | `ltcg.bucket_amount`, `ltcg.stacked` | |
| `LTCG_Rate` | `ltcg.marginal_rate` | Returns `None` when no bracket matches |
| `StandardDeduction_Basic` / `_Full` | `deductions.standard_deduction_basic` / `_full` | Constants from `tblParameters` |
| `SS_Taxable` | `socialsec.taxable_ss` | |
| `NII_Buildup`, `NIIT_Threshold`, `NIIT_Tax` | `niit.nii_buildup`, `niit_threshold`, `niit_tax` | |
| `AMT_ExemptionRate`, `AMT_Exemption`, `AMT_Tax`, `AMT_Owed` | `amt.exemption_rate`, `exemption`, `tentative_tax`, `amt_owed` | `stacked=True` taxes gains at 0/15/20%; plus `salt_cap`, `salt_addback` |
| Sheet formulas C6…M43 | `engine.compute` → `TaxResult` | Returns every intermediate and the bracket allocations |

`RMDOLD` is not ported (legacy definition with embedded factors).

### 5.1 Calculation order in `engine.compute` (from spec §5.2)
1. RMD (`C6`). The distribution income is `C9 = C6`.
2. Preferential subtotal (`C20`) = LT gains + loss carryover + qualified dividends.
3. Taxable SS (`C21`) = `SS_Taxable(SSI, other income)`. Other income is `SUM(C13:C19)` plus IRA conversion; default mode also adds the RMD.
4. AGI (`C22`) = RMD + taxable SS + conversion + ST + wages + LT + interest + ordinary dividends + addl income + carryover.
5. Medical threshold (7.5% AGI) and cash limit (60% AGI).
6. Standard deduction (`C28`). Applicable deduction (`C31`) = `max(min(SchedA + QBI, cashLimit), std)`.
7. Adjusted taxable income (`C33`) = AGI − deduction. Ordinary income (`C34`) = AGI − preferential subtotal. Taxable ordinary (`C35`) = `max(ordinary − deduction, 0)`. Taxable preferential (`C36`) = LT + QD + carryover − `max(0, deduction − ordinary)`.
8. Ordinary tax from bracket allocation. LTCG tax from stacked `bucket_amount` × rate.
9. NII = interest + ordinary dividends + (ST + LT + carryover). NIIT is computed from AGI.
10. AMT, using the SALT cap from `tblAMT` and `min(SchedA SALT, cap)`.
11. Total = regular + NIIT + AMT. Due/(refund) = total − paid. Effective % = total / AGI.

## 6. Web app (Streamlit)
Entry point: `streamlit_app.py`. Streamlit reruns the script on each interaction; widget state lives in `st.session_state` under keys `in_<field>` (plus `has_<field>` checkboxes for optional inputs), and the engine is a pure function of that state.

**Layout (since 0.5.0)**
- **Header band:** sticky, full width, navy with a bronze rule; the shield, product name and tagline.
- **Sidebar (navy):** the 'Inputs' heading, then the panel 'Scenario: import / export' (uploader and the 'Export scenario (JSON)' button), the panel 'Options' (legacy mode, 'Reload tables'), then one collapsible light-blue panel per `tblInputMap` Group: Filer, Retirement, Investments, Other income, Deductions, AMT, Payments. The first group starts open. Fields appear in `Order` order within their group.
- **Main area:** an editable report title ('Add a client name'), the tax year and last-updated date, then three tabs.
- **Footer:** disclosure and the application version.

**Tabs**
- **Results:** two rows of headline metrics (total tax, amount due or refund, effective rate of AGI, marginal ordinary rate; AGI, taxable ordinary income, RMD, standard deduction), engine warnings, the 'Download PDF report' button, expandable result sections and the ordinary and LTCG bracket tables.
- **Tables:** any loaded CSV (sentinel limits shown as 'No limit').
- **Status:** validation result, application version, supported years, workbook baseline, table warnings.

**Tooltips.** Every input has a tooltip (the '?' icon) from `app/input_help.py`, keyed by field name. Optional inputs (spouse DOB, Schedule A SALT) show it on their check box and on the value field. Tests fail if an input lacks a tooltip, if a tooltip refers to an unknown field, or if a widget in the running app does not show its tooltip.

**Optional inputs.** Spouse DOB and Schedule A SALT are optional (a blank SALT differs from zero). The tax year defaults to the current year if supported, otherwise the latest.

**Branding.** Colours, fonts and logo files come from `brand/fga_brand.json`; CSS is generated by `app/branding.py`. Headings and large figures use Playfair Display; everything else uses Source Sans 3 (loaded from Google Fonts). Logo files named `*_navy` are for navy surfaces, `*_cream` for off-white surfaces, and `ribbon_white` is used on the PDF. The sidebar and header styles follow the FGA forecaster app.

**Saved scenarios (removed in 0.5.0).** The Save, Load and Delete controls were removed because Community Cloud wipes local disk on restart. Exported JSON files are the way to keep a scenario. `scenario_store.py` and its tests remain in the code, unused.

**PDF report (`pdf_report.py`):** logo, title, tax year and status, last-updated and generated times, headline figures, warnings, result sections, both bracket tables, the scenario inputs grouped as in the form, a planning-use disclaimer, and page numbers.

- Display rules: currency `$#,##0`, rates as percentages.

Not in scope for Streamlit: REST endpoints and a token-protected admin reload. If an API is needed later, `engine.compute` can be wrapped in FastAPI unchanged.

## 7. Known workbook defects: status
`engine.compute(..., legacy=True)` reproduces the workbook; the default `legacy=False` applies the fixes marked below.

| # | Issue | Status |
|---|---|---|
| 1 | Installed `IncomeTax`/`LTCGTax` don't filter by year | Fixed |
| 2 | 2026 has no 37% bracket row | Fixed (row added, sourced from Rev. Proc. 2025-32). Legacy mode keeps the workbook's six-row estimator and warns above its top row. |
| 3 | RMD table covers only 73–100 | Fixed (ages 72–120 from Pub. 590-B). Ages above 120 still raise an error; the workbook used a divisor of 2. |
| 4 | Std-deduction add-ons use the current year, not the tax year | Fixed in default mode |
| 5 | Status coverage inconsistent | Aliases done. `Separate` is still unsupported for ordinary, LTCG and standard-deduction tables (no rows). |
| 6 | Social Security provisional income excludes the RMD and tax-exempt interest | Partly fixed: default mode includes the RMD. There is still no tax-exempt-interest input. |
| 7 | AMT taxes all capital gains at a flat 15% | Fixed in default mode (stacked 0/15/20%) |
| 8 | Division by zero (`D21`, `J27`, `M43`) | Fixed in both modes (returns `None`) |
| 9 | NIIT can go negative | Fixed in default mode |
| 10 | `C33`, `C36` not clamped | Fixed in default mode |
| 11 | QBI field meaning unclear | Open. Kept as in the workbook. The tooltip says so. |
| 12 | Broken names (`IRABalance`, `RMDage`, `RMDFactor`, `tblRMDFactors`) | Dropped. The Excel import ignores them. |

Other differences between legacy and default mode: a blank Schedule A SALT counts as the full cap in legacy mode and as zero (with a warning) in default mode; legacy mode limits the ordinary estimator to six rows and the LTCG estimator to three; legacy mode takes the age year from the current date.

## 8. Testing
**Golden test** (`tests/test_golden_workbook.py`; workbook as saved: MFJ, 2026, DOB 1952-04-14, spouse 1974-09-30). Inputs: IRA prior-YE 1,000,000; qualified dividends 1,800; interest 900; ordinary dividends 2,400; ST −3,000; wages 145,000; LT 6,000; Sch A 12,000; withheld 16,500. Legacy mode with the as-of year fixed at 2026 reproduces:

| Output | Expected |
|---|---|
| RMD | 39,215.69 |
| AGI | 190,515.69 |
| Standard deduction | 37,419 |
| Adjusted taxable income | 153,096.69 |
| Taxable ordinary | 145,296.69 |
| Taxable LTCG | 7,800 |
| Ordinary tax | 21,389.27 |
| LTCG tax | 1,170 |
| Total tax | 22,559.27 |
| NII | 6,300 (NIIT 0, below 250k) |
| AMT tax / owed | 12,999.14 / 0 |
| Due | 6,059.27 |
| Effective % of AGI | 11.84% |

Default mode gives the same total tax. Its tentative AMT is 1,325.14 because gains are stacked at 0/15/20% and a blank SALT counts as zero.

**Other tests (exist):**
- Table loader and validator: duplicate keys, unsorted buckets, header mismatches, missing files, invalid values, missing top bracket.
- One file per calculation module, with boundary cases; property tests (hypothesis).
- `test_phase3.py`: 2026 and 2027 tax amounts against the Rev. Procs., 2027 LTCG, AMT and NIIT tables, stacked AMT gains, RMD in provisional income.
- Scenario JSON: round trip, BOM, unknown names, bad types, schema version, every-error-at-once. Saved scenarios (module only): save, list, load, delete, overwrite, unsafe names, corrupt files.
- PDF: valid file, key figures and inputs present, markup characters in titles, warnings, multiple pages, optional logo.
- Form state, report formatting, input map, key performance figures; Streamlit AppTest smoke tests (skipped if Streamlit is not installed).
- Branding: brand file merge, CSS selectors, heading and body fonts, navy sidebar with light-blue cards, header and footer HTML, theme file matches the brand file, logo files exist.
- Excel import (`test_excel_import.py`, `test_excel_values.py`, `test_excel_aliases.py`): names, sheet-level names, address fallback, old names, priority order, case-insensitivity, blank and unusable cells, metadata, bad files, and a round trip through `scenario_io.import_scenario`.
- Tooltips (`test_input_help.py`), versioning (`test_version.py`) and documentation (`test_docs.py`).

**Manual checks still to do:**
1. In the app, enter the golden case, turn on legacy mode, and confirm total tax $22,559 and amount due $6,059. Then switch to tax year 2027 and confirm it calculates.
2. Export, reload, import, and confirm every field is restored. Upload `TaxRetirementOptimizer.xlsx` and confirm the forms fill (15 inputs filled and 6 blank for the saved workbook). Download the PDF and open it.
3. Run the xlwings export and import against the real workbook (section 12.6).
4. Upload a workbook that still has the old names, if one exists, and confirm the 'old input names' notice.

## 9. Phases and deliverables
| Phase | Scope | Status |
|---|---|---|
| 0 | Repo skeleton, CSVs, loader, validator, CI, Streamlit skeleton | Done |
| 1 | Pure calc modules, `legacy=True` engine | Done |
| 2 | Inputs form, results page, scenario JSON import/export (web + xlwings) | Committed; manual checks pending |
| 3 | 2027 data, 2026 top bracket, RMD ages, stacked AMT gains, RMD in SS income | Committed |
| 4 | PDF report, saved scenarios (local folder) | Committed; saved-scenarios UI removed in 0.5.0 |
| 5 | Release 0.5.0: brand layout, Excel template upload with old-name aliases, tooltips, versioning, documentation | Done on `test`; pending merge |
| 6 (proposed) | Separate status; tax-exempt interest input; QBI clarification; durable storage only if wanted | Needs the decisions in section 11 |

## 10. Annual maintenance (no code change)
1. Append the new year's rows to each CSV in `data/`, with a full set across all dependent tables (`tblParameters`, `tblStandDeductionBase`, `tblAMT`, `tblNIIT`, `tblTaxRate`, `tblTaxRateLTCG`). Use the IRS revenue procedure for the year.
2. Add the year's tests to `tests/test_phase3.py`: tax at each bracket top from the Rev. Proc.'s own table.
3. Run `python scripts/validate_tables.py`. CI runs it on every push.
4. Add a MINOR version entry to `CHANGELOG.md` and update the version (section 14).
5. Push to GitHub. Community Cloud redeploys; use 'Reload tables' if the app is already running.

## 11. Open questions for the owner
1. **Separate (MFS) status:** in scope? It needs MFS rows in the ordinary, LTCG and standard-deduction tables and a decision on the Separate column of `tblParameters`.
2. **Durable scenario storage:** resolved for now. The saved-scenarios feature was removed; exported JSON files are the record. Reopen only if server-side storage is wanted.
3. **Client data and access control:** will real client data be entered in the hosted app? If so, decide on access control before first use. Exported JSON and PDF files contain client data and need secure handling.
4. **Tax-exempt interest:** add an input? It needs a workbook cell and an `inp...` name.
5. **2027 SALT cap:** verify 40,804 (20,402 separate) against a source.
6. **Workbook cells:** in the saved workbook `version!B12` and `version!B13` are empty, so they can hold the report title and last-updated date. Cell `A13` already holds the versioning-scheme note, so do not put labels in A12 and A13 as section 12.7 first suggested; the script only needs the B cells.
7. **Streamlit Community Cloud:** is another private app already using the one-private-app slot?
8. **Local Python:** a traceback from your machine showed Python 3.14; the project targets 3.11+ and Streamlit Cloud is set to 3.12. Use a 3.12 environment if any install fails.
9. **Branch protection:** on a private repository on the free GitHub plan, rulesets and branch protection are not enforced. The rule that changes go to `test` and are merged by the owner is a convention. A paid plan or a separate development repository would enforce it.
10. **Version 1.0.0:** declare it once the manual checks in section 8 pass.

## 12. Scenario JSON import/export

### 12.1 Purpose
One JSON file carries every editable input of a scenario between Excel and the web app. The same file is produced and consumed by both. It holds the `inp...` named-range inputs as ordered name/value pairs, plus a report title and a last-updated date. Schedule709 is out of scope.

### 12.2 File format (schemaVersion 1.0)
```json
{
  "schemaVersion": "1.0",
  "reportTitle": "Maxwell 2026 Roth Conversion Study",
  "lastUpdated": "2026-11-16T18:53:00",
  "workbookVersion": "2026.3.0",
  "inputs": [
    {"name": "inpTaxYear", "value": 2026},
    {"name": "inpFilingStatus", "value": "Jointly"},
    {"name": "inpDateOfBirth", "value": "1952-04-14"},
    {"name": "inpSpouseDateOfBirth", "value": "1974-09-30"},
    {"name": "inpPriorYearEndIRABalance", "value": 1000000},
    {"name": "inpAdditionalIncome", "value": null}
  ]
}
```
Rules:
- `inputs` is an ordered array of `{name, value}` pairs. Order follows `data/tblInputMap.csv`.
- `reportTitle` is a required string, 1–200 characters. `lastUpdated` is a required ISO 8601 local timestamp; the exporter sets it to the time of export.
- Dates are `YYYY-MM-DD` strings. Money is a plain number. A blank cell is `null`.
- Only editable input cells are exported. An importer skips any pair whose target is a formula.
- Unknown names, unsupported tax years and unrecognized filing statuses are ignored with a warning. Names missing from the file leave the current value unchanged. Type errors reject the file, and all errors are reported together.
- Files are UTF-8 without a BOM; readers tolerate one.

### 12.3 Input map (external CSV, not in code)
`data/tblInputMap.csv` (21 rows) defines the pairs, their order, the Excel fallback address, the type (`int`, `text`, `date`, `money`), the Python field on `FilerInputs`, and the form `Label` and `Group`.

Notes:
- Rows 1–3 and 5–19 are existing `inp...` names in the workbook spec.
- `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42) and `inpAdditionalTax` (C43) are recommended names the workbook does not have yet. Both the xlwings script and the Excel upload fall back to the `Cell` column.
- `inpScheduleADeductions`, `inpIRAConversion`, `inpSocialSecurityBenefits` and `inpShortTermCapitalGainLoss` are sheet-scoped to `TaxSheetSingle`; the script and the upload resolve names through that worksheet.
- `C9` (RMD) is a formula, so it is not an input and is not in the file.

### 12.4 Python components (built)
- `scenario_io.export_scenario(inputs, title, tables, ...)` and `scenario_io.import_scenario(text, tables)`; the `ScenarioFile` Pydantic model validates the structure.
- `form_state.read_state`, `apply_import`, `init_state`: translate between widget state and `FilerInputs`.
- Streamlit: `st.download_button` for export, `st.file_uploader` for import (JSON or Excel), an editable report title, and the last-updated date shown on the Results page and in the PDF.

### 12.5 Tests (built)
Round trip, BOM-prefixed file, unknown names, invalid types and dates, missing or blank title, bad schema version, optional inputs, and form-state application. The Excel-side round trip (workbook → JSON → web → JSON → workbook) is still to be run by hand.

### 12.6 Excel integration: xlwings (replaces VBA)
`excel/scenario_xlwings.py` reads and writes the input cells in the open workbook. It needs Excel and Python on the machine (`pip install -e '.[excel]'`). It runs locally only and is not part of the hosted app.

```
python excel/scenario_xlwings.py export --file scenario.json --title 'Maxwell 2026 Roth Conversion Study'
python excel/scenario_xlwings.py import --file scenario.json
```
- `--book PATH` targets a specific workbook; otherwise the active workbook is used.
- The input list, order and cell fallbacks come from `data/tblInputMap.csv`; there is no second copy of the map.
- Export converts each cell by type (`app/excel_values.py`), lists unusable cells under `problems`, and writes the title and timestamp into the workbook only after the JSON file is saved.
- Formula cells are never overwritten on import and are listed in the summary. A `null` clears the cell. The workbook recalculates after an import.
- The script has not yet been run end to end against Excel.

### 12.7 Workbook changes required
- Use two metadata cells on the `version` sheet: `B12` (report title, name `inpReportTitle`) and `B13` (last updated, name `inpLastUpdated`). Both are empty in the saved workbook. Do not use A12 or A13 for labels: A13 holds the versioning-scheme note. The script and the upload use the cell addresses if the names do not exist.
- Optionally create the names `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42), `inpAdditionalTax` (C43).
- No other layout or formula changes. The workbook's own tables lack the 2027 rows and the 2026 top bracket added here; the CSVs are the source of truth for those.

### 12.8 Excel template upload (web app)
`app/excel_import.py` converts an uploaded `.xlsx` or `.xlsm` file to scenario JSON in memory, then loads it with the same validation as a JSON import. It uses openpyxl, so no copy of Excel is needed and it works on Community Cloud.
- Reads the saved cell values (not formulas). The file must have been saved in Excel after calculation.
- Reads only the sheet `TaxSheetSingle`; the `version` sheet supplies the workbook version (`B4`), the optional title (`B12`) and the last-updated time (`B13`). With no title, the file name is used (underscores and hyphens become spaces).
- Locating an input: its current name (workbook-wide, then sheet-level), then its old names (12.9), then the fixed address from `tblInputMap`. Names are matched without regard to case. A name that points to a range or to a broken reference is skipped.
- Cell values are converted by input type (`app/excel_values.py`): dates (date cells or Excel serial numbers), integers, money and text. A value that cannot be converted becomes blank and is reported.
- Messages: how many inputs were filled and blank; whether old names were used; which named inputs were read by address. Inputs that never had a name (spouse DOB, tax withheld, additional tax) are read by address without a notice.
- Limits: 25 MB; `.xls` and password-protected files are rejected with a message.
- Verified against the saved workbook: 15 inputs filled and 6 blank (additional income, capital loss carryover, qualified business income, Schedule A SALT, AMT other preferences, additional tax paid).

### 12.9 Old named ranges (aliases)
The 2026 naming-convention migration (workbook specification section 4) renamed 34 named ranges and removed the old names. `excel/input_name_aliases.csv` (columns `Name,Alias,Note`) maps each current input name to its old name so older workbooks still upload. The 18 pairs come from the migration dictionary in the workbook specification: year, status, DOB, priorIRAbal, SSI, RothConv, QualDivs, TaxableInt, OrdDivs, AddlIncome, STcapgain, wages, LTcapgains, losscarry, Deductions, QualBusinessInc, SALTschedA, OtherPreferences.
- Current names always win; old names are tried in file order; then the cell address.
- An input can have several old names: add another row with the same `Name`. Lines starting with `#` are ignored.
- `IRABalance` is deliberately not aliased: the specification found it broken and did not assume it equals `priorIRAbal`.
- Tests check that every aliased name exists in `tblInputMap.csv`, that no old name maps to two inputs, and that no old name equals a current name.

## 13. Hosting on Streamlit Community Cloud
**Deploy steps**
1. The repo is on GitHub. You need admin rights on it, and Streamlit needs authorization for private repos.
2. At share.streamlit.io, create an app: repo, branch `main`, main file `streamlit_app.py`.
3. In Advanced settings choose Python 3.12. The Python version cannot be changed later without deleting and redeploying the app.
4. Deploy. Every push to `main` redeploys.

**Dependencies:** Community Cloud installs from `requirements.txt` (`pydantic`, `streamlit`, `reportlab`, `openpyxl`). `xlwings` is local-only and deliberately left out.

**Access and privacy**
- A private-repo app is private by default: only invited viewers (by email) can open it. Community Cloud allows one private app at a time.
- Do not enter real client identifiers or account data until access control is decided (open question 3).

**Behavior to design around**
- Files written to the app's local disk are lost on restart. The app therefore keeps nothing: export scenarios as JSON files.
- The app reads `data/*.csv` from the repo. CSV changes take effect on redeploy or after 'Reload tables'.
- Table validation failures do not stop the deploy. The app shows the errors, and CI flags them on the push.

## 14. Versioning and releases
**Scheme.** Semantic Versioning, MAJOR.MINOR.PATCH, starting at 0.x until the owner declares 1.0.0 (open question 10). The Excel workbook keeps its own YYYY.MAJOR.MINOR scheme (currently 2026.3.0); the app records the workbook version its calculations were built from in `app/version.py` (`WORKBOOK_BASELINE`).

**Where the version lives.** `app/version.py` (`__version__`, the source of truth), `pyproject.toml`, the heading for the version in `CHANGELOG.md`, and the header of this document. `tests/test_version.py` fails if they disagree. The version is shown in the app footer and on the Status tab.

**Rules**
- PATCH: bug fixes, tooltip and documentation text.
- MINOR: new features, a new tax year, a calculation change (state the effect on results in the changelog).
- MAJOR (after 1.0.0): a breaking change to the scenario JSON schema or removal of a feature. The JSON `schemaVersion` is separate and changes only when the file format changes.

**Release steps.** Update the four places, add the changelog entry, run `python -m pytest -q` and `python scripts/validate_tables.py`, merge the pull request from `test` to `main`, then tag the release (`git tag v0.5.0`, `git push origin v0.5.0`).

**History.** Versions 0.0.1 to 0.4.0 are labels applied afterwards to phases 0 to 4; see `CHANGELOG.md`.

## 15. Development workflow
- `main` is deployed. Changes are made on branch `test` and reach `main` through a pull request that the owner merges. The AI assistant used on this project pushes only to `test`.
- On a private repository on the free GitHub plan, branch protection and rulesets are not enforced (open question 9), so this is a convention.
- Developer details: `docs/ARCHITECTURE.md`.
