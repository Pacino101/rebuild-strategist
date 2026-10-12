#!/usr/bin/env python3
"""Upstream-JSON adapter — consume figures produced by another tool (MCP, warehouse export, script).

STRUCTURALLY DIFFERENT FROM THE OTHER TWO EXAMPLES
--------------------------------------------------
  csv_export.py   reads a file you exported by hand            (manual path)
  posthog.py      calls an HTTP API with credentials            (live path)
  upstream_json.py reads a documented JSON envelope on stdin    (tool-to-tool path)

The third shape is how an MCP server, a dbt run, an Airflow task or a colleague's script hands
data over without either side knowing the other's internals. There is no network, no credential
and no vendor assumption — only a declared envelope.

THE ENVELOPE
  {
    "source_system": "warehouse",            required
    "resource": "finance.monthly_unit_econ", required — what was queried
    "method": "dbt run --select unit_econ",  optional
    "generated_at": "2026-10-12T21:00:00+08:00",  optional
    "measures": [                            required
      {"name": "price_per_unit", "value": 99, "grade": "A", "note": "from orders table"},
      {"name": "gross_margin_pct", "value": 0.42, "grade": "A"}
    ]
  }

WHY AN ENVELOPE AND NOT JUST A DICT OF NUMBERS
  A bare {"price_per_unit": 99} carries no provenance, so the adapter would have to invent grades —
  exactly what resources/ADAPTER_CONTRACT.md forbids. The envelope forces the upstream tool to say
  where each number came from and how good it is. If the upstream cannot say, the number does not
  get used.

UNIT CONVERSION IS DECLARED, NOT ASSUMED
  A margin percentage is not a cost. `gross_margin_pct: 0.42` alongside `price_per_unit: 99`
  derives `variable_cost_per_unit = 99 * (1 - 0.42)`, and the derivation is recorded with the note
  so a reviewer can check the arithmetic. Anything converted without a note is a bug.

USAGE
  python3 tools/adapters/upstream_json.py < envelope.json
  cat envelope.json | python3 tools/adapters/upstream_json.py --system warehouse
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone

# Fields strategy_calc.py consumes. Anything else is reported as unrecognised, not silently kept.
NUMERIC_FIELDS = {
    "price_per_unit", "variable_cost_per_unit", "purchases_per_month", "retention_months",
    "discount_rate_monthly", "monthly_fixed_costs", "capacity_units", "marketing_budget",
    "expected_new_customers", "expected_units", "claimed_cac", "payback_tolerance_months",
    "margin_of_safety", "test_baseline_rate", "test_relative_effect", "available_sample",
}
GRADES = {"A", "B", "C", "D", "E", "NOT_GRADED"}


def parse_envelope(text: str) -> dict:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: stdin is not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise SystemExit("error: the envelope must be a JSON object")
    for key in ("source_system", "measures"):
        if key not in doc:
            raise SystemExit(f"error: the envelope is missing '{key}' — "
                             f"see the docstring for the required shape")
    if not isinstance(doc["measures"], list) or not doc["measures"]:
        raise SystemExit("error: 'measures' must be a non-empty list")
    return doc


def build(doc: dict, *, system_override: str | None = None) -> dict:
    model: dict = {}
    provenance: list[dict] = []
    missing: list[str] = []
    unused: list[str] = []

    for measure in doc["measures"]:
        if not isinstance(measure, dict):
            missing.append("a measure that was not an object")
            continue
        name = str(measure.get("name", "")).strip()
        if not name:
            missing.append("a measure with no name")
            continue
        grade = str(measure.get("grade", "NOT_GRADED")).strip().upper()
        if grade not in GRADES:
            print(f"warning: unrecognised grade {grade!r} for {name}; treating as NOT_GRADED",
                  file=sys.stderr)
            grade = "NOT_GRADED"
        value = measure.get("value")
        note = measure.get("note")

        # ---- declared conversions. Each one records its own arithmetic. ----
        if name == "gross_margin_pct":
            price = next((m["value"] for m in doc["measures"]
                          if isinstance(m, dict) and m.get("name") == "price_per_unit"), None)
            if not isinstance(value, (int, float)) or not (0 < value < 1):
                missing.append(f"gross_margin_pct ({value!r} is not a fraction between 0 and 1)")
                continue
            if not isinstance(price, (int, float)):
                missing.append("variable_cost_per_unit (needs price_per_unit to convert a margin)")
                continue
            cost = price * (1 - value)
            model["variable_cost_per_unit"] = cost
            provenance.append({
                "field": "variable_cost_per_unit",
                "source_field": "gross_margin_pct",
                "note": f"derived: {price} × (1 − {value}) = {cost:.4f}",
                "grade": grade,
            })
            continue

        if name == "monthly_revenue":
            # Recognised as real, but strategy_calc.py does not consume it. Keeping it in `model`
            # would fail the output schema; dropping it without a word would hide that the
            # upstream supplied something we did not use. So it is recorded in provenance only,
            # and flagged as unused.
            if isinstance(value, (int, float)) and value > 0:
                provenance.append({"field": "monthly_revenue", "source_field": "monthly_revenue",
                                   "note": "supplied by upstream but NOT consumed by "
                                           "strategy_calc.py; not placed in `model`",
                                   "grade": grade})
                unused.append("monthly_revenue (supplied, not consumed)")
            else:
                missing.append("monthly_revenue (not a positive number)")
            continue

        # ---- pass-through numerics ----
        if name in NUMERIC_FIELDS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                missing.append(f"{name} (not numeric: {value!r})")
                continue
            if not math.isfinite(value):
                missing.append(f"{name} (not finite: {value!r})")
                continue
            model[name] = float(value)
            provenance.append({"field": name, "source_field": name,
                               "note": note or "direct passthrough", "grade": grade})
            continue

        # ---- anything else: report it, never drop it silently ----
        missing.append(f"{name} (unrecognised field name)")

    # Anything the upstream gave us that we did not consume is reported, not swallowed.
    missing.extend(unused)

    return {
        "adapter": "upstream-json",
        "source": {
            "system": system_override or doc["source_system"],
            "resource": doc.get("resource") or "unspecified",
            "retrieved_at": doc.get("generated_at")
                            or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "method": doc.get("method") or "JSON envelope on stdin",
            # This adapter reads a handed-over document. However good that document is, it is
            # not a live read, so it cannot evidence more than `configured`.
            "status": "configured",
        },
        "model": model,
        "provenance": provenance,
        "missing": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--system", default=None, help="override source_system for the record")
    ap.add_argument("--file", default=None, help="read the envelope from a file instead of stdin")
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    if not text.strip():
        print("error: no envelope on stdin", file=sys.stderr)
        return 2

    result = build(parse_envelope(text), system_override=args.system)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    if result["missing"]:
        print(f"note: {len(result['missing'])} measure(s) not usable: "
              f"{', '.join(result['missing'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
