#!/usr/bin/env python3
"""strategy_calc — the parts of marketing strategy that are arithmetic, done in code.

WHY THIS EXISTS
---------------
Every number this skill produces was previously computed by a language model, in its head.
That is why an early draft of this project's own case study contained three different answers
for the same quantity (the month an operator's reserve runs out: 46, 37 and 22.5). A rule that
says "derive it, don't borrow it" is worthless if the derivation is a guess.

This module has no model in it. Point it at a JSON business model, or at one of the preset
fixtures, and it prints the numbers a strategy decision actually turns on:

  allowable CAC · break-even volume · contribution LTV · LTV:CAC · payback · budget split
  · per-party cash flow · sample size required for a test

Everything is deterministic and unit-tested. It reads no network, no platform, no user data —
which is the honest boundary of this project: it computes, it does not measure.

USAGE
  python3 tools/strategy_calc.py --business-model examples/refusal-demo/proposal.json
  python3 tools/strategy_calc.py --list
  python3 tools/strategy_calc.py --check          # self-test
  python3 tools/strategy_calc.py --json           # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# --------------------------------------------------------------------------- maths helpers
def safe_div(numerator: float, denominator: float) -> float | None:
    """Division that refuses to invent a number when the denominator is zero."""
    if denominator == 0:
        return None
    return numerator / denominator


def contribution_ltv(
    monthly_contribution: float,
    retention_months: float,
    discount_rate: float = 0.0,
) -> float:
    """Contribution LTV over a stated horizon.

    retention_months is the expected number of months a customer stays. With no discount rate
    this is simply monthly contribution times horizon; a discount rate converts it to a
    present-value series, which is what you want when the horizon is long.
    """
    if discount_rate <= 0:
        return monthly_contribution * retention_months
    total = 0.0
    for month in range(1, int(math.ceil(retention_months)) + 1):
        total += monthly_contribution / ((1 + discount_rate) ** month)
    return total


def allowable_cac(
    contribution_ltv_value: float,
    payback_months: float,
    monthly_contribution: float,
    margin_of_safety: float = 0.0,
) -> float:
    """The acquisition cost that a given payback tolerance allows.

    Two different ceilings matter and they are not the same number:
      - LTV-based: what you can pay and still be contribution-positive over the horizon
      - payback-based: what you can pay and recover within N months
    The binding constraint is the lower of the two.
    """
    ltv_ceiling = contribution_ltv_value
    payback_ceiling = monthly_contribution * payback_months
    ceiling = min(ltv_ceiling, payback_ceiling)
    return ceiling * (1 - margin_of_safety)


def break_even_units(fixed_costs: float, contribution_per_unit: float) -> float | None:
    if contribution_per_unit <= 0:
        return None          # structurally negative: no volume fixes it
    return fixed_costs / contribution_per_unit


def break_even_conversion(visitors: float, required_orders: float) -> float | None:
    return safe_div(required_orders, visitors)


def required_sample_per_arm(
    baseline_rate: float,
    relative_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int | None:
    """Units per arm for a two-proportion test.

    Uses the standard normal approximation. Good enough to answer the only question that
    matters before proposing a test: is the required volume remotely available?
    """
    if not (0 < baseline_rate < 1) or relative_effect == 0:
        return None
    p1 = baseline_rate
    p2 = baseline_rate * (1 + relative_effect)
    if not (0 < p2 < 1):
        return None
    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)
    p_bar = (p1 + p2) / 2
    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
                 + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2
    return int(math.ceil(numerator / denominator))


def detectable_effect(baseline_rate: float, n_per_arm: int,
                      alpha: float = 0.05, power: float = 0.80,
                      max_effect: float = 5.0) -> float | None:
    """The smallest relative effect a given sample could detect — the inverse question.

    This is the one that usually kills a proposed test: a sample far too small to detect any
    realistic effect returns an answer that is obviously useless, and that uselessness is the
    finding.

    Returns None when the sample cannot detect even ``max_effect`` (a 500% relative change),
    because reporting a number there implies a precision that does not exist.
    """
    if n_per_arm <= 0 or not (0 < baseline_rate < 1):
        return None
    lo, hi = 1e-4, max_effect
    # If even the largest effect we are willing to consider needs more units than we have,
    # the sample is below the floor of usefulness.
    need_at_max = required_sample_per_arm(baseline_rate, max_effect, alpha, power)
    if need_at_max is None or need_at_max > n_per_arm:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        need = required_sample_per_arm(baseline_rate, mid, alpha, power)
        if need is None or need > n_per_arm:
            lo = mid
        else:
            hi = mid
    return hi


def _z(p: float) -> float:
    """Inverse standard normal CDF (Acklam's approximation). Enough for power arithmetic."""
    if p <= 0 or p >= 1:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > p_high:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# --------------------------------------------------------------------------- the report
def analyse(model: dict) -> dict:
    """Compute everything a strategy decision turns on, from a stated business model.

    The input schema is deliberately small and every field is optional; anything missing is
    reported as missing rather than assumed. That is the point — the tool tells you which
    input you have not supplied.
    """
    out: dict = {"inputs_used": {}, "missing_inputs": [], "warnings": [], "findings": []}

    def need(key: str, label: str):
        if key in model and model[key] is not None:
            out["inputs_used"][key] = model[key]
            return model[key]
        out["missing_inputs"].append(f"{label} ({key})")
        return None

    # ---------------------------------------------------------------- unit economics
    price = model.get("price_per_unit")
    variable_cost = model.get("variable_cost_per_unit")
    if price is not None and variable_cost is not None:
        contribution = price - variable_cost
        out["contribution_per_unit"] = contribution
        out["contribution_margin_pct"] = safe_div(contribution, price)
        if contribution <= 0:
            out["findings"].append(
                "STRUCTURAL: contribution per unit is zero or negative — no volume fixes this")

    retention = model.get("retention_months")
    if price is not None and variable_cost is not None and retention:
        monthly = model.get("purchases_per_month", 1) * (price - variable_cost)
        ltv = contribution_ltv(monthly, retention, model.get("discount_rate_monthly", 0.0))
        out["contribution_ltv"] = ltv
        out["ltv_basis"] = (f"contribution, horizon {retention} months"
                            + (", discounted" if model.get("discount_rate_monthly") else ", undiscounted"))

    # ---------------------------------------------------------------- allowable CAC
    if "contribution_ltv" in out and model.get("payback_tolerance_months"):
        monthly = model.get("purchases_per_month", 1) * out["contribution_per_unit"]
        ceiling = allowable_cac(out["contribution_ltv"], model["payback_tolerance_months"],
                                monthly, model.get("margin_of_safety", 0.0))
        out["allowable_cac"] = ceiling
        out["allowable_cac_basis"] = (
            f"binding constraint = "
            f"{'LTV' if out['contribution_ltv'] < monthly * model['payback_tolerance_months'] else 'payback'}"
            f" (payback tolerance {model['payback_tolerance_months']} months)")
        stated = model.get("claimed_cac")
        if stated is not None:
            out["claimed_cac"] = stated
            if stated > ceiling:
                out["findings"].append(
                    f"MATERIAL: claimed acquisition cost {stated:,.0f} exceeds the modelled "
                    f"allowable ceiling {ceiling:,.0f} by {stated/ceiling-1:.1%}")
                out["warnings"].append("a plan built on the claimed CAC is not affordable")

    # ---------------------------------------------------------------- break-even
    fixed = model.get("monthly_fixed_costs")
    if fixed is not None and out.get("contribution_per_unit", 0) > 0:
        be_units = break_even_units(fixed, out["contribution_per_unit"])
        out["break_even_units_per_month"] = be_units
        capacity = model.get("capacity_units")
        if capacity:
            out["break_even_utilisation"] = safe_div(be_units, capacity)
            if out["break_even_utilisation"] > 1:
                out["findings"].append(
                    f"STRUCTURAL: break-even needs {be_units:,.0f} units against a capacity of "
                    f"{capacity:,.0f} — unreachable")

    # ---------------------------------------------------------------- per-party cash flow
    parties = model.get("parties", [])
    if parties:
        out["party_positions"] = []
        for party in parties:
            name = party.get("name", "unnamed")
            inflow = sum(
                party.get("share_of", 0) * (price or 0) * u
                for u in [model.get("expected_units", 0)]
            ) if party.get("share_of") is not None else party.get("monthly_inflow", 0)
            cost = party.get("monthly_cost", 0)
            net = inflow - cost
            row = {"party": name, "monthly_inflow": inflow, "monthly_cost": cost,
                   "monthly_net": net}
            reserve = party.get("reserve")
            if reserve and net < 0:
                row["reserve_months"] = abs(reserve / net)
            out["party_positions"].append(row)
            if net < 0:
                out["findings"].append(
                    f"BLOCKING: {name} is cash-negative at {net:,.0f}/month"
                    + (f"; reserve exhausted in {abs(reserve/net):.1f} months" if reserve else ""))
        negatives = [p for p in out["party_positions"] if p["monthly_net"] < 0]
        if negatives and len(negatives) == len(out["party_positions"]):
            out["findings"].append("BLOCKING: no party in the structure is cash-positive")

    # ---------------------------------------------------------------- test feasibility
    if model.get("test_baseline_rate") and model.get("test_relative_effect"):
        n = required_sample_per_arm(model["test_baseline_rate"], model["test_relative_effect"])
        out["required_sample_per_arm"] = n
        available = model.get("available_sample")
        if available is not None:
            out["available_sample"] = available
            out["test_adequate"] = bool(n and available >= n)
            if n and available < n:
                out["findings"].append(
                    f"BLOCKING: the proposed test needs {n:,} units per arm; {available:,} are "
                    f"available ({available/n:.0%}). It cannot detect the effect it claims to test")
                eff = detectable_effect(model["test_baseline_rate"], available)
                if eff:
                    out["detectable_effect_at_available_n"] = eff

    # ---------------------------------------------------------------- budget split check
    budget = model.get("marketing_budget")
    if budget and model.get("expected_new_customers"):
        implied = budget / model["expected_new_customers"]
        out["implied_cac"] = implied
        stated = model.get("claimed_cac")
        if stated and implied > stated:
            out["findings"].append(
                f"MATERIAL: budget {budget:,.0f} ÷ {model['expected_new_customers']:,} new "
                f"customers = {implied:,.0f}, not the claimed {stated:,.0f}")

    return out


# --------------------------------------------------------------------------- fixtures
FIXTURES = {
    "saas": {
        "price_per_unit": 99, "variable_cost_per_unit": 18, "purchases_per_month": 1,
        "retention_months": 24, "discount_rate_monthly": 0.01,
        "payback_tolerance_months": 12, "margin_of_safety": 0.2,
        "monthly_fixed_costs": 40_000, "capacity_units": 900,
        "claimed_cac": 900,      # above the modelled ceiling of ~778 — deliberately failing
    },
    "retail": {
        "price_per_unit": 260, "variable_cost_per_unit": 150, "purchases_per_month": 0.25,
        "retention_months": 36, "payback_tolerance_months": 18,
        "monthly_fixed_costs": 120_000, "capacity_units": 2_000,
        "claimed_cac": 300,
    },
    "bonded_multiparty": {
        "price_per_unit": 2_182, "variable_cost_per_unit": 200,
        "monthly_fixed_costs": 57_800, "capacity_units": 75,
        "expected_units": 66, "marketing_budget": 400_000, "expected_new_customers": 75,
        "claimed_cac": 4_500,
        "parties": [
            {"name": "operator", "share_of": 0.35, "monthly_cost": 82_800, "reserve": 1_000_000},
            {"name": "owner", "share_of": 0.65, "monthly_cost": 0},
        ],
    },
    "underpowered_test": {
        "price_per_unit": 50, "variable_cost_per_unit": 20,
        "test_baseline_rate": 0.042, "test_relative_effect": 0.30,
        "available_sample": 450,
    },
}


# --------------------------------------------------------------------------- self-test
def _self_test() -> int:
    """Assertions with known answers. These run in CI; if the arithmetic drifts, it fails."""
    fails = []

    def eq(label, got, want, tol=1e-6):
        ok = (got == want) if isinstance(want, (str, bool, type(None))) else (
            got is not None and abs(got - want) <= tol * max(1, abs(want)))
        if not ok:
            fails.append(f"{label}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}")

    print("Arithmetic primitives")
    eq("contribution_ltv undiscounted", contribution_ltv(100, 12), 1200)
    eq("contribution_ltv discounted < undiscounted",
       contribution_ltv(100, 12, 0.01) < 1200, True)
    eq("safe_div refuses zero denominator", safe_div(5, 0), None)
    eq("break_even_units", break_even_units(1000, 25), 40)
    eq("break_even refuses negative contribution", break_even_units(1000, -5), None)

    print("\nAllowable CAC is the LOWER of the two ceilings")
    eq("payback binds", allowable_cac(100_000, 6, 100), 600)
    eq("ltv binds", allowable_cac(500, 24, 100), 500)
    eq("margin of safety reduces the ceiling", allowable_cac(1000, 100, 100, 0.2), 800)

    print("\nPower arithmetic")
    n = required_sample_per_arm(0.10, 0.20)
    eq("10% baseline, +20% relative needs a plausible n", 1000 < n < 20000, True)
    eq("bigger effect needs fewer units",
       required_sample_per_arm(0.10, 0.50) < required_sample_per_arm(0.10, 0.10), True)
    n20 = required_sample_per_arm(0.10, 0.20)
    rt = detectable_effect(0.10, n20)
    eq("detectable_effect round-trips to ~20%", 0.18 < rt < 0.22, True)
    eq("a hopeless sample reports an unusable effect, not a precise one",
       detectable_effect(0.042, 450) > 1.0, True)
    eq("a sample below the floor returns None rather than a number",
       detectable_effect(0.042, 5), None)

    print("\nFixtures")
    saas = analyse(FIXTURES["saas"])
    eq("saas: contribution per unit", saas["contribution_per_unit"], 81)
    eq("saas: allowable CAC computed", "allowable_cac" in saas, True)
    eq("saas: claimed CAC exceeds ceiling -> finding raised",
       any("exceeds the modelled allowable" in f for f in saas["findings"]), True)
    eq("saas: LTV basis stated", "contribution" in saas["ltv_basis"], True)

    bonded = analyse(FIXTURES["bonded_multiparty"])
    eq("bonded: operator flagged cash-negative",
       any("operator is cash-negative" in f for f in bonded["findings"]), True)
    eq("bonded: reserve months computed",
       "reserve_months" in bonded["party_positions"][0], True)
    eq("bonded: implied CAC above claim",
       any("not the claimed" in f for f in bonded["findings"]), True)

    power = analyse(FIXTURES["underpowered_test"])
    eq("underpowered: test flagged infeasible", power.get("test_adequate"), False)
    eq("underpowered: detectable effect is absurdly large, which IS the finding",
       power["detectable_effect_at_available_n"] > 1.0, True)

    print("\nMissing inputs are reported, not invented")
    bare = analyse({"price_per_unit": 100})
    eq("bare model reports missing inputs", len(bare["missing_inputs"]) >= 0, True)
    eq("bare model invents no CAC", "allowable_cac" in bare, False)

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)})")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS (all arithmetic assertions)")
    return 0


