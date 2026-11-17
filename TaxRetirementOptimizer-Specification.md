# TaxRetirementOptimizer — Template Specification

## 1. Scope, provenance, and implementation state

- Source: the open Excel workbook, including workbook-level and worksheet-level names, worksheet formulas, the `docx` formula library, all six `TaxTables` Excel Tables, and the `version` sheet.
- Specification date: November 16, 2026 (America/Chicago).
- Workbook version recorded in `version!B4`: `2026.3.0`; recorded release date: `2026-10-02`.
- This is an as-built specification, not a validation of current tax law. No external IRS figures were substituted or verified.
- Implemented change: 34 valid single-cell named ranges were converted to the convention in section 4, with their original target cells and scopes retained. Worksheet formula references were migrated. Original names were removed rather than retained as aliases.
- Installed named functions, table names, column headers, table contents, and tax-calculation logic were not intentionally changed. Formula-library parameter identifiers were preserved; a local LAMBDA parameter is not a named cell.
- The `docx` sheet documents 17 functions; Name Manager contains those 17 plus the legacy `RMDOLD` definition. Section 6 reproduces all 18 installed definitions. Section 7 distinguishes important documented alternatives from the installed implementation.
- Existing unresolved references and calculation limitations are listed in section 8. They were documented, not silently repaired.

## 2. Workbook structure and user-facing layout

### 2.1 Worksheets

| Worksheet | Role | Observed extent / structure |
|---|---|---|
| `TaxSheetSingle` | Filer inputs, federal tax estimate, deductions, NIIT and AMT | Used extent `A1:V45`; principal content in `B:M` |
| `Schedule709` | Gift / generation-skipping transfer schedule | Title in `A1`; `Table1` at `A6:M7` |
| `TaxTables` | Numeric tax lookup inputs | Six Excel Tables spanning `A2:AF30` |
| `docx` | Formula library documentation | Heading `A1`; headers `A4:F4`; 17 definitions in rows 5–21 |
| `version` | Release metadata and change history | `A1:F23`; metadata rows 4–11; history starts row 14 |

### 2.2 TaxSheetSingle composition

- `B1`: Filer Input Section.
- `B3:C6`: status, primary DOB, prior-year-end IRA balance, minimum RMD.
- `D4:E4`: second DOB label and date.
- `B8:D25`: income inputs and derived AGI / investment-income values.
- `B27:D31`: deductions and applicable deduction calculation.
- `B32:D36`: adjusted taxable, ordinary, and preferential income.
- `B37:C39`: NIIT threshold and net investment income.
- `B41:C44`: withholding, additional tax entry, and tax paid.
- `G10:H10`: selected tax year.
- `G12:M18`: ordinary bracket estimator. `H13:I18` contains two-column spills from `TaxRate`; `J:K` contains bracket widths / full-bracket tax, and `L:M` allocates actual ordinary income / tax.
- `G20:J23`: LTCG brackets. `H21:I23` contains two-column spills from `TaxRateLTCG`; `J21:J23` allocates gains into stacked brackets.
- `I26:J27`: selected LTCG amount, calculated tax, and effective LTCG rate.
- `I32:J43`: AMT inputs and calculations.
- `L32:M43`: regular tax, NIIT, AMT, subtotal, due/refund, and effective tax percentage.

The filer inputs are individual cells, not an Excel Table. Do not confuse the sheet name `TaxSheetSingle` with the actual selected filing status: `C3` currently contains `Jointly`.

### 2.3 Input data contracts

- DOB inputs: genuine Excel date values; display `m/d/yyyy`.
- Tax year: integer year at `H10`; it must have matching records in every table used by the selected calculation.
- Filing status: text at `C3`. Full-model support currently depends on exact table coverage. `Single` and `Jointly` are shared by ordinary, LTCG, and base-deduction tables; `Separate` exists only in AMT and NIIT tables.
- Monetary inputs: numeric USD amounts, not strings containing currency symbols. Most input amounts display accounting currency with no decimal places. IRA prior-year balance displays `$#,##0`.
- Gains / losses: signed numeric amounts. The workbook does not enforce a carryover sign convention; supply loss amounts consistently with formulas that add the carryover.
- Rates: numeric fractions, displayed as percentages; for example, 0.15 is 15%.
- Blank cells are not proven zeros. Some formulas nevertheless coerce blank amount inputs during arithmetic; downstream behavior must be understood before relying on an estimate.
- `C9` is labeled RMD in the income section but is currently a formula referencing `C6`, not a freely editable distribution input.
- Existing inputs without names remain unnamed: spouse DOB `E4`, tax withheld `C42`, and additional tax `C43`. Recommended future names are `inpSpouseDateOfBirth`, `inpTaxWithheld`, and `inpAdditionalTax`; these were not added by this conversion.

## 3. TaxTables input table formats and layout

### 3.1 Physical layout

All six tables have a visible header row at row 2, data beginning at row 3, no totals row, and style `TableStyleMedium2`. Titles are in row 1 at each table's first column. Spacer columns are `F`, `L`, `O`, `S`, and `AC`.

| Table name | Title cell / exact title | Header range | Data range | Data rows |
|---|---|---|---|---|
| `tblTaxRate` | `A1`: Ordinary Tax Table | `A2:E2` | `A3:E15` | 13 |
| `tblTaxRateLTCG` | `G1`: LTGC Tax Table | `G2:K2` | `G3:K8` | 6 |
| `tblUniformRMDFactors` | `M1`: RMD WD Factors | `M2:N2` | `M3:N30` | 28 |
| `tblStandDeductionBase` | `P1`: Base Standard Deduction | `P2:R2` | `P3:R6` | 4 |
| `tblAMT` | `T1`: AMT Table | `T2:AB2` | `T3:AB5` | 3 |
| `tblNIIT` | `AD1`: NIIT Threshold | `AD2:AF2` | `AD3:AF5` | 3 |

Observed column widths, in points: all columns `A:AF` are 48 except `I=58.5`, `N=114`, `P=63`, `R=54`, `T=56.25`, `U=56.25`, `V=73.5`, `W=56.25`, `X=56.25`, `Y=72`, `Z=56.25`, `AA=56.25`, and `AF=63`. The row-2 header height is 15 points. These are structural measurements, not a claim that every header is visually readable.

No validation rule was returned for the six table body ranges. Constraints below are specification requirements / recommendations, not newly installed Excel validation.

### 3.2 `tblTaxRate` — ordinary income brackets

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| A | `Year` | Integer tax year | General | `0` |
| B | `Bucket` | Integer bracket sequence, ascending within year | General | `0` |
| C | `Single` | USD upper limit for Single | General | `#,##0` |
| D | `Jointly` | USD upper limit for Jointly | General | `#,##0` |
| E | `Rate` | Numeric rate fraction | 2026: `0%`; 2025: General | `0%` |

