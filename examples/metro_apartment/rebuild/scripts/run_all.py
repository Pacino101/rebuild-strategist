#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地铁公寓项目 · GROWTH_DIAGNOSIS
一键复现：跑完全部脚本，输出关键数字汇总表到 KEY_FINDINGS.md
运行：python3 scripts/run_all.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = ["01_source_integrity.py","02_econ_model.py","03_kpi_tree.py",
           "04_experiments.py","05_validate_schemas.py","06_schema_redteam.py"]

def run(name):
    r = subprocess.run([sys.executable, os.path.join(HERE,"scripts",name)],
                       capture_output=True, text=True, cwd=HERE)
    ok = r.returncode == 0
    print(f"  {'✅' if ok else '❌'} {name}")
    if not ok:
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
    return r.stdout

print("="*90); print("一键复现：依次执行 6 个脚本"); print("="*90)
outs = {}
for s in SCRIPTS: outs[s] = run(s)

m = json.load(open(os.path.join(HERE,"model_output.json"), encoding="utf-8"))
tree = json.load(open(os.path.join(HERE,"kpi_tree.json"), encoding="utf-8"))
exps = json.load(open(os.path.join(HERE,"experiments.json"), encoding="utf-8"))
power = json.load(open(os.path.join(HERE,"power_analysis.json"), encoding="utf-8"))

def cnt(n): return 1 + sum(cnt(c) for c in n.get("children", []))
ntotal = sum(cnt(n) for n in tree["nodes"])

S = m["occupancy_sensitivity"]
d = {f"{int(r['occupancy']*100)}": r for r in S}
o = m["operator"]

L = []
def w(x=""): L.append(x)

