# TaxRetirementOptimizer → Python Web App (Streamlit)
Source: TaxRetirementOptimizer.xlsx v2026.3.0 + TaxRetirementOptimizer-Specification.md
Owner: Robert Maxwell
Last updated: 2026-11-16 (Phases 0–2 committed; Phase 3 next)

## 0. Status at a glance
| Phase | Scope | Status |
|---|---|---|
| 0 | Repo skeleton, CSV tables, loader/validator, CI, Streamlit skeleton | Done |
| 1 | Calculation modules and engine, golden workbook test | Done. Legacy mode matches the saved workbook to the cent. |
| 2 | Streamlit inputs form, results page, scenario JSON import/export, xlwings script | Committed. Needs the manual golden-case check in the app (section 8) and a first Excel run of the xlwings script. |
| 3 | Fix remaining defects, more years/statuses, stacked AMT LTCG | Next |
| 4 | Saved scenarios (external storage), PDF report | Not started |

Open before first real use: first Streamlit Community Cloud deploy, the two missing data items in section 11, and the access-control decision for client data.

## 1. Goals and non-goals
**Goals**
- Reproduce the `TaxSheetSingle` estimate (ordinary tax, LTCG, NIIT, AMT, RMD, taxable Social Security, standard deduction, due/refund) as a Streamlit web app hosted on Streamlit Community Cloud.
- All tax-table data lives in external CSV files in `data/`. No table values are embedded in code.
- The 17 named LAMBDAs become pure Python functions with unit tests.
- The workbook's current outputs are the golden regression test.
- A scenario JSON file (ordered name/value pairs of the `inp...` named input cells, report title, last-updated date) moves scenarios between Excel and the web app (section 12).

**Non-goals**
- Validating current tax law. The spec is an as-built description, not a law check.
- Schedule709 (Form 709 gift/GST grid): out of scope, will not be converted, imported or exported.

## 2. Stack
| Layer | Choice | Reason |
|---|---|---|
| Web | Streamlit (Community Cloud) | Deploys straight from GitHub, no server to manage |
| Validation | Pydantic v2 | Typed input and CSV-row models |
| Math | `decimal.Decimal` for money and rates | Avoid float drift |
| Data | CSV via stdlib `csv` | Tables stay editable in Excel |
| Excel bridge | xlwings (Python, local only) | Reads/writes the named input cells and exchanges scenario JSON; no VBA |
| Tests | pytest, hypothesis, Streamlit AppTest | Golden case, edge cases, property tests, UI smoke tests |
| Packaging | `requirements.txt` for hosting, `pyproject.toml` for dev | Community Cloud installs from `requirements.txt` |

## 3. Repository layout (current)
```
├─ streamlit_app.py              # Streamlit entry point (Community Cloud main file)
├─ requirements.txt              # hosting dependencies (pydantic, streamlit)
├─ pyproject.toml                # dev install and extras (app, excel, dev)
├─ data/                         # EXTERNAL TABLES (edit without touching code)
│  ├─ tblTaxRate.csv, tblTaxRateLTCG.csv
│  ├─ tblUniformRMDFactors.csv, tblRMDStartAge.csv
│  ├─ tblStandDeductionBase.csv, tblAMT.csv, tblNIIT.csv
│  ├─ tblStatusAliases.csv       # status normalization
│  ├─ tblParameters.csv          # constants hard-coded in the LAMBDAs
│  └─ tblInputMap.csv            # input names, cells, types, fields, UI labels and groups
├─ app/
│  ├─ config.py, models.py, tables.py   # settings, Pydantic models, CSV loader and validators
│  ├─ status.py                  # normalize_status() via tblStatusAliases
│  ├─ scenario_io.py             # scenario JSON export/import and validation
│  ├─ form_state.py              # Streamlit widget-state helpers (pure functions)
│  ├─ report.py, display.py      # result and table formatting (no Streamlit import)
│  └─ calc/
│     ├─ common.py               # Decimal helpers, errors, parameter lookup
│     ├─ ordinary.py, ltcg.py    # bracket lookup/allocation; stacked LTCG
│     ├─ rmd.py, deductions.py, socialsec.py, niit.py, amt.py
│     └─ engine.py               # compute(inputs, tables, legacy, as_of_year) -> TaxResult
├─ excel/scenario_xlwings.py     # Excel <-> scenario JSON via xlwings
├─ scripts/validate_tables.py    # CLI check, also run in CI
├─ tests/                        # one test file per module, plus test_golden_workbook.py
└─ .github/workflows/ci.yml      # validate tables, then pytest
```
The repository root also holds the original workbook, the specification, `README.md`, `assets/` and `brand/`.

