# Changelog

All notable changes to this package. Version numbers refer to the skill, not to any Harness.

This project keeps an unusual rule for a changelog: **every entry states what actually happened,
including what failed.** The audit trail is part of the method — a package that preaches evidence
discipline and then logs a tidy, flattering history would be contradicting itself.

## [3.2.6] — 2026-10-12

### Added — three reference adapters, in three different shapes

A contract with one example proves nothing: you cannot tell which parts are the contract and which
are that example's habits. So three ship, each exercising a different integration path, all runnable
offline against fixtures, all asserted in CI.

| Adapter | Shape | Demonstrates |
|---|---|---|
| `tools/adapters/csv_export.py` | manual export | the minimum viable adapter; also catches field-name typos instead of passing them through |
| `tools/adapters/posthog.py` | **live HTTP API** | credentials from the environment, a single read-only GET, explicit failure with no substituted data, and an `--offline` replay so it can be tested without a key |
| `tools/adapters/upstream_json.py` | **tool-to-tool** | a declared JSON envelope on stdin — how an MCP server, a dbt run or another team's script hands data over; includes a declared unit conversion with its arithmetic recorded |

### Two methodological fixes the adapters forced

- **Retention is not a half-life.** The first version inverted a retention curve by reading the period
  where it crossed 50%, which returned a **1-month** customer lifetime on a real-shaped curve. That is
  the half-life, not the lifetime, and it understates badly. Replaced with an exponential fit, which
  gives 2.1 months on the same data — and, critically, the note now says this is a **conservative
  floor**, because real retention decays closer to a power law and the true tail is longer. The
  adapter reports the method and its direction of bias rather than a confident point estimate.
- **Unconsumed fields are reported, not smuggled.** The upstream adapter first placed a
  `monthly_revenue` value into `model` where `strategy_calc.py` does not read it. That both failed the
  output schema and hid the fact that the upstream had supplied something unused. It is now recorded
  in provenance and flagged in `missing` as *supplied, not consumed*.

### Verified end to end
The chain runs: PostHog funnel fixture → contract checker → `strategy_calc.py`, producing an allowable
CAC of 499 (payback-bound, not LTV-bound at 790) and confirming a proposed test is adequately powered
at 5,785 units per arm against 12,480 available. Both facts are the kind a plan routinely gets wrong in
the direction that flatters it.

### Still not done
- **No adapter has touched a live system.** PostHog's live path is implemented and fails loudly without
  credentials, but it has never been run against a real project, so its status is `configured`, not
  `connected`. No integration status in `tool-registry.yaml` has moved.
- **No adapter for the other nine named platforms.** The contract now has three worked examples, which
  is enough to write a fourth; it does not make a fourth exist.
- **No write path**, in any adapter, by design.

## [3.2.5] — 2026-10-12

### The question that exposed a real gap

*Can a user plug in their own language model, or their own data platform?* Audited honestly, the
answer was **no, for both** — and not because of a policy decision, but because there was no interface
at all. `grep -rn "adapter|provider|plugin|interface"` returned nothing. The ten integration contracts
were prose: readable, unimplementable.

That is a worse gap than "not connected yet". A user who wants to plug something in should find a
contract and a checker, not an intention.

### Added — two integration points, and a third refused on purpose

- **`resources/ADAPTER_CONTRACT.md`** — separates three things that are usually conflated: model
  binding (your runtime's job, deliberately not ours), data source conversion (a contract you
  implement), and live platform access (allowed read-only, gated by evidence).
- **`resources/schemas/adapter_output.schema.json`** — the output contract an adapter must satisfy.
  Its central design choice is the required `missing` array: **an adapter cannot silently omit the
  fact that it omitted something.**
- **`tools/check_adapter.py`** — enforces the contract. It rejects an adapter that invents a value
  without provenance, reports a field as both supplied and missing, uses a grade outside the A–E
  scale, omits source metadata, adds an unknown key, or **promotes its own connection status**. That
  last rule matters most: a checker run can evidence `configured` at most, because `connected` is a
  claim about the real world and requires a recorded observation.
  - Eight self-test cases, all of which the checker must reject or accept correctly. Run in CI.
