# Status and Roadmap

## V3.4 Current status (locally verifiable)

| Capability | Status | Notes |
|---|---|---|
| Original methodology and phase gates | Documented | Still requires validation on a real project |
| Local project field validation | Implemented | The CLI runs handwritten checks and JSON Schema validation by default |
| JSON Schema validator | Implemented | Standard library only; unimplemented keywords raise a warning instead of passing silently |
| Deterministic state machine | Implemented | Only performs legal state transitions, never calls a model |
| Evidence ledger | Implemented | JSONL append storage, mandatory validation before write, semantic quality checks, gap analysis, verifiable-source ratio, Markdown export |
| Evidence source verification | Implemented | The `DOC-001` form is machine-verifiable; dangling links are errors rather than warnings; `evidence provenance` reports the verifiable ratio |
| Decision records and review | Implemented | Decisions are stored, overdue reviews are proactively surfaced, outcomes are backfilled with a mandatory deviation type, and results are written back to project.json |
| Data source layer | Implemented | Local files (CSV/TSV/JSON/JSONL/TXT/MD/XLSX, with Chinese-encoding fallbacks) + self-hosted HTTP endpoints; SHA-256 provenance; secrets only via environment variables |
| Runtime orchestrator | Implemented | Dispatches roles in phase order, injects evidence and materials, has the model decide the gate, lets the state machine adjudicate transitions, and emits schema-validated decision records |
| Unit tests | Implemented | Cover the state machine, CLI, Schema validation, evidence ledger, data sources, orchestrator, blind-review scaffold, and Provider |
| Benchmark cases and scoring protocol | Established | One pilot has been run (1/4 cases, n=1 per configuration); the sample is insufficient — see `bench/PILOT_B03.md` |
| Blind-review experiment scaffold | Implemented | ID hashing, identity concealment, reviewer-consistency checks |
| Model Provider integration layer | Implemented | Two calling conventions: OpenAI-compatible / Anthropic-compatible |
| scorecard structural validation | Implemented | Total-vs-component consistency, value ranges, required fields |
| DeepSeek Harness Skill | Provided | `harness/deepseek/SKILL.md` + installation instructions; CI validates frontmatter; not yet tested end to end |
| Parallel multi-agent scheduling | Not implemented | The orchestrator runs strictly sequentially, one model call per role; true parallelism needs host support and is not pretended |
| Built-in marketing platform connectors | Deliberately excluded | Does not depend on third-party projects such as n8n, PostHog or Mautic |
| Sub-agent role contracts | Documented | Each of the 8 roles has its own mission, input boundary, dedicated question checklist and failure modes |
| Decision history versioning and dependency rollback | Not implemented | Decisions can be stored and reviewed, but when an assumption is falsified the affected decision nodes are not yet listed automatically |
| Actual execution of marketing actions | Not implemented | It produces decisions and validation plans, but does not run campaigns, send messages, or write back to any external system |
| GitHub Actions CI | Configured | `.github/workflows/tests.yml`, a four-version matrix for Python 3.10–3.13, including an end-to-end smoke test |
| Open-source repository release | Done | MIT license, with SECURITY / CODE_OF_CONDUCT / PR and issue templates |
| Unit test results | Passing | `python -m unittest discover -s tests` — 211 tests; CI green on all four Python versions 3.10–3.13 |
| Quality of the orchestrator against a real model | **Unverified** | All existing tests inject fake models and make no network requests |

## Iteration roadmap

### V3.2.1 — Reproducible evaluation
- ✅ The blind-review scaffold is implemented (`bench/bench_runner.py`), including identity concealment and reviewer-consistency checks;
- Run the four fixed benchmark cases (**1/4 done**: the B03 pilot, n=1 per configuration, sample insufficient — see `bench/PILOT_B03.md`);
- Run the three-arm comparison: plain prompt, structured framework, REBUILD;
- At least two reviewers score blind, and at least one is unfamiliar with this methodology;
- Publish the raw scores and failure samples, not only the average scores;
- When the threshold is not met, record it honestly and analyse why.

### V3.3 — Runtime, evidence ledger and data sources (done)
- ✅ Schema validator: unimplemented keywords raise a warning instead of passing silently;
- ✅ Evidence ledger: JSONL storage, mandatory validation before write, semantic quality checks, gap analysis, export;
- ✅ Data source layer: local files + self-hosted HTTP endpoints, with Chinese-encoding fallbacks and hash provenance;
- ✅ Runtime orchestrator: sequential role dispatch, model-decided gates, state-machine-adjudicated transitions.

### V3.4 — Decision review loop (done)
- ✅ Decision record store: storage, review-due reminders, outcome backfill, write-back to project.json;
- ✅ Mandatory distinction of deviation types: execution / strategy / assumption / multiple / unattributable;
- ✅ Evidence sources are machine-verifiable (`DOC-###`), and dangling links are errors;
- ✅ The host Skill was rewritten and installation instructions added;
- ❌ **The output quality of the orchestrator against a real model remains unverified** — all existing tests inject fake models;
- ❌ **The review mechanism has not yet been used by any real project.**

### V3.5 — Real-model validation and project memory
- **Run one complete R→E→B→U→I→D on a real model**, and publish the raw output and failure samples;
- Invite nameable independent reviewers to redo the blind review, or explicitly label it as model self-assessment and lower the strength of the conclusions accordingly;
- Project status versioning and changelog;
- Connect key assumptions to decision dependencies: when evidence changes, automatically list the affected decision nodes;
- Introduce user confirmation and human approval.

### V3.6 — Harness-native execution layer
- Develop a separate adapter based on the Harness version and capabilities the user actually has installed;
- Use host capabilities to achieve true parallel sub-agent scheduling, timeouts and retries on failure;
- Add integration tests and installation instructions;
- No capability may be marked "implemented" until it has passed a test run.

### V4 — A publicly verifiable product
- Publish benchmark results, methodological limitations and reproduction scripts;
- Add industry cases, but strictly distinguish synthetic data from real client data;
- Establish a stable versioning policy, contribution guide, license and security policy.
