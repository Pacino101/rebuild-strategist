# Changelog

## V3.11.0 — Full English documentation

The repository was Chinese-only: **111,894 CJK characters, zero English**. An
international visitor could not tell what it was. This release translates it.

### What is now English

| Area | Files |
|---|---|
| Entry point | `README.md` (Chinese preserved as `README.zh-CN.md`) |
| Methodology | `core/REBUILD_METHOD.md`, all 9 `agents/*.md` role contracts |
| Docs | `docs/*`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `LICENSE_DECISION.md` |
| Schemas | all 6 `schemas/*.json` descriptions |
| Benchmark | `bench/*.md`, `bench/cases/*.json`, `bench/prompts/*.txt` |
| Host integration | `harness/README.md`, `harness/deepseek/SKILL.md` |
| Case study | `examples/*/README.md`, `ANONYMIZATION.md`, project and decision files |
| Code | comments, docstrings and user-facing messages across `core/`, `sources/`, `bench/` |

### What is deliberately still Chinese

**66 characters outside the case study, every one justified:**

| Where | Why it stays Chinese |
|---|---|
| `examples/metro_apartment/source/` (19,929) | **The client's own documents.** Translating raw evidence would be *altering evidence* — the exact thing this project exists to prevent. |
| `examples/metro_apartment/rebuild/` (36,660) | Artefacts that quote and analyse those documents. |
| `README.zh-CN.md` (5,201) | The original Chinese README, kept byte-for-byte. |
| `bench/runs/` (4,058) | Recorded model outputs — data, not documentation. |
| `ANONYMIZATION.md` (28) | Live `grep` regex ranges, e.g. `[一-龥]{2,12}(有限公司|...)`. Translating them breaks the command. |
| Case README (22) | Real source file names that exist on disk. |
| `core/ledger.py` (3) | `{"无", "待定"}` — values a *user* may type. Translating them stops matching Chinese input. |
| `core/orchestrator.py` (2) | A table-header skip list that keeps older Chinese-language model output parseable. |
| Copyright notices (6) | Must match `LICENSE` verbatim. |

The English case README explains what the case found and what it does not prove,
so a non-Chinese reader gets the finding without the evidence being rewritten.

### Verification

Translation was performed by four agents working on disjoint file sets, then
verified independently. Structure was diffed against the previous revision:
identical line counts, heading levels, table rows, code fences and list markers.
Two agents reported that proving "zero CJK" required touching test assertions
that hard-coded Chinese substrings; **all such edits were declared**, and the
final suite is green.

**297 tests pass. CI green on Python 3.9–3.13.**

### One bug fixed along the way

The case README contained a **self-contradiction introduced when the follow-up
section was added**: one section recorded that the owner adopted the
recommendation, while a surviving bullet still said "this directory does not
record whether it was adopted". In a document whose entire purpose is honesty,
that had to go. It now states plainly that the outcome is
**self-reported by the commissioning side and has not been independently verified**.

## V3.10.0 — English documentation, installer, Python 3.9

Two fair criticisms of the previous state, both fixed.

### 1. The project was Chinese-only
The repository held **111,827 Chinese characters and zero English**. An
international visitor could not tell what it was. Now:

- **`README.md` is English** and is the primary entry point.
- **`README.zh-CN.md` preserves the Chinese version byte-for-byte** — nothing lost.
- Remaining Chinese docs are being translated incrementally; the README is the
  front door and mattered most.

### 2. There was no way to install it
No `pyproject.toml`, no `install.sh`, no launcher, **no release and no tag** —
so there was literally nothing to download.

- **`install.sh`** — one command: checks Python, downloads the latest release
  (no git required), runs the test suite to verify, installs the DeepSeek
  Harness skill if `~/.dsh` exists, prints next steps.
  ```bash
  curl -fsSL https://raw.githubusercontent.com/Pacino101/rebuild-strategist/main/install.sh | bash
  ```
- **`bin/rebuild`** — a launcher that resolves symlinks and runs the CLI from
  the checkout, so the repository layout stays intact.
- **GitHub Release with a tag** — real downloadable archives.

