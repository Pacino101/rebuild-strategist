"""schema_validator 的测试。

重点不只是「能校验」，还包括：未实现的关键字必须报警而不是静默通过。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

import schema_validator as sv


class TypeCheckTests(unittest.TestCase):
    def test_integer_rejects_bool(self):
        # bool 是 int 的子类，最容易写错的一处
        errors, _ = sv.validate(True, {"type": "integer"})
        self.assertTrue(errors)

    def test_number_accepts_integer(self):
        errors, _ = sv.validate(7, {"type": "number"})
        self.assertEqual(errors, [])

    def test_type_union(self):
        schema = {"type": ["string", "null"]}
        self.assertEqual(sv.validate(None, schema)[0], [])
        self.assertEqual(sv.validate("x", schema)[0], [])
        self.assertTrue(sv.validate(3, schema)[0])

    def test_type_mismatch_stops_further_checks(self):
        # 类型不符时应立即返回，不应再报一堆字段级噪音
        errors, _ = sv.validate("not-an-object",
                                {"type": "object", "required": ["a", "b"]})
        self.assertEqual(len(errors), 1)


class ObjectTests(unittest.TestCase):
    def test_required_missing(self):
        errors, _ = sv.validate({}, {"type": "object", "required": ["a"]})
        self.assertTrue(any("缺少必填字段 'a'" in e for e in errors))

    def test_additional_properties_false(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}},
                  "additionalProperties": False}
        self.assertEqual(sv.validate({"a": "x"}, schema)[0], [])
        self.assertTrue(sv.validate({"a": "x", "b": 1}, schema)[0])

    def test_nested_path_in_error_message(self):
        schema = {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {"type": "object",
                              "properties": {"name": {"type": "string"}},
                              "required": ["name"]},
                }
            },
        }
        errors, _ = sv.validate({"options": [{"name": "ok"}, {}]}, schema)
        self.assertTrue(any("$.options[1]" in e for e in errors), errors)


class StringNumberArrayTests(unittest.TestCase):
    def test_min_length(self):
        self.assertTrue(sv.validate("", {"type": "string", "minLength": 1})[0])

    def test_pattern(self):
        schema = {"type": "string", "pattern": r"^[a-z]+$"}
        self.assertEqual(sv.validate("abc", schema)[0], [])
        self.assertTrue(sv.validate("ABC", schema)[0])

    def test_minimum(self):
        self.assertTrue(sv.validate(-1, {"type": "number", "minimum": 0})[0])

    def test_min_items(self):
        schema = {"type": "array", "minItems": 2}
        self.assertTrue(sv.validate([1], schema)[0])
        self.assertEqual(sv.validate([1, 2], schema)[0], [])

    def test_enum(self):
        schema = {"enum": ["FACT", "INFERENCE"]}
        self.assertEqual(sv.validate("FACT", schema)[0], [])
        self.assertTrue(sv.validate("GUESS", schema)[0])


class HonestyTests(unittest.TestCase):
    """本项目最核心的一条：不能假装检查过没有检查的东西。"""

    def test_unknown_keyword_produces_warning_not_silent_pass(self):
        errors, warnings = sv.validate("x", {"type": "string", "format": "email"})
        self.assertEqual(errors, [])
        self.assertTrue(any("format" in w for w in warnings), warnings)

    def test_ref_is_reported_as_unimplemented(self):
        errors, warnings = sv.validate({}, {"$ref": "#/definitions/x"})
        self.assertTrue(any("$ref" in w for w in warnings), warnings)

    def test_unknown_type_value_warns(self):
        errors, warnings = sv.validate("x", {"type": "strin"})
        self.assertTrue(any("未知的 type" in w for w in warnings), warnings)


class CombinatorTests(unittest.TestCase):
    def test_any_of(self):
        schema = {"anyOf": [{"type": "string"}, {"type": "number"}]}
        self.assertEqual(sv.validate("x", schema)[0], [])
        self.assertTrue(sv.validate([], schema)[0])

    def test_one_of_rejects_multiple_matches(self):
        schema = {"oneOf": [{"type": "number"}, {"type": "integer"}]}
        # 整数同时满足两个分支 -> oneOf 应失败
        self.assertTrue(sv.validate(3, schema)[0])

    def test_all_of(self):
        schema = {"allOf": [{"type": "string"}, {"minLength": 3}]}
        self.assertEqual(sv.validate("abc", schema)[0], [])
        self.assertTrue(sv.validate("ab", schema)[0])


class RealSchemaTests(unittest.TestCase):
    """用仓库里真实的 schema 与示例做回归。"""

    SCHEMAS = ["project", "evidence", "decision_record", "experiment", "kpi_tree"]

    def test_all_repo_schemas_parse(self):
        for name in self.SCHEMAS:
            path = ROOT / "schemas" / f"{name}.schema.json"
            self.assertTrue(path.exists(), f"{path} 不存在")
            with path.open(encoding="utf-8") as handle:
                self.assertIsInstance(json.load(handle), dict)

    def test_example_project_conforms_to_project_schema(self):
        errors, warnings = sv.validate_file(
            ROOT / "examples/nanjiang_tea/project.json",
            ROOT / "schemas/project.schema.json",
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [], f"有未被检查的约束：{warnings}")

    def test_project_schema_catches_bad_state(self):
        instance = json.loads(
            (ROOT / "examples/nanjiang_tea/project.json").read_text(encoding="utf-8")
        )
        instance["current_state"] = "NOT_A_STATE"
        errors, _ = sv.validate(instance, sv.load_schema(ROOT / "schemas/project.schema.json"))
        self.assertTrue(any("current_state" in e for e in errors), errors)

    def test_evidence_schema_rejects_fabricated_type(self):
        record = {
            "id": "E-1", "claim": "x", "type": "GUESS",
            "confidence": "HIGH", "scope": "s", "decision_impact": "d",
        }
        errors, _ = sv.validate(record, sv.load_schema(ROOT / "schemas/evidence.schema.json"))
        self.assertTrue(any("type" in e for e in errors), errors)

    def test_decision_record_requires_two_options(self):
        record = {
            "decision_id": "D-1", "question": "q", "options": [{"name": "a", "rationale": "r"}],
            "chosen_option": "a", "rejected_options": [], "tradeoffs": [],
            "key_assumptions": [], "falsification_conditions": [],
            "validation_actions": [], "review_date": "2026-01-01",
        }
        errors, _ = sv.validate(
            record, sv.load_schema(ROOT / "schemas/decision_record.schema.json")
        )
        self.assertTrue(any("minItems" in e or "元素数" in e for e in errors), errors)

    def test_no_unknown_keywords_in_repo_schemas(self):
        """仓库自己的 schema 不应触发未实现关键字警告。"""
        for name in self.SCHEMAS:
            path = ROOT / "schemas" / f"{name}.schema.json"
            with path.open(encoding="utf-8") as handle:
                schema = json.load(handle)
            _, warnings = sv.validate({}, schema)
            stray = [w for w in warnings if "未实现的关键字" in w]
            self.assertEqual(stray, [], f"{name}: {stray}")


class HelperTests(unittest.TestCase):
    def test_guess_schema(self):
        guess = sv.guess_schema("some/dir/project.json", ROOT / "schemas")
        self.assertIsNotNone(guess)
        self.assertEqual(guess.name, "project.schema.json")

    def test_guess_schema_returns_none_for_unknown(self):
        self.assertIsNone(sv.guess_schema("mystery.json", ROOT / "schemas"))

    def test_validate_file_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                sv.validate_file(Path(tmp) / "nope.json", ROOT / "schemas/project.schema.json")


if __name__ == "__main__":
    unittest.main()
