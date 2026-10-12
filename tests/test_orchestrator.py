"""运行时编排器测试。

全部使用注入的假 completer，不产生任何网络请求。
重点验证编排器**不会替模型越权**：
- 模型给出非法状态迁移时必须被拒绝；
- 模型提出的证据不得自动进入证据账本。
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

import ledger as ledger_module  # noqa: E402
import orchestrator as O  # noqa: E402

EXAMPLE = ROOT / "examples" / "nanjiang_tea"

#: 各阶段「向前推进」应使用的事件
FORWARD_EVENT = {
    "DISCOVER": "evidence_ready",
    "EVIDENCE": "evidence_sufficient",
    "STRATEGY": "decision_recorded",
    "ECONOMICS": "unit_economics_checked",
    "EXECUTION": "instrumentation_ready",
    "REVIEW": "decision_closed",
}


def valid_decision_record():
    return {
        "decision_id": "DR-001",
        "question": "优先选择哪一项品牌与渠道策略？",
        "deadline": None,
        "options": [
            {"name": "春茶季集中投放", "rationale": "需求集中", "risks": ["供应压力"]},
            {"name": "全年均投", "rationale": "稳定", "risks": ["峰值错过"]},
        ],
        "chosen_option": "春茶季集中投放",
        "rejected_options": [{"name": "全年均投", "reason": "峰值把握不足"}],
        "tradeoffs": ["放弃淡季曝光"],
        "key_assumptions": ["春茶季需求集中"],
        "falsification_conditions": ["若 4 月复购率低于 15% 则推翻"],
        "validation_actions": ["小规模 A/B 测试"],
        "review_date": "2026-05-01",
    }


def make_completer(events=None, record=None, role_body="# 角色输出\n\n| 主张 | 类型 | 可信度 |\n|---|---|---|\n| 需求集中 | FACT | MEDIUM |\n"):
    """构造一个假模型：按提示词内容返回角色输出 / 门禁判定 / 决策记录。"""
    events = events or {}

    def complete(prompt):
        if "门禁判定" in prompt:
            for phase, event in FORWARD_EVENT.items():
                if f"阶段 {phase}" in prompt:
                    event = events.get(phase, event)
                    if event is None:
                        return json.dumps(
                            {"event": "", "passed": False, "reason": "证据不足"}
                        )
                    return json.dumps(
                        {"event": event, "passed": True, "reason": "输出满足门禁"}
                    )
        if "各阶段输出摘要" in prompt:
            return json.dumps(record or valid_decision_record(), ensure_ascii=False)
        return role_body

    return complete


class TempProjectCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "nanjiang_tea"
        shutil.copytree(EXAMPLE, self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def config(self, **overrides):
        base = {"project_dir": self.dir, "provider_name": "manual"}
        base.update(overrides)
        return O.RunConfig(**base)


class ContextTests(TempProjectCase):
    def test_collects_project_and_empty_ledger(self):
        context = O.collect_context(self.dir)
        self.assertEqual(context["project"]["project_id"], "EXAMPLE-NANJIANG-TEA")
        self.assertEqual(context["evidence"], [])
        self.assertEqual(context["evidence_total"], 0)

    def test_includes_ledger_records(self):
        ledger = ledger_module.Ledger(self.dir)
        ledger.add({
            "claim": "春茶季前两周询价量翻倍", "type": "FACT",
            "source": "台账 2026-03", "confidence": "MEDIUM",
            "scope": "南涧县自饮客群", "decision_impact": "决定投放节奏",
        })
        context = O.collect_context(self.dir)
        self.assertEqual(context["evidence_total"], 1)
        self.assertEqual(context["evidence"][0]["claim"], "春茶季前两周询价量翻倍")

    def test_missing_project_raises(self):
        with self.assertRaises(O.OrchestratorError):
            O.collect_context(self._tmp.name)

    def test_evidence_cap_marks_truncation(self):
        ledger = ledger_module.Ledger(self.dir)
        for index in range(5):
            ledger.add({
                "claim": f"主张 {index}", "type": "FACT", "source": "s",
                "confidence": "MEDIUM", "scope": "范围", "decision_impact": "影响决策",
            })
        context = O.collect_context(self.dir, max_evidence=2)
        self.assertEqual(len(context["evidence"]), 2)
        self.assertTrue(context["evidence_truncated"])
        self.assertEqual(context["evidence_total"], 5)


class TaskPacketTests(TempProjectCase):
    def test_packet_contains_contract_and_requirements(self):
        context = O.collect_context(self.dir)
        packet = O.build_task_packet("business_model", "ECONOMICS", context)
        self.assertIn("商业模型 Agent", packet)
        self.assertIn("决策问题", packet)
        self.assertIn("禁止事项", packet)
        self.assertIn("验收标准", packet)
        self.assertIn("FACT", packet)

    def test_empty_ledger_forces_downgrade_language(self):
        context = O.collect_context(self.dir)
        packet = O.build_task_packet("red_team", "STRATEGY", context)
        self.assertIn("证据账本为空", packet)
        self.assertIn("不得假装掌握了事实", packet)

    def test_unknown_role_raises(self):
        with self.assertRaises(O.OrchestratorError):
            O.load_role_contract("does_not_exist")

    def test_gate_packet_lists_legal_events(self):
        context = O.collect_context(self.dir)
        packet = O.build_gate_packet("DISCOVER", context, {"master_agent": "输出"})
        self.assertIn("evidence_ready", packet)
        self.assertIn("need_clarification", packet)


class JsonExtractionTests(unittest.TestCase):
    def test_plain_object(self):
        self.assertEqual(O.extract_json_block('{"a": 1}'), {"a": 1})

    def test_fenced_block(self):
        self.assertEqual(O.extract_json_block('```json\n{"a": 1}\n```'), {"a": 1})

    def test_prose_around_object(self):
        self.assertEqual(
            O.extract_json_block('思考如下：\n{"a": 1}\n完毕'), {"a": 1}
        )

    def test_nested_braces(self):
        payload = '{"a": {"b": [1, 2]}}'
        self.assertEqual(O.extract_json_block(payload), {"a": {"b": [1, 2]}})

    def test_brace_inside_string(self):
        payload = '{"a": "含有 } 的文本"}'
        self.assertEqual(O.extract_json_block(payload), {"a": "含有 } 的文本"})

    def test_returns_none_on_garbage(self):
        self.assertIsNone(O.extract_json_block("没有 JSON"))
        self.assertIsNone(O.extract_json_block(""))
        self.assertIsNone(O.extract_json_block(None))


class DryRunTests(TempProjectCase):
    def test_dry_run_writes_packets_without_calling_model(self):
        calls = []

        def completer(prompt):
            calls.append(prompt)
            return "不应被调用"

        config = self.config(dry_run=True, phases=["EVIDENCE"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertEqual(calls, [], "dry-run 不应调用模型")
        self.assertEqual(report["mode"], "dry-run")
        run_dir = Path(report["run_dir"])
        self.assertTrue((run_dir / "EVIDENCE" / "customer_evidence.packet.md").exists())
        self.assertTrue((run_dir / "EVIDENCE" / "market_structure.packet.md").exists())

    def test_dry_run_does_not_change_project_state(self):
        original = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        O.Orchestrator(self.config(dry_run=True), completer=lambda p: "").run()
        after = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(original["current_state"], after["current_state"])


class ManualModeTests(TempProjectCase):
    def test_manual_mode_generates_packets_and_stops(self):
        report = O.Orchestrator(self.config(phases=["EVIDENCE"])).run()
        self.assertEqual(report["mode"], "manual")
        self.assertNotIn("decision_record", report)

    def test_manual_mode_never_calls_network(self):
        import urllib.request
        original = urllib.request.urlopen
        try:
            urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("manual 模式不应发起网络请求")
            )
            O.Orchestrator(self.config(phases=["DISCOVER"])).run()
        finally:
            urllib.request.urlopen = original


class ModelRunTests(TempProjectCase):
    def test_full_forward_run_reaches_review(self):
        config = self.config(provider_name="fake", phases=list(O.PHASES))
        report = O.Orchestrator(config, completer=make_completer()).run()
        self.assertEqual(report["final_state"], "REVIEW")
        self.assertEqual(report["gate_rejections"], [])
        self.assertEqual(
            [p["phase"] for p in report["phases"]], list(O.PHASES)
        )

    def test_state_is_persisted_to_project_json(self):
        # 门禁在阶段末尾判定并推进，所以跑完 EVIDENCE 后状态是 STRATEGY
        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        O.Orchestrator(config, completer=make_completer()).run()
        project = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(project["current_state"], "STRATEGY")
        self.assertIsNotNone(project["last_updated"])

    def test_role_outputs_written_to_disk(self):
        config = self.config(provider_name="fake",
                             phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(config, completer=make_completer()).run()
        run_dir = Path(report["run_dir"])
        self.assertTrue((run_dir / "EVIDENCE" / "customer_evidence.md").exists())
        self.assertTrue((run_dir / "EVIDENCE" / "market_structure.md").exists())
        self.assertTrue((run_dir / "EVIDENCE" / "gate.raw.md").exists())

    def test_illegal_event_is_rejected_and_blocks(self):
        # 模型在 DISCOVER 阶段返回一个在该状态不合法的事件
        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(
            config, completer=make_completer(events={"DISCOVER": "decision_closed"})
        ).run()
        self.assertEqual(report["final_state"], "BLOCKED")
        self.assertEqual(len(report["gate_rejections"]), 1)
        self.assertIn("不接受事件", report["gate_rejections"][0]["error"])

    def test_gate_that_requests_clarification_blocks(self):
        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(
            config,
            completer=make_completer(events={"DISCOVER": "need_clarification"}),
        ).run()
        self.assertEqual(report["final_state"], "BLOCKED")

    def test_unparseable_gate_output_does_not_advance(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                return "我觉得还行，但没有 JSON"
            if "各阶段输出摘要" in prompt:
                return "{}"
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertEqual(report["final_state"], "DISCOVER")
        self.assertFalse(report["phases"][0]["gate"]["passed"])

    def test_decision_record_produced_and_validated(self):
        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=make_completer()).run()
        record = report["decision_record"]
        self.assertEqual(record["schema_errors"], [])
        self.assertGreaterEqual(len(record["record"]["options"]), 2)

    def test_invalid_decision_record_reports_schema_errors(self):
        bad = valid_decision_record()
        bad["options"] = [bad["options"][0]]        # 只剩一个选项 -> 违反 minItems
        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(
            config, completer=make_completer(record=bad)
        ).run()
        self.assertTrue(report["decision_record"]["schema_errors"])

    def test_role_failure_does_not_lose_other_outputs(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                # DISCOVER 必须放行，否则 EVIDENCE 会被状态机正确跳过
                if "阶段 DISCOVER" in prompt:
                    return json.dumps(
                        {"event": "evidence_ready", "passed": True, "reason": "ok"}
                    )
                return json.dumps({"event": "", "passed": False, "reason": "x"})
            if "客户证据 Agent" in prompt:
                raise RuntimeError("模拟调用失败")
            return "# 市场结构输出"

        config = self.config(provider_name="fake",
                             phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(config, completer=completer).run()
        errors = [e for p in report["phases"] for e in p.get("errors", [])]
        self.assertTrue(any("模拟调用失败" in e["error"] for e in errors), errors)
        run_dir = Path(report["run_dir"])
        self.assertTrue((run_dir / "EVIDENCE" / "market_structure.md").exists())

    def test_phases_after_a_stalled_gate_are_skipped(self):
        """门禁不放行时后续阶段不得执行——这正是阶段门禁存在的意义。"""
        def completer(prompt):
            if "门禁判定" in prompt:
                return json.dumps({"event": "", "passed": False, "reason": "证据不足"})
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertEqual(report["final_state"], "DISCOVER")
        self.assertTrue(report["phases"][1].get("skipped"))

    def test_blocked_state_gives_actionable_hint(self):
        """BLOCKED 不在 PHASES 里，此前会输出「可用序列：[]」——毫无帮助。

        这个问题是接真实模型运行时暴露的，不是单元测试发现的。
        """
        project = json.loads((self.dir / "project.json").read_text(encoding="utf-8"))
        project["current_state"] = "BLOCKED"
        (self.dir / "project.json").write_text(
            json.dumps(project, ensure_ascii=False), encoding="utf-8"
        )
        report = O.Orchestrator(
            self.config(provider_name="fake"), completer=make_completer()
        ).run()
        hint = report.get("hint", "")
        self.assertIn("BLOCKED", hint)
        self.assertIn("clarification_received", hint)
        self.assertNotIn("[]", hint, "不应再出现空列表式的无用提示")

    def test_run_json_written(self):
        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=make_completer()).run()
        payload = json.loads(
            (Path(report["run_dir"]) / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["run_id"], report["run_id"])
        self.assertIn("log", payload)


class ProposedEvidenceTests(TempProjectCase):
    def test_proposals_are_not_written_to_the_ledger(self):
        """核心保障：模型输出不是证据，绝不能自动入账。"""
        config = self.config(provider_name="fake",
                             phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(config, completer=make_completer()).run()
        proposals = O.collect_proposed_evidence(report["run_dir"])
        self.assertTrue(proposals, "示例输出里应有表格行")
        ledger = ledger_module.Ledger(self.dir)
        self.assertEqual(ledger.load(), [], "证据账本必须保持为空")

    def test_packet_files_are_excluded_from_proposals(self):
        config = self.config(dry_run=True, phases=["EVIDENCE"])
        report = O.Orchestrator(config, completer=lambda p: "").run()
        self.assertEqual(O.collect_proposed_evidence(report["run_dir"]), [])


class ConfigTests(unittest.TestCase):
    def test_unknown_phase_rejected(self):
        with self.assertRaises(O.OrchestratorError):
            O.RunConfig(project_dir=ROOT, phases=["NOPE"])

    def test_phase_role_map_covers_all_phases(self):
        for phase in O.PHASES:
            self.assertIn(phase, O.PHASE_ROLES)

    def test_every_mapped_role_has_a_contract_file(self):
        for roles in O.PHASE_ROLES.values():
            for role in roles:
                self.assertTrue((ROOT / "agents" / f"{role}.md").exists(), role)


class PhaseGateTests(unittest.TestCase):
    """门禁必须**逐阶段不同**。

    早期版本对六个阶段套用同一套「证据是否充足」的标准，结果 DISCOVER 永远
    无法通过——R 阶段本来就发生在补证之前，它要求的是问题界定质量。
    这个缺陷是接真实模型跑出来的：连续 4 次运行全部卡死在 DISCOVER。
    """

    def setUp(self):
        self.context = {
            "project": {"decision_question": "q", "current_state": "DISCOVER",
                        "goals": [], "constraints": []},
            "evidence": [], "evidence_total": 0, "documents": [],
            "evidence_truncated": False,
        }

    def test_every_phase_has_criteria(self):
        for phase in O.PHASES:
            self.assertIn(phase, O.PHASE_GATES, f"{phase} 缺少门禁定义")
            gate = O.PHASE_GATES[phase]
            self.assertTrue(gate["criteria"], f"{phase} 门禁标准为空")
            self.assertTrue(gate.get("note"), f"{phase} 缺少门禁说明")

    def test_gate_packet_carries_phase_specific_text(self):
        pairs = {
            "DISCOVER": "症状",
            "EVIDENCE": "补证路径",
            "STRATEGY": "为什么选 A 而不是 B",
            "ECONOMICS": "分子分母",
            "EXECUTION": "不得称为实验",
            "REVIEW": "预期与实际",
        }
        for phase, token in pairs.items():
            packet = O.build_gate_packet(phase, self.context, {"master_agent": "x"})
            self.assertIn(token, packet, f"{phase} 门禁未包含其专属标准「{token}」")

    def test_gate_packet_forbids_using_other_phases_criteria(self):
        packet = O.build_gate_packet("DISCOVER", self.context, {"master_agent": "x"})
        self.assertIn("只按本阶段的标准判定", packet)

    def test_discover_gate_does_not_demand_sufficient_evidence(self):
        # R 阶段的要求是「未知被如实标记」，不是「证据充足」
        note = O.PHASE_GATES["DISCOVER"]["note"]
        self.assertIn("不要求证据充足", note)

    def test_economics_gate_allows_assumption_driven_progress(self):
        # U 阶段允许带假设推进：数据不全本身不是阻断理由
        note = O.PHASE_GATES["ECONOMICS"]["note"]
        self.assertIn("数据不全", note)

    def test_gate_offers_a_graded_path(self):
        """必须提供 DEGRADED（降级放行），否则流程只有「放行/阻断」两种选择，
        而真实项目几乎不可能等到证据齐全——结果就是永远阻断。"""
        packet = O.build_gate_packet("EVIDENCE", self.context, {"master_agent": "x"})
        self.assertIn("DEGRADED", packet)
        self.assertIn("降级放行", packet)
        self.assertIn("limitations", packet)

    def test_gate_states_that_hiding_gaps_is_the_real_failure(self):
        packet = O.build_gate_packet("EVIDENCE", self.context, {"master_agent": "x"})
        self.assertIn("假装证据是完整的", packet)


class DecisionRecordSchemaTests(unittest.TestCase):
    """真实模型把每条假设与它的反证条件配成对，比 schema 允许的纯字符串更有用。

    这是接真实模型跑出来的第二个缺陷：模型的产出被自己的 schema 判为非法。
    修法是放宽 schema，而不是压制模型的合理结构。
    """

    def setUp(self):
        import schema_validator as sv
        self.sv = sv
        self.schema = sv.load_schema(ROOT / "schemas" / "decision_record.schema.json")
        self.base = {
            "decision_id": "DR-1", "question": "q",
            "options": [{"name": "a", "rationale": "r"}, {"name": "b", "rationale": "r"}],
            "chosen_option": "a", "rejected_options": [], "tradeoffs": [],
            "falsification_conditions": [], "validation_actions": [],
            "review_date": "2026-01-01",
        }

    def test_plain_string_assumptions_still_valid(self):
        record = dict(self.base, key_assumptions=["纯字符串假设"])
        errors, _ = self.sv.validate(record, self.schema)
        self.assertEqual(errors, [])

    def test_structured_assumptions_valid(self):
        record = dict(self.base, key_assumptions=[
            {"assumption": "转化率 ≥15%",
             "falsification_condition": "实测 <5% 则推翻",
             "confidence": "LOW"},
        ])
        errors, _ = self.sv.validate(record, self.schema)
        self.assertEqual(errors, [])

    def test_structured_assumption_requires_the_assumption_field(self):
        record = dict(self.base, key_assumptions=[{"falsification_condition": "x"}])
        errors, _ = self.sv.validate(record, self.schema)
        self.assertTrue(errors)

    def test_structured_assumption_rejects_unknown_field(self):
        record = dict(self.base, key_assumptions=[{"assumption": "a", "typo": 1}])
        errors, _ = self.sv.validate(record, self.schema)
        self.assertTrue(errors)


class FaultPathTests(TempProjectCase):
    """故障路径。

    真实 API 会返回 429、超时、被截断的响应、以及各种非 JSON 内容。
    这些路径此前完全没有测试——单元测试跑的都是顺利路径。
    """

    def test_all_roles_failing_does_not_call_the_gate(self):
        """角色全挂时不应再拿空输入去调一次门禁——那是纯浪费。"""
        calls = []

        def completer(prompt):
            calls.append(prompt)
            if "门禁判定" in prompt:
                raise AssertionError("角色全部失败时不应调用门禁")
            raise RuntimeError("模拟 API 故障")

        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        # DISCOVER 需要放行才能进入 EVIDENCE
        report = O.Orchestrator(config, completer=completer).run()
        evidence = [p for p in report["phases"] if p["phase"] == "EVIDENCE"]
        # EVIDENCE 的两个角色都失败 → 门禁不应被调用
        self.assertFalse(
            any("门禁判定" in c and "EVIDENCE" in c for c in calls),
            "角色全失败时仍然调用了门禁",
        )

    def test_gate_call_exception_does_not_advance(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                raise RuntimeError("429 Too Many Requests")
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertEqual(report["final_state"], "DISCOVER")
        gate = report["phases"][0]["gate"]
        self.assertFalse(gate["passed"])
        self.assertIn("429", gate["reason"])

    def test_decision_record_failure_does_not_crash_the_run(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                return json.dumps({"event": "evidence_ready", "passed": True,
                                   "reason": "ok"})
            if "各阶段输出摘要" in prompt:
                raise RuntimeError("连接被重置")
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertIn("error", report["decision_record"])
        self.assertIn("连接被重置", report["decision_record"]["error"])
        # 运行本身仍然正常收尾，状态迁移照样生效
        self.assertEqual(report["final_state"], "EVIDENCE")

    def test_truncated_json_in_decision_record_is_reported_not_raised(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                return json.dumps({"event": "evidence_ready", "passed": True,
                                   "reason": "ok"})
            if "各阶段输出摘要" in prompt:
                # 响应被截断：JSON 未闭合
                return '{"decision_id": "DR-001", "question": "被截断的响应'
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertIn("error", report["decision_record"])
        self.assertIn("无法解析为 JSON", report["decision_record"]["error"])

    def test_truncated_json_in_gate_does_not_advance(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                return '{"event": "evidence_ready", "passed": tru'   # 截断
            return "# 输出"

        config = self.config(provider_name="fake", phases=["DISCOVER"])
        report = O.Orchestrator(config, completer=completer).run()
        self.assertEqual(report["final_state"], "DISCOVER")

    def test_manual_mode_with_provider_configured_still_offline(self):
        """provider_name 非 manual 但没有注入 completer 时，
        manual 判定应为 False；若 provider 层不可用应给出清晰错误。"""
        config = self.config(provider_name="nonexistent-provider", phases=["DISCOVER"])
        with self.assertRaises(O.OrchestratorError) as ctx:
            O.Orchestrator(config).run()      # 不注入 completer
        self.assertIn("nonexistent-provider", str(ctx.exception))

    def test_error_records_which_role_failed(self):
        def completer(prompt):
            if "门禁判定" in prompt:
                return json.dumps({"event": "evidence_ready", "passed": True,
                                   "reason": "ok"})
            if "客户证据 Agent" in prompt:
                raise RuntimeError("该角色专属故障")
            return "# 市场结构输出"

        config = self.config(provider_name="fake", phases=["DISCOVER", "EVIDENCE"])
        report = O.Orchestrator(config, completer=completer).run()
        errors = [e for p in report["phases"] for e in p.get("errors", [])]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["role"], "customer_evidence")
        self.assertIn("该角色专属故障", errors[0]["error"])


if __name__ == "__main__":
    unittest.main()
