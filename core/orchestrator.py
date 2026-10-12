#!/usr/bin/env python3
"""REBUILD runtime orchestrator.

It actually runs the role contracts under `agents/`: it schedules roles by
phase, injects evidence and material, collects output, judges gates, advances
state and produces the decision record.

Three non-negotiable design constraints
---------------------------------------
1. **Sequential execution; no pretending to be parallel.** Each role is one
   model call, one after another. This orchestrator is not a multi-agent
   parallel runtime — if the host (such as DeepSeek Harness) offers sub-agent
   capability, parallelism is the host's job. Calling sequential calls
   "multi-agent collaboration" is exactly the kind of self-deception this
   project rejects.

2. **State transitions are decided by the state machine, not by the model.**
   The model only judges "does the gate pass, and which event should fire";
   whether that event is legal and which state it leads to is always decided by
   `core/state_machine.json`. An illegal event from the model is rejected.

3. **Evidence proposed by the model does not enter the evidence ledger.** Model
   output is not evidence. Evidence items the model suggests are written to
   `proposed_evidence.jsonl` for human review and are never booked
   automatically. Automatic booking would degrade the "evidence ledger" into "a
   list of things the model said".
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _extra in (_HERE, _ROOT, _ROOT / "bench"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import ledger as ledger_module  # noqa: E402
import schema_validator as sv  # noqa: E402

#: Phase order, matching the states in core/state_machine.json (except BLOCKED).
PHASES = ["DISCOVER", "EVIDENCE", "STRATEGY", "ECONOMICS", "EXECUTION", "REVIEW"]

#: Which roles each phase needs. An empty list means that phase is framed by the
#: master agent alone.
PHASE_ROLES = {
    "DISCOVER": [],
    "EVIDENCE": ["customer_evidence", "market_structure"],
    "STRATEGY": ["positioning_strategy", "red_team"],
    "ECONOMICS": ["business_model"],
    "EXECUTION": ["growth_system", "measurement_experiment"],
    "REVIEW": ["learning_review"],
}

ROLE_LABELS = {
    "master_agent": "Master Agent (orchestration and gates)",
    "customer_evidence": "Customer Evidence Agent",
    "market_structure": "Market Structure Agent",
    "positioning_strategy": "Positioning and Strategy Agent",
    "business_model": "Business Model Agent",
    "growth_system": "Growth System Agent",
    "measurement_experiment": "Measurement and Experiment Agent",
    "red_team": "Red Team Agent",
    "learning_review": "Learning Review Agent",
}

#: Maximum characters injected per document into a task packet. With a lot of
#: material it is truncated at this point, and the packet says so.
DOCUMENT_EXCERPT_CHARS = 4000

#: Maximum number of evidence records injected into a task packet.
DEFAULT_MAX_EVIDENCE = 60


class OrchestratorError(Exception):
    """An expected error during orchestration; its message faces the user."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state_machine() -> dict:
    return json.loads((_HERE / "state_machine.json").read_text(encoding="utf-8"))


def load_role_contract(role: str) -> str:
    path = _ROOT / "agents" / f"{role}.md"
    if not path.exists():
        raise OrchestratorError(f"role contract not found: {path}")
    return path.read_text(encoding="utf-8")