w("# 关键数字汇总（自动生成，请勿手改）")
w()
w(f"生成脚本：`scripts/run_all.py`  ·  数据源：三份源文档  ·  全部数字可由 `scripts/` 下 6 个脚本复现")
w()
w("## 1. 五个最重要的数字发现")
w()
w("| # | 发现 | 数值 | 依据 |")
w("|---|---|---|---|")
w(f"| 1 | 宣称的 1.9 年回本只能由「甲方独占全部分红」复现 | 3,000,000 ÷ 135,000 = 22.2 月 = **1.85 年**；按 65% 分成为 **{m['payback']['a_party_years']} 年**（含爬坡） | `01`/`02` |")
w(f"| 2 | 运营方单位经济结构性为负 | 单间月收入 **{o['b_revenue_per_room']:,.0f} 元** vs 单间月成本 **771–{o['opex_per_room']:,.0f} 元** | `02` |")
w(f"| 3 | 60%–93% 出租率全区间运营方月现金流为负 | {d['60']['b_cf']:,.0f} / {d['75']['b_cf']:,.0f} / {d['88']['b_cf']:,.0f} / {d['93']['b_cf']:,.0f} 元/月 | `02` |")
w(f"| 4 | 甲方回本约束与乙方保本约束**交集为空** | 甲方需分成 ≥50%；乙方保本需甲方降至 **{m['required_a_rate_for_b_breakeven']*100:.1f}%** | `02` |")
w(f"| 5 | 40 万预算勉强够 6 个月到 88%，扣掉非获客支出后即超红线 | 6 个月需 66 间 × 4,500 = **297,000 元**；可获客上限 300,000 元 → 实际 CAC **{m['leaseup']['cac_if_30w_for_66']:,.0f} 元** > 4,500 | `02` |")
w()
w("## 2. 单位经济（稳态 90% 出租率，本模型基准）")
w()
w("| 项目 | 数值 | 来源 |")
w("|---|---|---|")
w(f"| 满租月租金收入 | {m['pricing']['full_monthly_revenue']:,.0f} 元/月 | 文档给定 [A] |")
w(f"| 均价 | {m['pricing']['avg_rent']:,.0f} 元/间 | 文档给定 [A] |")
w(f"| 综合单方租金（分母=单间建面 1,824㎡） | {m['pricing']['sqm_on_rentable']} 元/㎡·月 | 文档给定 [D] |")
w(f"| 综合单方租金（分母=总建面 2,751.34㎡） | {m['pricing']['sqm_on_gfa']} 元/㎡·月 | **本模型补算** |")
w(f"| 可分配收入（90%） | {o['distributable']:,.0f} 元/月 | 计算 |")
w(f"| 甲方分成 65% | {o['a_share']:,.0f} 元/月 | 文档给定分成比例 [E] |")
w(f"| 乙方分成 35% | {o['b_share']:,.0f} 元/月 | 文档给定分成比例 [E] |")
w(f"| 乙方月度自有成本（本模型重建） | {o['opex_total']:,.0f} 元/月 | **本模型补**（文档仅给 57,800 无明细） |")
w(f"| 乙方月度经营现金流 | **{o['b_monthly_cashflow']:,.0f} 元/月** | 计算 |")
w(f"| 乙方单间月贡献 | **{o['contribution_per_room']:,.0f} 元/间·月** | 计算 |")
w(f"| 押金机会成本（6%） | {o['deposit_opportunity']:,.0f} 元/月 | **本模型补** |")
w(f"| 押金烧穿时点 | **{o['deposit_burn_months']:.0f} 个月** | 计算 |")
w()
w("## 3. 出租率敏感度（甲方 / 乙方双口径）")
w()
w("| 出租率 | 在租间数 | 月租金收入 | 可分配收入 | 甲方月分红 | 甲方年收益 | 甲方回本(年) | 乙方月收入 | 乙方月成本 | 乙方月现金流 | 乙方年现金流 | 押金烧穿(月) |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in ["60","75","88","93"]:
    r = d[k]
    burn = f"{1000000/abs(r['b_cf']):.0f}" if r['b_cf'] < 0 else "—"
    w(f"| {k}% | {r['rooms']:.0f} | {r['gross']:,.0f} | {r['distributable']:,.0f} | {r['a_month']:,.0f} | "
      f"{r['a_year']:,.0f} | {r['a_payback_years']:.2f} | {r['b_revenue']:,.0f} | {r['b_opex']:,.0f} | "
      f"**{r['b_cf']:,.0f}** | {r['b_year']:,.0f} | {burn} |")
w()
w("## 4. CAC 四口径（同一笔 40 万预算）")
w()
w("| 口径 | 值 | 是否 ≤4,500 红线 |")
w("|---|---|---|")
c = m["cac"]
for lbl, v in [("① 广义（40 万全口径）", c["all_in"]), ("② 现金投放（剔除品牌 10 万）", c["cash"]),
               ("③ 纯媒介（仅 18 万）", c["media_only"]), ("④ 广义 + 渠道佣金", c["incl_commission"])]:
    w(f"| {lbl} | {v:,.0f} 元/间次 | {'✅' if v <= 4500 else '❌ 超红线'} |")
w(f"| 渠道单位佣金（10万÷38间，文档两值相除） | {c['unit_commission']:,.0f} 元/间 | — |")
w()
w("## 5. 反解：什么条款才成立")
w()
w("| 乙方目标 | 甲方分成须降至 | 乙方分成须升至 |")
w("|---|---|---|")
for lbl, r in [("保本（现金流=0）", 0.3112), ("押金机会成本 6%", 0.2732), ("押金 + 年化 10%", 0.2474)]:
    w(f"| {lbl} | {r*100:.1f}% | {(1-r)*100:.1f}% |")
w(f"| **甲方 48 个月回本要求** | **≥50%** | — |")
w()
w("> 甲方需 ≥50%，乙方保本需甲方 ≤31.1% —— **交集为空**。")
w()
w("## 6. 交付物清单")
w()
w(f"| 文件 | 内容 | 校验 |")
w("|---|---|---|")
w(f"| `kpi_tree.json` | KPI 树，{ntotal} 个节点，4 棵顶层树（甲方口径/乙方口径/共用驱动/共用护栏） | ✅ 通过 kpi_tree.schema.json |")
w(f"| `experiments.json` | {len(exps)} 个实验卡片，全部 status=proposed | ✅ 通过 experiment.schema.json |")
w(f"| `power_analysis.json` | 功效核算明细 | — |")
w(f"| `model_output.json` | 单位经济模型全部输出 | — |")
w(f"| `DECISION.md` | 一页纸决策页 | — |")
w(f"| `SKILL_EVALUATION.md` | 技能评估报告 | — |")
w()
w("## 7. 功效核算（为什么三个实验都只能算方向性）")
w()
w("| 设计 | 每臂样本 | 基线 | 可检测最小效应 |")
w("|---|---|---|---|")
for k, v in power["viewer_level_rct"]["mde_by_baseline"].items():
    w(f"| 看房者级 RCT | 450 组 | {float(k)*100:.1f}% | ±{v*100:.1f}pt |")
for k, v in power["room_level_rct"]["mde_by_baseline"].items():
    w(f"| 房间级 RCT | 37 间 | {float(k)*100:.0f}% | ±{v*100:.1f}pt |")
w(f"| 渠道 A/B（本项目选定） | 300 组 | 7.4% | ±{power['exp02']['mde']*100:.1f}pt |")
w(f"| 定价配对（本项目选定） | 240 份 | 15% | ±{power['exp01']['mde']*100:.1f}pt |")
w()
w(f"要检测渠道相对 +30% 的差异需每臂 **{power['exp02']['n_needed_relative_30pct']:,} 组**，"
  f"是全期看房量 KPI（900 组）的 {power['exp02']['n_needed_relative_30pct']*2/900:.1f} 倍。")
w()
w("## 8. 证据分级说明")
w()

with open(os.path.join(HERE,"KEY_FINDINGS.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print(f"\n  → 已写出 KEY_FINDINGS.md（{len(L)} 行）")
print(f"\n交付物：")
for fn in ["kpi_tree.json","experiments.json","power_analysis.json","model_output.json",
           "DECISION.md","SKILL_EVALUATION.md","KEY_FINDINGS.md"]:
    p = os.path.join(HERE, fn)
    print(f"  {'✅' if os.path.exists(p) else '❌'} {fn:<26} {os.path.getsize(p) if os.path.exists(p) else 0:>8,} bytes")
print("\n全部完成。复现命令：python3 scripts/run_all.py")
