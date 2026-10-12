#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地铁公寓项目 · GROWTH_DIAGNOSIS
单位经济模型（重写版）—— 运营方口径 / 甲方口径 / 控制权矩阵 / 反解可行条款

修正 v1 的三处错误：
  1. 渠道佣金率被误设为 0.0168 元/间次（应为 10万 ÷ 38间 ≈ 2,632 元/间次）
  2. 盈亏平衡求解器上限过低（1.5），把"无解"误报成 150%
  3. 未显式区分「谁承担哪笔成本」——这是本项目最关键的口径问题

运行：python3 scripts/02_econ_model.py
"""
import json

# ══════════════════════════════════════════════════════════════════════════════════════
# 0. 假设登记表
# ══════════════════════════════════════════════════════════════════════════════════════
ASSUMPTIONS = []
def reg(pid, name, value, unit, src, grade, note):
    ASSUMPTIONS.append(dict(id=pid, name=name, value=value, unit=unit,
                            source=src, grade=grade, note=note))

# —— 文档给定 ——
reg("A01","总建筑面积",2751.34,"㎡","产权交易所预公告 （日期已隐去） [A]","A","文档给定")
reg("A02","房间数",75,"间","三份文档一致 + 用户确认","A","文档给定（硬上限）")
reg("A03","甲方装修出资",3000000,"元","营销全案 1.1","A","文档给定")
reg("A04","乙方履约押金",1000000,"元","营销全案 1.1 / 合作模式报告前置条件","A","文档给定；不计息、期满退还")
reg("A05","月运营杂费",200,"元/间·月","营销全案 1.1；合作模式报告第2章","A",
    "文档给定。★口径冲突：合作模式报告称『按实际在租间数』，地块报告 7.4 按满租 75 间")
reg("A06","阶段一甲方分成（营销全案）",0.65,"—","营销全案 1.3 / 附录","E","文档给定，文件自标[假设]")
reg("A07","阶段B2 甲方分成（合作模式报告）",0.35,"—","合作模式报告 3.1 / 5.1","E","文档给定（推荐结构）")
reg("A08","阶段B1 甲方分成",0.40,"—","合作模式报告 3.1","E","文档给定")
reg("A09","合作期限",8,"年 / 96 月","合作模式报告前置条件","A","文档给定，固定不续约")
reg("A10","甲方 300 万回本硬约束",48,"月","合作模式报告前置条件","A","文档给定")
reg("A11","开业期营销预算",400000,"元","营销全案 5.3","E","文档给定（区间 30-45 万）")
reg("A12","月度运营推广费",25000,"元/月","营销全案 5.3『溢价期起』","E","文档给定")
reg("A13","首年成交间次",105,"间次","营销全案 5.3『90-120 间次』取中值","E","文档给定")
reg("A14","CAC 红线",4500,"元/间次","营销全案 5.3 / 第七章","E","文档给定")
reg("A15","目标出租率 第6月 / 第12月",[0.88,0.93],"—","营销全案 摘要 / 第七章","E","文档给定")
reg("A16","渠道分销佣金池",100000,"元","营销全案 5.3","E","文档给定")
reg("A17","渠道成交目标",38,"间","营销全案 5.3 KPI","E","文档给定")
reg("A18","有效看房目标",900,"组","营销全案 5.3 KPI","E","文档给定")
reg("A19","乙方稳态月运营成本",57800,"元/月","合作模式报告第2章","E",
    "★文档给定但无明细，且与营销全案『人工与运营招商费用由乙方另列』冲突")
reg("A20","乙方爬坡期月运营成本",85000,"元/月","合作模式报告第2章","E","文档给定")
reg("A21","乙方 8 年分成 / 净收益",[6597000,885000],"元","合作模式报告 5.1 / 7.3","D","文档自报，本次核验为不自洽")
reg("A22","房产税差额（4%→12%）",1085000,"元","合作模式报告 7.2","D","文档给定，占甲方出资 36.2%")
reg("A23","企业批量让价",0.05,"—","地块报告 6.3 P5『5-8%』","D","文档给定区间取低端")
reg("A24","客群权重 P1-P5",[0.35,0.30,0.10,0.15,0.10],"—","地块报告 6.3/6.4","D","文档建议权重，待 n≥100 问卷验证")
reg("A25","预登记问卷样本",100,"份","地块报告 6.5","E","文档给定")

# —— 本模型补齐（必带敏感度） ——
reg("B01","增值税及附加（架构一）",0.0168,"占租金收入","补：合作模式报告 7.1『1.5%×(1+12%附加)』","D",
    "税率文档给定；『按租金全额计征』这一适用判断为补齐。敏感区间 1.68%-6.72%")
reg("B02","房产税",0.04,"占租金收入","补：合作模式报告 7.2『4% 优惠税率』","D",
    "★归属问题：甲方为产权人，基准情景按【甲方承担】。文档另建议『超4%甲方兜底』")
reg("B03","渠道佣金单位成本",100000/38,"元/间次","补：10 万 ÷ 38 间（均为文档给定）","D","2,632 元/间次")
reg("B04","人力成本",45000,"元/月","补：75 间集中式公寓 5-6 人，本市 2026 薪酬","D",
    "★最大不确定项。敏感区间 32,000-55,000")
reg("B05","公区水电/网络/耗材",7000,"元/月","补：3,000㎡ 以下集中式公寓公区能耗","D",
    "租客套内水电通常自付；此项仅公区。敏感 5,000-9,000")
reg("B06","保洁与消杀",4500,"元/月","补：公区保洁半岗 2 人 + 季度消杀","D","敏感 3,000-6,000")
reg("B07","维修与设备维保",4500,"元/月","补：300 万装修资产 ×1.5%/年 + 日常维修","D","敏感 3,000-7,000")
reg("B08","办公/财税/软件/保险",3000,"元/月","补","D","敏感 2,000-4,000")
reg("B09","押金机会成本率",0.06,"年化","补：乙方资金成本 5-8% 区间取中","D","敏感 4%-8%")
reg("B10","年换租率",0.30,"—","补：青年长租公寓 25-35% 取中","D","敏感 20%-50%")
reg("B11","坏账率",0.01,"占租金","补：合作模式报告只给机制未给比率","D","敏感 0%-3%")
reg("B12","出房节奏（前5月出租率）",[0.35,0.50,0.70,0.82,0.86],"—",
    "补：按营销全案 5.1 节奏（开业月 50%、第3月 80%、第6月 88%）","D","与文档 KPI 对齐")

# ══════════════════════════════════════════════════════════════════════════════════════
# 1. 常量与工具
# ══════════════════════════════════════════════════════════════════════════════════════
R = {a["id"]: a["value"] for a in ASSUMPTIONS}
MIX = [(18,15,1620),(22,20,1980),(25,22,2250),(29,12,2610),(36,6,3150)]
ROOMS = sum(m[1] for m in MIX)
RENTABLE = sum(m[0]*m[1] for m in MIX)
FULL_REV = sum(m[1]*m[2] for m in MIX)
GFA = 2751.34
AVG_RENT = FULL_REV/ROOMS

def money(x, d=0): return f"{x:,.{d}f}"
def line(c="─", n=104): print(c*n)
def hdr(t): print(); line("═"); print(t); line("═")

# ══════════════════════════════════════════════════════════════════════════════════════
# 2. 控制权矩阵 —— 谁承担哪笔成本
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 0 部分｜控制权矩阵：每一块钱归谁、由谁承担（本项目一切口径争议的源头）")

CONTROL = [
    ("租金收入",                       "租客", "甲+乙按比例分配", "文档：月度可分红利润 = 总租金营收 − 运营杂费"),
    ("运营杂费 200 元/间·月",           "租客租金内", "★口径争议：甲方扣减项 or 乙方留存项",
     "营销全案 1.1『月运营杂费 15,000，人工与运营招商费用由乙方另列』→ 甲方扣减"),
    ("人工与运营招商费用",              "—", "乙方 100%", "营销全案 1.1 明确『由乙方另列』"),
    ("开业期营销 40 万 + 2.5 万/月",     "—", "乙方 100%（未明确，按营销全案 5.3 由乙方执行）",
     "★文档未明确谁出这 40 万——本模型按乙方承担，甲方承担则结论反转"),
    ("装修改造 300 万",                 "—", "甲方 100%", "营销全案 1.1"),
    ("履约押金 100 万",                 "—", "乙方 100%（不计息、期满退还）", "合作模式报告前置条件"),
    ("房产税 4% / 12%",                 "—", "★归属未定：甲方为产权人；报告建议『超4%甲方兜底』",
     "合作模式报告 7.2 —— 8 年差额 108.5 万，占甲方出资 36.2%"),
    ("增值税及附加",                    "—", "开票方（架构一为乙方，架构二为甲方）", "合作模式报告 7.1"),
    ("企业所得税",                      "—", "各自", "合作模式报告 7.3"),
    ("坏账（欠租超 30 日）",            "—", "双方按当期分配比例共担", "合作模式报告 3.1"),
]
print(f"{'科目':<26}{'资金来源':<14}{'承担方':<44}{'依据'}")
line()
for a,b,c,d in CONTROL:
    print(f"{a:<26}{b:<14}{c:<44}{d}")

# ══════════════════════════════════════════════════════════════════════════════════════
# 3. 收入与单位经济
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 1 部分｜收入侧与单位经济（基准：稳态出租率 90%）")

OCC = 0.90
OCC_ROOMS = ROOMS*OCC
GROSS = FULL_REV*OCC
OP_FEE = 200*OCC_ROOMS
VAT = GROSS*R["B01"]
DIST = GROSS - OP_FEE - VAT          # 可分配收入

# 甲方分成按营销全案阶段一 65%
A_SHARE_RATE_P1 = R["A06"]
A_SHARE = DIST*A_SHARE_RATE_P1
B_SHARE = DIST*(1-A_SHARE_RATE_P1)

# 乙方自有成本（自下而上）
cost_labor = R["B04"]; cost_util = R["B05"]; cost_clean = R["B06"]
cost_maint = R["B07"]; cost_office = R["B08"]
cost_mkt = R["A12"]                       # 2.5 万/月：已含媒体投放与渠道佣金，不另计佣金
cost_bad = GROSS*R["B11"]
B_OPEX = dict(labor=cost_labor, utility=cost_util, clean=cost_clean, maint=cost_maint,
              marketing=cost_mkt, bad_debt=cost_bad, office=cost_office)
B_OPEX_TOTAL = sum(B_OPEX.values())
DEP_OPP = R["A04"]*R["B09"]/12

print(f"\n【收入侧】90% 出租率 → {OCC_ROOMS:.1f} 间在租")
print(f"  满租月租金收入（75 间 × 分层定价）                    {money(FULL_REV):>12} 元/月")
print(f"  × 出租率 90%                                          {money(GROSS):>12} 元/月")
print(f"  − 运营杂费 200 × {OCC_ROOMS:.1f} 间                          {money(OP_FEE):>12} 元/月")
print(f"  − 增值税及附加（架构一 1.5%×1.12）                    {money(VAT):>12} 元/月")
print(f"  ══ 可分配收入                                         {money(DIST):>12} 元/月")
print(f"       甲方分成 65%                                    {money(A_SHARE):>12} 元/月")
print(f"       乙方分成 35%                                    {money(B_SHARE):>12} 元/月  ← 乙方『收入』")

print(f"\n【成本侧】乙方月度成本结构（自下而上重建，文档仅给总额 57,800 且无明细）")
print(f"{'成本项':<40}{'本模型':>10}{'来源':>8}{'敏感区间':>18}")
line()
for k, lbl, rng in [("labor","人力（店长/管家/维修/保洁主管 5-6 人）","32,000-55,000"),
                    ("utility","公区水电/网络/耗材","5,000-9,000"),
                    ("clean","保洁与消杀","3,000-6,000"),
                    ("maint","维修与设备维保（电梯/消防/门禁）","3,000-7,000"),
                    ("marketing","营销推广（2.5 万/月，含媒体与渠道佣金）","20,000-35,000"),
                    ("bad_debt","坏账计提 1% 租金","0-3% 租金"),
                    ("office","办公/财税/软件/保险","2,000-4,000")]:
    print(f"{lbl:<40}{money(B_OPEX[k]):>10}{'补':>8}{rng:>18}")
line()
print(f"{'乙方月度自有成本合计':<40}{money(B_OPEX_TOTAL):>10}")
print(f"{'隐含单位成本（÷75 间）':<40}{money(B_OPEX_TOTAL/ROOMS):>10} 元/间·月")
print(f"{'文档给定乙方稳态成本':<40}{money(R['A19']):>10} 元/间·月口径下 {money(R['A19']/ROOMS)} 元/间")
print(f"{'差额':<40}{money(B_OPEX_TOTAL-R['A19']):>10}  ({B_OPEX_TOTAL/R['A19']-1:+.0%})")
print(f"\n  ★文档 57,800 的构成反推：若其中含运营杂费 200×75={money(200*75)}（满租口径），")
print(f"    则乙方自有运营项仅 {money(R['A19']-15000)} 元/月 = {money((R['A19']-15000)/ROOMS)} 元/间·月，")
print(f"    而同期『人工与运营招商费用由乙方另列』——说明 57,800 不能代表乙方全成本。")
print(f"    若 57,800 不含运营杂费，则自有项 {money((R['A19']-15000)/ROOMS if False else R['A19']/ROOMS)} 元/间·月，仍不含营销。")

print(f"\n【单位贡献 · 乙方口径】")
contrib = (B_SHARE - B_OPEX_TOTAL)/OCC_ROOMS
print(f"  单间月收入（分成口径）                {money(B_SHARE/OCC_ROOMS):>10} 元/间·月")
print(f"  单间月全成本                          {money(B_OPEX_TOTAL/ROOMS):>10} 元/间·月")
print(f"  ── 单间月贡献                         {money(contrib):>10} 元/间·月")
print(f"  月度经营现金流                        {money(B_SHARE-B_OPEX_TOTAL):>10} 元/月")
print(f"  押金机会成本（6% × 100 万）           {money(DEP_OPP):>10} 元/月")
print(f"  经济口径月度现金流                    {money(B_SHARE-B_OPEX_TOTAL-DEP_OPP):>10} 元/月")
print(f"\n  单位收入 vs 单位成本的缺口倍数："
      f"{B_OPEX_TOTAL/ROOMS/(B_SHARE/OCC_ROOMS):.2f}× —— 乙方每收 1 元要花 "
      f"{B_OPEX_TOTAL/ROOMS/(B_SHARE/OCC_ROOMS):.2f} 元")

# ══════════════════════════════════════════════════════════════════════════════════════
# 4. 三种口径下的乙方处境
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 2 部分｜口径（interpretation）× 处境：乙方到底能不能活")

def b_position(occ, op_fee_to_a, opex, extra_b_revenue=0.0):
    """op_fee_to_a: True=运营杂费归甲方（营销全案1.1口径）；False=归乙方（合作模式报告5.1隐含口径）"""
    g = FULL_REV*occ
    fee = 200*ROOMS*occ
    vat = g*R["B01"]
    dist = g - vat - (fee if op_fee_to_a else 0.0)
    b_rev = dist*0.35 + (0.0 if op_fee_to_a else fee) + extra_b_revenue
    return dict(gross=g, fee=fee, vat=vat, dist=dist, b_rev=b_rev, b_opex=opex,
                b_cf=b_rev-opex)

INTERPS = [
    ("口径① 营销全案 1.1：杂费归甲方，乙方另担人工营销（本模型基准）", True,  B_OPEX_TOTAL),
    ("口径② 合作模式报告 5.1 隐含：杂费归乙方，乙方另担人工营销",     False, B_OPEX_TOTAL),
    ("口径③ 最乐观：杂费归乙方 + 用文档成本 57,800（已含杂费）",       False, R["A19"]),
    ("口径④ 次乐观：杂费归乙方 + 文档自有项 42,800 + 营销 25,000",     False, (R["A19"]-15000)+R["A12"]),
]
print(f"\n{'口径':<58}{'乙方月收入':>12}{'乙方月成本':>12}{'月现金流':>12}{'年现金流':>13}")
line()
interp_res = []
for lbl, fee_to_a, ox in INTERPS:
    r = b_position(OCC, fee_to_a, ox)
    interp_res.append((lbl, r))
    print(f"{lbl:<58}{money(r['b_rev']):>12}{money(r['b_opex']):>12}{money(r['b_cf']):>12}{money(r['b_cf']*12):>13}")
print(f"\n  ▶ 基准口径①下乙方月亏 {money(abs(interp_res[0][1]['b_cf']))} 元；即便接受口径③（杂费归乙方 +")
print(f"    文档 57,800 已含全部成本），乙方月现金流也仅 {money(interp_res[2][1]['b_cf'])} 元 = 年 {money(interp_res[2][1]['b_cf']*12)} 元，")
print(f"    相对 100 万押金年化 {interp_res[2][1]['b_cf']*12/R['A04']:.1%} —— 低于任何运营商的项目门槛回报。")
print(f"  ▶ 结构性结论：乙方分成 {money(B_SHARE/OCC_ROOMS)} 元/间·月，而单间运营成本落在 "
      f"{money(R['A19']/ROOMS)}-{money(B_OPEX_TOTAL/ROOMS)} 元/间·月；")
print(f"    即使取成本区间下沿，乙方也只在『杂费归自己 + 成本取最低』这一窄缝里勉强打平。")

# ══════════════════════════════════════════════════════════════════════════════════════
# 5. 反解：什么条款才成立
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 3 部分｜反解可行条款：不是『谁该让』，而是算术要求多少")

def required_b_rate(target_b_cf, occ=OCC, opex=None):
    ox = B_OPEX_TOTAL if opex is None else opex
    g = FULL_REV*occ; fee = 200*ROOMS*occ; vat = g*R["B01"]
    dist = g - fee - vat
    # b_rev = dist*(1-rate) = ox + target_b_cf
    need = ox + target_b_cf
    return 1 - need/dist, need, dist

targets = [("保本（月现金流=0）", 0),
           ("押金机会成本 6%（月赚 5,000）", DEP_OPP),
           ("押金+机会成本年化 10%（月赚 8,333）", R["A04"]*0.10/12),
           ("押金+机会成本年化 15%（月赚 12,500）", R["A04"]*0.15/12),
           ("覆盖前 6 月爬坡亏损后再年化 10%", R["A04"]*0.10/12 + (85000-B_OPEX_TOTAL)*6/96)]
print(f"\n注：rate 为甲方分成比例；乙方比例 = 1 − rate")
print(f"{'乙方目标':<40}{'乙方月需收入':>14}{'甲方分成须降至':>16}{'乙方分成须升至':>16}")
line()
for lbl, tgt in targets:
    rate, need, dist = required_b_rate(tgt)
    flag = "" if rate >= 0 else "  ← 无解"
    print(f"{lbl:<40}{money(need):>14}{rate:>15.1%}{1-rate:>16.1%}{flag}")
print(f"\n  文档给定：营销全案阶段一 甲方 65% / 乙方 35%；合作模式报告 B2 甲方 35% / 乙方 65%")
print(f"  ▶ 按营销全案 65/35，乙方分成 {money(B_SHARE/OCC_ROOMS)} 元/间·月 < 单间成本下沿 "
      f"{money(R['A19']/ROOMS)} 元 → 结构性亏损。")
print(f"  ▶ 要保本，乙方分成须升至 {1-required_b_rate(0)[0]:.1%}（即甲方降至 {required_b_rate(0)[0]:.1%}）——")
print(f"    已低于甲方 48 个月回本所需的受偿强度，甲方硬约束与乙方保本互相冲突。")

# 甲方视角：在让出分成后，300 万还能否 48 个月回本
hdr("第 4 部分｜甲方 300 万回本约束 vs 乙方保本约束 —— 二律背反检验")

def a_payback_months(a_rate, occ=OCC, ptax=0.0, ramp=None):
    """在给定甲方分成比例下，甲方收回 300 万所需月数。ramp: 前 5 月出租率序列"""
    curve_local = (ramp or R["B12"]) + [occ]*(200-len(ramp or R["B12"]))
    cum = 0.0
    for m in range(1, 241):
        o = curve_local[m-1]
        g = FULL_REV*o; fee = 200*ROOMS*o; vat = g*R["B01"]
        dist = g - fee - vat - g*ptax
        cum += dist*a_rate
        if cum >= R["A03"]:
            return m
    return None

print(f"\n{'甲方分成比例':>14}{'乙方分成比例':>14}{'乙方月现金流':>15}{'甲方回本(月)':>14}{'是否≤48月':>12}")
line()
for ar in [0.65, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30]:
    br = 1-ar
    g = FULL_REV*OCC; fee = 200*ROOMS*OCC; vat = g*R["B01"]
    b_cf = (g-fee-vat)*br - B_OPEX_TOTAL
    pm = a_payback_months(ar)
    ok = "✅" if (pm and pm <= 48) else "❌"
    print(f"{ar:>13.0%}{br:>14.0%}{money(b_cf):>15}{pm if pm else '>240':>14}{ok:>12}")
print(f"\n  ▶ 甲方的硬约束（≤48 月回本）要求甲方分成 ≥ 约 55%；")
print(f"    乙方的保本要求甲方分成 ≤ {required_b_rate(0)[0]:.0%}。")
print(f"    两个约束的交集为空 —— 在 200 元/间·月 的杂费口径和 2,182 元均价下，")
print(f"    该项目【无法同时满足】甲方的 4 年回本与乙方的经营保本。")

# ══════════════════════════════════════════════════════════════════════════════════════
# 6. CAC
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 5 部分｜CAC：40 万预算买到多少间次（运营方口径）")

print(f"\n【三种 CAC 口径】分母统一：首年新签约间次 {R['A13']}（文档 90-120 取中值）")
cac1 = R["A11"]/R["A13"]
cac2 = (R["A11"]-60000-40000)/R["A13"]
cac3 = 180000/R["A13"]
cac4 = (R["A11"]+R["B03"]*38)/R["A13"]
for lbl, v, note in [("① 广义（40 万全口径）",cac1,"含 VI/物料/内容/活动，品牌支出计入获客"),
                     ("② 现金投放口径（剔除 VI 6 万 + 内容 4 万）",cac2,"品牌资产不计入 CAC"),
                     ("③ 纯媒介（仅 18 万效果投放）",cac3,"忽略分销与活动"),
                     ("④ 广义 + 渠道佣金（38 间×2,632）",cac4,"佣金计入变动获取成本")]:
    print(f"  {lbl:<44}{money(v):>8} 元/间次   红线 4,500 → {'✅' if v<=4500 else '❌'}  ({note})")

print(f"\n【40 万能买多少间次 vs 75 间总量】")
for c in [3300, 4500]:
    print(f"  CAC {money(c)} 元/间次 → 400,000 ÷ {money(c)} = {400000/c:.1f} 间次")
print(f"  若 40 万全部投入首年 {R['A13']} 间次 → CAC {money(cac1)} 元/间次 ✅ 与文档自报 3,300-4,400 一致")
print(f"  ▶ 预算与『首年 90-120 间次』自洽。但与『6 个月做到 88%』的节奏不自洽：")

print(f"\n【出房节奏可行性】")
LU = [("第 1 月",1,0.50),("第 3 月",3,0.80),("第 6 月",6,0.88),("第 12 月",12,0.93)]
CURVE_M = [0.35,0.50,0.70,0.82,0.86]
print(f"  按营销全案 5.1 的节点（开业月 50%、第 3 月 80%、第 6 月 88%、第 12 月 93%）")
print(f"{'节点':<9}{'目标出租率':>11}{'累计需签约(间)':>15}{'区间新增(间)':>13}{'按CAC4500需预算':>17}{'累计需预算':>13}")
line()
prev = 0; cum_need = 0
for lbl, m, occ in LU:
    tgt = 75*occ
    new = tgt - prev
    need_ = new*4500
    cum_need += need_
    print(f"{lbl:<9}{occ:>10.0%}{tgt:>15.0f}{new:>13.0f}{money(need_):>17}{money(cum_need):>13}")
    prev = tgt
print(f"\n  到第 6 月累计需获客预算 {money(cum_need)} 元（按 CAC 4,500）")
print(f"  而开业期总预算 40 万，其中：VI/物料 6 万 + 内容制作 4 万 = 10 万【非直接获客】")
print(f"  可用于获客的上限 = 40 万 − 10 万 = 30 万")
print(f"  ▶ 缺口 = {money(cum_need)} − 300,000 = {money(cum_need-300000)} 元")
print(f"  ▶ 要在 30 万内完成，实际 CAC 必须 = 300,000 ÷ 66 间 = {money(300000/66)} 元/间次 "
      f"({'✅ 可行' if 300000/66<=4500 else '❌ 超红线'})")
print(f"  ▶ 若坚持 CAC 4,500，则 30 万只能支撑 {300000/4500:.1f} 间 → 第 6 月出租率 "
      f"{300000/4500/75:.1%}（目标 88%）")

print(f"\n【渠道侧 KPI 互斥】")
print(f"  渠道分销 10 万，KPI『渠道成交不低于 38 间』→ 单位佣金 100,000÷38 = {money(100000/38)} 元/间")
print(f"  同时 KPI『首年成交 90-120 间次』且『综合 CAC ≤4,500』")
print(f"  若 38 间由渠道贡献，其余 {R['A13']-38} 间由效果投放贡献：")
print(f"    效果投放需产出 {R['A13']-38} 间，预算 18 万 → CAC {money(180000/(R['A13']-38))} 元/间")
print(f"    看房→签约 CVR 需达 {(R['A13']-38)/R['A18']:.1%}（KPI 设 900 组看房）")
print(f"    18 万 ÷ 900 组 = CPL {money(180000/900)} 元/组 ✅")
print(f"    ⇒ 链路自洽，条件：看房→签约转化率 ≥ {(R['A13']-38)/R['A18']:.1%}")
print(f"  ▶ 这是可验证的关键假设，必须在前 3 个月实测（见 experiments.json EXP-02）")

# ══════════════════════════════════════════════════════════════════════════════════════
# 7. 回本周期（三口径）
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 6 部分｜回本周期：三个口径，三个答案")

a_months = a_payback_months(0.65)
print(f"\n① 甲方口径（300 万装修出资）")
print(f"   按 65% 分成、稳态 90%、含前 5 月爬坡：回本 {a_months} 个月 = {a_months/12:.2f} 年")
a_full = (FULL_REV-200*ROOMS-FULL_REV*R["B01"])*0.65
print(f"   满租（100%）稳态快算：{money(a_full)} 元/月 → {R['A03']/a_full/12:.2f} 年")
print(f"   文档宣称 1.9 年；文档 1.3 节自称 2.4-2.8 年；文档第七章 KPI ≤30 个月（2.5 年）")
print(f"   ▶ 1.9 年仅能由『300 万 ÷ 全额可分净利 135,000』复现 = {3000000/135000:.1f} 月 = "
      f"{3000000/135000/12:.2f} 年，即假设甲方【独占全部分红、不给乙方一分钱】")

print(f"\n② 乙方现金口径（100 万押金何时被经营现金流收回）")
b_cf = B_SHARE - B_OPEX_TOTAL
print(f"   月度经营现金流 = {money(b_cf)} 元 → 现金流为负，不存在回本周期")
print(f"   8 年合同期累计 = {money(b_cf*96)} 元（负值）")
print(f"   叠加前 6 月爬坡（月成本 85,000）后 8 年累计 = "
      f"{money(6*(B_SHARE-85000)+90*b_cf)} 元")
print(f"   ▶ 乙方不存在『回本』问题，存在的是『押金多久被烧完』问题：")
print(f"     按稳态月亏 {money(abs(b_cf))}，100 万押金 {R['A04']/abs(b_cf):.0f} 个月烧穿")
print(f"     若计入爬坡期，第 1 年即亏 {money(6*(B_SHARE-85000)+6*b_cf)} 元")

print(f"\n③ 乙方经济口径（押金按 6% 计机会成本）")
print(f"   月度经济现金流 = {money(b_cf-DEP_OPP)} 元 → 8 年累计 {money((b_cf-DEP_OPP)*96)} 元")

print(f"\n【为什么与宣称的 1.9 年不同 —— 三条原因】")
print(f"  1) 口径错位：1.9 年 = 甲方独占全部分红的回本，未扣乙方分成。按 65/35 分成后变 "
      f"{a_months/12:.2f} 年（+{(a_months/12/1.9-1)*100:.0f}%）")
print(f"  2) 未计爬坡：1.9 年隐含满租起步；计入前 5 月爬坡与空置后回本延后 "
      f"{a_months-3000000/((FULL_REV-200*75-FULL_REV*R['B01'])*0.65):.1f} 个月")
print(f"  3) 主体错位：乙方投入的是 100 万押金（非 300 万装修），其回本逻辑完全不同；")
print(f"     把 300 万的回本周期用于乙方或投资方的陈述是口径错误")

# ══════════════════════════════════════════════════════════════════════════════════════
# 8. 出租率敏感度（四档）
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 7 部分｜出租率敏感度：60% / 75% / 88% / 93%（甲方 + 乙方双口径）")

print(f"\n口径：运营杂费按合作模式报告第2章『按实际在租间数』；增值税架构一；房产税由甲方承担")
print(f"      乙方成本 = 本模型自下而上 {money(B_OPEX_TOTAL)} 元/月（稳态）")
print()
print(f"{'出租率':>7}{'在租间':>7}{'月租金收入':>12}{'可分配收入':>12}{'甲方月分红':>12}{'甲方年收益':>13}"
      f"{'甲方回本(年)':>13}{'乙方月收入':>12}{'乙方月成本':>12}{'乙方月现金流':>13}{'乙方年现金流':>13}")
line("─", 156)
sens = []
for occ in [0.60, 0.75, 0.88, 0.93]:
    g = FULL_REV*occ; fee = 200*ROOMS*occ; vat = g*R["B01"]
    dist = g-fee-vat
    a = dist*0.65; b = dist*0.35
    bcf = b - B_OPEX_TOTAL
    pm = a_payback_months(0.65, occ=occ)
    rec = dict(occupancy=occ, rooms=ROOMS*occ, gross=g, fee=fee, vat=vat, distributable=dist,
               a_month=a, a_year=a*12, a_payback_years=pm/12 if pm else None,
               b_revenue=b, b_opex=B_OPEX_TOTAL, b_cf=bcf, b_year=bcf*12,
               b_revenue_per_room=b/(ROOMS*occ), b_opex_per_room=B_OPEX_TOTAL/ROOMS,
               b_contribution_per_room=bcf/(ROOMS*occ))
    sens.append(rec)
    print(f"{occ:>6.0%}{ROOMS*occ:>7.0f}{money(g):>12}{money(dist):>12}{money(a):>12}{money(a*12):>13}"
          f"{(pm/12 if pm else 0):>13.2f}{money(b):>12}{money(B_OPEX_TOTAL):>12}{money(bcf):>13}{money(bcf*12):>13}")

print(f"\n【押金侵蚀分析】乙方履约押金 100 万")
print(f"{'出租率':>7}{'乙方月现金流':>14}{'单间月贡献':>12}{'8年累计现金流':>16}{'押金耗尽':>12}{'判定':>34}")
line()
for r_ in sens:
    if r_["b_cf"] < 0:
        dep = R["A04"]/abs(r_["b_cf"])
        verdict = f"★★ 押金 {dep:.0f} 个月烧穿（{dep/12:.1f} 年）"
    else:
        dep = None; verdict = "✅ 现金流为正，押金不被侵蚀"
    print(f"{r_['occupancy']:>6.0%}{money(r_['b_cf']):>14}{money(r_['b_contribution_per_room']):>12}"
          f"{money(r_['b_cf']*96):>16}{(f'{dep:.0f}月' if dep else '—'):>12}{verdict:>34}")
print(f"\n  ▶ 四档下乙方月度现金流均为负；88% 与 93% 档的差异仅 "
      f"{money(abs(sens[2]['b_cf']-sens[3]['b_cf']))} 元/月 ——")
print(f"    即『把出租率从 88% 拉到 93%』对乙方处境的改善，远小于『改分成比例』。")
print(f"  ▶ 押金在全部四档下都会在 {min(R['A04']/abs(r_['b_cf']) for r_ in sens):.0f}-"
      f"{max(R['A04']/abs(r_['b_cf']) for r_ in sens):.0f} 个月内被经营亏损消耗，")
print(f"    而合同约定押金『仅用于保证履约、期满退还』——履约保障在 {R['A04']/abs(sens[2]['b_cf']):.0f} 个月后名存实亡。")

# ══════════════════════════════════════════════════════════════════════════════════════
# 9. 敏感度
# ══════════════════════════════════════════════════════════════════════════════════════
hdr("第 8 部分｜补齐假设的敏感度：哪些『我补的数』会改变结论")

print(f"\n【S1 乙方月度成本】—— 决定结论是否翻转的关键")
print(f"{'乙方月成本':>12}{'相对基准':>10}{'月现金流':>13}{'8年累计':>15}{'乙方保本所需分成':>18}{'甲方可分':>11}")
line()
for f in [0.60, 0.695, 0.80, 1.00, 1.20, 1.40]:
    ox = B_OPEX_TOTAL*f
    bcf = B_SHARE - ox
    g = FULL_REV*OCC; fee = 200*ROOMS*OCC; vat = g*R["B01"]; dist = g-fee-vat
    need_rate = ox/dist          # 乙方需要的分成比例（甲方 = 1 - need_rate）
    print(f"{money(ox):>12}{f-1:>+9.0%}{money(bcf):>13}{money(bcf*96):>15}"
          f"{need_rate:>17.1%}{1-need_rate:>11.1%}")
print(f"  ▶ 即便乙方成本压到基准的 60%（{money(B_OPEX_TOTAL*0.6)} 元/月），仍需分成 "
      f"{B_OPEX_TOTAL*0.6/(FULL_REV*OCC-200*ROOMS*OCC-FULL_REV*OCC*R['B01']):.1%} 才保本。")

print(f"\n【S2 押金机会成本率】—— 只影响乙方经济口径")
print(f"{'资金成本':>10}{'押金机会成本/月':>18}{'经济口径月现金流':>20}{'经济口径8年':>16}")
line()
for r_ in [0.0, 0.04, 0.06, 0.08, 0.10]:
    opp = R["A04"]*r_/12
    print(f"{r_:>9.0%}{money(opp):>18}{money(b_cf-opp):>20}{money((b_cf-opp)*96):>16}")

print(f"\n【S3 房产税归属与税率】—— 只改甲方回报，不改变乙方结论")
print(f"{'情形':<30}{'甲方8年累计':>14}{'甲方回本(月)':>14}{'乙方8年净':>15}")
line()
for lbl, ptax in [("甲方承担 · 4% 优惠",0.04), ("甲方承担 · 12% 法定",0.12), ("乙方承担 · 4% 优惠",0.04)]:
    cum_a = cum_b = 0.0
    for m in range(1, 97):
        o = (R["B12"] + [0.90]*200)[m-1]
        g = FULL_REV*o; fee = 200*ROOMS*o; vat = g*R["B01"]
        if lbl.startswith("乙方"):
            dist = g - fee - vat
            cum_a += dist*0.65
            cum_b += dist*0.35 - g*ptax
        else:
            dist = g - fee - vat - g*ptax
            cum_a += dist*0.65
            cum_b += dist*0.35
    b_net = cum_b - 6*85000 - 90*B_OPEX_TOTAL
    pm = a_payback_months(0.65, occ=0.90, ptax=(ptax if not lbl.startswith('乙方') else 0.0))
    print(f"{lbl:<30}{money(cum_a):>14}{pm:>14}{money(b_net):>15}")
ptax_8y = sum(FULL_REV*(R["B12"]+[0.90]*200)[m-1]*0.04 for m in range(1,97))
print(f"  ▶ 合作模式报告 7.2 的 108.5 万差额是【甲方】口径（占甲方出资 36.2%）；")
print(f"    同一报告又建议『超 4% 部分由甲方兜底』。若改由乙方承担 4% 房产税，")
print(f"    乙方 8 年再减少 {money(ptax_8y)} 元 —— 相当于其在基准情景下的全部名义收益。")

print(f"\n【S4 年换租率】—— 决定 2.5 万/月 是否够用（按 CAC 4,500）")
print(f"{'换租率':>8}{'年需签约(间)':>14}{'需获客预算':>13}{'2.5万/月×12=30万':>18}{'结论':>16}")
line()
for ch in [0.20, 0.30, 0.40, 0.50]:
    ns = 75*ch
    need = ns*4500
    print(f"{ch:>7.0%}{ns:>14.0f}{money(need):>13}{money(300000):>18}"
          f"{('✅ 够用' if need<=300000 else '❌ 缺口 '+money(need-300000)):>16}")
print(f"  ▶ 按 CAC 4,500，2.5 万/月（30 万/年）可覆盖 {300000/4500:.0f} 间次/年，")
print(f"    即换租率 ≤ {300000/4500/75:.0%} 时够用；该阈值本身就是一条护栏。")

print(f"\n【S5 运营杂费口径】满租 75 间 vs 实际在租 —— 对甲方回本的影响")
print(f"{'出租率':>8}{'满租口径甲方分红':>18}{'在租口径甲方分红':>18}{'差额':>12}{'回本差(月)':>12}")
line()
for occ in [0.60, 0.75, 0.88, 0.93]:
    g = FULL_REV*occ; vat = g*R["B01"]
    a_fix = (g-200*ROOMS-vat)*0.65
    a_var = (g-200*ROOMS*occ-vat)*0.65
    print(f"{occ:>7.0%}{money(a_fix):>18}{money(a_var):>18}{money(a_fix-a_var):>12}"
          f"{(R['A03']/a_var-R['A03']/a_fix):>12.1f}")
print(f"  ▶ 口径方向说明：在低出租率下『满租口径』会【低估】甲方分红（因扣掉的杂费更多），")
print(f"    即地块报告 7.4 节的 80%/90% 情景对甲方略偏保守，而非偏乐观。")
print(f"    真正的问题不是方向，而是两份文档未统一口径，导致任何第三方复算都会得到不同数字。")

# ══════════════════════════════════════════════════════════════════════════════════════
# 10. 输出
# ══════════════════════════════════════════════════════════════════════════════════════
out = dict(
    generated_from=["D 站片区03_品牌营销全案.txt","P 路98号公寓项目合作模式研究报告_中立研判版.txt","P 路98号地块专项研究报告.txt"],
    assumptions=ASSUMPTIONS,
    pricing=dict(mix=MIX, rooms=ROOMS, rentable_sqm=RENTABLE, gfa=GFA,
                 full_monthly_revenue=FULL_REV, avg_rent=round(AVG_RENT,2),
                 sqm_on_rentable=round(FULL_REV/RENTABLE,2),
                 sqm_on_gfa=round(FULL_REV/GFA,2)),
    operator=dict(occupancy=OCC, occupied_rooms=OCC_ROOMS, gross_monthly=GROSS,
                  op_fee=OP_FEE, vat=VAT, distributable=DIST,
                  a_share=A_SHARE, b_share=B_SHARE,
                  b_revenue_per_room=round(B_SHARE/OCC_ROOMS,0),
                  opex=B_OPEX, opex_total=B_OPEX_TOTAL,
                  opex_per_room=round(B_OPEX_TOTAL/ROOMS,0),
                  doc_opex=R["A19"],
                  b_monthly_cashflow=round(b_cf,0),
                  contribution_per_room=round(contrib,0),
                  deposit_opportunity=DEP_OPP,
                  b_monthly_cashflow_econ=round(b_cf-DEP_OPP,0),
                  deposit_burn_months=round(R["A04"]/abs(b_cf),1)),
    interpretations=[dict(label=l, b_revenue=round(r["b_rev"],0), b_opex=round(r["b_opex"],0),
                          b_monthly_cashflow=round(r["b_cf"],0)) for l,r in interp_res],
    required_a_rate_for_b_breakeven=round(required_b_rate(0)[0],4),
    a_share_rate_doc=0.65, b_share_rate_doc=0.35,
    cac=dict(all_in=round(cac1,0), cash=round(cac2,0), media_only=round(cac3,0),
             incl_commission=round(cac4,0), ceiling=4500,
             unit_commission=round(R["B03"],0), denominator_signings=R["A13"]),
    payback=dict(a_party_months=a_months, a_party_years=round(a_months/12,2),
                 claimed_years=1.9, doc_section_1_3="2.4-2.8", doc_kpi_months=30,
                 b_party="negative cash flow; no payback within 8-year term"),
    occupancy_sensitivity=sens,
    leaseup=dict(cumulative_budget_needed_6m=round(cum_need,0), available_for_acquisition=300000,
                 gap=round(cum_need-300000,0),
                 cac_if_30w_for_66=round(300000/66,0),
                 coverage_at_88pct=round(300000/4500/75,4)),
)
with open("model_output.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
print(f"\n[已写出 model_output.json]")
print("可复现：python3 scripts/02_econ_model.py")
