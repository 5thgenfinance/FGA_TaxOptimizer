from decimal import Decimal
from types import SimpleNamespace

from app import curves

D = Decimal


def make_run(base_income, brackets, extra_for=None, ss=lambda x: 0):
    """A stand-in engine: tax is progressive on base_income + x. brackets = [(upper_limit, rate), ...]."""
    def tax_on(income):
        income, lower, tax = D(income), D(0), D(0)
        for limit, rate in brackets:
            if income > lower:
                tax += (min(income, D(limit)) - lower) * D(rate)
            lower = D(limit)
        return tax

    def run(x):
        if x < -base_income:
            return None
        return SimpleNamespace(total_tax=tax_on(base_income + x), taxable_social_security=D(ss(x)))
    return run


BRACKETS = [(10_000, "0.10"), (40_000, "0.12"), (90_000, "0.22"), (10**9, "0.24")]


def test_first_exceed_finds_the_bracket_edge_to_the_nearest_hundred():
    run = make_run(20_000, BRACKETS)
    out = curves.analyze(run, "extra_ira", 0, 250_000, cap_percent=12)
    assert abs(out["cap_amount"] - 20_000) <= curves.TOLERANCE  # 12% bracket ends at 40,000 of income
    assert out["cap_added_tax"] > 0


def test_a_cap_that_is_never_exceeded_returns_the_top_of_the_range():
    run = make_run(0, [(10**9, "0.10")])
    out = curves.analyze(run, "extra_ira", 0, 250_000, cap_percent=12)
    assert out["cap_amount"] == 250_000
    assert "top of the slider range" in " ".join(curves.guidance(out, 0))


def test_a_cap_below_the_current_rate_leaves_no_room():
    run = make_run(95_000, BRACKETS)  # already in the 24% bracket
    out = curves.analyze(run, "extra_ira", 0, 250_000, cap_percent=12)
    assert out["cap_amount"] < curves.TOLERANCE
    assert "already taxed above 12%" in " ".join(curves.guidance(out, 0))


def test_the_no_tax_zone_for_long_term_gains():
    zero_rate = [(60_000, "0"), (10**9, "0.15")]  # gains are free until total income reaches 60,000
    run = make_run(25_000, zero_rate)
    out = curves.analyze(run, "ltcg", -50_000, 250_000)
    assert abs(out["free_amount"] - 35_000) <= curves.TOLERANCE
    assert abs(out["after_free_rate"] - 0.15) < 1e-9
    notes = " ".join(curves.guidance(out, 40_000))
    assert "Up to about $35," in notes and "above the no-tax zone" in notes


def test_long_term_gains_with_no_free_zone():
    run = make_run(80_000, [(10**9, "0.15")])
    out = curves.analyze(run, "ltcg", -50_000, 250_000)
    assert out["free_amount"] < curves.TOLERANCE
    assert "add tax right away" in " ".join(curves.guidance(out, 0))
    assert abs(out["down_rate"] - 0.15) < 1e-9


def test_points_cover_the_range_and_include_zero_with_marginal_rates():
    out = curves.analyze(make_run(20_000, BRACKETS), "stcg", -10_000, 100_000)
    xs = [p[0] for p in out["points"]]
    assert xs[0] == -10_000 and xs[-1] == 100_000 and 0 in xs and xs == sorted(xs)
    marginal = {p[0]: p[2] for p in out["points"]}
    assert abs(marginal[0] - 0.12) < 1e-9 and abs(marginal[10_000] - 0.12) < 1e-9
    assert abs(marginal[20_000] - 0.22) < 1e-9  # income 40,000 is the top of the 12% bracket
    assert out["tax0"] == float(next(p[1] for p in out["points"] if p[0] == 0))


def test_points_that_cannot_be_calculated_are_skipped():
    out = curves.analyze(make_run(5_000, BRACKETS), "stcg", -50_000, 100_000)
    assert min(p[0] for p in out["points"]) >= -5_000
    assert curves.analyze(lambda x: None, "ltcg", -50_000, 250_000)["points"] == []
    assert "could not be calculated" in curves.guidance({"points": [], "lever": "ltcg"}, 0)[0]


def test_deduction_guidance_before_and_after_itemizing():
    # tax falls only once deductions pass 15,000 (the standard deduction gap)
    def run(x):
        taxable = max(100_000 - max(30_000, 15_000 + x), 0)
        return SimpleNamespace(total_tax=D(taxable) * D("0.22"), taxable_social_security=D(0))
    out = curves.analyze(run, "extra_deductions", 0, 100_000, gap=15_000)
    assert abs(out["saving_rate"] - 0.22) < 1e-9
    notes = " ".join(curves.guidance(out, 0))
    assert "$15,000 more deductions" in notes and "bunching" in notes and "$220" in notes
    already = curves.analyze(run, "extra_deductions", 0, 100_000, gap=0)
    assert "already itemize" in " ".join(curves.guidance(already, 0))


def test_social_security_note_appears_when_taxable_benefits_rise():
    run = make_run(20_000, BRACKETS, ss=lambda x: max(x, 0) * 0.5)
    out = curves.analyze(run, "extra_ira", 0, 250_000, cap_percent=22)
    assert out["ss_rises"] and "Social Security taxable" in " ".join(curves.guidance(out, 0))
    flat = curves.analyze(make_run(20_000, BRACKETS), "extra_ira", 0, 250_000, cap_percent=22)
    assert not flat["ss_rises"]


def test_short_term_guidance_and_cap_options():
    out = curves.analyze(make_run(50_000, BRACKETS), "stcg", -50_000, 100_000)
    notes = " ".join(curves.guidance(out, 0))
    assert "taxed as ordinary income" in notes and "$220" in notes
    assert curves.MARGINAL_CAPS == (10, 12, 22, 24, 32, 35, 37)
    assert set(curves.RANGES) == set(curves.LEVERS)