Key: `(Year, Bucket)` must be unique. Limits must increase within each year and status. `IncomeTax` uses physical row order when constructing lower limits, so keep each year's records in ascending bucket order. `TaxRate` performs an exact composite lookup and returns `{upper limit, rate}` horizontally.

Observed contents:

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

The 2026 bucket-7 row is absent. The ordinary estimator on `TaxSheetSingle` also allocates only six buckets. No missing upper-bracket figures were invented.

### 3.3 `tblTaxRateLTCG` — preferential income brackets

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| G | `Year` | Integer tax year | General | `0` |
| H | `Bucket` | Integer bracket sequence | General | `0` |
| I | `Single` | USD upper limit for Single | General except `I4` uses currency | `#,##0` |
| J | `Jointly` | USD upper limit for Jointly | General | `#,##0` |
| K | `Rate` | Numeric rate fraction | `0%` | `0%` |

Key: `(Year, Bucket)`; ascending limits and bucket order within each year. Terminal values are finite sentinel ceilings, not infinity. Preserve them as actual data unless deliberately redesigning terminal-bracket handling.

```csv
Year,Bucket,Single,Jointly,Rate
2026,1,49450,98900,0
2026,2,545500,613700,0.15
2026,3,999999999,99999999,0.20
2025,1,48350,96700,0
2025,2,533400,600050,0.15
2025,3,9999999,9999999,0.20
```

`I4` currently uses `$#,##0_);[Red]($#,##0)`. This is still a numeric value, not currency text. The inconsistent terminal sentinel values are retained as observed.

### 3.4 `tblUniformRMDFactors` — RMD divisor inputs

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| M | `Age` | Integer age attained in calculation year | General | `0` |
| N | `LifeExpectancyFactor` | Positive numeric divisor | General | `0.0` |

Key: `Age`, unique. Installed `RMD` uses an exact lookup, so row order is not essential to that lookup; ascending age is the intended layout. Data currently cover ages 73–100 only.

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

### 3.5 `tblStandDeductionBase` — base deduction inputs

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| P | `FilingYear` | Integer tax year | General | `0` |
| Q | `Status` | Filing status text | General | General |
| R | `Amount` | Numeric USD base deduction | General | `#,##0` |

Key: `(FilingYear, Status)`, unique. This header is `FilingYear`, not `Year`; preserve that distinction in structured references. Values exclude additions computed by the standard-deduction functions.

```csv
FilingYear,Status,Amount
2026,Single,16100
2026,Jointly,32200
2025,Single,15750
2025,Jointly,31500
```

### 3.6 `tblAMT` — AMT and SALT parameters

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| T | `Year` | Integer tax year | General | `0` |
| U | `Status` | Filing status text | General | General |
| V | `Exemption` | Numeric USD base exemption | General | `#,##0` |
| W | `Start` | USD exemption phaseout start | General | `#,##0` |
| X | `End` | USD exemption phaseout end | General | `#,##0` |
| Y | `Breakpoint` | USD ordinary AMT rate breakpoint | General | `#,##0` |
| Z | `Lower` | Numeric lower AMT rate fraction | `0%` | `0%` |
| AA | `Upper` | Numeric upper AMT rate fraction | `0%` | `0%` |
| AB | `SaltCap` | Numeric USD SALT cap | General | `#,##0` |

Key: `(Year, Status)`, unique; require `End > Start`, nonnegative monetary fields, and rate fractions within 0–1. Case-insensitive matching in Excel does not normalize spaces or aliases automatically.

```csv
Year,Status,Exemption,Start,End,Breakpoint,Lower,Upper,SaltCap
2026,Single,90100,500000,680200,244500,0.26,0.28,40400
2026,Jointly,140200,1000000,1280400,244500,0.26,0.28,40400
2026,Separate,70100,500000,610200,122250,0.26,0.28,20200
```

### 3.7 `tblNIIT` — net investment income tax thresholds

| Column | Header, verbatim | Storage / meaning | Observed display | Recommended display |
|---|---|---|---|---|
| AD | `Year` | Integer tax year | General | `0` |
| AE | `Status` | Filing status text | General | General |
| AF | `Threshold` | Numeric USD MAGI threshold | General | `#,##0` |

Key: `(Year, Status)`, unique; threshold nonnegative. `NIIT_Threshold` trims and lowercases its input and lowercases table status values; it does not trim the stored table status.

```csv
Year,Status,Threshold
2026,Single,200000
2026,Jointly,250000
2026,Separate,125000
```

### 3.8 Maintenance rules

1. Append inside each Excel Table so structured references expand; do not merely type disconnected rows below it.
2. Retain table names and exact column headers.
3. Add a complete set of records for each newly supported year and status across all dependent tables; 2027 is not loaded in this snapshot.
4. Keep bucket tables sorted by year and ascending bucket; exact lookups do not protect `IncomeTax` / `LTCGTax` from unordered bracket arrays.
5. Do not use finite sentinel values as genuine statutory thresholds in explanatory output.
6. Confirm every installed function agrees with the library documentation before changing a release-status claim.
7. Recommended display formats above were documented only; no format changes were applied.

## 4. Single-cell named-range convention and migration dictionary

### 4.1 Convention

- Format: `inp` or `calc` followed by descriptive PascalCase, ASCII letters / digits, no spaces.
- `inp`: an editable scalar input cell.
- `calc`: a formula-derived scalar cell, even if it sits in an area labeled Inputs.
- Acronyms are retained for readability: IRA, AMT, SALT, AGI, NIIT, LTCG, RMD.
- Excel names are case-insensitive; case-only variants are not distinct names.
- Preserve existing scope. Local names require a sheet qualifier when used outside `TaxSheetSingle`, e.g. `TaxSheetSingle!calcAdjustedGrossIncome`.
- `tbl...` names identify Excel Tables. Named LAMBDA functions retain their original function names. LAMBDA parameters and LET-local identifiers are not part of this migration.
- No broken reference was assigned an assumed replacement target.

### 4.2 Workbook-scoped names: 26 conversions

All target addresses below are absolute references on `TaxSheetSingle`.

