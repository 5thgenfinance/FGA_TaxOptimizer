# Changelog

This project uses Semantic Versioning (MAJOR.MINOR.PATCH). Before 1.0.0, MINOR releases added features, tax years or calculation changes, and PATCH releases fixed bugs or changed text. Version 1.0.0 was declared on 2026-11-17 after the manual checks in PROJECT_PLAN.md section 8 passed and the owner signed off. From 1.0.0, MAJOR releases change inputs or results in a way that breaks saved scenario files, MINOR releases add features or tax years, and PATCH releases fix bugs or change text.

The Excel workbook keeps its own scheme (YYYY.MAJOR.MINOR, currently 2026.3.0). The application records which workbook version its calculations were built from in `app/version.py`.

Versions 0.0.1 to 0.4.0 are labels applied afterwards to the phases in PROJECT_PLAN.md; their dates are the dates the phases were committed.

## [Unreleased]

## [1.0.0] - 2026-11-17
First release for deployment. The calculations, screens and documents are unchanged from 0.5.0 apart from the additions below. Deployment steps are in `docs/DEPLOYMENT.md`.

### Added
- A 'Download Excel Version' button at the right end of the header band. It serves `TaxRetirementOptimizer.xlsx` from the repository, so the downloaded file always matches the repository copy.
- What-if tax curves: above each slider, a chart of total tax across that lever's range (the other sliders held where you set them) with a second line for the tax on the next dollar, and your setting marked. Planning notes under each chart: the no-tax zone for long-term gains, the cost of short-term gains, the deductions needed before itemizing beats the standard deduction (with the saving beyond it), and how much IRA income fits under a chosen marginal rate (10% to 37%). Each lever has its own 'Show curve and notes' checkbox; a hidden lever skips its calculation. The sliders and their curves are 60% of the column width.
- What-if tab: sliders to add or remove long-term capital gains and short-term capital gains, add Schedule A deductions, and add an IRA distribution (taxed as ordinary income like a Roth conversion). It compares the current result with the adjusted one: total tax, amount due, effective rate, tax on the change, and a table of 14 measures. The sliders change a copy of the inputs only.
- Results: two new figures under the headline rows. 'Additional LTCG at 0%' is the long-term capital gains you could still realize in the 0% bracket (the 0% ceiling less taxable ordinary income and the gains already in it). 'Left before Schedule A' is how much more Schedule A deductions fit before itemizing beats the standard deduction. Each has a tooltip.
- Six 2026 cross-check scenarios (single wage earner; joint itemizer with dividends and gains; joint retirees with Social Security and a Roth conversion; single filer age 75 with an RMD, Social Security and gains; single high earner with net investment income tax; joint filers realizing gains in the 0% bracket), each with expected results worked out independently of the app.
- `docs/DEPLOYMENT.md`: release checklist, hosting settings, access control options, and known limits for the hosted app.

### Fixed
- A What-if test failed because it read a session key that is not available in the test harness. It now reads the named session keys.

### Release checks
- The manual checks in PROJECT_PLAN.md section 8 passed (owner sign-off, 2026-11-17).
- The six cross-check scenarios agreed with the app's results (owner report).

### Known limits carried into 1.0.0
- Filing status Separate is not supported for ordinary tax, long-term gains or the standard deduction.
- There is no tax-exempt interest input.
- The 2027 SALT cap (40,804; 20,402 separate) is derived, not read from an IRS document.
- State tax, IRMAA and ACA subsidy cliffs are not modeled.
- The app has no sign-in of its own; see `docs/DEPLOYMENT.md` for access control.

## [0.5.0] - 2026-11-17
### Added
- Brand layout from the FGA forecaster: navy sidebar with light-blue category panels, sticky navy header band with the shield, Playfair Display headings, Source Sans 3 body text, and a disclosure footer.
- Upload an Excel template (.xlsx or .xlsm) to convert it to scenario JSON and fill the forms. No copy of Excel is needed.
- Old named ranges are recognised through `excel/input_name_aliases.csv` (18 old names). Lookup order: current name, old names, fixed cell address.
- A tooltip on every input, from `app/input_help.py`. Tests fail if an input has none.
- Application version, shown in the footer and on the Status tab, with the Excel workbook version the calculations were built from.
- Documentation: user guide, architecture guide, updated specification, README.

### Changed
- Inputs moved from a tab to collapsible category panels in the sidebar (Filer, Retirement, Investments, Other income, Deductions, AMT, Payments).
- The xlwings export converts each cell value by type, lists unusable cells, and writes the title and timestamp into the workbook only after the JSON file is saved.

### Removed
- The Saved scenarios controls (Save, Load, Delete). Use Export scenario (JSON) to keep a scenario. The `scenario_store` module is still in the code but unused.

## [0.4.0] - 2026-11-16
### Added
- PDF report; saved scenarios in a local folder.

## [0.3.0] - 2026-11-16
### Added
- 2027 tax tables, the 2026 37% bracket, RMD ages 72 and 101 to 120, stacked AMT capital gains, RMD counted in Social Security provisional income.

## [0.2.0] - 2026-11-16
### Added
- Inputs form, results page, scenario JSON import and export, xlwings script.

## [0.1.0] - 2026-11-16
### Added
- Calculation modules and engine; legacy mode reproduces the saved workbook to the cent (golden test).

## [0.0.1] - 2026-11-16
### Added
- Repository skeleton, CSV tables with loader and validator, CI, Streamlit skeleton.
