#!/usr/bin/env python3
"""REBUILD evidence ledger.

The methodology makes "every key judgement must be traceable" a core
requirement, but until now `evidence.schema.json` was a specification nobody
read and evidence had nowhere to live. This module turns it into usable storage:

- **Append-only JSONL**: one record per line. Append-friendly, diffable,
  readable by a human, no database, no third-party dependency.
- **Validation enforced before writing**: a record that does not conform to the
  schema is not written, instead of being written and sorted out later.
- **Quality checks beyond the schema**: the schema can only guarantee that
  fields are present and values are legal; it cannot guarantee that "this piece
  of evidence is useful". So extra checks ask whether a FACT has a source,
  whether an ASSUMPTION has a recheck condition, and whether `decision_impact`
  really says which decision would change. These surface as warnings and do not
  block writing — but they do appear in the `validate` output.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema_validator as sv

EVIDENCE_FILENAME = "evidence.jsonl"
EVIDENCE_SCHEMA = "evidence.schema.json"

VALID_TYPES = ("FACT", "INFERENCE", "ASSUMPTION", "UNKNOWN")
VALID_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

#: These phrasings amount to "saying nothing" — if one appears, the decision
#: impact counts as unfilled.
_EMPTY_IMPACT = {"", "无", "n/a", "na", "none", "-", "—", "待定", "tbd"}


class EvidenceError(Exception):
    """The record is invalid; writing is refused."""


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


#: A source shaped like DOC-001 is treated as a reference into the material
#: library and can be verified by machine.
DOC_REF_PATTERN = re.compile(r"^DOC-\d+$")


def document_ref(source):
    """Return the material id if the source is one, otherwise None.

    This is what turns "traceable" from a slogan into a mechanism: a free-text
    source cannot be verified automatically, a material id can. Both are
    allowed, but the system knows which of the two it is handling.
    """
    text = str(source or "").strip()
    return text if DOC_REF_PATTERN.match(text) else None


def documents_dir(project_dir) -> Path:
    return Path(project_dir) / "sources" / "documents"


def existing_document_ids(project_dir) -> set:
    directory = documents_dir(project_dir)
    if not directory.exists():
        return set()
    return {path.stem for path in directory.glob("DOC-*.json")}


def provenance_report(project_dir) -> dict:
    """How verifiable the evidence sources are.

    Three buckets:
      - linked     the source is a material id and the material exists
                   → **machine-verifiable**
      - dangling   the source is a material id but the material is missing
                   → dangling link, an error
      - free_text  the source is free text → cannot be verified automatically,
                   only by hand
    """
    project_dir = Path(project_dir)
    ledger = Ledger(project_dir)
    known = existing_document_ids(project_dir)

    linked, dangling, free_text, missing = [], [], [], []
    for record in ledger.load():
        rid = record.get("id", "?")
        source = str(record.get("source") or "").strip()
        ref = document_ref(source)
        if ref:
            (linked if ref in known else dangling).append(
                {"id": rid, "source": ref, "claim": record.get("claim")}
            )
        elif source:
            free_text.append({"id": rid, "source": source, "claim": record.get("claim")})
        else:
            missing.append({"id": rid, "claim": record.get("claim")})

    total = len(linked) + len(dangling) + len(free_text) + len(missing)
    return {
        "total": total,
        "linked": linked,
        "dangling": dangling,
        "free_text": free_text,
        "no_source": missing,
        "verifiable_ratio": round(len(linked) / total, 3) if total else None,
    }


def load_evidence_schema() -> dict:
    return sv.load_schema(schemas_dir() / EVIDENCE_SCHEMA)


# ---------------------------------------------------------------------------
# Stateless quality checks
# ---------------------------------------------------------------------------

def quality_warnings(record) -> list[str]:
    """Semantic problems the schema cannot police. Returns a warning list (does
    not block writing)."""
    problems = []
    rid = record.get("id", "?")
    kind = record.get("type")
    claim = (record.get("claim") or "").strip()

    if not claim:
        problems.append(f"{rid}: claim is empty")

    impact = (record.get("decision_impact") or "").strip()
    if impact.lower() in _EMPTY_IMPACT:
        problems.append(
            f"{rid}: does not say which decision this evidence would change — "
            f"the methodology requires every key piece of evidence to point at a "
            f"concrete decision, otherwise it is not evidence"
        )
    elif len(impact) < 6:
        problems.append(f"{rid}: decision_impact is too short ({impact!r}); it may not point at a concrete decision")

    if kind == "FACT" and not (record.get("source") or "").strip():
        problems.append(f"{rid}: labelled FACT but no source was provided — a fact must be verifiable")

    if kind == "ASSUMPTION" and not (
        (record.get("recheck_trigger") or "").strip() or record.get("counter_evidence")
    ):
        problems.append(
            f"{rid}: labelled ASSUMPTION but has neither recheck_trigger nor counter_evidence — "
            f"an unverified premise must state the conditions under which it will be rechecked"
        )

    if kind == "UNKNOWN" and record.get("confidence") != "LOW":
        problems.append(
            f"{rid}: labelled UNKNOWN but confidence is {record.get('confidence')} — "
            f"a record with insufficient information should not carry high confidence"
        )

    if kind == "FACT" and record.get("confidence") == "LOW":
        problems.append(f"{rid}: labelled FACT but given LOW confidence — the two conflict semantically; check whether the type is wrong")

    if not (record.get("scope") or "").strip():
        problems.append(f"{rid}: no scope of applicability was written; the conclusion will be over-generalised")

    return problems


class Ledger:
    """A project's evidence ledger. The ledger file lives beside project.json."""

    def __init__(self, project_dir, schema=None):
        self.project_dir = Path(project_dir)
        self.schema = schema if schema is not None else load_evidence_schema()

    # ------------------------------------------------------------------ path
    @property
    def path(self) -> Path:
        return self.project_dir / EVIDENCE_FILENAME

    @property
    def exists(self) -> bool:
        return self.path.exists()

    # ------------------------------------------------------------- read/write
    def load(self) -> list[dict]:
        """Read every record. A corrupt line raises EvidenceError instead of
        being silently skipped."""
        if not self.exists:
            return []
        records = []
        for lineno, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise EvidenceError(
                    f"{self.path}:{lineno} is not valid JSON ({exc}). "
                    f"The ledger is corrupt; repair it by hand first — silently "
                    f"skipping bad lines would make evidence vanish unnoticed."
                ) from exc
        return records

    def next_id(self) -> str:
        """Generate the next id, shaped like E-001."""
        highest = 0
        for record in self.load():
            rid = str(record.get("id", ""))
            if rid.startswith("E-") and rid[2:].isdigit():
                highest = max(highest, int(rid[2:]))
        return f"E-{highest + 1:03d}"

    def add(self, record) -> dict:
        """Validate and append one record. If validation fails, writing is
        refused."""
        record = dict(record)
        record.setdefault("id", self.next_id())

        errors, warnings = sv.validate(record, self.schema)
        if errors:
            raise EvidenceError(
                "record does not conform to evidence.schema.json; writing refused:\n  "
                + "\n  ".join(errors)
            )

        existing = {r.get("id") for r in self.load()}
        if record["id"] in existing:
            raise EvidenceError(f"id {record['id']} already exists; duplicate writing refused")

        self.project_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    # -------------------------------------------------------------- validate
    def validate(self):
        """Full validation. Returns (errors, warnings).

        errors   = does not conform to the schema, or the ledger is corrupt
        warnings = conforms to the schema but fails methodologically
                   (see quality_warnings)
        """
        errors, warnings = [], []
        try:
            records = self.load()
        except EvidenceError as exc:
            return [str(exc)], []

        seen = {}
        for record in records:
            rid = record.get("id", "?")
            record_errors, record_warnings = sv.validate(record, self.schema)
            errors.extend(f"{rid}: {e}" for e in record_errors)
            warnings.extend(f"{rid}: {w}" for w in record_warnings)
            warnings.extend(quality_warnings(record))
            if rid in seen:
                errors.append(f"{rid}: duplicate id")
            seen[rid] = True

        # A source pointing at a missing material is a **dangling link**: it
        # claims to be verifiable but cannot be verified. That is worse than a
        # free-text source, so it counts as an error rather than a warning.
        known = existing_document_ids(self.project_dir)
        for record in records:
            ref = document_ref(record.get("source"))
            if ref and ref not in known:
                errors.append(
                    f"{record.get('id', '?')}: source points at material {ref}, "
                    f"but the material library does not contain it (dangling link)"
                )
        return errors, warnings

    # ----------------------------------------------------------------- query
    def filter(self, kind=None, confidence=None, min_confidence=None, source=None):
        records = self.load()
        if kind:
            records = [r for r in records if r.get("type") == kind]
        if confidence:
            records = [r for r in records if r.get("confidence") == confidence]
        if min_confidence:
            floor = CONFIDENCE_ORDER.get(min_confidence, 0)
            records = [
                r for r in records
                if CONFIDENCE_ORDER.get(r.get("confidence"), 0) >= floor
            ]
        if source:
            needle = source.lower()
            records = [
                r for r in records
                if needle in str(r.get("source") or "").lower()
            ]
        return records

    def summary(self) -> dict:
        records = self.load()
        by_type = {t: 0 for t in VALID_TYPES}
        by_confidence = {c: 0 for c in VALID_CONFIDENCE}
        with_counter = 0
        for record in records:
            by_type[record.get("type")] = by_type.get(record.get("type"), 0) + 1
            by_confidence[record.get("confidence")] = (
                by_confidence.get(record.get("confidence"), 0) + 1
            )
            if record.get("counter_evidence"):
                with_counter += 1
        return {
            "total": len(records),
            "by_type": by_type,
            "by_confidence": by_confidence,
            "with_counter_evidence": with_counter,
        }

    def high_leverage(self):
        """High-leverage evidence: low-confidence records that would change a
        major decision. These are the ones that most deserve further evidence
        first."""
        return [
            r for r in self.load()
            if r.get("confidence") in ("LOW", "MEDIUM")
            and (r.get("decision_impact") or "").strip()
            and r.get("type") in ("ASSUMPTION", "UNKNOWN")
        ]