## 4. External CSV tables
The CSV files in `data/` are the source of truth; this plan does not copy their contents. File name = Excel table name, and column headers are kept verbatim, including `FilingYear` in `tblStandDeductionBase`. Values were copied from the workbook.

Notes on specific tables:
- `tblUniformRMDFactors.csv` covers ages 73–100, exactly as in the workbook. Ages outside the table raise a clear error.
- `tblRMDStartAge.csv` (new) holds the RMD start age by birth year (72, 73, 75), replacing the cutoffs hard-coded in the workbook formula.
- `tblStatusAliases.csv` (new) replaces the inconsistent status string checks in the LAMBDAs.
- `tblParameters.csv` (new) holds constants the LAMBDAs hard-code (Social Security bases, age add-ons, senior bonus, NIIT rate, AMT flat LTCG rate, deduction limits). The Separate column is a placeholder; confirm it.
- `tblInputMap.csv` (new) has columns `Order,Name,Cell,Type,Field,Label,Group` (section 12.3).

### 4.1 Loader and validation rules (`tables.py`)
- Load once and cache. `reload_tables()` clears the cache; in the app this is the sidebar "Reload tables" button, and a push to GitHub redeploys.
- Each file is validated against a Pydantic row model with exact header matching. Checks:
  - Keys are unique per table.
  - Bucket numbers run 1..n in file order, and bucket limits ascend within each year and status.
  - Rates are in 0–1, and money fields are ≥ 0. `AMT.End > Start`.
  - RMD factor ages are contiguous; `tblRMDStartAge` ascends and starts at 0.
  - Every `tblInputMap` field exists on `FilerInputs`; `Order` and `Field` are unique.
- Sentinel ceilings (≥ 9,999,999) are data. `is_unbounded()` detects them, and the UI shows "No limit".
- A top bracket that is not a sentinel produces a warning (currently the 2026 ordinary table).
- Failures raise `TableValidationError`; the app shows the errors instead of crashing.
- `supported_years()` returns the years present in every table a calculation needs (currently 2026 only).

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
| `AMT_ExemptionRate`, `AMT_Exemption`, `AMT_Tax`, `AMT_Owed` | `amt.exemption_rate`, `exemption`, `tentative_tax`, `amt_owed` | Plus `amt.salt_cap`, `amt.salt_addback` |
| Sheet formulas C6…M43 | `engine.compute` → `TaxResult` | Returns every intermediate and the bracket allocations |

`RMDOLD` is not ported (legacy definition with embedded factors).

### 5.1 Calculation order in `engine.compute` (from spec §5.2)
1. RMD (`C6`). The distribution income is `C9 = C6`.
2. Preferential subtotal (`C20`) = LT gains + loss carryover + qualified dividends.
3. Taxable SS (`C21`) = `SS_Taxable(SSI, sum(C13:C19) + IRA conversion)`.
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

- **Inputs tab:** form generated from `tblInputMap.csv`, grouped by its `Group` column. Spouse DOB and Schedule A SALT are optional (a blank SALT differs from zero).
- **Results tab:** report title, tax year and status, last-updated time, headline metrics (total tax, amount due or refund, effective rate), engine warnings, expandable result sections, and ordinary and LTCG bracket tables.
- **Tables tab:** any loaded CSV, with sentinel limits shown as "No limit".
- **Status tab:** validation result, supported years, table warnings.
- **Sidebar:** scenario import (`st.file_uploader`) and export (`st.download_button`), legacy-mode toggle, "Reload tables".
- Display rules: currency `$#,##0`, rates as percentages.

