# TaxRetirementOptimizer → Python Web App
Source: TaxRetirementOptimizer.xlsx v2026.3.0 + TaxRetirementOptimizer-Specification.md
Owner: Robert Maxwell

## 1. Goals and non-goals
**Goals**
- Reproduce the `TaxSheetSingle` estimate (ordinary tax, LTCG, NIIT, AMT, RMD, taxable Social Security, standard deduction, due/refund) as a web app.
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
| Web | FastAPI + Jinja2 + HTMX | Server-rendered form, live recalculation, minimal JS |
| Validation | Pydantic v2 | Typed input and CSV-row models |
| Math | `decimal.Decimal` for money, `Decimal` rates | Avoid float drift |
| Data | CSV via stdlib `csv` (or pandas) | Tables stay editable in Excel |
| Excel bridge | xlwings (Python) | Reads/writes the named input cells and exchanges scenario JSON; no VBA |
| Tests | pytest + hypothesis | Golden case, edge cases, property tests |
| Packaging | uv/pip, Dockerfile | Local and hosted deploy |

## 3. Repository layout
```
taxopt/
├─ data/                         # EXTERNAL TABLES (edit without touching code)
│  ├─ tblTaxRate.csv
│  ├─ tblTaxRateLTCG.csv
│  ├─ tblUniformRMDFactors.csv
│  ├─ tblStandDeductionBase.csv
│  ├─ tblAMT.csv
│  ├─ tblNIIT.csv
│  ├─ tblStatusAliases.csv       # NEW: status normalization
│  ├─ tblParameters.csv          # NEW: constants hard-coded in LAMBDAs
│  └─ tblInputMap.csv            # NEW: ordered input names, cells, types, fields
├─ app/
│  ├─ main.py                    # FastAPI routes
│  ├─ config.py                  # DATA_DIR, env settings
│  ├─ models.py                  # Pydantic: FilerInputs, TaxResult, table rows
│  ├─ tables.py                  # CSV loader + validators + lookups (cached)
│  ├─ scenario_io.py             # NEW: ScenarioFile model, JSON import/export
│  ├─ status.py                  # normalize_status()
│  ├─ calc/
│  │  ├─ ordinary.py             # IncomeTax, TaxRate bracket allocation
│  │  ├─ ltcg.py                 # LTCGTax, LTCG_Bucket_Amount, LTCG_Rate
│  │  ├─ rmd.py
│  │  ├─ deductions.py           # StandardDeduction_Basic/Full
│  │  ├─ socialsec.py            # SS_Taxable
│  │  ├─ niit.py
│  │  ├─ amt.py
│  │  └─ engine.py               # orchestrates TaxSheetSingle logic
│  ├─ templates/ (base.html, form.html, results.html, tables.html)
│  └─ static/
├─ excel/
│  └─ scenario_xlwings.py        # NEW: Excel <-> scenario JSON via xlwings
├─ tests/
│  ├─ test_tables.py, test_rmd.py, test_ordinary.py, test_ltcg.py,
│  │  test_amt.py, test_niit.py, test_socialsec.py, test_deductions.py
│  ├─ test_scenario_io.py
│  └─ test_golden_workbook.py
├─ scripts/validate_tables.py    # CLI check before deploy
├─ pyproject.toml
├─ Dockerfile
└─ README.md
```

## 4. External CSV tables
Rule: file name = Excel table name, and the column headers are kept verbatim. This includes `FilingYear` in `tblStandDeductionBase`, which is not `Year`. Values below are the workbook contents.

**data/tblTaxRate.csv**
```csv
Year,Bucket,Single,Jointly,Rate
2026,1,12400,24800,0.10
2026,2,50400,100800,0.12
2026,3,105700,211400,0.22
2026,4,201775,403550,0.24
2026,5,256225,512450,0.32
2026,6,640600,768700,0.35
2025,1,11925,23850,0.10
2025,2,48475,96950,0.12
2025,3,103350,206700,0.22
2025,4,197300,394600,0.24
2025,5,250525,501050,0.32
2025,6,626350,751600,0.35
2025,7,9999999,9999999,0.37
```

**data/tblTaxRateLTCG.csv**
```csv
Year,Bucket,Single,Jointly,Rate
2026,1,49450,98900,0
2026,2,545500,613700,0.15
2026,3,999999999,99999999,0.20
2025,1,48350,96700,0
2025,2,533400,600050,0.15
2025,3,9999999,9999999,0.20
```

**data/tblStandDeductionBase.csv**
```csv
FilingYear,Status,Amount
2026,Single,16100
2026,Jointly,32200
2025,Single,15750
2025,Jointly,31500
```

**data/tblAMT.csv**
```csv
Year,Status,Exemption,Start,End,Breakpoint,Lower,Upper,SaltCap
2026,Single,90100,500000,680200,244500,0.26,0.28,40400
2026,Jointly,140200,1000000,1280400,244500,0.26,0.28,40400
2026,Separate,70100,500000,610200,122250,0.26,0.28,20200
```

