#!/usr/bin/env python3
"""Decision record store: keep decisions, and feed outcomes back in.

Why it is needed
----------------
In the methodology, the D (Decision Review) phase requires you to **compare
expectation with actuals, separate execution failure from strategy failure, and
record how the next step changes**. But before this, `decision_records` in
`project.json` was an array that stayed empty forever — decisions were made and
scattered, and nobody ever looked back.

The result: the system could produce decisions but **could never learn whether
its own decisions were right**. This layer closes the loop.

Two honesty constraints
-----------------------
1. **A decision without a review date is not a decision.** A decision you do not
   intend to check back on cannot be falsified, and therefore cannot be learned
   from. A warning is emitted when it is written.
2. **Overdue, unreviewed decisions are actively listed.** The `due` command sorts
   by review date and puts decisions that "should be reviewed but have not been"
   in front of you — instead of waiting for you to remember.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema_validator as sv  # noqa: E402

DECISIONS_DIRNAME = "decisions"
OUTCOMES_DIRNAME = "outcomes"
DECISION_SCHEMA = "decision_record.schema.json"
OUTCOME_SCHEMA = "outcome.schema.json"

DEVIATION_LABELS = {
    "AS_EXPECTED": "As expected (no attribution needed)",
    "EXECUTION": "Execution failure (right direction, insufficient effort)",
    "STRATEGY": "Strategy failure (the direction itself was wrong)",
    "ASSUMPTION": "Key assumption was wrong",
    "MIXED": "Multiple causes",
    "UNKNOWN": "Cannot attribute",
}

NEXT_ACTION_LABELS = {
    "CONTINUE": "Continue",
    "ADJUST": "Adjust",
    "STOP": "Stop",
    "ROLLBACK": "Roll back to the affected decision phase",
}


class DecisionError(Exception):
    """The decision record is invalid; writing is refused."""


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Quality checks (the part the schema cannot police)
# ---------------------------------------------------------------------------

def quality_warnings(record) -> list[str]:
    problems = []
    rid = record.get("decision_id", "?")

    if not record.get("review_date"):
        problems.append(
            f"{rid}: no review date — a decision you do not intend to check back "
            f"on cannot be falsified, and cannot be learned from"
        )

    if not record.get("falsification_conditions"):
        problems.append(
            f"{rid}: no falsification conditions — what evidence should overturn "
            f"this decision?"
        )

    if record.get("chosen_option") is None:
        if not record.get("validation_actions"):
            problems.append(
                f"{rid}: no choice was made (chosen_option is null) and no "
                f"validation actions were given — \"gather further evidence before "
                f"deciding\" must state what evidence is needed before a decision "
                f"can be made, otherwise it amounts to no conclusion"
            )

    if not record.get("tradeoffs"):
        problems.append(f"{rid}: no trade-offs written — if you cannot say what you give up, the choice is not yet thought through")

    if not record.get("key_assumptions"):
        problems.append(f"{rid}: no key assumptions listed — an assumption that is not written down cannot be tested")

    options = record.get("options") or []
    if len(options) >= 2:
        names = {str(o.get("name", "")).strip() for o in options}
        if len(names) < len(options):
            problems.append(f"{rid}: duplicate option names exist; this does not look like a real comparison")
    if len(options) == 1:
        problems.append(f"{rid}: only one option — this looks more like an announcement than a decision")

    chosen = record.get("chosen_option")
    if chosen and options and chosen not in {o.get("name") for o in options}:
        problems.append(
            f"{rid}: the chosen option {chosen!r} is not in the list of options"
        )

    deadline = record.get("deadline") or ""
    if deadline and _parse_date(deadline) and _parse_date(deadline) < date.today():
        problems.append(f"{rid}: decision deadline {deadline} has passed; update it or explain the delay")

    return problems


def _parse_date(text):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(text)[:len(fmt) + 2].strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(str(text)).date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Decision store
# ---------------------------------------------------------------------------

class DecisionStore:
    """A project's decision record store. Lives beside project.json."""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.decision_schema = sv.load_schema(schemas_dir() / DECISION_SCHEMA)
        self.outcome_schema = sv.load_schema(schemas_dir() / OUTCOME_SCHEMA)

    @property
    def root(self) -> Path:
        return self.project_dir / DECISIONS_DIRNAME

    @property
    def outcomes_dir(self) -> Path:
        return self.root / OUTCOMES_DIRNAME

    # ------------------------------------------------------------------ read
    def list(self) -> list[dict]:
        if not self.root.exists():
            return []
        records = []
        for path in sorted(self.root.glob("DR-*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                raise DecisionError(f"{path} is corrupt ({exc}). Please repair it by hand.") from exc
        return records

    def load(self, decision_id) -> dict:
        path = self.root / f"{decision_id}.json"
        if not path.exists():
            raise DecisionError(f"decision record {decision_id} not found ({path})")
        return json.loads(path.read_text(encoding="utf-8"))

    def next_id(self) -> str:
        highest = 0
        for record in self.list():
            rid = str(record.get("decision_id", ""))
            if rid.startswith("DR-") and rid[3:].isdigit():
                highest = max(highest, int(rid[3:]))
        return f"DR-{highest + 1:03d}"

    def outcome_of(self, decision_id):
        path = self.outcomes_dir / f"{decision_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # ----------------------------------------------------------------- write
    def add(self, record) -> dict:
        record = dict(record)
        record.setdefault("decision_id", self.next_id())
        rid = record["decision_id"]

        if (self.root / f"{rid}.json").exists():
            raise DecisionError(f"decision id {rid} already exists; overwriting refused")

        errors, warnings = sv.validate(record, self.decision_schema)
        if errors:
            raise DecisionError(
                "decision record does not conform to decision_record.schema.json; "
                "writing refused:\n  "
                + "\n  ".join(errors)
            )

        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{rid}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._sync_project()
        return record

    def record_outcome(self, outcome) -> dict:
        outcome = dict(outcome)
        rid = outcome.get("decision_id")
        if not rid:
            raise DecisionError("outcome is missing decision_id")
        if not (self.root / f"{rid}.json").exists():
            raise DecisionError(f"decision record {rid} not found; cannot record an outcome")

        outcome.setdefault("recorded_at", _now())
        errors, warnings = sv.validate(outcome, self.outcome_schema)
        if errors:
            raise DecisionError(
                "outcome record does not conform to outcome.schema.json; "
                "writing refused:\n  "
                + "\n  ".join(errors)
            )

        actual = (outcome.get("actual") or "").strip()
        if len(actual) < 8:
            raise DecisionError(
                "actual is too short. A review must state the outcome actually "
                "observed; when there is no data, write \"no data collected\" — an "
                "impression must not stand in for it."
            )
        if outcome.get("deviation_type") == "UNKNOWN" and not outcome.get("notes"):
            raise DecisionError(
                "when deviation_type is UNKNOWN, notes must explain why it cannot "
                "be attributed"
            )

        self.outcomes_dir.mkdir(parents=True, exist_ok=True)
        (self.outcomes_dir / f"{rid}.json").write_text(
            json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._sync_project()
        return outcome

    def _sync_project(self):
        """Write the decision summary back into project.json so the project file
        reflects the real decision history."""
        path = self.project_dir / "project.json"
        if not path.exists():
            return
        project = json.loads(path.read_text(encoding="utf-8"))
        summary = []
        for record in self.list():
            rid = record.get("decision_id")
            outcome = self.outcome_of(rid)
            summary.append({
                "decision_id": rid,
                "question": record.get("question"),
                "chosen_option": record.get("chosen_option"),
                "review_date": record.get("review_date"),
                "status": "REVIEWED" if outcome else "PENDING_REVIEW",
                "outcome": (
                    {
                        "deviation_type": outcome.get("deviation_type"),
                        "next_action": outcome.get("next_action"),
                        "recorded_at": outcome.get("recorded_at"),
                    }
                    if outcome else None
                ),
            })
        project["decision_records"] = summary
        project["last_updated"] = _now()
        path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # ----------------------------------------------------------------- review
    def due_for_review(self, today=None) -> dict:
        """Classify by review date: overdue and unreviewed / due soon / already
        reviewed."""
        today = today or date.today()
        overdue, upcoming, reviewed = [], [], []
        for record in self.list():
            rid = record.get("decision_id")
            outcome = self.outcome_of(rid)
            entry = {
                "decision_id": rid,
                "question": record.get("question"),
                "chosen_option": record.get("chosen_option"),
                "review_date": record.get("review_date"),
            }
            if outcome:
                entry["deviation_type"] = outcome.get("deviation_type")
                entry["next_action"] = outcome.get("next_action")
                reviewed.append(entry)
                continue
            review_date = _parse_date(record.get("review_date"))
            if review_date is None:
                entry["reason"] = "no review date that can be parsed"
                overdue.append(entry)
            elif review_date <= today:
                entry["days_overdue"] = (today - review_date).days
                overdue.append(entry)
            else:
                entry["days_remaining"] = (review_date - today).days
                upcoming.append(entry)

        overdue.sort(key=lambda e: e.get("days_overdue", 0), reverse=True)
        upcoming.sort(key=lambda e: e.get("days_remaining", 0))
        return {"overdue": overdue, "upcoming": upcoming, "reviewed": reviewed}

    def validate(self):
        errors, warnings = [], []
        for record in self.list():
            rid = record.get("decision_id", "?")
            record_errors, record_warnings = sv.validate(record, self.decision_schema)
            errors.extend(f"{rid}: {e}" for e in record_errors)
            warnings.extend(f"{rid}: {w}" for w in record_warnings)
            warnings.extend(quality_warnings(record))
            outcome = self.outcome_of(rid)
            if outcome:
                outcome_errors, outcome_warnings = sv.validate(
                    outcome, self.outcome_schema
                )
                errors.extend(f"{rid} outcome: {e}" for e in outcome_errors)
                warnings.extend(f"{rid} outcome: {w}" for w in outcome_warnings)
        return errors, warnings

    # ----------------------------------------------------------------- export
    def to_markdown(self) -> str:
        records = self.list()
        if not records:
            return "# Decision records\n\nNo decision records yet.\n"

        lines = ["# Decision records", ""]
        for record in records:
            rid = record.get("decision_id")
            outcome = self.outcome_of(rid)
            lines += [
                f"## {rid} — {record.get('question', '')}",
                "",
                f"- **Decision**: {record.get('chosen_option', '')}",
                f"- **Review date**: {record.get('review_date') or '(not set)'}",
                f"- **Deadline**: {record.get('deadline') or '(not set)'}",
                "",
            ]
            rejected = record.get("rejected_options") or []
            if rejected:
                lines.append("**Rejected options**")
                lines.append("")
                for item in rejected:
                    lines.append(f"- {item.get('name')}: {item.get('reason')}")
                lines.append("")
            tradeoffs = record.get("tradeoffs") or []
            if tradeoffs:
                lines.append("**Trade-offs**: " + "; ".join(str(t) for t in tradeoffs))
                lines.append("")
            conditions = record.get("falsification_conditions") or []
            if conditions:
                lines.append("**Falsification conditions**")
                lines.append("")
                lines += [f"- {c}" for c in conditions]
                lines.append("")

            if outcome:
                lines += [
                    "**Review outcome**",
                    "",
                    f"- Expected: {outcome.get('expected')}",
                    f"- Actual: {outcome.get('actual')}",
                    f"- Deviation type: {DEVIATION_LABELS.get(outcome.get('deviation_type'), outcome.get('deviation_type'))}",
                    f"- Next step: {NEXT_ACTION_LABELS.get(outcome.get('next_action'), outcome.get('next_action'))}",
                    "",
                ]
            else:
                lines += ["> Not reviewed yet.", ""]
        return "\n".join(lines)
