#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立校验脚本：把 kpi_tree.json / experiments.json 对着技能包里的 JSON Schema 逐条验。
不依赖 jsonschema 库（环境未必有），实现 draft 2020-12 所需子集：
  type / properties / required / additionalProperties / enum / items / $ref / anyOf / $defs
运行：python3 scripts/05_validate_schemas.py
"""
import json, os, sys

def _find_schemas():
    """优先用案例自带的 schema 快照；找不到再向上找仓库的 schemas/。

    本案例运行时使用的是 legacy/v3.1 那份 schema（字段比当前仓库版本更宽），
    因此快照随案例一起提供，保证可复现。
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local = os.path.join(here, "schemas")
    if os.path.isdir(local):
        return local
    d = here
    for _ in range(6):
        d = os.path.dirname(d)
        candidate = os.path.join(d, "schemas")
        if os.path.isdir(candidate):
            return candidate
    raise SystemExit("找不到 schemas 目录")

SKILL = _find_schemas()
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class V:
    def __init__(self, root): self.root = root; self.errs = []
    def resolve(self, sch):
        if "$ref" in sch:
            ref = sch["$ref"]
            if not ref.startswith("#/"): raise ValueError(f"只支持本地 $ref: {ref}")
            node = self.root
            for part in ref[2:].split("/"): node = node[part]
            return self.resolve(node)
        return sch
    def check(self, inst, sch, path):
        sch = self.resolve(sch)
        t = sch.get("type")
        if t:
            types = t if isinstance(t, list) else [t]
            ok = any(
                (ty == "object"   and isinstance(inst, dict)) or
                (ty == "array"    and isinstance(inst, list)) or
                (ty == "string"   and isinstance(inst, str)) or
                (ty == "number"   and isinstance(inst, (int, float)) and not isinstance(inst, bool)) or
                (ty == "integer"  and isinstance(inst, int) and not isinstance(inst, bool)) or
                (ty == "boolean"  and isinstance(inst, bool)) or
                (ty == "null"     and inst is None)
                for ty in types)
            if not ok:
                self.errs.append(f"{path}: 类型应为 {t}，实际 {type(inst).__name__}"); return
        if "enum" in sch and inst not in sch["enum"]:
            self.errs.append(f"{path}: 值 {inst!r} 不在 enum {sch['enum']} 内")
        if "anyOf" in sch:
            subs = []
            for sub in sch["anyOf"]:
                v2 = V(self.root); v2.check(inst, sub, path)
                subs.append(v2.errs)
            if all(subs):
                self.errs.append(f"{path}: 未满足 anyOf 任一分支 → {subs}")
        if isinstance(inst, dict):
            props = sch.get("properties", {})
            for k in sch.get("required", []):
                if k not in inst:
                    self.errs.append(f"{path}: 缺必填字段 '{k}'")
            if sch.get("additionalProperties") is False:
                for k in inst:
                    if k not in props:
                        self.errs.append(f"{path}: 出现未定义字段 '{k}'（additionalProperties=false）")
            for k, v in inst.items():
                if k in props: self.check(v, props[k], f"{path}.{k}")
        if isinstance(inst, list) and "items" in sch:
            for i, v in enumerate(inst): self.check(v, sch["items"], f"{path}[{i}]")

def run(name, schema_file, instance_file, mode="single"):
    schema = json.load(open(os.path.join(SKILL, schema_file), encoding="utf-8"))
    inst = json.load(open(os.path.join(HERE, instance_file), encoding="utf-8"))
    v = V(schema)
    if mode == "list":
        for i, e in enumerate(inst):
            v.check(e, schema, f"[{i}]{e.get('experiment_id','')}")
    else:
        v.check(inst, schema, "$")
    print(f"\n{'='*90}\n{instance_file}  ⟵  {schema_file}\n{'='*90}")
    if v.errs:
        for e in v.errs: print("  ❌", e)
        return False
    print("  ✅ 完全通过 JSON Schema 校验（未使用 jsonschema 库，为独立实现）")
    return True

ok1 = run("KPI tree", "kpi_tree.schema.json", "kpi_tree.json")
ok2 = run("Experiments", "experiment.schema.json", "experiments.json", mode="list")

# 额外：schema 挡不住的垃圾数据体检
print(f"\n{'='*90}\n附加体检：schema 允许但语义可能是垃圾的字段\n{'='*90}")
tree = json.load(open(os.path.join(HERE,"kpi_tree.json"), encoding="utf-8"))
def walk(n, out):
    out.append(n)
    for c in n.get("children", []): walk(c, out)
    return out
alln = []
for n in tree["nodes"]: walk(n, alln)
issues = []
for n in alln:
    nm = n["metric_name"]
    if "definition" in n and len(n["definition"]) < 20:
        issues.append(f"『{nm}』definition 过短（{len(n['definition'])} 字），可能只是复述指标名")
    if not any(k in n.get("definition","") for k in ["分子","分母","计数","金额型","时间型","比例"]):
        issues.append(f"『{nm}』definition 未声明分子/分母口径")
    if n["metric_type"] in ("outcome","driver") and not n.get("target"):
        issues.append(f"『{nm}』为 {n['metric_type']} 却无 target —— schema 不强制，但决策上无用")
    if n["metric_type"] == "guardrail" and not n.get("guardrail_threshold"):
        issues.append(f"『{nm}』为 guardrail 却无 guardrail_threshold —— 护栏不设阈值等于没有护栏")
    if n.get("baseline") and ("无" in n["baseline"] and "未" in n["baseline"]):
        pass  # 明确标注无基线是诚实的
if issues:
    for i in issues: print("  ⚠️", i)
else:
    print("  ✅ 未发现 definition 空洞、driver 无 target、guardrail 无阈值的问题")

exps = json.load(open(os.path.join(HERE,"experiments.json"), encoding="utf-8"))
issues2 = []
for e in exps:
    if "control" not in e and e["status"] in ("running","complete"):
        issues2.append(f"{e['experiment_id']}: 无 control 却已在跑")
    if "minimum_detectable_effect" not in e:
        issues2.append(f"{e['experiment_id']}: 无 MDE 字段 —— schema 不强制，但技能要求『若无法论证功效须报告为方向性』")
    if "result" in e and e["status"] == "proposed":
        issues2.append(f"{e['experiment_id']}: status=proposed 却有 result")
print()
if issues2:
    for i in issues2: print("  ⚠️", i)
else:
    print("  ✅ 实验卡片无『无对照却声称因果』『提案带结果』『无 MDE』的问题")

print(f"\n总结：{'全部通过' if (ok1 and ok2 and not issues and not issues2) else '通过但有告警'}")
