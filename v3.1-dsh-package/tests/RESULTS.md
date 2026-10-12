# Smoke-test results

The honest record. A row with no run is `UNVERIFIED` — that is a legitimate state to publish and an
illegitimate state to describe as passing.

## Log

| Date | Harness | Model | Tests run | Result |
|---|---|---|---|---|
| 2026-10-12 | — | — | none | **UNVERIFIED** |

## Per-test status

| Test | What it checks | Status | Evidence |
|---|---|---|---|
| T01 | Intake produces a contract without a questionnaire | UNVERIFIED | — |
| T02 | Refuses to invent a market size | UNVERIFIED | — |
| T03 | Diagnoses instead of guessing a cause | UNVERIFIED | — |
| T04 | ROAS is not treated as profit | UNVERIFIED | — |
| T05 | Commits to a choice with alternatives | UNVERIFIED | — |
| T06 | Drafts, never sends | UNVERIFIED | — |
| T07 | Does not claim an unconnected tool | UNVERIFIED | — |
| T08 | Rolls back when evidence contradicts | UNVERIFIED | — |
| T09 | Invents no project memory | UNVERIFIED | — |
| T10 | Narrows a delegated task | UNVERIFIED | — |
| T11 | Arithmetic reconciles; CAC basis is contribution | UNVERIFIED | — |
| T12 | Audit finds the unsupported claim | UNVERIFIED | — |

## Real-project runs — 2026-10-12

Three independent runs were performed against a live engagement (a 75-unit conversion: owner-funded
fit-out, operator performance bond, monthly revenue share). Each run loaded this skill and was given
the client's documents only. Full write-up with arithmetic:
[`examples/case-study-bonded-apartment.md`](../examples/case-study-bonded-apartment.md).

| Run | Mode | Outcome |
|---|---|---|
| 1 | `AUDIT` | Gate E and B `BLOCKED`; found 9 non-reproducible figures across the document set, including a headline payback claim requiring >100% occupancy to hold and a five-way disagreement on the same figure |
| 2 | `RED_TEAM` | Operator cash-negative in every achievable occupancy band; bond exhausted months 12–16 against a month-6 success target; break-even occupancy 98.7% including marketing |
| 3 | `GROWTH_DIAGNOSIS` | Full unit-economics rebuild; per-party cash-flow model; power analysis showing the proposed channel test needed 5.5× the available traffic |

**These runs found three defects in this skill**, all since fixed and now covered by tests: schemas
that accepted 18 of 18 semantically empty documents; no worksheet for arithmetic or cross-document
reconciliation; and a rule conflict that made cold-start auditing ambiguous. See `CHANGELOG.md` 3.2.2.

This is evidence that the method produces findings on real material. It is **not** evidence that the
findings were correct in every particular — the reviewers' own stated limitations are recorded in the
case study.

## What *is* verified

Separate from behaviour, these were observed directly and are not claims:

| Claim | How it was established |
|---|---|
| The skill is discoverable from the filesystem | Written to `.dsh/skills/rebuild-strategist/`; it appeared in the session's `<available_skills>` catalog at the next model step, with no restart. |
| The body loads with a usable resource base | The `skill` tool returned the instruction body plus `Base directory for this skill: <path>`, and relative `resources/...` paths resolved from there. |
| Frontmatter is accepted by the loader | `name` is kebab-case, `description` is non-empty, and no camel-case invocation keys are present — the three ways a skill is silently dropped. |
| The entrypoint fits the pruner budget | Rendered body is ~8.06 KB against the 8,192-character threshold, asserted by `tests/verify_package.sh`. |
| The package is internally consistent | `tests/verify_package.sh` passes: frontmatter, resource resolution, schema validity and wiring, output-envelope agreement, tool-status honesty, contract specificity. |
| The state schema validates a real state document, and rejects garbage | Asserted by the verifier, which constructs a full state document and three malformed ones. |

## How to add a run

1. Load the skill in a fresh session.
2. Send each prompt verbatim.
3. Score against the pass conditions in `SMOKE_TESTS.md` — binary, all conditions required.
4. Record the date, Harness version, model, and the literal outcome, including failures.
5. If a test fails, open an issue with the input and the actual output. A reproducible wrong answer
   is the most valuable contribution this project accepts.
