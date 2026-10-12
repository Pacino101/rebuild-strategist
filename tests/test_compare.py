"""多次运行比对的测试。

重点：**过程可复现性**与**结论一致性**必须分开。
把「迁移路径相同」说成「建议相同」是这类工具最容易犯的错。
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))

import compare as C  # noqa: E402
import orchestrator as O  # noqa: E402

EXAMPLE = ROOT / "examples" / "nanjiang_tea"


def make_report(run_id="r1", path=None, final="REVIEW", grades=None,
                chosen="方案甲", counts=None):
    """构造一份最小可比的 run.json 结构。"""
    path = path or [("DISCOVER", "evidence_ready", "EVIDENCE"),
                    ("EVIDENCE", "evidence_sufficient", "STRATEGY")]
    grades = grades or {"DISCOVER": "DEGRADED", "EVIDENCE": "DEGRADED"}
    counts = counts or {"options": 3, "falsification": 8, "validation": 8,
                        "rejected": 2, "assumptions": 4}
    phases = []
    for index, (phase, event, to) in enumerate(path):
        phases.append({
            "phase": phase,
            "transition": {"from": phase, "event": event, "to": to},
            "gate": {"evidence_grade": grades.get(phase, "DEGRADED"),
                     "passed": True, "event": event},
            "role_outputs": {"x": "y"},
        })
    phases.append({
        "phase": path[-1][2],
        "gate": {"evidence_grade": grades.get(path[-1][2], "DEGRADED")},
        "role_outputs": {"x": "y"},
    })
    record = {
        "decision_id": "DR-001", "question": "q", "chosen_option": chosen,
        "options": [{"name": "a", "rationale": "r"}] * counts["options"],
        "rejected_options": [{"name": "b", "reason": "r"}] * counts["rejected"],
        "falsification_conditions": ["x"] * counts["falsification"],
        "validation_actions": ["x"] * counts["validation"],
        "key_assumptions": ["x"] * counts["assumptions"],
    }
    return {
        "run_id": run_id, "final_state": final, "phases": phases,
        "decision_record": {"record": record, "schema_errors": [],
                            "schema_warnings": []},
        "initial_state": "DISCOVER",
    }


class VerdictTests(unittest.TestCase):
    def test_identical_paths(self):
        reports = [make_report("r1"), make_report("r2")]
        self.assertEqual(C.compare(reports)["process_verdict"], C.PATH_IDENTICAL)

    def test_same_outcome_different_path(self):
        reports = [
            make_report("r1"),
            make_report("r2", path=[("DISCOVER", "need_clarification", "BLOCKED")],
                        final="REVIEW"),
        ]
        result = C.compare(reports)
        self.assertEqual(result["process_verdict"], C.OUTCOME_IDENTICAL)
        self.assertTrue(result["final_state_consistent"])
        self.assertFalse(result["path_consistent"])

    def test_divergent_outcomes(self):
        reports = [
            make_report("r1", final="REVIEW"),
            make_report("r2", path=[("DISCOVER", "need_clarification", "BLOCKED")],
                        final="BLOCKED"),
        ]
        result = C.compare(reports)
        self.assertEqual(result["process_verdict"], C.OUTCOME_DIVERGENT)
        self.assertFalse(result["final_state_consistent"])
        self.assertEqual(result["final_states"], {"REVIEW": 1, "BLOCKED": 1})

    def test_requires_two_runs(self):
        with self.assertRaises(C.CompareError):
            C.compare([make_report()])


class DistributionTests(unittest.TestCase):
    def test_gate_grade_distribution_flags_inconsistency(self):
        reports = [
            make_report("r1", grades={"DISCOVER": "DEGRADED", "EVIDENCE": "DEGRADED"}),
            make_report("r2", grades={"DISCOVER": "DEGRADED", "EVIDENCE": "INSUFFICIENT"}),
        ]
        grades = C.compare(reports)["gate_grades"]
        self.assertTrue(grades["DISCOVER"]["consistent"])
        self.assertFalse(grades["EVIDENCE"]["consistent"])
        self.assertEqual(grades["EVIDENCE"]["distribution"],
                         {"DEGRADED": 1, "INSUFFICIENT": 1})

    def test_count_spread_quantifies_detail_drift(self):
        reports = [
            make_report("r1", counts={"options": 3, "falsification": 6,
                                      "validation": 8, "rejected": 2, "assumptions": 4}),
            make_report("r2", counts={"options": 3, "falsification": 15,
                                      "validation": 12, "rejected": 2, "assumptions": 6}),
        ]
        counts = C.compare(reports)["counts"]
        self.assertEqual(counts["falsification"]["range"], 9)
        self.assertEqual(counts["falsification"]["min"], 6)
        self.assertEqual(counts["falsification"]["max"], 15)
        self.assertEqual(counts["options"]["range"], 0)

    def test_caveat_says_process_is_not_conclusion(self):
        result = C.compare([make_report(), make_report()])
        self.assertIn("不等于", result["caveat"])


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "runs").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, report):
        target = self.dir / "runs" / name
        target.mkdir(exist_ok=True)
        (target / "run.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )

    def test_missing_runs_dir(self):
        with self.assertRaises(C.CompareError):
            C.collect_runs(self.dir / "nope")

    def test_empty_runs_dir(self):
        with self.assertRaises(C.CompareError):
            C.collect_runs(self.dir)

    def test_sorted_and_limited(self):
        for name in ("20260101-000003", "20260101-000001", "20260101-000002"):
            self._write(name, make_report(name))
        self.assertEqual([r["run_id"] for r in C.collect_runs(self.dir)],
                         ["20260101-000001", "20260101-000002", "20260101-000003"])
        self.assertEqual([r["run_id"] for r in C.collect_runs(self.dir, last=2)],
                         ["20260101-000002", "20260101-000003"])

    def test_load_run_rejects_plain_dir(self):
        with self.assertRaises(C.CompareError):
            C.load_run(self.dir)


class JudgeTests(unittest.TestCase):
    def test_judge_parses_verdict_and_marks_it_model_judged(self):
        def fake_call(prompt):
            self.assertIn("各次运行的建议", prompt)
            return json.dumps({"agree": True, "direction": "都主张先验证",
                               "groups": [["r1", "r2"]], "why": "三次均要求补证",
                               "confidence": "MEDIUM"}, ensure_ascii=False)

        verdict = C.judge_agreement([make_report("r1"), make_report("r2")], fake_call)
        self.assertTrue(verdict["agree"])
        self.assertTrue(verdict["judged_by_model"])
        self.assertIn("模型判定", verdict["caveat"])

    def test_judge_handles_unparseable_output(self):
        verdict = C.judge_agreement(
            [make_report("r1"), make_report("r2")], lambda p: "我觉得差不多吧"
        )
        self.assertIn("error", verdict)
        self.assertTrue(verdict["judged_by_model"])

    def test_judge_includes_all_runs(self):
        seen = {}

        def fake_call(prompt):
            seen["prompt"] = prompt
            return json.dumps({"agree": True})

        C.judge_agreement([make_report("r1"), make_report("r2"),
                           make_report("r3")], fake_call)
        for token in ("r1", "r2", "r3"):
            self.assertIn(token, seen["prompt"])

    def test_judge_requires_two_runs(self):
        with self.assertRaises(C.CompareError):
            C.judge_agreement([make_report()], lambda p: "{}")


class RenderTests(unittest.TestCase):
    def test_markdown_contains_both_axes(self):
        text = C.render_markdown(C.compare([make_report("r1"), make_report("r2")]))
        self.assertIn("过程可复现性", text)
        self.assertIn("结论一致性", text)
        self.assertIn("模型判定", text)
        self.assertIn("PATH_IDENTICAL", text)

    def test_markdown_lists_each_run(self):
        text = C.render_markdown(
            C.compare([make_report("r1", chosen="方案甲"),
                       make_report("r2", chosen="方案乙")])
        )
        self.assertIn("方案甲", text)
        self.assertIn("方案乙", text)


class UsageAggregationTests(unittest.TestCase):
    def _with_usage(self, run_id, tokens, cost, seconds=10.0):
        report = make_report(run_id)
        report["usage"] = {"calls": 20, "calls_with_usage": 20,
                           "total_tokens": tokens, "seconds": seconds}
        report["cost_estimate"] = {"total": cost, "currency": "USD"}
        return report

    def test_totals_summed(self):
        result = C.compare([self._with_usage("r1", 1000, 0.1),
                            self._with_usage("r2", 2000, 0.2)])
        total = result["total_usage"]
        self.assertEqual(total["total_tokens"], 3000)
        self.assertAlmostEqual(total["cost_total"], 0.3)
        self.assertEqual(total["calls"], 40)

    def test_incomplete_tokens_are_flagged_not_summed(self):
        good = self._with_usage("r1", 1000, 0.1)
        bad = make_report("r2")
        bad["usage"] = {"calls": 20, "calls_with_usage": 0, "total_tokens": None,
                        "seconds": 5.0}
        total = C.compare([good, bad])["total_usage"]
        self.assertIsNone(total["total_tokens"])
        self.assertTrue(total["tokens_incomplete"])

    def test_no_pricing_reports_zero_cost_info(self):
        result = C.compare([make_report("r1"), make_report("r2")])
        self.assertIsNone(result["total_usage"]["cost_total"])
        self.assertIn("未提供单价", result["total_usage"]["cost_note"])

    def test_markdown_has_cost_section(self):
        text = C.render_markdown(C.compare([self._with_usage("r1", 1000, 0.1),
                                            self._with_usage("r2", 2000, 0.2)]))
        self.assertIn("成本与耗时", text)
        self.assertIn("3,000", text)
        self.assertIn("0.3", text)


class NullChoiceRenderTests(unittest.TestCase):
    def test_null_choice_is_distinguished_from_missing_record(self):
        with_null = make_report("r1")
        with_null["decision_record"]["record"]["chosen_option"] = None
        missing = make_report("r2")
        missing["decision_record"] = {}
        text = C.render_markdown(C.compare([with_null, missing]))
        self.assertIn("本轮未做出选择", text)
        self.assertIn("未产出决策记录", text)


class RepeatedRunTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "proj"
        shutil.copytree(EXAMPLE, self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def _completer(self, prompt):
        if "门禁判定" in prompt:
            if "阶段 DISCOVER" in prompt:
                return json.dumps({"event": "evidence_ready", "passed": True,
                                   "reason": "ok"})
            return json.dumps({"event": "", "passed": False, "reason": "停"})
        if "各阶段输出摘要" in prompt:
            return json.dumps({
                "decision_id": "DR-001", "question": "q",
                "options": [{"name": "a", "rationale": "r"},
                            {"name": "b", "rationale": "r"}],
                "chosen_option": "a", "rejected_options": [],
                "tradeoffs": [], "key_assumptions": [],
                "falsification_conditions": [], "validation_actions": [],
                "review_date": "2099-01-01",
            }, ensure_ascii=False)
        return "# 输出"

    def test_repeated_runs_reset_state_between_iterations(self):
        config = O.RunConfig(project_dir=self.dir, provider_name="fake",
                             phases=["DISCOVER"])
        reports = O.run_repeated(config, 3, completer=self._completer)
        self.assertEqual(len(reports), 3)
        # 每次都从 DISCOVER 出发
        for report in reports:
            self.assertEqual(report["initial_state"], "DISCOVER")
            self.assertEqual(report["final_state"], "EVIDENCE")

    def test_repeated_runs_get_distinct_directories(self):
        config = O.RunConfig(project_dir=self.dir, provider_name="fake",
                             phases=["DISCOVER"])
        reports = O.run_repeated(config, 3, completer=self._completer)
        dirs = {r["run_dir"] for r in reports}
        self.assertEqual(len(dirs), 3)

    def test_project_state_restored_after_repeats(self):
        before = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        config = O.RunConfig(project_dir=self.dir, provider_name="fake",
                             phases=["DISCOVER"])
        O.run_repeated(config, 2, completer=self._completer)
        after = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(before["current_state"], after["current_state"])

    def test_repeats_must_be_positive(self):
        config = O.RunConfig(project_dir=self.dir, provider_name="fake",
                             phases=["DISCOVER"])
        with self.assertRaises(O.OrchestratorError):
            O.run_repeated(config, 0, completer=self._completer)

    def test_collect_and_compare_end_to_end(self):
        config = O.RunConfig(project_dir=self.dir, provider_name="fake",
                             phases=["DISCOVER"])
        O.run_repeated(config, 2, completer=self._completer)
        result = C.compare(C.collect_runs(self.dir))
        self.assertEqual(result["runs"], 2)
        self.assertEqual(result["process_verdict"], C.PATH_IDENTICAL)


if __name__ == "__main__":
    unittest.main()
