# REBUILD Strategist

**A strategy skill with an exit code.**

An agent skill for business, brand and growth strategy that runs a six-phase loop — Reframe, Explore,
Build Position, Unify, Implement, Develop & Decide — with evidence labels on every claim, gates that
can block, arithmetic you can check, and a test suite that can fail it.

Most AI marketing tools generate. This one decides, shows its work, and **stops when the evidence
runs out.**

**And its arithmetic runs in code, not in a model's head.** Three independent runs of an earlier
version of this skill produced three different answers for the same number — the month an operator's
reserve runs out. A rule that says *derive it, do not borrow it* is worthless if the derivation is a
guess, so the calculations were taken out of the model and put in `tools/strategy_calc.py`, with
assertions that run in CI.

```bash
git clone <this-repo> && cd rebuild-strategist
python3 examples/refusal-demo/demo.py     # a plan that cannot pass the gates — fails on purpose
./tests/verify_package.sh                 # package integrity
```

**Start with the demo.** It applies the skill's stated rules to a delivered proposal, mechanically,
with no model involved, offline, in under a second — and exits non-zero because the proposal does not
survive them. You can read every rule it applies in [`SKILL.md`](SKILL.md) and every number it prints is
reproducible from the figures it shows.

```
Rule 1 — a headline figure must be reproducible
  recomputation: 3,000,000 ÷ (148,620 × 65%) = 31.1 months = 2.59 years
  to reach the claimed 1.9 years: occupancy 132.9%  ← impossible

Gate E (evidence)    BLOCKED
Gate B (choice)      BLOCKED
...
Exit code 1 = the proposal failed the gates. This demo fails on purpose.
```

That is the point of the project. Not a prompt pack you take on faith — a rule set you can execute,
and a test suite that can fail it.

---

## What is actually unoccupied in this space

An honest survey of the category, because you should know what you are looking at:

| Capability | State of the ecosystem | Here |
|---|---|---|
| Channel execution skills (SEO, ads, email, content) | **Saturated and funded.** The category leader ships ~386 skills and ~115 integration tests against real CLIs. Competing on breadth is already lost. | Not attempted |
| **Evidence grading and source discipline** | Almost absent. Mainstream packs require you to paste data in; otherwise the model grades its own guesses. | Core |
| **Falsifiability — thresholds, stop rules, "what would change this decision"** | **Not one** of the fifteen most relevant projects surveyed ships any of these. Everything ends at generation. | Core |
| Strategy → measurement bridge | MMM and incrementality libraries are mature (Meridian, Robyn, PyMC) but are analyst tooling with no strategy interface. | Schema-level, not a library |
| Brand measurement in the open | A vacuum — the `brand-equity` topic on GitHub tops out at 4 stars while GEO trackers crowd the space. | Not attempted |
| Licensing and maintenance hygiene | Several high-star packs ship no licence at all; many are single-author burst-then-abandon. | MIT, verified, `not_configured` until proven |

Two consequences shaped this project:

1. **Scope discipline.** This does not do channel execution. It does the part that decides whether
   channel execution is worth funding.
2. **Executable proof, or it reads as slop.** A markdown pack with no test, no refusal behaviour and no
   worked case gets classified as AI slop regardless of how good its frameworks are. So the schemas
   reject malformed input, the verifier fails on inconsistency, and the smoke tests have binary pass
   conditions.

---

## The problem it solves

Ask a general model for a marketing strategy and you get something fluent, confident and
unfalsifiable: an invented market size, a borrowed benchmark, a positioning statement with no
alternatives, and no way to tell which sentence was verified and which was improvised. It reads well
and it is not safe to act on — and the failure is invisible, because nothing in the output
distinguishes a checked number from a plausible one.

Four disciplines change that:

**1. Every claim carries its epistemic status.** `FACT` · `INTERPRETATION` · `HYPOTHESIS` ·
`DECISION` · `UNKNOWN`, with source quality graded separately from relevance (A first-party ·
B official or audited · C credible secondary · D expert judgment · E untested assumption) — and the
grades **limit use**: grade C cannot support a pricing ceiling, a TAM or a demand conclusion.

**2. Numbers are derived, not borrowed.** Break-even, allowable CAC and budget caps are computed from
the margin structure in front of you. CAC is distinguished from CPL, contribution LTV from revenue
LTV, ROAS from ROI, attribution from incrementality. Calculations are run **once per party**, because
in any shared-revenue or bonded structure "the unit economics" is not one number.

