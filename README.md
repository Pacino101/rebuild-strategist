# REBUILD Strategist

[![CI](https://github.com/Pacino101/rebuild-strategist/actions/workflows/tests.yml/badge.svg)](https://github.com/Pacino101/rebuild-strategist/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#requirements)

**A decision-centric operating system for marketing strategy.**

Most marketing prompts and template tools solve the wrong problem: *"how do I produce a document that looks like a consulting report."*

REBUILD solves this one: **how do you know whether the conclusions in that report are worth believing — and worth spending money on?**

It does not try to produce longer reports. It forces four questions:

1. What decision actually needs to be made right now?
2. Which statements are facts, which are inferences, which are only assumptions?
3. What was given up, and at what cost?
4. What evidence would prove this decision wrong?

[中文说明见 README.zh-CN.md](README.zh-CN.md)

---

## Install

### Requirements

**Python 3.9+ and nothing else.** Zero third-party dependencies — the entire system is standard library. No numpy, pandas, openpyxl, jsonschema, or LLM SDK.

### Option 1 — one command

```bash
curl -fsSL https://raw.githubusercontent.com/Pacino101/rebuild-strategist/main/install.sh | bash
```

Downloads the repository to `~/.rebuild-strategist`, runs the test suite, and installs the DeepSeek Harness skill if `~/.dsh` exists.

### Option 2 — download the release (no git needed)

```bash
curl -L -o rebuild-strategist.tar.gz \
  https://github.com/Pacino101/rebuild-strategist/archive/refs/tags/v3.10.0.tar.gz
tar -xzf rebuild-strategist.tar.gz
cd rebuild-strategist-3.10.0
python -m unittest discover -s tests
```

### Option 3 — clone, then put the launcher on your PATH

```bash
git clone https://github.com/Pacino101/rebuild-strategist.git
cd rebuild-strategist
ln -s "$PWD/bin/rebuild" /usr/local/bin/rebuild
rebuild --help
```

> **There is no pip package, deliberately.** The orchestrator reads `agents/`,
> `schemas/` and `examples/` relative to the repository root. Installing the code
> into `site-packages` would separate it from those files and break the tool.
> Run it from a checkout.

```bash
git clone https://github.com/Pacino101/rebuild-strategist.git
cd rebuild-strategist
python -m unittest discover -s tests -v      # 297 tests, no network
```

### Verify the install

```bash
python core/rebuild_cli.py validate examples/metro_apartment/project.json
cd examples/metro_apartment/rebuild && python3 scripts/run_all.py
```

The second command reproduces every number in the worked case study.

---

## What this project is NOT

Stated before what it can do, because a project whose selling point is "we don't overclaim" should not be vague in its own introduction.

| It is not | Because |
|---|---|
| **An ads / CRM / analytics tool** | It connects to no marketing data platform, sends no ads, manages no customers, collects no behavioural data. Keep using your existing platforms for that. |
| **An automated execution system** | It performs no marketing action. It produces decisions and validation plans; execution is still human. |
| **A parallel multi-agent runtime** | `core/orchestrator.py` calls role contracts **sequentially** — one role, one model call. Roles do not talk to each other or run concurrently. Wrapping sequential calls as "multi-agent collaboration" is exactly what this project argues against. |
| **A connector library** | It imports local files and HTTP endpoints *you* provide. It ships **no** connectors for PostHog, Mautic, ad platforms, or CRMs. |
| **A guarantee of correct conclusions** | It constrains whether the *reasoning* is honest, traceable and falsifiable. It does not make the conclusion right. |

**Its commercial value is currently a hypothesis, not a result.** Plausible directions include consulting delivery, corporate training, and use as an evaluation layer for marketing proposals or AI output. **None has been validated by a real client engagement, and this repository does not claim otherwise.**

What *has* been verified: the methodology is internally consistent; the state machine is deterministic; the schema validator, evidence ledger, decision store, data sources and orchestrator are implemented and covered by tests; the orchestrator runs end-to-end against a real model; and one real, anonymised project has been run through it.

---

## Quick start

### 1. Validate a project

```bash
python core/rebuild_cli.py validate examples/metro_apartment/project.json
```

### 2. Load your evidence

```bash
# Import raw material (CSV / TSV / JSON / JSONL / TXT / MD / XLSX)
python core/rebuild_cli.py source add-file projects/my-project ~/Downloads/orders.csv

# Record a piece of evidence — validated against the schema before it is written
python core/rebuild_cli.py evidence add projects/my-project \
    --claim "Enquiries in the two weeks before peak season run ~3x the annual average" \
    --type FACT --confidence MEDIUM \
    --source-doc DOC-001 \
    --scope "Owned stores, local repeat customers" \
    --decision-impact "Determines whether the annual budget shifts to a peak-season push"

# Which assumptions still have no evidence behind them?
python core/rebuild_cli.py evidence gaps projects/my-project
```

### 3. Run the loop

```bash
# No API key needed: generates task packets only, zero network calls
python core/rebuild_cli.py run projects/my-project --dry-run

# Or drive a real model
export DEEPSEEK_API_KEY=sk-xxx
python core/rebuild_cli.py run projects/my-project --provider deepseek
```

### 4. Record the decision, review it later

```bash
python core/rebuild_cli.py decision add projects/my-project \
    --question "Which brand and channel strategy should we commit to?" \
    --option "Peak-season push|Demand is concentrated" \
    --option "Even spend year-round|Stable but misses the peak" \
    --chosen "Peak-season push" \
    --rejected "Even spend year-round|Misses the peak" \
    --tradeoff "Gives up off-season visibility" \
    --assumption "Demand concentrates in late March" \
    --falsification "Refuted if April repeat rate falls below 15%" \
    --validation "Small A/B test, n=200" \
    --review-date 2027-05-01

# Later: which decisions are due for review and have not been reviewed?
python core/rebuild_cli.py decision due projects/my-project

# Back-fill what actually happened
python core/rebuild_cli.py decision outcome projects/my-project --id DR-001 \
    --expected "Peak-season sales up 30%" \
    --actual "Up 12%, below target" \
    --deviation EXECUTION --next-action ADJUST \
    --notes "Underfunded, not a wrong direction"
```

---

## The six-phase loop

```text
R  Reality             Frame it        What is the decision vs. the symptom?
E  Evidence            Build evidence  Label every claim FACT / INFERENCE / ASSUMPTION / UNKNOWN
B  Bet                 Choose          Compare 2-4 materially different options; state what you gave up
U  Unit Economics      Does it work    Revenue != profit, ROAS != contribution margin
I  Implementation      Execute         Bind every action to owner, cost, metric, stop condition
D  Decision Review     Review          Separate execution failure from strategy failure
                         ^                    |
                         +--- assumption falsified ---+
```

It is a **loop with rollback**, not a pipeline. Insufficient evidence rolls back to E; broken unit economics roll back to B; a falsified assumption rolls back to the affected phase — rather than appending a risk paragraph to the end of a report.

## Three hard constraints

**Evidence must be traceable.** Every material claim is labelled `FACT`, `INFERENCE`, `ASSUMPTION` or `UNKNOWN`, with confidence `HIGH` / `MEDIUM` / `LOW`. **Model tone is not evidence.**

**Trade-offs must be explicit.** Every recommendation carries at least one alternative, what was rejected, the cost, and the conditions under which it holds. If you cannot say what you gave up, you have not finished deciding.

**Financial definitions must be reproducible.** Every metric states its formula, numerator, denominator, time window and data source. An LTV without an observation window is not a number. A CAC that does not distinguish channel / blended / incremental basis is not a number.

---

## Roles

A master agent owns orchestration and gates. Eight specialist roles each have a distinct mission, explicit input boundaries (they **refuse** out-of-scope questions), their own interrogation checklist and their own failure modes.

| Role | Core question |
|---|---|
| Customer Evidence | Does the need actually exist, for whom, in what situation? |
| Market Structure | What structure is this business in, and what earns entry? |
| Positioning & Strategy | What position do we hold in the customer's mind, and what do we give up? |
| Business Model | Does it work financially, how long to payback, when does it break? |
| Growth System | Through what mechanism do we acquire repeatably? |
| Measurement & Experiment | How do we know it worked, and how do we know to stop? |
| Red Team | What evidence would overturn the current choice? |
| Learning & Review | What actually happened, and how do the assumptions update? |

The refusal mechanism is the point: Market Structure refuses to answer demand-strength questions; Business Model refuses to propose positioning. Contracts live in `agents/`.

---

## Connecting your own model

`bench/provider.py` is a pluggable model layer: standard library only, no SDK. Two modes.

**Manual (default) — zero network calls.** Render the prompt, paste it into any chat window, save the output back.

**HTTP — call an API directly.**

```bash
python bench/provider.py list                      # built-in presets
python bench/provider.py check deepseek            # preflight: base_url / model / key

export DEEPSEEK_API_KEY=sk-xxx
python bench/provider.py call deepseek --prompt-file prompt.txt
```

Presets: `openai` · `deepseek` · `moonshot` · `qwen` · `anthropic` · `ollama` (local) · `custom`.

**Any OpenAI-compatible endpoint** — a self-hosted proxy, another vendor, a local inference server:

```bash
python bench/provider.py call custom \
    --base-url https://your-endpoint/v1 \
    --model your-model \
    --api-key-env YOUR_KEY
```

**Extending it:** add one dict to `PROVIDER_PRESETS` in `provider.py` (`label` / `api_style` / `base_url` / `model` / `api_key_env`). Custom headers go in `ProviderConfig.extra_headers`. Two protocols are implemented: `openai` (`/chat/completions`) and `anthropic` (`/messages`).

> **API keys are read from environment variables only** — never written to disk, never committed. In HTTP mode, prompt content is sent to the endpoint you specify. For confidential material, use manual mode or a local model.

---

## Evidence ledger

The methodology demands that every key judgement be traceable. Before this existed, `evidence.schema.json` was a specification nobody read, and there was nowhere to put evidence.

```bash
python core/rebuild_cli.py evidence list       projects/my-project
python core/rebuild_cli.py evidence check      projects/my-project   # schema + semantic quality
python core/rebuild_cli.py evidence gaps       projects/my-project   # assumptions with no evidence
python core/rebuild_cli.py evidence provenance projects/my-project   # how much is machine-verifiable
python core/rebuild_cli.py evidence export     projects/my-project --out ledger.md
```

Stored as `<project>/evidence.jsonl` — one record per line: diffable, human-readable, no database.

**Records that violate the schema are rejected before being written.** A corrupt line raises an error rather than being skipped, because silently skipping would make evidence disappear.

Beyond the schema, it checks what a schema cannot:

| Situation | Why it is a problem |
|---|---|
| Labelled `FACT` with no source | Facts must be verifiable; otherwise downgrade to inference |
| Labelled `ASSUMPTION` with no recheck trigger | An unverified premise must state when it gets rechecked |
| Labelled `UNKNOWN` with `HIGH` confidence | Contradiction: insufficient information cannot be high confidence |
| `decision_impact` is empty or "n/a" | Evidence that changes no decision is not evidence |

These are **warnings, not errors** — they do not block writing, but they surface in `evidence check`.

**Machine-verifiable provenance.** A `source` of the form `DOC-001` points into the material library and can be checked automatically; free text cannot. A reference to a document that does not exist is a **dangling link**, and dangling links are errors, not warnings — a link that claims to be verifiable but is not is worse than plain text.

---

## Importing your data

```bash
# Local files: CSV / TSV / JSON / JSONL / TXT / MD / XLSX
python core/rebuild_cli.py source add-file projects/my-project ~/Downloads/orders.csv

# Your own HTTP endpoint
python core/rebuild_cli.py source add-url projects/my-project \
    --name my-orders --url https://api.example.com/orders \
    --header-env "Authorization=MY_API_TOKEN" \
    --records-path "data.items" --save-spec

python core/rebuild_cli.py source list   projects/my-project
python core/rebuild_cli.py source verify projects/my-project   # has the source been altered?
```

Two deliberate choices:

- **CJK encoding fallback.** It tries utf-8-sig → utf-8 → gb18030 → big5 → latin-1 in order. CSV files exported from Chinese tools are frequently GBK; reading them as UTF-8 produces mojibake, and **mojibake fed to a model is worse than no data** — the model writes confidently about garbage.
- **Secrets never enter the spec file.** The spec records *which header maps to which environment variable*; the value is read at runtime. A secret written to a file ends up in git eventually.

**XLSX is parsed with the standard library** (`zipfile` + `xml.etree`) — no pandas, no openpyxl. Every document is stored with a SHA-256 so `source verify` can detect tampering.

---

## Runtime orchestrator

```bash
python core/rebuild_cli.py run projects/my-project --dry-run       # packets only, no network
python core/rebuild_cli.py run projects/my-project --provider deepseek
```

The orchestrator dispatches roles phase by phase, injects evidence and material, asks the model to judge the gate, and has the **state machine** adjudicate the transition.

Three constraints that are not negotiable:

1. **Sequential, not pretending to be parallel.** One role, one model call, in order.
2. **The state machine adjudicates transitions, not the model.** The model answers "which event should fire"; whether that event is legal and where it leads is decided by `core/state_machine.json`. An illegal event is rejected and recorded.
3. **Evidence proposed by the model never enters the ledger.** Model output is not evidence. Suggestions are written to run artefacts for human review — auto-ingesting would degrade the ledger into "a list of things the model said."

**Per-phase gates.** Each phase is judged against its own criteria from `REBUILD_METHOD.md` — R asks whether the problem is framed, not whether evidence is sufficient. Gate verdicts are graded: `SUFFICIENT` / `DEGRADED` (must declare limitations) / `INSUFFICIENT`.

> The failure this system guards against is **not** "proceeding with incomplete evidence" — it is **"proceeding while pretending the evidence is complete."**

Artefacts land in `<project>/runs/<timestamp>/`: packet and output per role, raw gate verdicts, and a schema-validated decision record. `runs/` is gitignored.

---

## Cost

Measured against a real API:

| Scope | Model calls | Tokens | Time |
|---|---|---|---|
| Two phases | 6 | 28,671 | 56 s |
| **Full six-phase loop** | **16** | **91,723** | **~110 s** |

Cost requires unit prices you supply — **no prices are built in**, because prices change and a hardcoded price becomes a number that silently goes stale:

```bash
python core/rebuild_cli.py run projects/my-project --provider deepseek \
    --price-input 0.28 --price-output 0.42
```

- **Tokens are facts, cost is an estimate.** Token counts are read from the API's `usage` field. When usage is unavailable it is recorded as unavailable and the total is marked **incomplete** — never estimated.
- Every cost result carries a caveat: this is an estimate from *your* unit prices, **not a bill**.

`compare` aggregates cost across runs.

---

## Multi-run comparison

A single run is a starting point, not an answer. Measured on identical input at `temperature 0`, three runs all concluded "validate first" but differed by **2.5x** in the number of falsification conditions.

```bash
# Repeat the same input N times (state is reset between runs)
python core/rebuild_cli.py run projects/my-project --provider deepseek \
    --temperature 0 --repeat 3

# Deterministic comparison
python core/rebuild_cli.py compare projects/my-project --last 3

# Plus a model-judged verdict on whether the recommendations agree in direction
python core/rebuild_cli.py compare projects/my-project --last 3 --judge-with deepseek
```

Two axes, deliberately kept apart:

| Axis | Computed how | What it tells you |
|---|---|---|
| **Process reproducibility** | Deterministic, no model | whether paths, final states and gate grades matched |
| **Conclusion agreement** | Model-judged, flagged `judged_by_model` | whether the recommendations point the same way |

**"Same transition path" is not "same recommendation."** Conflating them is the easiest mistake this kind of tool can make. The comparison exits non-zero when process outcomes diverge, so it is usable in scripts.

---

## Decision records and review

Phase D requires comparing expectation against actual, separating execution failure from strategy failure, and recording what changes next. **This loop was previously empty** — `decision_records` in `project.json` was an array that never filled up, so the system could produce decisions but never learn whether they were right.

`decision due` surfaces **decisions past their review date that have not been reviewed**, rather than waiting to be remembered.

| Deviation type | Meaning |
|---|---|
| `AS_EXPECTED` | It went as predicted — no attribution needed |
| `EXECUTION` | Right direction, insufficient force |
| `STRATEGY` | The direction itself was wrong |
| `ASSUMPTION` | A key assumption was false |
| `MIXED` / `UNKNOWN` | Multiple causes / cannot attribute (choosing `UNKNOWN` requires a stated reason) |

Decisions sync back into `project.json` marked `PENDING_REVIEW` or `REVIEWED`.

> **Decision records produced by the model do not enter the store automatically.** The orchestrator writes them to run artefacts; a human runs `decision import`. Same principle as evidence: model output is not an established decision.

---

## Maturity statement

This is the most important section. Please read it.

**Implemented and tested**
- Methodology and phase gates (documented)
- Deterministic state machine: 7 states, legal and rollback transitions
- **JSON Schema validator** (standard library): type / required / properties / additionalProperties / items / enum / ranges / anyOf / oneOf / allOf. **Unimplemented keywords raise warnings rather than being silently ignored**
- **Evidence ledger**: JSONL append, schema validation before write, semantic quality checks, gap analysis, verifiable-provenance ratio, Markdown export
- **Data sources**: local files (CSV / TSV / JSON / JSONL / TXT / MD / XLSX with CJK encoding fallback) and user-supplied HTTP endpoints; SHA-256 provenance; secrets from environment only
- **Runtime orchestrator**: sequential per-phase role dispatch, evidence and material injection, per-phase gates with three-tier verdicts, state-machine-adjudicated transitions, schema-validated decision record. **Validated end-to-end against a real model**
- **Decision store and review**: persistence, proactive overdue-review surfacing, outcome back-fill with mandatory deviation typing, write-back to `project.json`
- **Multi-run comparison**: process reproducibility kept strictly separate from model-judged conclusion agreement
- **Token accounting**: per-call usage capture; cost computed only when you supply prices
- 6 JSON Schemas enforced: project, evidence, decision, decision outcome, experiment, KPI tree
- 8 differentiated specialist role contracts
- DeepSeek Harness skill and installation guide (`harness/`)
- Blind-review harness: hashed IDs, shuffled order, identity hiding, reviewer agreement checks
- Model provider layer (OpenAI-compatible and Anthropic-compatible)
- 297 unit tests, passing on Python 3.9–3.13
- GitHub Actions CI, including an end-to-end smoke test and reproduction of the worked case

**Not implemented**
- **Parallel multi-agent dispatch** — the orchestrator is strictly sequential
- **Built-in marketing platform connectors** — deliberately excluded
- **Decision history versioning and dependency rollback** — decisions are stored and reviewable, but a falsified assumption does not yet auto-list affected decisions
- **Execution of marketing actions** — the system produces decisions and validation plans; it does not advertise, message, or write to any external system

**Unverified**
- End-to-end quality in any host environment
- **The absolute quality of orchestrator output** — it runs end-to-end, and multi-run comparison tells you whether it is *stable*; **it cannot tell you whether it is *right***
- Whether the model-judged agreement verdict is itself reliable (it is a model output, subject to the same variance)
- Comparative quality against plain prompts or single-skill setups (the pilot is underpowered and **does not constitute comparative evidence**)
- Reviewer independence in the pilot (the two reviewers have no recorded provenance)
- A complete loop on a real commercial project (the real case correctly blocks at R; E–I–D were exercised on a constructed test project)
- Real-world ROI impact, and the commercial value hypotheses

> `agents/*.md` are **methodology contracts, not runtime agent instances.**
> Writing "sub-agent" in a prompt does not create a sub-agent at runtime.
> The distinction is deliberate: packaging prompts as delivered capability is the most common form of self-deception in this field.

---

## Worked case study

[`examples/metro_apartment/`](examples/metro_apartment/) is a **real commercial project, anonymised**, containing the three source documents, the full output (decision page, KPI tree, experiment cards, unit-economics model, power analysis), and six scripts that reproduce every number.

```bash
cd examples/metro_apartment/rebuild && python3 scripts/run_all.py
```

What it found: **this was not a marketing problem, it was a profit-split problem.** Under the proposed terms the operator burned cash every month at *any* occupancy between 60% and 93%, and the owner's payback constraint and the operator's break-even constraint had an **empty intersection**. The recommendation was not to sign the current terms.

**What happened next:** the owner accepted the recommendation, the split structure was changed, and the operator did not sign. The predicted blocker materialised.

**What that does and does not prove** — the case README states this in full: it proves the analysis **changed a real decision**; it does **not** prove the analysis was arithmetically right, nor that the **revised** structure works (it has not been modelled), nor that the project is viable (it has not opened, there is no operating data).

> **Being adopted is not the same as being validated.** Adoption shows a conclusion was persuasive; validation takes time.
> And the owner calling it "viable" is *exactly what the model predicted* — the model said the terms work **for the owner** and not for the operator. The owner was always the party for whom the arithmetic worked.

Anonymisation scope and residual risk are documented in [`ANONYMIZATION.md`](examples/metro_apartment/ANONYMIZATION.md), including an honest list of what could still be inferred.

---

## Real-model validation log

[`docs/VALIDATION_2026-10.md`](docs/VALIDATION_2026-10.md) records the first end-to-end runs against a live model, including the five defects those runs exposed that **the unit test suite did not catch**.

The most serious: every phase was judged against one shared gate criterion, so `DISCOVER` could never pass — **4 out of 4 runs stalled at the first phase**. After the fix, the same input completed `DISCOVER → REVIEW`.

A recurring pattern worth naming: **four separate schema defects, all found by real use, all the same failure mode** — writing "the normal case" as "the only case":

| # | Schema assumed | Reality |
|---|---|---|
| 1 | assumptions are plain strings | the model produced structured objects pairing each assumption with its falsification condition — more useful |
| 2 | only the current schema is in use | the real project ran on a wider earlier schema |
| 3 | a decision is always made | when evidence is insufficient, `chosen_option: null` is the honest answer |
| 4 | every review finds a deviation | "it went as expected" is a legitimate conclusion, not "cannot attribute" |

Unit tests check whether code conforms to the schema. The defects were in whether **the schema conforms to reality**.

---

## Originality boundary

The phase model, decision-record protocol, evidence grading, phase gates, role contracts, falsification mechanism, evaluation protocol and state machine in this repository are original designs.

This project does **not** claim nobody has ever proposed similar concepts. Originality should be established through **concrete implementation, independent documentation, version history and reproducible experiments** — not through a "world first" claim. If you find substantially similar work, please open an issue; that makes the project more credible, not less.

No third-party marketing projects are bundled. A host (such as DeepSeek Harness) is a runtime environment, not the source of the methodology, and an adapter may not redefine REBUILD policy.

---

## Evaluation

`bench/` provides four fixed benchmark cases and a 32-point eight-dimension rubric, where **a zero on honesty fails the sample outright** — total score cannot compensate.

The protocol requires three configurations (plain prompt / single skill / full system), at least three independent runs each, and two blind reviewers.

**The published scorecard is a single-case pilot, not a result.** One case out of four, one run per configuration, reviewers with no recorded provenance. It does not constitute comparative evidence. See [`bench/PILOT_B03.md`](bench/PILOT_B03.md).

---

## Repository layout

```text
core/            Methodology, state machine, schema validator, evidence ledger,
                 decision store, orchestrator, multi-run comparison, CLI
agents/          Master agent and 8 specialist role contracts
sources/         Data layer: local files and user-supplied HTTP endpoints
schemas/         Project, evidence, decision, outcome, experiment, KPI tree
bench/           Benchmark cases, rubric, blind-review harness, review protocol
examples/        nanjiang_tea (empty framework); metro_apartment (real, anonymised)
harness/         Host integration docs and an installable DeepSeek Harness skill
tests/           Unit tests and a static checklist
docs/            Status and roadmap; first real-model validation log
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Core requirements:
a new strategy rule must state **which decision it affects, where it applies and how it fails**;
a new case must be labelled real / synthetic / anonymised;
a test that has not been run may not be marked as passing.

Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). The licence covers only content the publisher has the right to license; the REBUILD name and any unauthorised third-party material are not automatically covered.
