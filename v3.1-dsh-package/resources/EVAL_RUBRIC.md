# Evaluation rubric — scoring a strategy deliverable

**What this is.** A machine-checkable standard for judging a strategy document (or a model's strategy
output) on the properties that determine whether it can be acted on. It exists because "this strategy
is good" is not a measurable statement, and because this project's own documentation failed several of
these checks before they were written down.

**What it is not.** An automated grader. Two thirds of these checks need a reader. What *is* automated
is the arithmetic half: `tools/strategy_calc.py` recomputes the numbers, and a rubric score that
disagrees with the arithmetic is wrong.

**Why it might matter commercially.** If the checks below are the ones that separate a usable strategy
from a fluent one, then this is a standard a consultancy can be held to, an internal team can be
trained against, or a buyer can apply to a proposal. That is a hypothesis — it has not been validated
with anyone. The rubric is offered as a candidate standard, not a proven one.

---

## How to score

Ten checks, each **pass or fail** — no partial credit, because the failure mode being tested is
"looks approximately right".

| Score | Reading |
|---|---|
| 9–10 | Defensible. The arithmetic reconciles and the reasoning can be challenged. |
| 6–8 | Usable with named gaps. Do not commit budget on the failed checks. |
| 3–5 | Presentation, not analysis. It cannot support a commitment. |
| 0–2 | Do not act on this. |

---

## The checks

### Automatable — recompute these

**1. Headline figures are reproducible.**
Every number in the summary must be derivable from inputs stated somewhere in the document.
*Fail if:* any summary figure requires an input the document does not give.
*Caveat:* "approximately" is not a defence — state the basis or downgrade the claim.

**2. One basis per quantity.**
No quantity appears with two incompatible definitions.
*Fail if:* "profit", "cost", "occupancy" or "payback" is defined differently in two places, or the same
figure carries different values in the summary and the body.
*Check with:* `python3 tools/strategy_calc.py --model <figures>.json` for the recomputation half.

**3. Unit economics reconcile per party.**
For every party to the deal, contribution, cash position and the month their reserve runs out.
*Fail if:* one aggregate model stands in for parties whose interests differ, or a party is
cash-negative with no stated remedy.

**4. Experiments could detect their own effect.**
Each proposed test states control, guardrails with thresholds, an MDE, units per arm, available
volume, and a pre-agreed action for pass/fail/inconclusive.
*Fail if:* a test's required sample exceeds the traffic available, or the primary metric is an activity
measure (impressions, clicks, reach).
*Check with:* `tools/strategy_calc.py` (`required_sample_per_arm`, `detectable_effect`).

**5. Budget and targets are mutually consistent.**
The budget divided by the target volume equals the stated acquisition cost.
*Fail if:* the denominator counts renewals as acquisition, or the numerator excludes labour the plan
itself assigns to the operator.

### Human judgement — a reader must decide

**6. Every material claim carries its evidence status.**
`FACT` / `INTERPRETATION` / `HYPOTHESIS` / `DECISION` / `UNKNOWN`, with source quality graded.
*Fail if:* an assumption stated early is later cited as a fact — the commonest failure in real
documents, and the hardest to spot without relabelling each claim.

**7. Demand claims rest on demand evidence.**
Enquiries, completed pre-registrations, tour or trial conversion, comparable properties' *actual*
occupancy, price tests, or first-party transactions.
*Fail if:* plans, targets, benchmarks, policy documents or market-size estimates are used as evidence
that customers will buy. **A target is a commitment, not a measurement.**

**8. Real alternatives were compared.**
At least three distinct options, or an explicit statement of why fewer are appropriate.
*Fail if:* a strategy name is announced (e.g. "premium tiering strategy") with no alternatives
anywhere in the document — a label is not a decision.

**9. Stop rules exist and are observable.**
Named conditions with thresholds, an owner, and what happens when each triggers.
*Fail if:* risks are listed with no observable trigger, or a high-rated risk has no corresponding
threshold anywhere in the plan. **A risk that cannot fire a rule is decoration.**

**10. The decision is stated, with what would reverse it.**
The commitment required, the recommendation, the options rejected and why, and the evidence that would
change the answer.
*Fail if:* the document ends in a summary rather than a decision.

---

## Applying it

```bash
# the arithmetic half, on the numbers the strategy depends on
python3 tools/strategy_calc.py --model figures.json
```

Then walk checks 6–10 by hand. Record the score, the failed checks, and — importantly — **which failed
checks would have to pass before money is committed.**

A worked application to a real engagement, including where it scored badly:
[`examples/case-study-bonded-apartment.md`](../examples/case-study-bonded-apartment.md).

## Using it on this project

This rubric was written after three runs against a real engagement exposed defects in this package's
own documentation. Scored against itself, an earlier version would have failed checks 1, 2 and 9: it
quoted a payback figure without its basis, gave three different values for the same quantity, and
presented a run's answer as settled. The corrections are in `CHANGELOG.md`.

That is the intended use. A standard that its own authors pass on the first attempt is probably
measuring nothing.
