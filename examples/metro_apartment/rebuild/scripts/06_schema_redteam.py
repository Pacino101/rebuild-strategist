#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能评估 · 步骤 3：对抗测试 —— schema 到底挡不挡得住垃圾数据？

方法：构造 N 张"语义上是垃圾、但结构上完全合法"的 KPI 节点与实验卡片，
      用 05_validate_schemas.py 里的校验器跑一遍。
      凡是 PASS 的，就是这个 schema 挡不住的垃圾。
运行：python3 scripts/06_schema_redteam.py
"""
import json, os, sys, importlib.util

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

spec = importlib.util.spec_from_file_location("v", os.path.join(HERE, "scripts", "05_validate_schemas.py"))
# 直接内联校验器，避免执行 05 的副作用
class V:
    def __init__(self, root): self.root = root; self.errs = []
    def resolve(self, sch):
        if "$ref" in sch:
            node = self.root
            for part in sch["$ref"][2:].split("/"): node = node[part]
            return self.resolve(node)
        return sch
    def check(self, inst, sch, path):
        sch = self.resolve(sch); t = sch.get("type")
        if t:
            types = t if isinstance(t, list) else [t]
            ok = any((ty=="object" and isinstance(inst,dict)) or (ty=="array" and isinstance(inst,list))
                     or (ty=="string" and isinstance(inst,str)) or (ty=="number" and isinstance(inst,(int,float)) and not isinstance(inst,bool))
                     or (ty=="integer" and isinstance(inst,int) and not isinstance(inst,bool))
                     or (ty=="boolean" and isinstance(inst,bool)) or (ty=="null" and inst is None) for ty in types)
            if not ok: self.errs.append(f"{path}: 类型应为 {t}"); return
        if "enum" in sch and inst not in sch["enum"]: self.errs.append(f"{path}: 不在 enum 内")
        if "anyOf" in sch:
            subs=[]
            for sub in sch["anyOf"]:
                v2=V(self.root); v2.check(inst,sub,path); subs.append(v2.errs)
            if all(subs): self.errs.append(f"{path}: 未满足 anyOf")
        if isinstance(inst, dict):
            props = sch.get("properties", {})
            for k in sch.get("required", []):
                if k not in inst: self.errs.append(f"{path}: 缺必填 '{k}'")
            if sch.get("additionalProperties") is False:
                for k in inst:
                    if k not in props: self.errs.append(f"{path}: 未定义字段 '{k}'")
            for k,v in inst.items():
                if k in props: self.check(v, props[k], f"{path}.{k}")
        if isinstance(inst, list) and "items" in sch:
            for i,v in enumerate(inst): self.check(v, sch["items"], f"{path}[{i}]")

KPI_SCHEMA = json.load(open(os.path.join(SKILL, "kpi_tree.schema.json"), encoding="utf-8"))
EXP_SCHEMA = json.load(open(os.path.join(SKILL, "experiment.schema.json"), encoding="utf-8"))

def kpi_ok(node):
    v = V(KPI_SCHEMA); v.check(node, {"$ref":"#/$defs/node"}, "$"); return v.errs
def exp_ok(e):
    v = V(EXP_SCHEMA); v.check(e, EXP_SCHEMA, "$"); return v.errs

print("="*100)
print("对抗测试 A｜KPI 节点：10 种『结构合法、语义垃圾』的数据")
print("="*100)

GARBAGE_KPI = [
 ("A1 定义只是复述指标名",
  dict(metric_name="出租率", metric_type="outcome", definition="出租率",
       unit="%", period="月度", source_of_truth="台账", owner="运营")),
 ("A2 分母未定义（'提升转化率'）",
  dict(metric_name="转化率", metric_type="driver", definition="把转化率提上去，越高越好",
       unit="%", period="月度", source_of_truth="后台", owner="运营")),
 ("A3 outcome 无 target、无 baseline",
  dict(metric_name="营收", metric_type="outcome", definition="分子=当月租金收入；分母=1",
       unit="元", period="月度", source_of_truth="财务", owner="财务")),
 ("A4 guardrail 不设阈值（等于没有护栏）",
  dict(metric_name="客诉率", metric_type="guardrail", definition="分子=客诉件数；分母=在租间数",
       unit="件/间", period="月度", source_of_truth="工单", owner="客服")),
 ("A5 数据来源写『系统』这种无法执行的占位符",
  dict(metric_name="CAC", metric_type="diagnostic", definition="分子=营销支出；分母=签约间数",
       unit="元", period="月度", source_of_truth="系统", owner="市场")),
 ("A6 owner 写虚职（'项目组'）",
  dict(metric_name="回本进度", metric_type="outcome", definition="分子=累计分红；分母=300万",
       unit="%", period="月度", source_of_truth="台账", owner="项目组")),
 ("A7 period 写『随时』",
  dict(metric_name="现金流", metric_type="outcome", definition="分子=收入；分母=成本",
       unit="元", period="随时", source_of_truth="财务", owner="财务")),
 ("A8 同一指标在父子里重复出现（循环定义）",
  dict(metric_name="出租率", metric_type="outcome", definition="分子=在租间数；分母=75",
       unit="%", period="月度", source_of_truth="台账", owner="运营",
       children=[dict(metric_name="出租率", metric_type="driver",
                      definition="分子=在租间数；分母=75",
                      unit="%", period="月度", source_of_truth="台账", owner="运营")])),
 ("A9 target 写成口号（'大幅提升'）",
  dict(metric_name="出租率", metric_type="driver", definition="分子=在租间数；分母=75",
       unit="%", period="月度", source_of_truth="台账", owner="运营", target="大幅提升")),
 ("A10 把 activity 伪装成 outcome（曝光量当营收结果）",
  dict(metric_name="曝光量", metric_type="outcome", definition="分子=曝光次数；分母=1",
       unit="次", period="周度", source_of_truth="投放后台", owner="市场",
       target="100万次")),
]

passed = []
for label, node in GARBAGE_KPI:
    errs = kpi_ok(node)
    if errs:
        print(f"  ✅ 拦下 | {label}\n           → {errs[0]}")
    else:
        passed.append(label)
        print(f"  ❌ 放过 | {label}")

print(f"\n  结果：{len(passed)}/{len(GARBAGE_KPI)} 条垃圾数据通过 schema 校验")
for p in passed: print(f"    · {p}")

print()
print("="*100)
print("对抗测试 B｜实验卡片：8 种『结构合法、语义垃圾』的数据")
print("="*100)

GARBAGE_EXP = [
 ("B1 decision_rule 写『到时候再看』",
  dict(experiment_id="X1", hypothesis="提价能增收入", audience="全部客群", variant="提价10%",
       primary_metric="收入", guardrails=["不能掉出租率"], decision_rule="到时候再看", status="proposed")),
 ("B2 无 control 但声称因果（status=complete）",
  dict(experiment_id="X2", hypothesis="新渠道有效", audience="全部线索", variant="投小红书",
       primary_metric="线索数", guardrails=["成本"], decision_rule="通过则加投；失败则停；不确定则延长",
       status="complete", result="线索增加了30%，证明新渠道有效")),
 ("B3 primary_metric 是 activity（曝光量）",
  dict(experiment_id="X3", hypothesis="曝光越多签约越多", audience="全部", variant="加倍曝光",
       primary_metric="曝光量", guardrails=["预算"], decision_rule="通过/失败/不确定三分支齐全",
       status="proposed")),
 ("B4 MDE 写成『看情况』",
  dict(experiment_id="X4", hypothesis="A优于B", audience="全部", variant="A", primary_metric="CVR",
       guardrails=["成本"], decision_rule="通过/失败/不确定", status="proposed",
       minimum_detectable_effect="看情况，样本够了自然能看出来")),
 ("B5 样本逻辑写『跑一个月』（无功效依据）",
  dict(experiment_id="X5", hypothesis="A优于B", audience="全部", variant="A", primary_metric="CVR",
       guardrails=["成本"], decision_rule="通过/失败/不确定", status="proposed",
       sample_logic="先跑一个月看看", duration="一个月")),
 ("B6 无 control 字段但 hypothesis 是因果句",
  dict(experiment_id="X6", hypothesis="因为做了地推所以线索变多了", audience="全部", variant="地推",
       primary_metric="线索数", guardrails=["成本"], decision_rule="通过/失败/不确定", status="running")),
 ("B7 status=complete 但无 result",
  dict(experiment_id="X7", hypothesis="A优于B", audience="全部", variant="A", primary_metric="CVR",
       guardrails=["成本"], decision_rule="通过/失败/不确定", status="complete")),
 ("B8 guardrails 为空数组（无护栏的实验）",
  dict(experiment_id="X8", hypothesis="A优于B", audience="全部", variant="A", primary_metric="CVR",
       guardrails=[], decision_rule="通过/失败/不确定", status="approved")),
]

passed2 = []
for label, e in GARBAGE_EXP:
    errs = exp_ok(e)
    if errs:
        print(f"  ✅ 拦下 | {label}\n           → {errs[0]}")
    else:
        passed2.append(label)
        print(f"  ❌ 放过 | {label}")

print(f"\n  结果：{len(passed2)}/{len(GARBAGE_EXP)} 条垃圾数据通过 schema 校验")
for p in passed2: print(f"    · {p}")

print()
print("="*100)
print("汇总")
print("="*100)
print(f"  KPI schema   : 放过 {len(passed)}/{len(GARBAGE_KPI)} 条语义垃圾")
print(f"  Experiment schema: 放过 {len(passed2)}/{len(GARBAGE_EXP)} 条语义垃圾")
print("""
  结论：两个 schema 都是【结构校验器】而非【质量校验器】。
        它们能保证字段齐全、枚举合法、无拼写错误；
        但完全无法阻止：
          · 定义复述指标名、分母缺失
          · guardrail 不设阈值
          · activity 冒充 outcome
          · 无对照却声称因果
          · MDE 与样本量写成空话
        技能正文（§6 / MARKETING_OS / OPERATING_RULES）反复强调了这些要求，
        但 schema 没有把它们变成【机器可判的约束】——
        于是"遵守技能"完全依赖写作者的自觉，而这正是技能想要避免的。
""")
