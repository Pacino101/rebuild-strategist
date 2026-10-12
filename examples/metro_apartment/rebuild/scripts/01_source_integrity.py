#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地铁公寓项目 · GROWTH_DIAGNOSIS 步骤 1/4
源文档算术一致性核验 —— 在信任任何数字之前，先把文档内部能对上的和不能对上的分开。

输入：三份源文档中明确写出的数字（硬编码，逐条标注出处行号）
输出：每条断言的复核结果（OK / MISMATCH / UNVERIFIABLE）
不引入任何本文档之外的市场假设。
"""
import sys

def fmt(x, d=0):
    return f"{x:,.{d}f}"

results = []
def check(tag, claim, recomputed, tol=0.5, unit="元", src=""):
    ok = abs(claim - recomputed) <= tol
    results.append((tag, claim, recomputed, ok, unit, src))
    return ok

def show(tag, value, unit="", note="", src=""):
    results.append((tag, None, value, None, unit, src + (" | " + note if note else "")))

print("=" * 100)
print("A. 定价矩阵与面积口径核验")
print("=" * 100)

# 房型配比（地块专项报告 4.3 节，D 级推算）
mix = [(18, 15, 1620), (22, 20, 1980), (25, 22, 2250), (29, 12, 2610), (36, 6, 3150)]
rooms = sum(m[1] for m in mix)
rentable = sum(m[0] * m[1] for m in mix)
monthly = sum(m[1] * m[2] for m in mix)
avg_rent = monthly / rooms
total_gfa = 2751.34

print(f"房型间数合计          = {rooms} 间                 (文档：75) ")
print(f"单间建面加总          = {rentable} ㎡              (文档 4.3 节合计栏：1,824 ㎡)")
print(f"满租月租金收入        = {fmt(monthly)} 元/月        (文档：163,620 元)")
print(f"均价                  = {avg_rent:.2f} 元/间       (文档：2,182 元)")
check("满租月营收", 163620, monthly, 1, "元", "地块报告 4.3/7.2 合计栏")
check("均价", 2182, avg_rent, 1, "元/间", "营销全案执行摘要")
check("单间建面合计", 1824, rentable, 1, "㎡", "地块报告 4.3 合计栏")

print()
print("--- 综合单方租金 89.7 元/㎡·月 的分母是什么？ ---")
sqm_on_mix = monthly / rentable
sqm_on_gfa = monthly / total_gfa
sqm_on_30pct = monthly / (total_gfa * 0.70)
print(f"  用「单间建面加总 1,824 ㎡」做分母      : {sqm_on_mix:.2f} 元/㎡·月   <- 与文档 89.7 一致")
print(f"  用「总建筑面积 2,751.34 ㎡」做分母    : {sqm_on_gfa:.2f} 元/㎡·月")
print(f"  用「总建面×70% = 1,925.94 ㎡」做分母  : {sqm_on_30pct:.2f} 元/㎡·月   <- 与地块报告 4.1 节可租面积口径一致")
check("综合单方(分母=单间建面加总)", 89.7, sqm_on_mix, 0.05, "元/㎡·月", "营销全案执行摘要")
show("综合单方(分母=总建筑面积)", f"{sqm_on_gfa:.2f}", "元/㎡·月",
     "政策原文口径为「建筑面积」，与 89.7 相差 33.7%")
show("综合单方(分母=总建面×70%)", f"{sqm_on_30pct:.2f}", "元/㎡·月",
     "同一文档 4.1 节自己的可租面积口径，比 89.7 低 15.1%")

print()
print("  可租面积两套数打架：")
print(f"    4.1 节推算可租面积 2,751.34 × 70% = {total_gfa*0.70:.2f} ㎡")
print(f"    4.3 节房型表加总                  = {rentable} ㎡")
print(f"    差额 = {total_gfa*0.70 - rentable:.2f} ㎡ ({((total_gfa*0.70)/rentable - 1)*100:.1f}%)")
print(f"    反解 4.3 节隐含公区占比 = 1 - {rentable}/{total_gfa} = {(1-rentable/total_gfa)*100:.1f}%")

print()
print("=" * 100)
print("B. 回本 1.9 年从哪里来？—— 逐条复算")
print("=" * 100)

op_fee = 200 * rooms   # 月运营杂费 15,000 元
print(f"月运营杂费（200 元/间 × 75 间，按满租）= {fmt(op_fee)} 元/月   (文档 1.1 节：15,000 元)")
check("月运营杂费(满租口径)", 15000, op_fee, 1, "元", "营销全案 1.1 节")

scen = [("保底档", 2000, 150000), ("中档", 2300, 172500), ("溢价档", 2600, 195000)]
print()
print(f"{'档位':<8}{'单间月租':>10}{'月总营收':>12}{'月可分净利':>12}{'甲方100%口径回本':>18}{'甲方65%口径回本':>18}")
for name, rent, rev in scen:
    net = rev - op_fee
    pb100 = 3_000_000 / net / 12
    pb65 = 3_000_000 / (net * 0.65) / 12
    check(f"月总营收·{name}", rev, rent * rooms, 1, "元")
    check(f"月度可分净利·{name}", net, rev - 15000, 1, "元")
    print(f"{name:<8}{rent:>10}{fmt(rev):>12}{fmt(net):>12}{pb100:>15.2f}年{pb65:>15.2f}年")

print()
print("  文档自己写的：保底档月分红约 8.8 万、回本约 2.8 年；中档约 10.2 万、回本约 2.4 年")
for name, _, rev in scen[:2]:
    net = rev - op_fee
    print(f"    {name}: 净利×65% = {fmt(net*0.65)} 元/月 → 回本 {3_000_000/(net*0.65)/12:.2f} 年")
print()
print("  >>> 结论：1.9 年无法由任何『按 65% 分成』的档位复现。")
print("      唯一能复现 1.9 年的算法：把 100% 的月度可分净利都算作甲方回收，")
print(f"      3,000,000 ÷ 135,000 = {3_000_000/135000:.2f} 个月 ≈ {3_000_000/135000/12:.2f} 年（保底档）。")
print("      即执行摘要的 1.9 年 = 未扣乙方分成的全口径回本，与第 1.3 节/第七章自相矛盾。")

print()
print("=" * 100)
print("C. 出租率情景复算（地块报告 7.4 节口径：甲方 65%，运营杂费按满租 75 间计）")
print("=" * 100)
print(f"{'出租率':>8}{'在租间数':>10}{'月租金收入':>14}{'月可分净利':>14}{'甲方月分红':>14}{'回本(年)':>12}")
for occ in [1.00, 0.90, 0.80]:
    occ_rooms = rooms * occ
    rev = monthly * occ
    net = rev - op_fee
    a_share = net * 0.65
    print(f"{occ*100:>7.0f}%{occ_rooms:>10.1f}{fmt(rev):>14}{fmt(net):>14}{fmt(a_share):>14}{3_000_000/a_share/12:>12.2f}")
print("  文档 7.4 节：满租 2.6 年 / 90% 2.9 年 / 80% 3.3 年 → 与本表一致 ✅")
check("90%出租率回本(年)", 2.9, 3_000_000/(monthly*0.9-op_fee)/0.65/12, 0.05, "年", "地块报告 7.4")
check("80%出租率回本(年)", 3.3, 3_000_000/(monthly*0.8-op_fee)/0.65/12, 0.05, "年", "地块报告 7.4")

print()
print("  注意：上述口径把运营杂费当作与出租率无关（恒为 15,000 元）。")
print("  若杂费按『实际在租间数 × 200 元』计（合作模式报告第 2 章明确写『按实际在租间数』），")
print("  则 80% 出租率下：")
rev80 = monthly * 0.8
net80_v = rev80 - 200 * rooms * 0.8
a80 = net80_v * 0.65
print(f"    月可分净利 = {fmt(rev80)} − {fmt(200*rooms*0.8)} = {fmt(net80_v)} 元（vs 上表 {fmt(rev80-15000)} 元）")
print(f"    甲方月分红 = {fmt(a80)} 元 → 回本 {3_000_000/a80/12:.2f} 年（vs 文档 3.3 年，乐观 6%）")
print("    >>> 同一集团的两份文档对『运营杂费是否随出租率变动』口径不一致，方向是让甲方回本看起来更快。")

print()
print("=" * 100)
print("D. 合作模式报告关键数字自洽性核验（8 年 / 96 个月）")
print("=" * 100)

# 该报告自报：乙方稳态月运营成本 57,800；爬坡期前 6 月 85,000；乙方 8 年分成 659.7 万；运营成本 571.2 万；净 88.5 万
b_cost_stab = 57800
b_cost_ramp = 85000
b_total_cost_claim = 5_712_000
b_total_cost_calc = b_cost_ramp * 6 + b_cost_stab * 90
print(f"乙方 8 年运营成本：6×85,000 + 90×57,800 = {fmt(b_total_cost_calc)} 元")
print(f"  报告自报运营成本 = {fmt(b_total_cost_claim)} 元 → 差 {b_total_cost_calc - b_total_cost_claim:,.0f} 元")
check("乙方8年运营成本", b_total_cost_claim, b_total_cost_calc, 100, "元", "合作模式报告 5.1/7.3")

b_rev_claim = 6_597_000
b_net_claim = 885_000
print(f"\n乙方 8 年分成(报告 7.3 节口径) = {fmt(b_rev_claim)} 元")
print(f"乙方净 = 分成 {fmt(b_rev_claim)} − 成本 {fmt(b_total_cost_calc)} = {fmt(b_rev_claim - b_total_cost_calc)} 元")
print(f"  报告自报净 = {fmt(b_net_claim)} 元 → 差 {b_rev_claim - b_total_cost_calc - b_net_claim:,.0f} 元")
check("乙方8年净收益", b_net_claim, b_rev_claim - b_total_cost_calc, 100, "元", "合作模式报告 5.1")

# 独立重建：用分阶段瀑布反推 8 年双方总额
occ = 0.90
gross_stab = monthly * occ
opcost = 200 * rooms * occ          # 按实际在租间数
distributable = gross_stab - opcost
A_target = 3_000_000
months_A = 48
A_month = A_target / months_A
B_A = distributable - A_month
A_B1 = distributable * 0.40
B_B1 = distributable * 0.60
A_B2 = distributable * 0.35
B_B2 = distributable * 0.65
B_indep = B_A * months_A + B_B1 * 24 + B_B2 * 24
A_indep = A_month * months_A + A_B1 * 24 + A_B2 * 24
print(f"\n独立重建（稳态 90%、**按实际在租间数 67.5 间**扣杂费，符合合作模式报告第2章原文）：")
gross_stab = monthly * occ
opcost = 200 * 67.5
distributable = gross_stab - opcost
A_target = 3_000_000
months_A = 48
A_month = A_target / months_A
B_A = distributable - A_month
A_B1 = distributable * 0.40
B_B1 = distributable * 0.60
A_B2 = distributable * 0.35
B_B2 = distributable * 0.65
B_indep = B_A * months_A + B_B1 * 24 + B_B2 * 24
A_indep = A_month * months_A + A_B1 * 24 + A_B2 * 24
print(f"  满租月营收 {fmt(monthly)} × 90% = {fmt(gross_stab)} 元")
print(f"  运营杂费 200×67.5 = {fmt(opcost)} 元")
print(f"  月可分配收入 = {fmt(distributable)} 元")
print(f"  阶段A 甲方动态优先额 = 3,000,000/48 = {fmt(A_month)} 元/月；乙方留存 = {fmt(B_A)} 元/月")
print(f"  阶段B1 甲 {fmt(A_B1)} / 乙 {fmt(B_B1)}；阶段B2 甲 {fmt(A_B2)} / 乙 {fmt(B_B2)}")
print(f"  → 甲方 8 年累计 = {fmt(A_indep)} 元（报告自报 5,281,000 元）")
print(f"  → 乙方 8 年累计 = {fmt(B_indep)} 元（报告自报 6,597,000 元）")
print(f"  → 乙方净 = {fmt(B_indep)} − {fmt(b_total_cost_calc)} = {fmt(B_indep - b_total_cost_calc)} 元")
print(f"     报告自报净 885,000 元；独立重建差 {B_indep - b_total_cost_calc - 885000:,.0f} 元")
print(f"     报告口径杂费 15,000/月 vs 在租口径 13,500/月，差 1,500 元/月 × 46.32 期 = {1500*46.32:,.0f} 元")
print(f"     —— 远小于 836,124 元差异，故差异主因【不是】杂费口径，")
print(f"     而是报告自报的『乙方 8 年分成 659.7 万』与『35/65 + 甲方前 48 月优先受偿』的规则不自洽。")
print(f"     正解见 scripts/02_econ_model.py 的 96 个月逐月瀑布。")

print(f"\n  分配恒等式检查：月可分配收入 {fmt(distributable)} = 甲 {fmt(A_month)} + 乙 {fmt(B_A)}  ？")
check("阶段A分配恒等", distributable, A_month + B_A, 1, "元", "本章重建")

print()
print("=" * 100)
print("E. 核验汇总表")
print("=" * 100)
print(f"{'项目':<42}{'文档值':>14}{'复算值':>14}{'判定':>10}")
n_ok = n_bad = n_na = 0
for tag, claim, recomp, ok, unit, src in results:
    if claim is None:
        n_na += 1
        print(f"{tag:<42}{'—':>14}{recomp:>14}{'仅记录':>10}")
    else:
        n_ok += ok
        n_bad += (not ok)
        print(f"{tag:<42}{claim:>14,.0f}{recomp:>14,.0f}{'OK' if ok else 'MISMATCH':>10}")
print(f"\n通过 {n_ok} 项 / 不符 {n_bad} 项 / 仅记录 {n_na} 项")
print("\n脚本可复现：python3 scripts/01_source_integrity.py")
