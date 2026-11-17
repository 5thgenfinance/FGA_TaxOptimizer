# Fifth Generation Tax Optimizer: User Guide

Version 0.5.0

## 1. What it does
The tool estimates one year's federal income tax for a client. From the inputs you enter it works out the required minimum distribution (RMD) from a traditional IRA, how much Social Security is taxable, adjusted gross income (AGI), the deduction used, ordinary income tax, long-term capital gains tax, net investment income tax (NIIT), alternative minimum tax (AMT), and whether the client owes more or is due a refund.

It is a **planning estimate**. It is hypothetical, it follows simplified calculations, and it is not tax, legal or investment advice. Always confirm figures against the actual return.

## 2. Quick start
1. Open the app. The sidebar on the left holds the inputs.
2. In the **Filer** panel choose the tax year and filing status, and enter the date of birth.
3. Open the other panels and enter amounts. Hover over the **?** icon beside any input for guidance.
4. Read the **Results** tab. It updates as you type.
5. Click **Export scenario (JSON)** to save your work, or **Download PDF report** for a client-ready report.

## 3. The screen
- **Header band:** the firm name and the product name. It stays in view as you scroll.
- **Sidebar:** the **Inputs** heading, then the panels **Scenario: import / export**, **Options**, and one panel per input category.
- **Report title:** the large italic field at the top of the page. Type the client name or a scenario name. It becomes the title of the PDF and the name of exported files.
- **Tabs:** **Results** (the estimate), **Tables** (the tax tables the app uses) and **Status** (data checks and version).
- **Footer:** disclosure and the application version.

## 4. Entering inputs
Amounts are in dollars, with no dollar signs or commas needed. Enter a loss as a **negative** number. A blank amount counts as zero. Two inputs are optional and have a check box: tick it to enter a value.

| Panel | Input | What to enter |
|---|---|---|
| Filer | Tax year | Year of the return. Only years with complete tax tables are listed. |
| Filer | Filing status | Single, or Jointly. Married filing separately is not supported yet. |
| Filer | Date of birth | Primary filer. Sets the RMD start age and the age-65 standard deduction additions. |
| Filer | Spouse date of birth (joint filers) | Optional. Tick the box to enter it. Adds the spouse's age-65 additions. |
| Retirement | IRA balance, prior year-end | Traditional IRA balance on December 31 of the prior year. The RMD is calculated from it. |
| Retirement | Social Security benefits | Total benefits for the year. The app calculates the taxable part (up to 85%). |
| Retirement | IRA (Roth) conversion | Amount converted to a Roth IRA. Taxed as ordinary income. |
| Investments | Qualified dividends | The qualified part of dividends (Form 1040 line 3a). Also include it in Ordinary dividends. |
| Investments | Taxable interest | Form 1040 line 2b. |
| Investments | Ordinary dividends | Total dividends, Form 1040 line 3b, including the qualified part. |
| Investments | Short-term capital gain/loss | Net amount, taxed as ordinary income. Loss is negative. |
| Investments | Long-term capital gains | Net amount, taxed at 0%, 15% or 20%. Loss is negative. |
| Investments | Capital loss carryover | Loss carried in from earlier years. Enter as a negative number. |
| Other income | Additional income (Schedule 1) | Other Schedule 1 income, Form 1040 line 8. |
| Other income | Wages and tips | Before tax (W-2 box 1). |
| Deductions | Gifts and Schedule A deductions | Itemized deductions including charitable gifts. The larger of this and the standard deduction is used, within a limit of 60% of AGI. |
| Deductions | Qualified business income | Added to the Schedule A amount in the deduction test, as in the Excel workbook. Its intended meaning is an open question; leave at 0 unless you know how you want it treated. |
| AMT | Schedule A state, local and property taxes | Optional. Tick the box to enter it. Used for the AMT addback, capped at the year's SALT cap. Unticked counts as zero. |
| AMT | AMT other preferences | Other AMT adjustments (Form 6251). Leave at 0 if none. |
| Payments | Tax withheld | Federal tax already withheld. |
| Payments | Additional tax paid | Other payments such as quarterly estimates. Added to tax withheld. |

## 5. Importing and exporting a scenario
### Export
Open **Scenario: import / export** and click **Export scenario (JSON)**. The file name comes from the report title. The file holds the title, a last-updated time and every input. The app does not keep scenarios on its own, so exported files are how you save and share work. Store them securely.

### Import a JSON file
Use the uploader in the same panel. The forms fill in, and the report title and last-updated time are restored. Problems are listed in plain language, for example an unsupported tax year or an unrecognised filing status. A file with a wrong data type is rejected, and every error is listed.

