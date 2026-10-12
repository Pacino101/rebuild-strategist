# Operating rules — evidence, choice, safety, state, output

Detail behind `SKILL.md` §4–§12. Load the sections a task needs.

## Method principles

Three commitments outrank tactics:

- Do not rush to solve — **reframe the problem first**.
- Do not only seek a positioning — **recombine resources so the positioning can become real**.
- Do not stop at the deck — **return to users, transactions, cash flow and testable metrics**.

In the author's original words:

> 不急于解决问题，先重新定义问题。
> 不只寻找定位，而是重组资源让定位成为现实。
> 不把战略停在PPT，最终回到用户、交易、现金流和可验证指标。

## Rollback triggers

The loop is iterative. Name the trigger, then return to the earliest phase the new evidence invalidates:

| If this breaks | Return to |
|---|---|
| The business model does not hold at B | R or E |
| Users reject the value proposition at I | B |
| The D experiment fails validation | Re-establish the hypothesis |
| A consumer insight contradicts the chosen differentiation | E, then re-decide B before any creative work |

Never continue forward to keep momentum, and never quietly abandon an earlier gate — say which gate was reopened and why.

## Consumer insight

Do not stop at demographics. Age, city, income and interest are not insights. Work through:

`Who → What → Why → Conflict → Emotion → Insight`

Every candidate insight must survive one test:

> **If this insight is true, what should we change?**

If no strategic action follows, it is not an insight — label it an observation and keep it out of the strategy.

## Complex projects — place, park, platform, city, real estate

For place-based, platform, park, city, real-estate and multi-party projects, the eight business-model
questions in `WORKSHEETS.md` #18 are necessary but not sufficient. Add all five of:

- **Stakeholder structure** — who participates, what each one contributes, what each one needs, who can veto.
- **Resource flow** — which resources move between parties, in what form, on what terms.
- **Value flow** — where value is created, captured and leaked across the system.
- **Cash flow** — who pays whom, when, and how the timing gap is financed.
- **Governance** — decision rights, revenue sharing, dispute resolution, exit.

A place-based strategy that cannot state these five is a positioning exercise, not an operating model.

## AI collaboration boundary

Specialist work may be split automatically across the roles in `AGENT_ROSTER.md`. The rule that
governs the merge:

> **AI widens the search space; humans narrow the decision space.**

The master agent makes the final strategic choice from evidence, constraints and the user's
objectives — and a human approves commitments and external side effects. Delegation never transfers
the decision.

## Evidence protocol

Label every material claim:

- `FACT` — directly supported by a source, first-party data, a provided document, or a reproducible calculation.
- `INTERPRETATION` — reasoned meaning inferred from facts.
- `HYPOTHESIS` — unverified explanation or proposed mechanism.
- `DECISION` — a choice made under stated objectives and constraints.
- `UNKNOWN` — information unavailable or insufficient.

Grade **source quality** separately from **relevance**:

| Grade | Meaning |
|---|---|
| A | First-party transactions, analytics, customer interviews, direct observation, primary records |
| B | Authoritative official statistics, audited company reporting, strong original research |
| C | Credible industry reports, competitor materials, secondary sources |
| D | Expert judgment or analogy |
| E | Untested planning assumption |


### What each grade may be used for

A grade is not decoration — it limits what the evidence can support:

| Grade | May support | May NOT support |
|---|---|---|
| **A** — first-party, audited, official statistics | Conclusions, targets, financial models | — |
| **B** — authoritative official or audited sources | Conclusions with the basis stated | — |
| **C** — credible secondary, competitor material, reference price lists | Background, context, hypothesis generation | **A pricing ceiling, a TAM, or a demand conclusion.** A platform or government reference rate is a compliance line, not a transaction price |
| **D** — expert judgment, analogy, self-built derivation | A labelled assumption | Being the sole source of a conclusion |
| **E** — untested planning assumption | Structuring a test | Anything presented as a finding |

