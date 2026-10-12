# Quality Gates, Risk and Stop Conditions

## Gate statuses
- `PASS`: exit criteria met.
- `PASS_WITH_GAPS`: continue only with named limitations, owner and mitigation.
- `BLOCKED`: a decision-critical gap makes the next phase unsafe or wasteful.

## R gate — problem and contract
Pass when business decision, scope, stakeholder, constraints, baseline and success criteria are sufficiently explicit. Block if the requested output cannot be connected to any decision or success criterion.

## E gate — evidence and opportunity
Pass when decision-critical questions have relevant evidence or a consciously accepted test plan. Block unsupported claims that could materially alter the decision. **A demand-side claim with no demand-side evidence blocks this gate** — see "Gate E in particular" below.

## B gate — strategic choice
Pass when target, promise, economics, capabilities, trade-offs and rejected options are explicit. Block when options are not genuinely distinct or the selected option violates a known constraint.

## U gate — strategy-to-creative translation
Pass when creative/content expresses the chosen strategy, is audience-relevant, has proof and a desired action. Block slogan-only responses that do not change product, message or behavior.

## I gate — execution readiness
Pass when owners, timing, budget, channel roles, event tracking, CRM/sales handoff, approval rights, risks and stop rules are defined. Block external actions without authorization.

## D gate — learning and decision
Pass when actual vs expected results, data limitations and next decision are recorded. Decide `scale / iterate / pivot / pause / stop`; do not call a result successful just because activity completed.

## Red Team checklist

Attack from nine angles. Each carries a **minimum execution standard** — a direction without a depth
standard lets a reviewer produce "looks broadly sound" while a real attack would have killed it.

1. **Customer** — Is the need real, urgent and evidenced?
   *Minimum: name the evidence and its grade. If there is no demand-side evidence at all, say so
   explicitly; that single statement outweighs every other finding.*
2. **Competition** — Can incumbents copy this? Are substitutes overlooked?
   *Minimum: name the direct substitute and the actual price a buyer pays for it.*
3. **Business** — Does the model create durable value and revenue?
4. **Finance** — Does contribution work after real costs and payback?
   *Minimum: recompute at least three occupancy or volume scenarios plus one extreme case; list every
   assumption and every missing input; if unit economics are negative, state the break-even point.*
5. **Execution** — Can the team, time and channels deliver?
   *Minimum: name the binding constraint — the one resource that runs out first.*
6. **Organization** — Who can veto, and do incentives conflict?
   *Minimum: list the veto holders and check whether the stated goal and the stated remedy point the
   same way. A metric that cannot be hit by the sanctioned remedy is a designed failure.*
7. **Technology/data** — Are systems, permissions and data reliable?
8. **Measurement** — Could attribution, seasonality or selection bias explain results?
   *Minimum: verify the numerator and denominator of every headline metric. Check whether both were
   relaxed relative to the standard definition.*
9. **Reputation/legal** — Are claims, privacy and category constraints acceptable?

**The list exists to break structural resonance.** Without it, a reviewer follows the document's own
chapter order and arrives at the conclusion the author intended — "broadly sound, local optimisations
needed". The value is not nine perspectives; it is being forced out of the document's frame.

### Cash-flow timing is mandatory for multi-party structures

Any project with revenue sharing, a bond or deposit, staged investment, or more than one party
carrying cost **must** produce a month-by-month cash-flow table before any financial finding is
stated. For each month: who pays, who receives, who funds the gap, and when the funding party runs
out. A financial conclusion without that table is not a finding.

Three things this table reliably exposes, all of which are invisible in annual averages:

- whether the party carrying the demand risk is also the party with pricing power (usually not);
- whether a "guaranteed" return for one party is simply the other party absorbing all variance;
- the month at which the downside party's reserve is exhausted, compared with the month its own
  success target is due. If the reserve dies first, the target is unreachable by construction.

## Stop conditions

**Four or more of these firing at once is a stop, not a warning.** When they fire, say which ones
fired, in the deliverable, and name what would clear each. A stop condition that is identified but
not escalated is documentation, not control.

**Unmitigated high risk downgrades the verdict.** If a risk is rated high and the source document
contains no observable threshold, owner or remedy for it, downgrade the overall assessment one level
(`PASS` → `PASS_WITH_GAPS` → `BLOCKED`). A plan that names its own fatal risk and then does not plan
for it has not mitigated it.

Stop and request clarification/evidence if:
- critical source data is missing or contradictory;
- unit economics are structurally negative with no plausible testable route to repair;
- proposed action is outside granted authority;
- required privacy/legal/security controls are absent;
- the requested success claim exceeds available evidence;
- a live tool status is unknown but the task assumes it is connected.

## A gate is only real if it is recorded

A gate decision that exists only in conversation is decoration. A gate result is binding when it is
written into the project state:

- **persist it** — set the phase's value in `gate_status` to `PASS`, `PASS_WITH_GAPS`,
  `BLOCKED` or `NOT_REVIEWED`;
- **cite the evidence** — name the specific findings, figures or documents the decision rests on;
- **name the gaps** — for `PASS_WITH_GAPS`, state each limitation, its owner and its mitigation;
  an unnamed gap makes the pass meaningless;
- **record what it blocks** — for `BLOCKED`, state the exact missing input and the cheapest way to
  obtain it, so the next session can resume rather than re-argue.

If no state file exists, say so explicitly instead of implying the gate was evaluated. "I have
reviewed this" is not a gate result; `PASS_WITH_GAPS` with three named limitations is.

### Gate E in particular

Gate E fails more often than any other, and it is usually reported wrongly. Ask one question:

> **Does any evidence describe the demand side?**

Plans, targets, benchmarks and policy documents are not demand evidence. Demand evidence is
enquiries, pre-registrations that actually completed, tour or trial conversion, waitlists, comparable
properties' *actual* occupancy, price tests, or first-party transaction data. If none of that exists,
Gate E is `BLOCKED` — not `PASS_WITH_GAPS`, and not "to be validated later". A plan may proceed on
`PASS_WITH_GAPS` only when it names the specific test, its owner and its date.

Two related traps:

- **A target is not evidence.** "Occupancy ≥ 88%" is a commitment. It becomes evidence only when a
  comparable property's realised occupancy, or your own test, supports it.
- **A reference price is not a transaction price.** A government or platform reference rate
  establishes a ceiling or a compliance line; it does not establish that anyone will pay it. Actual
  paid prices, or actual asking prices of direct substitutes, are the relevant comparison.
