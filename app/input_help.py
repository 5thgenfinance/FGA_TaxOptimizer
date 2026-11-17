"""Tooltip text for every input in data/tblInputMap.csv, keyed by the FilerInputs field name.

The text is shown through the ``help=`` argument of each Streamlit widget (the "?" icon).
A test fails if an input has no tooltip, so adding a row to tblInputMap.csv means adding one here.
"""
from __future__ import annotations

HELP: dict[str, str] = {
    "tax_year": "The year of the return being estimated. Only years with a complete set of tax tables are listed.",
    "filing_status": "Single, or Jointly for married filing jointly. Married filing separately is not supported yet.",
    "dob": "Primary filer's date of birth. It sets the required minimum distribution (RMD) start age and the age-65 "
           "additions to the standard deduction.",
    "spouse_dob": "Check the box to enter a spouse's date of birth (joint filers). It adds the spouse's age-65 "
                  "standard deduction addition and senior bonus.",
    "prior_ye_ira_balance": "Traditional IRA balance on December 31 of the prior year. The RMD is this balance divided "
                            "by the IRS Uniform Lifetime Table factor for the filer's age.",
    "social_security_benefits": "Total Social Security benefits for the year, before any tax. The app works out how "
                                "much is taxable (up to 85%).",
    "ira_conversion": "Amount converted from a traditional IRA to a Roth IRA this year. It is taxed as ordinary income "
                      "and counts toward Social Security taxation.",
    "qualified_dividends": "The qualified part of your dividends (Form 1040 line 3a), taxed at long-term capital gain "
                           "rates. Also include it in Ordinary dividends.",
    "taxable_interest": "Taxable interest income (Form 1040 line 2b). It is taxed as ordinary income and counts as "
                        "net investment income.",
    "ordinary_dividends": "Total ordinary dividends (Form 1040 line 3b), including the qualified part entered above.",
    "additional_income": "Other income from Schedule 1 (Form 1040 line 8), taxed as ordinary income. Leave at 0 if none.",
    "short_term_gain_loss": "Net short-term capital gain or loss, taxed as ordinary income. Enter a loss as a "
                            "negative number.",
    "wages_and_tips": "Wages, salaries and tips before tax (W-2 box 1). Taxed as ordinary income.",
    "long_term_capital_gains": "Net long-term capital gain or loss. Gains are taxed at the 0%, 15% and 20% rates, "
                               "stacked on top of ordinary income. Enter a loss as a negative number.",
    "capital_loss_carryover": "Capital loss carried over from earlier years. It is added directly to your gains, so "
                              "enter a loss as a negative number.",
    "schedule_a_deductions": "Itemized deductions from Schedule A, including charitable gifts. The larger of this and "
                             "the standard deduction is used, within a limit of 60% of AGI.",
    "qualified_business_income": "Added to the Schedule A amount in the deduction test, exactly as the Excel workbook "
                                 "does. Its intended meaning is still an open question, so leave it at 0 unless you "
                                 "know how you want it treated.",
    "schedule_a_salt": "Check the box to enter state, local and property taxes paid (Schedule A). It feeds the AMT "
                       "addback and is capped at the year's SALT cap. Unchecked counts as zero.",
    "amt_other_preferences": "Other alternative minimum tax adjustments and preference items (Form 6251), added to the "
                             "AMT base. Leave at 0 if none.",
    "tax_withheld": "Federal income tax already withheld for the year (wages, pensions, IRA distributions).",
    "additional_tax": "Other tax already paid for the year, such as quarterly estimated payments. It is added to tax "
                      "withheld to get total tax paid.",
}


def help_for(field: str) -> str:
    """Tooltip text for an input field name ('' if there is none)."""
    return HELP.get(field, "")
