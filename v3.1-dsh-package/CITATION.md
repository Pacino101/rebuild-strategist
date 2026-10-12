# Citation

If this skill or its method helps your work, cite it as:

```bibtex
@misc{rebuild_strategist,
  title        = {REBUILD Strategist: an evidence-disciplined strategy skill for AI agents},
  author       = {{REBUILD Strategist contributors}},
  year         = {2026},
  version      = {3.2.0},
  howpublished = {\url{https://github.com/<owner>/<repo>}},
  note         = {Operates the REBUILD R→E→B→U→I→D loop with phase gates, evidence
                  labelling and explicit task contracts. MIT licensed.}
}
```

Plain text:

> REBUILD Strategist contributors (2026). *REBUILD Strategist: an evidence-disciplined strategy
> skill for AI agents*, version 3.2.0. https://github.com/&lt;owner&gt;/&lt;repo&gt;

Replace `<owner>/<repo>` with the published location before release.

## Citing a specific rule or framework

Several parts of this package are individually citable because they are defined precisely enough to
be checked rather than paraphrased:

| Component | File |
|---|---|
| Evidence labelling and source grading | `resources/OPERATING_RULES.md` |
| The five-category metric split (outcome / diagnostic / activity / guardrail) | `SKILL.md` §6 |
| Phase-gate exit criteria and stop conditions | `resources/QUALITY_GATES.md` |
| 5C+, PESTEL+ and the Evidence Ladder | `resources/ANALYTIC_FRAMEWORKS.md` |
| The 34 decision worksheets | `resources/WORKSHEETS.md` |

## Provenance

The method descends from an original Chinese-language strategy agent specification (the REBUILD
loop, the 20-tool inventory, the consumer-insight action test, and the eleven prohibitions). That
document is retained verbatim in `docs/LEGACY_SKILL_V3.md`, marked as superseded, so the lineage is
auditable rather than asserted. Where the current package and that archive disagree, the current
package wins, and the banner in the archive lists the specific differences.
