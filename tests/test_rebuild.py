"""状态机与项目校验测试。

注：`rebuild_cli.validate_project()` 自 V3.3.0 起返回 `(errors, warnings)`
元组（此前只返回 errors 列表），以便把「schema 中未被检查的约束」暴露出来。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
import rebuild_cli  # noqa: E402

EXAMPLE = ROOT / "examples" / "nanjiang_tea" / "project.json"


class StateMachineTests(unittest.TestCase):
    def test_valid_transition(self):
        self.assertEqual(
            rebuild_cli.transition("DISCOVER", "evidence_ready")["to"], "EVIDENCE"
        )

    def test_invalid_transition_rejected(self):
        with self.assertRaises(ValueError):
            rebuild_cli.transition("DISCOVER", "decision_closed")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            rebuild_cli.transition("MAGIC", "evidence_ready")

    def test_error_message_lists_legal_events(self):
        with self.assertRaises(ValueError) as ctx:
            rebuild_cli.transition("DISCOVER", "nonsense")
        self.assertIn("evidence_ready", str(ctx.exception))


class ProjectTests(unittest.TestCase):
    def test_example_project_valid(self):
        errors, warnings = rebuild_cli.validate_project(EXAMPLE)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [], f"有未被检查的约束：{warnings}")

    def test_missing_fields_detected(self):
        # 临时文件写在系统临时目录，不污染仓库
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            path.write_text(json.dumps({"project_id": "x"}), encoding="utf-8")
            errors, _ = rebuild_cli.validate_project(path)
            self.assertTrue(any("decision_question" in e for e in errors), errors)

    def test_schema_check_can_be_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            path.write_text(json.dumps({
                "project_id": "x", "name": "n", "decision_question": "q",
                "current_state": "DISCOVER", "goals": [], "constraints": [],
            }), encoding="utf-8")
            errors, warnings = rebuild_cli.validate_project(path, use_schema=False)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_schema_check_rejects_undeclared_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            path.write_text(json.dumps({
                "project_id": "x", "name": "n", "decision_question": "q",
                "current_state": "DISCOVER", "goals": [], "constraints": [],
                "surprise": True,
            }), encoding="utf-8")
            errors, _ = rebuild_cli.validate_project(path)
            self.assertTrue(any("surprise" in e for e in errors), errors)

    def test_schema_check_rejects_unknown_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            path.write_text(json.dumps({
                "project_id": "x", "name": "n", "decision_question": "q",
                "current_state": "WOBBLING", "goals": [], "constraints": [],
            }), encoding="utf-8")
            errors, _ = rebuild_cli.validate_project(path)
            self.assertTrue(any("current_state" in e for e in errors), errors)

    def test_project_dir_helper_accepts_both_forms(self):
        self.assertEqual(
            rebuild_cli.project_dir_of(EXAMPLE), EXAMPLE.parent
        )
        self.assertEqual(
            rebuild_cli.project_dir_of(EXAMPLE.parent), EXAMPLE.parent
        )

    def test_project_dir_helper_rejects_other_files(self):
        with self.assertRaises(ValueError):
            rebuild_cli.project_dir_of(ROOT / "README.md")


if __name__ == "__main__":
    unittest.main()
