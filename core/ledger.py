#!/usr/bin/env python3
"""REBUILD 证据账本（Evidence Ledger）。

方法论把「每条关键判断可追溯」当作核心要求，但此前 `evidence.schema.json`
只是一个没人读的规范文件，证据无处存放。本模块把它变成可用的存储：

- **追加写入 JSONL**：每行一条记录。追加友好、可 diff、可人工审阅、
  不需要数据库、不引入任何第三方依赖。
- **写入前强制校验**：不符合 schema 的记录不会被写进去，而不是写进去再说。
- **超出 schema 的质量检查**：schema 只能保证字段齐全与取值合法，
  保证不了「这条证据有用」。因此额外检查 FACT 是否给了来源、
  假设是否给了重查条件、`decision_impact` 是否真的说了会改变什么决策。
  这些以 warning 形式给出，不阻断写入——但会出现在 `validate` 输出里。
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

#: 这些措辞等于「没说」——出现即视为未填写决策影响。
_EMPTY_IMPACT = {"", "无", "n/a", "na", "none", "-", "—", "待定", "tbd"}


class EvidenceError(Exception):
    """记录不合法，拒绝写入。"""


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


#: 形如 DOC-001 的来源视为指向材料库的引用，可被机器核验。
DOC_REF_PATTERN = re.compile(r"^DOC-\d+$")


def document_ref(source):
    """若来源是材料编号则返回它，否则返回 None。

    这是把「可追溯」从口号变成机制的关键：自由文本来源无法自动核验，
    材料编号可以。两种都允许，但系统知道自己在处理哪一种。
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
    """证据来源的可核验程度统计。

    区分三档：
      - linked     来源是材料编号，且材料存在 → **可机器核验**
      - dangling   来源是材料编号，但材料不存在 → 断链，是错误
      - free_text  来源是自由文本 → 无法自动核验，只能靠人工
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
# 无状态的质量检查
# ---------------------------------------------------------------------------

def quality_warnings(record) -> list[str]:
    """schema 管不到的语义问题。返回 warning 列表（不阻断写入）。"""
    problems = []
    rid = record.get("id", "?")
    kind = record.get("type")
    claim = (record.get("claim") or "").strip()

    if not claim:
        problems.append(f"{rid}: claim 为空")

    impact = (record.get("decision_impact") or "").strip()
    if impact.lower() in _EMPTY_IMPACT:
        problems.append(
            f"{rid}: 未说明该证据会改变什么决策——"
            f"方法论要求每条关键证据都指向一个具体决策，否则它不构成证据"
        )
    elif len(impact) < 6:
        problems.append(f"{rid}: decision_impact 过短（{impact!r}），可能没有指向具体决策")

    if kind == "FACT" and not (record.get("source") or "").strip():
        problems.append(f"{rid}: 标为 FACT 但未提供 source——事实必须可核验")

    if kind == "ASSUMPTION" and not (
        (record.get("recheck_trigger") or "").strip() or record.get("counter_evidence")
    ):
        problems.append(
            f"{rid}: 标为 ASSUMPTION 但既无 recheck_trigger 也无 counter_evidence——"
            f"未验证的前提必须写明什么条件下重查"
        )

    if kind == "UNKNOWN" and record.get("confidence") != "LOW":
        problems.append(
            f"{rid}: 标为 UNKNOWN 但可信度为 {record.get('confidence')}——"
            f"信息不足的记录不应给高可信度"
        )

    if kind == "FACT" and record.get("confidence") == "LOW":
        problems.append(f"{rid}: 标为 FACT 却给 LOW 可信度——两者语义冲突，请确认类型标错没有")

    if not (record.get("scope") or "").strip():
        problems.append(f"{rid}: 未写适用范围（scope），该结论会被过度推广")

    return problems


class Ledger:
    """一个项目的证据账本。账本文件与 project.json 放在同一目录。"""

    def __init__(self, project_dir, schema=None):
        self.project_dir = Path(project_dir)
        self.schema = schema if schema is not None else load_evidence_schema()

    # ------------------------------------------------------------------ 路径
    @property
    def path(self) -> Path:
        return self.project_dir / EVIDENCE_FILENAME

    @property
    def exists(self) -> bool:
        return self.path.exists()

    # ------------------------------------------------------------------ 读写
    def load(self) -> list[dict]:
        """读取全部记录。遇到坏行会抛出 EvidenceError，而不是静默跳过。"""
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
                    f"{self.path}:{lineno} 不是合法 JSON（{exc}）。"
                    f"账本已损坏，请先人工修复——静默跳过坏行会让证据悄悄消失。"
                ) from exc
        return records

    def next_id(self) -> str:
        """生成下一个编号，形如 E-001。"""
        highest = 0
        for record in self.load():
            rid = str(record.get("id", ""))
            if rid.startswith("E-") and rid[2:].isdigit():
                highest = max(highest, int(rid[2:]))
        return f"E-{highest + 1:03d}"

    def add(self, record) -> dict:
        """校验并追加一条记录。校验不通过则拒绝写入。"""
        record = dict(record)
        record.setdefault("id", self.next_id())

        errors, warnings = sv.validate(record, self.schema)
        if errors:
            raise EvidenceError(
                "记录不符合 evidence.schema.json，已拒绝写入：\n  "
                + "\n  ".join(errors)
            )

        existing = {r.get("id") for r in self.load()}
        if record["id"] in existing:
            raise EvidenceError(f"编号 {record['id']} 已存在，拒绝重复写入")

        self.project_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    # ------------------------------------------------------------------ 校验
    def validate(self):
        """全量校验。返回 (errors, warnings)。

        errors  = 不符合 schema，或账本损坏
        warnings = 符合 schema 但方法学上不成立（见 quality_warnings）
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
                errors.append(f"{rid}: 编号重复")
            seen[rid] = True

        # 指向不存在材料的来源是**断链**：它自称可核验，实际核验不了。
        # 这比自由文本来源更糟，所以算错误而不是警告。
        known = existing_document_ids(self.project_dir)
        for record in records:
            ref = document_ref(record.get("source"))
            if ref and ref not in known:
                errors.append(
                    f"{record.get('id', '?')}: 来源指向材料 {ref}，"
                    f"但材料库中没有这份材料（断链）"
                )
        return errors, warnings

    # ------------------------------------------------------------------ 查询
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
        """高杠杆证据：可信度低、但会改变重大决策的记录。这些最该优先补证。"""
        return [
            r for r in self.load()
            if r.get("confidence") in ("LOW", "MEDIUM")
            and (r.get("decision_impact") or "").strip()
            and r.get("type") in ("ASSUMPTION", "UNKNOWN")
        ]


