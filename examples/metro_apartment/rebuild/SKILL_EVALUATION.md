# 技能评估 · rebuild-strategist 实测报告

**实测项目**：本市地铁公寓项目（P 路 98 号，75 间长租公寓）
**模式**：`GROWTH_DIAGNOSIS`（result → funnel → unit economics）
**实测日期**：2026-10-12
**执行方式**：单 agent，无委派（受权限限制，见 §5 困难 D1）

---

## 1. 技能的单位经济定义是否真的约束了我的计算？

**结论：部分约束。它约束了"怎么称呼"，没有约束"怎么算"。真正拦住我的是我自己补的控制权矩阵，不是技能。**

### 1.1 有用的部分（确实改变了我的输出）

| 技能条款 | 实际发生的作用 | 是否本来就会做 |
|---|---|---|
| `CAC = attributable acquisition spend ÷ new customers in one cohort and window`（SKILL.md §6） | 强制我**声明成本口径**。我最终输出了 4 个 CAC（3,810 / 2,857 / 1,714 / 4,762）。若不声明，我会只报一个数 | **否，这条有用**。同一笔 40 万预算在四口径下跨越 4,500 红线，这个发现完全依赖"必须声明口径"这一要求 |
| `ROAS = attributed revenue ÷ ad spend, **not profit ROI**；ROI = (incremental profit − investment) ÷ investment`（SKILL.md §6） | 文档宣称"回本 1.9 年"是把**现金流**当**利润**用。技能的 ROI 定义直接指出这是错的 | **否，这条抓住了真错**。文档用「300万 ÷ 全额可分净利 135,000」= 22.2 月，未扣乙方分成，属现金流口径冒充 ROI |
| `Payback = time until cumulative contribution covers acquisition cost`（MARKETING_OS.md:26） | 我照此算了获客回本；但项目的真实回本问题是 300 万装修资本回收，**该定义不覆盖** | **是，但定义不够用**（见 1.2） |
| `outcome / diagnostic / activity / guardrail` 四分类 | 强制我把"出租率"归为 driver 而非 outcome，把 CAC 归为 diagnostic 而非收入结果 | **否，这条有用**。文档第七章把 CAC、出租率、均价、回本周期混在一张"KPI 体系总表"里，四分类一压就暴露出它们不是同一层的指标 |
| `Never claim causal lift from platform-attributed conversions alone` | 我把三个实验全部标注"仅方向性证据，不得宣称因果" | 是，但这条被**写了 3 遍**（SKILL.md §6、OPERATING_RULES §Marketing economics、MARKETING_OS §Attribution） |

### 1.2 不够用的部分（我不得不自己补）

**缺口 A：Payback 的定义主体只有"acquisition cost"，没有"capital investment"。**
`MARKETING_OS.md:26` 与 `SKILL.md §6` 都把 payback 绑定在"acquired customers"上。本项目有两笔完全不同的投入：
- 甲方：300 万装修资本 → 用「300万 ÷ 月度分红」算回收
- 乙方：100 万履约押金（期满退还）+ 运营团队 → 用「押金多久被烧穿」算

技能没有任何条款告诉我这两个数不能混用。**是我自己发现文档把甲方的 1.9 年用在了整个项目上。** 建议在 §6 补一句：`Payback must name the payer and the capital base; a payback figure computed on one party's capital must never be quoted for another party or for the project as a whole.`

**缺口 B：技能没有任何应对"多主体合作"的单位经济条款。**
我系统性 grep 了技能包：`OPERATING_RULES.md` 的 §Economics 与 `MARKETING_OS.md` 通篇是单一主体的 CAC/LTV/ROAS/ROI。但本项目是**甲乙分成制**，核心问题是"同一笔租金在两套账里各算多少"。技能里唯一相关的是：

> **Complex projects — place, park, platform, city, real estate**：For place-based, platform, park, city, real-estate and multi-party projects … Add all five of: **Stakeholder structure / Resource flow / Value flow / Cash flow / Governance**（OPERATING_RULES.md:44-55）

**这是技能里最有价值的一条，也是本次诊断的核心工具。** 我据此建了"控制权矩阵"（谁出资、谁承担、谁扣减），它直接暴露了：
- 两份文档对"200 元/间·月运营杂费归谁"口径相反
- 四份文档对"回本周期"给了 1.9 / 2.4–2.8 / 2.6–3.3 / ≤2.5 年四套数
- 乙方在 60%–93% 出租率全区间月度现金流为负

