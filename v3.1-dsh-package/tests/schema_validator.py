#!/usr/bin/env python3
"""A small JSON Schema subset validator for this package's schemas.

WHY THIS EXISTS
---------------
`jsonschema` cannot be installed into the bundled runtime on this machine: its compiled
`rpds` dependency fails to load under macOS code signing. Rather than ship a validator that
silently mis-validates, this module implements exactly the keywords the five schemas in
`resources/schemas/` actually use, and is itself covered by unit tests in
`tests/test_validator.py`.

SUPPORTED: type, enum, const, properties, required, additionalProperties (bool or schema),
items, minItems, minProperties, minLength, maxLength, minimum, maximum, allOf, anyOf, oneOf,
not, if/then/else, $ref (local `#/$defs/x` and cross-file `other.json#/$defs/x`), $defs.

NOT SUPPORTED (and rejected loudly rather than ignored): patternProperties, dependencies,
dependentRequired, dependentSchemas, unevaluatedProperties, prefixItems, contains, pattern,
format, uniqueItems, propertyNames, maxItems.

If a schema uses an unsupported keyword, validation raises instead of passing silently —
a validator that ignores what it does not understand is how false compliance happens.
"""

from __future__ import annotations

import json
import os
from typing import Any

SUPPORTED = {
    "$schema", "$id", "title", "description", "type", "enum", "const", "properties",
    "required", "additionalProperties", "items", "minItems", "minProperties",
    "allOf", "anyOf", "oneOf", "not", "if", "then", "else", "$ref", "$defs",
    "minimum", "maximum", "default", "minLength", "maxLength",
}
UNSUPPORTED = {
    "patternProperties", "dependencies", "dependentRequired", "dependentSchemas",
    "unevaluatedProperties", "prefixItems", "contains", "pattern", "format",
    "uniqueItems", "propertyNames", "maxItems",
}


class SchemaError(Exception):
    """The schema itself is unusable, or uses an unsupported keyword."""