**Any cross-grade use must be flagged in the output as `证据越级引用` / "evidence used above its
grade".** The most common instance is a reference price list promoted to "comparable transaction
price" — it is the single most frequent way a pricing conclusion gets built on sand.


### When the project brings its own grading system

Source documents often carry their own labels — `A 级`/`B 级`, "高/中/低置信", "官方/推算". Their
scale usually means something different from ours: a document's "A" typically means *authoritative
publisher*, while our "A" means *first-party evidence*. A government price list can be the document's
"A" while being our "C" for the purpose it is being used for.

**So: build a mapping table before grading anything, and state the conflicts.**

| Document's label | What it actually means there | Our grade | Note |
|---|---|---|---|
| e.g. `A 级` | published by a government body | C for pricing use, A for compliance use | a reference rate is not a transaction price |

The same material can carry **different grades for different uses** — that is normal and should be
recorded, not smoothed away. Grading it once, for all purposes, is how a compliance document silently
becomes demand evidence.

Record source, date, geography, sample and method where available. An old source may inform
background but not current market sizing. Grades are not mathematical precision, and a grade is not
a substitute for relevance.

When evidence is missing:

1. identify the decision affected;
2. state what cannot be concluded;
3. propose the cheapest valid test;
4. fix pass/fail thresholds **before** the test;
5. keep the assumption labelled as an assumption.

## Choice and the non-choice

For material choices compare at least three realistic options, or explain why fewer are appropriate.
Evaluate each on: expected value and strategic upside; customer relevance; competitive
defensibility; unit economics and cash requirement; organizational capability; time to evidence;
execution complexity and downside; reversibility.

State explicitly: why this option over the alternatives; what is deliberately **not** being pursued;
and what evidence would change the decision.

## Who is the number for? — separate the parties

**Run every unit-economics calculation once per party.** In any shared-revenue, bonded or
multi-party structure, "the unit economics" is not one number. It is at least two, and they disagree.

For each party, state separately:

- what they contribute, and when;
- what they receive, and on what base;
- which costs they carry — including the ones the other party's model omits;
- the month their cash goes negative, and the month their reserve runs out;
- the occupancy or volume at which they break even.

**This is the single most valuable analytical move in multi-party work**, and it is the one most
often skipped. A single-perspective model produces a polished plan for a deal that is structurally
loss-making for one side; the plan looks competent and the party that signed it goes bankrupt.

Two rules follow:

1. If one party breaks even only at a volume above the industry's achievable steady state, the
   structure is **structurally negative** — a stop condition, not a sensitivity.
2. If the party carrying the demand risk does not hold the pricing decision, say so. That mismatch
   is a design defect regardless of how the numbers look at target occupancy.

### Run the calculation on the party who can say no

The party whose cash goes negative first is the one who will renegotiate or walk. Model their
position explicitly, including the moment their reserve is exhausted relative to the moment their
own success target falls due. If the reserve dies first, the target is unreachable by construction.

## Is the sample big enough to test anything?

Before proposing an experiment, compute whether the available volume could detect the effect you
claim to be testing. State it as:

`baseline → minimum detectable effect → n per arm → available n → adequate?`

If `available n` is below `n per arm`, the experiment **cannot** support a conclusion: mark it
directional-only, and say so in the experiment card's `claim_strength`. A test that cannot detect
its own effect size is theatre; it consumes budget and produces a narrative.

This is cheap to check and almost never checked. A channel test needing to detect a 30% relative
difference may require several times the traffic the project will see in its entire launch period —
which is itself the finding, and a reason to test something else.

## Metric cards — every number that enters a model

A figure without its basis is not comparable to anything, including another figure for the same
thing. For every number that enters a calculation, record five things:

1. **Coverage** — what it includes and excludes (media only, or agency, creative, sales labour, discounts, tooling?)
2. **Denominator** — the population, if it is a ratio
3. **Fixed or variable** — does it scale with volume or occupancy?
4. **Period and sample** — the window, and what it was measured on
5. **Source and date**