### 3. Deliberately *not* done: a pip package
The orchestrator reads `agents/`, `schemas/` and `examples/` relative to the
repository root. Installing the code into `site-packages` would separate it from
those files and break the tool. The README states this instead of advertising a
`pip install` that does not work.

### 4. Python 3.9 support (a real bug, not a version gate)
Two provider tests failed on 3.9, and the project simply declared "Python 3.10+".
The actual cause was a genuine defect: reading an error response body crashed
when the `HTTPError` carried no `fp`. Reading an error message should never take
down the call. Fixed — **all 297 tests now pass on 3.9**, the requirement is
lowered to 3.9+, and CI covers 3.9–3.13.

Hiding a bug behind a version requirement is the same failure mode this project
criticises elsewhere.

## V3.9.0 — The decision loop closes for real, for the first time

This is the **first time** the whole project has fed real-world outcomes back into the decision store. The D phase until now had only a mechanism,
no record of use.

### Real-world outcome

The real case analysis concluded "run a clause stress test first, renegotiate the revenue-share structure, then sign". The outcome was:

- Party A **adopted** the recommendation, did not sign under the current terms, and the revenue-share structure has been adjusted;
- **Party B did not sign**; the two sides are renegotiating;
- The blocking point the analysis predicted (Party B would not accept that revenue split) **materialised in reality**.

Recorded in `examples/metro_apartment/decisions/DR-001.json` and
`decisions/outcomes/DR-001.json`; the `decision_records` status in `project.json`
is `REVIEWED`.

### Fix: `deviation_type` was missing "as expected" (the fourth schema defect of the same kind)

Backfilling the real outcome got stuck: this review was **as expected**, but the enum
`EXECUTION / STRATEGY / ASSUMPTION / MIXED / UNKNOWN` **had no such value** —
it assumed that "every review finds a deviation".

So "everything went normally" could only be forced into `UNKNOWN`, and `UNKNOWN` means "unattributable".
**Describing "it happened as expected" as "unattributable" is itself a distortion.**

`AS_EXPECTED` has been added, and the schema description now states that it is a legitimate and important value.

### New: `decision outcome --assumption-update`
Update key assumptions during review (`CONFIRMED` / `REFUTED` / `STILL_UNKNOWN`).
This record updated three, and "Party B will accept 65:35" was **refuted**.

### The fourth instance of the same pattern

| Instance | Schema assumption | Real-world phenomenon |
|---|---|---|
| 1 | assumptions are plain strings | the model supplies a structured object, which is more useful |
| 2 | only the current schema is used | a real project runs on an earlier schema with broader fields |
| 3 | a decision will always be made | when evidence is insufficient, `chosen_option` being null is the honest answer |
| 4 | **a review will always find a deviation** | **when the outcome is as expected there is nowhere to put it, so it is mislabelled "unattributable"** |

All four were found through real use. This can no longer be called an "occasional defect"; it is **a stable failure mode**:
writing "the normal case" into the schema as "the only case".

### On "adopted"

The case README states plainly that "adopted ≠ verified":

- the analysis **changed a real decision** (✅ confirmable);
- the blocking point the analysis predicted **materialised** (✅ confirmable);
- whether the analysis **got it right** (❌ unconfirmed — Party B not signing could have other causes);
- whether the new revenue-share structure **holds** (❌ unconfirmed — **not yet modelled**);
- whether the project is **actually viable** (❌ unconfirmed — not yet open, no operating data).

> Party A saying "viable" is exactly what the model predicted — the model said "this clause works for Party A,
> but not for Party B", and Party A was always the side the numbers work out for.

### Changes
- Unit tests 294 → 297.

## V3.8.0 — Cost accounting

The last item on the previous version's to-do list: how much a run actually costs had never been measured. Now it has been.

### Measured numbers (real API)

| Scale | Calls | tokens | Duration | Estimated cost |
|---|---|---|---|---|
| Two phases (DISCOVER + EVIDENCE) | 6 | 28,671 | 56 s | $0.0095 |
| **Complete six-phase loop** | **16** | **91,723** | **~110 s** | **$0.0298** |