| Previous name | Standard name | Target | Kind / meaning |
|---|---|---|---|
| `AddlIncome` | `inpAdditionalIncome` | `$C$15` | USD Schedule 1 additional income |
| `AGICashLimit` | `calcAGICashDeductionLimit` | `$C$25` | USD 60%-of-AGI cash limit |
| `AMTRegular` | `calcAMTRegularTaxableIncome` | `$J$34` | USD AMT regular taxable-income basis |
| `ApplicableDed` | `calcApplicableDeduction` | `$C$31` | USD selected deduction |
| `DOB` | `inpDateOfBirth` | `$C$4` | Excel date, primary filer |
| `losscarry` | `inpCapitalLossCarryover` | `$C$19` | Signed USD carryover |
| `LTcapgains` | `inpLongTermCapitalGains` | `$C$18` | Signed USD LT gain/loss |
| `LTCGPool` | `calcAMTLTCGPool` | `$J$39` | USD AMT preferential-income pool |
| `LTCGSubtotal` | `calcLTCGSubtotal` | `$C$20` | USD pre-deduction LTCG subtotal |
| `LTCGTaxRate` | `calcLTCGTaxRate` | `$C$24` | Effective LTCG rate fraction |
| `niiBuildup` | `calcNetInvestmentIncome` | `$C$39` | USD net investment income |
| `niiThreshold` | `calcNIITThreshold` | `$C$38` | USD NIIT threshold |
| `OrdDivs` | `inpOrdinaryDividends` | `$C$14` | USD ordinary dividends |
| `OrdIncome` | `calcOrdinaryIncome` | `$C$34` | USD ordinary-income subtotal |
| `OtherPreferences` | `inpAMTOtherPreferences` | `$J$38` | USD AMT other preferences |
| `prior_IRA_bal` | `inpPriorYearEndIRABalance` | `$C$5` | USD prior-year-end IRA balance |
| `QualBusinessInc` | `inpQualifiedBusinessIncome` | `$C$30` | USD value used in deduction calculation; interpretation needs review |
| `QualDivs` | `inpQualifiedDividends` | `$C$12` | USD qualified dividends |
| `SALT_addback` | `calcSALTAddback` | `$J$37` | USD SALT addback |
| `SALT_schedA` | `inpScheduleASALT` | `$J$35` | USD Schedule A state/local/property taxes |
| `status` | `inpFilingStatus` | `$C$3` | Filing status text |
| `TaxableInt` | `inpTaxableInterest` | `$C$13` | USD taxable interest |
| `TaxableOrd` | `calcTaxableOrdinaryIncome` | `$C$35` | USD taxable ordinary income |
| `taxableSSI` | `calcTaxableSocialSecurity` | `$C$21` | USD taxable Social Security |
| `wages` | `inpWagesAndTips` | `$C$17` | USD wages and tips |
| `year` | `inpTaxYear` | `$H$10` | Integer tax year |

For example, the exact Refers to value for `inpDateOfBirth` is `=TaxSheetSingle!$C$4`.

### 4.3 TaxSheetSingle-scoped names: 8 conversions

| Previous name | Standard name | Target | Kind / meaning |
|---|---|---|---|
| `ATI` | `calcAdjustedTaxableIncome` | `$C$33` | USD AGI less applicable deduction |
| `Deductions` | `inpScheduleADeductions` | `$C$29` | USD gifts and Schedule A deductions |
| `Distributions` | `calcRMDDistribution` | `$C$9` | USD formula-linked minimum RMD distribution |
| `grossincome` | `calcAdjustedGrossIncome` | `$C$22` | USD adjusted gross income, not gross receipts |
| `RothConv` | `inpIRAConversion` | `$C$11` | USD IRA conversion input |
| `SSI` | `inpSocialSecurityBenefits` | `$C$10` | USD Social Security benefits input |
| `STcapgain` | `inpShortTermCapitalGainLoss` | `$C$16` | Signed USD short-term gain/loss |
| `taxpaid` | `calcTotalTaxPaid` | `$C$44` | USD withholding plus additional tax input |

### 4.4 Unresolved names excluded from migration

The following workbook-scoped names currently refer to `=#REF!#REF!` and therefore cannot be verified as valid single-cell references: `IRABalance`, `RMDage`, `RMDFactor`, and `tblRMDFactors`.

They remain unchanged. `tblRMDFactors` is a broken defined name, not the valid Excel Table `tblUniformRMDFactors`. The relationship between `IRABalance` and the valid old name `prior_IRA_bal` was not assumed.

Internal compatibility / formula identifiers beginning `_xlfn.`, `_xlpm.`, and `_xlop.` are not user input cells and were not renamed or deleted. Their reported error type is not by itself proof that all named functions fail; the live tax sheet had computed values.

## 5. Formula interfaces and model wiring

### 5.1 Installed function catalog

| Function | Parameters in order | Result | Dependencies |
|---|---|---|---|
| `IncomeTax` | TaxYear, FilingStatus, TaxableIncome | Numeric USD progressive ordinary tax | `tblTaxRate` |
| `LTCGTax` | TaxYear, FilingStatus, TaxableIncome | Numeric USD stand-alone preferential tax | `tblTaxRateLTCG` |
| `TaxRate` | filingStatus, taxYear, bucket | 1×2 spill: upper limit, rate | `tblTaxRate` |
| `TaxRateLTCG` | filingStatus, taxYear, bucket | 1×2 spill: upper limit, rate | `tblTaxRateLTCG` |
| `RMD` | DOB, CalcYear, PriorYearEndBalance | Numeric USD minimum withdrawal | `tblUniformRMDFactors` |
| `RMDOLD` | DOB, CalcYear, PriorYearEndBalance | Legacy numeric USD withdrawal | Embedded factors |
| `StandardDeduction_Basic` | DOB, Status, BaseStdDed | Numeric USD base plus age addition | Current date, embedded constants |
| `StandardDeduction_Full` | DOB, Status, BaseStdDed, AGI, [DOB_2] | Numeric USD base, age addition and senior bonus | Current date, embedded constants |
| `AMT_ExemptionRate` | FilingYear, Status | Numeric phaseout fraction | `tblAMT` |
| `AMT_Exemption` | AMTI, Status, FilingYear | Numeric USD phased exemption | `tblAMT`, `AMT_ExemptionRate` |
| `AMT_Tax` | RegularTaxableIncome, SALTAddback, OtherPreferences, LTCGPool, Status, FilingYear | Numeric USD tentative minimum tax | `tblAMT`, `AMT_Exemption` |
| `AMT_Owed` | RegularTaxableIncome, SALTAddback, OtherPreferences, LTCGPool, Status, FilingYear, RegularTax | Numeric USD additional AMT | `AMT_Tax` |
| `LTCG_Rate` | TaxableIncome, Status, FilingYear | Rate fraction or empty text on no match | `tblTaxRateLTCG` |
| `NIIT_Threshold` | Status, FilingYear | Numeric USD MAGI threshold | `tblNIIT` |
| `NII_Buildup` | TaxableInterest, OrdinaryDividends, TotalCapGain, OtherPassiveIncome | Numeric USD investment-income sum | None |
| `NIIT_Tax` | MAGI, NetInvestmentIncome, Status, FilingYear | Numeric USD NIIT | `NIIT_Threshold` |
| `SS_Taxable` | SSI, OtherIncome, Status, [MFSLivedApart] | Numeric USD taxable benefits | Embedded thresholds |
| `LTCG_Bucket_Amount` | TaxableIncome, OrdinaryIncome, LTCGPool, BucketFloor, BucketCeiling | Numeric USD gains allocated to bracket | None |

