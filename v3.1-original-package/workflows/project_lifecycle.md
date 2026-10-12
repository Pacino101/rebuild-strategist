# Workflow: REBUILD Project Lifecycle

```text
User request
  ↓
Intake / Project Contract
  ↓
Classify mode + phase + risk
  ↓
Load project state and relevant worksheets
  ↓
Route specialist task packets
  ↓
Execute (parallel only when dependencies permit)
  ↓
Validate schema + evidence + math
  ↓
Merge conflicts / resolve gaps
  ↓
Red Team (proportional to risk)
  ↓
Quality gate decision
  ├─ BLOCKED → request evidence / revise task packet / rollback phase
  ├─ PASS_WITH_GAPS → proceed only with documented limitation and owner
  └─ PASS → next phase / deliverable
  ↓
Human approval gate for external side effects
  ↓
Deliver decision page + action plan + project-state change log
```

## Retry and rollback
- Schema failure: one targeted correction request to the producing role.
- Contradictory evidence: assign a comparison task using exact sources and methods.
- Unsupported conclusion: downgrade to hypothesis or block the gate.
- Arithmetic failure: recompute independently; preserve inputs and formula.
- Failed experiment: update assumption status and return to the earliest affected phase.
- Repeated failure after two targeted retries: stop automatic retries and ask the user for a decision or missing input.

## Completion definition
A task is complete only if acceptance criteria are checked, evidence provenance is recorded, risks/gaps are disclosed, and the project state is updated. A generated document alone is not proof of execution.