**data/tblNIIT.csv**
```csv
Year,Status,Threshold
2026,Single,200000
2026,Jointly,250000
2026,Separate,125000
```

**data/tblUniformRMDFactors.csv**
```csv
Age,LifeExpectancyFactor
73,26.5
74,25.5
75,24.6
76,23.7
77,22.9
78,22
79,21.1
80,20.2
81,19.4
82,18.5
83,17.7
84,16.8
85,16
86,15.2
87,14.4
88,13.7
89,12.9
90,12.2
91,11.5
92,10.8
93,10.1
94,9.5
95,8.9
96,8.4
97,7.8
98,7.3
99,6.8
100,6.4
```
Phase 1 loads this table exactly as it stands (ages 73–100). The RMDOLD factors, which cover 72–120 per spec §6.6, are only a reference for a later extension. Verify them against the IRS table before use.

**data/tblStatusAliases.csv** (new; replaces the inconsistent string checks in the LAMBDAs)
```csv
Alias,Canonical
single,Single
s,Single
jointly,Jointly
mfj,Jointly
married filing jointly,Jointly
separate,Separate
mfs,Separate
married filing separately,Separate
```

**data/tblParameters.csv** (new; constants hard-coded in the LAMBDAs, so they move out of code too)
```csv
Year,Key,Single,Jointly,Separate
2026,SS_Base1,25000,32000,25000
2026,SS_Base2,34000,44000,34000
2026,AgeAddOn65,2050,1650,1650
2026,SeniorBonusPerPerson,6000,6000,6000
2026,SeniorBonusPhaseoutStart,75000,150000,75000
2026,SeniorBonusPhaseoutRate,0.06,0.06,0.06
2026,NIIT_Rate,0.038,0.038,0.038
2026,AMT_LTCG_FlatRate,0.15,0.15,0.15
2026,MedicalAGIFloor,0.075,0.075,0.075
2026,CashDeductionAGILimit,0.60,0.60,0.60
```
Open item: Separate-status values in `tblParameters.csv` are placeholders. The workbook only states Single and Jointly (or MFS-lived-apart for SS), so confirm them.

**data/tblInputMap.csv** (new; defined in section 12.3)

### 4.1 Loader and validation rules (`tables.py`)
- Load once at startup, cache, and expose `reload_tables()` (admin endpoint) so a CSV edit doesn't need a redeploy.
- Validate each file against a Pydantic row model. The checks below come from spec §3:
  - Keys are unique: `(Year,Bucket)`, `Age`, `(FilingYear,Status)`, `(Year,Status)`.
  - Bucket limits ascend within each year and status.
  - Rates are in 0–1.
  - `AMT.End > Start`, and money fields are ≥ 0.
- Treat the sentinel ceilings (9999999, 99999999, 999999999) as data. Detect them with a `>= 9_999_999` rule and render them as "no limit" in the UI, never as statutory thresholds.
- Fail startup with a clear report if any file is invalid or missing.
- Provide `tables.supported_years()`, the intersection of years across all tables a calculation needs, so the UI only offers valid years.
- Add `scripts/validate_tables.py` as a CI step.

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

Excel named cells map to `FilerInputs` fields through `data/tblInputMap.csv` (section 12.3): `inpFilingStatus`, `inpDateOfBirth`, `inpTaxYear`, `inpPriorYearEndIRABalance`, `inpWagesAndTips`, and so on.

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

## 6. Web app
- `GET /`: input form (status, DOB, spouse DOB, year dropdown from `supported_years()`, all income, deduction and credit fields, report title).
- `POST /calculate`: HTMX partial. It re-renders the results panel on every field change.
- `GET /tables`: read-only view of each loaded CSV, with years and sources.
- `POST /admin/reload`: reload CSVs (protect with a token).
- `GET /api/calculate` (JSON): the same engine, for future integration with your RIA tools.
- Scenario import/export endpoints and buttons: see section 12.
- Display rules: currency `$#,##0`, rates `0%`, and sentinel limits shown as "No limit".
- Optional later: PDF/Excel export of the result, branded client report, saved scenarios (SQLite).

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
| 7 | AMT uses flat 15% on LTCG | Phase 2: stacked 0/15/20% |
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
- Table tests: duplicate keys, unsorted buckets and missing years must fail loudly.
- Cross-check: `income_tax()` (year-filtered) equals the bracket-allocation total.
- Scenario JSON tests: see section 12.5.

