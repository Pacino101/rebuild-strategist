# Architecture: REBUILD V3.2

```text
User Business Question
        |
        v
Master Agent / Decision Orchestrator
        |
        +--> Customer Evidence Role
        +--> Market Structure Role
        +--> Positioning & Strategy Role
        +--> Business Model Role
        +--> Growth System Role
        +--> Measurement & Experiment Role
        +--> Red Team Role
        +--> Learning & Review Role
        |
        v
Evidence Ledger + Decision Record + KPI/Experiment Specs
        |
        v
Deterministic Phase Gate / State Machine
        |
        +--> Advance to next phase
        +--> Return for more evidence
        +--> Rework economics or strategy
        +--> Block pending clarification
```

## Separation of concerns

- **Method layer:** REBUILD stages, evidence policy, decision protocol, gates and rubric.
- **Role layer:** responsibilities and deliverable contracts for the master and specialist roles.
- **State layer:** deterministic allowed transitions independent of model output.
- **Evaluation layer:** fixed cases, scorecard, critical failure conditions and blind review procedure.
- **Host adapter layer:** instructions for a host such as DeepSeek Harness. The adapter must not redefine REBUILD policy.

## Current implementation boundary

The current Python CLI validates basic project fields and checks deterministic transitions. It does not invoke a language model, create child agents, store project history, or connect marketing data. The Markdown role contracts describe expected behavior but are not runtime agent instances.
