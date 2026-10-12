# First real-model validation log (2026-10-13)

This file records the **first** time the orchestrator was run against a real language model, and the problems it exposed.

Before this, all 27 orchestrator tests injected a fake model — **test coverage of the real provider branch was zero**.
"Runtime" was a claim, not a fact. This run turned it into a fact, at the cost of finding three defects.

---

## 1. Run setup

| Item | Content |
|---|---|
| Model | DeepSeek `deepseek-chat`, temperature 0.3 |
| Project | `examples/metro_apartment` (anonymised version of a real project) + a test project with complete evidence |
| Evidence | 5 real evidence items (sources point to material library `DOC-001/002/003`) |
| Calls | Per phase: role calls + 1 gate decision; 1 decision-record generation at the end |

---

## 2. Three defects found and fixed

### Defect 1: All phases shared the same gate criteria (severe)

**Symptom**: **4** consecutive runs all got stuck at `DISCOVER`; not one advanced to the second phase.

**Cause**: `build_gate_packet()` applied the same gate checklist to all six phases, and its first item was
"insufficient evidence → must not proceed to a strategy decision". But `DISCOVER` (R, framing reality) **happens before evidence gathering by design** —
the gate `REBUILD_METHOD.md` gives the R phase is "write business goals and symptoms separately; anything lacking a baseline must be marked unknown",
which is **problem-framing quality**, not evidence sufficiency.

Applying a later phase's criteria to an earlier phase meant the flow could never advance.

**Fix**: added `PHASE_GATES`, so each phase uses its own criteria (taken directly from `REBUILD_METHOD.md`),
and the gate packet now states explicitly: "judge only by this phase's criteria".

**Effect of the fix**: with the same project and the same model, 4/4 runs were blocked before the fix and a complete `DISCOVER → REVIEW` run succeeded after it.

### Defect 2: The gate offered only two choices, "pass / block" (severe)

**Symptom**: Even after the gate criteria were fixed, the model still leaned towards blocking.

**Cause**: the gate packet was worded like this —

> If the evidence does not support this phase's conclusion, choose the event that indicates rollback or the need for clarification, rather than forcing a pass.
> **Passing a phase with insufficient evidence is the most severe failure of this system.**

This wording made "block" the only safe option. But the methodology itself explicitly allows **degraded output**
("when evidence is insufficient, staying put, gathering further evidence, or degraded output is allowed"), and the gate packet never offered that option.

**Fix**: introduced a three-tier decision — `SUFFICIENT` / `DEGRADED` (degraded pass, with `limitations` listed item by item) /
`INSUFFICIENT`; and redefined failure:

> The most severe failure of this system is **not** "advancing with incomplete evidence" but **"pretending the evidence is complete while advancing"**.

**Effect of the fix**: the model began using the `evidence_grade` field and could give **precise reasons for its tier choice**.
In the real case, for example, it chose `INSUFFICIENT` and explained: "there are two veto-level blockers …
the direction of the conclusion would flip because of the missing information … only the decision-maker can supply that information" — matching the criteria exactly.

### Defect 3: The schema rejected a reasonable model output as invalid (moderate)

**Symptom**: decision-record validation reported 7 errors: `$.key_assumptions[n]: type should be string, got object`.

**Cause**: the model spontaneously paired each key assumption with its falsification condition:

```json
{"assumption": "measured conversion rate ≥15%",
 "falsification_condition": "if measured <5%, the assumption is refuted"}
```

But the schema allowed only `array of string`. **The model's output was more useful than the schema** —
the methodology requires that "every key assumption be paired with a condition that can refute it", and that is exactly what the model did.

**Fix**: relaxed `key_assumptions` in `decision_record.schema.json`
to accept both plain strings (backwards compatible) and structured objects via `oneOf`.

> This matches the finding from the real project case exactly: the case ran on an earlier schema,
> and even then it exposed that "a real project needs more fields than the schema provides". This time it was **reproduced live**.

