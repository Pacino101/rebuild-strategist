"""决策记录库与结果回填测试。

重点：D 阶段（复盘）此前完全没有实现——决策做完就散了。这里验证
循环真的闭上了：决策会被存下来、过期未复盘会被主动列出、结果能回填，
且不合格的记录会被拒绝而不是默默接受。
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

import decisions as D  # noqa: E402

EXAMPLE = ROOT / "examples" / "nanjiang_tea"


def good_record(**overrides):
    record = {
        "question": "优先选择哪一项品牌与渠道策略？",
        "deadline": None,
        "options": [
            {"name": "春茶季集中投放", "rationale": "需求集中", "risks": ["供应压力"]},
            {"name": "全年均投", "rationale": "稳定", "risks": ["错过峰值"]},
        ],
        "chosen_option": "春茶季集中投放",
        "rejected_options": [{"name": "全年均投", "reason": "峰值把握不足"}],
        "tradeoffs": ["放弃淡季曝光"],
        "key_assumptions": ["春茶季需求集中"],
        "falsification_conditions": ["若 4 月复购率低于 15% 则推翻"],
        "validation_actions": ["小规模 A/B 测试"],
        "review_date": "2099-05-01",
    }
    record.update(overrides)
    return record


def good_outcome(**overrides):
    outcome = {
        "decision_id": "DR-001",
        "expected": "春茶季销量提升 30%",
        "actual": "实际提升 12%，未达预期",
        "deviation_type": "EXECUTION",
        "evidence_ids": ["E-001"],
        "next_action": "ADJUST",
        "notes": "投放量不足，不是方向错误",
    }
    outcome.update(overrides)
    return outcome


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "proj"
        shutil.copytree(EXAMPLE, self.dir)
        self.store = D.DecisionStore(self.dir)

    def tearDown(self):
        self._tmp.cleanup()


class WriteTests(Base):
    def test_add_assigns_id_and_persists(self):
        saved = self.store.add(good_record())
        self.assertEqual(saved["decision_id"], "DR-001")
        self.assertTrue((self.dir / "decisions" / "DR-001.json").exists())

    def test_ids_increment(self):
        self.assertEqual(self.store.add(good_record())["decision_id"], "DR-001")
        self.assertEqual(self.store.add(good_record())["decision_id"], "DR-002")

    def test_rejects_schema_violation(self):
        with self.assertRaises(D.DecisionError) as ctx:
            self.store.add(good_record(options=[{"name": "唯一选项", "rationale": "r"}]))
        self.assertIn("decision_record.schema.json", str(ctx.exception))

    def test_rejects_missing_required_field(self):
        record = good_record()
        del record["falsification_conditions"]
        with self.assertRaises(D.DecisionError):
            self.store.add(record)

    def test_rejects_duplicate_id(self):
        self.store.add(good_record(decision_id="DR-001"))
        with self.assertRaises(D.DecisionError) as ctx:
            self.store.add(good_record(decision_id="DR-001"))
        self.assertIn("已存在", str(ctx.exception))

    def test_corrupt_decision_file_raises(self):
        self.store.add(good_record())
        (self.dir / "decisions" / "DR-001.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(D.DecisionError):
            self.store.list()


class QualityWarningTests(Base):
    def test_missing_review_date_warns(self):
        self.store.add(good_record(review_date=""))
        _, warnings = self.store.validate()
        self.assertTrue(any("复审日期" in w for w in warnings), warnings)

    def test_missing_falsification_warns(self):
        self.store.add(good_record(falsification_conditions=[]))
        _, warnings = self.store.validate()
        self.assertTrue(any("反证条件" in w for w in warnings), warnings)

    def test_missing_tradeoffs_warns(self):
        self.store.add(good_record(tradeoffs=[]))
        _, warnings = self.store.validate()
        self.assertTrue(any("代价" in w for w in warnings), warnings)

    def test_chosen_not_among_options_warns(self):
        self.store.add(good_record(chosen_option="第三个方案"))
        _, warnings = self.store.validate()
        self.assertTrue(any("不在候选方案列表" in w for w in warnings), warnings)

    def test_duplicate_option_names_warn(self):
        self.store.add(good_record(options=[
            {"name": "A", "rationale": "r1"},
            {"name": "A", "rationale": "r2"},
        ], chosen_option="A"))
        _, warnings = self.store.validate()
        self.assertTrue(any("同名选项" in w for w in warnings), warnings)

    def test_expired_deadline_warns(self):
        self.store.add(good_record(deadline="2000-01-01"))
        _, warnings = self.store.validate()
        self.assertTrue(any("已过期" in w for w in warnings), warnings)

    def test_clean_record_has_no_warnings(self):
        self.store.add(good_record())
        errors, warnings = self.store.validate()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [], warnings)


class OutcomeTests(Base):
    def test_records_outcome(self):
        self.store.add(good_record())
        saved = self.store.record_outcome(good_outcome())
        self.assertEqual(saved["deviation_type"], "EXECUTION")
        self.assertIsNotNone(self.store.outcome_of("DR-001"))

    def test_rejects_outcome_for_unknown_decision(self):
        with self.assertRaises(D.DecisionError) as ctx:
            self.store.record_outcome(good_outcome(decision_id="DR-999"))
        self.assertIn("找不到决策记录", str(ctx.exception))

    def test_rejects_vague_actual(self):
        self.store.add(good_record())
        with self.assertRaises(D.DecisionError) as ctx:
            self.store.record_outcome(good_outcome(actual="不错"))
        self.assertIn("actual 过短", str(ctx.exception))

    def test_unknown_deviation_requires_notes(self):
        self.store.add(good_record())
        with self.assertRaises(D.DecisionError) as ctx:
            self.store.record_outcome(
                good_outcome(deviation_type="UNKNOWN", notes=None)
            )
        self.assertIn("无法归因", str(ctx.exception))

    def test_rejects_invalid_deviation_type(self):
        self.store.add(good_record())
        with self.assertRaises(D.DecisionError):
            self.store.record_outcome(good_outcome(deviation_type="WHATEVER"))

    def test_rejects_missing_expected(self):
        self.store.add(good_record())
        outcome = good_outcome()
        del outcome["expected"]
        with self.assertRaises(D.DecisionError):
            self.store.record_outcome(outcome)


class ProjectSyncTests(Base):
    def test_decision_records_written_back_to_project_json(self):
        self.store.add(good_record())
        project = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(len(project["decision_records"]), 1)
        entry = project["decision_records"][0]
        self.assertEqual(entry["decision_id"], "DR-001")
        self.assertEqual(entry["status"], "PENDING_REVIEW")
        self.assertIsNone(entry["outcome"])

    def test_status_becomes_reviewed_after_outcome(self):
        self.store.add(good_record())
        self.store.record_outcome(good_outcome())
        project = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        entry = project["decision_records"][0]
        self.assertEqual(entry["status"], "REVIEWED")
        self.assertEqual(entry["outcome"]["next_action"], "ADJUST")

    def test_sync_works_without_project_file(self):
        lonely = Path(self._tmp.name) / "lonely"
        lonely.mkdir()
        store = D.DecisionStore(lonely)
        store.add(good_record())          # 不应抛错
        self.assertEqual(len(store.list()), 1)


class DueTests(Base):
    def test_overdue_is_listed(self):
        self.store.add(good_record(review_date="2026-05-01"))
        report = self.store.due_for_review(today=date(2026, 5, 10))
        self.assertEqual(len(report["overdue"]), 1)
        self.assertEqual(report["overdue"][0]["days_overdue"], 9)

    def test_upcoming_is_listed(self):
        self.store.add(good_record(review_date="2026-06-01"))
        report = self.store.due_for_review(today=date(2026, 5, 10))
        self.assertEqual(len(report["upcoming"]), 1)
        self.assertEqual(report["upcoming"][0]["days_remaining"], 22)

    def test_reviewed_is_excluded_from_overdue(self):
        self.store.add(good_record(review_date="2026-05-01"))
        self.store.record_outcome(good_outcome())
        report = self.store.due_for_review(today=date(2026, 5, 10))
        self.assertEqual(report["overdue"], [])
        self.assertEqual(len(report["reviewed"]), 1)

    def test_unparseable_review_date_is_flagged(self):
        self.store.add(good_record(review_date="下个月"))
        report = self.store.due_for_review(today=date(2026, 5, 10))
        self.assertEqual(len(report["overdue"]), 1)
        self.assertIn("reason", report["overdue"][0])

    def test_overdue_sorted_by_most_overdue_first(self):
        self.store.add(good_record(review_date="2026-05-01"))   # DR-001
        self.store.add(good_record(review_date="2026-01-01"))   # DR-002
        report = self.store.due_for_review(today=date(2026, 5, 10))
        self.assertEqual(
            [e["decision_id"] for e in report["overdue"]], ["DR-002", "DR-001"]
        )


class ExportTests(Base):
    def test_markdown_includes_decision_and_outcome(self):
        self.store.add(good_record())
        self.store.record_outcome(good_outcome())
        text = self.store.to_markdown()
        self.assertIn("DR-001", text)
        self.assertIn("春茶季集中投放", text)
        self.assertIn("执行偏差", text)
        self.assertIn("调整", text)

    def test_markdown_marks_unreviewed(self):
        self.store.add(good_record())
        self.assertIn("尚未复盘", self.store.to_markdown())

    def test_empty_store_message(self):
        self.assertIn("尚无决策记录", self.store.to_markdown())


class SchemaTests(unittest.TestCase):
    def test_outcome_schema_exists_and_parses(self):
        path = ROOT / "schemas" / "outcome.schema.json"
        self.assertTrue(path.exists())
        with path.open(encoding="utf-8") as handle:
            self.assertIsInstance(json.load(handle), dict)


if __name__ == "__main__":
    unittest.main()
