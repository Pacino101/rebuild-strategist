# REBUILD Bench — evaluation protocol

## Goal
To evaluate whether the system improves decision quality, rather than comparing who produces longer output that looks more like a consulting report. V3.2 provides a benchmark framework and does not claim to have completed a model comparison experiment.

## Scoring (0–4 points per item)
1. Problem definition: does it distinguish symptoms, goals and decisions.
2. Evidence discipline: does it label sources and FACT/INFERENCE/ASSUMPTION/UNKNOWN.
3. Strategic trade-offs: does it compare substantively different options and state the rejected options.
4. Business loop: does it check unit economics, budget and constraints.
5. Validation design: are there metrics, sample/window, and stop conditions.
6. Falsification capability: does it propose falsification conditions that could change the decision.
7. Executability: are there owners, sequence, cost and time.
8. Honesty: does it avoid fabricating numbers, citations or results.

Maximum 32. If honesty scores 0, the sample is judged a failure and the total score does not offset it.

## Controlled experiment
For the same case, the same model version and the same available materials, run at least: A. a plain task prompt; B. a single-agent REBUILD Skill; C. REBUILD master agent + sub-agents (only when genuinely runnable). At least 3 independent runs per configuration; after hiding the configuration names, two reviewers score against the rubric and the score differences are recorded.

## Must be reported
- model/version, prompt version, run date, temperature or available parameters
- input materials and missing information
- per-item scores, total score, count of fabricated-fact errors, count of non-recomputable numbers
- run duration, token/cost (if obtainable)
- failure samples and reproduction method

## Pass thresholds (initial assumptions, to be adjusted later based on data)
- average score at least 24/32;
- no critical honesty failure;
- at least a 15% average improvement over the plain prompt;
- at least 90% of key numbers recomputable.
These are pre-set thresholds, not results already achieved.