### Incidental fix

The skip hint in the `BLOCKED` state used to print "available sequences: **[]**" — no help to the user at all,
in precisely the state that most needs guidance. It now explains how to clear the block.

---

## 3. All three state-machine paths have now been run through on a real model

| Path | Observed result |
|---|---|
| **Full advance** | `DISCOVER → EVIDENCE → STRATEGY → ECONOMICS → EXECUTION → REVIEW`; all six phase gates were judged `DEGRADED` (evidence incomplete but a conditional conclusion is possible) |
| **Rollback** | `DISCOVER → EVIDENCE → DISCOVER` (the gate judged `DEGRADED` but chose `evidence_gap` to roll back and gather further evidence) |
| **Block** | Real case: `DISCOVER → BLOCKED` (two P0 veto items unchecked; the model judged that it must not proceed) |

All three paths were legal transitions adjudicated by the state machine, and **not a single illegal event was accepted**.

---

## 4. Two things worth recording from the real-case run

**① The model refused an assumption disguised as a conclusion.** In a scenario test, the injected evidence was labelled
`ASSUMPTION`, and the model wrote explicitly that "ledger E-006 is only a scenario assumption, not verified", refusing to advance
on that basis. Label synthetic data as "synthetic" and the model will not treat it as evidence.

**② The model found a substantive contradiction between the source materials.** The three materials described the revenue-share direction
inconsistently (the task package said 65:35, while one document recommended 35:65); the model flagged it as an **evidence conflict** and required the basis to be adjudicated first
— a contradiction that no party had pointed out in the original project.

---

## 5. What this validation did not achieve

- **A full loop on a "real project" has still not been completed.** The real case was correctly blocked at the R phase,
  so E/B/U/I/D were run through on a **test project** (constructed by the author, not a real business project).
- **Failure paths were not tested**: 429, timeouts, truncated responses, non-JSON responses, and gate outputs the model returns that cannot be parsed
  (the last has unit-test coverage; the rest do not).
- **No repeated runs were done**: the same input run twice produced different results (one advanced to REVIEW, one rolled back to DISCOVER);
  this is normal variance at temperature 0.3, but it also shows that **a single run is not enough to evaluate output quality**.
- **The absolute level of output quality was not assessed**: running through ≠ analysing well. That requires independent review, which does not currently exist.

---

## 6. Failure paths (second round)

### Real API failure probes

Each failure was triggered in turn against the real DeepSeek endpoint, observing how `bench/provider.py` reacted:

| Failure | Actual behaviour | Assessment |
|---|---|---|
| Invalid key | `HTTP 401`, **no retry**, echoes the API's original text + a hint to check the key | ✅ retrying a 4xx is pointless; the judgement is correct |
| Non-existent model | `HTTP 400`, echoes the list of model names the API supports | ✅ the error message is enough to self-repair |
| Unreachable host | retries 3 times (2s/4s/8s backoff), then reports a connection error | ✅ transient failures are worth retrying |
| Wrong base_url path | `HTTP 404` + "check base_url, model name and key" | ✅ |

> Minor blemish: when the 404 response body is empty, the error message has nothing after "HTTP 404:", which reads as if content were missing.

### Orchestrator failure paths (7 new tests)

| Scenario | Behaviour |
|---|---|
| A single role call fails | the other roles' artefacts are kept; the failure is recorded in `errors` (with role name and reason) |
| **All roles fail** | the gate is **no longer called** — previously it wastefully called the model once with empty input. Fixed |
| The gate call throws | does not advance; `reason` records the exception text |
| The gate returns truncated JSON | does not advance |
| The decision-record call fails | the run finishes normally, the state transition still takes effect, and the error is recorded in `decision_record.error` |
| The decision record returns truncated JSON | same as above; reports "cannot parse as JSON" and points to the raw output file |
| **Provider name misspelled** | previously every role failed once, recorded as 6 "role failures" — and the user would go and check the network. **Fixed**: it now errors before writing any artefact and lists the available names |

