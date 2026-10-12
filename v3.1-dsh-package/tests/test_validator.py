#!/usr/bin/env python3
"""Unit tests for tests/schema_validator.py, then adversarial tests on the real schemas.

Run: python3 tests/test_validator.py

Part 1 anchors the validator itself against the exact keyword interactions the package's
schemas rely on — in particular `anyOf` alongside sibling keywords, and
`additionalProperties` scope. Part 2 is the adversarial suite the growth-diagnosis run
demanded: semantically empty documents must be rejected, not merely structurally valid ones.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schema_validator import SchemaError, Validator  # noqa: E402

FAILS = []


def _raises(fn):
    try:
        fn()
        return False
    except SchemaError:
        return True


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")


# --------------------------------------------------------------- part 1: validator
print("Part 1 — validator keyword semantics")

v = Validator({"anyOf": [{"required": ["a"]}, {"required": ["b"]}],
               "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
               "additionalProperties": False})
check("anyOf satisfied + siblings honoured", v.iter_errors({"a": "x"}), [])
check("anyOf satisfied but sibling type wrong", bool(v.iter_errors({"b": "not-an-int"})), True)
check("anyOf unsatisfied", bool(v.iter_errors({"c": 1})), True)
check("additionalProperties scope: nested object uses its OWN props",
      Validator({"properties": {"o": {"properties": {"in": {"type": "string"}},
                                     "additionalProperties": False}},
                 "additionalProperties": False}).iter_errors({"o": {"in": "x"}}), [])

check("$ref local resolves",
      Validator({"$defs": {"s": {"type": "string"}},
                 "properties": {"a": {"$ref": "#/$defs/s"}}}).iter_errors({"a": "y"}), [])
check("$ref local type violation",
      bool(Validator({"$defs": {"s": {"type": "string"}},
                      "properties": {"a": {"$ref": "#/$defs/s"}}}).iter_errors({"a": 3})), True)

check("if/then applies when condition met",
      bool(Validator({"if": {"required": ["k"]}, "then": {"required": ["must"]}})
           .iter_errors({"k": 1})), True)
check("if/then skipped when condition unmet",
      Validator({"if": {"required": ["k"]}, "then": {"required": ["must"]}}).iter_errors({}), [])
check("const mismatch detected",
      bool(Validator({"properties": {"t": {"const": "guardrail"}}}).iter_errors({"t": "outcome"})), True)
check("minItems enforced",
      bool(Validator({"properties": {"g": {"type": "array", "minItems": 1}}})
           .iter_errors({"g": []})), True)
check("minProperties enforced",
      bool(Validator({"properties": {"o": {"type": "object", "minProperties": 1}}})
           .iter_errors({"o": {}})), True)
check("unsupported keyword refuses loudly",
      _raises(lambda: Validator({"patternProperties": {}})), True)
check("unknown keyword refuses loudly",
      _raises(lambda: Validator({"banana": 1})), True)


# --------------------------------------------------- part 2: adversarial on real schemas
SCHEMA_DIR = os.path.join(HERE, "..", "resources", "schemas")


def load(name):
    with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as fh:
        return Validator(json.load(fh), root_dir=SCHEMA_DIR)


print("\nPart 2 — adversarial tests on the shipped schemas")
exp = load("experiment.schema.json")
kpi = load("kpi_tree.schema.json")
state = load("project_state.schema.json")

GARBAGE_EXP = {
    "experiment_id": "E1", "hypothesis": "h", "audience": "a", "variant": "v",
    "primary_metric": "impressions", "guardrails": [], "decision_rule": "we'll see",
    "status": "complete",
}
check("experiment: no control, empty guardrails, vague rule -> rejected",
      exp.is_valid(GARBAGE_EXP), False)

GOOD_EXP = {
    "experiment_id": "E1", "hypothesis": "elasticity holds at 14", "audience": "tier-1 stores",
    "control": "12 CNY", "variant": "14 CNY", "primary_metric": "units per store per week",
    "primary_metric_definition": "units sold / store-weeks observed",
    "guardrails": ["return rate"],
    "guardrail_thresholds": {"return rate": "> 5%"},
    "minimum_detectable_effect": {"value": "0.1 units", "method": "two-proportion z-test",
                                  "n_per_arm": 100, "available_n": 120, "adequate": True},
    "decision_rule": {"pass": "ship", "fail": "stop", "inconclusive": "extend 2 weeks",
                      "threshold": ">= 0.85x control units"},
    "status": "proposed", "claim_strength": "directional", "limitations": ["single city"],
}
check("experiment: complete card -> accepted", exp.is_valid(GOOD_EXP), True)

NO_CONTROL = dict(GOOD_EXP, control="", status="complete")
check("experiment: complete but undeclared control -> rejected", exp.is_valid(NO_CONTROL), False)

NODE = {"metric_name": "m", "definition": "d", "unit": "%", "period": "monthly",
        "source_of_truth": "ERP", "owner": "CFO"}

check("kpi: guardrail without threshold -> rejected",
      kpi.is_valid({"root": dict(NODE, metric_type="guardrail")}), False)
check("kpi: guardrail with threshold -> accepted",
      kpi.is_valid({"root": dict(NODE, metric_type="guardrail", guardrail_threshold="< 3%")}), True)
check("kpi: outcome without target -> rejected",
      kpi.is_valid({"root": dict(NODE, metric_type="outcome")}), False)
check("kpi: outcome with target -> accepted",
      kpi.is_valid({"root": dict(NODE, metric_type="outcome", target="+8pp")}), True)
check("kpi: neither root nor nodes -> rejected", kpi.is_valid({"objective": "x"}), False)
check("kpi: nested children accepted",
      kpi.is_valid({"root": dict(NODE, metric_type="outcome", target="+8pp",
                                 children=[dict(NODE, metric_type="diagnostic")])}), True)

STATE = {
    "project_id": "p", "project_name": "n", "version": "1", "current_phase": "B",
    "project_contract": {"objective": "decide"}, "gate_status": {"R": "PASS"},
    "decisions": [], "evidence": [], "assumptions": [], "tasks": [], "risks": [],
    "open_questions": [], "change_log": [],
}
check("state: minimal valid document -> accepted", state.is_valid(STATE), True)
check("state: unknown top-level property -> rejected",
      state.is_valid(dict(STATE, banana=1)), False)
check("state: kpi_tree must satisfy the KPI schema -> rejected on garbage",
      state.is_valid(dict(STATE, kpi_tree={"garbage": 1})), False)

print()
if FAILS:
    print(f"RESULT: FAIL ({len(FAILS)} assertion(s))")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("RESULT: PASS (all validator and adversarial assertions)")