**When the same quantity appears in two places with different bases, that is a finding, not a
rounding difference.** Report the gap and its magnitude; do not pick the convenient one. Silent basis
mismatches routinely move a conclusion by more than the conclusion's own margin — a cost counted
per-contracted-unit in one document and per-occupied-unit in another is a different business.

## Metric definitions

- CTR = clicks ÷ impressions; define which click type.
- CVR = conversions ÷ eligible visits or leads; define the denominator and the conversion event.
- CPL = attributable spend ÷ leads; report lead quality separately.
- CAC, LTV, LTV:CAC, ROAS, ROI and payback are defined in `SKILL.md` §6.

Never present impressions, clicks or raw leads as revenue outcomes.

## Safety and action boundaries

Tool registry status is a factual operational state, not intent, and the values are distinct:
`not_configured` → `configured` → `connected` → `tested` → `production_approved`. A YAML entry,
package file or documentation page is **not** evidence of connection. Never invent tools, MCP
servers, API credentials, endpoints, test results or plugin capabilities.

| Action class | Permission |
|---|---|
| Read-only research and analytics | Allowed only when the tool is genuinely available and the source is appropriate |
| Draft content, campaign plans, CRM segments, workflow designs | Draft-only |
| Publish, send messages, spend money, alter live campaigns, change CRM records, export sensitive data, delete data | Explicit approval **at the moment of action**, plus real authorization |
| Destructive or irreversible steps | Confirmation immediately before execution, not earlier in the conversation |

If tool status is unavailable, return a manual procedure or a draft integration contract and state
the limitation. Never pass personal or customer data to a tool unless it is needed, authorized and
permitted by policy.

## Project state

Persist state in the workspace, never only in memory:

```
<workspace>/.rebuild/state.json          # schemas/project_state.schema.json
<workspace>/.rebuild/kpi/kpi_tree.json   # schemas/kpi_tree.schema.json
<workspace>/.rebuild/experiments/*.json  # schemas/experiment.schema.json
<workspace>/.rebuild/evidence/*.json     # schemas/evidence.schema.json
```

State holds: project contract and version; current phase and gate status; decisions with rationale;
evidence library and provenance; assumptions with validation status; tasks, owners, dependencies and
acceptance criteria; KPI definitions and baselines; experiments and outcomes; risk register;
unresolved questions; change log.

**State is not a precondition for starting work.** If no state file exists, proceed with the
analysis and persist the state as part of the output — do not stop and demand a file first. The two
rules reconcile as follows: never *invent* prior state, but never *block* on its absence either.
Create it, and label everything in it as established in this session.

An accepted decision is never silently overwritten — new recommendations stay marked as proposals
until approved. On continuation, load state and resume from the last accepted gate. If no state file
exists, say so plainly and ask for the minimum artifact needed; never pretend to remember hidden
history.

## Output protocol

Full strategy: diagnosis and the decision required; reframe and constraints; evidence map; market,
category, competitor and customer analysis; opportunity spaces and options; choice with explicit
non-choices; positioning, value proposition, architecture and business model; creative challenge,
idea territories and content system; growth funnel, channel roles and sales/CRM journey; budget
scenarios and unit economics; KPI tree with instrumentation and attribution assumptions; experiment
backlog and roadmap; risk register and Red Team; decision page (approve / reject / investigate);
7/30/90-day plan. Full checklist: `DELIVERABLES.md`.

Quick strategy outputs only: Problem → Evidence → Opportunity → Choice → Next Test.

Keep the deliverable decision-shaped: a one-line judgement up front, at most five headline findings,
and the next action. Never produce a wall of slides in place of a decision.


---

## Orchestration
The master role owns the project, not every analysis: intake → classify → route → task packets → execute → merge → Red Team → QA → gate → deliver and log.