**但它藏在 `OPERATING_RULES.md` 的中段，且只列了 5 个问题的名字，没有任何模板、字段或算例。** 我是读到第 44 行才发现的。建议把它提升为 §6 Economics 的一个子节，并配一个最小模板。

**缺口 C：没有"分母口径"的强制声明要求。**
本项目最尖锐的合规问题就是分母：`89.7 元/㎡·月` 是用「单间建面加总 1,824 ㎡」算的；用「总建筑面积 2,751.34 ㎡」算是 `59.47 元/㎡·月`，差 34%。技能只对 CAC/LTV 要求声明口径，对"单位面积租金""每间成本"这类**行业惯用的比率指标**没有要求。建议把"declared cost scope"的原则从 CAC 泛化到所有比率型指标。

---

## 2. 「区分运营方口径与甲方口径」这一条有价值吗？

**结论：极有价值，是本次诊断唯一真正的分析杠杆。但技能里根本没有这一条 —— 是我从 `OPERATING_RULES.md:44-55` 的五个问题自己推出来的。**

### 2.1 它带来了什么

如果只有一套口径，我会得到这样的结论："项目出租率 90% 时甲方年分红 102 万，回本 2.9 年，可行。"——**这是错的，而且错得看不出来。**

区分口径后暴露的事实：

| 发现 | 数值 | 只做单口径能否发现 |
|---|---|---|
| 乙方单间月收入（分成口径） | **681 元/间·月** | ❌ 不能 |
| 乙方单间月成本（区间） | **771 – 1,513 元/间·月** | ❌ 不能 |
| 结构性缺口 | 乙方在 60%–93% 出租率**全区间**月现金流为负 | ❌ 不能 |
| 甲方 48 月回本要求分成 ≥50%；乙方保本要求甲方分成 ≤31.1% | **交集为空** | ❌ 不能 |
| 押金被侵蚀时点 | 17–23 个月（远早于 8 年合同期） | ❌ 不能 |

**这一条把一个"营销诊断"变成了"合作条款诊断"。** 如果技能要我评估"40 万预算怎么花"，我会交出一份漂亮的渠道方案；因为强制分口径，我交出的结论是"先别签这份合同"。

### 2.2 但它执行得不够

技能的表述是"甲方/乙方"视角吗？不是。技能里出现的都是 `operator` / `customer` / `business`，从未出现"出资方/运营方"这种**同一交易中两个资本主体**的划分。我实际用的是：

- 甲方 = 300 万装修资本出资方，回报 = 月度分红，风险 = 回本周期
- 乙方 = 100 万押金 + 运营能力，回报 = 分成收入，风险 = 押金被烧穿

**这两个主体的最优决策方向相反**：甲方要分成比例高，乙方要分成比例低（甲方让利多）。技能的经济学章节默认"主体"是单一的，无法表达这种对立。建议在 §6 增加：`When value is split between two capital-bearing parties, compute unit economics twice, name each party's capital base and horizon, and state explicitly where their interests diverge. If the two break-even conditions have no intersection, the deal structure — not the marketing plan — is the binding constraint.`

---

## 3. 哪些规则空洞、啰嗦、或互相矛盾？

### 3.1 空洞（说了等于没说）

| 条款 | 问题 |
|---|---|
| `Payback = time until cumulative contribution covers acquisition cost` | 只覆盖获客场景；本项目核心回本问题（资本回收）落在定义之外 |
| `Sibling file to project_state.schema.json, stored at .rebuild/kpi/kpi_tree.json under the split-files convention`（kpi_tree.schema.json:5） | 但任务要求写到别处；技能没有任何"遵循调用方路径约定"的条款，schema 描述里却写死了路径 |
| `resource flow / value flow / cash flow`（OPERATING_RULES:44-55） | 只有名词，无定义、无模板、无判据。我花了不少时间才想清楚"resource flow"与"value flow"的区别，最后合并处理 |
| §3 Orchestration 的 10 字段返回契约（`summary/findings/evidence/assumptions/unknowns/recommendation/confidence/dependencies/risks/next_actions`） | 与 `task_packet.schema.json`、`project_state.schema.json` 的字段**不互通**，也无映射表。对单 agent 执行完全无用 |
| `AI widens the search space; humans narrow the decision space` | 正确的废话。可操作版本是"提案保持 proposed 直到人工批准"——而这条在 §10 已单独出现 |

### 3.2 啰嗦（同一规则重复 3–7 次）

