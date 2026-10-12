#!/usr/bin/env python3
"""REBUILD command-line entry point.

Subcommands
-----------
  validate    validate project state (includes JSON Schema validation)
  transition  ask whether one state-machine transition is legal
  schema      validate any JSON file against a given schema
  evidence    evidence ledger: write / list / validate / gaps / export
  source      data sources: import local files / fetch from your own endpoint / inspect material
  run         runtime orchestration: schedule roles by phase, judge gates, advance state

Exit codes: 0 success; 1 validation failed; 2 runtime error.
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
    """Collect the custom exception types of the various modules.

    The messages of these exceptions are written for the user and should be
    printed as errors rather than raised as a traceback with a stack — a stack
    trace is no help to the user.
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
# Basics
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def project_dir_of(path) -> Path:
    """Accept a project directory or a project.json path; always return the
    project directory."""
    path = Path(path)
    if path.is_dir():
        return path
    if path.name == "project.json":
        return path.parent
    raise ValueError(f"give the project directory or the project.json inside it, not: {path}")


def transition(state, event):
    machine = load_json(STATE_FILE)
    if state not in machine["states"]:
        raise ValueError(f"unknown state: {state}. Available: {machine['states']}")
    nxt = machine["transitions"].get(state, {}).get(event)
    if not nxt:
        raise ValueError(
            f"transition not allowed: {state} + {event}. "
            f"Events available in that state: {sorted(machine['transitions'].get(state, {}))}"
        )
    return {"from": state, "event": event, "to": nxt}