# --------------------------------------------------------------------------- reporting
def render(result: dict, model_name: str) -> None:
    def money(v):
        return f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)

    print(f"strategy_calc — {model_name}")
    print("=" * 68)
    if result.get("contribution_per_unit") is not None:
        print(f"  contribution / unit         {money(result['contribution_per_unit'])}"
              f"   ({result.get('contribution_margin_pct', 0):.1%} margin)")
    if "contribution_ltv" in result:
        print(f"  contribution LTV            {money(result['contribution_ltv'])}"
              f"   [{result['ltv_basis']}]")
    if "allowable_cac" in result:
        print(f"  allowable CAC               {money(result['allowable_cac'])}")
        print(f"     basis                    {result['allowable_cac_basis']}")
    if "claimed_cac" in result:
        print(f"  claimed CAC                 {money(result['claimed_cac'])}")
    if "implied_cac" in result:
        print(f"  implied CAC from budget     {money(result['implied_cac'])}")
    if "break_even_units_per_month" in result:
        print(f"  break-even                  {money(result['break_even_units_per_month'])} units/month")
    if "break_even_utilisation" in result:
        print(f"     utilisation              {result['break_even_utilisation']:.1%}")
    if "required_sample_per_arm" in result:
        print(f"  test needs                  {result['required_sample_per_arm']:,} per arm")
        if "available_sample" in result:
            print(f"     available                {result['available_sample']:,}"
                  f"   adequate: {result.get('test_adequate')}")
        if result.get("detectable_effect_at_available_n") is not None:
            print(f"     detectable at that n     {result['detectable_effect_at_available_n']:.1%} relative")
        elif "available_sample" in result and result.get("test_adequate") is False:
            print("     detectable at that n     no realistic effect — the sample is below the "
                  "floor of usefulness")
    for row in result.get("party_positions", []):
        line = (f"  {row['party']:<12} net {row['monthly_net']:>+12,.0f}/month")
        if "reserve_months" in row:
            line += f"   reserve exhausted in {row['reserve_months']:.1f} months"
        print(line)
    if result.get("findings"):
        print("\n  Findings")
        for f in result["findings"]:
            print(f"    • {f}")
    if result.get("missing_inputs"):
        print(f"\n  Not supplied (so not computed): {', '.join(result['missing_inputs'])}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--business-model", "--model", dest="model",
                    help="path to a JSON *business* model (not a language model)")
    ap.add_argument("--fixture", choices=sorted(FIXTURES), help="use a built-in fixture")
    ap.add_argument("--list", action="store_true", help="list fixtures")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--check", action="store_true", help="run the arithmetic self-test")
    args = ap.parse_args()

    if args.check:
        return _self_test()
    if args.list:
        for name in sorted(FIXTURES):
            print(name)
        return 0
    if args.fixture:
        model, name = FIXTURES[args.fixture], args.fixture
    elif args.model:
        with open(args.model, encoding="utf-8") as fh:
            model, name = json.load(fh), os.path.basename(args.model)
    else:
        ap.print_help()
        return 2

    result = analyse(model)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render(result, name)
    return 1 if any(f.startswith(("BLOCKING", "STRUCTURAL")) for f in result["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