---

## 7. Run-to-run consistency (second round)

The same input, same model and same evidence, run 3 times each.

### Did the flow complete

| Temperature | Completed all six phases | Final state |
|---|---|---|
| 0 | **3 / 3** | DISCOVER ×2, REVIEW ×1 (`new_cycle` returning to the start is a normal path) |
| 0.3 | **3 / 3** | DISCOVER ×3 |

> Comparison: before the gate defect was fixed it was **0 / 4** (all stuck at DISCOVER). After the fix, **6 / 6** completed.

### Was the decision content consistent

| Run | Choice | Options | Falsification conditions | Validation actions |
|---|---|---|---|---|
| 1 | Do not take any option live for now; if a direction is required, prioritise validating B's redemption assumption | 3 | **15** | 12 |
| 2 | Defer launch; gather further evidence first | 3 | **6** | 8 |
| 3 | Take option A as the direction; run a closed pilot of 30 people over 4 weeks first | 4 | **10** | 10 |

**Conclusion: the direction is consistent; the details are not reproducible.**

- **Direction is stable**: all three runs concluded "validate first, don't rush to launch" — which is the conclusion this decision should reach.
- **Details are unstable**: falsification conditions numbered 6 / 10 / 15, a 2.5× spread; one run gave a complete pilot design (4 weeks, 30 people) while another said only "gather further evidence first".
- **temperature=0 does not eliminate the differences.** Most APIs do not guarantee determinism even at temperature=0.

**What this means for users:**

1. **The output of a single run must not be treated as "the answer"**, only as "a usable starting point".
2. To obtain a stable conclusion, run several times and compare — if the direction is consistent but the details differ, the direction is credible; if even the direction differs, the evidence itself does not support the decision, and `INSUFFICIENT` is then the honest answer.
3. The system currently has **no built-in multi-run comparison**. This is a capability gap, not a completed capability.

---

## 8. Cost accounting (third round)

The actual consumption of one complete loop, measured against the real API:

| Scale | Model calls | tokens | Duration | Estimated cost |
|---|---|---|---|---|
| Two phases (DISCOVER + EVIDENCE) | 6 | 28,671 | 56 s | $0.0095 |
| **Complete six-phase loop** | **16** | **91,723** | **~110 s** | **$0.0298** |

(unit prices are $0.28 input / $0.42 output per million tokens; the cost is an estimate, not a bill.)

**In one line: one complete R→E→B→U→I→D run costs about 16 model calls, 90,000 tokens, 3 cents and roughly two minutes.**

Why the call count is 16 rather than 6 phases × 3: DISCOVER needs only the master agent,
each later phase is "number of roles + 1 gate", and one decision-record generation is added at the end.

### Two design constraints

1. **tokens are fact, cost is estimate.** The token count is read directly from the `usage` field of the API response;
   if it cannot be read, `available: false` is recorded **and the total is stated to be incomplete — never estimated**.
   A token count that was estimated and then written into a report as actual usage is worse than no number at all.
2. **This project hard-codes no prices.** Unit prices are supplied by the user via `--price-input` / `--price-output`.
   Prices change; hard-coding a price in the code manufactures a conclusion that will silently drift.

Cost results always carry a caveat: this is an estimate computed from the unit prices you supplied, **not a billed amount**,
and it excludes cache-hit discounts and batch discounts, and does not deduct duplicate charges from failed retries.

---

## 9. What remains unresolved after these three rounds

- A full loop on a real business project (the real case was correctly blocked at the R phase; E–D were run through on a constructed project)
- The **absolute** level of output quality (running through ≠ analysing well; consistent direction ≠ correct direction)
- Whether the model-judged conclusion consistency is itself reliable (it too is model output and equally affected by temperature)
- Multi-user collaboration and project persistence
