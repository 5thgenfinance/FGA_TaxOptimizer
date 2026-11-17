"""Tax curves and planning guidance for the What-if levers (no Streamlit import, so it is testable).

Each lever (long-term gains, short-term gains, extra Schedule A deductions, extra IRA distribution)
is swept over a range while the other sliders stay where the user left them. ``run(x)`` must return
an engine result for lever value ``x`` (or None if it cannot be calculated).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from app import report

D = Decimal
LEVERS = ("ltcg", "stcg", "extra_deductions", "extra_ira")
RANGES = {"ltcg": (-50_000, 250_000), "stcg": (-50_000, 100_000), "extra_deductions": (0, 100_000),
          "extra_ira": (0, 250_000)}
GRID_STEP = 5_000
PROBE = 1_000          # size of the step used to measure the tax on the next dollars
TOLERANCE = 100        # thresholds are found to the nearest 100 dollars
ZERO_RATE_CAP = D("0.001")
MARGINAL_CAPS = (10, 12, 22, 24, 32, 35, 37)


def first_exceed(rate: Callable[[int, int], Decimal | None], xs: list[int], taxes: list[Decimal], cap: Decimal,
                 probe: int = PROBE, tolerance: int = TOLERANCE) -> int:
    """The amount (from 0 upward) at which the tax on the next dollars first exceeds ``cap``.

    The coarse grid finds the first interval whose average rate is above the cap; bisection then
    narrows it to ``tolerance`` dollars. Returns the last grid amount if the cap is never exceeded.
    """
    ordered = [(x, t) for x, t in zip(xs, taxes) if x >= 0]
    for (x0, t0), (x1, t1) in zip(ordered, ordered[1:]):
        if (t1 - t0) / D(x1 - x0) > cap:
            low, high = x0, x1
            while high - low > tolerance:
                mid = (low + high) // 2
                value = rate(mid, mid + probe)
                if value is None:
                    break
                if value > cap:
                    high = mid
                else:
                    low = mid
            return low
    return ordered[-1][0] if ordered else 0


def analyze(run: Callable[[int], Any], lever: str, lo: int | None = None, hi: int | None = None,
            step: int = GRID_STEP, cap_percent: int | None = None, gap: float | None = None,
            probe: int = PROBE) -> dict:
    """Sample the tax over the lever's range and find the thresholds that matter for planning."""
    if lo is None or hi is None:
        lo, hi = RANGES[lever]
    cache: dict[int, Any] = {}

    def at(x: int):
        if x not in cache:
            cache[x] = run(x)
        return cache[x]

    def tax(x: int) -> Decimal | None:
        result = at(x)
        return None if result is None else result.total_tax

    def rate(x0: int, x1: int) -> Decimal | None:
        t0, t1 = tax(x0), tax(x1)
        return None if t0 is None or t1 is None else (t1 - t0) / D(x1 - x0)

    xs = [x for x in range(lo, hi + 1, step) if at(x) is not None]
    out: dict = {"lever": lever, "points": [], "tax0": None, "lo": lo, "hi": hi}
    if 0 not in xs:
        return out
    taxes = [tax(x) for x in xs]
    for i, x in enumerate(xs):
        j = i + 1 if i + 1 < len(xs) else i - 1
        slope = (taxes[j] - taxes[i]) / D(xs[j] - xs[i]) if j >= 0 and xs[j] != xs[i] else None
        out["points"].append((x, float(taxes[i]), None if slope is None else float(slope),
                              float(at(x).taxable_social_security)))
    tax0 = tax(0)
    out["tax0"] = float(tax0)
    ss0 = float(at(0).taxable_social_security)
    out["ss_rises"] = any(p[3] > ss0 + 1 for p in out["points"] if p[0] > 0)
    up = rate(0, probe) if hi >= probe else None
    out["up_rate"] = None if up is None else float(up)
    down = rate(-probe, 0) if lo <= -probe else None
    out["down_rate"] = None if down is None else float(down)

    if lever == "ltcg":
        free = first_exceed(rate, xs, taxes, ZERO_RATE_CAP, probe)
        after = rate(free, free + probe) if free + probe <= hi else None
        out["free_amount"] = free
        out["after_free_rate"] = None if after is None else float(after)
    elif lever == "extra_ira" and cap_percent is not None:
        amount = first_exceed(rate, xs, taxes, D(cap_percent) / 100 + D("0.0005"), probe)
        added = tax(amount)
        out["cap_percent"] = cap_percent
        out["cap_amount"] = amount
        out["cap_added_tax"] = None if added is None else float(added - tax0)
    elif lever == "extra_deductions" and gap is not None:
        out["gap"] = gap
        start = int(-(-gap // 1))  # round up to a whole dollar
        saving = rate(start, start + probe) if start + probe <= hi else None
        out["saving_rate"] = None if saving is None else float(-saving)
    return out


def _m(value: float) -> str:
    return report.fmt_money(D(str(round(value))))


def guidance(analysis: dict, current: int) -> list[str]:
    """Plain-language planning notes for one lever, from its analysis."""
    if not analysis.get("points"):
        return ["This lever could not be calculated for the current inputs."]
    lever, up, down = analysis["lever"], analysis.get("up_rate"), analysis.get("down_rate")
    notes: list[str] = []
    if lever == "ltcg":
        free = analysis.get("free_amount", 0)
        if free >= TOLERANCE:
            notes.append(f"Up to about {_m(free)} more long-term gain adds no federal tax.")
            after = analysis.get("after_free_rate")
            if after is not None:
                notes.append(f"Past that point the next {_m(PROBE)} costs about {_m(after * PROBE)} ({after:.0%}).")
            if current > free:
                notes.append(f"Your setting is {_m(current - free)} above the no-tax zone.")
            elif current > 0:
                notes.append(f"Your setting uses {_m(current)} of the no-tax zone.")
        elif up is not None:
            notes.append(f"Extra long-term gains add tax right away: about {_m(up * PROBE)} per {_m(PROBE)} ({up:.1%}).")
        if down is not None and down > 0:
            notes.append(f"Removing {_m(PROBE)} of gains saves about {_m(down * PROBE)}.")
    elif lever == "stcg":
        if up is not None:
            notes.append(f"Each added {_m(PROBE)} of short-term gain costs about {_m(up * PROBE)} ({up:.0%}) here, "
                         "because short-term gains are taxed as ordinary income.")
        if down is not None and down > 0:
            notes.append(f"Each {_m(PROBE)} of short-term gain removed or offset by losses saves about {_m(down * PROBE)}.")
        notes.append("Compare with the long-term chart: gains held over a year are usually taxed at lower rates.")
    elif lever == "extra_deductions":
        gap, saving = analysis.get("gap"), analysis.get("saving_rate")
        if gap is not None and gap > 0:
            notes.append(f"You need {_m(gap)} more deductions before itemizing beats the standard deduction; "
                         "the first part of that saves no tax.")
            if saving is not None:
                notes.append(f"Beyond that point each added {_m(PROBE)} saves about {_m(saving * PROBE)} ({saving:.0%}).")
            notes.append("If gifts or other deductions can be timed, bunching them into one year can cross this threshold.")
        elif saving is not None:
            notes.append(f"You already itemize. Each added {_m(PROBE)} of deductions saves about {_m(saving * PROBE)} ({saving:.0%}).")
    elif lever == "extra_ira":
        if up is not None:
            notes.append(f"The next {_m(PROBE)} of IRA income is taxed at about {up:.0%} ({_m(up * PROBE)}).")
        cap = analysis.get("cap_percent")
        if cap is not None:
            amount = analysis.get("cap_amount", 0)
            added = analysis.get("cap_added_tax")
            if amount < TOLERANCE:
                notes.append(f"Any more IRA income is already taxed above {cap}% on the margin.")
            else:
                limit = "to the top of the slider range" if amount >= analysis["hi"] else f"up to about {_m(amount)}"
                extra = "" if added is None else f" (extra tax about {_m(added)})"
                notes.append(f"To keep each added dollar at or below a {cap}% rate, add {limit}{extra}.")
    if analysis.get("ss_rises") and lever in ("ltcg", "stcg", "extra_ira"):
        notes.append("Part of this range makes more Social Security taxable, so the tax on the next dollar can be "
                     "higher than the bracket rate.")
    return notes
