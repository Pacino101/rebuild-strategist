#!/usr/bin/env python3
"""决策记录库：把决策存下来，并把结果回填回去。

为什么需要它
------------
方法论里 D（Decision Review）阶段的要求是：**比较预期与实际、区分执行偏差与
策略失效、记录下一步如何改变**。但在此之前，`project.json` 里的
`decision_records` 只是一个永远为空的数组——决策做完了就散了，没人回头核对。

结果是：系统能产出决策，却**永远学不到自己的决策对不对**。这一层把循环闭上。

两条诚实性约束
--------------
1. **没有复审日期的决策不算决策。** 一个不打算回头核对的决策，无法被证伪，
   也就无法被学习。写入时会给出警告。
2. **过期未复盘的决策会被主动列出来。** `due` 命令按复审日期排序，
   把「该复盘但没复盘」的决策摆到眼前——而不是等你想起来。
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
    "EXECUTION": "执行偏差（方向对、力度不足）",
    "STRATEGY": "策略失效（方向本身错了）",
    "ASSUMPTION": "关键假设错误",
    "MIXED": "多重原因",
    "UNKNOWN": "无法归因",
}

NEXT_ACTION_LABELS = {
    "CONTINUE": "继续",
    "ADJUST": "调整",
    "STOP": "停止",
    "ROLLBACK": "回退到受影响的决策阶段",
}


class DecisionError(Exception):
    """决策记录不合法，拒绝写入。"""


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 质量检查（schema 管不到的部分）
# ---------------------------------------------------------------------------

def quality_warnings(record) -> list[str]:
    problems = []
    rid = record.get("decision_id", "?")

    if not record.get("review_date"):
        problems.append(
            f"{rid}: 没有复审日期——不打算回头核对的决策无法被证伪，也无法被学习"
        )

    if not record.get("falsification_conditions"):
        problems.append(
            f"{rid}: 没有反证条件——什么证据出现时应当推翻这个决定？"
        )

    if not record.get("tradeoffs"):
        problems.append(f"{rid}: 没有写明代价——说不清放弃什么，说明还没想清楚选择")

    if not record.get("key_assumptions"):
        problems.append(f"{rid}: 没有列出关键假设——假设没写出来就无法被检验")

    options = record.get("options") or []
    if len(options) >= 2:
        names = {str(o.get("name", "")).strip() for o in options}
        if len(names) < len(options):
            problems.append(f"{rid}: 存在同名选项，看起来不是一个真正的比较")
    if len(options) == 1:
        problems.append(f"{rid}: 只有一个选项——这更像是通报而不是决策")

    chosen = record.get("chosen_option")
    if chosen and options and chosen not in {o.get("name") for o in options}:
        problems.append(
            f"{rid}: 选择的方案 {chosen!r} 不在候选方案列表里"
        )

    deadline = record.get("deadline") or ""
    if deadline and _parse_date(deadline) and _parse_date(deadline) < date.today():
        problems.append(f"{rid}: 决策期限 {deadline} 已过期，请更新或说明延期理由")

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
# 决策库
# ---------------------------------------------------------------------------

class DecisionStore:
    """一个项目的决策记录库。与 project.json 放在同一目录。"""

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

    # ------------------------------------------------------------------ 读
    def list(self) -> list[dict]:
        if not self.root.exists():
            return []
        records = []
        for path in sorted(self.root.glob("DR-*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                raise DecisionError(f"{path} 损坏（{exc}）。请人工修复。") from exc
        return records

    def load(self, decision_id) -> dict:
        path = self.root / f"{decision_id}.json"
        if not path.exists():
            raise DecisionError(f"找不到决策记录 {decision_id}（{path}）")
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

    # ------------------------------------------------------------------ 写
    def add(self, record) -> dict:
        record = dict(record)
        record.setdefault("decision_id", self.next_id())
        rid = record["decision_id"]

        if (self.root / f"{rid}.json").exists():
            raise DecisionError(f"决策编号 {rid} 已存在，拒绝覆盖")

        errors, warnings = sv.validate(record, self.decision_schema)
        if errors:
            raise DecisionError(
                "决策记录不符合 decision_record.schema.json，已拒绝写入：\n  "
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
            raise DecisionError("outcome 缺少 decision_id")
        if not (self.root / f"{rid}.json").exists():
            raise DecisionError(f"找不到决策记录 {rid}，无法回填结果")

        outcome.setdefault("recorded_at", _now())
        errors, warnings = sv.validate(outcome, self.outcome_schema)
        if errors:
            raise DecisionError(
                "结果记录不符合 outcome.schema.json，已拒绝写入：\n  "
                + "\n  ".join(errors)
            )

        actual = (outcome.get("actual") or "").strip()
        if len(actual) < 8:
            raise DecisionError(
                "actual 过短。复盘必须写出实际观察到的结果；"
                "没有数据时请写「未采集到数据」，不得用印象代替。"
            )
        if outcome.get("deviation_type") == "UNKNOWN" and not outcome.get("notes"):
            raise DecisionError(
                "deviation_type 为 UNKNOWN 时必须用 notes 说明为什么无法归因"
            )

        self.outcomes_dir.mkdir(parents=True, exist_ok=True)
        (self.outcomes_dir / f"{rid}.json").write_text(
            json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._sync_project()
        return outcome

    def _sync_project(self):
        """把决策摘要写回 project.json，让项目文件反映真实决策历史。"""
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

    # ------------------------------------------------------------------ 复盘
    def due_for_review(self, today=None) -> dict:
        """按复审日期分类：已过期未复盘 / 即将到期 / 已复盘。"""
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
                entry["reason"] = "没有可解析的复审日期"
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

    # ------------------------------------------------------------------ 导出
    def to_markdown(self) -> str:
        records = self.list()
        if not records:
            return "# 决策记录\n\n尚无决策记录。\n"

        lines = ["# 决策记录", ""]
        for record in records:
            rid = record.get("decision_id")
            outcome = self.outcome_of(rid)
            lines += [
                f"## {rid} — {record.get('question', '')}",
                "",
                f"- **决定**：{record.get('chosen_option', '')}",
                f"- **复审日期**：{record.get('review_date') or '（未设定）'}",
                f"- **期限**：{record.get('deadline') or '（未设定）'}",
                "",
            ]
            rejected = record.get("rejected_options") or []
            if rejected:
                lines.append("**放弃的方案**")
                lines.append("")
                for item in rejected:
                    lines.append(f"- {item.get('name')}：{item.get('reason')}")
                lines.append("")
            tradeoffs = record.get("tradeoffs") or []
            if tradeoffs:
                lines.append("**代价**：" + "；".join(str(t) for t in tradeoffs))
                lines.append("")
            conditions = record.get("falsification_conditions") or []
            if conditions:
                lines.append("**反证条件**")
                lines.append("")
                lines += [f"- {c}" for c in conditions]
                lines.append("")

            if outcome:
                lines += [
                    "**复盘结果**",
                    "",
                    f"- 预期：{outcome.get('expected')}",
                    f"- 实际：{outcome.get('actual')}",
                    f"- 偏差类型：{DEVIATION_LABELS.get(outcome.get('deviation_type'), outcome.get('deviation_type'))}",
                    f"- 下一步：{NEXT_ACTION_LABELS.get(outcome.get('next_action'), outcome.get('next_action'))}",
                    "",
                ]
            else:
                lines += ["> 尚未复盘。", ""]
        return "\n".join(lines)