实测 grep 结果：

| 规则 | 出现次数 | 位置 |
|---|---|---|
| incrementality / 归因不等于因果 | **7** | SKILL.md §6、OPERATING_RULES §Marketing economics、MARKETING_OS §Attribution、…… |
| ROAS 定义 | **7** | 同上 |
| payback 定义 | **7** | 同上 |
| allowable CAC / 不用通用基准 | **6** | SKILL.md §6、OPERATING_RULES §Marketing economics、MARKETING_OS §Metric definitions |
| LTV:CAC 口径一致 | **4** | 同上 |
| attributed conversions 不可声称因果 | **3** | 同上 |

**同一套定义在 `SKILL.md §6`、`OPERATING_RULES.md §Marketing economics`、`MARKETING_OS.md §Metric definitions` 三处各写一遍，措辞略有差异**：

- SKILL.md:44 `CAC = attributable acquisition spend ÷ new customers in one cohort and window.`
- MARKETING_OS.md:21 `CAC = acquisition cost under a declared cost scope / new customers in a declared cohort and window.`
- OPERATING_RULES.md:187 `CAC = attributable acquisition spend ÷ new customers, same cohort and window; declare whether spend is media only or includes agency, creative, sales labour, discounts, tooling.`

三处**不一致**（`attributable acquisition spend` vs `acquisition cost under a declared cost scope`）。我最终以 OPERATING_RULES 那版为准，因为它最具体。**权威来源不明是真实成本**：任何复核者都会问"以哪一版为准"。

### 3.3 互相矛盾

| # | 矛盾 | 位置 | 后果 |
|---|---|---|---|
| **C1** | 状态文件既说写 `.rebuild/state.json`（OPERATING_RULES:142-145、DSH_ADAPTER:35-44），又说按 `storage_convention` 可以是 single-file 或 split-files（project_state.schema.json:5,24） | 两处 | 无法判断哪个是规范 |
| **C2** | `specialists never approve budget, publish, contact customers or change production systems`（OPERATING_RULES:183）vs §Safety 已有的"human approves commitments"（SKILL.md §8） | 两处 | 纯重复，且把"专家不得批准"与"人必须批准"混为一谈 |
| **C3** | `Never produce slides in place of a decision`（§11）vs §3 要求返回 10 字段结构化契约 | 两处 | 输出形态指引方向相反（叙事 vs 结构） |
| **C4** | `at most five headline findings`（OPERATING_RULES:171）vs 要求"诊断要有 outcome→driver→diagnostic→guardrail 四层树" | 两处 | 五条发现装不下四层树，实操中必然违反其一 |

### 3.4 最严重的一处矛盾（不是文字上的，是效果上的）

技能**要求实验必须预设功效**：

> `If statistical power cannot be justified, report the test as directional rather than conclusive.`（MARKETING_OS.md:48）

但技能**从不检查样本量是否可能支撑任何实验**。本项目 75 间房源、6 个月签约 66 间、全期 900 组看房 —— 我实测：

- 房间级 RCT（37 间/臂）：只能检测 **±28 个百分点**的差异
- 看房者级 RCT（450 组/臂）：只能检测**相对 +76%** 的渠道差异
- 要检测渠道相对 +30% 的差异，需 **2,479 组/臂** = 全期看房量 KPI 的 **5.5 倍**

**技能让作者"声明功效不足"，却没有教作者"在功效不足时该做什么设计"。** 它把责任推给一句 `report as directional`，然后就没有下文了。三个实验我全部标为方向性（`power_analysis.json` 可复核），但这是我自己的判断，不是技能的指引。建议补：`When unit count or traffic caps the design, prefer upstream or continuous primary metrics (willingness-to-pay, cost per qualified visit), paired/within-subject designs, and staggered rollout — and state the minimum effect the design can detect before launch.`

---

## 4. 使用中遇到什么困难？schema 好不好用？字段够不够用？挡不挡得住垃圾？

### 4.1 schema 挡不住垃圾 —— 有实测证据

我用对抗测试跑了两组"结构合法、语义垃圾"的数据（`scripts/06_schema_redteam.py`）：

**KPI schema：放过 10/10 条**