That is: one complete R→E→B→U→I→D run takes about **16 model calls, 90,000 tokens, 3 cents and two minutes**.

### Two design constraints

**① tokens are fact, cost is estimate, and the two are kept separate.**
The token count is read directly from the `usage` field of the API response. If it cannot be read, `available: false` is recorded,
and the total is noted to be **incomplete** — **never estimated**. A token count that was estimated and treated as actual usage
and written into a report is worse than no number at all. Cost is computed only when the user supplies unit prices.

**② This project hard-codes no prices.**
Unit prices are supplied by the user via `--price-input` / `--price-output`.
Prices change; hard-coding a price in the code manufactures a conclusion that will silently drift.
Cost results always carry a caveat: this is an estimate computed from the unit prices you supplied, **not a billed amount**,
and it excludes cache discounts and duplicate charges from retries.

### Added
- `bench/provider.py`: `complete_with_usage()` returns `(text, usage)`;
  `_extract_usage()` supports both the OpenAI (`prompt_tokens`) and Anthropic
  (`input_tokens`) shapes, and reports `available: false` when it cannot recognise one.
- `core/orchestrator.py`: records usage and duration per call, and the report gives
  `usage` (with a per-phase summary) and `cost_estimate`.
- CLI: `run` gains `--price-input` / `--price-output` / `--currency`;
  `compare` gains a cost summary section, totalling across runs.
- 17 new tests (including a dedicated assertion that "no estimation is allowed when usage is unavailable").

Unit tests 277 → 294.

## V3.7.0 — Comparing multiple runs

Turning "run it a few more times to see whether it is stable" from a manual action into a tool. The previous version measured that "the output of a single run is not the
answer, only a starting point", but no tool backed that statement up — this version adds one.

### New `core/compare.py` + CLI `compare` subcommand
- `run --repeat N`: repeat the same input N times, resetting project state each time and giving each run its own artefact directory.
- `compare <project> [--last N]`: deterministic comparison, outputting transition paths, final-state distribution,
  per-phase gate tiers, and the range of decision-item counts.
- `--judge-with <provider>`: use a model to judge whether the N recommendations are consistent **in direction**.

### Two kinds of conclusion are deliberately kept apart
This is the most important design constraint of this module:

| Axis | How it is computed | What it can show |
|---|---|---|
| **Process reproducibility** | deterministic computation, no model needed | whether path / final state / tier are consistent |
| **Conclusion consistency** | model judgement, labelled `judged_by_model` | whether the recommendation direction is consistent |

**"The same transition path" does not mean "the same recommendation".** Claiming the former is the latter is the easiest mistake this kind of tool can make,
so the return value carries an explicit caveat, and the model-judgement result carries its own caveat too.
When the process is inconsistent it returns a non-zero exit code, which makes scripting easier.

### Fix: `chosen_option` may be null (the third schema defect)

`compare` exposed it the moment it ran: in **2 of 3** runs `chosen_option` was `null`,
which the schema judged invalid (`type should be string, got null`).

But **null is the honest answer** — when the gate judges the evidence insufficient and this round should gather further evidence before deciding, there simply is no
"adopted option". The earlier schema assumed "a decision will always be made",
so the more honest the model was, the more "invalid" its output became.

Fix:
- the schema allows `chosen_option` to be `string` or `null`;
- the decision packet tells the model explicitly that "writing null is correct; do not invent an option just to fill the field";
- new quality hint: null with no `validation_actions` → "equivalent to no conclusion";
- `compare` output distinguishes "no decision record produced" from "no choice made this round" —
  conflating the two makes "no conclusion was produced" read as "the conclusion is not to decide".

### A pattern that has now repeated three times

All three schema-related defects were found by **real runs**, and all were the same class of problem —
**the schema wrote "the normal case" as the only case**:

| Instance | Schema assumption | Real-world phenomenon |
|---|---|---|
| 1 | assumptions are plain strings | the model supplies a structured "assumption + falsification condition" object, which is more useful |
| 2 | this project uses only the current schema | a real project runs on an earlier schema with broader fields |
| 3 | a decision will always be made | when evidence is insufficient, `chosen_option` being null is the honest answer |

