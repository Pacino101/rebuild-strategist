#!/usr/bin/env python3
"""数据源层：把外部材料变成可追溯的「文档」。

设计边界
--------
本层**只读**，且**不内置任何具体平台的连接器**。使用者自己决定从哪里取数：

- 本地文件（CSV / JSON / JSONL / TXT / MD / XLSX）
- 使用者自己的 HTTP 端点（URL 与密钥都由使用者提供）

为什么每条材料都要存哈希：方法论要求每条证据可追溯到来源。若来源可以
被悄悄改动而无人察觉，「可追溯」就是空话。哈希让来源可被校验。

本层不解析营销语义、不做归因、不写回任何外部系统。
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

#: 单个文档的字符上限，超出则截断并在 meta 中标记。
#: 目的是避免一次误操作把几百兆文件灌进提示词。
MAX_CONTENT_CHARS = 200_000


class SourceError(Exception):
    """取数失败。消息面向使用者，应能直接看懂。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Document:
    """一份取回来的原始材料。"""

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
    """超长内容截断并留痕——静默截断会让人以为拿到的是全文。"""
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    meta["truncated"] = True
    meta["original_chars"] = len(content)
    meta["kept_chars"] = MAX_CONTENT_CHARS
    return content[:MAX_CONTENT_CHARS]


class DocumentStore:
    """项目的原始材料库。与 project.json 放在同一目录。"""

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

    # ------------------------------------------------------------------ 写入
    def add(self, origin, content, media_type="text/plain", meta=None) -> Document:
        if not isinstance(content, str):
            raise SourceError(f"content 必须是字符串，收到 {type(content).__name__}")
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

    # ------------------------------------------------------------------ 读取
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
                    f"{self.index_path}:{lineno} 损坏（{exc}）。请人工修复。"
                ) from exc
        return entries

    def get(self, doc_id) -> Document:
        path = self.documents_dir / f"{doc_id}.json"
        if not path.exists():
            raise SourceError(f"找不到文档 {doc_id}（{path}）")
        return Document.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def verify(self, doc_id) -> bool:
        """校验文档内容与记录的哈希是否一致——来源是否被改动过。"""
        document = self.get(doc_id)
        return sha256_of(document.content) == document.sha256
