#!/usr/bin/env python3
"""Data source layer: turn external material into traceable "documents".

Design boundaries
-----------------
This layer is **read-only** and **ships no connector for any specific platform**.
The user decides where data comes from:

- Local files (CSV / JSON / JSONL / TXT / MD / XLSX)
- The user's own HTTP endpoints (both URL and keys are supplied by the user)

Why every piece of material is hashed: the methodology requires every piece of
evidence to be traceable to its source. If a source could be quietly modified
without anyone noticing, "traceable" would be an empty promise. Hashing makes
sources verifiable.

This layer does not parse marketing semantics, does not do attribution, and does
not write back to any external system.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

SOURCES_DIRNAME = "sources"
INDEX_FILENAME = "index.jsonl"
DOCUMENTS_DIRNAME = "documents"

#: Character limit for a single document; anything longer is truncated and
#: flagged in meta. The point is to avoid one careless operation pouring a few
#: hundred megabytes into the prompt.
MAX_CONTENT_CHARS = 200_000


class SourceError(Exception):
    """Data fetch failed. Messages face the user and must be immediately clear."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Document:
    """A single piece of source material that was fetched."""

    doc_id: str
    origin: str
    media_type: str
    fetched_at: str
    sha256: str
    content: str
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data) -> "Document":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def preview(self, limit=120) -> str:
        text = " ".join(self.content.split())
        return text[:limit] + ("…" if len(text) > limit else "")


def truncate(content: str, meta: dict) -> str:
    """Truncate over-long content and leave a trace — silent truncation makes
    people believe they got the full text."""
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    meta["truncated"] = True
    meta["original_chars"] = len(content)
    meta["kept_chars"] = MAX_CONTENT_CHARS
    return content[:MAX_CONTENT_CHARS]


class DocumentStore:
    """The project's source material library. Lives beside project.json."""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)

    @property
    def root(self) -> Path:
        return self.project_dir / SOURCES_DIRNAME

    @property
    def index_path(self) -> Path:
        return self.root / INDEX_FILENAME

    @property
    def documents_dir(self) -> Path:
        return self.root / DOCUMENTS_DIRNAME

    # ------------------------------------------------------------------ write
    def add(self, origin, content, media_type="text/plain", meta=None) -> Document:
        if not isinstance(content, str):
            raise SourceError(
                f"content must be a string, got {type(content).__name__}"
            )
        meta = dict(meta or {})
        content = truncate(content, meta)

        self.root.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        doc_id = self._next_id()
        document = Document(
            doc_id=doc_id,
            origin=str(origin),
            media_type=media_type,
            fetched_at=_now(),
            sha256=sha256_of(content),
            content=content,
            meta=meta,
        )

        payload = document.to_dict()
        (self.documents_dir / f"{doc_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {k: v for k, v in payload.items() if k != "content"},
                ensure_ascii=False,
            ) + "\n")
        return document

    def _next_id(self) -> str:
        highest = 0
        for entry in self.list():
            doc_id = str(entry.get("doc_id", ""))
            if doc_id.startswith("DOC-") and doc_id[4:].isdigit():
                highest = max(highest, int(doc_id[4:]))
        return f"DOC-{highest + 1:03d}"

    # ------------------------------------------------------------------- read
    def list(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        entries = []
        for lineno, raw in enumerate(
            self.index_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            line = raw.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SourceError(
                    f"{self.index_path}:{lineno} is corrupt ({exc}). "
                    "Please repair it by hand."
                ) from exc
        return entries

    def get(self, doc_id) -> Document:
        path = self.documents_dir / f"{doc_id}.json"
        if not path.exists():
            raise SourceError(f"document {doc_id} not found ({path})")
        return Document.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def verify(self, doc_id) -> bool:
        """Check whether document content matches the recorded hash — i.e.
        whether the source has been modified."""
        document = self.get(doc_id)
        return sha256_of(document.content) == document.sha256