Not in scope for Streamlit: REST endpoints and a token-protected admin reload. If an API is needed later, `engine.compute` can be wrapped in FastAPI unchanged.

## 7. Known workbook defects: status
`engine.compute(..., legacy=True)` reproduces the workbook; the default `legacy=False` applies the fixes marked below.

| # | Issue | Status |
|---|---|---|
| 1 | Installed `IncomeTax`/`LTCGTax` don't filter by year | Fixed (year-filtered functions) |
| 2 | 2026 has no 37% bracket row | Open data item. The engine and table loader warn when income exceeds the top bracket. |
| 3 | RMD table covers only 73–100 | Open data item. Ages outside the table raise a clear error. |
| 4 | Std-deduction add-ons use `TODAY()` year | Fixed in default mode (uses the tax year); legacy mode keeps today's year |
| 5 | Status coverage inconsistent | Aliases done. `Separate` is still unsupported for ordinary, LTCG and standard-deduction tables (no rows). |
| 6 | SS provisional income excludes the RMD; no tax-exempt-interest input | Open. Decide before Phase 3. |
| 7 | AMT uses flat 15% on LTCG | Open (Phase 3: stacked 0/15/20%) |
| 8 | Division by zero (`D21`, `J27`, `M43`) | Fixed in both modes (returns `None`) |
| 9 | NIIT can go negative | Fixed in default mode; legacy mode keeps the workbook behavior |
| 10 | `C33`, `C36` not clamped | Fixed in default mode |
| 11 | QBI field semantics unclear | Open. Kept as in the workbook. |
| 12 | Broken names (`IRABalance`, `RMDage`, `RMDFactor`, `tblRMDFactors`) | Dropped |

Also differs from the workbook: a blank Schedule A SALT counts as the full cap in legacy mode and as zero (with a warning) in default mode; the workbook's divisor of 2 at ages 120+ is not ported; legacy mode limits the ordinary estimator to six rows and the LTCG estimator to three.

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

Default mode gives the same total tax; only the AMT intermediate differs (blank SALT counts as zero).

**Other tests (exist):**
- Table loader and validator: duplicate keys, unsorted buckets, header mismatches, missing files, invalid values.
- One file per calculation module, with boundary cases.
- Property tests (hypothesis): tax is non-decreasing in income; allocations sum to income.
- Scenario JSON: round trip, BOM, unknown names, bad types, schema version, every-error-at-once.
- Form state, report formatting, input map.
- Streamlit AppTest smoke tests (skipped if Streamlit is not installed).

**Manual check still to do in the app:** enter the golden case, turn on legacy mode, and confirm total tax $22,559 and amount due $6,059. Then export, reload, import, and confirm every field is restored.