| 垃圾类型 | 为什么 schema 挡不住 |
|---|---|
| 定义只复述指标名（`出租率 = "出租率"`） | `definition` 只约束 `type: string`，无最小长度、无关键词要求 |
| 分母未定义（`"把转化率提上去，越高越好"`） | 同上 |
| `outcome` 无 `target`、无 `baseline` | 二者**都不在 required 里** |
| `guardrail` 不设阈值 | `guardrail_threshold` **不在 required 里** —— 不设阈值的护栏等于装饰 |
| `source_of_truth = "系统"` | 无枚举、无格式约束 |
| `owner = "项目组"` | 无枚举、无人员引用 |
| `period = "随时"` | 无枚举、无格式约束（注释里只举了 `monthly` / `28-day rolling` 为例） |
| 父子节点同一指标循环定义 | 无唯一性检查 |
| `target = "大幅提升"` | 无格式约束 |
| `activity` 冒充 `outcome`（曝光量标为 outcome） | 枚举值合法即可，无内容校验 |

**Experiment schema：放过 8/8 条**

| 垃圾类型 | 为什么 schema 挡不住 |
|---|---|
| `decision_rule = "到时候再看"` | `decision_rule` 只要求是字符串；**技能正文要求"事先约定 pass/fail"，schema 完全没有对应约束** |
| 无 `control` 却 `status=complete` + `result="证明新渠道有效"` | `control` **不在 required 里** —— 有因果声称却无对照，schema 放行 |
| `primary_metric = "曝光量"` | 无类型校验，技能明令禁止的 activity 指标照样通过 |
| `minimum_detectable_effect = "看情况，样本够了自然能看出来"` | 纯字符串 |
| `sample_logic = "先跑一个月看看"` | 纯字符串 |
| 因果句 hypothesis + 无 `control` + `status=running` | 同上 |
| `status=complete` 但无 `result` | 无交叉约束 |
| `guardrails = []`（空数组） | `required` 只要求字段存在，**空数组合法** |

**判断：两个 schema 都是结构校验器，不是质量校验器。** 技能正文（§6、MARKETING_OS、OPERATING_RULES）反复强调的这些要求，一条都没有变成机器可判的约束。**结果是"遵守技能"完全依赖写作者自觉 —— 而这恰恰是技能想要避免的。**

### 4.2 字段缺什么（按我实际卡住的顺序）

**`kpi_tree.schema.json`：**

1. **缺 `status`** —— 无法区分"这是实测基线"还是"这是目标"。我把两者都塞进 `baseline` 字符串（写"无（未开业）"），语义就丢了。
2. **缺 `evidence_grade`** —— 技能在 §4 强制 A–E 分级，`evidence.schema.json` 有 `quality_grade`，**但 KPI 树没有**。我的每个 KPI 都有分级（文档给定 A / 本模型补 D），却无处安放，只能写进 `limitations` 的自由文本。**这是最该补的字段。**
3. **缺 `data_lag` / `refresh`** —— 无法表达"这个指标滞后 30 天才可信"。本项目里"签约均价"当月可知，"回本进度"要等分红到账。
4. **缺 `conflict` / `contradiction`** —— 我发现了三处源文档矛盾（分成比例、均价目标、回本周期），没有地方结构化记录，只能塞进 `limitations`。
5. **缺 `unmeasurable`** —— 有些指标结构上不可测（本项目：真实增量性、竞品实际成交价），schema 逼我或者不写、或者写一个假定义。
6. **`guardrail_threshold` 可选** —— 应改为：`metric_type == "guardrail"` 时必填。
7. **`target` 对 outcome/driver 可选** —— 应改为必填。

**`experiment.schema.json`：**

1. **`control` 可选** —— 应为：`status ∈ {running, complete}` 时必填。**这是最硬的漏洞：可以合法地写出"无对照却声称因果"的实验卡。**
2. **缺 `owner`** —— 实验没有人负责。技能 §12 自检问"Owners, timing, budget and dependencies real rather than decorative?"，schema 却不给 owner 字段。
3. **缺 `cost` / `budget`** —— 无法表达"这个实验本身要花多少钱"，而技能要求"stop-loss 规则"。
4. **缺 `power_basis`** —— `minimum_detectable_effect` 是纯字符串，无法区分"实测功效"与"拍脑袋写的数"。建议加 `power_analysis: {alpha, power, baseline, n_per_arm, method}` 子对象。
5. **缺 `result_status`** —— `status=complete` 但无 `result` 是合法的。
6. **缺 `primary_metric_type`** —— 无法机器拒绝 activity 冒充 primary metric。
7. **`guardrails` 允许空数组** —— 应加 `minItems: 1`。
8. **`decision_rule` 无结构** —— 技能要求三分支（通过/失败/不确定），schema 是自由字符串。我的实测：3 个实验我都手写了三分支，但对抗测试证明写"到时候再看"同样合法。