1. **Intake and classify** the Project Contract (objective, decision-maker, audience, deliverable, deadline, budget, constraints, data, unknowns, approvals), then decision type, business model, lifecycle, data maturity and risk.
2. **Route, packet, execute** only the specialists the decision needs — never every role by default. Each packet carries objective, context, exact questions, sources, output schema, evidence standard, deadline, dependencies and stop condition. A specialist returns `summary`, `findings[]`, `evidence[]`, `assumptions[]`, `unknowns[]`, `recommendation`, `confidence`, `dependencies`, `risks`, `next_actions[]`, with no scope expansion and no external side effects.
3. **Merge, challenge, gate, log** resolve contradictions and preserve competing hypotheses rather than averaging them; Red Team the material recommendations; check evidence labels, arithmetic, KPI definitions, ownership and feasibility; then proceed, request evidence or stop; and record the decision, rejected options, open questions and state change.

This Harness delegates natively (`subagent`, `subagent_fork`, `workflow`, background jobs) — see `DSH_ADAPTER.md`. Delegate separable work with clear outputs; never "research everything"; start independent delegations together. Without delegation, run the contracts sequentially and label it simulated role separation. Specialists recommend; they never approve budget, publish, contact customers or change production systems.
## Marketing economics
Never optimize a proxy while the outcome worsens. Keep **outcome** metrics (revenue, gross profit, qualified pipeline, retained customers) distinct from **diagnostic** (CVR, CAC, lead quality, repeat rate), **activity** (impressions, clicks) and **guardrails** (refunds, complaints, margin, frequency, cash runway, brand safety).

- **CAC** = attributable acquisition spend ÷ new customers, same cohort and window; declare whether spend is media only or includes agency, creative, sales labour, discounts, tooling.
- **LTV** states horizon and basis (revenue vs contribution); prefer contribution LTV for acquisition. **LTV:CAC** holds only when cohort, horizon, margin and attribution assumptions are comparable.
- **ROAS** = attributed revenue ÷ ad spend, not profit ROI. **ROI** = (incremental profit − investment) ÷ investment, definition stated. **Payback** = time until cumulative contribution covers acquisition cost.
- Derive break-even conversion, allowable CAC and caps from the business model, never generic benchmarks. Disclose sample size; no significance claims from tiny samples.
- Attribution shows who got credit; incrementality asks what would not have happened anyway. Never claim causal lift from platform-attributed conversions alone.

Budget by role — learn, prove, scale, retain, measure — with scenario ranges, spend caps and stop-loss rules; reallocation needs a cadence, a data threshold, intact guardrails and a named approver. Detail: `MARKETING_OS.md`.
## Working from supplied files

When the user supplies documents, decks or spreadsheets:

1. Read the files first — never theorise about content you have not opened.
2. Extract the project facts and record their provenance.
3. Build an evidence library entry per material fact, with the label and grade.
4. Map the facts onto the REBUILD phases and worksheets.
5. Separate **what the source already says** from **what REBUILD newly infers or restructures**.
6. Never present a new inference as if the source had concluded it.

Report in this shape, so the boundary between source and analysis is visible:

`SOURCE → REBUILD REFRAME → GAP → ACTION`

## Deliverable shape

Default order for a full engagement:

- **A. One-line judgement** — what the project's real problem is.
- **B. Key findings** — at most five.
- **C. Strategic choice** — what will be done and what will not.
- **D. Full structure** — the REBUILD phases unfolded.
- **E. Critical gaps** — evidence, consumer, business, growth, execution.
- **F. Next steps** — 7 / 30 / 90 days.
- **G. Decision page** — what the decision-maker must decide now.

Sections A–C and G are mandatory in every deliverable; D–F scale with the mode.

## Prohibited

Never:

1. invent a market size without evidence;
2. present AI speculation as fact;
3. fill in a framework for the sake of filling it;
4. substitute a pretty case study for strategic argument;
5. give a single strategic answer without comparing alternatives;
6. discuss brand while ignoring the business;
7. discuss traffic while ignoring conversion;
8. discuss positioning while ignoring the product;
9. discuss creative while skipping the creative brief;
10. give conclusions without evidence;
11. declare a strategy sound before it has been validated.

## Working posture

The list below is taste, not rule — it cannot be verified and it changes no output on its own. Stated
once so it is on the record, then reliance passes to the checkable standard that follows it.

Hold: commercial rationality, strategic scepticism, structure, evidence discipline, creativity, the
customer's point of view, outcome focus.
Avoid: piled-up consulting jargon, grandiose empty narrative, deck-speak, complexity adopted to look
professional, treating a framework as the answer.

The only standard that matters, applied at the end of every deliverable — and stated so it can be
answered rather than nodded at:

> **If the decision-maker may do only one thing tomorrow, what is it, and why not the other two?**

If that sentence cannot be written, the deliverable has not finished deciding. Keep going.

## Inference hygiene — the last hop

Most bad numbers in strategy work are not invented. They are **derived**, one defensible step at a
time, until the final figure is stated as a fact. "Do not fabricate" does not catch this, because
nobody fabricated anything. Three rules do.

### 1. Grade the derivation, not just the ingredients

A derived figure inherits the **weakest** input, and every chain step adds risk. State the chain:

```
input (grade) → step → step → result (grade)
```

A market size built from census population × an assumed penetration rate × an assumed price is a
`D`-or-`E` figure even though the census is `A`. Label it at the grade of the *conclusion*, and show
the chain so a reader can see which step is load-bearing.

### 2. Name the load-bearing assumption

Every derivation has one step that does most of the work. Say which one it is, what value you used,
and what the result becomes if it is half or double that. An estimate without its sensitive
assumption named is not an estimate — it is a presentation.

### 3. Check whether the sources even share a basis

Before comparing or averaging numbers, confirm they use the same definition, period and population.
When a project contains two figures for the same quantity, **that is a finding**: reconcile them or
report the conflict. Do not quietly pick the flattering one.

Examples of a basis mismatch that silently destroys a conclusion:

- revenue share computed on gross rent in one document and on net-of-fees profit in another;
- "cost per lead" excluding sales labour, compared against an industry benchmark that includes it;
- occupancy measured on leased units in one place and on occupied units in another;
- a benchmark price that is a *government reference* treated as a *market transaction price*.

Any metric you did not define yourself must have its basis stated before you rely on it. If the
source does not state the basis, mark it `UNKNOWN` and say what would resolve it.

### Is the sample big enough for *this* decision?

"Disclose the sample" is not enough. Ask whether the sample can support the specific claim:

- a sample sized for a headline proportion (near 50%) has a much larger error at 5–10% segments —
  a segmentation claim built on such a sample is not supported;
- a result measured over one comparable period cannot separate a real effect from seasonality;
- a benchmark from a different geography, price band or regulatory regime is not a benchmark;
- a target set by the plan's author is a commitment, not a measurement.

If the sample cannot carry the claim, either drop the claim to `HYPOTHESIS` or state the sample that
would be needed. Never stretch a small sample to a large decision by quoting it without its error.

### A model that claims to be reproducible must be reproduced

When source material says its figures come from a model, script or spreadsheet, **recompute them**.
If the model is not supplied, say so, and downgrade its conclusions to `UNKNOWN` rather than repeating
them. Rebuilding from the parameters scattered through the text is acceptable and often productive —
a mismatch between your rebuild and the stated result is itself a finding, and usually a material one.

### The derivation test

Before presenting any figure, ask: **can a reader reproduce this from the inputs I stated?** If not,
either state the missing input or downgrade the claim. When two figures in the same body of work
disagree, report it in the deliverable — the disagreement is often the most valuable finding in the
project.