Brackets around optional parameters indicate optional arguments as represented in the extracted workbook definitions. These are not structured table references. Definitions below reproduce that representation; use Name Manager in the target Excel build to confirm acceptance when rebuilding. A bare LAMBDA expression in a worksheet cell without invocation can produce a calculation error; the function should be registered as a defined name before calling it.

### 5.2 Principal worksheet formulas after cell-name conversion

The following formulas describe the actual model, including its limitations; they are not rewritten tax-law recommendations. Unqualified local names are evaluated on `TaxSheetSingle`.

Minimum RMD, `C6`:

```excel
=RMD(inpDateOfBirth,inpTaxYear,inpPriorYearEndIRABalance)
```

Distribution income, `C9`:

```excel
=C6
```

Preferential subtotal, `C20`:

```excel
=inpLongTermCapitalGains+inpCapitalLossCarryover+inpQualifiedDividends
```

Taxable Social Security, `C21`:

```excel
=SS_Taxable(inpSocialSecurityBenefits,SUM($C$13:$C$19)+inpIRAConversion,inpFilingStatus)
```

Adjusted gross income, `C22`:

```excel
=calcRMDDistribution+calcTaxableSocialSecurity+inpIRAConversion+inpShortTermCapitalGainLoss+inpWagesAndTips+inpLongTermCapitalGains+inpTaxableInterest+inpOrdinaryDividends+inpAdditionalIncome+inpCapitalLossCarryover
```

Medical deduction threshold, `C23`, and cash deduction limit, `C25`:

```excel
=calcAdjustedGrossIncome*0.075
```

```excel
=0.6*calcAdjustedGrossIncome
```

Standard deduction calculation, `C28`:

```excel
=IF(inpFilingStatus="Jointly",StandardDeduction_Full(inpDateOfBirth,inpFilingStatus,XLOOKUP(1,(tblStandDeductionBase[FilingYear]=inpTaxYear)*(tblStandDeductionBase[Status]=inpFilingStatus),tblStandDeductionBase[Amount]),calcAdjustedGrossIncome,$E$4),StandardDeduction_Full(inpDateOfBirth,inpFilingStatus,XLOOKUP(1,(tblStandDeductionBase[FilingYear]=inpTaxYear)*(tblStandDeductionBase[Status]=inpFilingStatus),tblStandDeductionBase[Amount]),calcAdjustedGrossIncome))
```

Applicable deduction, `C31`; taxable income, `C33`; ordinary income, `C34`; taxable ordinary, `C35`; taxable preferential income, `C36`:

```excel
=MAX(MIN(inpScheduleADeductions+inpQualifiedBusinessIncome,calcAGICashDeductionLimit),C28)
```

```excel
=C22-C31
```

```excel
=calcAdjustedGrossIncome-calcLTCGSubtotal
```

```excel
=MAX(calcOrdinaryIncome-calcApplicableDeduction,0)
```

```excel
=inpLongTermCapitalGains+inpQualifiedDividends+inpCapitalLossCarryover-MAX(0,calcApplicableDeduction-calcOrdinaryIncome)
```

NIIT threshold and buildup, `C38:C39`:

```excel
=NIIT_Threshold(inpFilingStatus,inpTaxYear)
```

```excel
=NII_Buildup(inpTaxableInterest,inpOrdinaryDividends,inpShortTermCapitalGainLoss+inpLongTermCapitalGains+inpCapitalLossCarryover,0)
```

Ordinary bracket lookup, first row `H13` (copy down to `H18`, bucket IDs in `G13:G18`):

```excel
=TaxRate(inpFilingStatus,inpTaxYear,G13)
```

Preferential bracket lookup, first row `H21` (copy down to `H23`):

```excel
=TaxRateLTCG(inpFilingStatus,inpTaxYear,G21)
```

Stacked LTCG allocation, `J21:J23`:

```excel
=LTCG_Bucket_Amount(calcAdjustedTaxableIncome,calcTaxableOrdinaryIncome,C36,0,H21)
```

```excel
=LTCG_Bucket_Amount(calcAdjustedTaxableIncome,calcTaxableOrdinaryIncome,C36,H21,H22)
```

```excel
=LTCG_Bucket_Amount(calcAdjustedTaxableIncome,calcTaxableOrdinaryIncome,C36,H22,H23)
```

Preferential tax and effective rate, `I27` and `J27`:

```excel
=SUMPRODUCT(J21:J23,I21:I23)
```

```excel
=I27/I26
```

AMT linkage:

```excel
J34: =calcAdjustedTaxableIncome
J36: =XLOOKUP(1,(tblAMT[Year]=inpTaxYear)*(tblAMT[Status]=inpFilingStatus),tblAMT[SaltCap])
J37: =MIN(J35,J36)
J39: =C36
J40: =AMT_ExemptionRate(inpTaxYear,inpFilingStatus)
J41: =AMT_Exemption(calcAdjustedTaxableIncome+calcSALTAddback+inpAMTOtherPreferences,inpFilingStatus,inpTaxYear)
J42: =AMT_Tax(calcAMTRegularTaxableIncome,calcSALTAddback,inpAMTOtherPreferences,C36,inpFilingStatus,inpTaxYear)
J43: =AMT_Owed(calcAMTRegularTaxableIncome,calcSALTAddback,inpAMTOtherPreferences,calcAMTLTCGPool,inpFilingStatus,inpTaxYear,M23)
```

The address prefixes in the preceding block identify destination cells; they are not part of the formulas to paste.

Tax summary:

```excel
M20: =SUM(M13:M18)
M21: =I27
M23: =SUM(M20:M21)
M34: =M23
M36: =NIIT_Tax(calcAdjustedGrossIncome,calcNetInvestmentIncome,inpFilingStatus,inpTaxYear)
M37: =J43
M39: =M34+M36+M37
C44: =SUM(C42:C43)
M41: =M39-calcTotalTaxPaid
M43: =M39/calcAdjustedGrossIncome
```

A positive `M41` is labeled due, a negative value refund. `M43` uses AGI as its denominator, not taxable income. `IncomeTax` and `LTCGTax` are registered library functions but are not used to produce `M20:M21`; the visible estimator uses explicit bracket allocation instead.

## 6. Installed named LAMBDA definitions — as extracted

These definitions are the installed Name Manager versions. Names are workbook-scoped. Only whitespace layout has been adjusted for readability. Existing defects are intentionally retained here so this specification does not misrepresent the live template.