Not one unit test caught them — they test "whether the code conforms to the schema",
while the problem was "whether the schema conforms to reality".

### Changes
- Unit tests 251 → 277.

## V3.6.1 — Failure paths and run-to-run consistency

Picking up the two to-do items from V3.6.0. See sections 6 and 7 of [`docs/VALIDATION_2026-10.md`](docs/VALIDATION_2026-10.md) for the full record.

### Failure paths

**Real API probes** (each triggered in turn against the real endpoint): invalid key → `401`, no retry;
non-existent model → `400` with the available model names echoed back; unreachable host → 3 backoff retries, then an error;
wrong path → `404` with a hint to check base_url. **All four were judged correctly.**

**Two fixes:**
- **When all role calls failed, the gate was still called once** — `role_outputs` held a list of empty strings,
  the dictionary itself was still truthy, so it wastefully called the model once with empty input. It now checks the content first.
- **When the provider name was misspelled, every role failed once**, recorded as 6 "role failures" —
  the user would go and check the network, when the real cause was a typo. It now errors before writing any artefact and lists the available names.

7 new failure-path tests: single role failure, all roles failing, gate throwing, gate returning truncated JSON,
decision-record failure, decision-record truncation, and fast failure on an unknown provider.

### Run-to-run consistency

The same input run 3 times each (temperature 0 and 0.3):

- **Flow completed: 6 / 6.** Compare the **0 / 4** before the gate defect was fixed.
- **Decision direction consistent**: all three concluded "validate first, don't rush to launch".
- **Details not reproducible**: falsification conditions 6 / 10 / 15 (a 2.5× spread), options 3 / 3 / 4;
  one run gave a complete pilot design (4 weeks, 30 people) while another said only "gather further evidence first".
- **temperature=0 does not eliminate the differences** — most APIs do not guarantee determinism at 0 either.

One usage constraint written into the docs as a result: **the output of a single run must not be treated as "the answer", only as a starting point.**
The system currently has **no** built-in multi-run comparison — this is a capability gap, and the docs honestly label it as not implemented.

### Changes
- CLI `run` gains `--temperature` (default 0.3).
- Unit tests 244 → 251.

## V3.6.0 — First real-model validation

The orchestrator had **never been connected to a real model** before: all 27 tests injected a fake model, and coverage of the real provider branch was zero.
This time it was run through against DeepSeek `deepseek-chat`, and three defects were found and fixed. See
[`docs/VALIDATION_2026-10.md`](docs/VALIDATION_2026-10.md) for the full record.

### Fix 1: All phases shared the same gate criteria (severe)
- **Symptom**: 4 consecutive runs all got stuck at DISCOVER; not one advanced to the second phase.
- **Cause**: the same gate checklist was applied to all six phases, and its first item was "insufficient evidence → must not proceed to a strategy decision".
  But the R phase **happens before evidence gathering by design**, and the gate `REBUILD_METHOD.md` gives it is
  "write goals and symptoms separately; anything lacking a baseline must be marked unknown" — that is problem-framing quality, not evidence sufficiency.
- **Fix**: added `PHASE_GATES`, so each phase uses its own criteria, with the explicit rule "judge only by this phase's criteria".
- **Effect**: with the same project and same model, 4/4 blocked before the fix and a complete `DISCOVER → REVIEW` run succeeded after it.

### Fix 2: The gate offered only two choices, "pass / block" (severe)
- **Cause**: the gate packet said "passing a phase with insufficient evidence is the most severe failure of this system",
  which made blocking the only safe option; yet the methodology explicitly allows **degraded output**, and the gate packet never offered that option.
- **Fix**: introduced three tiers `SUFFICIENT` / `DEGRADED` (with `limitations` listed item by item) / `INSUFFICIENT`,
  and redefined failure:
  > The most severe failure is **not** advancing with incomplete evidence, but **pretending the evidence is complete while advancing**.
- **Effect**: the model began using `evidence_grade` and could give precise reasons for its tier choice.

### Fix 3: The schema rejected a reasonable model output as invalid
- **Symptom**: the decision record reported 7 errors, with a `key_assumptions` type mismatch.
- **Cause**: the model spontaneously paired each assumption with its **falsification condition**, which is more useful than the plain strings the schema allowed
  — and the methodology requires exactly that "every key assumption be paired with a condition that can refute it".