## 9. Phases and deliverables
| Phase | Scope | Done when |
|---|---|---|
| 0 | Repo skeleton, CSVs, loader, validator, CI, Streamlit skeleton | Done |
| 1 | Pure calc modules, `legacy=True` engine | Done: golden test passes to the cent |
| 2 | Streamlit inputs form, results page, scenario JSON import/export (web + xlwings) | Committed; done when the manual check above passes and the xlwings round trip runs in Excel |
| 3 | Remaining fixes (§7 #6, #7, #11), 2027 data, Separate status support, tests for each | 2027 loads by CSV edit only |
| 4 | Saved scenarios (external storage), PDF report | As prioritized |

## 10. Annual maintenance (no code change)
1. Append the new year's rows to each CSV in `data/`, with a full set across all dependent tables (`tblParameters`, `tblStandDeductionBase`, `tblAMT`, `tblNIIT`, `tblTaxRate`, `tblTaxRateLTCG`).
2. Run `python scripts/validate_tables.py`. CI runs it on every push.
3. Push to GitHub. Community Cloud redeploys; use "Reload tables" if the app is already running.
4. Add a regression test for the new year.

## 11. Open questions for the owner
1. Is Separate (MFS) status in scope? It needs rows in the ordinary, LTCG and standard-deduction tables.
2. Source for the 2026 37% ordinary bracket and the missing RMD ages (72, 101–120), as sourced figures.
3. Confirm the Separate column of `tblParameters.csv`, which is a placeholder.
4. Social Security: should RMD and tax-exempt interest count toward provisional income (defect #6)?
5. Confirm `version!B12` and `version!B13` are empty so they can hold the report title and last-updated date (section 12.7).
6. Is another private app already using the one-private-app slot on Streamlit Community Cloud?
7. Will real client data be entered in the hosted app? If so, decide on access control before first use.

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
- `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42) and `inpAdditionalTax` (C43) are recommended names the workbook does not have yet. The xlwings script falls back to the `Cell` column.
- `inpScheduleADeductions`, `inpIRAConversion`, `inpSocialSecurityBenefits` and `inpShortTermCapitalGainLoss` are sheet-scoped to `TaxSheetSingle`; the script resolves every name through that worksheet.
- `C9` (RMD) is a formula, so it is not an input and is not in the file.

### 12.4 Python components (built)
- `scenario_io.export_scenario(inputs, title, tables, ...)` and `scenario_io.import_scenario(text, tables)`; the `ScenarioFile` Pydantic model validates the structure.
- `form_state.read_state`, `apply_import`, `init_state`: translate between widget state and `FilerInputs`.
- Streamlit: `st.download_button` for export, `st.file_uploader` for import, an editable report title, and the last-updated date shown on the Results tab.

### 12.5 Tests (built)
Round trip, BOM-prefixed file, unknown names, invalid types and dates, missing or blank title, bad schema version, optional inputs, and form-state application. The Excel-side round trip (workbook → JSON → web → JSON → workbook) is still to be run by hand.

### 12.6 Excel integration: xlwings (replaces VBA)
`excel/scenario_xlwings.py` reads and writes the input cells in the open workbook. It needs Excel and Python on the machine (`pip install -e ".[excel]"`). It runs locally only and is not part of the hosted app. It has not yet been run against Excel.

```
python excel/scenario_xlwings.py export --file scenario.json --title "Maxwell 2026 Roth Conversion Study"
python excel/scenario_xlwings.py import --file scenario.json
```
- `--book PATH` targets a specific workbook; otherwise the active workbook is used.
- The input list, order and cell fallbacks come from `data/tblInputMap.csv`; there is no second copy of the map.
- Formula cells are never overwritten on import and are listed in the summary. A `null` clears the cell. The workbook recalculates after an import.

### 12.7 Workbook changes required
- Add two metadata cells on the `version` sheet (rows 12–13 are free per the spec layout; confirm): `A12` "Report Title" with `B12` named `inpReportTitle`, and `A13` "Last Updated" with `B13` named `inpLastUpdated`. The script uses the cell addresses if the names do not exist.
- Optionally create the names `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42), `inpAdditionalTax` (C43).
- No other layout or formula changes.

## 13. Hosting on Streamlit Community Cloud
**Deploy steps**
1. The repo is on GitHub. You need admin rights on it, and Streamlit needs authorization for private repos.
2. At share.streamlit.io, create an app: repo, branch `main`, main file `streamlit_app.py`.
3. In Advanced settings choose Python 3.12. The Python version cannot be changed later without deleting and redeploying the app.
4. Deploy. Every push to `main` redeploys.

**Dependencies:** Community Cloud installs from `requirements.txt` (`pydantic`, `streamlit`). `xlwings` is local-only and deliberately left out.

**Access and privacy**
- A private-repo app is private by default: only invited viewers (by email) can open it. Community Cloud allows one private app at a time.
- Do not enter real client identifiers or account data until access control is decided (open question 7).

**Behavior to design around**
- Files written to the app's local disk are lost on restart. Saved scenarios (phase 4) need external storage; until then scenarios are exported and imported as JSON files.
- The app reads `data/*.csv` from the repo. CSV changes take effect on redeploy or after "Reload tables".
- Table validation failures do not stop the deploy. The app shows the errors, and CI flags them on the push.