def validate_project(path, use_schema=True):
    """Returns (errors, warnings)."""
    data = load_json(path)
    errors = []
    machine = load_json(STATE_FILE)
    if data.get("current_state") not in machine["states"]:
        errors.append(
            f"current_state is not a known state: {data.get('current_state')!r}. "
            f"Available: {machine['states']}"
        )
    if not isinstance(data.get("goals", []), list):
        errors.append("goals must be an array")
    if not isinstance(data.get("constraints", []), list):
        errors.append("constraints must be an array")

    warnings = []
    if use_schema:
        schema_path = sv.guess_schema(path, SCHEMAS)
        if schema_path is None:
            warnings.append(
                f"no schema matching {Path(path).name} was found; schema validation skipped"
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

            DocumentStore(directory).get(args.source_doc)  # raises if it is absent
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
            print("\nQuality warnings (writing was not blocked, but deal with them):",
                  file=sys.stderr)
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
                print(f"the evidence ledger is empty ({ledger.path})")
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
                f"\n{len(warnings)} quality warnings: the fields of these records are "
                f"legal, but methodologically they cannot support a judgement.",
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
            print(f"exported to {args.out}")
        else:
            print(text)
        return 0

    if args.action == "provenance":
        report = ledger_module.provenance_report(directory)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["dangling"]:
            print(
                f"\n{len(report['dangling'])} pieces of evidence have dangling sources "
                f"(they point at material that does not exist).",
                file=sys.stderr,
            )
            return 1
        if report["total"] and report["verifiable_ratio"] is not None:
            print(
                f"\nMachine-verifiable ratio: {report['verifiable_ratio']:.0%}"
                f" ({len(report['linked'])}/{report['total']})."
                f" Free-text sources cannot be verified automatically, only by hand.",
                file=sys.stderr,
            )
        return 0

    raise ValueError(f"unknown evidence action: {args.action}")


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
            print(f"spec saved: {http_api.save_spec(directory, spec)}")
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
            print("no material has been imported yet")
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
            print("no material has been imported yet")
            return 0
        bad = [e["doc_id"] for e in entries if not store.verify(e["doc_id"])]
        print(json.dumps(
            {"checked": len(entries), "tampered": bad}, ensure_ascii=False, indent=2
        ))
        return 1 if bad else 0

    raise ValueError(f"unknown source action: {args.action}")


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
            print(f"\n{len(reports)} runs totalled {total_calls} model calls, "
                  f"{sum(tokens):,} tokens", file=sys.stderr)
        else:
            print(f"\n{len(reports)} runs totalled {total_calls} model calls; "
                  f"some runs returned no usage, so the total is incomplete",
                  file=sys.stderr)
        states = {r["final_state"] for r in reports}
        print(f"\n{args.repeat} runs finished, {len(states)} distinct final states: "
              f"{sorted(states)}", file=sys.stderr)
        print(f"Compare: python {Path(__file__).name} compare {args.project} "
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
               else "not obtained")
        print(f"\nModel calls: {usage['calls']} ({usage['calls_with_usage']} returned usage), "
              f"{tok} tokens in total, {usage['seconds']}s elapsed", file=sys.stderr)
        if usage.get("note"):
            print(f"  ⚠ {usage['note']}", file=sys.stderr)
    cost = report.get("cost_estimate")
    if cost:
        print(f"  Estimated cost: {cost['total']} {cost['currency']}"
              f" (from the unit price you supplied; not a bill amount)", file=sys.stderr)

    print(f"\nArtefact directory: {report['run_dir']}", file=sys.stderr)
    print(f"Initial state {report['initial_state']} → final state {report['final_state']}",
          file=sys.stderr)
    if report.get("hint"):
        print(f"\nHint: {report['hint']}", file=sys.stderr)
    if report.get("gate_rejections"):
        print("\nRejected transitions (illegal events the model produced):", file=sys.stderr)
        for item in report["gate_rejections"]:
            print(f"  ✗ {item['phase']}: {item['event']} — {item['error']}",
                  file=sys.stderr)

    if args.mode == "dry-run" or args.provider == "manual":
        print(
            "\nThis is manual mode: only task packets were generated and no model "
            "was called.\n"
            f"Open the *.packet.md files under {report['run_dir']}, paste them into "
            "a model yourself, then save the output as a .md file of the same name.",
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
            print("\nQuality warnings (written, but deal with them):", file=sys.stderr)
            for warning in warnings:
                print(f"  ⚠ {warning}", file=sys.stderr)
        return 0

    if args.action == "list":
        records = store.list()
        if not records:
            print("no decision records yet")
            return 0
        for record in records:
            rid = record.get("decision_id")
            outcome = store.outcome_of(rid)
            status = "reviewed" if outcome else "pending review"
            print(
                f"{rid:<8}{status:<8}{record.get('review_date') or '(no review date)':<14}"
                f"{record.get('chosen_option')}"
            )
        return 0

    if args.action == "show":
        if not args.id:
            raise ValueError("decision show requires --id")
        record = store.load(args.id)
        outcome = store.outcome_of(args.id)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print("\n--- Review outcome ---")
        print(json.dumps(outcome, ensure_ascii=False, indent=2) if outcome
              else "Not reviewed yet.")
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
            raise ValueError("decision outcome requires --id")
        # --assumption-update "assumption text|CONFIRMED|short note"
        updates = []
        for raw in args.assumption_update or []:
            parts = [p.strip() for p in str(raw).split("|")]
            if len(parts) < 2:
                raise ValueError(
                    'assumption-update must be shaped "assumption text|CONFIRMED|note"; '
                    f"got: {raw!r}"
                )
            status = parts[1].upper()
            if status not in ("CONFIRMED", "REFUTED", "STILL_UNKNOWN"):
                raise ValueError(
                    f"the status in assumption-update must be CONFIRMED / REFUTED / "
                    f"STILL_UNKNOWN; got: {parts[1]!r}"
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
                f"\n{len(report['overdue'])} decisions are past their review date and "
                f"have not been reviewed. The methodology requires the D phase to "
                f"close — without review there is no learning.",
                file=sys.stderr,
            )
            return 1
        return 0

    if args.action == "import":
        # A decision record produced by a model is stored only after human
        # confirmation. Same principle as evidence: model output does not equal
        # an established decision.
        if not args.from_path:
            raise ValueError("decision import requires --from <decision_record.json>")
        source = Path(args.from_path)
        if not source.exists():
            raise ValueError(f"file not found: {source}")
        record = json.loads(source.read_text(encoding="utf-8"))
        record.pop("decision_id", None)      # renumber, so it cannot clash with an existing record
        saved = store.add(record)
        print(json.dumps({"imported": saved}, ensure_ascii=False, indent=2))
        print(
            "\nNote: this is a decision draft produced by a model, stored exactly as "
            "it stands. The review date and the falsification conditions need your "
            "own confirmation and edits.",
            file=sys.stderr,
        )
        for warning in decisions_module.quality_warnings(saved):
            print(f"  ⚠ {warning}", file=sys.stderr)
        return 0

    if args.action == "export":
        text = store.to_markdown()
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"exported to {args.out}")
        else:
            print(text)
        return 0

    raise ValueError(f"unknown decision action: {args.action}")


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
        except Exception as exc:  # noqa: BLE001 - a failed judgement must not discard the comparison
            result["agreement"] = {"judged_by_model": True, "error": str(exc)}

    text = compare_module.render_markdown(result)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written to {args.out}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(text)

    if result.get("agreement"):
        agreement = result["agreement"]
        print("\n" + "=" * 60)
        if agreement.get("error"):
            print(f"agreement judgement failed: {agreement['error']}", file=sys.stderr)
        else:
            print(f"Conclusions agree in direction: {agreement.get('agree')}"
                  f" (confidence {agreement.get('confidence')})")
            print(f"Shared direction: {agreement.get('direction')}")
            print(f"Reason: {agreement.get('why')}")
        print("\n⚠️ This is a model judgement, not a fact.", file=sys.stderr)

    # Return non-zero when the process is inconsistent, so scripts can rely on it
    return 0 if result["final_state_consistent"] else 1


def cmd_schema(args):
    schema_path = Path(args.schema_file) if args.schema_file else sv.guess_schema(
        args.file, SCHEMAS
    )
    if schema_path is None:
        print(json.dumps(
            {"valid": False,
             "errors": [f"cannot infer a schema for {args.file}; specify one with --schema-file"]},
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
# Entry point
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="rebuild",
        description="REBUILD — a decision-centric brand marketing methodology toolkit",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate project state (includes schema validation by default)")
    v.add_argument("project")
    v.add_argument("--no-schema", action="store_true", help="skip JSON Schema validation")

    t = sub.add_parser("transition", help="ask whether one state-machine transition is legal")
    t.add_argument("--state", required=True)
    t.add_argument("--event", required=True)

    s = sub.add_parser("schema", help="validate any JSON file against a schema")
    s.add_argument("file")
    s.add_argument("--schema-file", default=None)

    e = sub.add_parser("evidence", help="evidence ledger")
    e.add_argument("action",
                   choices=["add", "list", "check", "gaps", "export", "provenance"])
    e.add_argument("project")
    e.add_argument("--claim")
    e.add_argument("--type", choices=["FACT", "INFERENCE", "ASSUMPTION", "UNKNOWN"])
    e.add_argument("--confidence", choices=["HIGH", "MEDIUM", "LOW"])
    e.add_argument("--min-confidence", choices=["HIGH", "MEDIUM", "LOW"])
    e.add_argument("--source", default=None,
                   help="free-text source; cannot be verified automatically")
    e.add_argument("--source-doc", default=None, dest="source_doc",
                   help="an id pointing into the material library (e.g. DOC-001); machine-verifiable")
    e.add_argument("--observed-at", default=None)
    e.add_argument("--scope", default=None)
    e.add_argument("--decision-impact", default=None)
    e.add_argument("--recheck-trigger", default=None)
    e.add_argument("--counter-evidence", action="append")
    e.add_argument("--id", default=None)
    e.add_argument("--json", action="store_true")
    e.add_argument("--out", default=None)

    d = sub.add_parser("decision", help="decision records and review")
    d.add_argument("action",
                   choices=["add", "list", "show", "validate", "outcome",
                            "due", "export", "import"])
    d.add_argument("project")
    d.add_argument("--id", default=None)
    d.add_argument("--question", default=None)
    d.add_argument("--deadline", default=None)
    d.add_argument("--option", action="append",
                   help='an option, shaped "name|rationale"; repeatable')
    d.add_argument("--chosen", default=None, help="name of the option chosen")
    d.add_argument("--rejected", action="append",
                   help='a rejected option, shaped "name|reason"; repeatable')
    d.add_argument("--tradeoff", action="append", help="a trade-off; repeatable")
    d.add_argument("--assumption", action="append", help="a key assumption; repeatable")
    d.add_argument("--falsification", action="append",
                   help="a falsification condition; repeatable")
    d.add_argument("--validation", action="append", help="a validation action; repeatable")
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
                   help='update a key assumption during review, shaped '
                        '"assumption text|CONFIRMED|note"; '
                        'status may be CONFIRMED / REFUTED / STILL_UNKNOWN')
    d.add_argument("--notes", default=None)
    d.add_argument("--out", default=None)
    d.add_argument("--from", default=None, dest="from_path",
                   help="import: import a decision record JSON from a run artefact")

    src = sub.add_parser("source", help="data sources")
    src.add_argument("action",
                     choices=["add-file", "add-url", "list", "show", "verify"])
    src.add_argument("project")
    src.add_argument("path", nargs="?", help="file path for add-file")
    src.add_argument("--name", default=None)
    src.add_argument("--url", default=None)
    src.add_argument("--method", default="GET")
    src.add_argument("--header", action="append", help="shaped NAME=VALUE")
    src.add_argument("--header-env", action="append", help="shaped NAME=ENV_VAR")
    src.add_argument("--records-path", default=None)
    src.add_argument("--timeout", type=int, default=30)
    src.add_argument("--save-spec", action="store_true")
    src.add_argument("--doc-id", default=None, dest="doc_id")

    c = sub.add_parser("compare", help="compare multiple runs of one project (process reproducibility + optional agreement of conclusions)")
    c.add_argument("project")
    c.add_argument("--last", type=int, default=None, help="compare only the most recent N runs")
    c.add_argument("--judge-with", default=None, dest="judge_with",
                   help="use the given provider to judge whether the conclusions point "
                        "the same way. This is a model judgement, not a fact")
    c.add_argument("--json", action="store_true")
    c.add_argument("--out", default=None)

    r = sub.add_parser("run", help="runtime orchestration: schedule roles, judge gates, advance state")
    r.add_argument("project")
    r.add_argument("--provider", default="manual",
                   help="manual (default, zero network) or a preset name from bench/provider.py")
    r.add_argument("--phase", action="append", help="run only the given phase; repeatable")
    r.add_argument("--dry-run", action="store_true", help="generate task packets only")
    r.add_argument("--max-evidence", type=int, default=60)
    r.add_argument("--repeat", type=int, default=1,
                   help="number of repeated runs. Running the same input several times "
                        "reveals consistency; use together with the `compare` subcommand")
    r.add_argument("--price-input", type=float, default=None, dest="price_input",
                   help="input token unit price (per million). If omitted, only tokens are "
                        "counted and no cost is computed — this project hard-codes no "
                        "prices, because prices change")
    r.add_argument("--price-output", type=float, default=None, dest="price_output",
                   help="output token unit price (per million)")
    r.add_argument("--currency", default="USD", help="pricing currency, used for labelling only")
    r.add_argument("--temperature", type=float, default=0.3,
                   help="sampling temperature, default 0.3. Setting it to 0 improves "
                        "consistency across runs, but most APIs do not guarantee full "
                        "determinism, so repeated runs are still needed to verify")
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
        raise ValueError(f"unknown subcommand: {args.cmd}")
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
        print(json.dumps({"error": f"JSON parse failed: {exc}"},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
