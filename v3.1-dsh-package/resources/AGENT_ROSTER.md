# Register of delegable roles

The REBUILD role set, and how to brief each one in this Harness. Full contracts, including
constraints and required output fields, live in `resources/agents/<file>.md`.

| Role | Contract | Owns | Typical deliverable |
|---|---|---|---|
| Master CMO / orchestrator | `agents/master_cmo.md` | Project contract, routing, merge, gate, final recommendation | Decision page + project state |
| Research & intelligence | `agents/research_intelligence.md` | Market, category, competitor, trend evidence | Evidence map with sources and dates |
| Customer insight | `agents/customer_insight.md` | Segments, jobs, barriers, tensions | Segment logic + validation plan |
| Business & economics | `agents/business_economics.md` | Value capture, cost, margin, pricing, unit economics | Unit-economics model with scenarios |
| Strategy & positioning | `agents/strategy_positioning.md` | Option comparison, positioning, value proposition | Three-option choice with trade-offs |
| Brand & product | `agents/brand_product.md` | Portfolio roles, product ladder, brand architecture | Architecture map + governance |
| Creative & content | `agents/creative_content.md` | Creative challenge, idea territories, content system | Creative brief + territories |
| SEO / GEO | `agents/seo_geo.md` | Search and generative-engine discovery, intent | Keyword/intent architecture plan |
| Growth & media | `agents/growth_media.md` | Funnel, channel roles, media plan, budget | Channel plan with caps and stop rules |
| CRM & lifecycle | `agents/crm_lifecycle.md` | Qualification, handoff, retention, lifecycle messaging | Lifecycle map + CRM stage definitions |
| Analytics & experimentation | `agents/analytics_experimentation.md` | KPI tree, instrumentation, cohorts, experiments | KPI tree + experiment cards |
| Red Team | `agents/red_team.md` | Adversarial review of the recommendation | Strongest failure case + kill criteria |
| Review & learning | `agents/review_learning.md` | Postmortem, decision log, reusable rules | Postmortem + updated decision log |

## Common contract for every role

Every role returns these ten fields, in this order:

`summary` · `findings[]` · `evidence[]` · `assumptions[]` · `unknowns[]` · `recommendation` ·
`confidence` · `dependencies` · `risks` · `next_actions[]`

Each contract file in `resources/agents/` additionally defines that role's **Inputs**, the
**Questions** it must answer, its **Method**, its **Must** rules and its role-specific **Stop**
constraint — so a brief can quote the contract rather than restate it.

Every role must: follow the evidence protocol and label claims `FACT` / `INTERPRETATION` /
`HYPOTHESIS` / `DECISION` / `UNKNOWN`; keep the smallest useful scope and not duplicate another
specialist's work; flag conflicts with the brief or with other evidence; perform no external side
effects and claim no tool use without execution evidence; and, when blocked, state the exact
missing input and the cheapest way to obtain it.

Roles recommend. They never approve budget, publish, contact customers, change production systems
or authorize spend.

## Briefing a role in this Harness

Use `subagent` for one role with fresh context, `subagent_fork` when the role needs this
conversation, and `workflow` when many independent pieces share one contract. A usable brief has
all seven parts — a role name and a vibe is not a brief:

1. **Role** — which contract, by file.
2. **Decision at stake** — the specific decision this work informs.
3. **Exact questions** — numbered, answerable, no "research everything".
4. **Inputs** — the documents, data or prior findings to use, by path.
5. **Output schema** — the ten fields above, plus any project-specific extras.
6. **Evidence standard** — minimum grade, required date/geography/sample, and what must stay an assumption.
7. **Stop condition** — when to return, when to return blocked, and what must never be done unasked.

Example skeleton:

```
Role: business_economics (resources/agents/business_economics.md)
Decision at stake: whether to fund the paid-acquisition test at 30k CNY.
Questions: 1) contribution margin per delivered order? 2) allowable CAC at 12-month
contribution LTV? 3) payback period at the proposed spend? 4) the CAC level at which the
test stops being worth running?
Inputs: <paths to supplied figures>; declare anything not supplied as UNKNOWN.
Output: the ten standard fields; show formulas, units, period and arithmetic.
Evidence standard: first-party numbers only for A; label every inference.
Stop condition: return with what is derivable; do not estimate a missing cost silently,
do not contact anyone, do not spend anything.
```

Never dispatch a role whose upstream dependency is still unstable — research that depends on a
settled category, or analytics that depends on a defined conversion event, must wait. For
conflicting results, send a targeted follow-up question rather than re-running the whole role.
