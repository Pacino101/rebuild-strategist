#!/usr/bin/env python3
"""Refusal demo — the skill's arithmetic and evidence rules, executed deterministically.

WHY THIS EXISTS
---------------
The README's headline claim is that this skill refuses to certify a plan the evidence cannot
support. That claim is about model behaviour, which is probabilistic and cannot be unit-tested
from a repository. So this demo takes a different route: it applies the *rules the skill states*
to a synthetic proposal, mechanically, with no model involved.

If a visitor runs `python3 examples/refusal-demo/demo.py` they get the same refusal a competent
run should produce, reproducibly, offline, in under a second.

Exit code is 1 when the proposal fails the gates. That is deliberate: this demo fails on purpose.

The input is synthetic and derived from the anonymised engagement in
`examples/case-study-bonded-apartment.md`. It contains no client data.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- input
# A delivered proposal, as its own documents state it. Two documents disagree; both are quoted.
PROPOSAL = {
    "units": 75,
    "monthly_revenue_at_full_occupancy": 163_620,
    "owner_fitout_investment": 3_000_000,
    "claim_summary": {
        "payback_years": 1.9,
        "occupancy_target_6m": 0.88,
        "opening_marketing_budget": 400_000,
        "cac_ceiling": 4_500,
    },
    "claim_modelling": {"payback_years_low": 2.4, "payback_years_high": 2.8},
    "claim_kpi_table": {"payback_months_max": 30},
    # Document A defines distributable profit one way; document B states the real cost.
    "doc_a_operating_fee": 15_000,
    "doc_b_operator_steady_cost": 57_800,
    "doc_b_operator_ramp_cost": 85_000,
    "owner_share_pct": 0.65,
    "owner_priority_draw": 63_768,
    "monthly_marketing_from_premium_phase": 25_000,
    "occupied_unit_ratio": None,       # not stated anywhere
    "renewals_included_in_cac_denominator": True,
    "sales_labour_in_cac_numerator": False,
    "demand_evidence": [],             # plans and targets are not demand evidence
    "planned_experiment": {
        "status": "complete",
        "control": "",
        "guardrails": [],
        "decision_rule": "we'll figure it out later",
        "primary_metric": "impressions",
        "claim_strength": "causal",
    },
}

FINDINGS: list[tuple[str, str, str]] = []   # (severity, gate, finding)


def finding(severity: str, gate: str, text: str) -> None:
    FINDINGS.append((severity, gate, text))


# ------------------------------------------------------------------- rule 1: arithmetic
def check_payback(p: dict) -> None:
    """SKILL.md §6 + worksheet 35 — a headline figure must be reproducible."""
    rev = p["monthly_revenue_at_full_occupancy"]
    distributable = rev - p["doc_a_operating_fee"]
    owner = distributable * p["owner_share_pct"]
    months = p["owner_fitout_investment"] / owner
    claimed_months = p["claim_summary"]["payback_years"] * 12

    print(f"  recomputation: {p['owner_fitout_investment']:,} ÷ ({distributable:,} × "
          f"{p['owner_share_pct']:.0%}) = {months:.1f} months = {months/12:.2f} years")

    if abs(months - claimed_months) > 1:
        # What occupancy would be needed for the claim to hold?
        needed_owner = p["owner_fitout_investment"] / claimed_months
        needed_rev = needed_owner / p["owner_share_pct"] + p["doc_a_operating_fee"]
        needed_occ = needed_rev / rev
        finding("BLOCKING", "E",
                f"headline payback of {p['claim_summary']['payback_years']} years is not reproducible "
                f"from the stated figures (recomputed {months/12:.2f} years); it would require "
                f"{needed_occ:.1%} occupancy")
        print(f"  to reach {p['claim_summary']['payback_years']} years: payout {needed_owner:,.0f} → "
              f"revenue {needed_rev:,.0f} → occupancy {needed_occ:.1%}  ← impossible")

    # Same figure, several answers, in one body of work
    stated = {
        "executive summary": p["claim_summary"]["payback_years"],
        "modelling section": p["claim_modelling"]["payback_years_high"],
        "KPI table": p["claim_kpi_table"]["payback_months_max"] / 12,
    }
    spread = max(stated.values()) - min(stated.values())
    if spread > 0.5:
        detail = ", ".join(f"{k} {v:.1f}y" for k, v in stated.items())
        finding("BLOCKING", "E",
                f"the same figure carries {len(stated)} values within one body of work "
                f"({detail}); spread {spread:.1f} years")


# ------------------------------------------------------------- rule 2: one basis or none
def check_cost_basis(p: dict) -> None:
    """OPERATING_RULES.md — metric cards; cross-document reconciliation (worksheet 36)."""
    gap = p["doc_b_operator_steady_cost"] - p["doc_a_operating_fee"]
    if gap <= 0:
        return
    owner_impact = gap * p["owner_share_pct"]
    print(f"  basis gap: {p['doc_b_operator_steady_cost']:,} − {p['doc_a_operating_fee']:,} = "
          f"{gap:,}/month on the operator's side")

    rev = p["monthly_revenue_at_full_occupancy"]
    months_a = p["owner_fitout_investment"] / ((rev - p["doc_a_operating_fee"]) * p["owner_share_pct"])
    months_b = p["owner_fitout_investment"] / ((rev - p["doc_b_operator_steady_cost"]) * p["owner_share_pct"])
    print(f"  payback on basis A: {months_a/12:.2f} y   on basis B: {months_b/12:.2f} y   "
          f"difference {(months_b-months_a)/12:.1f} y")
    finding("BLOCKING", "E",
            f"two documents define distributable profit differently. The {gap:,}/month cost gap is "
            f"borne by the operator; because the owner takes a share, it also reduces the owner's "
            f"payout by {owner_impact:,.0f}/month ({owner_impact*12:,.0f}/year), and it moves payback "
            f"from {months_a/12:.2f} to {months_b/12:.2f} years — a {(months_b-months_a)/12:.1f}-year "
            f"swing decided by which document you read")


# ------------------------------------------------------- rule 3: per-party unit economics
def check_per_party(p: dict) -> None:
    """OPERATING_RULES.md — 'Who is the number for?'; a party breaking even above achievable
    occupancy is a stop condition, not a sensitivity."""
    rev = p["monthly_revenue_at_full_occupancy"]
    op_cost = p["doc_b_operator_steady_cost"] + p["monthly_marketing_from_premium_phase"]

    print("  operator position by occupancy (marketing included):")
    rows = []
    for occ in (0.93, 0.88, 0.75, 0.60):
        gross = rev * occ
        distributable = gross - p["doc_a_operating_fee"]
        owner_draw = min(p["owner_priority_draw"], distributable)
        residual = distributable - owner_draw
        net = residual - op_cost
        rows.append((occ, net))
        print(f"    {occ:.0%}: revenue {gross:>9,.0f}  owner {owner_draw:>8,.0f}  "
              f"operator residual {residual:>8,.0f}  net {net:>+9,.0f}")

    if all(net < 0 for _, net in rows):
        # Break-even occupancy, algebraically
        # residual = rev*occ - fee - priority  must equal op_cost
        breakeven = (op_cost + p["doc_a_operating_fee"] + p["owner_priority_draw"]) / rev
        finding("BLOCKING", "B",
                f"the operator is cash-negative at every occupancy tested; break-even occupancy is "
                f"{breakeven:.1%}, and the plan's own target is {p['claim_summary']['occupancy_target_6m']:.0%}")

    # Reserve exhaustion. The month depends heavily on two unstated assumptions, so they are
    # printed rather than buried: the ramp curve, and whether ramp-period costs apply.
    def months_until_reserve_gone(ramp_months: int, ramp_multiplier: float) -> int | None:
        cum = 0.0
        for month in range(1, 97):
            occ = min(0.88, 0.50 + (0.88 - 0.50) * (month - 1) / 5)   # plan's own ramp targets
            gross = rev * occ
            distributable = gross - p["doc_a_operating_fee"]
            residual = distributable - min(p["owner_priority_draw"], distributable)
            cost = op_cost * (ramp_multiplier if month <= ramp_months else 1.0)
            cum += residual - cost
            if cum <= -1_000_000:
                return month
        return None

    scenarios = {
        "ramp costs for 6 months (report's own figures)": months_until_reserve_gone(6, 85_000 / op_cost),
        "steady-state costs only, no ramp": months_until_reserve_gone(0, 1.0),
        "ramp costs for 12 months": months_until_reserve_gone(12, 85_000 / op_cost),
    }
    print("  reserve exhaustion depends on unstated assumptions:")
    for label, month in scenarios.items():
        print(f"    {label:<46} month {month if month else '—'}")
    worst = min(m for m in scenarios.values() if m)
    if worst < 12:
        when = f"as early as month {worst}"
    else:
        when = f"between months {worst} and {max(m for m in scenarios.values() if m)} depending on the assumption"
    finding("BLOCKING", "I",
            f"the operator's reserve is consumed {when}; the plan's own success target falls due in "
            f"month 6, by which point the operator is still loss-making, so meeting the target does "
            f"not restore solvency. The exact month is assumption-dependent and the plan does not "
            f"state the ramp curve or whether ramp costs apply")


# -------------------------------------------------------------- rule 4: acquisition cost
def check_cac(p: dict) -> None:
    """SKILL.md §6 — CAC denominator counts new customers; numerator declares its scope."""
    budget = p["claim_summary"]["opening_marketing_budget"]
    ceiling = p["claim_summary"]["cac_ceiling"]
    units = p["units"]

    if p["renewals_included_in_cac_denominator"]:
        lo, hi = budget / 90, budget / 120
        print(f"  as claimed: {budget:,} ÷ 90–120 lease events = {lo:,.0f}–{hi:,.0f}  (under the "
              f"{ceiling:,} ceiling)")
    new_customers = units  # the plan's own first-year target implies ~all units newly let
    actual = budget / new_customers
    print(f"  on new customers only: {budget:,} ÷ {new_customers} = {actual:,.0f}")
    if actual > ceiling:
        finding("MATERIAL", "I",
                f"acquisition cost is {actual:,.0f} per new customer against a stated ceiling of "
                f"{ceiling:,} — the ceiling holds only because renewals are counted as acquisitions"
                + ("" if p["sales_labour_in_cac_numerator"]
                   else " and sales labour is excluded from the numerator"))


# ------------------------------------------------------------- rule 5: demand evidence
def check_demand_evidence(p: dict) -> None:
    """QUALITY_GATES.md — Gate E in particular. Plans, targets and benchmarks are not evidence."""
    if not p["demand_evidence"]:
        finding("BLOCKING", "E",
                "no demand-side evidence of any kind: no completed pre-registrations, no survey "
                "results, no competitor occupancy, no tour conversion, no price test. Occupancy "
                "targets are commitments, not measurements")


# ------------------------------------------------------------ rule 6: experiment quality
def check_experiment(p: dict) -> None:
    """experiment.schema.json — a card must be able to fail before it can prove anything."""
    e = p["planned_experiment"]
    problems = []
    if not e["control"]:
        problems.append("no control")
    if not e["guardrails"]:
        problems.append("no guardrails")
    if e["primary_metric"] in {"impressions", "clicks", "reach", "views"}:
        problems.append(f"primary metric is an activity measure ({e['primary_metric']})")
    if "later" in e["decision_rule"] or "再说" in e["decision_rule"]:
        problems.append("decision rule is not pre-agreed")
    if e["status"] in {"running", "complete"} and e["claim_strength"] == "causal" and not e["control"]:
        problems.append("claims causality without a comparison")
    if problems:
        finding("BLOCKING", "D", "the proposed experiment cannot support any conclusion: "
                                 + "; ".join(problems))


# ------------------------------------------------------------------------ gate verdicts
def verdicts() -> dict[str, str]:
    by_gate: dict[str, list[str]] = {}
    for severity, gate, _ in FINDINGS:
        by_gate.setdefault(gate, []).append(severity)
    out = {}
    for gate in "REBUID":
        sevs = by_gate.get(gate, [])
        if "BLOCKING" in sevs:
            out[gate] = "BLOCKED"
        elif sevs:
            out[gate] = "PASS_WITH_GAPS"
        else:
            out[gate] = "PASS"
    return out


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print()
    print("Input: a delivered proposal, as its own documents state it.")
    print("No model is involved. These are the skill's stated rules, applied mechanically.")
    print()

    for title, fn in [
        ("Rule 1 — a headline figure must be reproducible", check_payback),
        ("Rule 2 — one basis, or the comparison is meaningless", check_cost_basis),
        ("Rule 3 — compute it once per party", check_per_party),
        ("Rule 4 — acquisition cost counts new customers", check_cac),
        ("Rule 5 — plans and targets are not demand evidence", check_demand_evidence),
        ("Rule 6 — a test must be able to fail", check_experiment),
    ]:
        print(title)
        fn(PROPOSAL)
        print()

    v = verdicts()
    print("Gate verdicts")
    for gate, label in [("R", "problem"), ("E", "evidence"), ("B", "choice"), ("U", "creative"),
                        ("I", "execution readiness"), ("D", "learning")]:
        print(f"  Gate {gate} ({label:<20}) {v[gate]}")
    print()

    print("Findings")
    for severity, gate, text in FINDINGS:
        print(f"  [{severity}] Gate {gate}: {text}")
    print()

    blocked = [g for g, s in v.items() if s == "BLOCKED"]
    print("Decision page")
    if blocked:
        print("  The project cannot proceed on this evidence.")
        print(f"  Blocked at: {', '.join(blocked)}.")
        print("  Cheapest next actions, in order:")
        print("    1. Verify the two land-use pre-conditions the plan itself names as fatal.")
        print("    2. Rebuild the economics on ONE cost basis, signed by both parties.")
        print("    3. Attach the demand evidence, or price the project as unvalidated.")
        print("  Recommendation: do not sign, and do not spend the marketing budget, until 1–3 are done.")
    else:
        print("  Gates pass; proceed.")

    print()
    print("Exit code 1 = the proposal failed the gates. This demo fails on purpose.")
    return 1 if blocked else 0


if __name__ == "__main__":
    json.dump(PROPOSAL, open(os.path.join(HERE, "proposal.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    sys.exit(main())
