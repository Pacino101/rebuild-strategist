"""证据账本测试。

除功能外，重点验证「坏数据不会被悄悄接受」：
不符合 schema 的记录拒绝写入、账本坏行报错而不是跳过、
以及 schema 管不到的语义问题会被报成 warning。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

import ledger as L


def good_record(**overrides):
    record = {
        "claim": "目标客户在春茶季前两周集中比价",
        "type": "FACT",
        "source": "访谈 F-03 / 2026-03-11",
        "observed_at": "2026-03-11",
        "confidence": "MEDIUM",
        "scope": "云南南涧县内 35–55 岁自饮客群",
        "counter_evidence": [],
        "decision_impact": "决定是否把预算从全年均投改为春茶季集中投放",
        "recheck_trigger": None,
    }
    record.update(overrides)
    return record


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.ledger = L.Ledger(self.dir)

    def tearDown(self):
        self._tmp.cleanup()


class WriteTests(LedgerTestCase):
    def test_add_and_load_roundtrip(self):
        added = self.ledger.add(good_record())
        self.assertEqual(added["id"], "E-001")
        records = self.ledger.load()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["claim"], "目标客户在春茶季前两周集中比价")

    def test_ids_increment(self):
        self.assertEqual(self.ledger.add(good_record())["id"], "E-001")
        self.assertEqual(self.ledger.add(good_record())["id"], "E-002")
        self.assertEqual(self.ledger.add(good_record())["id"], "E-003")

    def test_rejects_schema_violation(self):
        with self.assertRaises(L.EvidenceError) as ctx:
            self.ledger.add(good_record(type="GUESS"))
        self.assertIn("evidence.schema.json", str(ctx.exception))
        self.assertFalse(self.ledger.exists, "非法记录不应产生账本文件")

    def test_rejects_missing_required_field(self):
        record = good_record()
        del record["decision_impact"]
        with self.assertRaises(L.EvidenceError):
            self.ledger.add(record)

    def test_rejects_unknown_extra_field(self):
        with self.assertRaises(L.EvidenceError):
            self.ledger.add(good_record(note="schema 未声明的字段"))

    def test_rejects_duplicate_id(self):
        self.ledger.add(good_record(id="E-001"))
        with self.assertRaises(L.EvidenceError) as ctx:
            self.ledger.add(good_record(id="E-001"))
        self.assertIn("已存在", str(ctx.exception))

    def test_chinese_survives_roundtrip(self):
        self.ledger.add(good_record())
        raw = self.ledger.path.read_text(encoding="utf-8")
        self.assertIn("春茶季", raw, "不应被转义成 \\u 序列")


class CorruptionTests(LedgerTestCase):
    def test_corrupt_line_raises_not_skipped(self):
        self.ledger.add(good_record())
        with self.ledger.path.open("a", encoding="utf-8") as handle:
            handle.write("{ this is not json }\n")
        with self.assertRaises(L.EvidenceError) as ctx:
            self.ledger.load()
        self.assertIn("不是合法 JSON", str(ctx.exception))

    def test_validate_reports_corruption_as_error(self):
        self.ledger.path.write_text("garbage\n", encoding="utf-8")
        errors, _ = self.ledger.validate()
        self.assertTrue(errors)


class QualityWarningTests(LedgerTestCase):
    def test_fact_without_source_warns(self):
        self.ledger.add(good_record(source=None))
        _, warnings = self.ledger.validate()
        self.assertTrue(any("FACT 但未提供 source" in w for w in warnings), warnings)

    def test_assumption_without_recheck_warns(self):
        self.ledger.add(good_record(type="ASSUMPTION", confidence="LOW"))
        _, warnings = self.ledger.validate()
        self.assertTrue(any("recheck_trigger" in w for w in warnings), warnings)

    def test_assumption_with_recheck_is_fine(self):
        self.ledger.add(good_record(
            type="ASSUMPTION", confidence="LOW",
            recheck_trigger="若 4 月复购率低于 15% 则重查",
        ))
        _, warnings = self.ledger.validate()
        self.assertFalse([w for w in warnings if "recheck_trigger" in w])

    def test_unknown_with_high_confidence_warns(self):
        self.ledger.add(good_record(type="UNKNOWN", confidence="HIGH"))
        _, warnings = self.ledger.validate()
        self.assertTrue(any("UNKNOWN" in w and "可信度" in w for w in warnings), warnings)

    def test_empty_decision_impact_warns(self):
        self.ledger.add(good_record(decision_impact="无"))
        _, warnings = self.ledger.validate()
        self.assertTrue(any("会改变什么决策" in w for w in warnings), warnings)

    def test_fact_with_low_confidence_warns(self):
        self.ledger.add(good_record(confidence="LOW"))
        _, warnings = self.ledger.validate()
        self.assertTrue(any("语义冲突" in w for w in warnings), warnings)

    def test_clean_record_has_no_warnings(self):
        self.ledger.add(good_record())
        errors, warnings = self.ledger.validate()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [], warnings)


class QueryTests(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.ledger.add(good_record(claim="事实一", type="FACT", confidence="HIGH"))
        self.ledger.add(good_record(claim="推断一", type="INFERENCE", confidence="MEDIUM"))
        self.ledger.add(good_record(
            claim="假设一", type="ASSUMPTION", confidence="LOW",
            recheck_trigger="触发条件", source=None,
        ))

    def test_filter_by_type(self):
        self.assertEqual(len(self.ledger.filter(kind="FACT")), 1)

    def test_filter_by_min_confidence(self):
        self.assertEqual(len(self.ledger.filter(min_confidence="MEDIUM")), 2)

    def test_summary(self):
        summary = self.ledger.summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_type"]["FACT"], 1)
        self.assertEqual(summary["by_type"]["ASSUMPTION"], 1)

    def test_high_leverage_finds_low_confidence_assumptions(self):
        picked = self.ledger.high_leverage()
        self.assertEqual([r["claim"] for r in picked], ["假设一"])


class GapTests(LedgerTestCase):
    def test_reports_uncovered_assumptions(self):
        project = self.dir / "project.json"
        project.write_text(json.dumps({
            "project_id": "P", "name": "n", "decision_question": "q",
            "current_state": "DISCOVER", "goals": [], "constraints": [],
            "assumptions": ["复购率能达到 20%", "春茶季前两周完成投放"],
            "unknowns": ["真实获客成本"],
            "known_facts": [],
        }, ensure_ascii=False), encoding="utf-8")

        self.ledger.add(good_record(claim="春茶季前两周完成投放是可行的"))

        report = L.gaps(project)
        self.assertIn("复购率能达到 20%", report["assumptions_without_evidence"])
        self.assertNotIn("春茶季前两周完成投放", report["assumptions_without_evidence"])
        self.assertEqual(report["unknowns_without_evidence"], ["真实获客成本"])

    def test_short_text_does_not_falsely_match(self):
        project = self.dir / "project.json"
        project.write_text(json.dumps({
            "project_id": "P", "name": "n", "decision_question": "q",
            "current_state": "DISCOVER", "goals": [], "constraints": [],
            "assumptions": ["成本"], "unknowns": [], "known_facts": [],
        }, ensure_ascii=False), encoding="utf-8")
        self.ledger.add(good_record(claim="成本结构在淡旺季差异极大"))
        report = L.gaps(project)
        self.assertEqual(report["assumptions_without_evidence"], ["成本"])


class ExportTests(LedgerTestCase):
    def test_markdown_contains_ledger_rows(self):
        self.ledger.add(good_record(claim="事实一"))
        text = L.to_markdown(self.dir)
        self.assertIn("# 证据账本", text)
        self.assertIn("事实一", text)
        self.assertIn("E-001", text)

    def test_markdown_handles_empty_ledger(self):
        text = L.to_markdown(self.dir)
        self.assertIn("共 0 条", text)

    def test_markdown_escapes_pipe(self):
        self.ledger.add(good_record(claim="A | B"))
        text = L.to_markdown(self.dir)
        self.assertIn("A \\| B", text)


if __name__ == "__main__":
    unittest.main()
