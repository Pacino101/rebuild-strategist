#!/usr/bin/env python3
"""Comparison across multiple runs.

Why it is needed
----------------
Measured with the same input, the same evidence and **temperature=0**, three
runs produced outputs pointing the same way but differing in detail by a factor
of 2.5 (6/10/15 falsification conditions). So **the output of a single run is
not "the answer", only a starting point**.

This module turns "run it a few times and see whether it is stable" from a
manual chore into a usable tool.

Two kinds of conclusion must be kept apart, never conflated
-----------------------------------------------------------
1. **Process reproducibility** (computed deterministically by this module):
   final state, transition path, gate grade, item counts. These are directly
   comparable.
2. **Whether the conclusions agree** (needs a model judgement): whether the
   several recommendations point in the **same direction**. That is free text
   and mechanical comparison cannot do it. Judge it separately with
   `judge_agreement()`, and label it explicitly as a model judgement, not a
   fact.

Presenting the first kind as the second is the easiest mistake for a tool like
this to make — "the same path" does not equal "the same recommendation".
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _extra in (_HERE, _HERE.parent, _HERE.parent / "bench"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from orchestrator import extract_json_block  # noqa: E402

#: The paths are exactly identical
PATH_IDENTICAL = "PATH_IDENTICAL"
#: Same final state but different paths
OUTCOME_IDENTICAL = "OUTCOME_IDENTICAL"
#: The final states themselves differ
OUTCOME_DIVERGENT = "OUTCOME_DIVERGENT"


class CompareError(Exception):
    """The comparison cannot proceed."""


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_run(run_dir) -> dict:
    path = Path(run_dir) / "run.json"
    if not path.exists():
        raise CompareError(f"{run_dir} is not a run artefact (run.json is missing)")
    return json.loads(path.read_text(encoding="utf-8"))


def collect_runs(project_dir, last=None) -> list[dict]:
    """Collect the run artefacts under a project, ascending by run_id. `last`
    takes only the most recent N."""
    runs_root = Path(project_dir) / "runs"
    if not runs_root.is_dir():
        raise CompareError(
            f"{runs_root} does not exist. Use `run` to produce at least two runs first."
        )
    dirs = sorted(d for d in runs_root.iterdir() if (d / "run.json").exists())
    if not dirs:
        raise CompareError(f"{runs_root} holds no run artefacts to compare")
    if last:
        dirs = dirs[-last:]
    return [load_run(d) for d in dirs]


# ---------------------------------------------------------------------------
# Extract comparable fields
# ---------------------------------------------------------------------------

def _path_of(report) -> list:
    """Transition path: a sequence of (phase, event, target state). Skipped
    phases are skipped."""
    path = []
    for phase in report.get("phases", []):
        if phase.get("skipped"):
            continue
        transition = phase.get("transition") or {}
        path.append((
            phase.get("phase"),
            transition.get("event"),
            transition.get("to"),
        ))
    return path


def _grades_of(report) -> dict:
    grades = {}
    for phase in report.get("phases", []):
        if phase.get("skipped"):
            continue
        gate = phase.get("gate") or {}
        grades[phase.get("phase")] = gate.get("evidence_grade") or "?"
    return grades


def _decision_of(report) -> dict:
    block = report.get("decision_record") or {}
    record = block.get("record") or {}
    return {
        "produced": bool(record),
        "error": block.get("error"),
        "schema_errors": len(block.get("schema_errors") or []),
        "chosen_option": record.get("chosen_option"),
        "options": len(record.get("options") or []),
        "rejected": len(record.get("rejected_options") or []),
        "falsification": len(record.get("falsification_conditions") or []),
        "validation": len(record.get("validation_actions") or []),
        "assumptions": len(record.get("key_assumptions") or []),
    }


def _usage_of(report) -> dict:
    usage = report.get("usage") or {}
    cost = report.get("cost_estimate") or {}
    return {
        "calls": usage.get("calls"),
        "calls_with_usage": usage.get("calls_with_usage"),
        "total_tokens": usage.get("total_tokens"),
        "seconds": usage.get("seconds"),
        "cost_total": cost.get("total"),
        "currency": cost.get("currency"),
        "note": usage.get("note"),
    }


def _spread(values):
    values = [v for v in values if isinstance(v, int)]
    if not values:
        return None
    return {"min": min(values), "max": max(values),
            "range": max(values) - min(values),
            "mean": round(sum(values) / len(values), 2)}


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(reports) -> dict:
    """Deterministic comparison. **Answers process reproducibility only; it does
    not answer whether the conclusions agree.**"""
    if len(reports) < 2:
        raise CompareError(f"at least 2 runs are needed to compare; currently {len(reports)}")

    paths = [_path_of(r) for r in reports]
    finals = [r.get("final_state") for r in reports]
    grades = [_grades_of(r) for r in reports]
    decisions = [_decision_of(r) for r in reports]

    if all(p == paths[0] for p in paths):
        verdict = PATH_IDENTICAL
    elif len(set(finals)) == 1:
        verdict = OUTCOME_IDENTICAL
    else:
        verdict = OUTCOME_DIVERGENT

    # Consistency of gate grades, phase by phase
    all_phases = []
    for report in reports:
        for phase in report.get("phases", []):
            if not phase.get("skipped") and phase.get("phase") not in all_phases:
                all_phases.append(phase.get("phase"))

    grade_table = {}
    for phase in all_phases:
        seen = Counter(g.get(phase, "(not executed)") for g in grades)
        grade_table[phase] = {
            "distribution": dict(seen),
            "consistent": len(seen) == 1,
        }

    chosen = [d["chosen_option"] for d in decisions]
    # "No decision record produced" and "produced but no choice was made this
    # run" are two different things and must be expressed separately, otherwise
    # "no conclusion came out" is misread as "the conclusion is not to decide".
    status = [
        "NOT_PRODUCED" if not d["produced"]
        else ("NULL_CHOICE" if d["chosen_option"] is None else "CHOSEN")
        for d in decisions
    ]
    counts = {
        key: _spread([d[key] for d in decisions])
        for key in ("options", "rejected", "falsification", "validation", "assumptions")
    }

    usages = [_usage_of(r) for r in reports]
    tokens = [u["total_tokens"] for u in usages if u["total_tokens"] is not None]
    costs = [u["cost_total"] for u in usages if u["cost_total"] is not None]
    seconds = [u["seconds"] for u in usages if u["seconds"] is not None]

    total_usage = {
        "calls": sum(u["calls"] or 0 for u in usages),
        "calls_with_usage": sum(u["calls_with_usage"] or 0 for u in usages),
        "total_tokens": sum(tokens) if len(tokens) == len(reports) else None,
        "tokens_incomplete": len(tokens) != len(reports),
        "seconds": round(sum(seconds), 1) if seconds else None,
        "cost_total": round(sum(costs), 6) if costs else None,
        "currency": usages[0]["currency"] if costs else None,
        "cost_note": (
            "the cost is estimated from the unit price the user supplied; it is not a bill amount."
            if costs else
            "no unit price was provided, so only tokens are counted and no cost is computed."
        ),
    }

    return {
        "runs": len(reports),
        "per_run_usage": usages,
        "total_usage": total_usage,
        "run_ids": [r.get("run_id") for r in reports],
        "process_verdict": verdict,
        "final_states": dict(Counter(finals)),
        "final_state_consistent": len(set(finals)) == 1,
        "paths": [
            " → ".join(f"{p[0]}:{p[1]}" for p in path) or "(no transitions)"
            for path in paths
        ],
        "path_consistent": all(p == paths[0] for p in paths),
        "gate_grades": grade_table,
        "decisions_produced": sum(1 for d in decisions if d["produced"]),
        "decision_errors": [d["error"] for d in decisions if d["error"]],
        "schema_error_runs": sum(1 for d in decisions if d["schema_errors"]),
        "counts": counts,
        "chosen_options": chosen,
        "decision_status": status,
        "caveat": (
            "Everything above is a **process** metric. \"The transition path is the "
            "same\" does not equal \"the recommendations are the same\" — whether the "
            "conclusions agree needs a model judgement; use judge_agreement()."
        ),
    }


# ---------------------------------------------------------------------------
# Agreement of conclusions (a model judgement, not a fact)
# ---------------------------------------------------------------------------

JUDGE_HEADER = """You are the reviewer. Below are N recommendations that the same system produced independently, for the same question and the same body of evidence.
Judge whether they agree in **direction** — that is, whether a decision maker following any one of them would end up on a different path.

