#!/usr/bin/env python3
"""极简 JSON Schema 校验器（纯标准库实现）。

覆盖范围：本仓库 `schemas/` 实际使用的关键字子集，外加若干常用关键字。

设计原则
--------
**未实现的关键字会被记录为 warning，而不是静默忽略。**
静默忽略会让「校验通过」变成假象——一个 schema 里写了 `pattern` 却
没人检查，使用者会以为自己受保护。这正是本项目要避免的那类自欺。

未实现：`$ref`、`not`、`if/then/else`、`dependentSchemas`、`format`、
`unevaluatedProperties` 等。用到时会明确报警，不会假装通过。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

#: 本校验器认识的关键字。列表之外的一律记 warning。
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
    # bool 是 int 的子类，必须显式排除，否则 True 会被当成合法整数
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def type_name(value):
    """返回实例的 JSON 类型名。"""
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
    """校验实例。返回 `(errors, warnings)`，均为字符串列表。

    errors 为空表示通过；warnings 非空表示有约束**未被检查**，
    调用方应据此判断「通过」的可信度。
    """
    ctx = _Context()
    _validate(instance, schema, path, ctx)
    return ctx.errors, ctx.warnings


def _validate(instance, schema, path, ctx):
    if not isinstance(schema, dict):
        ctx.warn(path, f"schema 不是对象（{type_name(schema)}），已跳过")
        return

    for keyword in schema:
        if keyword not in KNOWN_KEYWORDS:
            ctx.warn(
                path,
                f"schema 使用了未实现的关键字 '{keyword}'，该约束未被检查",
            )

    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        unknown = [o for o in options if o not in _TYPE_CHECKS]
        if unknown:
            ctx.warn(path, f"未知的 type 取值 {unknown}，已跳过类型检查")
        elif not any(_TYPE_CHECKS[o](instance) for o in options):
            wanted = "/".join(str(o) for o in options)
            ctx.error(
                path,
                f"类型应为 {wanted}，实际为 {type_name(instance)}",
            )
            # 类型不符时，后续针对该类型的约束没有意义，直接返回
            return

    if "const" in schema and instance != schema["const"]:
        ctx.error(path, f"应等于常量 {schema['const']!r}，实际为 {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        ctx.error(path, f"取值必须属于 [{allowed}]，实际为 {instance!r}")

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
        ctx.error(path, f"长度应 ≥ {schema['minLength']}，实际为 {len(instance)}")
    if "maxLength" in schema and len(instance) > schema["maxLength"]:
        ctx.error(path, f"长度应 ≤ {schema['maxLength']}，实际为 {len(instance)}")
    pattern = schema.get("pattern")
    if pattern is not None:
        try:
            if re.search(pattern, instance) is None:
                ctx.error(path, f"不匹配 pattern {pattern!r}")
        except re.error as exc:
            ctx.warn(path, f"schema 中的 pattern 无法编译（{exc}），未检查")


def _validate_number(instance, schema, path, ctx):
    if "minimum" in schema and instance < schema["minimum"]:
        ctx.error(path, f"应 ≥ {schema['minimum']}，实际为 {instance}")
    if "maximum" in schema and instance > schema["maximum"]:
        ctx.error(path, f"应 ≤ {schema['maximum']}，实际为 {instance}")
    if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
        ctx.error(path, f"应 > {schema['exclusiveMinimum']}，实际为 {instance}")
    if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
        ctx.error(path, f"应 < {schema['exclusiveMaximum']}，实际为 {instance}")
    if "multipleOf" in schema:
        divisor = schema["multipleOf"]
        if divisor and (instance % divisor) != 0:
            ctx.error(path, f"应为 {divisor} 的倍数，实际为 {instance}")


def _validate_array(instance, schema, path, ctx):
    if "minItems" in schema and len(instance) < schema["minItems"]:
        ctx.error(path, f"元素数应 ≥ {schema['minItems']}，实际为 {len(instance)}")
    if "maxItems" in schema and len(instance) > schema["maxItems"]:
        ctx.error(path, f"元素数应 ≤ {schema['maxItems']}，实际为 {len(instance)}")
    if schema.get("uniqueItems") and len(instance) != len(
        {json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) for item in instance}
    ):
        ctx.error(path, "元素应互不重复")
    item_schema = schema.get("items")
    if item_schema is not None:
        for index, item in enumerate(instance):
            _validate(item, item_schema, f"{path}[{index}]", ctx)


def _validate_object(instance, schema, path, ctx):
    for key in schema.get("required", []):
        if key not in instance:
            ctx.error(path, f"缺少必填字段 '{key}'")

    properties = schema.get("properties", {})
    for key, subschema in properties.items():
        if key in instance:
            _validate(instance[key], subschema, f"{path}.{key}", ctx)

    if schema.get("additionalProperties") is False:
        extra = [k for k in instance if k not in properties]
        if extra:
            shown = ", ".join(repr(k) for k in sorted(extra)[:5])
            more = "" if len(extra) <= 5 else f" 等 {len(extra)} 个"
            ctx.error(path, f"出现未声明的字段：{shown}{more}")
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
    """在隔离的上下文里试跑一个子 schema，返回 (是否通过, 错误列表, 警告列表)。"""
    sub = _Context()
    _validate(instance, subschema, path, sub)
    return (not sub.errors), sub.errors, sub.warnings


def _validate_combinators(instance, schema, path, ctx):
    if "allOf" in schema:
        for index, subschema in enumerate(schema["allOf"]):
            _validate(instance, subschema, path, ctx)

    for keyword, rule in (("anyOf", "至少"), ("oneOf", "恰好")):
        options = schema.get(keyword)
        if not options:
            continue
        results = [_subschema_ok(instance, option, path) for option in options]
        passed = sum(1 for ok, _, _ in results if ok)
        if keyword == "anyOf":
            if passed == 0:
                detail = "; ".join(results[0][1][:2]) if results else ""
                ctx.error(path, f"anyOf：没有任何分支通过。首分支错误：{detail}")
        else:  # oneOf
            if passed != 1:
                ctx.error(
                    path,
                    f"oneOf：应{rule}有 1 个分支通过，实际通过 {passed} 个",
                )
        # 组合器内部用到的关键字也要暴露给调用方，避免"通过"掩盖未检查的约束
        for _, _, warns in results:
            for warning in warns:
                if warning not in ctx.warnings:
                    ctx.warnings.append(warning)


# ---------------------------------------------------------------------------
# 文件级便捷接口
# ---------------------------------------------------------------------------

def load_schema(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_instance(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_file(instance_path, schema_path):
    """校验一个 JSON 文件是否符合给定 schema。返回 (errors, warnings)。"""
    return validate(load_instance(instance_path), load_schema(schema_path))


#: 文件名 → schema 文件的约定映射，供 CLI 自动选 schema。
DEFAULT_SCHEMA_MAP = {
    "project.json": "project.schema.json",
    "project_state.json": "project.schema.json",
    "evidence.json": "evidence.schema.json",
    "decision_record.json": "decision_record.schema.json",
    "experiment.json": "experiment.schema.json",
    "kpi_tree.json": "kpi_tree.schema.json",
}


def guess_schema(instance_path, schema_dir):
    """按文件名猜测对应的 schema。猜不到返回 None。"""
    name = Path(instance_path).name
    candidate = DEFAULT_SCHEMA_MAP.get(name)
    if candidate is None:
        return None
    resolved = Path(schema_dir) / candidate
    return resolved if resolved.exists() else None
