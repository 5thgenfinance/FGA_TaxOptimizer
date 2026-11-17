# TaxRetirementOptimizer → Python Web App (Streamlit)
Source: TaxRetirementOptimizer.xlsx v2026.3.0 + TaxRetirementOptimizer-Specification.md
Owner: Robert Maxwell

## 1. Goals and non-goals
**Goals**
- Reproduce the `TaxSheetSingle` estimate (ordinary tax, LTCG, NIIT, AMT, RMD, taxable Social Security, standard deduction, due/refund) as a Streamlit web app hosted on Streamlit Community Cloud.
- All tax-table data lives in external CSV files in `data/`. No table values are embedded in code.
- The 17 named LAMBDAs become pure Python functions with unit tests.
- The workbook's current outputs become the golden regression test.
- A scenario JSON file (ordered name/value pairs of the `inp...` named input cells, report title, last-updated date) moves scenarios between Excel and the web app (section 12).

**Non-goals**
- Validating current tax law. The spec is an as-built description, not a law check.
- Schedule709 (Form 709 gift/GST grid): out of scope, will not be converted, imported or exported.

## 2. Stack
| Layer | Choice | Reason |
|---|---|---|
| Web | Streamlit (Community Cloud) | Deploys straight from GitHub, no server to manage |
| Validation | Pydantic v2 | Typed input and CSV-row models |
| Math | `decimal.Decimal` for money, `Decimal` rates | Avoid float drift |
| Data | CSV via stdlib `csv` | Tables stay editable in Excel |
| Excel bridge | xlwings (Python) | Reads/writes the named input cells and exchanges scenario JSON; no VBA |
| Tests | pytest + hypothesis (+ Streamlit AppTest) | Golden case, edge cases, property tests, UI smoke test |
| Packaging | `requirements.txt` for hosting, `pyproject.toml` for dev | Community Cloud installs from `requirements.txt` |

## 3. Repository layout
```
├─ streamlit_app.py              # Streamlit entry point (Community Cloud main file)
├─ requirements.txt              # hosting dependencies (pydantic, streamlit)
├─ pyproject.toml                # dev install and extras
├─ data/                         # EXTERNAL TABLES (edit without touching code)
│  ├─ tblTaxRate.csv
│  ├─ tblTaxRateLTCG.csv
│  ├─ tblUniformRMDFactors.csv
│  ├─ tblStandDeductionBase.csv
│  ├─ tblAMT.csv
│  ├─ tblNIIT.csv
│  ├─ tblStatusAliases.csv       # status normalization
│  ├─ tblParameters.csv          # constants hard-coded in the LAMBDAs
│  └─ tblInputMap.csv            # ordered input names, cells, types, fields
├─ app/
│  ├─ config.py                  # DATA_DIR, env settings
│  ├─ models.py                  # Pydantic: row models, FilerInputs
│  ├─ tables.py                  # CSV loader + validators + lookups
│  ├─ display.py                 # table display helpers (no Streamlit import)
│  ├─ scenario_io.py             # Phase 2: ScenarioFile model, JSON import/export
│  ├─ status.py                  # Phase 1: normalize_status()
│  └─ calc/                      # Phase 1
│     ├─ ordinary.py             # IncomeTax, TaxRate bracket allocation
│     ├─ ltcg.py                 # LTCGTax, LTCG_Bucket_Amount, LTCG_Rate
│     ├─ rmd.py
│     ├─ deductions.py           # StandardDeduction_Basic/Full
│     ├─ socialsec.py            # SS_Taxable
│     ├─ niit.py
│     ├─ amt.py
│     └─ engine.py               # orchestrates TaxSheetSingle logic
├─ excel/
│  └─ scenario_xlwings.py        # Excel <-> scenario JSON via xlwings
├─ scripts/validate_tables.py    # CLI check, also run in CI
├─ tests/
│  ├─ test_tables.py, test_display.py, test_streamlit_app.py   # exist
│  ├─ test_rmd.py, test_ordinary.py, test_ltcg.py, test_amt.py,
│  │  test_niit.py, test_socialsec.py, test_deductions.py       # Phase 1
│  ├─ test_scenario_io.py                                      # Phase 2
│  └─ test_golden_workbook.py                                  # Phase 1
└─ .github/workflows/ci.yml
```