- **Fix**: `key_assumptions` uses `oneOf` to accept both strings (backwards compatible) and structured objects.
- **Corroboration**: this matches the finding from the real project case — running on an earlier schema already exposed
  that "a real project needs more fields than the schema provides". This time it was reproduced live.

### Incidental fix
- The skip hint in the `BLOCKED` state used to print "available sequences: **[]**" — no help at all, in precisely the state that most needs guidance.

### Validation coverage
- All three state-machine paths were run through on a real model: **full advance**, **rollback** (`evidence_gap`),
  and **block**. All three were legal transitions; no illegal event was accepted.
- 13 new regression tests pin down the three defects above (per-phase gates, the degraded channel, and the dual-format schema).
- Unit tests 232 → 244.

### Still unverified (recorded honestly)
- **A full loop on a real project has still not been completed**: the real case was correctly blocked at the R phase,
  and E/B/U/I/D were run through on a **constructed test project**, not a real business project.
- Failure paths (429 / timeouts / truncated responses) were not tested.
- The same input produced different results on two runs (one advanced, one rolled back) — **a single run is not enough to evaluate output quality**.
- Running through ≠ analysing well: the absolute level of output quality requires independent review, which does not currently exist.

## V3.5.0 — Real project case (anonymised)

The README's maturity statement long carried "**unverified: whether a complete
R→E→B→U→I→D can be run end to end on real client data**". This version strikes that line out.

### New: `examples/metro_apartment/` — a complete run on a real project
- Three anonymised real input materials (partnership-model study, site-specific study, full brand marketing plan).
- Complete outputs: decision page, KPI tree, experiment cards, unit-economics model, power calculation, skill assessment report.
- 6 analysis scripts reproduce every number in one command (`python3 scripts/run_all.py`, standard library only).

**The conclusion this case produced**: a fairly complete marketing plan did not hold up on unit economics —
the operator burns deposit money every month it operates, whether the occupancy rate is 60% or 93%; the revenue-share constraints for
Party A's 48-month payback and Party B's break-even have an **empty intersection**. **This is not a marketing problem, it is a revenue-share structure problem.**

### New: anonymisation guard (`tests/test_example_anonymization.py`)
- Once anonymisation is broken by a later change, the leak is **irreversible** — pushing to a public repository leaves a permanent trace in the history.
  So "is the anonymisation complete" became an error CI can catch.
- It checks generic patterns: full company/institution names, specific street addresses, subway station names, policy document numbers, local absolute paths.
- **The test file deliberately contains no list of the original terms** — writing out a mapping table of "Company X → Party A" would amount to undoing the anonymisation all over again.
- False-positive regression has been done: ordinary phrasing such as `the same group` / `this group` / `this contract` is not misflagged.

### New: `ANONYMIZATION.md`
- Explains which **categories** were anonymised (without the mapping table), what was deliberately kept, and how to self-check.
- **Honestly lists the residual risks**: the combination of data may itself be fingerprinting; the timeline was not shifted;
  the policy environment can narrow down the city; competitor structural features are unchanged. The conclusion is —
  this case is suitable for methodology demonstration and teaching, and **not suitable as fully untraceable public material**.

### Changes
- CI gains a case-reproduction step: if the scripts do not run, the case degrades into a static document.
- Unit tests 223 → 232.

### Known deviations (listed in the case README)
- The case ran on an earlier schema (archived at `legacy/v3.1`) whose fields are **broader** than the current `schemas/`.
  The runtime snapshot is provided with the case. **This deviation is itself a finding: a real project needs more fields than the current schema provides.**
- Party B's costs in the unit-economics model are **reconstructed**, not original data.
- The customer-segment proportions are not validated by survey; all three experiments are `proposed`, none executed.

## V3.4.0 — Decision review loop, verifiable sources, and Skill update

What this version closes is **the last broken segment of the loop**: the D (Decision Review) phase had not been implemented at all —
`decision_records` in `project.json` was an array that stayed empty forever, decisions scattered once they were made,
and the system could produce decisions yet never learn whether its own decisions were right.