**3. Gates can block.** Six gates, each returning `PASS`, `PASS_WITH_GAPS` or `BLOCKED`, recorded with
the evidence they rest on. "Do not pass a gate to keep momentum" is a rule, not a sentiment. There are
named stop conditions, and four or more firing at once is a stop.

**4. The loop goes backwards.** If the customer evidence contradicts the chosen differentiation, the
skill reopens the gate it invalidated instead of continuing into creative work because the brief said
to.

---

## The refusal behaviour, demonstrated

The part most tools do not have. From an audit run on a delivered proposal that claimed a 1.9-year
payback:

> **Recomputation.** 3,000,000 ÷ (148,620 × 65%) = 31.1 months = **2.59 years**. For 1.9 years to
> hold, the monthly payout would need to be 131,579 — implying **132.9% occupancy**.
>
> **Same document, three answers.** The executive summary says 1.9 years; the modelling section says
> 2.4–2.8 years; the KPI table says ≤ 30 months.
>
> **Verdict.** Gate E: `BLOCKED`. The claim is not imprecise; it is not reproducible.

And on cost basis, in the same engagement:

> The plan's distributable-profit definition subtracts a monthly fee of 15,000. The companion research
> report puts the operator's actual monthly operating cost at 57,800. The gap is **42,800 per month** —
> 333,840 per year against the landlord's share — and it moves the payback period by **12.5 months**.
> Two documents, two definitions of "profit", one printed summary.

Neither finding needed data the user did not already have. They needed arithmetic and cross-reading,
which is exactly what most strategy output never does.

---

## Install

A skill is a directory discovered from the filesystem. Discovery is **one level deep**, so the folder
must be `<root>/rebuild-strategist/SKILL.md`.

```bash
# DeepSeek Harness roots, in priority order:
#   100  <projectRoot>/.dsh/skills      this workspace only
#   400  ~/.dsh/skills                  every session
#   500  ~/.agents/skills               shared agent-config convention

mkdir -p ~/.dsh/skills
cp -R . ~/.dsh/skills/rebuild-strategist
```

Any runtime that loads directory-shaped skills with YAML frontmatter (`name`, `description`) can use it
unchanged; the same directory works under `~/.agents/skills`. Reference files are addressed relative to
the skill directory, which the loader reports as the base directory. See
[`resources/DSH_ADAPTER.md`](resources/DSH_ADAPTER.md).

---

## What runs, and what does not

Stated plainly, because the boundary is the honest part.

| Capability | Status |
|---|---|
| Deterministic arithmetic — contribution LTV, allowable CAC, break-even, per-party cash flow, required sample size | **Runs in code.** `tools/strategy_calc.py`, asserted in CI |
| Rule enforcement — gates, evidence grades, refusal to certify unsupported claims | **Runs as instructions to a model.** Verified in a live session and in the demo |
| Package integrity, schema quality | **Runs in code.** CI on every push |
| Reading your data platform, ad accounts, CRM, analytics | **Does not do this, and will not pretend to.** All ten integration contracts ship `not_configured` |
| Measuring your users, campaigns or incrementality | **Does not do this.** There is no telemetry, no network call, no data collection |
| Replacing an ads platform, CRM, or BI tool | **No.** It is not that kind of software |

So what is it? **A decision instrument that operates on material you already have.** You paste in the
figures — a media plan, a P&L, an operations report, a competitor's published pricing — and it
computes, labels and challenges them. Where a number cannot be derived from what you supplied, it says
which input is missing instead of inventing one.

That boundary is deliberate and it is also a limit. It means this cannot tell you what your customers
did; it can only tell you whether the story you are telling about them holds together arithmetically.

## Verify it, don't trust it

```bash
./tests/verify_package.sh        # static integrity
python3 tests/test_validator.py  # validator unit tests + adversarial schema tests
python3 examples/refusal-demo/demo.py   # the rules, executed (exits 1 by design)
```

All three run in CI on Python 3.9 and 3.12 for every push and pull request
([`.github/workflows/verify.yml`](.github/workflows/verify.yml)).