## 4. External CSV tables
The CSV files in `data/` are the source of truth. This plan no longer copies their contents, so there is only one version to maintain.

Rule: file name = Excel table name, and the column headers are kept verbatim. This includes `FilingYear` in `tblStandDeductionBase`, which is not `Year`. Values were copied from the workbook.

Notes on specific tables:
- `tblUniformRMDFactors.csv` covers ages 73–100, exactly as in the workbook. The RMDOLD factors (72–120, spec §6.6) are only a reference for a later extension. Verify them against the IRS table before use.
- `tblStatusAliases.csv` is new. It replaces the inconsistent status string checks in the LAMBDAs.
- `tblParameters.csv` is new. It holds constants that the LAMBDAs hard-code (Social Security bases, age add-ons, senior bonus, NIIT rate, AMT flat LTCG rate, deduction limits). The Separate-status column is a placeholder; confirm it.
- `tblInputMap.csv` is new and is described in section 12.3.

### 4.1 Loader and validation rules (`tables.py`)
- Load once and cache. `reload_tables()` clears the cache. In Streamlit this is the sidebar "Reload tables" button; pushing to GitHub also redeploys the app.
- Each file is validated against a Pydantic row model with exact header matching. Checks:
  - Keys are unique: `(Year,Bucket)`, `Age`, `(FilingYear,Status)`, `(Year,Status)`, `Alias`, `(Year,Key)`, `Name`.
  - Bucket numbers run 1..n in file order, and bucket limits ascend within each year and status.
  - Rates are in 0–1, and money fields are ≥ 0.
  - `AMT.End > Start`.
  - RMD ages are contiguous.
  - Every `tblInputMap` field exists on `FilerInputs`, and `Order` and `Field` are unique.
- Sentinel ceilings (≥ 9,999,999) are data. `is_unbounded()` detects them, and the UI shows them as "No limit", never as statutory thresholds.
- A top bracket that is not a sentinel produces a warning (currently the 2026 ordinary table).
- Validation errors raise `TableValidationError`. The Streamlit app shows the errors on the Status tab instead of crashing.
- `supported_years()` returns the years present in every table a calculation needs (currently 2026 only).
- `scripts/validate_tables.py` runs the same checks in CI.

## 5. Function mapping (Excel → Python)
| Excel | Python module.function | Table / params used |
|---|---|---|
| `RMD` | `rmd.calc_rmd(dob, year, prior_bal)` | tblUniformRMDFactors |
| `TaxRate` / `TaxRateLTCG` | `ordinary.bracket(status, year, n)` | tblTaxRate / tblTaxRateLTCG |
| Ordinary estimator `G12:M18` | `ordinary.allocate(taxable_ord, status, year)` | tblTaxRate |
| `IncomeTax` / `LTCGTax` | `ordinary.income_tax`, `ltcg.ltcg_tax` | Year-filtered (documented fix, spec §7.1–7.2) |
| `LTCG_Bucket_Amount` | `ltcg.bucket_amount(...)` | none |
| `LTCG_Rate` | `ltcg.marginal_rate(...)` | tblTaxRateLTCG |
| `StandardDeduction_Basic` / `_Full` | `deductions.standard_deduction(...)` | tblStandDeductionBase + tblParameters |
| `SS_Taxable` | `socialsec.taxable_ss(...)` | tblParameters |
| `NII_Buildup`, `NIIT_Threshold`, `NIIT_Tax` | `niit.*` | tblNIIT, tblParameters |
| `AMT_ExemptionRate`, `AMT_Exemption`, `AMT_Tax`, `AMT_Owed` | `amt.*` | tblAMT |
| Sheet formulas C6…M43 | `engine.compute(inputs) -> TaxResult` | all |

Excel named cells map to `FilerInputs` fields through `data/tblInputMap.csv` (section 12.3).

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
10. AMT, using the SALT cap from tblAMT and `min(SchedA SALT, cap)`.
11. Total = regular + NIIT + AMT. Due/(refund) = total − paid. Effective % = total / AGI.

