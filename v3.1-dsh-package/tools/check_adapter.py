#!/usr/bin/env python3
"""check_adapter — verify that a data adapter honours resources/ADAPTER_CONTRACT.md.

An adapter is only useful if it can be trusted not to have invented something. This runs your
adapter, validates its output against adapter_output.schema.json, and then applies the rules a
schema cannot express.

USAGE
  python3 tools/check_adapter.py --adapter ./my_adapter.sh -- --input figures.csv
  python3 tools/check_adapter.py --self-test

EXIT
  0  the adapter honours the contract (that makes it `configured`, not `connected`)
  1  the adapter violates the contract; the reasons are printed
  2  the checker could not run the adapter at all
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from schema_validator import Validator  # noqa: E402

SCHEMA_PATH = os.path.join(ROOT, "resources", "schemas", "adapter_output.schema.json")


def load_schema() -> Validator:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return Validator(json.load(fh), root_dir=os.path.dirname(SCHEMA_PATH))


def run_adapter(command: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        raise SystemExit(f"error: cannot execute {command[0]!r}")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"error: adapter timed out after {timeout}s")


def check(doc: dict, schema: Validator, *, expect_missing_ok: bool = True) -> list[str]:
    """Schema validation, then the contract rules a schema cannot state."""
    problems = schema.iter_errors(doc)
    problems = [f"schema: {p}" for p in problems]
    if problems:
        return problems

    source = doc["source"]
    model = doc["model"]
    provenance = {p["field"]: p for p in doc.get("provenance", [])}
    missing = doc["missing"]

    # Rule 2 — derived fields must be declared. A field present in `model` whose name differs from
    # anything in the source metadata, or which has a transformation note, needs provenance.
    for field in model:
        if field not in provenance:
            # Passthroughs are allowed to omit provenance only when the field name matches a
            # source column; without extra metadata we cannot prove that, so ask for it.
            problems.append(
                f"rule 2: '{field}' has no provenance entry — declare where it came from or "
                f"state that it is a direct passthrough")

    # Rule 3 — grades must be from the skill's own scale.
    for field, entry in provenance.items():
        if entry.get("grade") in (None, ""):
            problems.append(f"rule 3: '{field}' has no grade")

    # Rule 1 — a field cannot be both supplied and reported missing.
    both = sorted(set(model) & set(missing))
    if both:
        problems.append(f"rule 1: {both} appear in both `model` and `missing`")

    # Rule 5 — an empty `missing` is a claim. If the source clearly had gaps and the adapter
    # reported none, that is the failure this contract exists to prevent; we can only flag the
    # unambiguous case of a model with no derived fields at all and no provenance.
    if not missing and not model:
        problems.append("rule 1: no fields supplied and none reported missing — "
                        "an adapter that finds nothing must say so in `missing`")

    # Rule 6 — the status an adapter may claim about itself.
    if source["status"] in {"connected", "tested", "production_approved"}:
        problems.append(
            f"rule 6: adapter claims status '{source['status']}'. A checker run cannot evidence "
            f"more than 'configured' — a live connection must be recorded separately with its "
            f"observation")

    return problems


def self_test() -> int:
    """Prove the checker actually rejects bad adapters, not just accepts good ones."""
    schema = load_schema()
    good = {
        "adapter": "t", "source": {"system": "s", "resource": "r",
                                   "retrieved_at": "2026-10-12T00:00:00+08:00",
                                   "method": "manual CSV export", "status": "configured"},
        "model": {"price_per_unit": 99},
        "provenance": [{"field": "price_per_unit", "source_field": "price", "grade": "A"}],
        "missing": ["variable_cost_per_unit"],
    }
    cases = [
        ("a conforming adapter passes", good, 0),
        ("invented value with no provenance is rejected",
         {**good, "provenance": []}, 1),
        ("a field both supplied and missing is rejected",
         {**good, "missing": ["price_per_unit"]}, 1),
        ("claiming 'connected' from a file read is rejected",
         {**good, "source": {**good["source"], "status": "connected"}}, 1),
        ("unknown grade is rejected",
         {**good, "provenance": [{"field": "price_per_unit", "grade": "Z"}]}, 1),
        ("missing source metadata is rejected",
         {**good, "source": {"system": "s"}}, 1),
        ("an extra top-level key is rejected",
         {**good, "extra": 1}, 1),
        ("everything empty is rejected",
         {"adapter": "t",
          "source": {"system": "s", "resource": "r", "retrieved_at": "x",
                     "method": "m", "status": "configured"},
          "model": {}, "provenance": [], "missing": []}, 1),
    ]
    fails = 0
    for label, doc, want in cases:
        got = 1 if check(doc, schema) else 0
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    print()
    if fails:
        print(f"RESULT: FAIL ({fails})")
        return 1
    print("RESULT: PASS (the checker rejects every malformed adapter it was given)")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    if argv[0] == "--self-test":
        return self_test()

    adapter = None
    timeout = 60
    passthrough: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--adapter":
            adapter = argv[i + 1]; i += 2
        elif token == "--timeout":
            timeout = int(argv[i + 1]); i += 2
        elif token == "--":
            # Everything after `--` goes to the adapter untouched. This is deliberate:
            # the adapter's own flags must not be parsed by this checker.
            passthrough = argv[i + 1:]
            break
        else:
            print(f"error: unexpected argument {token!r}; pass adapter arguments after '--'",
                  file=sys.stderr)
            return 2

    if not adapter:
        print("error: --adapter is required", file=sys.stderr)
        return 2

    command = ([sys.executable, adapter] if adapter.endswith(".py") else [adapter]) + passthrough
    code, out, err = run_adapter(command, timeout)
    if err:
        print(f"adapter stderr:\n{err.rstrip()}", file=sys.stderr)
    if code != 0:
        print(f"FAIL: adapter exited {code}; a partial success must not exit 0", file=sys.stderr)
        return 1
    try:
        doc = json.loads(out)
    except json.JSONDecodeError as exc:
        print(f"FAIL: adapter did not emit JSON on stdout: {exc}", file=sys.stderr)
        return 1

    problems = check(doc, load_schema())
    if problems:
        print(f"FAIL: {len(problems)} contract violation(s):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"PASS: adapter '{doc['adapter']}' honours the contract.")
    print(f"  status claimed : {doc['source']['status']} (a checker run cannot evidence more)")
    print(f"  fields supplied: {len(doc['model'])}")
    print(f"  fields missing : {len(doc['missing'])}"
          + (f" — {', '.join(doc['missing'])}" if doc['missing'] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