- **`tools/adapters/csv_export.py`** — a working reference adapter: CSV in, business-model JSON out,
  no network, no credentials, no dependencies. It reports unrecognised field names rather than
  silently passing them through, so a typo cannot look like data.
- **`examples/adapter/figures.csv`** — the fixture the reference adapter and CI use.

### Fixed
- `strategy_calc.py` took a `--model` flag that meant *business* model. In a project adjacent to
  language models that is a trap. Renamed to `--business-model`, with `--model` kept as an alias and
  the help text now stating the distinction.

### Not done, stated plainly
- **No adapter for any of the ten named platforms exists.** The contract makes one implementable; it
  does not make one exist. Every integration remains `not_configured`.
- **No model provider adapter ships**, by design — that belongs in the runtime.
- **No write path ships at all**, and none will.

## [3.2.4] — 2026-10-12

### The problem this release answers

A fair challenge was put to this project: *it connects to no data platform, collects no user
behaviour, makes no network request, and is not a marketing tool; its commercial value might lie in
consulting, training or evaluation, and none of that is validated.*

The critique is correct, and the sharpest part of it was not the absence of integrations. It was this:
**every number this skill produced was computed by a language model, in its head.** Three independent
runs had returned three different answers for the same quantity — the month an operator's reserve runs
out: 46, 37 and 22.5. A rule that says *derive it, do not borrow it* is worthless if the derivation is a
guess.

### Added — arithmetic moved out of the model

- **`tools/strategy_calc.py`** — deterministic strategy arithmetic with no model involved: contribution
  LTV (optionally discounted), allowable CAC as the binding constraint of the LTV ceiling and the
  payback ceiling, break-even units and utilisation, per-party monthly cash flow with reserve
  exhaustion, and statistical power (`required_sample_per_arm`, `detectable_effect`). It reads no
  network, no platform and no user data.
  - Missing inputs are **reported, not assumed**: the tool names the field you did not supply instead
    of inventing a plausible value.
  - A structurally negative business is labelled `STRUCTURAL` rather than optimised.
  - Self-tested with 22 assertions covering the primitives, the two-ceiling rule, the power
    arithmetic, every fixture, and the refusal to invent. Run in CI and asserted by the verifier.
  - Two defects were found and fixed during its own self-test: `detectable_effect` returned an absurd
    `1000%` for hopeless samples (now returns the real value, or `None` below the floor of
    usefulness), and two of the assertions themselves were wrong rather than the code.
- **`resources/EVAL_RUBRIC.md`** — a ten-check, pass/fail standard for scoring a strategy deliverable,
  split into five checks that are recomputable and five that need a reader. Offered as a candidate
  standard for consultancy, training or procurement, explicitly **not** validated with anyone.
  Scored against itself, an earlier version of this package fails three of the ten; those failures are
  named in the rubric.
- The skill entrypoint now instructs the model to compute with `tools/strategy_calc.py` rather than in
  its head.

### Changed — the boundary is now stated where visitors look

The README gained a "What runs, and what does not" table. It states plainly that this reads none of
your platforms, measures none of your users, and will not pretend to. What it does is operate on
material you already have: paste in the figures and it computes, labels and challenges them, and tells
you which input is missing when a number cannot be derived.

That limit is real. It means this cannot tell you what your customers did — only whether the story you
are telling about them holds together arithmetically.

## [3.2.3] — 2026-10-12

### Fixed — the package contradicted itself, in the way it warns about
A pre-publication review of this repository found that its own case study and its refusal demo gave
**different answers for the same quantity**, and that two figures in the case study could not be
reproduced from the stated inputs:

- the case study asserted the operator's bond was exhausted in "months 12–16"; the demo computed
  month 46 from the same figures, and an independent run computed month 22.5;
