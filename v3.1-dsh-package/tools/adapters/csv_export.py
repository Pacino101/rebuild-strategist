#!/usr/bin/env python3
"""Reference data adapter — a CSV export, no network, no credentials, no dependencies.

Copy this shape. It exists to make the contract in resources/ADAPTER_CONTRACT.md concrete:
an adapter converts one external source into the business-model JSON that
tools/strategy_calc.py consumes, and it declares what it could not find rather than defaulting it.

USAGE
  python3 tools/adapters/csv_export.py --input figures.csv
  python3 tools/adapters/csv_export.py --input figures.csv --system Shopify --resource "orders export"

INPUT — a two-column CSV. The first column names a business-model field; the second is its value
and, optionally, its grade:

  field,value,grade
  price_per_unit,99,A
  variable_cost_per_unit,18,A
  retention_months,24,B
  test_baseline_rate,0.042,A

Recognised fields are the ones tools/strategy_calc.py accepts. An unrecognised field name is
reported as missing rather than silently passed through — a typo must not look like data.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

# The fields strategy_calc.py understands. Kept explicit so a typo fails loudly.
NUMERIC_FIELDS = {
    "price_per_unit", "variable_cost_per_unit", "purchases_per_month", "retention_months",
    "discount_rate_monthly", "monthly_fixed_costs", "capacity_units", "marketing_budget",
    "expected_new_customers", "expected_units", "claimed_cac", "payback_tolerance_months",
    "margin_of_safety", "test_baseline_rate", "test_relative_effect", "available_sample",
}
GRADES = {"A", "B", "C", "D", "E", "NOT_GRADED"}


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def build(rows: list[dict], system: str, resource: str) -> dict:
    model: dict = {}
    provenance: list[dict] = []
    missing: list[str] = []

    for row in rows:
        field = (row.get("field") or "").strip()
        raw = (row.get("value") or "").strip()
        grade = (row.get("grade") or "NOT_GRADED").strip().upper()

        if not field:
            continue
        if grade not in GRADES:
            # A malformed grade is a data-quality problem, not something to guess at.
            print(f"warning: unrecognised grade {grade!r} for {field}; treating as NOT_GRADED",
                  file=sys.stderr)
            grade = "NOT_GRADED"

        if field not in NUMERIC_FIELDS:
            # Not a field this project uses — do not drop it silently.
            missing.append(f"{field} (unrecognised field name)")
            continue
        if raw == "":
            missing.append(field)
            continue
        try:
            model[field] = float(raw)
        except ValueError:
            missing.append(f"{field} (not numeric: {raw!r})")
            continue

        provenance.append({"field": field, "source_field": field, "grade": grade})

    return {
        "adapter": "csv-export",
        "source": {
            "system": system,
            "resource": resource,
            "retrieved_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "method": "manual CSV export",
            # An adapter that has only ever read a file is `configured` at most. It becomes
            # `connected` when it has read the live system and that was recorded. Do not raise
            # this without the observation.
            "status": "configured",
        },
        "model": model,
        "provenance": provenance,
        "missing": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True, help="path to the CSV export")
    ap.add_argument("--system", default="unknown", help="name of the source system")
    ap.add_argument("--resource", default=None, help="what was exported")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"error: no such file: {args.input}", file=sys.stderr)
        return 2

    rows = read_csv(args.input)
    if not rows:
        print("error: the export contains no rows", file=sys.stderr)
        return 2

    result = build(rows, args.system, args.resource or os.path.basename(args.input))
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    if result["missing"]:
        # A gap is not a failure of the adapter; hiding it would be.
        print(f"note: {len(result['missing'])} field(s) not sourced: "
              f"{', '.join(result['missing'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
