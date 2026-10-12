# Case study — three runs against a real engagement

**What this is.** A record of three independent runs of this skill against a live commercial
engagement: an `AUDIT` of a delivered proposal, a `RED_TEAM` of the same, and a `GROWTH_DIAGNOSIS`
that rebuilt the unit economics from scratch. Each run was given the client's documents and the skill,
nothing else.

**What it is not.** It is not a claim that the skill works. It is the evidence you need in order to
judge that yourself — including the fact that **these runs found three serious defects in this skill**,
which are documented at the end along with what changed.

**Anonymisation.** Entity names, locations and project identifiers are removed. The figures are the
ones that appeared in the arithmetic, because removing them would remove the point. No client document
is reproduced. Where a figure came from the client's own papers it is marked `[doc]`; where it is a
recomputation it is marked `[calc]`; where it is an assumption, `[assumption]`.

---

## The engagement, in one paragraph

An ageing non-residential property is to be converted into ~75 long-stay apartments. The property owner
funds the fit-out; an operator supplies a refundable performance bond and runs the building, sharing
revenue monthly with the owner. A marketing plan has been delivered, with a headline claim of a
**1.9-year payback**, a **40万 opening marketing budget**, a target of **88% occupancy within six
months**, and a blended rent of about **2,182 per unit** `[doc]`.

The plan is well made. It has sourced facts with per-claim provenance tags, a compliance analysis
citing specific regulation by number, a working budget that reconciles two ways, and a genuine RACI
split. Anyone skimming it would call it competent. **That is what made it worth auditing.**

---

## What the three runs found

### 1. A headline number that cannot be reproduced

The plan's summary states a payback of approximately 1.9 years `[doc]`. From the plan's own figures:

```
monthly revenue at full occupancy        163,620   [doc]
less monthly operating fee                15,000   [doc]
distributable                            148,620   [calc]
owner share at 65%                        96,603   [calc]
payback = 3,000,000 ÷ 96,603            = 31.1 months = 2.59 years   [calc]
```

For 1.9 years to hold, the monthly payout would have to be 131,579, which requires revenue of 202,429
and therefore **132.9% occupancy** `[calc]`. The run reported the figure as not reproducible rather
than approximately right.

Then the cross-reading, which is where the real finding sat:

| Location in the same body of work | Payback stated |
|---|---|
| Executive summary | 1.9 years |
| Modelling section | 2.4–2.8 years |
| KPI table (north star) | ≤ 30 months |
| Companion research report | 2.6–3.3 years |
| Companion cooperation-paper mechanism | 48 months |

Five figures, one project, no reconciliation. **Gate E: `BLOCKED`.**

### 2. Two definitions of "profit", 42,800 apart

The plan computes distributable profit as revenue minus a 15,000 monthly operating fee, and states in
its own line item that labour and leasing costs are borne separately by the operator `[doc]`. The
companion research report puts the operator's actual steady-state operating cost at **57,800 per
month** `[doc]`.

```
cost gap (operator's side)    57,800 − 15,000 = 42,800 per month   [calc]
effect on owner's payout (65% share)              27,820 per month   [calc]
annualised effect on the owner                   333,840 per year    [calc]
payback on basis A                               31.1 months = 2.59 y  [calc]
payback on basis B                               43.6 months = 3.63 y  [calc]
```

**A one-year swing in payback, decided by which document you read.** Note which party bears what: the
42,800 is a cost on the operator's side; the 27,820 is the reduction in the owner's payout arising from
the owner's share of it. Conflating those two numbers is a category error, and an earlier draft of this
document did exactly that — presenting "12.5 months" as the owner's annualised impact when it is the
payback swing. Both figures are now labelled by party and basis.

### 3. The operator loses money at every achievable occupancy

The run rebuilt the operator's position month by month, using the deal's own parameters
`[doc]`: owner priority draw 63,768; operator steady-state cost 57,800; ramp-period cost 85,000;
marketing 25,000 per month from the premium phase.