- the case study described a 42,800/month cost basis gap as having a "12.5 months" effect, without
  saying whose effect. The gap is a cost on the operator's side; the annualised owner impact is
  27,820/month = 333,840/year; and the *payback* swing is 1.0 year. Three different quantities, one
  unattributed number.

Both were corrected. The bond paragraph now presents all three models in a table and states what is
robust across them (the operator is cash-negative at every achievable occupancy, so the target does not
restore solvency) versus what is assumption-dependent and therefore open. The cost paragraph now labels
each figure by party and basis.

This is the defect this project exists to catch, committed by this project's own documentation — one
run's answer quoted without its basis, in a document about the danger of doing precisely that. It is
recorded rather than quietly amended, consistent with the rule in the changelog preamble.

### Added
- **`examples/refusal-demo/`** — the skill's arithmetic and evidence rules executed deterministically,
  with no model involved. It fails on purpose (exit code 1) and prints its own assumption variants
  side by side. This exists because the package's headline claim is about model behaviour, which
  cannot be unit-tested from a repository; the rules can be, and now are.
- **CI** (`.github/workflows/verify.yml`) — runs the verifier, the validator suite and the refusal demo
  on Python 3.9 and 3.12 for every push and pull request. Without it, "verify it, don't trust it" was
  an instruction with no automation behind it.

### Changed
- `tests/RESULTS.md` and the case study now cite the three independent runs with their differing
  results, instead of presenting one as settled.

## [3.2.2] — 2026-10-12

Second round of changes driven by real-project runs: an AUDIT of a delivered proposal, a RED_TEAM
of the same engagement, and a GROWTH_DIAGNOSIS with a full unit-economics rebuild. All three
reviewers produced concrete defects with reproduction steps. Their criticisms are recorded here
rather than summarised away.

### Fixed — the schemas were structural, not meaningful
The most serious defect found in this project so far. A reviewer ran adversarial tests and
demonstrated that the KPI schema accepted **10 of 10** semantically empty documents and the
experiment schema **8 of 8** — including a card with no control, empty guardrails, the decision rule
"we'll figure it out later", `primary_metric: impressions`, and `status: complete` while claiming a
causal result. Their assessment: *"this is more dangerous than no schema, because it manufactures a
false sense of compliance."* They were right.

- `experiment.schema.json` rebuilt as a **quality** checker. `control` is required and non-empty;
  `guardrails` needs at least one entry; `guardrail_thresholds` must name a level for each guardrail
  (a guardrail without a threshold stops nothing); `decision_rule` is now an object requiring
  `pass`, `fail`, `inconclusive` and `threshold` (the inconclusive branch is the one everyone omits
  and the one everyone needs); `minimum_detectable_effect` requires `value`, `method`, `n_per_arm`,
  `available_n` and `adequate`; `claim_strength` and `limitations` are required.
- `kpi_tree.schema.json`: a **guardrail** node must state its threshold; an **outcome or driver**
  node must state a target. A metric that cannot stop anything or cannot be managed is not a metric.
- `evidence.schema.json` gained `$defs.grade` and `$defs.label` so other schemas can reference the
  grades instead of restating them.

### Added — a validator that can actually fail
- `tests/schema_validator.py`: a documented JSON Schema subset validator, because `jsonschema`
  cannot be installed into the bundled runtime here (its compiled `rpds` dependency fails macOS code
  signing). It **raises** on any keyword it does not implement rather than ignoring it — a validator
  that silently skips what it does not understand is how false compliance happens.
- `tests/test_validator.py`: 13 unit tests anchoring the validator's keyword semantics, plus 12
  adversarial tests against the shipped schemas. Both must pass for the package to verify.
- The ad-hoc checker previously embedded in `verify_package.sh` was **deleted**. It had twice
  accepted documents it should have rejected, and it is what allowed the false "prose requirements
  are representable" claim in 3.2.0.

