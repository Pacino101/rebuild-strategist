#!/usr/bin/env python3
"""A minimal JSON Schema validator (pure standard library).

Coverage: the subset of keywords the `schemas/` directory of this repository
actually uses, plus a handful of common keywords.

Design principle
----------------
**Unimplemented keywords are recorded as warnings, never silently ignored.**
Silently ignoring them turns "validation passed" into an illusion — if a schema
writes `pattern` and nobody checks it, the user believes they are protected.
That is exactly the kind of self-deception this project exists to avoid.

Not implemented: `$ref`, `not`, `if/then/else`, `dependentSchemas`, `format`,
`unevaluatedProperties` and so on. When they are used they raise an explicit
warning; they never pretend to pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

#: Keywords this validator knows. Anything outside the list is warned about.
KNOWN_KEYWORDS = {
    "$schema", "$id", "$comment", "title", "description", "default", "examples",
    "type", "enum", "const",
    "properties", "required", "additionalProperties", "propertyNames",
    "items", "minItems", "maxItems", "uniqueItems",
    "minLength", "maxLength", "pattern",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "anyOf", "oneOf", "allOf",
}

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    # bool is a subclass of int and must be excluded explicitly, otherwise True
    # would count as a valid integer
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def type_name(value):
    """Return the JSON type name of an instance."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


class _Context:
    __slots__ = ("errors", "warnings")

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path, message):
        self.errors.append(f"{path}: {message}")

    def warn(self, path, message):
        self.warnings.append(f"{path}: {message}")


def validate(instance, schema, path="$"):
    """Validate an instance. Returns `(errors, warnings)`, both lists of strings.

    Empty errors means it passed; non-empty warnings mean some constraints were
    **not checked**, and the caller should judge the credibility of that "pass"
    accordingly.
    """
    ctx = _Context()
    _validate(instance, schema, path, ctx)
    return ctx.errors, ctx.warnings


def _validate(instance, schema, path, ctx):
    if not isinstance(schema, dict):
        ctx.warn(path, f"schema is not an object ({type_name(schema)}), skipped")
        return

    for keyword in schema:
        if keyword not in KNOWN_KEYWORDS:
            ctx.warn(
                path,
                f"schema uses the unimplemented keyword '{keyword}'; "
                "that constraint was not checked",
            )

    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        unknown = [o for o in options if o not in _TYPE_CHECKS]
        if unknown:
            ctx.warn(path, f"unknown type value {unknown}; type check skipped")
        elif not any(_TYPE_CHECKS[o](instance) for o in options):
            wanted = "/".join(str(o) for o in options)
            ctx.error(
                path,
                f"type should be {wanted}, got {type_name(instance)}",
            )
            # When the type does not match, later constraints for that type are
            # meaningless, so return right away
            return

    if "const" in schema and instance != schema["const"]:
        ctx.error(path, f"should equal the constant {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        ctx.error(path, f"value must be one of [{allowed}], got {instance!r}")

    if isinstance(instance, bool) or instance is None:
        pass
    elif isinstance(instance, str):
        _validate_string(instance, schema, path, ctx)
    elif isinstance(instance, (int, float)):
        _validate_number(instance, schema, path, ctx)
    elif isinstance(instance, list):
        _validate_array(instance, schema, path, ctx)
    elif isinstance(instance, dict):
        _validate_object(instance, schema, path, ctx)

    _validate_combinators(instance, schema, path, ctx)


def _validate_string(instance, schema, path, ctx):
    if "minLength" in schema and len(instance) < schema["minLength"]:
        ctx.error(path, f"length should be ≥ {schema['minLength']}, got {len(instance)}")
    if "maxLength" in schema and len(instance) > schema["maxLength"]:
        ctx.error(path, f"length should be ≤ {schema['maxLength']}, got {len(instance)}")
    pattern = schema.get("pattern")
    if pattern is not None:
        try:
            if re.search(pattern, instance) is None:
                ctx.error(path, f"does not match pattern {pattern!r}")
        except re.error as exc:
            ctx.warn(path, f"the pattern in schema cannot be compiled ({exc}); not checked")


def _validate_number(instance, schema, path, ctx):
    if "minimum" in schema and instance < schema["minimum"]:
        ctx.error(path, f"should be ≥ {schema['minimum']}, got {instance}")
    if "maximum" in schema and instance > schema["maximum"]:
        ctx.error(path, f"should be ≤ {schema['maximum']}, got {instance}")
    if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
        ctx.error(path, f"should be > {schema['exclusiveMinimum']}, got {instance}")
    if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
        ctx.error(path, f"should be < {schema['exclusiveMaximum']}, got {instance}")
    if "multipleOf" in schema:
        divisor = schema["multipleOf"]
        if divisor and (instance % divisor) != 0:
            ctx.error(path, f"should be a multiple of {divisor}, got {instance}")


def _validate_array(instance, schema, path, ctx):
    if "minItems" in schema and len(instance) < schema["minItems"]:
        ctx.error(path, f"number of items should be ≥ {schema['minItems']}, got {len(instance)}")
    if "maxItems" in schema and len(instance) > schema["maxItems"]:
        ctx.error(path, f"number of items should be ≤ {schema['maxItems']}, got {len(instance)}")
    if schema.get("uniqueItems") and len(instance) != len(
        {json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) for item in instance}
    ):
        ctx.error(path, "items should be unique")
    item_schema = schema.get("items")
    if item_schema is not None:
        for index, item in enumerate(instance):
            _validate(item, item_schema, f"{path}[{index}]", ctx)