The verifier checks that the frontmatter is one the loader will accept (three specific mistakes make a
skill vanish silently), that every resource the entrypoint references resolves against the base
directory, that the rendered body stays under the 8,192-character context-pruner threshold, that the
ten-field output envelope agrees across every file, that the schemas are wired to one another **and
reject malformed state**, that no two agent contracts are identical templates, and that the package
over-claims nothing in its own README.

The adversarial suite exists because an earlier version of these schemas **passed 10 of 10 semantically
empty KPI documents and 8 of 8 empty experiment cards** — including a card with no control, empty
guardrails, the decision rule "we'll figure it out later", and `status: complete` while claiming a
causal result. A schema that validates structure while accepting nonsense manufactures false
compliance. It was rebuilt, and the tests that caught it are now part of the suite.

Behaviour is tested separately in [`tests/SMOKE_TESTS.md`](tests/SMOKE_TESTS.md): 12 prompts with binary
pass conditions, including a refusal test, a tool-honesty test, an arithmetic test and a rollback test.
Current results — including unverified runs — are in [`tests/RESULTS.md`](tests/RESULTS.md).

---

## What makes it different, concretely

|  | Typical marketing prompt pack | REBUILD Strategist |
|---|---|---|
| Unit of value | A prompt per task | A decision process with gates |
| Claims | Presented flat | Labelled and graded, with provenance |
| Numbers | Benchmarks, often invented | Derived from the business model, formulas shown |
| When evidence is missing | Confident answer anyway | Blocks, or `PASS_WITH_GAPS` with a named test |
| Arithmetic | Not checked | Recomputed; unreproducible figures are `UNKNOWN`, not approximate |
| Multi-party deals | One model | One model **per party**, with the month each reserve runs out |
| Experiments | Proposed | Must state control, guardrails with thresholds, MDE vs available n, and a three-branch decision rule |
| Delegation | One big prompt | 13 role contracts, ten-field output envelope |
| State | Re-explained each session | Persisted and validated against a schema |
| Verification | None | Verifier + validator + 12 behavioural tests |

---

## Modes

`FULL_STRATEGY` · `QUICK_STRATEGY` (Problem → Evidence → Opportunity → Choice → Next Test) ·
**`AUDIT`** (Keep / Upgrade / Delete / Validate, with recomputation and cross-document reconciliation) ·
**`RED_TEAM`** (nine angles, each with a minimum execution standard, plus a mandatory cash-flow timing
table for multi-party structures) · `GROWTH_DIAGNOSIS` · `CAMPAIGN_BUILD` · `WORKSHEET` ·
`PROJECT_CONTINUATION`.

A full run produces a decision page, not a deck: the decision required, the recommendation, the options
rejected and why, the unit-economics line it rests on, what evidence would reverse it, who must
approve, and the conditions under which it should be stopped.

---

## Who it is for

- **Founders and operators** deciding whether a plan is worth funding — you get the arithmetic and the
  assumption register, not a story.
- **Strategy, brand and marketing practitioners** who have a proposal and need it attacked before the
  client sees it (`AUDIT`, `RED_TEAM`).
- **Agencies and consultants** whose reasoning has to be auditable, because someone asked "where does
  this number come from?"
- **Analysts and CMOs** diagnosing a metric that moved — denominator, cohort and window pinned down
  before anyone names a cause.
- **Engineers building agents** who want a worked example of schema-validated agent state, contracts
  and a self-failing test suite rather than free-form chat.

A poor fit if you want volume content generation, channel execution at scale, or a guaranteed answer
regardless of evidence.

---

## Plugging in your own model, or your own data

Two different integrations, deliberately separated. A third is refused on purpose.

### Your model — nothing here to change

This package contains **no model client, no API key handling, no network code**. Your runtime selects
the model; the skill is instructions plus resources. To run it on GPT, Claude or a local model, install
the directory into that runtime's skill root — `SKILL.md` is plain Markdown with YAML frontmatter, which
is the portable subset. If you are writing your own agent loop, load `SKILL.md` as the system prompt,
expose `resources/` as readable files, and expose `tools/strategy_calc.py` as a tool named
`strategy_calc`.

Model adapters belong in your runtime, not in this repository. Adding one here would make the package
runtime-dependent while claiming to be portable.

### Your data — a contract, and a checker that enforces it

