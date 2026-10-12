# Contributing

This project is a **decision instrument**, not a content collection. That single fact determines
what belongs here and what does not.

## The admission test

Every rule, worksheet, agent contract or gate you propose must answer one question:

> **What decision would come out differently if this did not exist?**

If you cannot name a concrete decision that changes — a go/no-go, a price, a budget, a channel, a
stop rule — it is commentary, and commentary does not belong in the skill body. It can live in
`docs/` as an essay, clearly separated from the operating instructions.

Corollary: a rule that sounds wise but never changes an output is worse than no rule, because it
consumes the model's attention budget and dilutes the rules that do bite.

## What we most want

| Contribution | Why it is valuable |
|---|---|
| **A new failure mode with a test** | A case where the skill produced a confident, wrong, or unfalsifiable answer — plus a smoke test that reproduces it. This is the highest-value contribution we accept. |
| **A metric definition that closes a loophole** | e.g. a formula that cannot be gamed by redefining the denominator mid-sentence. |
| **A gate criterion that is observable** | A condition a reviewer can check without trusting the author's summary. |
| **A worked example with real arithmetic** | Anonymised. Shows the loop handling a real constraint, not a tidy hypothetical. |
| **A schema tightening** | A field that currently accepts garbage, plus the validation that rejects it. |
| **A translation** | The skill is English-first with Chinese routing keywords. A full Chinese edition that keeps the *discipline* (not just the words) is a large, welcome contribution. |

## What we will decline

- More frameworks, more sections, longer output templates. The skill already has more structure than
  most decisions need; the scarce resource is judgment, not slots.
- Prompt-style "act as a world-class CMO" personas. The method is the value; the persona is noise.
- Anything requiring a paid tool to be useful by default. Integrations are contracts, and they ship
  `not_configured` until someone has actually connected and tested one.
- Claims of performance. You may not add a benchmark, market size, or "clients saw X% lift" that is
  not traceable to a named, dated source. Fabricated evidence is the one unrecoverable defect in a
  project whose entire premise is evidence discipline.

## Definition of done

Before opening a pull request:

```bash
./tests/verify_package.sh          # static integrity; must pass
```

And for any behavioural change, run the relevant smoke test in `tests/SMOKE_TESTS.md` and report the
**actual** result. "Should pass" is not a result. If you cannot run it, say so in the PR and mark the
test unverified — an honest gap is acceptable, a claimed pass that was never run is not.

If your change alters the entrypoint body, keep it under the 8,192-character threshold that
`tests/verify_package.sh` enforces: above that, a compaction event can silently trim the middle of
the skill out of the model's context.

## Style rules that are not negotiable

1. **Label claims.** `FACT` / `INTERPRETATION` / `HYPOTHESIS` / `DECISION` / `UNKNOWN`, with source
   quality graded separately from relevance. Applies to documentation about this project too — do not
   assert that the method "works" without saying what evidence you have.
2. **Never present a plan as a result**, or a proposed integration as a connected one.
3. **Keep the non-mandatory clause.** Frameworks are prompts for judgment. If a rule you add would
   force a field to be filled for its own sake, it contradicts the design.
4. **Prefer a derived number to a borrowed one.** Break-even, allowable CAC and budget caps must come
   from the business model in front of you, never from a generic benchmark.
5. **Do not weaken the stop conditions.** The skill refusing to answer is a feature. If your change
   makes it easier to produce an answer without evidence, it is a regression.

## Reporting a problem

Open an issue with: the mode you ran, the input (anonymised), what the skill produced, and what it
should have produced. A reproducible wrong answer is more useful than a general complaint.

## Licence

By contributing you agree your work is licensed under the MIT Licence in `LICENSE`.
