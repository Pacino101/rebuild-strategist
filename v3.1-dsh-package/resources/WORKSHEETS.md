# REBUILD 34 Decision Worksheets

Use worksheets as decision tools, not mandatory paperwork. For each worksheet record: `purpose`, `inputs`, `finding`, `evidence`, `decision_implication`, `owner`, `status`, `next_action`. Status: `not_started / in_progress / blocked / reviewed / accepted / not_applicable`. If not applicable, explain why.

| No. | Worksheet | Phase | Minimum fields / decision |
|---:|---|---|---|
| 01 | Project Contract | R | Objective, decision-maker, deliverable, deadline, budget, constraints, approval rights |
| 02 | Brief Decoder | R | Client request, explicit ask, hidden need, desired business outcome |
| 03 | Stakeholder Map | R | Actor, incentive, influence, veto power, conflict, engagement |
| 04 | Problem Tree | R | Symptom, possible causes, root-cause hypotheses, evidence needed |
| 05 | Assumption Log | R/D | Assumption, impact if false, confidence, test, owner, expiry |
| 06 | Research Questions | E | Decision-critical question, method, source, cost/time, priority |
| 07 | Market Map | E | Category, geography, size method, growth, structure, source date |
| 08 | Category Map | E | Category/geography scope, source date, category entry points, buying criteria, substitutes, demand occasions |
| 09 | Competitor Matrix | E | Direct/indirect competitors, target, promise, price, channel, proof, weakness |
| 10 | Consumer Segment | E | Need/behavior/context, jobs-to-be-done, barriers, value, evidence |
| 11 | Interview Guide | E | Hypothesis, neutral question, probe, target segment, sample size/recruitment, consent handling, bias controls, analysis method |
| 12 | Consumer Insight | E/B | Behavior, context, tension, emotion, motivation, evidence, action implied |
| 13 | Trend Radar | E | Signal, source, persistence, relevance, uncertainty, time horizon |
| 14 | Opportunity Matrix | E | Opportunity, attractiveness, fit, economics, evidence, risk, priority |
| 15 | Strategic Choice | B | At least 3 options where realistic, upside, downside, capability, cost, choice |
| 16 | Positioning Statement | B | Target, frame/category, differentiated promise, reason to believe |
| 17 | Value Proposition | B | Customer job, pain/gain, offer, proof, objection, desired action |
| 18 | Business Model 8Q | B | Customer, value, product, revenue, cost, channel, scalability, risk |
| 19 | Product Architecture | B | Entry/core/premium/retention products, role, price, margin, upsell |
| 20 | Brand Architecture | B | Master/sub-brand relationships, role, endorsement, governance |
| 21 | Strategy Architecture | B | Goal, strategic choices, capabilities, initiatives, dependencies, exclusions |
| 22 | Creative Brief | U | Business problem, audience, tension, insight, promise, proof, creative challenge, action |
| 23 | Big Idea Generator | U | Territories, distinctive mechanism, fit, extensibility, risk |
| 24 | Content System | U/I | Pillars, formats, cadence, channel role, owner, CTA, repurposing |
| 25 | Growth Funnel | I | Stage, period/window, entry volume, conversion, friction, source of truth, owner, tracking event |
| 26 | KPI Tree | I/D | Business outcome → driver → diagnostic → guardrail; each with definition, period, baseline, target, event/source, owner |
| 27 | Experiment Card | D | Hypothesis, control, variant, audience, primary metric, guardrail, MDE/threshold, analysis plan, sample, duration, rule |
| 28 | Risk Register | D | Risk, probability, impact, trigger, mitigation, owner, residual risk |
| 29 | Red Team | D | Strongest failure case, assumptions attacked, evidence, countermeasure, kill criteria |
| 30 | Postmortem | D | Expected vs actual, causal uncertainty, what worked, what failed, next rule |
| 31 | Marketing Budget Planner | I/D | Objective, spend categories, scenario, unit economics, caps, approval |
| 32 | Media & Channel Strategy | I | Audience-channel fit, funnel role, creative needs, CTA, cadence, owner, cost, KPI, measurement, dependencies |
| 33 | Campaign Performance | D | Period/window, cohort, baseline, spend, reach, qualified outcomes, conversion, contribution, attribution limits |
| 34 | Budget Reallocation | D | Current allocation, marginal returns, data threshold, guardrails, approval, next review |

## Worksheet execution rule
A worksheet is accepted only when its decision implication is explicit. A filled table without a decision is not completion. If a worksheet is skipped, record the reason and any risk created by skipping it.

## Worksheet 35 — Arithmetic and basis reconciliation

Not part of the original 34. Added because in a real audit of a delivered proposal, most of the
value came from recomputation, and none of the 34 worksheets asked for it. Run this on any proposal
that contains numbers you are expected to act on.

For **every** headline figure:

| Field | What to record |
|---|---|
| Claim | the figure as stated, and where |
| Document value | as written |
| Numerator / denominator | as the document defines them — quote it |
| Window and cohort | period, sample, population |
| Recomputed value | your own calculation, shown |
| Gap | absolute and percentage |
| Nature of the gap | rounding · transcription · basis switch · not reproducible · definition missing |
| Decision impact | does this change the recommendation? |
| Rounding direction | does the rounding favour the conclusion? |

**Run at least three scenarios and one extreme case.** A single-point model cannot be audited; the
sensitivity is the finding.

**Check for silent basis switches specifically.** The four that recur:

1. a cost counted per contracted unit in one place and per occupied unit in another;
2. a ratio whose denominator includes renewals, so it stops measuring new-customer acquisition;
3. a "profit" figure that excludes labour, tax or fulfilment;
4. a reference or list price compared against a transacted price.

**Rule:** if a figure cannot be recomputed from the inputs the document states, it is `UNKNOWN`, not
approximately right. Say what input would settle it.

## Worksheet 36 — Cross-document reconciliation

Run whenever the user supplies more than one document about the same project. In practice, delivered
proposals almost always contradict each other, and the contradictions decide the engagement.

| Field | What to record |
|---|---|
| Variable | e.g. monthly operating cost, payback period, opening date, success metric |
| Value by document | each document's value **with section reference** |
| Consistent? | yes / no |
| Cause | basis change · superseded model · different author · typo · different scenario |
| Which governs | and **who decides** which governs |
| Magnitude of impact | in money or time, not adjectives |

### The four variables that break first

Check these before anything else — they are where proposals disagree most often:

1. **Cost basis** — what counts as a cost, and whether it is fixed or volume-linked;
2. **Time axis** — opening date, contract start, payback start, and whether they use the same clock;
3. **Allocation mechanism** — a fixed share versus a dynamic or priority-based split produces
   different numbers from identical revenue;
4. **Success definition** — occupancy of leased units versus occupied units; target versus baseline.

**Never average conflicting values.** Report the gap, name what governs, and state who has the
authority to decide. A reconciled average of two incompatible bases is a third wrong number.

**A disagreement between two documents is itself a finding** — frequently the most important one in
the engagement, because it means at least one party is planning against a number the other does not
recognise.