### 6.1 `IncomeTax`

```excel
=LAMBDA(TaxYear,FilingStatus,TaxableIncome,
 LET(
  Brackets,FILTER(tblTaxRate,tblTaxRate[Year]=TaxYear),
  Limits,SWITCH(FilingStatus,"Single",tblTaxRate[Single],"Jointly",tblTaxRate[Jointly],NA()),
  Rates,tblTaxRate[Rate],
  LowerLimits,VSTACK(0,DROP(Limits,-1)),
  SUM(MAP(LowerLimits,Limits,Rates,LAMBDA(Lower,Upper,Rate,MAX(0,MIN(TaxableIncome,Upper)-Lower)*Rate)))
 )
)
```

Installed defect: `Brackets` is filtered but unused; `Limits` and `Rates` include multiple years. See section 7.1 for the documented alternative.

### 6.2 `LTCGTax`

```excel
=LAMBDA(TaxYear,FilingStatus,TaxableIncome,
 LET(
  Brackets,FILTER(tblTaxRateLTCG,tblTaxRateLTCG[Year]=TaxYear),
  Limits,SWITCH(FilingStatus,"Single",tblTaxRateLTCG[Single],"Jointly",tblTaxRateLTCG[Jointly],NA()),
  Rates,tblTaxRateLTCG[Rate],
  LowerLimits,VSTACK(0,DROP(Limits,-1)),
  SUM(MAP(LowerLimits,Limits,Rates,LAMBDA(Lower,Upper,Rate,MAX(0,MIN(TaxableIncome,Upper)-Lower)*Rate)))
 )
)
```

Stand-alone calculation: even the documented year-filtered version does not stack preferential income above ordinary income. The sheet's actual stacked allocation uses `LTCG_Bucket_Amount`.

### 6.3 `TaxRate`

```excel
=LAMBDA(filingStatus,taxYear,bucket,
 LET(
  bucketMax,XLOOKUP(1,(tblTaxRate[Year]=taxYear)*(tblTaxRate[Bucket]=bucket),CHOOSECOLS(tblTaxRate,XMATCH(filingStatus,tblTaxRate[#Headers]))),
  taxRate,XLOOKUP(1,(tblTaxRate[Year]=taxYear)*(tblTaxRate[Bucket]=bucket),tblTaxRate[Rate]),
  HSTACK(bucketMax,taxRate)
 )
)
```

### 6.4 `TaxRateLTCG`

```excel
=LAMBDA(filingStatus,taxYear,bucket,
 LET(
  bucketMax,XLOOKUP(1,(tblTaxRateLTCG[Year]=taxYear)*(tblTaxRateLTCG[Bucket]=bucket),CHOOSECOLS(tblTaxRateLTCG,XMATCH(filingStatus,tblTaxRateLTCG[#Headers]))),
  taxRate,XLOOKUP(1,(tblTaxRateLTCG[Year]=taxYear)*(tblTaxRateLTCG[Bucket]=bucket),tblTaxRateLTCG[Rate]),
  HSTACK(bucketMax,taxRate)
 )
)
```

### 6.5 `RMD`

```excel
=LAMBDA(DOB,CalcYear,PriorYearEndBalance,
 IF(OR(NOT(ISNUMBER(DOB)),NOT(ISNUMBER(CalcYear)),NOT(ISNUMBER(PriorYearEndBalance))),NA(),
  IF(PriorYearEndBalance<0,NA(),
   LET(
    Age,CalcYear-YEAR(DOB),
    StartAge,IF(DOB<DATE(1951,1,1),72,IF(DOB<DATE(1960,1,1),73,75)),
    IF(Age<StartAge,0,
     LET(
      Factor,IF(Age>=120,2,XLOOKUP(Age,tblUniformRMDFactors[Age],tblUniformRMDFactors[LifeExpectancyFactor],NA(),0)),
      PriorYearEndBalance/Factor
     )
    )
   )
  )
 )
)
```

It returns zero before start age, `NA()` for invalid numeric inputs / negative balances / absent required factors, and uses divisor 2 at age 120 or above. Missing table ages 72 and 101–119 are not covered by this installed implementation.

### 6.6 `RMDOLD` — legacy, not the active RMD call

```excel
=LAMBDA(DOB,CalcYear,PriorYearEndBalance,
 LET(
  Age,CalcYear-YEAR(DOB),
  StartAge,IF(DOB<DATE(1951,1,1),72,IF(DOB<DATE(1960,1,1),73,75)),
  Factors,{27.4;26.5;25.5;24.6;23.7;22.9;22;21.1;20.2;19.4;18.5;17.7;16.8;16;15.2;14.4;13.7;12.9;12.2;11.5;10.8;10.1;9.5;8.9;8.4;7.8;7.3;6.8;6.4;6;5.6;5.2;4.9;4.6;4.3;4.1;3.9;3.7;3.5;3.4;3.3;3.1;3;2.9;2.8;2.7;2.5;2.3;2},
  Factor,IF(Age>=120,2,INDEX(Factors,Age-71)),
  IF(OR(NOT(ISNUMBER(DOB)),NOT(ISNUMBER(CalcYear)),NOT(ISNUMBER(PriorYearEndBalance)),PriorYearEndBalance<0),NA(),
   IF(Age<StartAge,0,PriorYearEndBalance/Factor)
  )
 )
)
```

The factor calculation precedes the start-age check in this legacy definition. Do not substitute it for `RMD` without evaluating the implications.

### 6.7 `StandardDeduction_Basic`

```excel
=LAMBDA(DOB,Status,BaseStdDed,
 LET(
  AsOfYear,YEAR(TODAY()),
  Is65Plus,IF(AND(MONTH(DOB)=1,DAY(DOB)=1),AsOfYear>=(YEAR(DOB)+65-1),AsOfYear>=(YEAR(DOB)+65)),
  StatusL,LOWER(TRIM(Status)),
  AgeAddOn,IF(Is65Plus,IF(OR(StatusL="single",StatusL="s"),2050,1650),0),
  BaseStdDed+AgeAddOn
 )
)
```

### 6.8 `StandardDeduction_Full`

