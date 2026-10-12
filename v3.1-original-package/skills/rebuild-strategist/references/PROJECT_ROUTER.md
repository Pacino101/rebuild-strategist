# Project Router

## Classification
Classify the project across five dimensions:
1. Decision type: diagnose / research / strategy / campaign / growth optimization / audit / postmortem.
2. Business model: B2C / B2B / platform / place-based / public brand / nonprofit / mixed.
3. Lifecycle: discover / launch / scale / turnaround / retain / exit.
4. Data maturity: none / fragmented / instrumented / cohort-ready / incrementality-ready.
5. Risk: low / medium / high based on spend, privacy, reputation, regulated category, external side effects.

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
- `red_team`: adversarial review across customer, competition, business, finance, execution, organization, technology.
- `review_learning`: postmortem, decision log, reusable learning.

## Routing matrix
| Request | Required roles | Optional roles | Gate |
|---|---|---|---|
| Brand/business strategy | master, research, customer, business, strategy, brand_product, red_team | creative, growth, analytics | R→E→B |
| Campaign plan | master, business, creative, growth_media, analytics | customer, CRM, red_team | B→U→I |
| Conversion drop | master, analytics, growth_media, CRM, customer | research, business, red_team | R→E→I→D |
| SEO/GEO plan | master, research, seo_geo, content, analytics | growth_media, red_team | E→U→I |
| Existing proposal audit | master, research, business, strategy, red_team | any relevant specialist | AUDIT |
| Marketing budget allocation | master, business, growth_media, analytics, red_team | CRM, research | I→D |
| Postmortem | master, analytics, review_learning, red_team | relevant channel specialist | D |
| Place-based / industrial project | master, research, business, strategy, customer | stakeholder/resource-flow analysis, brand_product, red_team | R→E→B |
| Product/offer launch | master, customer, business, brand_product, creative, growth_media, analytics | CRM, red_team | B→U→I |

## Routing constraints
- Do not invoke all agents by default.
- Do not ask research to estimate market size without geography, category, period and sizing method.
- Do not ask analytics to calculate CAC/LTV without defining numerator, denominator, cohort and time window.
- Do not ask creative to invent a campaign before target, customer tension, offer and desired action are sufficiently clear.
- For conflicting results, request a targeted follow-up task, not a broad re-run.
