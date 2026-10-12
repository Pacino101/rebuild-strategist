# Case study: the metro apartment project — a complete run on a real project

> **Authenticity statement**: this is an anonymised version of a **real commercial project**. The owner, the site, the consultancy and all identifiable information have been removed entirely;
> what is retained is **the data actually used for the analysis and the complete set of outputs**. For the anonymisation method see [`ANONYMIZATION.md`](ANONYMIZATION.md).

---

## Why this case is included

The README's maturity statement long carried the line **"unverified: whether a complete R→E→B→U→I→D can be run end to end on real client data"**.

This directory is that verification.

More important is what it verified: **on a real project, this process caught a problem that no marketing technique can fix.**

A brand marketing programme written to a fairly complete standard — clear positioning, attributable customer segmentation, channel budget normalised to 100%, KPIs with review checkpoints —
does not hold on unit economics: **the operator burns through the deposit every month it operates, whether the occupancy rate is 60% or 93%.**

The problem is not marketing; it is the revenue-share clause.

---

## Five key findings

| # | Finding | Figure |
|---|---|---|
| 1 | The "1.9-year payback" claimed in the document can only be reproduced if the owner takes all of the profit share | At a 65% share it is **3.08 years** |
| 2 | The operator's unit economics are **structurally negative** | Revenue per room per month **681 yuan** vs cost per room per month **771–1,206 yuan** |
| 3 | **Across the entire 60%–93% occupancy range** the operator's monthly cash flow is negative | −59,840 / −52,181 / −45,544 / −42,992 yuan/month |
| 4 | The owner's payback constraint and the operator's break-even constraint **have an empty intersection** | The owner needs a share ≥50%; the operator's break-even needs the owner to drop to **31.1%** |
| 5 | Once non-acquisition spending is deducted from the 400,000 budget it exceeds the red line | Actual CAC **4,545 yuan** > the 4,500 yuan red line |

Item 4 is decisive: **this is not a negotiation question of "who should give ground"; given the average price and the cost structure, it has no solution.**
Signing locks in a contract under which the operator loses a cumulative 2.34–4.27 million yuan over 8 years.

> This is exactly why the "U (Unit Economics)" phase exists in the methodology — **revenue ≠ profit, ROAS ≠ contribution profit**.
> A marketing plan can be written beautifully, but the arithmetic will not change because of it.

---

## Contents

```text
project.json          Project state that can be run directly (run it with the repository CLI)
source/               Three anonymised real input documents
  ├── 01_合作模式研究报告.txt
  ├── 02_地块专项研究报告.txt
  └── 03_品牌营销全案.txt
rebuild/              The actual outputs of this project
  ├── KEY_FINDINGS.md     Summary of key figures (auto-generated)
  ├── DECISION.md         One-page decision page
  ├── SKILL_EVALUATION.md Skill evaluation report (including the conflicts and defects found)
  ├── kpi_tree.json      KPI tree
  ├── experiments.json   Experiment cards
  ├── model_output.json  Full output of the unit economics model
  ├── power_analysis.json Power calculation
  ├── scripts/            6 analysis scripts (reproduce every figure)
  └── schemas/            Snapshot of the schemas used at runtime (see "Known deviations" below)
```

---

## How to run it

```bash
# 1. Validate the project state (including the JSON Schema)
python core/rebuild_cli.py validate examples/metro_apartment/project.json

# 2. Inspect evidence gaps: which assumptions have no supporting evidence yet
python core/rebuild_cli.py evidence gaps examples/metro_apartment

# 3. Generate task packets (zero network requests)
python core/rebuild_cli.py run examples/metro_apartment --dry-run

# 4. Reproduce every figure in the case
cd examples/metro_apartment/rebuild && python3 scripts/run_all.py
```

`scripts/run_all.py` runs all 6 scripts in sequence and rewrites `KEY_FINDINGS.md`.
**No third-party dependencies are needed**; the standard library is enough.

---

## Known deviations (please read these)

**① The schemas used when this case was run differ from those in the current repository.**