`TaxResult` returns every intermediate (bracket table, per-bucket tax, AMT steps) so the UI can show a line-by-line breakdown matching the sheet.

## 6. Web app (Streamlit)
Entry point: `streamlit_app.py`. Streamlit reruns the script on each interaction, so inputs live in `st.session_state` and the engine is a pure function.

Current skeleton (Phase 0):
- Report title field at the top.
- Sidebar "Reload tables" button (clears the cached tables and reruns).
- Status tab: validation result, table count, supported years, warnings (or the list of validation errors).
- Tables tab: select a table and view it with `st.dataframe`; sentinel limits show as "No limit".
- Scenario tab: placeholder plus the 21 fields defined in `tblInputMap.csv`.

Phase 2 additions:
- Inputs form built from `tblInputMap.csv` (year dropdown from `supported_years()`, filing status, DOBs, income, deductions, credits).
- Results panel with the line-by-line breakdown from `TaxResult`, headed by the report title and last-updated date.
- Scenario export: `st.download_button` serving the JSON file (stamps `lastUpdated`).
- Scenario import: `st.file_uploader` accepting the JSON, validating it with `scenario_io.py`, loading values into `st.session_state`, and listing warnings.
- Display rules: currency `$#,##0`, rates `0%`, sentinel limits "No limit".

Not in scope for Streamlit: REST endpoints (`/api/...`), a token-protected admin reload, and a separate JSON API. If an API is needed later, `engine.compute` can be wrapped in FastAPI without changing the calculation code.

Optional later: PDF export of the result, branded client report, saved scenarios (needs external storage; see section 13).

## 7. Known workbook defects: decide on each
These come from spec §8. The workbook's behavior and the intended behavior differ in several places.