### New: decision records and review (`core/decisions.py` + `schemas/outcome.schema.json`)
- Decisions are stored, managed by review date, and backfilled with outcomes, synchronised back to `decision_records`
  in `project.json` (labelled `PENDING_REVIEW` / `REVIEWED`).
- **`decision due` puts decisions that "should have been reviewed but were not" right in front of you**, instead of waiting for the user to remember.
- **Mandatory distinction of deviation types**: `EXECUTION` (execution failure) / `STRATEGY` (strategy failure) /
  `ASSUMPTION` (assumption failure) / `MIXED` / `UNKNOWN`. Choosing `UNKNOWN` requires explaining why the outcome cannot be attributed.
- When backfilling outcomes, an `actual` field that is too short is rejected: a review must state the outcome actually observed,
  and when there is no data it must say "no data collected"; impressions must not be used as a substitute.
- Quality hints: no review date, no falsification condition, no cost, no key assumptions, a single option,
  the chosen option not in the candidate list, duplicate option names, an expired deadline.
- **Decision records produced by the model are not stored automatically**: the orchestrator only writes run artefacts; storing
  requires a human to run `decision import` — the same principle as for evidence.

### New: verifiable evidence sources (`ledger.provenance_report` + `evidence provenance`)
- When `source` is written in the `DOC-001` form it is treated as pointing to the material library and **can be machine-verified**;
  free text cannot. The system distinguishes the two cases explicitly and reports the verifiable ratio.
- **A dangling link is an error, not a warning**: pointing at a non-existent material is worse than free text —
  it claims to be verifiable but cannot actually be verified.
- `evidence add --source-doc DOC-001` confirms the material exists before writing.

### Updated: host integration (`harness/`)
- `harness/deepseek/SKILL.md` rewritten: it previously mentioned none of the capabilities introduced in V3.3
  (orchestrator / evidence ledger / data sources / decision store); all are now included, along with boundary statements.
- New `harness/README.md`: installation steps, DSH skill discovery rules, uninstall instructions, and capability boundaries.
- New `tests/test_harness_skill.py`: turns "invalid frontmatter makes the skill silently discarded"
  into an error CI can catch.

### Changes
- `schemas/` goes from 5 to 6 files (adding `outcome.schema.json`).
- Unit tests go from 174 to 211.

## V3.3.0 — Runtime, evidence ledger and data sources

This version closes three gaps where "the docs describe it but the code does not have it": the Schema was only a specification file,
the evidence ledger had nowhere to live, and the role contracts had no orchestrator. **Note: these are capability additions, not proof of quality** —
the orchestrator's output quality has not yet been validated on any real model.

### New: JSON Schema validator (`core/schema_validator.py`)
- Implemented with the standard library only, covering the keywords this repository's schemas actually use, plus `anyOf` / `oneOf` / `allOf`.
- **Unimplemented keywords raise a warning rather than being silently ignored.** Silent ignoring would make "validation passed" an illusion.
- `rebuild_cli.py validate` runs schema validation by default; a new `schema` subcommand validates arbitrary JSON.

### New: evidence ledger (`core/ledger.py`)
- Turns `evidence.schema.json` from a specification file into usable storage: `<project>/evidence.jsonl`, append-only, diffable, with no database dependency.
- **Mandatory validation before writing**: non-conforming records are rejected outright, never "written first and sorted out later".
- A corrupt ledger raises an error instead of skipping the bad line — silent skipping would make evidence quietly disappear.
- Semantic checks beyond the schema (presented as warnings): `FACT` with no source, `ASSUMPTION` with no re-check condition,
  `UNKNOWN` given high confidence, `decision_impact` written as "none".
- New `evidence add / list / check / gaps / export` subcommands; `gaps` finds assumptions and unknowns declared in the project but not covered by the ledger.