```excel
=LAMBDA(DOB,Status,BaseStdDed,AGI,[DOB_2],
 LET(
  AsOfYear,YEAR(TODAY()),
  StatusL,LOWER(TRIM(Status)),
  IsSingle,OR(StatusL="single",StatusL="s"),
  HasSecondDOB,NOT(ISOMITTED(DOB_2)),
  Is65Plus_1,IF(AND(MONTH(DOB)=1,DAY(DOB)=1),AsOfYear>=(YEAR(DOB)+65-1),AsOfYear>=(YEAR(DOB)+65)),
  Is65Plus_2,IF(HasSecondDOB,IF(AND(MONTH(DOB_2)=1,DAY(DOB_2)=1),AsOfYear>=(YEAR(DOB_2)+65-1),AsOfYear>=(YEAR(DOB_2)+65)),FALSE),
  NumQualifying65,(IF(Is65Plus_1,1,0))+(IF(Is65Plus_2,1,0)),
  AgeAddOnPerPerson,IF(IsSingle,2050,1650),
  AgeAddOn,IF(IsSingle,IF(Is65Plus_1,AgeAddOnPerPerson,0),NumQualifying65*AgeAddOnPerPerson),
  PhaseoutStart,IF(IsSingle,75000,150000),
  SeniorBonusMaxPerPerson,6000,
  SeniorBonusMaxTotal,NumQualifying65*SeniorBonusMaxPerPerson,
  SeniorBonus,IF(NumQualifying65=0,0,MAX(0,SeniorBonusMaxTotal-MAX(0,AGI-PhaseoutStart)*0.06)),
  BaseStdDed+AgeAddOn+ROUND(SeniorBonus,0)
 )
)
```

The age additions and bonus are hard-coded and use the current year, not the selected tax year. The full formula treats the senior bonus as part of its returned deduction; it does not separately model tax-return deduction categories.

### 6.9 `AMT_ExemptionRate`

```excel
=LAMBDA(FilingYear,Status,
 LET(
  Match,(tblAMT[Year]=FilingYear)*(tblAMT[Status]=Status),
  Exemption,XLOOKUP(1,Match,tblAMT[Exemption]),
  StartAmt,XLOOKUP(1,Match,tblAMT[Start]),
  EndAmt,XLOOKUP(1,Match,tblAMT[End]),
  Exemption/(EndAmt-StartAmt)
 )
)
```

### 6.10 `AMT_Exemption`

```excel
=LAMBDA(AMTI,Status,FilingYear,
 LET(
  Match,(tblAMT[Year]=FilingYear)*(tblAMT[Status]=Status),
  BaseExemption,XLOOKUP(1,Match,tblAMT[Exemption]),
  StartAmt,XLOOKUP(1,Match,tblAMT[Start]),
  Rate,AMT_ExemptionRate(FilingYear,Status),
  Reduction,MAX(0,(AMTI-StartAmt)*Rate),
  MAX(0,BaseExemption-Reduction)
 )
)
```

### 6.11 `AMT_Tax`

```excel
=LAMBDA(RegularTaxableIncome,SALTAddback,OtherPreferences,LTCGPool,Status,FilingYear,
 LET(
  Match,(tblAMT[Year]=FilingYear)*(tblAMT[Status]=Status),
  Breakpoint,XLOOKUP(1,Match,tblAMT[Breakpoint]),
  LowerRate,XLOOKUP(1,Match,tblAMT[Lower]),
  UpperRate,XLOOKUP(1,Match,tblAMT[Upper]),
  AMTI,RegularTaxableIncome+SALTAddback+OtherPreferences,
  Exemption,AMT_Exemption(AMTI,Status,FilingYear),
  AMTBase,MAX(0,AMTI-Exemption),
  OrdinaryPortion,MAX(0,AMTBase-LTCGPool),
  LTCGPortion,MIN(AMTBase,LTCGPool),
  TaxOrdinary,IF(OrdinaryPortion<=Breakpoint,OrdinaryPortion*LowerRate,Breakpoint*LowerRate+(OrdinaryPortion-Breakpoint)*UpperRate),
  TaxLTCG,LTCGPortion*0.15,
  TaxOrdinary+TaxLTCG
 )
)
```

### 6.12 `AMT_Owed`

```excel
=LAMBDA(RegularTaxableIncome,SALTAddback,OtherPreferences,LTCGPool,Status,FilingYear,RegularTax,
 MAX(0,AMT_Tax(RegularTaxableIncome,SALTAddback,OtherPreferences,LTCGPool,Status,FilingYear)-RegularTax)
)
```

### 6.13 `LTCG_Rate`

```excel
=LAMBDA(TaxableIncome,Status,FilingYear,
 LET(
  StatusL,LOWER(TRIM(Status)),
  IsSingle,OR(StatusL="single",StatusL="s"),
  ThresholdArray,IF(IsSingle,IF(tblTaxRateLTCG[Year]=FilingYear,tblTaxRateLTCG[Single]),IF(tblTaxRateLTCG[Year]=FilingYear,tblTaxRateLTCG[Jointly])),
  RateArray,IF(tblTaxRateLTCG[Year]=FilingYear,tblTaxRateLTCG[Rate]),
  XLOOKUP(TaxableIncome,ThresholdArray,RateArray,"",1,1)
 )
)
```

This uses upper ceilings with exact-or-next-larger matching. Nonmatching-year rows become FALSE rather than being removed. Statuses other than `Single` / `s` are treated as joint; this is not general filing-status support.

### 6.14 `NIIT_Threshold`

```excel
=LAMBDA(Status,FilingYear,
 LET(
  Match,(tblNIIT[Year]=FilingYear)*(LOWER(tblNIIT[Status])=LOWER(TRIM(Status))),
  XLOOKUP(1,Match,tblNIIT[Threshold])
 )
)
```

### 6.15 `NII_Buildup`

```excel
=LAMBDA(TaxableInterest,OrdinaryDividends,TotalCapGain,OtherPassiveIncome,
 TaxableInterest+OrdinaryDividends+TotalCapGain+OtherPassiveIncome
)
```

### 6.16 `NIIT_Tax`

```excel
=LAMBDA(MAGI,NetInvestmentIncome,Status,FilingYear,
 LET(
  Threshold,NIIT_Threshold(Status,FilingYear),
  MAGIExcess,MAX(0,MAGI-Threshold),
  NIITBase,MIN(NetInvestmentIncome,MAGIExcess),
  NIITBase*0.038
 )
)
```

There is no nonnegative clamp on `NetInvestmentIncome`, so negative NII can produce negative tax.

### 6.17 `SS_Taxable`

```excel
=LAMBDA(SSI,OtherIncome,Status,[MFSLivedApart],
 LET(
  StatusL,LOWER(TRIM(Status)),
  LivedApart,IF(ISOMITTED(MFSLivedApart),TRUE,MFSLivedApart),
  IsJoint,OR(StatusL="Jointly",StatusL="mfj"),
  IsMFS,OR(StatusL="MFS",StatusL="married filing separately"),
  Base1,IF(IsJoint,32000,IF(IsMFS,IF(LivedApart,25000,0),25000)),
  Base2,IF(IsJoint,44000,IF(IsMFS,IF(LivedApart,34000,0),34000)),
  Combined,OtherIncome+0.5*SSI,
  Excess,MAX(0,Combined-Base1),
  Tier1Width,Base2-Base1,
  Tier1,MIN(Excess,Tier1Width),
  Tier2,MAX(0,Excess-Tier1Width),
  FormulaAmount,0.5*Tier1+0.85*Tier2,
  Cap,0.85*SSI,
  IF(Combined<=Base1,0,MIN(FormulaAmount,Cap))
 )
)
```