def _validate_object(instance, schema, path, ctx):
    for key in schema.get("required", []):
        if key not in instance:
            ctx.error(path, f"missing required field '{key}'")

    properties = schema.get("properties", {})
    for key, subschema in properties.items():
        if key in instance:
            _validate(instance[key], subschema, f"{path}.{key}", ctx)

    if schema.get("additionalProperties") is False:
        extra = [k for k in instance if k not in properties]
        if extra:
            shown = ", ".join(repr(k) for k in sorted(extra)[:5])
            more = "" if len(extra) <= 5 else f" and {len(extra)} in total"
            ctx.error(path, f"undeclared fields present: {shown}{more}")
    elif isinstance(schema.get("additionalProperties"), dict):
        for key in instance:
            if key not in properties:
                _validate(
                    instance[key], schema["additionalProperties"],
                    f"{path}.{key}", ctx,
                )

    if isinstance(schema.get("propertyNames"), dict):
        for key in instance:
            _validate(key, schema["propertyNames"], f"{path}.<key {key!r}>", ctx)


def _subschema_ok(instance, subschema, path):
    """Trial-run one sub-schema in an isolated context. Returns
    (passed, errors, warnings)."""
    sub = _Context()
    _validate(instance, subschema, path, sub)
    return (not sub.errors), sub.errors, sub.warnings


def _validate_combinators(instance, schema, path, ctx):
    if "allOf" in schema:
        for index, subschema in enumerate(schema["allOf"]):
            _validate(instance, subschema, path, ctx)

    for keyword, rule in (("anyOf", "at least"), ("oneOf", "exactly")):
        options = schema.get(keyword)
        if not options:
            continue
        results = [_subschema_ok(instance, option, path) for option in options]
        passed = sum(1 for ok, _, _ in results if ok)
        if keyword == "anyOf":
            if passed == 0:
                detail = "; ".join(results[0][1][:2]) if results else ""
                ctx.error(path, f"anyOf: no branch passed. First branch error: {detail}")
        else:  # oneOf
            if passed != 1:
                ctx.error(
                    path,
                    f"oneOf: {rule} 1 branch should pass, but {passed} did",
                )
        # Keywords used inside combinators must also be exposed to the caller,
        # so that a "pass" cannot hide unchecked constraints
        for _, _, warns in results:
            for warning in warns:
                if warning not in ctx.warnings:
                    ctx.warnings.append(warning)


# ---------------------------------------------------------------------------
# File-level convenience interface
# ---------------------------------------------------------------------------

def load_schema(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_instance(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_file(instance_path, schema_path):
    """Validate one JSON file against the given schema. Returns (errors, warnings)."""
    return validate(load_instance(instance_path), load_schema(schema_path))


#: Conventional mapping from file name → schema file, used by the CLI to pick a
#: schema automatically.
DEFAULT_SCHEMA_MAP = {
    "project.json": "project.schema.json",
    "project_state.json": "project.schema.json",
    "evidence.json": "evidence.schema.json",
    "decision_record.json": "decision_record.schema.json",
    "experiment.json": "experiment.schema.json",
    "kpi_tree.json": "kpi_tree.schema.json",
}


def guess_schema(instance_path, schema_dir):
    """Guess the matching schema from the file name. Returns None if it cannot."""
    name = Path(instance_path).name
    candidate = DEFAULT_SCHEMA_MAP.get(name)
    if candidate is None:
        return None
    resolved = Path(schema_dir) / candidate
    return resolved if resolved.exists() else None