# ---------------------------------------------------------------------------
# 与 project.json 的缺口分析
# ---------------------------------------------------------------------------

def gaps(project_path) -> dict:
    """找出「项目里声明了、但账本里没有证据支撑」的假设与未知项。"""
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding="utf-8"))
    records = Ledger(project_path.parent).load()

    def covered(text):
        """双向子串匹配。过短的文本（<4 字符）不参与匹配——
        「成本」「渠道」这类词几乎会命中任何记录，那样的「已覆盖」是假象。"""
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
# 导出
# ---------------------------------------------------------------------------

def to_markdown(project_dir) -> str:
    ledger = Ledger(project_dir)
    records = ledger.load()
    summary = ledger.summary()

    lines = [
        "# 证据账本",
        "",
        f"共 {summary['total']} 条："
        + "、".join(f"{k} {v}" for k, v in summary["by_type"].items() if v)
        if summary["total"] else "共 0 条。",
        "",
        "| ID | 类型 | 可信度 | 主张 | 来源 | 适用范围 | 会改变什么决策 |",
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
                source=cell(record.get("source") or "（未提供）"),
                scope=cell(record.get("scope")),
                impact=cell(record.get("decision_impact")),
            )
        )

    counters = [r for r in records if r.get("counter_evidence")]
    if counters:
        lines += ["", "## 反证记录", ""]
        for record in counters:
            lines.append(f"- **{record.get('id')}** {record.get('claim')}")
            for item in record["counter_evidence"]:
                lines.append(f"  - 反证：{item}")

    return "\n".join(lines) + "\n"