| # | Issue | Proposed handling |
|---|---|---|
| 1 | Installed `IncomeTax`/`LTCGTax` don't filter by year | Implement the year-filtered version |
| 2 | 2026 has no 37% bracket row | Add row to the CSV only after verifying the IRS figure. Until then the app warns when taxable income exceeds the last bracket. |
| 3 | RMD table covers only 73–100 | The app returns a clear error outside coverage. Optionally add ages 72 and 101–120. |
| 4 | Std-deduction add-ons use `TODAY()` year | Use the selected tax year and `tblParameters` |
| 5 | Status coverage inconsistent (`Separate` missing in ordinary/LTCG/deduction tables) | Alias table now. Add Separate rows to the other tables, or restrict the UI to Single/Jointly. |
| 6 | SS provisional income excludes the RMD, with no tax-exempt-interest input | Add a tax-exempt-interest input. Confirm whether to include the RMD (spec §8.1 #7). |
| 7 | AMT uses flat 15% on LTCG | Phase 3: stacked 0/15/20% |
| 8 | Division by zero (`D21`, `J27`, `M43`) | Guard and return `None` |
| 9 | NIIT can go negative | Clamp NII at ≥ 0 |
| 10 | `C33`, `C36` not clamped | Clamp at 0 |
| 11 | QBI field semantics unclear | Keep as-is in phase 1, label "needs review" |
| 12 | Broken names (`IRABalance`, `RMDage`, `RMDFactor`, `tblRMDFactors`) | Drop |

Preserve-then-fix approach: ship `engine.compute(..., legacy=True)` to reproduce the workbook exactly for the golden test, and make `legacy=False` (the default) apply fixes 1, 4, 8, 9 and 10. Each fix is flagged in the result.

## 8. Testing
**Golden test** (workbook as saved: MFJ, 2026, DOB 1952-04-14, spouse 1974-09-30)
Inputs: IRA prior-YE 1,000,000; qualified dividends 1,800; interest 900; ordinary dividends 2,400; ST −3,000; wages 145,000; LT 6,000; Sch A 12,000; withheld 16,500.

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

Note that the standard-deduction check depends on `YEAR(TODAY())` in the workbook. The golden test must fix the as-of year to 2026.

**Other tests**
- Unit tests per function, using boundary values at each bracket edge.
- Property tests: tax is non-decreasing in income, allocation buckets sum to taxable income, and the app never returns a negative tax.
- Table tests (exist): duplicate keys, unsorted buckets, header mismatches, missing files and invalid values fail loudly.
- Cross-check: `income_tax()` (year-filtered) equals the bracket-allocation total.
- UI smoke test: `streamlit.testing.v1.AppTest` runs `streamlit_app.py` and asserts no exception. Skipped if Streamlit is not installed.
- Scenario JSON tests: see section 12.5.

## 9. Phases and deliverables
| Phase | Scope | Status / done when |
|---|---|---|
| 0 | Repo skeleton, CSVs (incl. `tblInputMap.csv`), loader, validator, CI, Streamlit skeleton | Done except the first Streamlit Cloud deploy; `validate_tables.py` passes |
| 1 | Pure calc modules, `legacy=True` engine | Golden test passes to the cent |
| 2 | Streamlit inputs form, results page, scenario JSON import/export (web + xlwings) | Manual run matches the workbook for 3+ scenarios; Excel/web round trip passes |
| 3 | Fix flags (§7), more years and statuses, stacked AMT LTCG | 2027 loads by CSV edit only |
| 4 | Saved scenarios (external storage), PDF report | As prioritized |

## 10. Annual maintenance (no code change)
1. Append the new year's rows to each CSV in `data/`, with a full set across all dependent tables (the spec notes that 2027 is not loaded).
2. Update `tblParameters.csv` constants.
3. Run `python scripts/validate_tables.py`. CI runs it on every push.
4. Push to GitHub. Community Cloud redeploys the app; use "Reload tables" if the app is already running.
5. Add a regression test for the new year.

## 11. Open questions for the owner
1. Is Separate (MFS) status in scope for phase 1?
2. Should the app default to `legacy=False` (fixes on)?
3. Where do the 2026 37% bracket and the missing 72/101+ RMD ages come from? Please supply sourced figures.
4. Confirm `version!B12` and `version!B13` are empty so they can hold the report title and last-updated date (section 12.7).
5. Is another private app already using the one-private-app slot on Streamlit Community Cloud (section 13)?
6. Will real client data ever be entered in the hosted app? If so, decide on access control before first use.

## 12. Scenario JSON import/export

### 12.1 Purpose
One JSON file carries every editable input of a scenario between Excel and the web app. The same file is produced and consumed by both. It holds the `inp...` named-range inputs as ordered name/value pairs, plus a report title and a last-updated date. Schedule709 is out of scope: nothing from that sheet is imported or exported.

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
- `inputs` is an ordered array of `{name, value}` pairs. Order follows `data/tblInputMap.csv`, which follows the sheet layout.
- `reportTitle` is a required string, 1–200 characters. `lastUpdated` is a required ISO 8601 local timestamp. The exporter sets it to the time of export.
- Dates are `YYYY-MM-DD` strings. Money is a plain number (no symbols or strings). Rates are fractions. A blank cell is `null`.
- Only editable input cells are exported. Formula (`calc...`) cells are never written to the file, and an importer must skip any pair whose target is a formula.
- Unknown names are ignored on import and listed in a warning. Missing names leave the existing value unchanged.
- Files are UTF-8 without a BOM. Readers open with `utf-8-sig` so a BOM does not break them.

### 12.3 Input map (external CSV, not in code)
`data/tblInputMap.csv` (21 rows, in the repo) defines the pairs, their order, the Excel fallback address, the type (`int`, `text`, `date`, `money`) and the Python field on `FilerInputs`. Columns: `Order,Name,Cell,Type,Field`.

Notes:
- Rows 1–3 and 5–19 are existing `inp...` names in the workbook spec.
- `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42) and `inpAdditionalTax` (C43) are the names the spec recommends but did not add. Until they exist in the workbook, the xlwings script falls back to the `Cell` column.
- `inpScheduleADeductions`, `inpIRAConversion`, `inpSocialSecurityBenefits` and `inpShortTermCapitalGainLoss` are sheet-scoped to `TaxSheetSingle`. The script resolves every name through that worksheet.
- `C9` (RMD) is a formula, so it is not an input and is not in the file.

### 12.4 Python components
- `app/scenario_io.py` (Phase 2): `ScenarioFile` Pydantic model (`schema_version`, `report_title`, `last_updated`, `workbook_version`, `inputs: list[InputPair]`). It provides `to_filer_inputs()` and `from_filer_inputs(inputs, title)`, both driven by `tblInputMap.csv`.
- Validation: reject an unsupported `schemaVersion` major. Check type per `Type` column (date parse, numeric, non-negative where the engine requires). Warn on unknown names. Require `reportTitle`.
- Streamlit export: `st.download_button` with the JSON string, file name derived from the report title, `lastUpdated` stamped at export time.
- Streamlit import: `st.file_uploader` (type `json`), parse and validate, copy values into `st.session_state`, show a warnings list.
- UI: editable Report title field; the results header shows the title and last-updated date.
- `tables.py` already validates `tblInputMap.csv` at startup: unique `Order` and `Name`, valid `Type`, and every `Field` exists on `FilerInputs`.

### 12.5 Tests
- Round trip: Excel export → Python import → Python export is identical in names, order and values.
- The golden-case inputs from section 8 survive export and import unchanged.
- Failure cases: blank values, a missing title, a malformed date, an unknown name, a formula target, and a BOM-prefixed file.

### 12.6 Excel integration: xlwings (replaces VBA)
`excel/scenario_xlwings.py` uses xlwings to read and write the input cells in the open workbook. It needs Excel and Python on the machine (`pip install xlwings`, or the `excel` extra). No VBA module is required. It runs locally only; it is not part of the hosted Streamlit app.

Command-line use, with the workbook open in Excel:
```
python excel/scenario_xlwings.py export --file scenario.json --title "Maxwell 2026 Roth Conversion Study"
python excel/scenario_xlwings.py import --file scenario.json
```
Options:
- `--book PATH` targets a specific workbook. Without it the script uses the active workbook.
- The same `export_scenario(book, path, title)` and `import_scenario(book, path)` functions can be called from the xlwings add-in ribbon or from a one-line `RunPython` button if you want buttons inside the workbook later.

Behavior:
- The input list, order and cell fallbacks come from `data/tblInputMap.csv`, the same file the web app uses. There is no second copy of the map.
- Formula cells are never overwritten on import. They are listed in the summary.
- Dates are read and written as real Excel dates. A `null` value clears the cell.
- `Application.Calculate` runs after an import so the sheet reflects the new inputs.
- Windows and Mac are both supported by xlwings. Only the Windows path has been considered in the design; test on Mac before relying on it.

### 12.7 Workbook changes required
- Add two metadata cells on the `version` sheet (rows 12–13 are free per the spec layout; confirm): `A12` "Report Title" with `B12` named `inpReportTitle`, and `A13` "Last Updated" with `B13` named `inpLastUpdated`. The script uses the cell addresses if the names do not exist.
- Optionally create the three recommended names `inpSpouseDateOfBirth` (E4), `inpTaxWithheld` (C42), `inpAdditionalTax` (C43). Existing formulas are unaffected.
- No other layout or formula changes.

## 13. Hosting on Streamlit Community Cloud
**Deploy steps**
1. Push the repo to GitHub (done). You need admin rights on the repo. Private repos need Streamlit authorized for private access.
2. At share.streamlit.io, create an app: pick the repo, branch `main`, main file `streamlit_app.py`.
3. In Advanced settings choose Python 3.12. The Python version cannot be changed later without deleting and redeploying the app.
4. Deploy. Every push to `main` redeploys.

**Dependencies**
- Community Cloud installs from `requirements.txt` in the repo root (currently `pydantic` and `streamlit`). `pyproject.toml` alone is not used for hosting.
- `xlwings` is intentionally not in `requirements.txt`; it is local-only.

**Access and privacy**
- A private-repo app is private by default: only invited viewers (by email) can open it. Community Cloud allows one private app at a time.
- Do not enter real client identifiers or account data until access control is decided (open question 6). For a public app, add app-level authentication.

**Behavior to design around**
- Files written to the app's local disk are lost on restart. Saved scenarios (phase 4) need external storage. Until then, scenarios are exported and imported as JSON files.
- The app reads `data/*.csv` from the repo. CSV changes take effect on redeploy, or after "Reload tables".
- Table validation failures do not stop the deploy. The app shows the errors on the Status tab, and CI flags them on the push.