If your figures live in an analytics tool, CRM, ad platform or warehouse, write a small adapter that
converts them into the JSON `strategy_calc.py` consumes. The contract is in
[`resources/ADAPTER_CONTRACT.md`](resources/ADAPTER_CONTRACT.md); the output shape is
[`resources/schemas/adapter_output.schema.json`](resources/schemas/adapter_output.schema.json); a
Three working references ship, in three different shapes, because one template proves nothing:

| Adapter | Shape | Handles |
|---|---|---|
| [`tools/adapters/csv_export.py`](tools/adapters/csv_export.py) | manual | a CSV you exported by hand |
| [`tools/adapters/posthog.py`](tools/adapters/posthog.py) | **live API** | credentials from the environment, one read-only GET, plus `--offline` replay for CI and for working without a key |
| [`tools/adapters/upstream_json.py`](tools/adapters/upstream_json.py) | **tool-to-tool** | a declared JSON envelope on stdin — how an MCP server, a dbt run or a colleague's script hands data over |

All three run against fixtures in [`examples/adapter/`](examples/adapter/) with no credentials and no
network, and all three pass the contract checker in CI.

```bash
python3 tools/check_adapter.py --adapter ./my_adapter.py -- --input export.csv
```

The checker runs your adapter and rejects it for the failures that matter:

```
FAIL: 3 contract violation(s):
  - rule 2: 'retention_months' has no provenance entry — declare where it came from
  - rule 2: 'price_per_unit' has no provenance entry
  - rule 6: adapter claims status 'connected'. A checker run cannot evidence more than 'configured'
```

Three rules do the real work, and they are the reason this contract exists rather than a connector zoo:

1. **Never invent a value.** A field the source cannot supply goes in `missing`. An adapter cannot
   silently omit the fact that it omitted something.
2. **Declare provenance for anything derived**, with a grade from the skill's own A–E scale. A number
   read from a platform is not automatically grade A — it is A only if that platform is your system of
   record.
3. **An adapter may not promote its own status.** A checker run can evidence `configured` at most;
   `connected` requires a recorded read of the live system, and `production_approved` requires a named
   human.

### Live platform access — allowed, and gated

Read-only access is the place to start, and the status ladder in
[`resources/tool-registry.yaml`](resources/tool-registry.yaml) records how far each one has actually
got. **Every integration ships `not_configured`.** A YAML entry is not evidence, and neither is a
passing unit test — moving a status without the corresponding observation is the one thing this project
treats as a defect rather than a gap.

### The whole chain, end to end

A real run of the chain — a PostHog funnel, contract-checked, then combined with finance's figures:

```
  contribution / unit         42   (42.0% margin)
  contribution LTV            790   [contribution, horizon 19 months, undiscounted]
  allowable CAC               499
     basis                    binding constraint = payback (payback tolerance 12 months)
  test needs                  5,785 per arm
     available                12,480   adequate: True
```

Two things worth reading in that output. The **binding constraint is payback, not LTV** — the 12-month
tolerance caps acquisition cost at 499 where lifetime value would have allowed 790, so a plan built on
the higher number is wrong by 58%. And the **proposed test is adequately powered** — 5,785 units per arm
needed against 12,480 available. Had it gone the other way, the arithmetic would have said so before
anyone spent money.

Note what PostHog contributed: a retention curve and a funnel conversion. It could not contribute
margins, ad spend or sales labour, and the adapter names all seven of those in `missing` rather than
filling them with plausible defaults. That division of labour is the design, not a shortcoming.

**What is refused by design:** no write path ships in this repository. Adjusting a bid, sending a
campaign or updating a CRM record belongs in code you wrote and reviewed, behind an approval gate you
control. The skill drafts; a human authorises.

## Where the commercial value might be — and what is unvalidated

This project has no customers, no pilot and no revenue. Three plausible uses exist; none is validated,
and saying so is part of the deliverable.

| Possible use | Why it is plausible | What is unvalidated |
|---|---|---|
| **Consulting / advisory** | A consultant can apply the rubric and the gate rules to a client's proposal and show their working. The engagement record in `examples/` is a real instance of this. | Whether a client would pay for it, and whether the findings change their decision |
| **Training / internal capability** | The ten-check rubric in `resources/EVAL_RUBRIC.md` is a teachable standard, and the refusal demo is a teaching artefact: it fails visibly, which is rare in training material | Whether teams adopt it, and whether it survives contact with deadlines |
| **Evaluation layer** | Judging strategy output is a real and growing need, and there is no widely accepted standard. Half the rubric is machine-checkable today | Whether anyone else accepts these ten checks as the right ones. A standard with one author is a proposal, not a standard |