### 4.3 schema 本身的一处内部矛盾

`kpi_tree.schema.json:5` 的 description 写死路径 `.rebuild/kpi/kpi_tree.json`，而 `project_state.schema.json:5,24` 说可以是 `single-file` 或 `split-files` 两种约定。**同一技能包里两个 schema 对存储路径的说法不一致。**

---

## 5. 使用中遇到的其他困难

| # | 困难 | 影响 |
|---|---|---|
| **D1** | 本会话为受限子 agent：审批提示被禁用，`sandbox_permissions` 一律被拒；技能 §3 却推荐用 `subagent` / `workflow` 委派 | 无法按技能建议做角色分工（财务/市场/KPI 专员），只能单 agent 顺序执行。技能对"无委派能力时怎么办"只有一句"label it simulated role separation"，没有任何降级指引 |
| **D2** | 任务要求写到 `<案例目录>/rebuild/`，技能 `OPERATING_RULES:141-146` 要求写 `<workspace>/.rebuild/…` | 直接冲突。我按任务要求写，但这意味着**产出不符合技能的状态约定**，技能下次续跑会找不到状态文件。技能缺"调用方路径优先"条款 |
| **D3** | 技能 §10 要求把项目状态写入 `state.json`（走 `project_state.schema.json`），但该 schema 有 **18KB / 大量嵌套必填** | 在单次诊断任务里，完整填写 state.json 的成本高于收益。我最终没写，这也意味着**这次诊断不是"可续跑"的** —— 技能对"轻量模式"没有定义 |
| **D4** | 技能没有"文档间互相矛盾时怎么办"的条款 | 我发现三处实质矛盾（分成 65% vs 35%、均价 2,182 vs 2,300、回本 1.9 vs 2.4–2.8 vs ≤2.5 年），技能只说"never average conflicting claims"（§3），但没说该怎么呈现。我自己发明了"控制权矩阵 + 源文档算术核验脚本" |
| **D5** | `resources/` 有 12 个 md + 13 个 agent 契约 + 5 个 schema，SKILL.md §9 只给了一句话索引 | 我实际只读了 OPERATING_RULES / MARKETING_OS / 4 个 schema。**没有读到的（WORKSHEETS 34 张表、ANALYTIC_FRAMEWORKS、QUALITY_GATES）可能有用，但索引不足以判断该不该读**。建议每个资源加一行"何时该读" |

---

## 6. 我会继续用吗？

**会，但只保留其中三样。**

### 保留（不可替代）

1. **`outcome / driver / diagnostic / activity / guardrail` 五分类** —— 这是技能里最实用的单一工具。它一压就把文档第七章的"KPI 体系总表"压出了层级错误。
2. **`FACT / INTERPRETATION / HYPOTHESIS / DECISION / UNKNOWN` + `A–E` 分级** —— 强制我把"文档给定的"与"我补的"分开，并给补齐项标敏感区间。本次所有补齐假设（人力 45,000、押金成本率 6%、换租率 30%）都带区间，这是这套标签的直接产物。
3. **`OPERATING_RULES:44-55` 的 place/platform/multi-party 五问** —— 本次诊断的分析杠杆。建议提升权重。

### 不保留（或需要大改）

1. **`resources/agents/` 的 13 个角色契约** —— 单 agent 场景下是纯负担。
2. **同一套定义的三处重复** —— 应指定唯一权威来源（建议 `MARKETING_OS.md §Metric definitions`），其余改为引用。
3. **`project_state.schema.json`（18KB）** —— 对单次诊断任务过重；需要一个 `state.lite.schema.json`。
4. **两个质量 schema（`kpi_tree` / `experiment`）** —— 结构没问题，但缺关键约束（见 §4.2）。**目前的实际效果是"看起来有规范，实际写什么都能过"** —— 这比没有 schema 更危险，因为它制造虚假的合规感。

---

## 7. 改进建议（按重要性排序）

