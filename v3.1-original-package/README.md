# REBUILD Strategist Agent V3.1 — DeepSeek Harness Package

**Package status: authored and statically checked; not yet installed or runtime-tested in DeepSeek Harness.**

This package upgrades the existing REBUILD Skill and Digital Marketing OS V2.0 design. It preserves the REBUILD R→E→B→U→I→D loop, the 34 decision worksheets, the 10-tool integration baseline, evidence discipline, Red Team review, and the CMO/master-agent orchestration concept.

## What's new in V3.1
- Explicit orchestration contract: intake → route → task packets → execution → merge → Red Team → QA → approval gate → delivery.
- A phase-gate system with entry/exit criteria and mandatory rollback conditions.
- Structured task and evidence schemas, avoiding free-form agent handoffs.
- Marketing economics guardrails for funnel, CAC, LTV, ROAS/ROI, attribution, budget allocation and reallocation.
- Tool registry distinguishes `configured`, `connected`, `tested`, and `production-approved`; no false claims of integration.
- Human approval requirements for spending, publishing, CRM/customer messaging, data deletion, and external side effects.
- Harness-neutral adapter notes because exact DeepSeek Harness import/runtime conventions must be verified in the user's installation.

## Package map
- `skills/rebuild-strategist/SKILL.md`: main skill entrypoint.
- `skills/rebuild-strategist/references/34_WORKSHEETS.md`: 34 decision worksheets and their minimum fields.
- `skills/rebuild-strategist/references/MARKETING_OS.md`: full-funnel operating model and metrics.
- `skills/rebuild-strategist/references/PROJECT_ROUTER.md`: project classification and routing.
- `skills/rebuild-strategist/references/QUALITY_GATES.md`: gates, QA, evidence, and stop conditions.
- `agents/`: role contracts for the master and specialist agents.
- `config/`: routing, permission, install order, tool registry.
- `schemas/`: JSON schemas for project state, task packets, evidence, experiments, KPI trees.
- `workflows/`: lifecycle workflow and test scenarios.
- `integrations/`: integration contracts, not pre-connected plugins.
- `examples/nanjiang_tea/`: demonstration input/output skeleton with assumptions clearly labelled.
- `tests/`: static validation checklist and smoke-test prompts.

## Installation plan
1. Back up the existing Skill and Digital Marketing OS folder.
2. Inspect the target Harness's accepted Skill format, agent definition format, tool/MCP configuration format, and whether subagents can be invoked natively.
3. Import `skills/rebuild-strategist/SKILL.md` as the primary skill/instructions.
4. Add the reference files as retrievable knowledge files if Harness supports them; otherwise paste the compact routing/quality rules into the primary instruction and attach the references.
5. Configure the master agent first. Add specialist agents only if Harness supports separate agents and explicit delegation. If not, use the same contracts as sequential role-play within one agent.
6. Configure tools one at a time, starting with read-only research/analytics. Never enable spend, publish, send-message, delete, or write actions before approval policies are tested.
7. Run the smoke tests in `tests/SMOKE_TESTS.md`.
8. Record actual status in `config/tool-registry.yaml`: `not_configured` → `configured` → `connected` → `tested` → `production_approved`.

Do not claim installation or execution succeeded until the actual Harness run produces evidence.
