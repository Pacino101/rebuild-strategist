# Adapter contract — how to plug your own data or model into this skill

**Status: the contract below is new and no adapter has been built against it yet.** It is written so
that a developer can implement one today, and so that `tools/check_adapter.py` can verify the result.
An adapter that exists but has not been run is still `configured`, not `connected` — see the status
ladder at the end.

There are three separate integration points. They are often confused, so they are separated here.

| # | You want to… | Integration point | Who implements it |
|---|---|---|---|
| 1 | Run this skill on a different model (GPT, Claude, a local model) | **Nothing in this repository.** Your agent runtime selects the model. See §1 | Your runtime |
| 2 | Give the skill figures from your analytics, CRM, ad platform or data warehouse | **Data adapter.** See §2 | You |
| 3 | Let the skill read a platform live, with credentials | **Adapter + the approval boundaries.** See §3 | You, with care |

---

## 1. Model binding — deliberately not ours

This package contains **no model client, no API key handling, and no network code**. That is not an
omission. A skill is instructions plus resources; the runtime decides which model executes them.

So to run this on a different model you change the runtime, not this repository:

- **DeepSeek Harness** — the profile's `agent-default-model` row sets provider and model; see
  `resources/DSH_ADAPTER.md`.
- **Claude / other skill runtimes** — install the directory into that runtime's skill root; `SKILL.md`
  is plain Markdown with YAML frontmatter (`name`, `description`), which is the portable subset.
- **Bring your own agent loop** — load `SKILL.md` as the system prompt, expose `resources/` as files
  the model can read, and call `tools/strategy_calc.py` as a tool. The skill's rules refer to that
  script by name, so a tool named `strategy_calc` satisfies them.

**If you want a model-specific adapter, do not add it here.** It would make the package
runtime-dependent while pretending to be portable. Put it in your runtime.

## 2. Data adapter — the contract

An adapter converts one external source into the business-model JSON that
`tools/strategy_calc.py` consumes. That is the whole job.

### Input

Whatever your source provides: a CSV export, an HTTP response, a database query, a spreadsheet.

### Output — required

A JSON object on **stdout**, conforming to [`adapter_output.schema.json`](adapter_output.schema.json).
Shape:

```json
{
  "adapter": "posthog-export",
  "source": {
    "system": "PostHog",
    "resource": "events export 2026-Q3",
    "retrieved_at": "2026-10-12T21:00:00+08:00",
    "method": "manual CSV export",
    "status": "connected"
  },
  "model": {
    "price_per_unit": 99,
    "variable_cost_per_unit": 18,
    "retention_months": 24
  },
  "provenance": [
    {"field": "retention_months", "source_field": "cohort_retention_m12",
     "note": "inverted from 12-month retention", "grade": "A"}
  ],
  "missing": ["variable_cost_per_unit"]
}
```

### Rules — these are the ones that make an adapter trustworthy

1. **Never invent a value.** If the source does not supply a field, put it in `missing` and omit it from
   `model`. A fabricated default is worse than a gap, because the gap is visible downstream and the
   default is not.
2. **Declare provenance per derived field.** If you computed `retention_months` from a retention curve,
   say so in `provenance`. Untransformed fields may be omitted from `provenance`; derived ones may not.
3. **Grade what you emit.** Reuse the skill's grades: `A` first-party system data, `B` official or
   audited, `C` credible secondary, `D` expert judgment, `E` assumption. A number pulled from a
   platform is not automatically `A` — it is `A` only if that platform is your system of record.
4. **State the method.** `manual CSV export`, `REST API v2`, `SQL warehouse query`, `MCP tool`. A
   reviewer must be able to reproduce the retrieval.
5. **Exit non-zero on failure**, with a message on stderr. A partial success that exits 0 will be
   treated as complete by everything downstream.
6. **No writes without explicit approval.** A read adapter may only read. If you are building a write
   path — adjusting a bid, sending a campaign, updating a CRM record — it must stop and request
   approval at the moment of action, and that is stated in the skill's safety rules, not optional here.
7. **Log no secrets and no personal data.** Credentials come from the environment or a secret manager.
   Export nothing that identifies an individual unless the task genuinely requires it and it is
   authorised.

### Validate your adapter

```bash
python3 tools/check_adapter.py --adapter ./your_adapter.sh --source ./sample_input.csv
```

The checker runs your adapter, validates the output against the schema, and applies the seven rules
above — in particular it fails an adapter that emits a `model` field absent from the source, and one
that exits 0 while reporting `missing` fields it could have derived. A passing check means
`configured`; it does not mean `connected` until you have run it against the live system and recorded
the result.

### Reference implementation

`tools/adapters/csv_export.py` is a minimal working adapter for a CSV export: no network, no
credentials, no dependency. Use it as the shape to copy. It is deliberately boring.

## 3. Live platform access — the part that needs care

The skill ships ten integration contracts (`resources/tool-registry.yaml`) as **plans, not
connections**. To make one real:

1. **Write the adapter** per §2, starting read-only.
2. **Prove it against the live system** and record sanitised evidence: response shape, timestamp,
   permission scope.
3. **Update the status** in `resources/tool-registry.yaml`. The ladder is ordered and each step needs
   evidence:

| Status | Means |
|---|---|
| `not_configured` | Default. Every integration ships here. |
| `configured` | Code exists and passes `check_adapter.py` against sample data. |
| `connected` | Has successfully read the live system at least once. |
| `tested` | A positive and a negative path have both been exercised (including a failure or rate limit). |
| `production_approved` | A named human has approved it for live use, with a rollback plan. |

A YAML entry is not evidence. Neither is a passing unit test. Moving a status without the corresponding
observation is the one thing this project treats as a defect rather than a gap — its entire premise is
that a claim and its evidence are distinguishable.

## 4. What this contract deliberately does not do

- **No connector zoo.** No pre-built integrations, because an unverified connector is a claim without
  evidence, and a repository full of them trains users to trust status they have not checked.
- **No credential storage.** Secrets belong in your secret manager.
- **No orchestrator.** If you want n8n, Airflow or a cron job to schedule adapters, that is your
  infrastructure and it should stay yours.
- **No write path in the shipped code**, ever. Writes belong in code you wrote and reviewed, behind an
  approval gate you control.