## 9. Phases and deliverables
| Phase | Scope | Done when |
|---|---|---|
| 0 | Repo skeleton, CSVs (incl. `tblInputMap.csv`), loader, validator, CI | `validate_tables.py` passes |
| 1 | Pure calc modules, `legacy=True` engine | Golden test passes to the cent |
| 2 | FastAPI form, results page, tables view, scenario JSON import/export (web + xlwings) | Manual run matches the workbook for 3+ scenarios; Excel/web round trip passes |
| 3 | Fix flags (§7), more years and statuses, JSON API, Dockerfile | 2027 loads by CSV edit only |
| 4 | Saved scenarios (SQLite), PDF report, auth | As prioritized |

## 10. Annual maintenance (no code change)
1. Append the new year's rows to each CSV, with a full set across all dependent tables (the spec notes that 2027 is not loaded).
2. Update `tblParameters.csv` constants.
3. Run `scripts/validate_tables.py`, then `POST /admin/reload`.
4. Add a regression test for the new year.

## 11. Open questions for the owner
1. Is Separate (MFS) status in scope for phase 1?
2. Should the app default to `legacy=False` (fixes on)?
3. Where do the 2026 37% bracket and the missing 72/101+ RMD ages come from? Please supply sourced figures.
4. Confirm `version!B12` and `version!B13` are empty so they can hold the report title and last-updated date (section 12.7).

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
`data/tblInputMap.csv` defines the pairs, their order, the Excel fallback address, and the Python field.
```csv
Order,Name,Cell,Type,Field
1,inpTaxYear,H10,int,tax_year
2,inpFilingStatus,C3,text,filing_status
3,inpDateOfBirth,C4,date,dob
4,inpSpouseDateOfBirth,E4,date,spouse_dob
5,inpPriorYearEndIRABalance,C5,money,prior_ye_ira_balance
6,inpSocialSecurityBenefits,C10,money,social_security_benefits
7,inpIRAConversion,C11,money,ira_conversion
8,inpQualifiedDividends,C12,money,qualified_dividends
9,inpTaxableInterest,C13,money,taxable_interest
10,inpOrdinaryDividends,C14,money,ordinary_dividends
11,inpAdditionalIncome,C15,money,additional_income
12,inpShortTermCapitalGainLoss,C16,money,short_term_gain_loss
13,inpWagesAndTips,C17,money,wages_and_tips
14,inpLongTermCapitalGains,C18,money,long_term_capital_gains
15,inpCapitalLossCarryover,C19,money,capital_loss_carryover
16,inpScheduleADeductions,C29,money,schedule_a_deductions
17,inpQualifiedBusinessIncome,C30,money,qualified_business_income
18,inpScheduleASALT,J35,money,schedule_a_salt
19,inpAMTOtherPreferences,J38,money,amt_other_preferences
20,inpTaxWithheld,C42,money,tax_withheld
21,inpAdditionalTax,C43,money,additional_tax
```
Notes:
- Rows 1–3 and 5–19 are existing `inp...` names in the workbook spec.
- `inpSpouseDateOfBirth`, `inpTaxWithheld` and `inpAdditionalTax` are the names the spec recommends but did not add. Until they exist in the workbook, the xlwings script falls back to the `Cell` column (E4, C42, C43).
- `inpScheduleADeductions`, `inpIRAConversion`, `inpSocialSecurityBenefits` and `inpShortTermCapitalGainLoss` are sheet-scoped to `TaxSheetSingle`. The script resolves every name through that worksheet.
- `C9` (RMD) is a formula, so it is not an input and is not in the file.

### 12.4 Python components
- `app/scenario_io.py`: `ScenarioFile` Pydantic model (`schema_version`, `report_title`, `last_updated`, `workbook_version`, `inputs: list[InputPair]`). It provides `to_filer_inputs()` and `from_filer_inputs(inputs, title)`, both driven by `tblInputMap.csv`.
- Validation: reject an unsupported `schemaVersion` major. Check type per `Type` column (date parse, numeric, non-negative where the engine requires). Warn on unknown names. Require `reportTitle`.
- `GET /api/scenario/export?title=...` returns the JSON file and stamps `lastUpdated`.
- `POST /api/scenario/import` accepts the JSON, validates it, fills the form and returns a warnings list.
- UI: "Import scenario" and "Export scenario" buttons plus an editable Report title field on the form.
- The results page and any PDF/print output show the report title and last-updated date in the header.
- `tables.py` validates `tblInputMap.csv` at startup: unique `Order` and `Name`, valid `Type`, and every `Field` exists on `FilerInputs`.

### 12.5 Tests
- Round trip: Excel export → Python import → Python export is identical in names, order and values.
- The golden-case inputs from section 8 survive export and import unchanged.
- Failure cases: blank values, a missing title, a malformed date, an unknown name, a formula target, and a BOM-prefixed file.

### 12.6 Excel integration: xlwings (replaces VBA)
`excel/scenario_xlwings.py` uses xlwings to read and write the input cells in the open workbook. It needs Excel and Python on the machine (`pip install xlwings`). No VBA module is required.

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