### New: data source layer (`sources/`)
- Local files: CSV / TSV / JSON / JSONL / TXT / MD / XLSX.
- **Chinese-encoding fallbacks**: utf-8-sig → utf-8 → gb18030 → big5 → latin-1. Feeding mojibake to the model is worse than having no data.
- **XLSX is parsed with the standard library** (zipfile + xml.etree), without pulling in pandas / openpyxl.
- Self-hosted HTTP endpoints: the URL, method and value path are supplied by the user; **no platform connectors are built in**.
- Secrets are read only from environment variables and are not stored in spec files; anything resembling a secret triggers a warning.
- Each material stores a SHA-256, and `source verify` can check whether a source has been altered.

### New: runtime orchestrator (`core/orchestrator.py`)
- Dispatches role contracts in phase order, injects evidence and materials, collects outputs, decides the gate, advances state, and produces decision records.
- **Sequential execution, no pretending to be parallel**: one model call per role, and roles do not communicate with each other.
- **State transitions are adjudicated by the state machine**: the model only answers "which event should be triggered"; legality is decided by `state_machine.json`,
  and an illegal event from the model is rejected and recorded in the report.
- **Evidence proposed by the model is not entered into the ledger automatically**: it is written to run artefacts for human review. Automatic entry would degrade the evidence ledger into "a list of things the model said".
- Default `--provider manual`: it only generates task packets, with zero network requests; `--dry-run` likewise means zero network and zero state changes.

### Changes
- `rebuild_cli.validate_project()` now returns an `(errors, warnings)` tuple instead of an `errors` list,
  in order to expose "constraints in the schema that were not checked". This is a **breaking change**, and callers must be updated accordingly.
- `tests/test_rebuild.py` writes its temporary files to the system temp directory and no longer pollutes the repository workspace.
- `.gitignore` gains `runs/`, `sources/documents/`, `sources/index.jsonl`, `sources/specs/`, `evidence.jsonl`:
  these directories contain client data and model output by default.
- CI gains an end-to-end smoke test (import materials → write evidence → dry-run the orchestrator) and asserts that the example directories are not polluted by artefacts.

### Tests
- Unit tests go from 28 to 174.
- All orchestrator tests inject a fake model and **make no network requests whatsoever**.

## V3.2.4 — Boundary statements and model interface documentation

### Corrections
- **A factual error in SECURITY.md**: the original text said "runs as a purely local tool and makes no network requests". That statement has not held since `bench/provider.py` was introduced in V3.2.2. It now states honestly: no behavioural data is collected and there is no telemetry, but enabling `--provider` sends requests to the model endpoint the user specifies and transmits the prompt content; the default manual mode makes no network requests.

### Documentation
- README gains "**What this project is not**": it is not an ad-serving / CRM / analytics tool, not an automated execution system, not a multi-agent runtime, not a data ingestion layer, and it does not guarantee that its conclusions are correct.
- README states explicitly that the commercial-value assumptions (consulting delivery / corporate training / evaluation layer) are **all unverified**, and the repository does not endorse them.
- README gains "**Connect your own model**", documenting the provider layer's preset list, how to use a custom OpenAI-compatible endpoint, how to plug in the blind-review flow, and how to extend it.
- The maturity statement honestly flags two previously undisclosed gaps:
  - **no code reads the 5 JSON schemas**; the CLI only performs handwritten field checks on `project.json`;
  - **the evidence ledger had only a Schema, with no path for entry or retrieval** — and it is the core artefact of the methodology.
- Quick-verification section corrected: the clone URL changed from a placeholder to the real repository address, and the test count was corrected from "5" to 28.

## V3.2.3 — Pilot results and scorecard validation

### Corrections
- **Fixed a column misalignment in `reveal()` in `bench_runner.py`**: `config_key` used to be written into the `case_id` column, so the published scorecard lost the real case IDs (B01–B04). `case_id` now comes from the manifest, and the revealed configuration name is stored separately in the `config` column.
- `summarise()` now reads the `config` column and remains compatible with the older `config_blinded` format.

### Evaluation
- Published one pilot (case B03, n=1 per configuration). **The sample size is far below the `RUBRIC.md` standard and does not constitute quality-comparison evidence.**
- New `bench/PILOT_B03.md`, declaring the limitations item by item: insufficient sample size, unverified reviewer independence, a single case, and anomalous full marks.

