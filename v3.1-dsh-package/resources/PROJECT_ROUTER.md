# Project Router

## Classification
Classify the project across five dimensions:
1. Decision type: diagnose / research / strategy / brand-and-business plan (品牌全案、商业策划) / project positioning (项目定位) / industry or park planning (产业规划、园区规划) / campaign / growth optimization / audit / postmortem.
2. Business model: B2C / B2B / platform / place-based (文旅、地产、园区) / public brand / nonprofit / mixed.
3. Lifecycle: discover / launch / scale / turnaround / retain / exit.
4. Data maturity: none / fragmented / instrumented / cohort-ready / incrementality-ready.
5. Risk: low / medium / high based on spend, privacy, reputation, regulated category, external side effects.

A place-based, park, city, real-estate or platform project must additionally carry the five
complex-project analyses named in `OPERATING_RULES.md` — stakeholder structure, resource flow,
value flow, cash flow and governance. Route those with `business_economics` and
`strategy_positioning`, not as an unnamed extra.

## Specialist roles
- `master_cmo`: intake, route, merge, gate, final decision recommendation.
- `research_intelligence`: market/category, sources, trends, competitor evidence.
- `customer_insight`: segmentation, behavior, barriers, qualitative evidence.
- `business_economics`: business model, pricing, cost, margin, unit economics, scenarios.
- `strategy_positioning`: option comparison, positioning, value proposition, choices.
- `brand_product`: portfolio, brand architecture, product/offer roles.
- `creative_content`: creative brief, concept territories, content system.
- `seo_geo`: SEO, local discovery, GEO/AEO content, search intent; verify live tools before claiming data.
- `growth_media`: funnel, channel roles, media plan, tests and budget scenario.
- `crm_lifecycle`: lead qualification, sales handoff, retention, lifecycle messaging.
- `analytics_experimentation`: KPI tree, instrumentation, cohort analysis, experiment design.
- `red_team`: adversarial review across nine angles — customer, competition, business, finance, execution, organization, technology, measurement, reputation/legal (see `QUALITY_GATES.md`).
- `review_learning`: postmortem, decision log, reusable learning.

## Routing matrix
Role ids used here are the exact contract ids above.

| Request | Required roles | Optional roles | Gate |
|---|---|---|---|
| Brand/business strategy | master_cmo, research_intelligence, customer_insight, business_economics, strategy_positioning, brand_product, red_team | creative_content, growth_media, analytics_experimentation | R→E→B |
| Campaign plan | master_cmo, business_economics, creative_content, growth_media, analytics_experimentation | customer_insight, crm_lifecycle, red_team | B→U→I |
| Conversion drop | master_cmo, analytics_experimentation, growth_media, crm_lifecycle, customer_insight | research_intelligence, business_economics, red_team | R→E→I→D |
| SEO/GEO plan | master_cmo, research_intelligence, seo_geo, creative_content, analytics_experimentation | growth_media, red_team | E→U→I |
| Existing proposal audit | master_cmo, research_intelligence, business_economics, strategy_positioning, red_team | any relevant specialist | AUDIT |
| Marketing budget allocation | master_cmo, business_economics, growth_media, analytics_experimentation, red_team | crm_lifecycle, research_intelligence | I→D |
| Postmortem | master_cmo, analytics_experimentation, review_learning, red_team | the relevant channel specialist | D |
| Place-based / industrial / park / cultural-tourism project | master_cmo, research_intelligence, business_economics, strategy_positioning, customer_insight | brand_product, red_team — and the five complex-project additions in `OPERATING_RULES.md` | R→E→B |
| Product/offer launch | master_cmo, customer_insight, business_economics, brand_product, creative_content, growth_media, analytics_experimentation | crm_lifecycle, red_team | B→U→I |

## Routing constraints
- Do not invoke all agents by default.
- Run the **5C+** commercial diagnosis before the B gate on any strategy, positioning or
  brand/business engagement, and **PESTEL+** whenever the decision depends on forces the client does
  not control — new market, regulated sector, place-based or long-horizon plan. Both are in
  `ANALYTIC_FRAMEWORKS.md`.
- Do not ask research to estimate market size without geography, category, period and sizing method.
- Do not ask analytics to calculate CAC/LTV without defining numerator, denominator, cohort and time window.
- Do not ask creative to invent a campaign before target, customer tension, offer and desired action are sufficiently clear.
- For conflicting results, request a targeted follow-up task, not a broad re-run.