| Occupancy | Monthly revenue | Owner priority | Operator residual | Operator net after costs |
|---|---|---|---|---|
| 93% | 152,167 | 63,768 | 73,399 | **−9,401** |
| 88% (the plan's target) | 143,986 | 63,768 | 65,218 | **−17,582** |
| 75% | 122,715 | 63,768 | 43,947 | **−38,853** |
| 60% | 98,172 | 63,768 | 19,404 | **−63,396** |

All `[calc]`. The operator's break-even occupancy is **83.5%** excluding marketing and **98.7%
including it** — and 98.7% is above the industry's own steady state. The plan's own risk section
concedes the operator is cash-negative for the first four years.

**On the bond: three independent models, three answers — and that disagreement is the finding.**

| Model | Monthly operator result | Bond exhausted |
|---|---|---|
| `GROWTH_DIAGNOSIS` run, using the deal's own cost lines | −44,523 | **month 22.5** |
| `RED_TEAM` run, ramp costs applied to its own curve | not shown | **months 12–16** |
| Refusal demo in this repository, mechanical, ramp 6 months | −17,582 at 88% | **month 46** |

`[calc]` throughout. The spread is not a mistake to average away — it comes from assumptions the plan
**does not state**: the ramp curve, whether ramp-period costs apply, and which cost lines are counted
against the operator. The demo prints its own variants side by side for exactly this reason.

What is robust across all three: **the operator is cash-negative at every occupancy the project can
realistically achieve, so meeting the target does not restore solvency, and the bond is gone well
before the 8-year term ends.** The precise month is an open question because the plan does not supply
the assumption — which is itself a finding, and the first thing to fix.

An earlier draft of this document stated "months 12–16" as though it were settled. That was one run's
answer, quoted without its basis, in a document about the danger of doing exactly that. Corrected here,
and the correction is recorded in `CHANGELOG.md`.

This is a stop condition under the skill's own rules — *unit economics structurally negative with no
plausible testable route to repair* — and it is the finding that changed the recommendation from
"improve the marketing" to **"do not sign this contract."**

### 4. The acquisition cost was measured with both ends loosened

The plan claims acquisition cost of 3,300–4,400 per lease against a 4,500 ceiling `[doc]`.

```
40万 ÷ 90–120 lease events                = 3,333–4,444   [doc arithmetic, checks out]
40万 ÷ 70 new customers (plan's own target) = 5,714         [calc]  → 27% over the ceiling
```

The denominator counted lease renewals as acquisition; the numerator excluded sales and leasing labour,
which the plan itself assigns to the operator. Both ends relaxed, so the ceiling held `[calc]`. On the
plan's own occupancy targets, first-year CAC is **5,333–5,714**, over the stated red line.

### 5. Experiments that could not have detected their own effect

The growth run computed the statistical power available before proposing any test:

| Design | Units per arm | Smallest detectable effect |
|---|---|---|
| Unit-level randomisation | 37 | ±28 percentage points |
| Visitor-level randomisation | 450 | +76% relative |
| Detecting a +30% relative channel difference | needs 2,479 per arm | **5.5× the project's entire launch-period traffic** |

All `[calc]`. The honest conclusion is not "run the test" but "this project cannot support that test" —
which is itself a finding, and a reason to test something else. The skill now requires this check
before an experiment is proposed.

### 6. A compliance margin of 0.3% resting on an unverified basis

The rent is set at 89.7 per unit-area against a regulatory reference of 90, and described as compliant
`[doc]`. Recomputed per unit type, four of the five unit types price at **exactly 90.00**, covering 92%
of the units; only the largest falls below `[calc]`. The blend falls below the line because of six
units. The regulation says *below*, not *not above*.

Separately, the per-area figure uses total lettable unit area as its denominator. Using total
construction area instead gives **59.47** `[calc]` — a 34% difference, which changes whether the
compliance test is even being applied to the right quantity.

---

## What the skill contributed, and what it did not

Each run reported this unprompted. Summarised honestly:

**It contributed — verifiably — three things the reviewers said they would not have done otherwise:**

1. **The demand-evidence question.** The rule that a gate blocks when a demand-side claim has no
   demand-side evidence forced an explicit check that found **zero** first-party demand evidence across
   three documents: no completed pre-registrations, no survey results, no competitor occupancy, no
   tour conversion, no price test. Plans, targets and benchmarks are not demand evidence.
2. **Separating the parties.** A reviewer wrote that this was *"the only real analytical lever"*: a
   single-perspective model yields a polished channel plan, while per-party modelling yields "do not
   sign." The rule did not exist when they started — they inferred it from the complex-project
   questions — and it has since been added explicitly.
3. **The nine Red Team angles.** *"Without the list I would have followed the document's chapter order
   to the conclusion its author intended."* The reviewers' point: the list's value is not nine
   perspectives, it is **breaking structural resonance** with the document.

**It did not contribute** — stated plainly by the reviewers, and accepted:

- **The arithmetic.** Every numerical finding came from someone doing division. The skill's
  contribution was a reminder to check, not a method — which is why worksheets 35 and 36 were added.
- **Cross-document contradiction hunting.** Found by reading carefully. No worksheet asked for it.
- **Attack depth.** The nine angles gave direction, not intensity. A reviewer could read "does
  contribution work after real costs?" as "glance at the margin" or as "rebuild 96 months of
  cash flow". The conclusion depends entirely on which — hence the minimum execution standards now
  attached to each angle.

---

## The three defects these runs found in this skill

This is the most useful part of the case study, and the reason it is published.

### Defect 1 — the schemas validated structure, not meaning

A reviewer ran adversarial tests. The KPI schema accepted **10 of 10** semantically empty documents;
the experiment schema accepted **8 of 8**, including a card with no control, empty guardrails, the
decision rule *"we'll figure it out later"*, `primary_metric: impressions`, and `status: complete`
while claiming a causal result.

Their assessment, quoted because it was correct: *"this is more dangerous than having no schema,
because it manufactures a false sense of compliance."*

A previous version of this package's own verifier had **printed "prose requirements are representable
in the schemas"** on the strength of checking the field names it had just added. It was measuring its
own homework.

**Fixed:** the experiment schema now requires a non-empty `control`, at least one guardrail *with a
threshold*, a decision rule with `pass`/`fail`/`inconclusive`/`threshold`, an MDE block carrying
`n_per_arm` versus `available_n`, and an explicit `claim_strength`. The KPI schema requires guardrails
to state a threshold and outcome/driver nodes to state a target. The ad-hoc verifier was deleted and
replaced by `tests/schema_validator.py` plus 25 assertions, 12 of them adversarial, which now run as
part of `verify_package.sh`.

### Defect 2 — no worksheet asked for the work that produced the value

A reviewer reported that roughly 90% of their audit's value came from recomputing numbers and
cross-reading documents, and that **not one of the 34 worksheets asked for either.** The AUDIT mode
itself had no specification in the skill body; the reviewer had to `grep` a file marked LEGACY to find
it, and noted that *"strictly following the instruction to read `resources/` would have missed the
definition entirely."*

**Fixed:** `resources/AUDIT_MODE.md` is now a first-class resource, and worksheets 35 (arithmetic and
basis reconciliation) and 36 (cross-document reconciliation) exist — including the check for whether a
rounding direction happens to favour the conclusion.

### Defect 3 — a rule conflict that made the skill unusable as written

One rule said: with no state file, ask for the minimum artifact first. Another said: never block on a
questionnaire. On a cold audit with no state file, these are opposites, and the skill gave no
precedence. The reviewer chose to proceed — *"but that was my judgement, not the skill's authority."*

**Fixed:** never invent prior state, never block on its absence. Create it, and label what was
established in this session.

---

## Reproducing this

The fixture in [`bonded-apartment-intake/BRIEF.md`](bonded-apartment-intake/BRIEF.md) is built from the
same shape of engagement, with figures that are internally consistent and clearly labelled. It does not
contain the client's numbers. Run any mode against it and compare the output to the "what a good run
should produce" list at the end of the brief.

If your run produces a confident answer where this case study says it should have blocked, that is a
defect worth reporting — and it is the contribution this project most wants.
