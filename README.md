# REBUILD Strategist

**一套原创的、以决策为中心的品牌营销方法论操作系统。**

大多数营销 prompt 和模板工具解决的是「怎么写出一份看起来像咨询报告的文档」。
REBUILD 解决的是另一个问题：**你怎么知道这份报告里的结论值得相信，以及它值得被花多少钱去执行。**

它不追求产出更长的报告，而强制回答四个问题：

1. 现在真正需要做出的是什么决定？
2. 哪些是事实，哪些是推断，哪些只是假设？
3. 为此放弃了什么，代价是什么？
4. 什么证据出现时，应当推翻这个决定？

## 六阶段决策循环

```text
R  Reality             界定现实     什么问题、症状与决策分别是什么
E  Evidence            建立证据     每条判断标记 FACT/INFERENCE/ASSUMPTION/UNKNOWN
B  Bet                 战略下注     2–4 个实质不同的选项，显式取舍
U  Unit Economics      商业成立性   收入≠利润，ROAS≠贡献利润，口径必须可复算
I  Implementation      执行与观测   每项行动绑定负责人、成本、指标与停止条件
D  Decision Review     决策复盘     区分执行偏差、策略偏差与假设偏差
                         ▲                    │
                         └──── 假设被证伪 ─────┘
```

关键在于：它是一个**带回退的循环**，不是一条单向流水线。证据不足退回 Evidence，单位经济不成立退回 Strategy，假设被反证退回受影响的决策阶段——而不是在报告末尾加一段风险提示了事。

## 三条硬约束

**证据必须可追溯。** 每条关键判断标注四类之一：
`FACT`（可核验来源）、`INFERENCE`（须写明推理桥梁）、`ASSUMPTION`（暂定前提）、`UNKNOWN`（信息不足）。
可信度分 HIGH / MEDIUM / LOW，**不以模型语气作为证据**。

**取舍必须显式。** 每个战略建议至少包含一个备选方案、放弃项、代价与成立条件。
说不清放弃什么，说明还没想清楚选择。

**财务口径必须可复算。** 每个指标写清公式、分子分母、时间范围与数据来源。
LTV 不标观察窗口即无效，CAC 不区分渠道/全口径/增量口径即无效。

## 角色分工

主 Agent 负责编排与门禁，8 个职能角色各有独立的使命、输入边界、专属追问清单与失败模式：

| 角色 | 核心问题 |
|---|---|
| Customer Evidence | 需求是否真实存在，由谁在什么情境下发生 |
| Market Structure | 生意处于什么结构里，凭借什么进入 |
| Positioning & Strategy | 在客户心里占什么位置，为此放弃什么 |
| Business Model | 财务上是否成立，多久回本，何时会崩 |
| Growth System | 通过什么机制获得可重复的获客 |
| Measurement & Experiment | 怎么知道成了，怎么知道该停 |
| Red Team | 什么证据能推翻当前选择 |
| Learning & Review | 实际发生了什么，假设如何更新 |

角色之间有明确的越权拒绝机制——例如 Market Structure 拒绝回答需求强度，Business Model 拒绝提出定位主张。

## 快速验证

需要 Python 3.10+，**无任何第三方依赖**。

```bash
git clone https://github.com/<your-account>/rebuild-strategist.git
cd rebuild-strategist

# 单元测试（5 项）
python -m unittest discover -s tests -v

# 项目状态校验
python core/rebuild_cli.py validate examples/nanjiang_tea/project.json

# 确定性状态迁移
python core/rebuild_cli.py transition --state DISCOVER --event evidence_ready
```

状态机由 7 个状态与明确的回退迁移构成，见 `core/state_machine.json`。
门禁不通过时，系统允许停留、补证或降级输出——**不以「完成所有表格」为成功标准**。

## 成熟度声明

这一节是本项目最重要的部分，请认真读。

**已实现并通过测试**
- 原创方法论与阶段门禁（已文档化）
- 确定性状态机：7 状态 / 合法与回退迁移
- 项目 JSON 校验 CLI
- 5 份数据 Schema：项目、证据、决策、实验、KPI 树
- 8 个角色的完整契约
- 单元测试（14 项，Python 3.10–3.13）
- 盲评实验脚手架：编号散列、身份隐藏、评审一致性检查
- 基准用例与 32 分评分量表

**未实现**
- 模型调用与多 Agent 运行时调度
- 项目持久化与决策历史版本
- 营销数据接入
- DeepSeek Harness 端到端集成

**未验证**
- 在任何宿主中的端到端运行效果
- 与单 Agent / 基础提示词的质量对照
- 真实商业项目中的 ROI 改善

> `agents/*.md` 中的角色是**方法论契约**，不是运行时的 Agent 实例。
> 提示词里写了子 Agent，不等于运行时创建了子 Agent。
> 这个区分是刻意的，因为我们认为把提示词包装成已交付的能力是行业里最常见的一种自欺。

## 原创性边界

本仓库中的阶段模型、决策记录协议、证据等级体系、阶段门禁、角色契约、反证机制、评测规程与状态机均为原创设计。

不声称营销理论史上绝对无人提出过类似概念。原创性应以**具体实现、独立文档、版本历史和可复现实验**来建立，而不是靠「世界首创」的宣传。如果你发现实质相似的方法论，欢迎提 Issue 讨论——这会让这个项目更可信。

不内置 n8n、PostHog、Mautic 等第三方营销项目。宿主（如 DeepSeek Harness）是运行环境，不是方法论来源，适配层不得重新定义 REBUILD 策略。

## 评测

`bench/` 提供四个固定基准用例、32 分八项量表，以及一套**防止自欺的盲评脚手架**。

其中**诚实性得 0 分即判定样本失败**，不以总分抵消。

```bash
python bench/bench_runner.py generate --runs 3    # 生成盲评清单
python bench/bench_runner.py template             # 空白评分表
python bench/bench_runner.py import r1.csv r2.csv  # 合并评审
python bench/bench_runner.py reveal               # 揭示身份（需 ≥2 名评审）
python bench/bench_runner.py summarise            # 汇总并检查门槛
```

脚手架强制执行：编号由 SHA-256 散列生成且同配置每次运行不同、呈现顺序打乱、评审看不到配置身份、少于两名评审或任一评审未覆盖全部条目时拒绝揭示、两名评审分差超 6 分时提示复核。

操作手册见 `bench/HOWTO.md`，评审规程见 `bench/REVIEW_PROTOCOL.md`。

**当前 scorecard 为空。** 这意味着本项目尚未公布任何对照实验结果。评测框架已就绪，但数据要等真实运行之后才有——在那之前，本项目不会声称自己在质量上优于任何方案。

## 目录

```text
core/            方法论、状态机、决策协议、CLI
agents/          主 Agent 与 8 个职能角色契约
schemas/         项目、证据、决策、实验、KPI 数据结构
bench/           基准用例、评分量表、盲评脚手架、评审规程
examples/        案例框架（不含未经验证的项目数据）
harness/         宿主接入说明与 Skill 文件
tests/           单元测试与静态检查清单
docs/            状态与路线图
```

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。核心要求：
新增战略规则必须说明它**影响的决策、适用边界和失败条件**；
新增案例必须标注真实/合成/匿名化属性；
未运行的测试不得标记为通过。

行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，安全报告见 [SECURITY.md](SECURITY.md)。

## 许可证

[MIT License](LICENSE)。许可证仅适用于发布者有权授权的仓库内容；REBUILD 名称、标识及未获授权的第三方素材不因本许可证而自动获得使用许可。