| 优先级 | 建议 | 具体做法 | 解决什么 |
|---|---|---|---|
| **P0** | **给 experiment schema 加机器可判的硬约束** | `control` 在 `status ∈ {running, complete}` 时必填；`guardrails` 加 `minItems: 1`；`decision_rule` 改为对象 `{pass, fail, inconclusive}` 三必填字段；`minimum_detectable_effect` 改为对象 `{value, alpha, power, baseline, n_per_arm, method}` | 直接堵住"无对照声称因果""decision_rule 写空话""MDE 写空话"三类垃圾（对抗测试 B1/B2/B4/B8） |
| **P0** | **给 kpi_tree schema 加同样的硬约束** | `metric_type == "guardrail"` 时 `guardrail_threshold` 必填；`metric_type ∈ {outcome, driver}` 时 `target` 必填；`definition` 加 `minLength: 30` 并用 pattern 要求包含"分子"或"分母"字样；`primary_metric` 类字段禁止 `activity` 值 | 堵住 KPI 垃圾 A1–A4、A9、A10 |
| **P0** | **补 `evidence_grade` 到 kpi_tree 与 experiment 的每个节点/卡片** | 复用 `evidence.schema.json` 的 `quality_grade` 枚举 | 技能 §4 强制分级，但这两个 schema 无处安放，导致分级只存在于自由文本 |
| **P1** | **把 `OPERATING_RULES:44-55` 的多主体五问提升为 §6 Economics 的正式子节，并配模板** | 给出"控制权矩阵"最小字段集：科目 / 资金来源 / 承担方 / 依据 | 本次诊断的核心工具目前在文档中段、只有一句名词列表 |
| **P1** | **在 §6 补 payback 的资本主体要求** | `Payback must name the payer and the capital base. A payback computed on one party's capital must never be quoted for another party or the project as a whole.` | 文档把甲方 1.9 年用在整个项目上，技能无法识别这是错的 |
| **P1** | **把"声明口径"从 CAC/LTV 泛化到所有比率型指标** | 加一条：`Any ratio metric (per unit, per sqm, per room, per visit) must declare its denominator and its unit basis in the metric definition itself.` | 89.7 vs 59.47 元/㎡·月的分母歧义，是本项目最尖锐的合规风险 |
| **P2** | **指定单位经济定义的唯一权威来源，其余改为引用** | 保留 `MARKETING_OS.md §Metric definitions` 为唯一全文，SKILL.md §6 与 OPERATING_RULES §Marketing economics 改为指针 | 消除三处措辞不一致（`attributable acquisition spend` vs `acquisition cost under a declared cost scope`） |
| **P2** | **补"文档互相矛盾时怎么办"的操作条款** | 建议：`When supplied documents contradict each other on a material number, do not reconcile by averaging. Build an arithmetic verification pass that recomputes every claim that is recomputable, publish a pass/fail table, and identify which variant each downstream number depends on.` | 我发现三处实质矛盾，技能只说不许平均，没给替代做法 |
| **P2** | **补"功效不足时的设计菜单"** | 上游指标 / 连续型主指标 / 配对设计 / 交错投放，并要求在启动前写出"本设计能检测的最小效应" | 技能要求声明功效不足，但不给替代设计；本项目的 900 组看房量根本支撑不了任何 RCT |
| **P3** | **给 `resources/` 每个文件加一行"何时该读"** | 在 §9 的资源索引里补 `when_to_read` | 我漏读了 WORKSHEETS（34 张表）、QUALITY_GATES、ANALYTIC_FRAMEWORKS，因为索引不足以判断相关性 |
| **P3** | **提供 `state.lite.schema.json`** | 仅含 task / gate_status / decisions / assumptions / open_questions 五段 | 18KB 的完整 state schema 让轻量任务直接放弃写状态，导致不可续跑 |
| **P3** | **明确"调用方路径约定优先于技能默认路径"** | 在 §10 加一句 | 任务要求与技能 `OPERATING_RULES:141-146` 直接冲突 |
| **P3** | **删除或降级冗余条款** | `specialists never approve budget…`（与 §Safety 重复）；`AI widens the search space…`（正确的废话）；`Never produce slides in place of a decision`（与 §3 结构化契约冲突） | 减少阅读负担与自相矛盾 |

---

## 8. 一句话总结

**技能最有价值的不是它写了什么定义，而是它逼我做了什么动作** —— 分口径、标证据等级、把 outcome 与 diagnostic 分开。但它把这些要求写成了**散文式规范**而不是**可校验约束**：实测 KPI schema 放过 10/10 条语义垃圾，experiment schema 放过 8/8 条，包括"无对照却声称因果"这种技能正文明令禁止的情况。

**最该改的一件事**：把技能正文里那些"必须"，变成 schema 里机器能拒绝的约束。否则技能的合规感是假的。
