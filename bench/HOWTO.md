# Bench operations manual

## What this is

`bench_runner.py` is REBUILD's controlled-experiment scaffold. It solves this problem: **making the question "how much better is REBUILD than a plain prompt, really?" answerable with data, rather than with marketing.**

Python standard library only, no third-party dependencies.

## Five-step flow

```bash
# 1. Generate the blind-review manifest (each case × 3 arms × N runs)
python bench/bench_runner.py generate --runs 3

# 2. Get the blank score sheet
python bench/bench_runner.py template

# 3. Merge reviewer results (at least two reviewers, each scoring all items)
python bench/bench_runner.py import runs/review_1.csv runs/review_2.csv

# 4. Reveal identities and write the scorecard
python bench/bench_runner.py reveal

# 5. Summarise and check the thresholds
python bench/bench_runner.py summarise
```

## Three arms

| Arm | Content | Purpose |
|---|---|---|
| A | `bench/prompts/A_plain.txt` — a plain "senior marketing consultant" prompt | Baseline |
| B | `bench/prompts/B_skill.txt` — a structured goal-oriented framework | Structured, but without REBUILD discipline |
| C | `harness/deepseek/SKILL.md` — the full REBUILD flow | Treatment arm |

**Note**: arm B uses a generic goal-oriented analysis framework. If you want to compare against a specific competitor (such as one of marketingskills' skills), simply put that skill's original text into `prompts/B_skill.txt` and note it in the CHANGELOG. That is more convincing than building a weak baseline of your own.

## How blind review is kept valid

The script derives IDs with SHA-256 from `case + configuration + run index + salt` and shuffles the presentation order. Reviewers see `X-XXXXXXXXXX` and have no way to tell which configuration it is.

Key safeguards (all tested in practice):

| Safeguard | Behaviour |
|---|---|
| Duplicate-ID detection | multiple runs of the same configuration get different IDs, so reviewers cannot infer from repetition |
| Same-salt reproducibility | the same `--salt` produces exactly the same order, which makes checking easier |
| Single-reviewer refusal | `reveal` errors out with fewer than 2 independent reviewers |
| Coverage completeness | refused if any reviewer has not scored every item, avoiding unequal sample sizes |
| Reviewer-consistency check | when two reviewers differ by > 6 points it prompts a re-check and does not average automatically |

## Reviewer requirements

At least **2 independent reviewers**, each scoring every item. See `REVIEW_PROTOCOL.md` for the review protocol.

The most important rule of all: **arm A (the baseline) should not be scored by the REBUILD author alone**. You are the author of the methodology and have a systematic tendency to overrate your own approach. If you can only find one reviewer, they should at least be someone unfamiliar with the REBUILD methodology.

## Thresholds

Pre-set targets (the initial assumptions in `RUBRIC.md`, not existing results):

- arm C mean score ≥ 24/32
- no honesty score of 0 in arm C
- arm C improves ≥ 15% over arm A
- ≥ 90% of key numbers recomputable

**Failing to meet the threshold is also a valid result.** Record it honestly and analyse why; do not adjust the rubric or discard failure samples. This is the thing this project cares about most.

## Publishing results

`scorecard.csv` records the item-by-item scores, and `runs/reveal_key.json` records the mapping. When publishing results:

1. Publish the full `scorecard.csv`, not just the average scores
2. Publish the failure samples verbatim
3. State the model version, prompt version and run date
4. If the threshold was not met, state that it was not met and why

The `runs/` directory contains unpublished answer content and the salt, and is not committed by default (see `.gitignore`). If you need to publish a complete reproducible record, delete that line and explain separately.

## FAQ

**Q: How many runs should N be?**
The protocol requires at least 3 per arm, to observe variance. For a first validation you can use `--runs 1` to walk through the flow quickly, but the conclusions are not strong enough to publish.

**Q: Do I have to use two models?**
No. But if you run all three arms on the same model, the conclusions can only speak to "methodology differences", not to "switching models helps more".

**Q: Can't find reviewers?**
Ideally, find peers unfamiliar with this methodology. Failing that: find two people unconnected to marketing but capable of logical evaluation — at least that guarantees they are not stakeholders in REBUILD.