### CI
- Removed the assertion that "the scorecard must be empty". That assertion could only prevent "filling in numbers before running the experiment"; once real data exists it is bound to false-positive, and it cannot identify a mis-filled row.
- Replaced with running `bench_runner.py check-scorecard`: it validates the header, value ranges, total-versus-component-sum consistency, and required fields.

### Documentation
- The README's statement that "the current scorecard is empty" was changed to match the repository's actual data, with the pilot's limitations explicitly flagged.
- The README maturity statement was synchronised: the model Provider integration layer is listed as implemented, and multi-agent runtime scheduling remains not implemented.

## V3.2.2 — Provider integration layer
- New `bench/provider.py`: OpenAI-compatible and Anthropic-compatible calling conventions.
- `bench_runner.py` gains `render` and `execute` subcommands.

## V3.2.1 — Blind-review controlled-experiment scaffold
- New `bench/bench_runner.py`: ID hashing, shuffled presentation order, identity concealment, reviewer-consistency checks, and refusal when there are fewer than two reviewers or coverage is incomplete.
- New `bench/HOWTO.md`, `bench/REVIEW_PROTOCOL.md`, `bench/prompts/`.
- New `tests/test_bench_runner.py`.
- `.gitignore` gains `bench/runs/` (containing the salt and unpublished model output).

## V3.2.0 — Original Decision-Centric OS

### Methodology
- Removed the third-party marketing tool integration directory and the tool registry.
- Shifted the system's focus to an original decision protocol, evidence traceability, explicit trade-offs, unit economics, and a falsification loop.
- A six-phase decision loop (R-E-B-U-I-D) with phase gates and rollback paths.
- The Nanjian tea factory example was changed into a framework awaiting verification, with no pre-set project results.

### Engineering
- Added a deterministic state machine and a local CLI.
- Added JSON Schema, benchmark cases, a blind-review protocol and a maturity statement.
- Added GitHub Actions CI (Python 3.10–3.13).

### Role contract differentiation
- Rewrote the 8 specialist role contracts. Previously all roles shared one generic template (identical apart from the title), leaving role boundaries vague.
- Each role now has its own mission, input boundary and out-of-scope rejection rules, role-specific delivery fields, its own question checklist, and its own failure modes.
- The master agent gains a per-phase role dispatch table, degradation rules, and conflict- and out-of-scope-handling rules.

### Repository infrastructure
- Corrected `docs/STATUS_AND_ROADMAP.md`: it said GitHub CI was "not configured", but `.github/workflows/tests.yml` already existed.
- Cleaned up leftover `__pycache__` and `.pyc` files.
- New `SECURITY.md`, `CODE_OF_CONDUCT.md`, PR and issue templates.
- The LICENSE copyright line changed from the placeholder `REBUILD Project Contributors` to the actual author.
- README rewritten around the "decision-centric methodology OS" positioning, clearly distinguishing implemented / not implemented / unverified.

### Evaluation scaffold (V3.2.1 landed early)
- New `bench/bench_runner.py`: a five-step flow generate → template → import → reveal → summarise, standard library only.
- Three comparison arms: A plain-prompt baseline, B structured framework, C full REBUILD flow.
- Blind-review safeguards: SHA-256 ID hashing, shuffled presentation order, concealed configuration identity, same-salt reproducibility.
- Mandatory checks: refusal to reveal with fewer than 2 independent reviewers; refusal to reveal if any reviewer has not covered every item; a re-check prompt when two reviewers differ by > 6 points.
- New `bench/REVIEW_PROTOCOL.md` (scoring anchors and common misjudgements), `bench/HOWTO.md` (operations manual).
- New `bench/prompts/A_plain.txt`, `bench/prompts/B_skill.txt`.
- New `tests/test_bench_runner.py`, with 9 tests covering the safeguards above; total test count 5 → 14.
- Fixed 3 unclosed file handles in `bench_runner.py` (found by a `-W error::ResourceWarning` check).
- CI gains a ResourceWarning strict mode, a bench CLI smoke test, and an empty-scorecard guard.
- `.gitignore` excludes `bench/runs/` (containing unpublished answers and the salt).