Compare **direction** only (do it / do not do it / verify first / switch options ...). Do not call them inconsistent merely because the wording, the number of items or the level of detail differs.

## The recommendations from each run

"""

JUDGE_FOOTER = """

## Output format

Output a single JSON object:

```json
{
  "agree": true or false,
  "direction": "summarise in one sentence the shared direction of these recommendations; if they disagree, state which directions there are",
  "groups": [["the identifier of a run, e.g. r1"], ["r3"]],
  "why": "the reason for the judgement; cite specific wording",
  "confidence": "HIGH | MEDIUM | LOW"
}
```

`groups` groups runs that point in the same direction. If they all agree, there
is only one group. When unsure, mark `confidence` LOW; do not force a grouping
just to produce a conclusion.
"""


def build_judge_packet(reports) -> str:
    lines = [JUDGE_HEADER]
    for index, report in enumerate(reports, 1):
        decision = _decision_of(report)
        lines.append(f"### r{index} (run_id {report.get('run_id')})")
        lines.append("")
        if not decision["produced"]:
            lines.append(f"(no decision record produced: {decision['error'] or 'unknown reason'})")
        else:
            lines.append(f"**Choice**: {decision['chosen_option']}")
            record = (report.get("decision_record") or {}).get("record") or {}
            rejected = record.get("rejected_options") or []
            if rejected:
                lines.append("")
                lines.append("**Rejected**: " + "; ".join(
                    str(r.get("name")) for r in rejected[:4]
                ))
        lines.append("")
    lines.append(JUDGE_FOOTER)
    return "\n".join(lines)


def judge_agreement(reports, completions):
    """Use a model to judge whether N recommendations agree in direction.

    `completions` is a `callable(prompt) -> str` supplied by the caller — this
    module never touches the network itself, which makes it easy to test and to
    swap out.

    The returned verdict carries `judged_by_model: True`: it is a **model
    judgement**, not a fact.
    """
    if len(reports) < 2:
        raise CompareError("at least 2 runs are needed to judge agreement")
    packet = build_judge_packet(reports)
    raw = completions(packet)
    verdict = extract_json_block(raw)
    if not isinstance(verdict, dict):
        return {
            "judged_by_model": True,
            "error": "the model output cannot be parsed as JSON",
            "raw": raw[:2000],
        }
    verdict["judged_by_model"] = True
    verdict["caveat"] = (
        "This is a **model judgement**, not a fact. It can itself be wrong and is "
        "affected by temperature. Treat it as a reference signal, not a conclusion."
    )
    return verdict


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(result: dict) -> str:
    lines = [
        "# Comparison across multiple runs",
        "",
        f"Runs: **{result['runs']}**　"
        f"run_id: {', '.join(str(r) for r in result['run_ids'])}",
        "",
        "## 1. Process reproducibility (deterministic computation)",
        "",
        f"**Verdict: `{result['process_verdict']}`**",
        "",
        f"- Final state distribution: {json.dumps(result['final_states'], ensure_ascii=False)}",
        f"- Transition paths consistent: {'yes' if result['path_consistent'] else 'no'}",
        "",
        "| Run | Transition path |",
        "|---|---|",
    ]
    for run_id, path in zip(result["run_ids"], result["paths"]):
        lines.append(f"| {run_id} | {path} |")

    lines += ["", "### Gate grade by phase", "",
              "| Phase | Distribution | Consistent |", "|---|---|---|"]
    for phase, info in result["gate_grades"].items():
        dist = ", ".join(f"{k}×{v}" for k, v in info["distribution"].items())
        lines.append(f"| {phase} | {dist} | {'✅' if info['consistent'] else '❌'} |")

    lines += ["", "### Number of decision items", "",
              "| Item | Min | Max | Range | Mean |", "|---|---|---|---|---|"]
    for key, spread in result["counts"].items():
        if spread is None:
            continue
        lines.append(
            f"| {key} | {spread['min']} | {spread['max']} | "
            f"**{spread['range']}** | {spread['mean']} |"
        )

    if result["decision_errors"]:
        lines += ["", "### Decision record generation failed", ""]
        lines += [f"- {e}" for e in result["decision_errors"]]

    usage = result.get("total_usage") or {}
    if usage.get("calls"):
        lines += [
            "", "## 2. Cost and elapsed time", "",
            f"- Total model calls: **{usage['calls']}**"
            f" (of which {usage['calls_with_usage']} returned token usage)",
        ]
        if usage.get("total_tokens") is not None:
            lines.append(f"- Total tokens: **{usage['total_tokens']:,}**")
        elif usage.get("tokens_incomplete"):
            lines.append("- Total tokens: **incomplete** (some runs returned no usage)")
        if usage.get("seconds") is not None:
            lines.append(f"- Total elapsed: {usage['seconds']}s")
        if usage.get("cost_total") is not None:
            lines.append(
                f"- Estimated cost: **{usage['cost_total']} {usage.get('currency')}**"
                f" ({usage['cost_note']})"
            )
        else:
            lines.append(f"- Cost: not computed. {usage.get('cost_note')}")

        lines += ["", "| Run | Calls | Tokens | Elapsed | Estimated cost |", "|---|---|---|---|---|"]
        for run_id, item in zip(result["run_ids"], result.get("per_run_usage", [])):
            tokens = f"{item['total_tokens']:,}" if item["total_tokens"] is not None else "—"
            cost = (f"{item['cost_total']} {item['currency']}"
                    if item["cost_total"] is not None else "—")
            lines.append(f"| {run_id} | {item['calls']} | {tokens} | "
                         f"{item['seconds']}s | {cost} |")

    lines += ["", "## 3. Recommendations per run (verbatim)", ""]
    for run_id, chosen, state in zip(result["run_ids"], result["chosen_options"],
                                     result.get("decision_status", [])):
        if state == "NOT_PRODUCED":
            shown = "(no decision record produced)"
        elif state == "NULL_CHOICE":
            shown = f"(no choice was made this run — chosen_option is null) {chosen or ''}"
        else:
            shown = chosen
        lines += [f"**{run_id}**: {shown}", ""]

    lines += [
        "> ⚠️ " + result["caveat"],
        "",
        "## 4. Agreement of conclusions",
        "",
        "Requires a model judgement: `judge_agreement()`. What it gives is a **reference signal**, not a fact.",
        "",
    ]
    return "\n".join(lines)