### Added — method
- **`resources/AUDIT_MODE.md`**: auditing a supplied proposal is the highest-value use of this skill
  and previously had no specification in the body. A reviewer had to `grep` a file marked LEGACY to
  find it — *"strictly following the instructions to read `resources/` would have missed the
  definition entirely."* Now a first-class resource with the seven judgement questions, the four
  verdict tags, a severity scale separate from the gate scale, and an output shape.
- **Worksheet 35 — arithmetic and basis reconciliation**, and **Worksheet 36 — cross-document
  reconciliation**. A reviewer reported that 90% of their audit's value came from recomputation and
  cross-reading, and that *not one of the 34 worksheets asked for either*. Both now exist, including
  the required check for whether a rounding direction favours the conclusion.
- **Separate the calculation per party.** A reviewer identified that distinguishing the operator's
  position from the landlord's was the single analytical lever that turned a polished channel plan
  into "do not sign this contract" — and that the skill never asked for it. It now does, with the
  rule that a party breaking even only above achievable occupancy is a stop condition.
- **Sample-size adequacy.** The skill required reporting under-powered tests as directional but
  never checked whether any test was possible. Now: `baseline → MDE → n per arm → available n →
  adequate?`, and an inadequate test is labelled directional in the card itself.
- **Cash-flow timing is mandatory** for multi-party, revenue-share, bond or staged-investment work,
  before any financial finding is stated.
- **Minimum execution standards** on each of the nine Red Team angles — a direction without a depth
  standard lets a reviewer return "broadly looks sound".
- **Evidence-grade usage limits**: grade C may not support a pricing ceiling, a TAM or a demand
  conclusion; cross-grade use must be labelled.
- **Mapping table** when source documents carry their own grading system, since a document's "A"
  (authoritative publisher) and this skill's "A" (first-party evidence) run in opposite directions.
- **Metric cards**; **six-part Red Team argument structure**; **inference hygiene** (grade the
  derivation, name the load-bearing assumption, never average across incompatible bases); a
  **reproducibility rule** (a model claiming to be reproducible must be reproduced).

### Fixed — contradictions the reviewers found
- `next_actions[]` was listed in two files and omitted from a third: the envelope is now ten fields
  everywhere, asserted by the verifier.
- Red Team angles were 7 in one place and 9 in another; nine everywhere.
- Router role aliases matched no contract id; all rows now use canonical ids.
- `SKILL.md` referenced `resources/...` paths that did not exist, and a bare-name variant that
  resolved nowhere; the verifier now resolves exactly as the model is told to.
- Resource file permissions were mixed 600/644, a distribution hazard on a shared machine. All 644.
- Replaced the unfalsifiable self-check ("can the decision-maker act within 60 seconds?") with an
  answerable one. Reframed the "working persona" list as declared taste rather than rule; a reviewer
  called it *"prayer, not a rule"*, which is fair.

### Known limitations, stated plainly
- **Smoke tests T01–T12 remain unexecuted** and the log says so.
- The reviewers' harshest structural criticism stands partly unaddressed: the skill is **large
  relative to what a single task uses** — one reviewer estimated using under 15% of it for a
  10,000-word audit. The `§2 Modes` routing and the AUDIT specification are the first response to
  that; a future release should cut, not add.
- All ten integrations remain `not_configured`, and no run has ever claimed otherwise.

## [3.2.1] — 2026-10-12

Changes driven by a real-project red-team run on a live engagement (a 75-room bonded apartment
conversion). Every item below traces to a defect that run exposed. The reviewer's own words are
preserved where they identify the failure precisely.

### Added
- **Cash-flow timing is mandatory for multi-party structures.** Any project with revenue sharing, a
  bond or deposit, staged investment, or more than one party carrying cost must produce a
  month-by-month table — who pays, who receives, who funds the gap, when the funding party runs out —
  *before* any financial finding is stated. In the triggering engagement this was the single highest-
  value rule: it surfaced an entire missing input (whether the operator pays base rent) that two
  research reports totalling 22,000 words had skipped.
