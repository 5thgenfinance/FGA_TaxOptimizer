"""Orchestrates the TaxSheetSingle calculation (spec section 5.2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.calc import amt, deductions, ltcg, niit, ordinary, rmd, socialsec
from app.calc.common import ZERO, MissingDataError, dec, get_param
from app.models import FilerInputs
from app.status import normalize_status
from app.tables import Tables, get_tables

LEGACY_ORDINARY_BUCKETS = 6  # the workbook estimator has six allocation rows
LEGACY_LTCG_BUCKETS = 3


@dataclass
class TaxResult:
    filing_status: str
    tax_year: int
    legacy: bool
    as_of_year: int
    rmd: Decimal
    taxable_social_security: Decimal
    preferential_subtotal: Decimal
    agi: Decimal
    medical_threshold: Decimal
    cash_deduction_limit: Decimal
    standard_deduction: Decimal
    applicable_deduction: Decimal
    adjusted_taxable_income: Decimal
    ordinary_income: Decimal
    taxable_ordinary: Decimal
    taxable_preferential: Decimal
    ordinary_allocations: list
    ltcg_allocations: list
    ordinary_tax: Decimal
    ltcg_tax: Decimal
    regular_tax: Decimal
    net_investment_income: Decimal
    niit_threshold: Decimal
    niit: Decimal
    salt_cap: Decimal
    salt_addback: Decimal
    amt_exemption_rate: Decimal
    amt_exemption: Decimal
    amt_tentative: Decimal
    amt_owed: Decimal
    total_tax: Decimal
    tax_paid: Decimal
    due_or_refund: Decimal
    effective_rate: Decimal | None
    ltcg_effective_rate: Decimal | None
    taxable_ss_share: Decimal | None
    warnings: list = field(default_factory=list)


def _ratio(num: Decimal, den: Decimal) -> Decimal | None:
    return None if den == 0 else num / den


def compute(inputs: FilerInputs, tables: Tables | None = None, legacy: bool = False,
            as_of_year: int | None = None) -> TaxResult:
    """Run the full estimate.

    legacy=True reproduces the workbook: six ordinary rows, TODAY()-based age
    year, blank SALT = full cap, RMD left out of Social Security provisional
    income, flat-rate AMT on capital gains, and no NII or taxable-income clamps.
    legacy=False applies the planned fixes: tax-year-based age, RMD included in
    provisional income, AMT capital gains stacked at 0/15/20%, clamps, and
    every bracket in the tables. Zero-denominator ratios return None in both modes.
    """
    t = tables or get_tables()
    status = normalize_status(inputs.filing_status, t)
    year = inputs.tax_year
    if year not in t.supported_years():
        raise MissingDataError(f"Tax year {year} is not loaded in every required table")
    as_of = as_of_year or (date.today().year if legacy else year)
    warnings: list[str] = []

    wages, st, lt = dec(inputs.wages_and_tips), dec(inputs.short_term_gain_loss), dec(inputs.long_term_capital_gains)
    carry, qd = dec(inputs.capital_loss_carryover), dec(inputs.qualified_dividends)
    interest, od = dec(inputs.taxable_interest), dec(inputs.ordinary_dividends)
    addl, conv = dec(inputs.additional_income), dec(inputs.ira_conversion)
    ssi = dec(inputs.social_security_benefits)

    distribution = rmd.calc_rmd(inputs.dob, year, inputs.prior_ye_ira_balance, t)
    pref_subtotal = lt + carry + qd
    other_income = interest + od + addl + st + wages + lt + carry + conv
    if not legacy:
        other_income += distribution
    taxable_ss = socialsec.taxable_ss(ssi, other_income, status, t, year)
    agi = distribution + taxable_ss + conv + st + wages + lt + interest + od + addl + carry

    medical_threshold = get_param(t, year, "MedicalAGIFloor", status) * agi
    cash_limit = get_param(t, year, "CashDeductionAGILimit", status) * agi

    base = deductions.base_standard_deduction(t, year, status)
    spouse = inputs.spouse_dob if status == "Jointly" else None
    std = deductions.standard_deduction_full(inputs.dob, status, base, agi, as_of, t, year, spouse)
    applicable = max(min(dec(inputs.schedule_a_deductions) + dec(inputs.qualified_business_income),
                         cash_limit), std)

    ati = agi - applicable
    ordinary_income = agi - pref_subtotal
    taxable_ordinary = max(ordinary_income - applicable, ZERO)
    taxable_pref = lt + qd + carry - max(ZERO, applicable - ordinary_income)
    if not legacy:
        ati = max(ati, ZERO)
        taxable_pref = max(taxable_pref, ZERO)

    ord_brackets = ordinary.get_brackets(t, "tblTaxRate", year, status)
    if legacy:
        ord_brackets = ord_brackets[:LEGACY_ORDINARY_BUCKETS]
    ord_alloc = ordinary.allocate(taxable_ordinary, ord_brackets)
    ord_tax = ordinary.total_tax(ord_alloc)
    if ordinary.exceeds_top_bracket(taxable_ordinary, ord_brackets):
        warnings.append("Taxable ordinary income exceeds the highest bracket in tblTaxRate; "
                        "the excess is not taxed. Add the top bracket to the CSV.")

    ltcg_brackets = ltcg.ltcg_brackets(t, year, status)
    if legacy:
        ltcg_brackets = ltcg_brackets[:LEGACY_LTCG_BUCKETS]
    ltcg_alloc = ltcg.stacked(ati, taxable_ordinary, taxable_pref, ltcg_brackets)
    ltcg_tax_amount = ordinary.total_tax(ltcg_alloc)
    regular = ord_tax + ltcg_tax_amount

    nii = niit.nii_buildup(interest, od, st + lt + carry)
    threshold = niit.niit_threshold(t, year, status)
    niit_amount = niit.niit_tax(agi, nii, t, year, status, clamp_nii=not legacy)

    cap = amt.salt_cap(t, year, status)
    salt_add = amt.salt_addback(inputs.schedule_a_salt, cap, legacy)
    if inputs.schedule_a_salt is None and not legacy:
        warnings.append("Schedule A SALT is blank: the AMT SALT addback is treated as 0. "
                        "The workbook treats a blank as the full cap.")
    other_prefs = dec(inputs.amt_other_preferences)
    amti = ati + salt_add + other_prefs
    amt_rate = amt.exemption_rate(t, year, status)
    amt_ex = amt.exemption(amti, t, year, status)
    stacked = not legacy
    amt_tent = amt.tentative_tax(ati, salt_add, other_prefs, taxable_pref, t, year, status, stacked)
    amt_due = amt.amt_owed(ati, salt_add, other_prefs, taxable_pref, t, year, status, regular, stacked)

    total = regular + niit_amount + amt_due
    paid = dec(inputs.tax_withheld) + dec(inputs.additional_tax)
    pref_alloc_total = sum((a.amount for a in ltcg_alloc), ZERO)

    return TaxResult(
        filing_status=status, tax_year=year, legacy=legacy, as_of_year=as_of,
        rmd=distribution, taxable_social_security=taxable_ss,
        preferential_subtotal=pref_subtotal, agi=agi,
        medical_threshold=medical_threshold, cash_deduction_limit=cash_limit,
        standard_deduction=std, applicable_deduction=applicable,
        adjusted_taxable_income=ati, ordinary_income=ordinary_income,
        taxable_ordinary=taxable_ordinary, taxable_preferential=taxable_pref,
        ordinary_allocations=ord_alloc, ltcg_allocations=ltcg_alloc,
        ordinary_tax=ord_tax, ltcg_tax=ltcg_tax_amount, regular_tax=regular,
        net_investment_income=nii, niit_threshold=threshold, niit=niit_amount,
        salt_cap=cap, salt_addback=salt_add, amt_exemption_rate=amt_rate,
        amt_exemption=amt_ex, amt_tentative=amt_tent, amt_owed=amt_due,
        total_tax=total, tax_paid=paid, due_or_refund=total - paid,
        effective_rate=_ratio(total, agi),
        ltcg_effective_rate=_ratio(ltcg_tax_amount, pref_alloc_total),
        taxable_ss_share=_ratio(taxable_ss, ssi),
        warnings=warnings,
    )