### Import the Excel template
You can upload the TaxRetirementOptimizer workbook (.xlsx or .xlsm) directly. The app converts it to scenario JSON, fills the forms, and tells you how many inputs it filled and how many were blank. Click **Export scenario (JSON)** afterwards if you also want the JSON file.

- Save the workbook in Excel first. The app reads the values stored in the file, so unsaved changes are not seen.
- The app finds each input by its named range. Workbooks from before the naming change are recognised by their old names, and the app says so.
- If a named range is missing, the app reads the fixed cell address and lists those inputs. Check them.
- The report title comes from the file name (underscores become spaces) unless the workbook's version sheet has a title in B12. Edit it as you like.
- Only the sheet named TaxSheetSingle is read. Old .xls files and password-protected files are not supported.

## 6. Reading the results
The **Results** tab opens with two rows of headline figures:
- **Total tax**, **Amount due** (or **Refund**), **Effective rate (of AGI)** and **Marginal ordinary rate** (the top ordinary bracket that holds any income).
- **Adjusted gross income**, **Taxable ordinary income**, **Required minimum distribution** and **Standard deduction**.

Below them, yellow warnings explain anything unusual, such as income above the top loaded bracket. Expandable sections follow: Income, Deductions, Tax, Alternative minimum tax and Summary, then the ordinary income and long-term capital gains bracket tables ('No limit' marks the top bracket).

**Download PDF report** produces a report with the title, the headline figures, every section, both bracket tables, the inputs grouped as in the form, and a planning-use disclaimer.

## 7. Options
- **Reproduce workbook (legacy mode):** matches the Excel workbook exactly, including its known quirks. Leave it off for normal use. Use it to check the app against the workbook.
- **Reload tables:** re-reads the tax tables after they have been updated.

## 8. Tables and Status tabs
**Tables** shows any tax table the app uses, so you can see the brackets and factors behind a result. **Status** confirms the tables loaded and validated, shows the supported tax years, the application version and the Excel workbook version the calculations were built from, and lists any table warnings.

## 9. Worked example
Check your setup with this case. Set the tax year to 2026, filing status **Jointly**, date of birth 1952-04-14, tick the spouse box and enter 1974-09-30. Then enter: IRA balance 1,000,000; qualified dividends 1,800; taxable interest 900; ordinary dividends 2,400; short-term loss -3,000; wages 145,000; long-term gains 6,000; Schedule A deductions 12,000; tax withheld 16,500.

Turn on legacy mode and you should see total tax of about $22,559, an amount due of about $6,059, AGI of about $190,516, a standard deduction of $37,419 and an RMD of about $39,216. With legacy mode off, total tax is the same; only the AMT detail differs.

## 10. Limits to keep in mind
- Supported years are those listed in the Tax year box, currently 2026 and 2027.
- Married filing separately is not supported.
- There is no input for tax-exempt interest, so provisional income for Social Security is understated if the client has any.
- RMD factors cover ages 72 to 120.
- The 2027 SALT cap is derived from the statute and is flagged in the project plan for verification.
- Do not enter real client identifiers or account details in the hosted app until access control has been decided (PROJECT_PLAN.md section 11).

## 11. Troubleshooting
| You see | What to do |
|---|---|
| 'Cannot calculate: ...' on Results | Read the message; it names the problem, for example an age outside the RMD table. Correct the input. |
| 'Table validation failed' | A tax table has a data error. The messages say which. Fix the file in data/ and click Reload tables. |
| Upload says it is not an Excel workbook | The file is not .xlsx or .xlsm, is damaged, or is password protected. Re-save it in Excel. |
| Upload says the worksheet TaxSheetSingle was not found | This is not the template. Open the right workbook. |
| Many inputs read 0 after an Excel upload | The cells are blank, or the file was not saved after calculating. Save it in Excel and upload again. |
| 'Used old input names' warning | The workbook predates the naming change. It still loaded correctly; consider updating the workbook. |
| 'Read by cell address' warning | A named range is missing. Check the listed inputs against the workbook. |
| Unsupported tax year or filing status on import | That value was ignored. Choose it manually if it is available. |
| A tooltip says an input is optional | Tick the box beside it to enter a value. |

## 12. Terms
- **AGI:** adjusted gross income.
- **AMT:** alternative minimum tax, a parallel tax calculation.
- **NIIT:** the 3.8% net investment income tax on high incomes.
- **QBI:** qualified business income.
- **RMD:** required minimum distribution from a traditional IRA, starting at age 72, 73 or 75 depending on birth year.
- **SALT:** state and local taxes, capped for the AMT addback.
- **Legacy mode:** reproduces the Excel workbook including its known defects.