**What would falsify each.** Consulting: a client running the rubric and finding the output obvious.
Training: a team that scores well afterwards but makes the same errors. Evaluation: an alternative
rubric that predicts outcomes better.

None of that has been tested. The honest description today is: **a well-tested instrument looking for
evidence that anyone needs it.**

## Honest status

| Claim | Status |
|---|---|
| Installs and loads on DeepSeek Harness | **Verified** — observed in a live session; body and resource base delivered correctly |
| Static integrity | **Verified** — `tests/verify_package.sh` passes |
| Schemas reject malformed input and accept valid input | **Verified** — assertions in `tests/test_validator.py` |
| Real-project runs produced material findings | **Verified** — three independent runs on a live 75-unit engagement, each with reproducible arithmetic |
| Those runs also found defects **in this skill** | **Verified** — recorded in `CHANGELOG.md` rather than quietly fixed |
| Behavioural smoke tests T01–T12 | **Not yet run** — see `tests/RESULTS.md` |
| Any integration connected | **No** — all ten are `not_configured` |
| It improves a decision | **Your judgement, not our claim** |

---

## Worked example

[`examples/bonded-apartment-intake/`](examples/bonded-apartment-intake/BRIEF.md) is a realistic,
clearly-labelled intake brief for a 75-room bonded apartment conversion — deliberately incomplete in
the way real briefs are: no cost structure, no demand evidence, no competitors. Drop it into a session
and ask for an `AUDIT` or `GROWTH_DIAGNOSIS` run. The case study above is anonymised from a real
engagement; the client's documents are not included.

---

## Repository layout

| Path | Contents |
|---|---|
| `SKILL.md` | Entrypoint: loop, modes, orchestration, evidence, choice, economics, gates, safety |
| `resources/AUDIT_MODE.md` | Auditing a supplied proposal: seven questions, four verdict tags, severity scale |
| `resources/OPERATING_RULES.md` | Evidence protocol, metric cards, per-party economics, safety, state, output |
| `resources/QUALITY_GATES.md` | Gate criteria, nine Red Team angles with minimum standards, stop conditions |
| `resources/WORKSHEETS.md` | 36 worksheets, including arithmetic and cross-document reconciliation |
| `resources/ANALYTIC_FRAMEWORKS.md` | 5C+, PESTEL+, Evidence Ladder |
| `resources/MARKETING_OS.md` | Funnel, KPI tree, budgeting, attribution, B2B |
| `resources/PROJECT_ROUTER.md` · `resources/AGENT_ROSTER.md` · `resources/agents/` | Classification, routing, 13 role contracts |
| `resources/DELIVERABLES.md` · `resources/DSH_ADAPTER.md` | Output order and self-check; Harness install and delegation |
| `resources/schemas/` | JSON Schemas: project state, task packet, evidence, experiment, KPI tree |
| `tools/strategy_calc.py` | Deterministic strategy arithmetic: allowable CAC, break-even, per-party cash flow, sample size. Self-tested |
| `tools/check_adapter.py` · `tools/adapters/` | The adapter contract, its enforcement, and three reference adapters (manual, live API, tool-to-tool) |
| `resources/ADAPTER_CONTRACT.md` | How to plug in your own data source or model runtime |
| `examples/refusal-demo/` | The skill's rules executed deterministically, no model involved; exits 1 by design |
| `tests/` | Verifier, schema validator, validator tests, smoke tests, honest result log |
| `.github/workflows/` | CI: verifier, validator suite and demo on Python 3.9 and 3.12 |
| `docs/LEGACY_SKILL_V3.md` | The superseded original, kept for provenance and marked as such |

---

## Contributing

The admission test for any addition: **what decision comes out different if this does not exist?**
Rules that never change an output consume attention and dilute the ones that bite. The contribution we
most want is a reproducible failure — a case where the skill answered confidently and wrongly, plus a
test that catches it. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT — see [`LICENSE`](LICENSE). Advice for human decision-makers; not legal, financial or regulatory
advice. See [`SECURITY.md`](SECURITY.md) for the action boundaries the skill enforces: it drafts, it
does not publish, send, spend or delete without explicit approval at the moment of action.
