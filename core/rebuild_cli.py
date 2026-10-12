#!/usr/bin/env python3
"""REBUILD 命令行入口。

子命令
------
  validate    校验项目状态（含 JSON Schema 校验）
  transition  查询一次状态机迁移是否合法
  schema      用指定 schema 校验任意 JSON 文件
  evidence    证据账本：写入 / 列出 / 校验 / 缺口 / 导出
  source      数据源：导入本地文件 / 抓取自建端点 / 查看材料
  run         运行时编排：按阶段调度角色、判定门禁、推进状态

退出码：0 成功；1 校验未通过；2 运行错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
for _extra in (_HERE, ROOT):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import schema_validator as sv  # noqa: E402

STATE_FILE = _HERE / "state_machine.json"
SCHEMAS = ROOT / "schemas"


def _collect_domain_errors():
    """收集各模块自定义的异常类型。

    这些异常的消息是写给使用者看的，应当作为错误信息打印，
    而不是抛出带堆栈的 traceback——堆栈对使用者没有帮助。
    """
    found = []
    for module_name, attribute in (
        ("sources", "SourceError"),
        ("ledger", "EvidenceError"),
        ("orchestrator", "OrchestratorError"),
        ("decisions", "DecisionError"),
    ):
        try:
            module = __import__(module_name)
            found.append(getattr(module, attribute))
        except (ImportError, AttributeError):
            continue
    return tuple(found)


DOMAIN_ERRORS = _collect_domain_errors()


# ---------------------------------------------------------------------------
# 基础
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def project_dir_of(path) -> Path:
    """接受项目目录或 project.json 路径，统一返回项目目录。"""
    path = Path(path)
    if path.is_dir():
        return path
    if path.name == "project.json":
        return path.parent
    raise ValueError(f"请给出项目目录或其中的 project.json，而不是：{path}")


def transition(state, event):
    machine = load_json(STATE_FILE)
    if state not in machine["states"]:
        raise ValueError(f"未知状态：{state}。可用：{machine['states']}")
    nxt = machine["transitions"].get(state, {}).get(event)
    if not nxt:
        raise ValueError(
            f"不允许的迁移：{state} + {event}。"
            f"该状态可用事件：{sorted(machine['transitions'].get(state, {}))}"
        )
    return {"from": state, "event": event, "to": nxt}


def validate_project(path, use_schema=True):
    """返回 (errors, warnings)。"""
    data = load_json(path)
    errors = []
    machine = load_json(STATE_FILE)
    if data.get("current_state") not in machine["states"]:
        errors.append(
            f"current_state 不是已知状态：{data.get('current_state')!r}。"
            f"可用：{machine['states']}"
        )
    if not isinstance(data.get("goals", []), list):
        errors.append("goals 必须是数组")
    if not isinstance(data.get("constraints", []), list):
        errors.append("constraints 必须是数组")

    warnings = []
    if use_schema:
        schema_path = sv.guess_schema(path, SCHEMAS)
        if schema_path is None:
            warnings.append(
                f"未找到与 {Path(path).name} 匹配的 schema，已跳过 schema 校验"
            )
        else:
            schema_errors, schema_warnings = sv.validate_file(path, schema_path)
            errors.extend(schema_errors)
            warnings.extend(schema_warnings)
    return errors, warnings


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------

def cmd_evidence(args):
    import ledger as ledger_module

    directory = project_dir_of(args.project)
    ledger = ledger_module.Ledger(directory)

    if args.action == "add":
        source = args.source
        if args.source_doc:
            from sources import DocumentStore

            DocumentStore(directory).get(args.source_doc)  # 不存在则抛错
            source = args.source_doc
        record = {
            "claim": args.claim,
            "type": args.type,
            "source": source,
            "observed_at": args.observed_at,
            "confidence": args.confidence,
            "scope": args.scope,
            "counter_evidence": args.counter_evidence or [],
            "decision_impact": args.decision_impact,
            "recheck_trigger": args.recheck_trigger,
        }
        if args.id:
            record["id"] = args.id
        saved = ledger.add(record)
        warnings = ledger_module.quality_warnings(saved)
        print(json.dumps({"added": saved}, ensure_ascii=False, indent=2))
        if warnings:
            print("\n质量提示（不阻断写入，但请处理）：", file=sys.stderr)
            for warning in warnings:
                print(f"  ⚠ {warning}", file=sys.stderr)
        return 0

    if args.action == "list":
        records = ledger.filter(
            kind=args.type, confidence=args.confidence,
            min_confidence=args.min_confidence,
        )
        if args.json:
            print(json.dumps(records, ensure_ascii=False, indent=2))
        else:
            if not records:
                print(f"证据账本为空（{ledger.path}）")
                return 0
            for record in records:
                print(
                    f"{record.get('id'):<8}{record.get('type'):<12}"
                    f"{record.get('confidence'):<8}{record.get('claim')}"
                )
        return 0

    if args.action == "check":
        errors, warnings = ledger.validate()
        print(json.dumps(
            {"records": len(ledger.load()), "errors": errors, "warnings": warnings},
            ensure_ascii=False, indent=2,
        ))
        if errors:
            return 1
        if warnings:
            print(
                f"\n{len(warnings)} 条质量提示：这些记录字段合法，"
                f"但方法学上不足以支撑判断。",
                file=sys.stderr,
            )
        return 0

    if args.action == "gaps":
        project_file = directory / "project.json"
        report = ledger_module.gaps(project_file)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        missing = (
            len(report["assumptions_without_evidence"])
            + len(report["unknowns_without_evidence"])
            + len(report["known_facts_without_evidence"])
        )
        return 1 if missing else 0

    if args.action == "export":
        text = ledger_module.to_markdown(directory)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"已导出到 {args.out}")
        else:
            print(text)
        return 0

    if args.action == "provenance":
        report = ledger_module.provenance_report(directory)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["dangling"]:
            print(
                f"\n{len(report['dangling'])} 条证据的来源是断链（指向不存在的材料）。",
                file=sys.stderr,
            )
            return 1
        if report["total"] and report["verifiable_ratio"] is not None:
            print(
                f"\n可机器核验比例：{report['verifiable_ratio']:.0%}"
                f"（{len(report['linked'])}/{report['total']}）。"
                f"自由文本来源无法自动核验，只能靠人工。",
                file=sys.stderr,
            )
        return 0

    raise ValueError(f"未知的 evidence 动作：{args.action}")


# ---------------------------------------------------------------------------
# source
# ---------------------------------------------------------------------------

def cmd_source(args):
    from sources import DocumentStore, SourceError, files, http_api

    directory = project_dir_of(args.project)
    store = DocumentStore(directory)

    if args.action == "add-file":
        document = files.add_file(store, args.path)
        print(json.dumps(
            {"doc_id": document.doc_id, "origin": document.origin,
             "media_type": document.media_type, "sha256": document.sha256[:16],
             "chars": len(document.content), "meta": document.meta},
            ensure_ascii=False, indent=2,
        ))
        return 0

    if args.action == "add-url":
        header_env = dict(pair.split("=", 1) for pair in (args.header_env or []))
        headers = dict(pair.split("=", 1) for pair in (args.header or []))
        spec = http_api.HttpSourceSpec(
            name=args.name, url=args.url, method=args.method,
            headers=headers, header_env=header_env,
            records_path=args.records_path or "", timeout=args.timeout,
        )
        for warning in spec.warnings():
            print(f"  ⚠ {warning}", file=sys.stderr)
        if args.save_spec:
            print(f"已保存 spec：{http_api.save_spec(directory, spec)}")
        documents = http_api.add_http(store, spec)
        print(json.dumps(
            {"fetched": len(documents),
             "documents": [d.doc_id for d in documents]},
            ensure_ascii=False, indent=2,
        ))
        return 0

    if args.action == "list":
        entries = store.list()
        if not entries:
            print("尚未导入任何材料")
            return 0
        for entry in entries:
            print(
                f"{entry.get('doc_id'):<10}{entry.get('media_type'):<50}"
                f"{entry.get('origin')}"
            )
        return 0

    if args.action == "show":
        document = store.get(args.doc_id)
        print(json.dumps(
            {k: v for k, v in document.to_dict().items() if k != "content"},
            ensure_ascii=False, indent=2,
        ))
        print("-" * 60)
        print(document.content[:4000])
        return 0

    if args.action == "verify":
        entries = store.list()
        if not entries:
            print("尚未导入任何材料")
            return 0
        bad = [e["doc_id"] for e in entries if not store.verify(e["doc_id"])]
        print(json.dumps(
            {"checked": len(entries), "tampered": bad}, ensure_ascii=False, indent=2
        ))
        return 1 if bad else 0

    raise ValueError(f"未知的 source 动作：{args.action}")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def cmd_run(args):
    import orchestrator as orch

    directory = project_dir_of(args.project)
    phases = args.phase or list(orch.PHASES)
    config = orch.RunConfig(
        project_dir=directory,
        provider_name=args.provider,
        phases=phases,
        dry_run=args.dry_run,
        max_evidence=args.max_evidence,
        temperature=args.temperature,
        price_input_per_million=args.price_input,
        price_output_per_million=args.price_output,
        currency=args.currency,
    )
    if args.repeat > 1:
        reports = orch.run_repeated(config, args.repeat)
        print(json.dumps(
            [
                {"run_id": r["run_id"], "final_state": r["final_state"],
                 "gate_grades": [
                     (p.get("gate") or {}).get("evidence_grade")
                     for p in r["phases"] if not p.get("skipped")
                 ],
                 "usage": r.get("usage"),
                 "cost_estimate": r.get("cost_estimate")}
                for r in reports
            ],
            ensure_ascii=False, indent=2,
        ))
        total_calls = sum((r.get("usage") or {}).get("calls", 0) for r in reports)
        tokens = [(r.get("usage") or {}).get("total_tokens") for r in reports]
        if all(t is not None for t in tokens):
            print(f"\n{len(reports)} 次运行合计 {total_calls} 次模型调用，"
                  f"{sum(tokens):,} tokens", file=sys.stderr)
        else:
            print(f"\n{len(reports)} 次运行合计 {total_calls} 次模型调用；"
                  f"部分运行未取得用量，总数不完整", file=sys.stderr)
        states = {r["final_state"] for r in reports}
        print(f"\n{args.repeat} 次运行完成，终态 {len(states)} 种：{sorted(states)}",
              file=sys.stderr)
        print(f"比对：python {Path(__file__).name} compare {args.project} "
              f"--last {args.repeat}", file=sys.stderr)
        return 0 if len(states) == 1 else 1

    report = orch.Orchestrator(config).run()

    print(json.dumps(
        {k: v for k, v in report.items() if k != "log"},
        ensure_ascii=False, indent=2,
    ))
    usage = report.get("usage") or {}
    if usage:
        tok = (f"{usage['total_tokens']:,}" if usage.get("total_tokens") is not None
               else "未取得")
        print(f"\n模型调用 {usage['calls']} 次（{usage['calls_with_usage']} 次取得用量），"
              f"合计 {tok} tokens，耗时 {usage['seconds']}s", file=sys.stderr)
        if usage.get("note"):
            print(f"  ⚠ {usage['note']}", file=sys.stderr)
    cost = report.get("cost_estimate")
    if cost:
        print(f"  估算费用：{cost['total']} {cost['currency']}"
              f"（按你提供的单价；不是账单金额）", file=sys.stderr)

    print(f"\n产物目录：{report['run_dir']}", file=sys.stderr)
    print(f"初始状态 {report['initial_state']} → 最终状态 {report['final_state']}",
          file=sys.stderr)
    if report.get("hint"):
        print(f"\n提示：{report['hint']}", file=sys.stderr)
    if report.get("gate_rejections"):
        print("\n被拒绝的迁移（模型给出的非法事件）：", file=sys.stderr)
        for item in report["gate_rejections"]:
            print(f"  ✗ {item['phase']}: {item['event']} — {item['error']}",
                  file=sys.stderr)

    if args.mode == "dry-run" or args.provider == "manual":
        print(
            "\n当前是手动模式：只生成了任务包，没有调用任何模型。\n"
            f"请打开 {report['run_dir']} 下的 *.packet.md，自行粘贴到模型，"
            "再把输出保存为同名 .md 文件。",
            file=sys.stderr,
        )
    return 0


def cmd_decision(args):
    import decisions as decisions_module

    directory = project_dir_of(args.project)
    store = decisions_module.DecisionStore(directory)

    if args.action == "add":
        def pairs(values, left_key, right_key):
            out = []
            for raw in values or []:
                name, _, rest = str(raw).partition("|")
                out.append({left_key: name.strip(), right_key: rest.strip()})
            return out

        record = {
            "question": args.question,
            "deadline": args.deadline,
            "options": pairs(args.option, "name", "rationale"),
            "chosen_option": args.chosen,
            "rejected_options": pairs(args.rejected, "name", "reason"),
            "tradeoffs": args.tradeoff or [],
            "key_assumptions": args.assumption or [],
            "falsification_conditions": args.falsification or [],
            "validation_actions": args.validation or [],
            "review_date": args.review_date,
        }
        if args.id:
            record["decision_id"] = args.id
        saved = store.add(record)
        print(json.dumps({"added": saved}, ensure_ascii=False, indent=2))
        warnings = decisions_module.quality_warnings(saved)
        if warnings:
            print("\n质量提示（已写入，但请处理）：", file=sys.stderr)
            for warning in warnings:
                print(f"  ⚠ {warning}", file=sys.stderr)
        return 0

    if args.action == "list":
        records = store.list()
        if not records:
            print("尚无决策记录")
            return 0
        for record in records:
            rid = record.get("decision_id")
            outcome = store.outcome_of(rid)
            status = "已复盘" if outcome else "待复盘"
            print(
                f"{rid:<8}{status:<8}{record.get('review_date') or '(无复审日期)':<14}"
                f"{record.get('chosen_option')}"
            )
        return 0

    if args.action == "show":
        if not args.id:
            raise ValueError("decision show 需要 --id")
        record = store.load(args.id)
        outcome = store.outcome_of(args.id)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print("\n--- 复盘结果 ---")
        print(json.dumps(outcome, ensure_ascii=False, indent=2) if outcome
              else "尚未复盘。")
        return 0

    if args.action == "validate":
        errors, warnings = store.validate()
        print(json.dumps(
            {"decisions": len(store.list()), "errors": errors, "warnings": warnings},
            ensure_ascii=False, indent=2,
        ))
        return 1 if errors else 0

    if args.action == "outcome":
        if not args.id:
            raise ValueError("decision outcome 需要 --id")
        # --assumption-update "假设文本|CONFIRMED|简短说明"
        updates = []
        for raw in args.assumption_update or []:
            parts = [p.strip() for p in str(raw).split("|")]
            if len(parts) < 2:
                raise ValueError(
                    'assumption-update 格式应为 "假设文本|CONFIRMED|说明"，'
                    f"收到：{raw!r}"
                )
            status = parts[1].upper()
            if status not in ("CONFIRMED", "REFUTED", "STILL_UNKNOWN"):
                raise ValueError(
                    f"assumption-update 的状态必须是 CONFIRMED / REFUTED / "
                    f"STILL_UNKNOWN，收到：{parts[1]!r}"
                )
            updates.append({"assumption": parts[0], "status": status,
                            "note": parts[2] if len(parts) > 2 else None})

        outcome = {
            "decision_id": args.id,
            "expected": args.expected,
            "actual": args.actual,
            "deviation_type": args.deviation,
            "evidence_ids": args.evidence or [],
            "assumption_updates": updates,
            "next_action": args.next_action,
            "notes": args.notes,
        }
        saved = store.record_outcome(outcome)
        print(json.dumps({"recorded": saved}, ensure_ascii=False, indent=2))
        return 0

    if args.action == "due":
        report = store.due_for_review()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["overdue"]:
            print(
                f"\n{len(report['overdue'])} 项决策已过复审日期但尚未复盘。"
                f"方法论要求 D 阶段闭合——没有复盘就没有学习。",
                file=sys.stderr,
            )
            return 1
        return 0

    if args.action == "import":
        # 模型产出的决策记录需人工确认后才入账。
        # 与证据同一条原则：模型输出不等于已成立的决策。
        if not args.from_path:
            raise ValueError("decision import 需要 --from <decision_record.json>")
        source = Path(args.from_path)
        if not source.exists():
            raise ValueError(f"找不到文件：{source}")
        record = json.loads(source.read_text(encoding="utf-8"))
        record.pop("decision_id", None)      # 重新编号，避免与现有记录撞号
        saved = store.add(record)
        print(json.dumps({"imported": saved}, ensure_ascii=False, indent=2))
        print(
            "\n注意：这是模型产出的决策草案，已按原样入库。"
            "复审日期与反证条件需要你亲自确认后修改。",
            file=sys.stderr,
        )
        for warning in decisions_module.quality_warnings(saved):
            print(f"  ⚠ {warning}", file=sys.stderr)
        return 0

    if args.action == "export":
        text = store.to_markdown()
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"已导出到 {args.out}")
        else:
            print(text)
        return 0

    raise ValueError(f"未知的 decision 动作：{args.action}")


def cmd_compare(args):
    import compare as compare_module

    directory = project_dir_of(args.project)
    reports = compare_module.collect_runs(directory, last=args.last)
    result = compare_module.compare(reports)

    if args.judge_with:
        import orchestrator as orch

        config = orch.RunConfig(project_dir=directory,
                                provider_name=args.judge_with,
                                dry_run=True)
        provider_layer, provider_config = orch.Orchestrator(config)._resolve_provider()

        def call(prompt):
            return provider_layer.complete(provider_config, prompt)

        try:
            result["agreement"] = compare_module.judge_agreement(reports, call)
        except Exception as exc:  # noqa: BLE001 - 判定失败不应丢掉比对结果
            result["agreement"] = {"judged_by_model": True, "error": str(exc)}

    text = compare_module.render_markdown(result)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"已写入 {args.out}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(text)

    if result.get("agreement"):
        agreement = result["agreement"]
        print("\n" + "=" * 60)
        if agreement.get("error"):
            print(f"结论一致性判定失败：{agreement['error']}", file=sys.stderr)
        else:
            print(f"结论方向一致：{agreement.get('agree')}"
                  f"（置信度 {agreement.get('confidence')}）")
            print(f"共同方向：{agreement.get('direction')}")
            print(f"理由：{agreement.get('why')}")
        print("\n⚠️ 这是模型判定，不是事实。", file=sys.stderr)

    # 过程不一致时返回非零，便于脚本化使用
    return 0 if result["final_state_consistent"] else 1


def cmd_schema(args):
    schema_path = Path(args.schema_file) if args.schema_file else sv.guess_schema(
        args.file, SCHEMAS
    )
    if schema_path is None:
        print(json.dumps(
            {"valid": False,
             "errors": [f"无法为 {args.file} 推断 schema，请用 --schema-file 指定"]},
            ensure_ascii=False, indent=2,
        ))
        return 1
    errors, warnings = sv.validate_file(args.file, schema_path)
    print(json.dumps(
        {"file": args.file, "schema": str(schema_path),
         "valid": not errors, "errors": errors, "warnings": warnings},
        ensure_ascii=False, indent=2,
    ))
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="rebuild",
        description="REBUILD —— 以决策为中心的品牌营销方法论工具集",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="校验项目状态（默认含 schema 校验）")
    v.add_argument("project")
    v.add_argument("--no-schema", action="store_true", help="跳过 JSON Schema 校验")

    t = sub.add_parser("transition", help="查询一次状态机迁移是否合法")
    t.add_argument("--state", required=True)
    t.add_argument("--event", required=True)

    s = sub.add_parser("schema", help="用 schema 校验任意 JSON 文件")
    s.add_argument("file")
    s.add_argument("--schema-file", default=None)

    e = sub.add_parser("evidence", help="证据账本")
    e.add_argument("action",
                   choices=["add", "list", "check", "gaps", "export", "provenance"])
    e.add_argument("project")
    e.add_argument("--claim")
    e.add_argument("--type", choices=["FACT", "INFERENCE", "ASSUMPTION", "UNKNOWN"])
    e.add_argument("--confidence", choices=["HIGH", "MEDIUM", "LOW"])
    e.add_argument("--min-confidence", choices=["HIGH", "MEDIUM", "LOW"])
    e.add_argument("--source", default=None,
                   help="自由文本来源，无法自动核验")
    e.add_argument("--source-doc", default=None, dest="source_doc",
                   help="指向材料库的编号（如 DOC-001），可被机器核验")
    e.add_argument("--observed-at", default=None)
    e.add_argument("--scope", default=None)
    e.add_argument("--decision-impact", default=None)
    e.add_argument("--recheck-trigger", default=None)
    e.add_argument("--counter-evidence", action="append")
    e.add_argument("--id", default=None)
    e.add_argument("--json", action="store_true")
    e.add_argument("--out", default=None)

    d = sub.add_parser("decision", help="决策记录与复盘")
    d.add_argument("action",
                   choices=["add", "list", "show", "validate", "outcome",
                            "due", "export", "import"])
    d.add_argument("project")
    d.add_argument("--id", default=None)
    d.add_argument("--question", default=None)
    d.add_argument("--deadline", default=None)
    d.add_argument("--option", action="append",
                   help='候选方案，形如 "名称|理由"，可重复')
    d.add_argument("--chosen", default=None, help="采用的方案名称")
    d.add_argument("--rejected", action="append",
                   help='放弃的方案，形如 "名称|原因"，可重复')
    d.add_argument("--tradeoff", action="append", help="代价，可重复")
    d.add_argument("--assumption", action="append", help="关键假设，可重复")
    d.add_argument("--falsification", action="append",
                   help="反证条件，可重复")
    d.add_argument("--validation", action="append", help="验证动作，可重复")
    d.add_argument("--review-date", default=None, dest="review_date")
    # outcome
    d.add_argument("--expected", default=None)
    d.add_argument("--actual", default=None)
    d.add_argument("--deviation", default=None,
                   choices=["AS_EXPECTED", "EXECUTION", "STRATEGY",
                            "ASSUMPTION", "MIXED", "UNKNOWN"])
    d.add_argument("--next-action", default=None, dest="next_action",
                   choices=["CONTINUE", "ADJUST", "STOP", "ROLLBACK"])
    d.add_argument("--evidence", action="append")
    d.add_argument("--assumption-update", action="append", dest="assumption_update",
                   help='复盘时更新关键假设，形如 "假设文本|CONFIRMED|说明"；'
                        '状态可为 CONFIRMED / REFUTED / STILL_UNKNOWN')
    d.add_argument("--notes", default=None)
    d.add_argument("--out", default=None)
    d.add_argument("--from", default=None, dest="from_path",
                   help="import：从运行产物导入决策记录 JSON")

    src = sub.add_parser("source", help="数据源")
    src.add_argument("action",
                     choices=["add-file", "add-url", "list", "show", "verify"])
    src.add_argument("project")
    src.add_argument("path", nargs="?", help="add-file 时的文件路径")
    src.add_argument("--name", default=None)
    src.add_argument("--url", default=None)
    src.add_argument("--method", default="GET")
    src.add_argument("--header", action="append", help="形如 NAME=VALUE")
    src.add_argument("--header-env", action="append", help="形如 NAME=ENV_VAR")
    src.add_argument("--records-path", default=None)
    src.add_argument("--timeout", type=int, default=30)
    src.add_argument("--save-spec", action="store_true")
    src.add_argument("--doc-id", default=None, dest="doc_id")

    c = sub.add_parser("compare", help="比对同一项目的多次运行（过程可复现性 + 可选结论一致性）")
    c.add_argument("project")
    c.add_argument("--last", type=int, default=None, help="只比最近 N 次")
    c.add_argument("--judge-with", default=None, dest="judge_with",
                   help="用指定 provider 判定「结论方向是否一致」。"
                        "这是模型判定，不是事实")
    c.add_argument("--json", action="store_true")
    c.add_argument("--out", default=None)

    r = sub.add_parser("run", help="运行时编排：调度角色、判定门禁、推进状态")
    r.add_argument("project")
    r.add_argument("--provider", default="manual",
                   help="manual（默认，零网络）或 bench/provider.py 中的预设名")
    r.add_argument("--phase", action="append", help="只跑指定阶段，可重复")
    r.add_argument("--dry-run", action="store_true", help="只生成任务包")
    r.add_argument("--max-evidence", type=int, default=60)
    r.add_argument("--repeat", type=int, default=1,
                   help="重复运行次数。同一输入多次运行可观察一致性；"
                        "配合 `compare` 子命令使用")
    r.add_argument("--price-input", type=float, default=None, dest="price_input",
                   help="输入 token 单价（每百万）。不填则只统计 token，不算费用"
                        "——本项目不内置任何价格，因为价格会变")
    r.add_argument("--price-output", type=float, default=None, dest="price_output",
                   help="输出 token 单价（每百万）")
    r.add_argument("--currency", default="USD", help="计价货币，仅用于标注")
    r.add_argument("--temperature", type=float, default=0.3,
                   help="采样温度，默认 0.3。设为 0 可提高运行间一致性，"
                        "但多数 API 不保证完全确定，仍需多次运行验证")
    r.add_argument("--mode", default=None, help=argparse.SUPPRESS)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "validate":
            errors, warnings = validate_project(args.project,
                                                use_schema=not args.no_schema)
            print(json.dumps(
                {"valid": not errors, "project": args.project,
                 "errors": errors, "warnings": warnings},
                ensure_ascii=False, indent=2,
            ))
            return 0 if not errors else 1
        if args.cmd == "transition":
            print(json.dumps(transition(args.state, args.event),
                             ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "schema":
            return cmd_schema(args)
        if args.cmd == "evidence":
            return cmd_evidence(args)
        if args.cmd == "decision":
            return cmd_decision(args)
        if args.cmd == "source":
            return cmd_source(args)
        if args.cmd == "run":
            return cmd_run(args)
        if args.cmd == "compare":
            return cmd_compare(args)
        raise ValueError(f"未知子命令：{args.cmd}")
    except DOMAIN_ERRORS as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"JSON 解析失败：{exc}"},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