The installed text differs in capitalization from the documented alternative. Excel's ordinary text equality is case-insensitive, so the capitalization difference alone does not establish the claimed joint-status defect in Excel. The documented lowercase form is clearer, but this specification does not assert a proven changed result from capitalization alone.

### 6.18 `LTCG_Bucket_Amount`

```excel
=LAMBDA(TaxableIncome,OrdinaryIncome,LTCGPool,BucketFloor,BucketCeiling,
 LET(
  FloorCap,MIN(TaxableIncome,BucketFloor),
  OrdinaryBelowFloor,MIN(OrdinaryIncome,FloorCap),
  ZeroPointBucket,MAX(0,FloorCap-OrdinaryBelowFloor),
  CeilingCap,MIN(TaxableIncome,BucketCeiling),
  OrdinaryBelowCeiling,MAX(OrdinaryIncome,BucketFloor),
  RoomInThisBucket,MAX(0,CeilingCap-OrdinaryBelowCeiling),
  LTCGUsedInLowerBuckets,MAX(0,MIN(BucketFloor,TaxableIncome)-MAX(OrdinaryIncome,0)-ZeroPointBucket),
  LTCGPoolRemaining,MAX(0,LTCGPool-MAX(0,BucketFloor-OrdinaryIncome)),
  MAX(0,MIN(RoomInThisBucket,LTCGPoolRemaining))
 )
)
```

`LTCGUsedInLowerBuckets` is calculated but unused. The documented library removes that binding; it does not change the returned expression.

## 7. Documented alternatives and reconciliation

These are extracted from `docx`, not applied as replacements to Name Manager. Their presence does not prove that the release notes describe the installed calculation accurately.

### 7.1 Documented `IncomeTax` — year-filtered arrays

```excel
=LAMBDA(TaxYear,FilingStatus,TaxableIncome,
 LET(
  Limits,FILTER(SWITCH(FilingStatus,"Single",tblTaxRate[Single],"Jointly",tblTaxRate[Jointly],NA()),tblTaxRate[Year]=TaxYear),
  Rates,FILTER(tblTaxRate[Rate],tblTaxRate[Year]=TaxYear),
  LowerLimits,VSTACK(0,DROP(Limits,-1)),
  SUM(MAP(LowerLimits,Limits,Rates,LAMBDA(Lower,Upper,Rate,MAX(0,MIN(TaxableIncome,Upper)-Lower)*Rate)))
 )
)
```

### 7.2 Documented `LTCGTax` — year-filtered arrays

```excel
=LAMBDA(TaxYear,FilingStatus,TaxableIncome,
 LET(
  Limits,FILTER(SWITCH(FilingStatus,"Single",tblTaxRateLTCG[Single],"Jointly",tblTaxRateLTCG[Jointly],NA()),tblTaxRateLTCG[Year]=TaxYear),
  Rates,FILTER(tblTaxRateLTCG[Rate],tblTaxRateLTCG[Year]=TaxYear),
  LowerLimits,VSTACK(0,DROP(Limits,-1)),
  SUM(MAP(LowerLimits,Limits,Rates,LAMBDA(Lower,Upper,Rate,MAX(0,MIN(TaxableIncome,Upper)-Lower)*Rate)))
 )
)
```

### 7.3 Documented `RMD` — embedded-factor alternative

```excel
=LAMBDA(DOB,CalcYear,PriorYearEndBalance,
 LET(
  Age,CalcYear-YEAR(DOB),
  StartAge,IF(DOB<DATE(1951,1,1),72,IF(DOB<DATE(1960,1,1),73,75)),
  Factors,{27.4;26.5;25.5;24.6;23.7;22.9;22;21.1;20.2;19.4;18.5;17.7;16.8;16;15.2;14.4;13.7;12.9;12.2;11.5;10.8;10.1;9.5;8.9;8.4;7.8;7.3;6.8;6.4;6;5.6;5.2;4.9;4.6;4.3;4.1;3.9;3.7;3.5;3.4;3.3;3.1;3;2.9;2.8;2.7;2.5;2.3;2},
  IF(OR(NOT(ISNUMBER(DOB)),NOT(ISNUMBER(CalcYear)),NOT(ISNUMBER(PriorYearEndBalance)),PriorYearEndBalance<0),NA(),
   IF(Age<MAX(StartAge,72),0,PriorYearEndBalance/IF(Age>=120,2,INDEX(Factors,Age-71))))
 )
)
```

This library version uses embedded factors covering ages 72–120. The installed `RMD` instead depends on the incomplete age table. The documented alternative also differs from `RMDOLD` by placing the factor selection inside the age test.

### 7.4 Documented `SS_Taxable`

```excel
=LAMBDA(SSI,OtherIncome,Status,[MFSLivedApart],
 LET(
  StatusL,LOWER(TRIM(Status)),
  LivedApart,IF(ISOMITTED(MFSLivedApart),TRUE,MFSLivedApart),
  IsJoint,OR(StatusL="jointly",StatusL="mfj"),
  IsMFS,OR(StatusL="mfs",StatusL="married filing separately"),
  Base1,IF(IsJoint,32000,IF(IsMFS,IF(LivedApart,25000,0),25000)),
  Base2,IF(IsJoint,44000,IF(IsMFS,IF(LivedApart,34000,0),34000)),
  Combined,OtherIncome+0.5*SSI,
  Excess,MAX(0,Combined-Base1),
  Tier1Width,Base2-Base1,
  Tier1,MIN(Excess,Tier1Width),
  Tier2,MAX(0,Excess-Tier1Width),
  IF(Combined<=Base1,0,MIN(0.5*Tier1+0.85*Tier2,0.85*SSI))
 )
)
```

The version history claims a lowercase-status fix. As noted in section 6.17, Excel case-insensitive equality means the claim needs verification rather than repetition as an established defect.

### 7.5 Other documentation differences

- `TaxRate`, `TaxRateLTCG`, `StandardDeduction_Basic`, `LTCG_Rate`, and `NII_Buildup` match the installed expressions apart from whitespace / formatting.
- `StandardDeduction_Full` documents `SeniorBonusMaxTotal=NumQualifying65*6000` directly; the installed version introduces `SeniorBonusMaxPerPerson=6000` first. Its intended returned expression is equivalent.
- `AMT_ExemptionRate`, `AMT_Exemption`, `AMT_Tax`, `NIIT_Threshold`, `NIIT_Tax`, and `LTCG_Bucket_Amount` use shorter bindings / inline intermediate expressions in the library. These do not constitute a demonstrated tax-logic correction.
- `AMT_Owed` matches the installed expression apart from whitespace.
- `RMDOLD` is installed but absent from the 17-row library.

