"""Pydantic models: CSV table rows and filer inputs.

Row-model field names match the CSV headers verbatim (including
``FilingYear`` in tblStandDeductionBase).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

FilingStatus = Literal["Single", "Jointly", "Separate"]
InputType = Literal["int", "text", "date", "money"]
YearInt = Field(ge=1900, le=2200)
Money = Field(ge=0)
Rate = Field(ge=0, le=1)


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaxRateRow(_Row):
    Year: int = YearInt
    Bucket: int = Field(ge=1)
    Single: Decimal = Money
    Jointly: Decimal = Money
    Rate: Decimal = Rate


class TaxRateLTCGRow(TaxRateRow):
    pass


class UniformRMDFactorRow(_Row):
    Age: int = Field(ge=0, le=130)
    LifeExpectancyFactor: Decimal = Field(gt=0)


class StandDeductionBaseRow(_Row):
    FilingYear: int = YearInt
    Status: FilingStatus
    Amount: Decimal = Money


class AMTRow(_Row):
    Year: int = YearInt
    Status: FilingStatus
    Exemption: Decimal = Money
    Start: Decimal = Money
    End: Decimal = Money
    Breakpoint: Decimal = Money
    Lower: Decimal = Rate
    Upper: Decimal = Rate
    SaltCap: Decimal = Money

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.End <= self.Start:
            raise ValueError("End must be greater than Start")
        return self


class NIITRow(_Row):
    Year: int = YearInt
    Status: FilingStatus
    Threshold: Decimal = Money


class StatusAliasRow(_Row):
    Alias: str = Field(min_length=1)
    Canonical: FilingStatus


class ParameterRow(_Row):
    Year: int = YearInt
    Key: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    Single: Decimal
    Jointly: Decimal
    Separate: Decimal


class InputMapRow(_Row):
    Order: int = Field(ge=1)
    Name: str = Field(pattern=r"^inp[A-Za-z0-9]+$")
    Cell: str = Field(pattern=r"^[A-Z]{1,3}[0-9]{1,5}$")
    Type: InputType
    Field: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class FilerInputs(BaseModel):
    """Editable scenario inputs (fields mirror tblInputMap.csv)."""

    tax_year: int
    filing_status: FilingStatus
    dob: date
    spouse_dob: Optional[date] = None
    prior_ye_ira_balance: Decimal = Decimal(0)
    social_security_benefits: Decimal = Decimal(0)
    ira_conversion: Decimal = Decimal(0)
    qualified_dividends: Decimal = Decimal(0)
    taxable_interest: Decimal = Decimal(0)
    ordinary_dividends: Decimal = Decimal(0)
    additional_income: Decimal = Decimal(0)
    short_term_gain_loss: Decimal = Decimal(0)
    wages_and_tips: Decimal = Decimal(0)
    long_term_capital_gains: Decimal = Decimal(0)
    capital_loss_carryover: Decimal = Decimal(0)
    schedule_a_deductions: Decimal = Decimal(0)
    qualified_business_income: Decimal = Decimal(0)
    schedule_a_salt: Decimal = Decimal(0)
    amt_other_preferences: Decimal = Decimal(0)
    tax_withheld: Decimal = Decimal(0)
    additional_tax: Decimal = Decimal(0)