This case ran on an earlier set of schemas (archived in the `legacy/v3.1` branch); its fields are **wider** than the current `schemas/`:
it supports a multi-tree KPI structure and `$ref`, and the experiment cards also include fields such as `audience` / `control` / `variant` /
`minimum_detectable_effect` / `sample_logic`, which the current repository's `experiment.schema.json` does not have.

For reproducibility, the schema snapshot used at runtime is kept in `rebuild/schemas/`.

**This deviation is itself a finding: a real project needs more fields than the current schema provides.**
Converging the current schema to what real use cases need is a to-do item, not a completed one.

**② The operator's costs in the unit economics model are reconstructed, not original data.**

The document gives only "the operator's monthly own costs of 57,800 yuan" with no breakdown. `02_econ_model.py` **reconstructed** that cost
from line items such as labour, common areas, maintenance and marketing (90,473 yuan/month), and gives a range of 771–1,206 yuan/room·month.
**This is an inference, not a fact.** The confidence of all related conclusions is limited by this.

**③ The customer segment proportions have not been verified by questionnaire.**

The persona weights (35%/30%/15%/10%/10%) are values proposed by the plan; the original text itself labels them "to be verified by a pre-registration questionnaire with n≥100".
This case did not perform that verification.

**④ All three experiments are `proposed`; none was executed.**

The conclusion of `power_analysis.json` is: detecting a +30% relative difference between channels requires 2,479 groups per arm,
which is 5.5 times the full-period viewing-volume KPI (900 groups). **In other words the sample size is simply not sufficient**, so all three experiments can only count as directional.

---

## Follow-up: the loop closed (added 2026-10)

This analysis's recommendation was "**run a clause stress test first, renegotiate the revenue-share structure before signing**", not "sign" and not "abandon".

**Actual outcome** (recorded in `decisions/DR-001.json` + `decisions/outcomes/DR-001.json`):

| Item | Content |
|---|---|
| Expected | If signed under the current 65:35 clause, the operator's monthly cash flow would be negative and the deposit would burn through in about 22 months |
| Actual | The owner adopted the recommendation and **did not sign under the current clause**; the revenue-share structure has been adjusted; **the operator did not sign**, and the two parties are renegotiating |
| Deviation type | `AS_EXPECTED` (as expected) |
| Next step | `CONTINUE` |

Updates to the key assumptions:

| Assumption | Result |
|---|---|
| The operator would accept 65:35 | **Overturned** — the operator did not sign |
| The owner's payback and the operator's break-even have an empty intersection | **Confirmed** — the two parties indeed failed to reach agreement on the original clause |
| Steady-state occupancy can reach 93% | Still unknown (not yet open) |

**What this proves, and what it does not prove:**

✅ The analysis **changed a real decision** — the project did not proceed under the original clause;
✅ The blocking point the analysis predicted (the operator would not accept that revenue share) **did occur in reality**.

❌ It does **not** prove that the analysis's calculations are correct. The operator not signing could also be due to financing, capacity or something else;
❌ It does **not** prove that the new revenue-share structure holds — **it has not been calculated yet**.
    If the owner's share is still higher than the 31.1% back-solved from the constraint, the new clause may still not hold, just less obviously;
❌ There is no operating data yet. This project has not yet opened.

> **"Being adopted" is not the same as "being validated".** Adoption shows the conclusion was persuasive; validation takes time.
> And the owner saying "feasible" is precisely the result the model predicted — what the model says is "this clause holds for the owner
> but not for the operator", and the owner was always the party the numbers worked out for.

## What this case does not prove

- It does not prove that this method can raise the ROI of a real project — only that it can be run to completion, and catches an arithmetic problem.
- It does not prove that the analysis was arithmetically right. The operator declining to sign is **consistent with** the prediction, but it could have other causes — financing, capacity, a competing project.
- It does not prove that the **revised** revenue-share structure works. It has not been modelled.
- The outcome in the follow-up section is **self-reported by the commissioning side and has not been independently verified**.
- It does not prove generalisability — this is one case, not a sample.

**The only thing it proves is this: on real data, this process will indeed push the unit economics through to a conclusion,
rather than stopping at "recommend optimising the channel mix".**