class Validator:
    def __init__(self, schema: dict, root_dir: str | None = None):
        self.schema = schema
        self.root_dir = root_dir or os.getcwd()
        self._store: dict[str, dict] = {}
        self._check_keywords(schema)

    # ------------------------------------------------------------------ setup
    def _check_keywords(self, node: Any) -> None:
        """Walk only schema positions, so keyword names inside `required` lists are not
        mistaken for keywords."""
        if not isinstance(node, dict):
            return
        for key in node:
            if key in UNSUPPORTED:
                raise SchemaError(f"unsupported keyword '{key}' — refusing to validate silently")
            if key.startswith("$") or key in SUPPORTED:
                continue
            raise SchemaError(f"unknown keyword '{key}' — add support or remove it")
        # recurse only where a subschema can appear
        for key in ("properties", "$defs"):
            for sub in (node.get(key) or {}).values():
                self._check_keywords(sub)
        for key in ("items", "additionalProperties", "not", "if", "then", "else"):
            sub = node.get(key)
            if isinstance(sub, dict):
                self._check_keywords(sub)
        for key in ("allOf", "anyOf", "oneOf"):
            for sub in node.get(key) or []:
                self._check_keywords(sub)

    def _load(self, filename: str) -> dict:
        if filename not in self._store:
            path = os.path.join(self.root_dir, filename)
            if not os.path.exists(path):
                raise SchemaError(f"cannot resolve $ref to missing file {filename}")
            with open(path, encoding="utf-8") as fh:
                self._store[filename] = json.load(fh)
        return self._store[filename]

    def _deref(self, node: dict, defs: dict) -> tuple[dict, dict]:
        """Resolve one level of $ref. Returns (schema, defs_in_scope)."""
        while "$ref" in node:
            ref = node["$ref"]
            if ref.startswith("#/$defs/"):
                target, defs = defs.get(ref[len("#/$defs/"):], {}), defs
            elif "#" in ref:
                fname, frag = ref.split("#", 1)
                doc = self._load(fname)
                defs = doc.get("$defs", {})
                key = frag.rsplit("/", 1)[-1]
                target = defs.get(key, {})
            else:
                doc = self._load(ref)
                defs, target = doc.get("$defs", {}), doc
            node = target
        return node, defs

    # -------------------------------------------------------------- validation
    def iter_errors(self, instance: Any, schema: dict | None = None) -> list[str]:
        errors: list[str] = []

        def walk(data: Any, node: dict, path: str, defs: dict) -> None:
            node, defs = self._deref(node, defs)
            if not isinstance(node, dict):
                return

            # combinators
            for sub in node.get("allOf", []):
                walk(data, sub, path, defs)

            if "anyOf" in node:
                ok = False
                for sub in node["anyOf"]:
                    probe: list[str] = []
                    saved, errors[:] = list(errors), []
                    walk(data, sub, path, defs)
                    probe, errors[:] = list(errors), saved
                    if not probe:
                        ok = True
                        break
                if not ok:
                    errors.append(f"{path}: matches none of anyOf")

            if "oneOf" in node:
                matched = 0
                for sub in node["oneOf"]:
                    saved, errors[:] = list(errors), []
                    walk(data, sub, path, defs)
                    if not errors:
                        matched += 1
                    errors[:] = saved
                if matched != 1:
                    errors.append(f"{path}: matches {matched} of oneOf (expected exactly 1)")

            if "not" in node:
                saved, errors[:] = list(errors), []
                walk(data, node["not"], path, defs)
                failed = bool(errors)
                errors[:] = saved
                if not failed:
                    errors.append(f"{path}: matches 'not' schema")

            if "if" in node:
                saved, errors[:] = list(errors), []
                walk(data, node["if"], path, defs)
                condition_met = not errors
                errors[:] = saved
                branch = node.get("then") if condition_met else node.get("else")
                if branch:
                    walk(data, branch, path, defs)

            # type
            declared = node.get("type")
            if declared:
                types = declared if isinstance(declared, list) else [declared]
                if not _type_ok(data, types):
                    errors.append(f"{path}: expected {declared}, got {_kind(data)}")
                    return

            # value constraints
            if "const" in node and data != node["const"]:
                errors.append(f"{path}: expected const {node['const']!r}")
            if "enum" in node and data not in node["enum"]:
                errors.append(f"{path}: {data!r} not in enum")

            # objects
            if isinstance(data, dict):
                props = node.get("properties", {})
                for key in node.get("required", []):
                    if key not in data:
                        errors.append(f"{path}: missing required '{key}'")
                if "minProperties" in node and len(data) < node["minProperties"]:
                    errors.append(f"{path}: needs >= {node['minProperties']} properties")
                for key, value in data.items():
                    child = f"{path}.{key}"
                    if key in props:
                        walk(value, props[key], child, defs)
                    else:
                        ap = node.get("additionalProperties")
                        if ap is False:
                            errors.append(f"{path}: additional property '{key}' is not allowed")
                        elif isinstance(ap, dict):
                            walk(value, ap, child, defs)

            # arrays
            if isinstance(data, list):
                if "minItems" in node and len(data) < node["minItems"]:
                    errors.append(f"{path}: needs >= {node['minItems']} items")
                if "items" in node:
                    for i, item in enumerate(data):
                        walk(item, node["items"], f"{path}[{i}]", defs)

            # strings
            if isinstance(data, str):
                if "minLength" in node and len(data) < node["minLength"]:
                    errors.append(f"{path}: shorter than minLength {node['minLength']}")
                if "maxLength" in node and len(data) > node["maxLength"]:
                    errors.append(f"{path}: longer than maxLength {node['maxLength']}")

            # numbers
            if isinstance(data, (int, float)) and not isinstance(data, bool):
                if "minimum" in node and data < node["minimum"]:
                    errors.append(f"{path}: below minimum {node['minimum']}")
                if "maximum" in node and data > node["maximum"]:
                    errors.append(f"{path}: above maximum {node['maximum']}")

        start_defs = self.schema.get("$defs", {})
        walk(instance, schema if schema is not None else self.schema, "$", start_defs)
        return errors

    def is_valid(self, instance: Any) -> bool:
        return not self.iter_errors(instance)


def _kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _type_ok(value: Any, types: list[str]) -> bool:
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


def load_validator(schema_dir: str, filename: str) -> Validator:
    with open(os.path.join(schema_dir, filename), encoding="utf-8") as fh:
        return Validator(json.load(fh), root_dir=schema_dir)