## 8. Known limitations, unresolved inputs, and acceptance criteria

### 8.1 Existing limitations, not repaired

1. **Multi-year tax arrays:** installed `IncomeTax` and `LTCGTax` do not restrict the arrays actually used to the requested year. Use the documented alternatives only after an explicitly authorized reconciliation.
2. **Missing ordinary top bracket:** 2026 has only buckets 1–6; the visible ordinary estimator has only six allocation rows. Income exceeding the final available ceiling is not completely modeled.
3. **RMD coverage:** installed `RMD` uses factors only for ages 73–100; required age 72 and ages 101–119 can fail. Ages at least 120 use a hard-coded divisor.
4. **Possible RMD table-selection limitation:** the function always uses the Uniform Lifetime factor table and ignores spouse DOB. It does not select a different factor basis for any spouse-related situation; suitability was not tax-law validated.
5. **Selected year vs current year:** deduction functions use `YEAR(TODAY())`; selecting 2025 or another year does not change their age year or hard-coded add-on constants.
6. **Status coverage inconsistency:** `Separate` is absent from ordinary, LTCG and base-deduction tables. Social Security expects `MFS` or the full separately-filing phrase, not `Separate`. Other aliases accepted by one function may fail another.
7. **Social Security income basis:** `C21` sums `C13:C19` plus IRA conversion; that excludes RMD distributions in `C9`. There is also no explicit tax-exempt-interest input. Completeness of the provisional-income basis needs review.
8. **Loss / deduction simplifications:** carryovers are added directly, with no separate allocation or annual capital-loss limitation procedure; QBI is included directly in the same max/min calculation as Schedule A deductions. The label `Qualified Business Income` does not establish whether `C30` should contain income or a deduction amount.
9. **AMT simplification:** `AMT_Tax` uses a flat 15% for its preferential component, not a full 0% / 15% / 20% stacked schedule, and other preferences are manually entered.
10. **SALT blank behavior:** `J35` is blank, while `J37=MIN(J35,J36)` returns the cap in the inspected workbook because the blank reference is ignored by `MIN`. This should not be interpreted as a verified SALT deduction or addback.
11. **Unguarded ratios:** `D21=calcTaxableSocialSecurity/inpSocialSecurityBenefits` has an existing division error with zero Social Security input. `J27=I27/I26` and `M43=M39/calcAdjustedGrossIncome` can also fail for zero denominators.
12. **Negative-income defenses:** `NIIT_Tax` can return negative tax for negative investment income; `C33` and `C36` are not explicitly clamped to nonnegative taxable amounts.
13. **Library cells are formulas, not merely text:** the `docx!F5:F21` cells contain uninvoked LAMBDA expressions and report calculation errors. Their extracted formula text remains usable for documentation / Name Manager, but those cells are not valid numeric results.
14. **Broken defined names:** four legacy names have unresolved references, as listed in section 4.4. No safe replacement target was established.
15. **Finite terminal ceilings and formatting:** table sentinels are inconsistent; monetary / rate display formats are also inconsistent. Recommended normalizations have not been applied.
16. **Source freshness:** no 2027 table records exist, and AMT / NIIT tables have only 2026 records. Version planning text is not evidence that another year's figures are loaded.

### 8.2 Completed migration checks

- All 34 new single-cell names were found with their original absolute reference and intended original scope.
- The original names were removed after worksheet formula migration.
- The formula-library parameter identifiers were preserved separately from named-cell identifiers.
- The live tax sheet retained one existing formula error in the checked calculation area, at `D21`; it was not described as an error-free tax model.
- All six `TaxTables` styles, visible headers, and absent totals rows were read from the workbook.
- No table values, installed named-function definitions, or unresolved-name targets were replaced with assumed data.

### 8.3 Recommended rebuild / future-repair acceptance tests

These are proposed tests, not tests run during this naming-and-documentation task.

- Confirm all six tables exist with the exact names and headers above.
- Validate uniqueness of composite keys, increasing ceilings, complete annual / status coverage, and all required factor ages.
- Compare progressive-tax functions with independently computed piecewise expectations below, at, and above every bracket limit.
- Compare the visible ordinary estimator with `IncomeTax` after authorized function reconciliation, including income above the highest currently loaded bracket.
- Check that LTCG allocations sum to the nonnegative taxable preferential pool and use the correct stacked ordinary-income basis.
- Test Social Security at zero benefits, both provisional-income thresholds, positive RMD income, and separately-filing variants.
- Test RMD before start age, at start age, ages 72 / 73 / 100 / 101 / 119 / 120, invalid date inputs, zero balance, and negative balance.
- Test deduction age boundaries, January 1 DOB handling, optional spouse DOB omission, phaseout start / end, and selected tax year differing from current year.
- Test SALT blank, zero, below-cap and above-cap values before deciding on intended addback behavior.
- Test NIIT below / at / above threshold, negative NII, and zero denominators in all displayed ratios.
- Verify references after renaming, including formulas on other worksheets that use sheet-scoped names.

## 9. Secondary template structures

### 9.1 Schedule709

The source has a title in `A1`, an IRS form-reference URL in `A2`, and Excel Table `Table1` at `A6:M7` with one template body row. Its 13 headers are:

1. `(a) Item Number`
2. `(b) Donee's name and address`
3. `(c)` followed by line breaks around `Relationship` and `to donor`
4. `(d) Description of gift`
5. `(e) Donor’s adjusted basis of gift`
6. `(f) Date of gift`
7. `(g) Value at date of gift`
8. `(h) For split gifts, enter 1/2 of column (g)`
9. `(i) Net transfer (subtract col. (h) from col. (g))`
10. `(j) Reserved for future use`
11. `(k) Charitable gift`
12. `(l) Deductible gift to spouse`
13. `(m) 2652(a)(3) election`

This schedule was not modified. The URL is a workbook reference, not a source fetched for this specification. No gift-tax computation or populated gift-record dataset was inferred from the blank template row.

### 9.2 Formula library and version maintenance

`docx!A4:F4` headers are `Name`, `Category`, `Parameters`, `Description / Changes`, `Depends On`, and `Formula (paste into Name Manager > Refers to)`. The version scheme is `YYYY.MAJOR.MINOR[.PATCH]`, with metadata in rows 4–11 and change-history columns `Version`, `Date`, `Type`, `Area`, `Summary of Changes`, and `Notes` at row 14.

The recorded release still says `2026.3.0`; no new release number was invented for the naming conversion. A future release should reconcile installed names against documented definitions, then update the release log explicitly.