# ---------------------------------------------------------------------------
# Gap analysis against project.json
# ---------------------------------------------------------------------------

def gaps(project_path) -> dict:
    """Find the assumptions and unknowns that the project declares but the
    ledger has no evidence for."""
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding="utf-8"))
    records = Ledger(project_path.parent).load()

    def covered(text):
        """Two-way substring matching. Text that is too short (< 4 characters)
        does not take part — words like "cost" or "channel" would match almost
        any record, and that kind of "already covered" is an illusion."""
        text = (text or "").strip()
        if not text:
            return True
        if len(text) < 4:
            return False
        for record in records:
            claim = (record.get("claim") or "").strip()
            if not claim:
                continue
            if text in claim or (len(claim) >= 4 and claim in text):
                return True
        return False

    return {
        "project": str(project_path),
        "evidence_count": len(records),
        "assumptions_without_evidence": [
            a for a in (project.get("assumptions") or []) if not covered(a)
        ],
        "unknowns_without_evidence": [
            u for u in (project.get("unknowns") or []) if not covered(u)
        ],
        "known_facts_without_evidence": [
            f for f in (project.get("known_facts") or []) if not covered(f)
        ],
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def to_markdown(project_dir) -> str:
    ledger = Ledger(project_dir)
    records = ledger.load()
    summary = ledger.summary()

    lines = [
        "# Evidence ledger",
        "",
        f"{summary['total']} records: "
        + ", ".join(f"{k} {v}" for k, v in summary["by_type"].items() if v)
        if summary["total"] else "0 records.",
        "",
        "| ID | Type | Confidence | Claim | Source | Scope | Decision it would change |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in records:
        def cell(value):
            text = str(value if value is not None else "").replace("|", "\\|")
            return text.replace("\n", " ")

        lines.append(
            "| {id} | {type} | {confidence} | {claim} | {source} | {scope} | {impact} |".format(
                id=cell(record.get("id")),
                type=cell(record.get("type")),
                confidence=cell(record.get("confidence")),
                claim=cell(record.get("claim")),
                source=cell(record.get("source") or "(not provided)"),
                scope=cell(record.get("scope")),
                impact=cell(record.get("decision_impact")),
            )
        )

    counters = [r for r in records if r.get("counter_evidence")]
    if counters:
        lines += ["", "## Falsification records", ""]
        for record in counters:
            lines.append(f"- **{record.get('id')}** {record.get('claim')}")
            for item in record["counter_evidence"]:
                lines.append(f"  - Falsification: {item}")

    return "\n".join(lines) + "\n"