- **Minimum execution standards on each of the nine Red Team angles.** A direction without a depth
  standard lets a reviewer return "broadly sound". Finance now requires ≥3 scenarios plus one extreme
  case and a stated break-even; Organization requires checking whether the stated goal and the
  sanctioned remedy point the same way; Measurement requires verifying that a metric's numerator and
  denominator were not both relaxed.
- **Evidence-grade usage limits.** A/B may support conclusions; **C may not support a pricing ceiling,
  a TAM or a demand conclusion**; D may not be a conclusion's sole source; E may not be presented as a
  finding. Cross-grade use must be labelled `证据越级引用`. The commonest abuse — promoting a
  reference price list to "comparable transaction price" — is now named.
- **Mapping table requirement** when source documents carry their own grading system, because the two
  scales run in opposite directions (a document's "A" means *authoritative publisher*; ours means
  *first-party evidence*). The same material may hold different grades for different uses.
- **Metric cards.** Every number entering a model records coverage, denominator, fixed-or-variable,
  period/sample, and source/date. When the same quantity appears twice with different bases, that is a
  finding to report, not a rounding difference to absorb.
- **Six-part Red Team argument structure** (`assumption → evidence → failure mechanism → trigger →
  countermeasure → action`), which fits how an attack is actually argued, alongside the ten-field
  result envelope rather than instead of it.
- **Reproducibility rule.** A model that claims to be reproducible must be reproduced. If the script
  or spreadsheet is not supplied, its conclusions drop to `UNKNOWN` — and rebuilding it from scattered
  parameters is encouraged, because a mismatch between the rebuild and the stated result is itself a
  material finding.
- **Sample-adequacy test.** Whether the sample can carry *this* claim, not merely whether it was
  disclosed.
- **Unmitigated high risk downgrades the verdict** by one level. A plan that names its own fatal risk
  and then does not plan for it has not mitigated it.
- **Four or more stop conditions firing at once is a stop**, and the deliverable must name which ones
  fired and what would clear each.

### Fixed
- **A direct rule conflict**, reported by the reviewer: the state protocol said "with no state file,
  request the minimum artifact", while the modes section said "never block on a questionnaire". Now
  reconciled — never invent prior state, never block on its absence; create it and label what was
  established this session.
- **A gate that was never recorded.** The reviewer demonstrated that no gate had been persisted
  anywhere, making `PASS`/`BLOCKED` decorative. Gates must now be written to `gate_status` with their
  supporting evidence and named gaps.
- Replaced the unfalsifiable self-check — "can the decision-maker act within 60 seconds?" — with an
  answerable one: *if they may do only one thing tomorrow, what is it, and why not the other two?*
- Reframed the "working persona" list as declared taste rather than rule, so it stops masquerading as
  a control. The reviewer's assessment: "this is prayer, not a rule."

### Verified by the triggering run
The reviewer stated they would continue using the skill, and credited four findings they would not
otherwise have reached — none of which were marketing problems. Their summary of why it worked:
*"It pushed me out of a marketer's default frame."* They also confirmed the nine-angle list mainly
worked by **breaking structural resonance**: without it, a reviewer follows the document's chapter
order to the conclusion its author intended.

## [3.2.0] — 2026-10-12

### Added
- **DSH adapter** (`resources/DSH_ADAPTER.md`): how the skill is discovered and installed on
  DeepSeek Harness, the delegation mapping (`subagent` / `subagent_fork` / `workflow` / background
  jobs), state paths, and the honest verification-status table.
- **Operating rules** (`resources/OPERATING_RULES.md`): recovered methodology that existed only in
  the legacy Chinese file — the insight action test, rollback triggers, the five complex-project
  analyses (stakeholder structure, resource flow, value flow, cash flow, governance), the AI/human
  decision boundary, the supplied-file workflow, the A–G output protocol, the eleven prohibitions,
  and the working persona.
- **Analytic frameworks** (`resources/ANALYTIC_FRAMEWORKS.md`): 5C+, PESTEL+ and the Evidence
  Ladder. These three were named in the legacy file but existed **nowhere** in the package.
