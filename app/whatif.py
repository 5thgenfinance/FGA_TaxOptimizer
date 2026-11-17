"""What-if adjustments to a scenario (no Streamlit import, so it is testable).

The sliders on the What-if tab never change the real inputs. They build a copy of the inputs with
four adjustments and compare the engine's results for the copy with the results for the original.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from app import report

D = Decimal
SLIDER_KEYS = {"ltcg": "wi_ltcg", "stcg": "wi_stcg", "extra_deductions": "wi_deductions", "extra_ira": "wi_ira"}


@dataclass(frozen=True)
class Adjustments:
    """Dollar changes to apply on top of the entered inputs."""

    ltcg: Decimal = D(0)               # added to long-term capital gains (negative removes gains)
    stcg: Decimal = D(0)               # added to short-term capital gain/loss (negative removes gains)
    extra_deductions: Decimal = D(0)   # added to Schedule A deductions
    extra_ira: Decimal = D(0)          # added as taxable ordinary income from the IRA

    @property
    def is_zero(self) -> bool:
        return not (self.ltcg or self.stcg or self.extra_deductions or self.extra_ira)

    @property
    def income_change(self) -> Decimal:
        """Net change in income (deductions are not income)."""
        return self.ltcg + self.stcg + self.extra_ira


def _num(value: Any) -> Decimal:
    return D(str(value or 0))


def adjusted_inputs(inputs: Any, adjustments: Adjustments) -> Any:
    """A copy of ``inputs`` with the adjustments applied.

    An extra IRA distribution is taxed as ordinary income exactly like a Roth conversion, so it is
    added to the IRA (Roth) conversion line. It does not change the required minimum distribution.
    """
    return inputs.model_copy(update={
        "long_term_capital_gains": _num(inputs.long_term_capital_gains) + adjustments.ltcg,
        "short_term_gain_loss": _num(inputs.short_term_gain_loss) + adjustments.stcg,
        "schedule_a_deductions": _num(inputs.schedule_a_deductions) + adjustments.extra_deductions,
        "ira_conversion": _num(inputs.ira_conversion) + adjustments.extra_ira,
    })


def signed_money(value: Decimal) -> str:
    """'+$1,200', '-$300' or '$0'."""
    rounded = int(value.quantize(D(1)))
    if rounded == 0:
        return "$0"
    return f"+${rounded:,}" if rounded > 0 else f"-${-rounded:,}"


def signed_points(old: Decimal | None, new: Decimal | None) -> str:
    """Change between two rates in percentage points, e.g. '+1.25 pts'."""
    if old is None or new is None:
        return "n/a"
    points = (new - old) * 100
    if abs(points) < D("0.005"):
        return "0.00 pts"
    return f"{points:+.2f} pts"


def tax_on_the_change(base: Any, alt: Any, adjustments: Adjustments) -> Decimal | None:
    """Extra tax divided by the net income added (None when no income was added or removed)."""
    if adjustments.income_change == 0:
        return None
    return (alt.total_tax - base.total_tax) / adjustments.income_change


def _room(result: Any, inputs: Any) -> Decimal | None:
    return report.zero_ltcg_room(result)[0]


# (label, value function, kind) where kind is 'money' or 'rate'
MEASURES: list[tuple[str, Callable[[Any, Any], Decimal | None], str]] = [
    ("Total tax", lambda r, i: r.total_tax, "money"),
    ("Amount due (refund if negative)", lambda r, i: r.due_or_refund, "money"),
    ("Effective rate (of AGI)", lambda r, i: r.effective_rate, "rate"),
    ("Marginal ordinary rate", lambda r, i: report.marginal_ordinary_rate(r), "rate"),
    ("Adjusted gross income", lambda r, i: r.agi, "money"),
    ("Taxable Social Security", lambda r, i: r.taxable_social_security, "money"),
    ("Taxable ordinary income", lambda r, i: r.taxable_ordinary, "money"),
    ("Taxable preferential income", lambda r, i: r.taxable_preferential, "money"),
    ("Ordinary income tax", lambda r, i: r.ordinary_tax, "money"),
    ("Long-term capital gains tax", lambda r, i: r.ltcg_tax, "money"),
    ("Net investment income tax", lambda r, i: r.niit, "money"),
    ("AMT owed", lambda r, i: r.amt_owed, "money"),
    ("Additional LTCG at 0%", _room, "money"),
    ("Left before Schedule A", report.itemizing_gap, "money"),
]


def comparison(base: Any, base_inputs: Any, alt: Any, alt_inputs: Any) -> list[dict[str, str]]:
    """Rows for the comparison table: Measure, Current, What-if, Change."""
    rows = []
    for label, value, kind in MEASURES:
        old, new = value(base, base_inputs), value(alt, alt_inputs)
        if kind == "rate":
            places = 0 if label.startswith("Marginal") else 2
            rows.append({"Measure": label, "Current": report.fmt_rate(old, places),
                         "What-if": report.fmt_rate(new, places), "Change": signed_points(old, new)})
        else:
            rows.append({"Measure": label,
                         "Current": "n/a" if old is None else report.fmt_money(old),
                         "What-if": "n/a" if new is None else report.fmt_money(new),
                         "Change": "n/a" if old is None or new is None else signed_money(new - old)})
    return rows