def load_project(project_dir) -> dict:
    path = Path(project_dir) / "project.json"
    if not path.exists():
        raise OrchestratorError(f"project file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    project_dir: Path
    provider_name: str = "manual"
    phases: list = field(default_factory=lambda: list(PHASES))
    dry_run: bool = False
    max_evidence: int = DEFAULT_MAX_EVIDENCE
    max_documents: int = 10
    temperature: float = 0.3
    max_tokens: int = 4096
    # Pricing parameters. **No price is built in, deliberately** — prices change,
    # and hard-coding one turns it into a number that quietly goes stale. Token
    # counts are recorded faithfully; cost is computed only when the user gives a
    # unit price.
    price_input_per_million: float = None
    price_output_per_million: float = None
    currency: str = "USD"

    def __post_init__(self):
        self.project_dir = Path(self.project_dir)
        unknown = [p for p in self.phases if p not in PHASES]
        if unknown:
            raise OrchestratorError(
                f"unknown phase: {unknown}. Available phases: {PHASES}"
            )


# ---------------------------------------------------------------------------
# Context collection
# ---------------------------------------------------------------------------

def collect_context(project_dir, max_evidence=DEFAULT_MAX_EVIDENCE,
                    max_documents=10) -> dict:
    """Collect project state, the evidence ledger and source material for the
    task packets."""
    project_dir = Path(project_dir)
    project = load_project(project_dir)

    ledger = ledger_module.Ledger(project_dir)
    evidence = ledger.load()
    truncated = False
    if len(evidence) > max_evidence:
        evidence = evidence[:max_evidence]
        truncated = True

    documents = []
    index_path = project_dir / "sources" / "index.jsonl"
    if index_path.exists():
        # imported lazily, to avoid a hard dependency when there is no sources layer
        from sources import DocumentStore

        store = DocumentStore(project_dir)
        for entry in store.list()[:max_documents]:
            try:
                document = store.get(entry["doc_id"])
            except Exception:  # noqa: BLE001 - one corrupt document must not halt orchestration
                continue
            excerpt = document.content[:DOCUMENT_EXCERPT_CHARS]
            documents.append({
                "doc_id": document.doc_id,
                "origin": document.origin,
                "media_type": document.media_type,
                "sha256": document.sha256[:12],
                "chars": len(document.content),
                "truncated": len(document.content) > DOCUMENT_EXCERPT_CHARS,
                "excerpt": excerpt,
                "meta": document.meta,
            })

    return {
        "project": project,
        "evidence": evidence,
        "evidence_truncated": truncated,
        "evidence_total": len(ledger.load()),
        "documents": documents,
    }


# ---------------------------------------------------------------------------
# Task packets
# ---------------------------------------------------------------------------

def build_task_packet(role: str, phase: str, context: dict) -> str:
    """Assemble a task packet as the master agent contract requires: goal,
    inputs, outputs, evidence requirements, acceptance criteria."""
    project = context["project"]
    label = ROLE_LABELS.get(role, role)

    lines = [
        f"# Task packet — {label} (phase {phase})",
        "",
        "## 1. Role contract",
        "",
        load_role_contract(role),
        "",
        "## 2. Project context",
        "",
        f"- **Decision question**: {project.get('decision_question', '(not filled in)')}",
        f"- **Current phase**: {project.get('current_state', '(not filled in)')}",
        f"- **Decision deadline**: {project.get('decision_deadline') or '(not set)'}",
        f"- **Goals**: {'; '.join(project.get('goals') or []) or '(not filled in)'}",
        f"- **Constraints**: {'; '.join(project.get('constraints') or []) or '(not filled in)'}",
        "",
    ]

    known_facts = project.get("known_facts") or []
    if known_facts:
        lines += ["**Known facts the project claims (not verified by the ledger; do not treat them as verified evidence)**", ""]
        lines += [f"- {fact}" for fact in known_facts]
        lines += [""]

    assumptions = project.get("assumptions") or []
    unknowns = project.get("unknowns") or []
    if assumptions or unknowns:
        lines += ["**Assumptions awaiting verification and unknowns**", ""]
        lines += [f"- Assumption: {item}" for item in assumptions]
        lines += [f"- Unknown: {item}" for item in unknowns]
        lines += [""]

    lines += ["## 3. Evidence ledger", ""]
    if context["evidence"]:
        lines += [
            "| ID | Type | Confidence | Claim | Source | Scope | Decision it would change |",
            "|---|---|---|---|---|---|---|",
        ]
        for record in context["evidence"]:
            def cell(value):
                text = str(value if value is not None else "")
                return text.replace("|", "\\|").replace("\n", " ")

            lines.append(
                "| {id} | {type} | {conf} | {claim} | {src} | {scope} | {impact} |".format(
                    id=cell(record.get("id")), type=cell(record.get("type")),
                    conf=cell(record.get("confidence")), claim=cell(record.get("claim")),
                    src=cell(record.get("source") or "(not provided)"),
                    scope=cell(record.get("scope")),
                    impact=cell(record.get("decision_impact")),
                )
            )
        lines += [""]
        if context.get("evidence_truncated"):
            lines += [
                f"> Note: the ledger holds {context['evidence_total']} records; only "
                f"the first {len(context['evidence'])} are injected here, "
                f"**the rest are not shown**.",
                "",
            ]
    else:
        lines += [
            "**The evidence ledger is empty.** This means the project currently has no verified evidence at all.",
            "Your conclusions must be degraded accordingly: mark key judgements as UNKNOWN and give a path to further evidence;",
            "you must not pretend to know the facts.",
            "",
        ]

    lines += ["## 4. Source material", ""]
    if context["documents"]:
        for document in context["documents"]:
            lines += [
                f"### {document['doc_id']} — {document['origin']}",
                "",
                f"- Type: {document['media_type']}　characters: {document['chars']}"
                f"　fingerprint: {document['sha256']}",
            ]
            if document.get("meta"):
                meta_bits = {
                    k: v for k, v in document["meta"].items()
                    if k in ("rows", "columns", "records", "encoding", "status", "sheet")
                }
                if meta_bits:
                    lines.append(f"- Overview: {json.dumps(meta_bits, ensure_ascii=False)}")
            if document["truncated"]:
                lines.append(
                    f"- ⚠️ Only the first {DOCUMENT_EXCERPT_CHARS} characters are "
                    f"shown; **the rest is not displayed**"
                )
            lines += ["", "```text", document["excerpt"], "```", ""]
    else:
        lines += ["(no source material has been imported for this project yet)", ""]

    lines += [
        "## 5. What you must output",
        "",
        "Output in Markdown, strictly in this order:",
        "",
        "1. **Conclusion summary** — no more than 5 items",
        "2. **Evidence table** — claim / type / source or basis / confidence / limitations",
        "3. **Key assumptions and unknowns**",
        "4. **Impact on the main decision** — supports, opposes, or cannot yet be judged",
        "5. **Executable next-step validation** — for each item, write the validation method and the stop condition",
        "",
        "## 6. Evidence requirements",
        "",
        "- Label every claim with one of `FACT` / `INFERENCE` / `ASSUMPTION` / `UNKNOWN`.",
        "- When citing evidence from the ledger, write its id (e.g. `E-003`).",
        "- `FACT` must be verifiable; if it is not, downgrade it to `INFERENCE` or `ASSUMPTION`.",
        "- Label confidence `HIGH` / `MEDIUM` / `LOW`, and give the reason.",
        "",
        "## 7. Prohibited",
        "",
        "- Do not fabricate data, interviews, sources, competitor information or experiment results.",
        "- Do not treat example numbers or industry averages as real data.",
        "- Do not pad the output with unverifiable conclusions such as \"we suggest content marketing\" or \"improve the conversion rate\".",
        "- Do not answer out of scope for questions that belong to other roles (see the input boundary in the role contract).",
        "",
        "## 8. Acceptance criteria",
        "",
        "- Every conclusion can be traced to ledger evidence, to source material, or is explicitly marked as an assumption.",
        "- When those requirements are not met, state plainly \"what data is needed to judge\", rather than offering a guess.",
        "",
    ]
    return "\n".join(lines)


#: Each phase has its **own, different** gate criteria, taken directly from
#: core/REBUILD_METHOD.md.
#:
#: This used to be written wrongly: an early version applied the same "is the
#: evidence sufficient" criterion to every phase, so DISCOVER could never pass —
#: the R phase by definition happens before further evidence is gathered, and it
#: asks whether the problem is clearly defined, not whether the evidence is
#: enough. A real model run exposed the defect; the unit tests never caught it.
PHASE_GATES = {
    "DISCOVER": {
        "title": "R — Define reality",
        "criteria": [
            "Business goals and the observed symptoms are written **separately**; conflating the two fails the gate.",
            "A missing baseline must be marked as unknown; **do not fabricate a baseline** — as long as the unknown is marked honestly, this phase passes.",
            "State clearly \"what really needs deciding now\", the decision deadline and the constraints.",
        ],
        "note": "This phase **does not require sufficient evidence**. It happens before "
                "further evidence is gathered and asks for quality of problem definition. "
                "Listing the unknowns honestly is a pass.",
    },
    "EVIDENCE": {
        "title": "E — Build evidence",
        "criteria": [
            "Key conclusions must be traceable — point to a source, or state explicitly that there is none.",
            "An inference must not disguise itself as a fact (`INFERENCE` must not be written as `FACT`).",
            "Unknowns must be given a **path to further evidence**, not left blank.",
        ],
        "note": "This phase does not require every unknown to be eliminated; it requires "
                "knowing what you do not know.",
    },
    "STRATEGY": {
        "title": "B — Strategic bet",
        "criteria": [
            "It must be able to answer \"why A rather than B\".",
            "The options must differ **substantively**; if they are essentially the same, go back and rebuild.",
            "Write out the rejected options and the trade-offs.",
        ],
        "note": "The failure mode of this phase is \"options were given but the options "
                "are not different\", not \"not enough evidence\".",
    },
    "ECONOMICS": {
        "title": "U — Commercial viability",
        "criteria": [
            "Key financial metrics must state the formula, the numerator and denominator, the time range and the data source.",
            "When data is missing, output a **range or an assumption to be verified**; do not give a single precise value.",
            "Do not confuse revenue / gross margin / contribution profit / ROAS.",
        ],
        "note": "This phase allows advancing on assumptions — as long as every assumption "
                "is labelled and given a range. \"Incomplete data\" is not in itself a reason "
                "to block; \"hiding incomplete data behind a point estimate\" is.",
    },
    "EXECUTION": {
        "title": "I — Execution and observation",
        "criteria": [
            "An action without a measurement design **must not be called an experiment**.",
            "Every action is bound to an owner, a cost, a deadline, a leading indicator, a result metric and a stop condition.",
        ],
        "note": "The failure mode of this phase is \"writing actions as wishes\".",
    },
    "REVIEW": {
        "title": "D — Decision review",
        "criteria": [
            "A review must not merely say \"the results were good\".",
            "It must compare **expectation and actuals**, and separate execution failure, strategy failure and assumption failure.",
            "Record how the next step changes.",
        ],
        "note": "The failure mode of this phase is \"replacing data with impressions\". "
                "When there is no data, write \"no data collected\".",
    },
}


def build_gate_packet(phase: str, context: dict, outputs: dict) -> str:
    """Ask the master agent to judge the phase gate."""
    machine = load_state_machine()
    transitions = machine["transitions"].get(phase, {})
    gate = PHASE_GATES.get(phase, {"title": phase, "criteria": [], "note": ""})

    lines = [
        f"# Gate judgement — phase {phase} ({gate['title']})",
        "",
        "You are the REBUILD master agent. Below are this phase's role outputs. "
        "Judge whether the phase gate passes,",
        "and choose a transition event.",
        "",
        "## Events available in this phase",
        "",
    ]
    for event, target in transitions.items():
        lines.append(f"- `{event}` → {target}")
    lines += [
        "",
        f"## Gate criteria for this phase ({gate['title']}, from core/REBUILD_METHOD.md)",
        "",
    ]
    lines += [f"{i}. {c}" for i, c in enumerate(gate["criteria"], 1)]
    if gate["note"]:
        lines += ["", f"> **Note**: {gate['note']}"]
    lines += [
        "",
        "**Judge only by this phase's criteria.** Do not use another phase's criteria — "
        "every phase asks for something different,",
        "and applying a later phase's criteria to an earlier one means the flow can never advance.",
        "",
        "## Current state of the evidence ledger",
        "",
        f"- The ledger holds {context['evidence_total']} records.",
        f"- Source material: {len(context['documents'])} documents.",
        "",
        "## Role outputs for this phase",
        "",
    ]
    for role, text in outputs.items():
        lines += [f"### {ROLE_LABELS.get(role, role)}", "", text.strip(), ""]

    lines += [
        "## Your output format",
        "",
        "Output a single JSON object and nothing else:",
        "",
        "```json",
        "{",
        '  "event": "one of the event names in the list above",',
        '  "passed": true or false,',
        '  "evidence_grade": "SUFFICIENT | DEGRADED | INSUFFICIENT",',
        '  "reason": "why you judged so; cite specific output content",',
        '  "limitations": ["if this is a degraded pass, state item by item where this conclusion does not hold or is unverified"],',
        '  "blocking_gaps": ["specific items that are still missing and must be backed by further evidence"]',
        "}",
        "```",
        "",
        "## Three legal outcomes (choose one; do not default to the most conservative)",
        "",
        "**① `SUFFICIENT` — pass.** The evidence is enough to support this phase's conclusions; advance normally.",
        "",
        "**② `DEGRADED` — degraded pass.** The evidence is incomplete, but **the decision itself can still be made**, provided that:",
        "   - `limitations` states item by item which conclusions do not hold, which are assumptions, and which are untested;",
        "   - conclusions are worded down to the strength of the evidence (\"holds provided assumption X holds\", not \"holds\");",
        "   - `blocking_gaps` lists what must be completed before the next phase.",
        "   The methodology explicitly allows \"stay, gather further evidence, or **degrade the output**\". A real project can almost never wait for complete evidence before deciding,",
        "   so a degraded pass is often the right choice — as long as the limitations are written down, not hidden.",
        "",
        "**③ `INSUFFICIENT` — roll back or ask for clarification.** Applies when the decision **simply cannot be made**,",
        "   not merely when the evidence is not pretty enough. For example: an unchecked P0 veto item (if it hits, it overturns every conclusion),",
        "   key clauses whose definitions conflict and cannot be adjudicated, or data that only the decision maker can supply.",
        "",
        "**Key points for judging:**",
        "",
        "- The most serious failure of this system is **not** \"advancing with incomplete evidence\",",
        "  but **\"pretending the evidence is complete while advancing\"**. The former is handled by `limitations`; the latter is unacceptable.",
        "- If you find yourself listing many gaps yet can still write a conditional conclusion — choose `DEGRADED`,",
        "  not `INSUFFICIENT`.",
        "- Choose `INSUFFICIENT` only when **a veto item is unchecked**, or **missing information would reverse the direction of the conclusion**.",
        "- Do not block merely because it is \"not perfect yet\". The cost of blocking is that the decision is postponed indefinitely, which is itself a loss.",
        "",
    ]
    return "\n".join(lines)


def build_decision_record_packet(context: dict, phase_outputs: dict) -> str:
    lines = [
        "# Decision record",
        "",
        "Synthesise the role outputs from every phase into one decision record.",
        "",
        f"Decision question: {context['project'].get('decision_question')}",
        "",
        "## Summary of outputs by phase",
        "",
    ]
    for phase, outputs in phase_outputs.items():
        for role, text in outputs.items():
            lines += [f"### [{phase}] {ROLE_LABELS.get(role, role)}", "", text.strip(), ""]

    lines += [
        "## Output format",
        "",
        "Output a single JSON object whose fields match schemas/decision_record.schema.json:",
        "",
        "```json",
        "{",
        '  "decision_id": "DR-001",',
        '  "question": "...",',
        '  "deadline": null,',
        '  "options": [{"name": "...", "rationale": "...", "risks": ["..."]}],',
        '  "chosen_option": "name of the option adopted, or null",',
        '  "rejected_options": [{"name": "...", "reason": "..."}],',
        '  "tradeoffs": ["..."],',
        '  "key_assumptions": ["..."],',
        '  "falsification_conditions": ["..."],',
        '  "validation_actions": ["..."],',
        '  "review_date": "YYYY-MM-DD"',
        "}",
        "```",
        "",
        "Hard requirements: `options` must number at least 2 and must differ substantively; the rejected options and the trade-offs must be written out;",
        "every key assumption must be paired with a condition that could overturn it.",
        "",
        "**About `chosen_option`:** if this round's conclusion is \"gather further evidence before deciding\", "
        "write it as `null` — that is the **correct** value; do not invent an option just to fill the field.",
        "In that case `validation_actions` must state what evidence is needed before a decision can be made.",
        "Inventing an option you do not actually recommend is far more serious than leaving it null.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def extract_json_block(text: str):
    """Pull the first JSON object out of the model output. Returns None if there
    is none."""
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        stripped = "\n".join(lines)
    start = stripped.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(stripped[start:index + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    def __init__(self, config: RunConfig, completer=None, run_label=None):
        self.config = config
        self.project_dir = config.project_dir
        self._completer = completer
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        if run_label:
            # Repeated runs are told apart by a suffix, otherwise several runs
            # within the same second would write into the same directory
            self.run_id = f"{self.run_id}-{run_label}"
        self.run_dir = self.project_dir / "runs" / self.run_id
        self.state_machine = load_state_machine()
        self.log: list[str] = []
        #: Usage and elapsed time of each model call. When usage cannot be read
        #: it is recorded as available=False, never estimated.
        self.usage_log: list[dict] = []

    # -------------------------------------------------------------- provider
    def _resolve_provider(self):
        """Load and validate the provider configuration. An unknown name must
        fail **early**.

        Previously an unknown provider failed once in every role call and was
        recorded as a string of "role failures" — the user saw six roles down,
        rather than "you misspelled the provider name". The former sends people
        off to check the network; the latter is the real cause.
        """
        try:
            import provider as provider_layer  # bench/provider.py
        except ImportError as exc:
            raise OrchestratorError(f"cannot load bench/provider.py: {exc}") from exc
        try:
            config = provider_layer.ProviderConfig.from_preset(self.config.provider_name)
        except ValueError as exc:
            raise OrchestratorError(str(exc)) from exc
        config.temperature = self.config.temperature
        config.max_tokens = self.config.max_tokens
        ok, message = provider_layer.check_available(config)
        if not ok:
            raise OrchestratorError(f"provider configuration is unusable: {message}")
        return provider_layer, config

    def _complete(self, prompt: str, label: str = "", phase: str = "") -> str:
        started = time.monotonic()
        if self._completer is not None:
            text = self._completer(prompt)
            self._record_usage(label, phase, None, time.monotonic() - started)
            return text
        if self.config.provider_name == "manual":
            raise OrchestratorError(
                "manual mode does not call a model. Use `--provider <name>` to pick "
                "one, or use `--dry-run` to generate task packets only."
            )
        provider_layer, config = self._resolve_provider()
        text, usage = provider_layer.complete_with_usage(config, prompt)
        self._record_usage(label, phase, usage, time.monotonic() - started)
        return text

    def _record_usage(self, label, phase, usage, seconds):
        entry = {"label": label, "phase": phase,
                 "seconds": round(seconds, 2)}
        if usage is None:
            entry.update({"available": False, "reason": "the caller supplied no usage (fake model)"})
        else:
            entry.update(usage)
        self.usage_log.append(entry)

    # ----------------------------------------------------------- persistence
    def _write(self, relative: str, text: str) -> Path:
        path = self.run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _note(self, message: str):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    # ------------------------------------------------------------- main flow
    def run(self) -> dict:
        context = collect_context(
            self.project_dir,
            max_evidence=self.config.max_evidence,
            max_documents=self.config.max_documents,
        )
        current_state = context["project"].get("current_state")
        if current_state not in PHASES and current_state != "BLOCKED":
            raise OrchestratorError(f"illegal project state: {current_state}")

        manual = self.config.provider_name == "manual" and self._completer is None

        # Fail early: a misspelled provider name or a missing key should surface
        # before any artefact is written, not after six roles each fail once.
        if not self.config.dry_run and not manual and self._completer is None:
            self._resolve_provider()

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._note(f"run_id={self.run_id} provider={self.config.provider_name} "
                   f"dry_run={self.config.dry_run}")

        report = {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "provider": self.config.provider_name,
            "mode": "dry-run" if self.config.dry_run else (
                "manual" if manual else "model"
            ),
            "initial_state": current_state,
            "phases": [],
            "gate_rejections": [],
            "evidence_total": context["evidence_total"],
            "documents": len(context["documents"]),
        }

        phase_outputs = {}
        state = current_state

        for phase in self.config.phases:
            if phase != state and not self.config.dry_run:
                self._note(f"skipping {phase} (current state is {state})")
                report["phases"].append({"phase": phase, "skipped": True,
                                         "reason": f"current state is {state}"})
                continue

            result = self._run_phase(phase, context, manual)
            report["phases"].append(result)
            if result.get("role_outputs"):
                phase_outputs[phase] = result["role_outputs"]

            if self.config.dry_run:
                continue

            gate = self._run_gate(phase, context, result.get("role_outputs") or {})
            result["gate"] = gate

            if gate.get("event"):
                try:
                    transition = self._apply_transition(
                        state, gate["event"], gate.get("reason", "")
                    )
                except OrchestratorError as exc:
                    self._note(f"rejecting illegal transition: {exc}")
                    report["gate_rejections"].append({
                        "phase": phase,
                        "event": gate["event"],
                        "error": str(exc),
                    })
                    state = "BLOCKED"
                    break
                result["transition"] = transition
                state = transition["to"]
                self._persist_state(state)
                self._note(f"{phase} + {gate['event']} → {state}")
            if state == "BLOCKED":
                self._note(f"phase {phase} judged to need clarification; orchestration stops")
                break

        if not self.config.dry_run and phase_outputs and not manual:
            record = self._produce_decision_record(context, phase_outputs)
            report["decision_record"] = record

        ran = [p for p in report["phases"] if not p.get("skipped")]
        if not ran and not self.config.dry_run:
            report["hint"] = self._skip_hint(current_state)
            self._note(report["hint"])

        report["final_state"] = state
        report["usage"] = summarize_usage(self.usage_log)
        report["usage_log"] = self.usage_log
        cost = estimate_cost(report["usage"], self.config)
        if cost is not None:
            report["cost_estimate"] = cost
        report["log"] = self.log
        self._write("run.json", json.dumps(report, ensure_ascii=False, indent=2))
        return report

    # ---------------------------------------------------------- single phase
    def _run_phase(self, phase: str, context: dict, manual: bool) -> dict:
        roles = PHASE_ROLES.get(phase, [])
        result = {"phase": phase, "roles": roles, "role_outputs": {}, "packets": []}

        for role in roles:
            packet = build_task_packet(role, phase, context)
            packet_path = self._write(f"{phase}/{role}.packet.md", packet)
            result["packets"].append(str(packet_path.relative_to(self.run_dir)))

            if self.config.dry_run or manual:
                continue

            try:
                output = self._complete(packet, label=role, phase=phase)
            except OrchestratorError:
                raise
            except Exception as exc:  # noqa: BLE001 - one role failing must not lose the other artefacts
                self._note(f"role {role} call failed: {exc}")
                result["role_outputs"][role] = ""
                result.setdefault("errors", []).append({"role": role, "error": str(exc)})
                continue

            self._write(f"{phase}/{role}.md", output)
            result["role_outputs"][role] = output
            self._note(f"{phase}/{role} done ({len(output)} characters)")

        if phase == "DISCOVER" and not (self.config.dry_run or manual):
            # DISCOVER has no specialist role; the master agent defines the
            # problem itself
            packet = build_task_packet("master_agent", phase, context)
            self._write(f"{phase}/master_agent.packet.md", packet)
            try:
                output = self._complete(packet, label="master_agent", phase=phase)
                self._write(f"{phase}/master_agent.md", output)
                result["role_outputs"]["master_agent"] = output
            except Exception as exc:  # noqa: BLE001
                result.setdefault("errors", []).append(
                    {"role": "master_agent", "error": str(exc)}
                )

        return result

    # ----------------------------------------------------------------- gates
    def _run_gate(self, phase: str, context: dict, outputs: dict) -> dict:
        # When every role call failed, role_outputs holds a string of empty
        # strings — the dict itself is still truthy. Without a content check the
        # orchestrator would call the model again with empty input, wasting a
        # call.
        if not outputs or not any(str(v).strip() for v in outputs.values()):
            return {"event": None, "passed": False,
                    "reason": "this phase produced no valid role output, so the gate "
                              "cannot be judged — all role calls may have failed, see "
                              "the errors field"}

        packet = build_gate_packet(phase, context, outputs)
        self._write(f"{phase}/gate.packet.md", packet)
        try:
            raw = self._complete(packet, label="gate", phase=phase)
        except Exception as exc:  # noqa: BLE001
            self._note(f"gate judgement call failed: {exc}")
            return {"event": None, "passed": False, "reason": f"gate judgement failed: {exc}"}

        self._write(f"{phase}/gate.raw.md", raw)
        verdict = extract_json_block(raw)
        if not isinstance(verdict, dict):
            self._note(f"{phase} gate output cannot be parsed as JSON; treated as not passing")
            return {"event": None, "passed": False,
                    "reason": "the gate output cannot be parsed as JSON; treated as not passing"}
        verdict.setdefault("passed", False)
        return verdict

    def _apply_transition(self, state: str, event: str, reason: str = "") -> dict:
        transitions = self.state_machine["transitions"].get(state, {})
        if event not in transitions:
            raise OrchestratorError(
                f"state {state} does not accept event '{event}'. "
                f"Legal events: {sorted(transitions)}"
            )
        return {"from": state, "event": event, "to": transitions[event],
                "reason": reason}

    def _skip_hint(self, state: str) -> str:
        """When every requested phase was skipped, give an **actionable**
        explanation.

        BLOCKED is a special case: it is not in PHASES, and previously produced
        "available sequence: []", which is no help to the user at all — and it is
        precisely the state that most needs guidance. The problem surfaced in a
        real run, not in the unit tests.
        """
        if state == "BLOCKED":
            exits = sorted(self.state_machine["transitions"].get("BLOCKED", {}))
            return (
                "The project is currently BLOCKED (awaiting clarification), so no "
                "phase is executed. BLOCKED is not part of the phase sequence: the "
                f"block must be lifted first by firing one of {exits} before the "
                "project can return to DISCOVER and start again. If the block came "
                "from a gate judging the evidence insufficient, gather the evidence "
                "first and then change current_state in project.json."
            )
        if state not in PHASES:
            return f"the project's current state {state} is not in the phase sequence, so nothing can be executed."
        remaining = PHASES[PHASES.index(state):]
        return (
            f"every requested phase was skipped: the project's current state is "
            f"{state}, so execution can only continue in order from that phase. "
            f"Available sequence: {remaining}"
        )

    def _persist_state(self, state: str):
        path = self.project_dir / "project.json"
        project = json.loads(path.read_text(encoding="utf-8"))
        project["current_state"] = state
        project["last_updated"] = _now()
        path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # --------------------------------------------------------- decision record
    def _produce_decision_record(self, context: dict, phase_outputs: dict) -> dict:
        packet = build_decision_record_packet(context, phase_outputs)
        self._write("decision_record.packet.md", packet)
        try:
            raw = self._complete(packet, label="decision_record")
        except Exception as exc:  # noqa: BLE001
            self._note(f"decision record generation failed: {exc}")
            return {"error": str(exc)}
        self._write("decision_record.raw.md", raw)

        record = extract_json_block(raw)
        if not isinstance(record, dict):
            return {"error": "the model output cannot be parsed as JSON; see decision_record.raw.md for the raw output"}

        errors, warnings = sv.validate(
            record, sv.load_schema(_ROOT / "schemas" / "decision_record.schema.json")
        )
        self._write("decision_record.json",
                    json.dumps(record, ensure_ascii=False, indent=2))
        result = {"record": record, "schema_errors": errors, "schema_warnings": warnings}
        if errors:
            self._note(f"decision record does not conform to the schema: {len(errors)} errors")
        return result


# ---------------------------------------------------------------------------
# Usage and cost
# ---------------------------------------------------------------------------

def summarize_usage(usage_log) -> dict:
    """Summarise model call usage.

    **Only numbers actually obtained are summed; never estimate.** Calls whose
    usage could not be read are counted separately, and the note says the total
    is incomplete — an estimated token count written into the report as real
    usage is worse than having no number at all.
    """
    total_prompt = total_completion = 0
    have_prompt = have_completion = False
    measured = 0
    seconds = 0.0
    by_phase: dict = {}

    for entry in usage_log:
        seconds += entry.get("seconds") or 0
        phase = entry.get("phase") or "(unlabelled)"
        bucket = by_phase.setdefault(
            phase, {"calls": 0, "measured": 0, "total_tokens": 0}
        )
        bucket["calls"] += 1
        if not entry.get("available"):
            continue
        measured += 1
        bucket["measured"] += 1
        prompt = entry.get("prompt_tokens")
        completion = entry.get("completion_tokens")
        if isinstance(prompt, int):
            total_prompt += prompt
            have_prompt = True
        if isinstance(completion, int):
            total_completion += completion
            have_completion = True
        if isinstance(entry.get("total_tokens"), int):
            bucket["total_tokens"] += entry["total_tokens"]

    complete = have_prompt and have_completion
    summary = {
        "calls": len(usage_log),
        "calls_with_usage": measured,
        "prompt_tokens": total_prompt if have_prompt else None,
        "completion_tokens": total_completion if have_completion else None,
        "total_tokens": (total_prompt + total_completion) if complete else None,
        "seconds": round(seconds, 1),
        "by_phase": by_phase,
    }
    if measured < len(usage_log):
        summary["note"] = (
            f"token usage was not obtained for {len(usage_log) - measured} calls, "
            f"so the total token count is **incomplete** and must not be taken as "
            f"actual consumption."
        )
    return summary


def estimate_cost(usage_summary: dict, config) -> dict | None:
    """Estimate cost from the **unit price the user supplies**.

    Returns None when no unit price was given — this project builds in no
    prices. Prices change, and writing a number that will expire into the code
    is manufacturing a conclusion that quietly drifts out of date.
    """
    if (config.price_input_per_million is None
            or config.price_output_per_million is None):
        return None
    if not usage_summary.get("calls_with_usage"):
        return None

    prompt = usage_summary.get("prompt_tokens") or 0
    completion = usage_summary.get("completion_tokens") or 0
    input_cost = prompt / 1_000_000 * config.price_input_per_million
    output_cost = completion / 1_000_000 * config.price_output_per_million

    return {
        "currency": config.currency,
        "input": round(input_cost, 6),
        "output": round(output_cost, 6),
        "total": round(input_cost + output_cost, 6),
        "pricing_used": {
            "input_per_million": config.price_input_per_million,
            "output_per_million": config.price_output_per_million,
        },
        "caveat": (
            "This is an estimate computed from the **unit price the user supplied**; "
            "it is not a bill amount. It excludes cache-hit discounts and volume "
            "discounts, and does not deduct the double billing of failed retries."
        ),
        "incomplete": usage_summary.get("calls_with_usage", 0)
                      < usage_summary.get("calls", 0),
    }


def run_repeated(config: RunConfig, repeats: int, completer=None):
    """Run the same input N times, to observe consistency across runs.

    The project state is **reset to its initial value** before each run —
    otherwise the second run would start from the first run's final state, which
    is not "the same input". After all runs it is restored to the initial value
    too, so that the act of "repeated running" does not itself change the
    project.
    """
    if repeats < 1:
        raise OrchestratorError("repeats must be at least 1")

    project_path = Path(config.project_dir) / "project.json"
    if not project_path.exists():
        raise OrchestratorError(f"project file not found: {project_path}")

    def read_state():
        return json.loads(project_path.read_text(encoding="utf-8")).get("current_state")

    def write_state(state):
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["current_state"] = state
        project_path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    original_state = read_state()
    reports = []
    try:
        for index in range(1, repeats + 1):
            write_state(original_state)
            orchestrator = Orchestrator(config, completer=completer,
                                        run_label=f"r{index}")
            reports.append(orchestrator.run())
    finally:
        write_state(original_state)
    return reports


# ---------------------------------------------------------------------------
# Proposed evidence (human review; never booked automatically)
# ---------------------------------------------------------------------------

def collect_proposed_evidence(run_dir) -> list[dict]:
    """Extract the evidence items a model suggested from the role outputs, for
    **human review**.

    The returned items are never written into the evidence ledger
    automatically. Model output is not evidence — automatic booking would
    degrade the ledger into "a list of things the model said".
    """
    run_dir = Path(run_dir)
    proposals = []
    for path in sorted(run_dir.rglob("*.md")):
        if path.name.endswith((".packet.md", ".raw.md")):
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.startswith("|---"):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 3:
                continue
            if cells[0].lower() in ("主张", "claim", "id"):
                continue
            proposals.append({
                "from": str(path.relative_to(run_dir)),
                "claim": cells[0][:300],
                "cells": cells[:8],
            })
    return proposals