- **Role-specific agent contracts**: all 13 now define their own inputs, questions, method, musts
  and stop condition.
- **Reproducible example** (`examples/bonded-apartment-intake/`): a realistic, clearly-labelled
  intake brief for a 75-room bonded apartment conversion, written to exercise the full loop.
- **Objective smoke-test rubric** and `tests/RESULTS.md` result log.
- Release engineering: `LICENSE` (MIT), `CONTRIBUTING.md`, `.gitignore`, `CHANGELOG.md`.

### Changed
- **Schema rebuild.** All five schemas were rewritten. Previously `project_state.schema.json`
  rejected 9 of its own 10 documented containers under `additionalProperties: false`, 39 of 47 named
  fields had nowhere to live, and — because no schema referenced any other — `kpi_tree: {"garbage": 1}`
  and `experiments: [{}]` validated cleanly. Now: 26 top-level state properties, cross-file `$ref`s,
  and the verifier asserts that previously-accepted garbage is rejected.
- **Entrypoint budget.** `SKILL.md` is kept under the 8,192-character tool-result pruner threshold
  by moving detail into `resources/`. It is now ~8.06 KB rendered, so a compaction event cannot trim
  the middle of the instructions out of context.
- **Routing description** is now Chinese-first with the domains that actually trigger the skill
  (品牌全案、项目定位、产业策划、文旅、地产、园区), then English. Previously it was English-only, so
  those requests would not have routed here.
- Worksheet field lists strengthened where the prose demanded more than the row supplied: the
  insight chain's `emotion`, the creative brief's `creative challenge`, experiment `control` and
  `MDE`, funnel `period`/`source of truth`, campaign `cohort`/`baseline`, interview `consent`.
- Empty enums closed: `experiment.status` gained `proposed`, task-packet `source_status` gained
  `calculated` and `expert_judgment`, evidence labels gained `OBSERVATION`.

### Fixed
- The specialist output envelope was contradictory (9 fields in two files, 10 in a third). It is
  now consistently the ten-field envelope, and the verifier fails if the three files disagree.
- 12 of the 13 agent contracts were byte-identical copies of one template. The verifier now hashes
  contract bodies and fails on templating.
- Router role aliases (`master`, `research`, `analytics`…) did not match any contract id. All
  routing rows now use canonical ids.
- Red Team angles were 7 in the router and 9 in the quality gates. Now nine everywhere.
- `resources/` paths were listed bare in the entrypoint while the files live under `resources/`;
  the verifier now resolves exactly as the model is told to, instead of masking the bug.

### Removed
- The claim that the package was "statically checked" while its entrypoint was a byte-identical copy
  of the legacy file and therefore discoverable by nothing.
- `version:` from the skill frontmatter — the loader ignores unknown keys, so it was decorative.

## [3.1.0] — 2026-10-12

### Added
- First "DeepSeek Harness adaptation" package: orchestration protocol, task-packet and evidence
  schemas, phase gates, marketing-economics guardrails, tool status ladder, approval boundaries.
- 34 decision worksheets, 13 agent contracts, 5 JSON schemas, 11 integration contracts and a
  static checklist.

### Known state at release
- Authored and statically inspected only. **Not installed and not runtime-tested.** The entrypoint
  shipped as a byte-identical copy of the legacy `SKILL.md`, and the bundle was nested one level too
  deep to be discovered by any Harness. Recorded here because the package's own README said
  "statically checked", which was true and also not enough.

## [3.0] — legacy

The original Chinese `SKILL.md`: REBUILD loop, evidence protocol, 20 tools, strategic-choice rule,
consumer-insight rule with the action test, business-model questions plus complex-project additions,
creative and growth rules, AI collaboration boundary, file workflow, A–G output protocol, the
eleven prohibitions, and the working persona. Superseded by 3.2 but retained verbatim in
`docs/LEGACY_SKILL_V3.md` as the archive of record, with a banner listing what changed.
