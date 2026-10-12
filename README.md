# REBUILD Strategist

**一套原创的、以决策为中心的品牌营销方法论操作系统。**

大多数营销 prompt 和模板工具解决的是「怎么写出一份看起来像咨询报告的文档」。
REBUILD 解决的是另一个问题：**你怎么知道这份报告里的结论值得相信，以及它值得被花多少钱去执行。**

它不追求产出更长的报告，而强制回答四个问题：

1. 现在真正需要做出的是什么决定？
2. 哪些是事实，哪些是推断，哪些只是假设？
3. 为此放弃了什么，代价是什么？
4. 什么证据出现时，应当推翻这个决定？

## 这个项目不是什么

在说它能做什么之前，先划清边界。一个把「不夸大」当卖点的项目，最不该在自我介绍里含糊。

| 它不是 | 原因 |
|---|---|
| **不是投放 / CRM / 分析工具** | 不连接任何营销数据平台，不发送广告，不管理客户，不采集用户行为。这些事请继续用你现有的平台做。 |
| **不是自动化执行系统** | 它不替你执行任何营销动作。产出是决策与验证方案，落地仍然靠人。 |
| **不是开箱即用的多 Agent 运行时** | `agents/` 下是**方法论契约**（Markdown），不是运行中的 Agent 实例。目前没有编排器把它们真正跑起来。 |
| **不是数据接入层** | 没有任何数据源连接器。你的证据需要以文本方式自行提供。 |
| **不保证结论正确** | 它约束的是论证过程是否诚实、可追溯、可证伪，不是结论本身是否正确。 |

**它的商业价值目前是假设，不是结论。** 可能的方向包括咨询交付、企业内训、以及作为评测层（对已有营销方案或 AI 输出做结构化审查）。**这三个方向均未被任何真实项目验证，本仓库不为它们背书。**

目前**已被验证**的只有三件事：方法论自洽、状态机确定性、评测脚手架可端到端运行。其余全部是待验证假设。

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
git clone https://github.com/Pacino101/rebuild-strategist.git
cd rebuild-strategist

# 单元测试（28 项）
python -m unittest discover -s tests -v

# 项目状态校验
python core/rebuild_cli.py validate examples/nanjiang_tea/project.json

# 确定性状态迁移
python core/rebuild_cli.py transition --state DISCOVER --event evidence_ready
```

状态机由 7 个状态与明确的回退迁移构成，见 `core/state_machine.json`。
门禁不通过时，系统允许停留、补证或降级输出——**不以「完成所有表格」为成功标准**。

## 接入你自己的模型

`bench/provider.py` 是一个**可插拔的模型接入层**，纯标准库实现，不需要 `pip install` 任何东西。两种运行方式：

**手动模式（默认）** —— 零配置、**零网络请求**。渲染提示词，你自行粘贴到任意聊天窗口，再把输出贴回来。适合资料不能外发的场景。

**HTTP 模式** —— 直接调用模型 API：

```bash
python bench/provider.py list                      # 查看所有预设
python bench/provider.py check deepseek            # 预检 base_url / model / 密钥

export DEEPSEEK_API_KEY=sk-xxx
python bench/provider.py call deepseek --prompt-file prompt.txt
```

内置预设：`openai` · `deepseek` · `moonshot` · `qwen` · `anthropic` · `ollama`（本地模型）· `custom`。

**接任意 OpenAI 兼容端点**（自建代理、其他国产模型、本地推理服务都适用）：

```bash
python bench/provider.py call custom \
    --base-url https://your-endpoint/v1 \
    --model your-model \
    --api-key-env YOUR_KEY
```

**让盲评实验直接跑在你的模型上**：

```bash
python bench/bench_runner.py execute --provider deepseek
```

**如何扩展**：在 `provider.py` 的 `PROVIDER_PRESETS` 里加一条字典即可（字段 `label` / `api_style` / `base_url` / `model` / `api_key_env`）；需要自定义请求头时用 `ProviderConfig.extra_headers`。目前实现两种协议：`openai`（`/chat/completions`）与 `anthropic`（`/messages`）。

> ⚠️ **密钥只从环境变量读取**，不落盘、不进仓库。一旦使用 HTTP 模式，提示词内容会发送到你所指定的端点——涉及客户资料或商业机密时，请改用手动模式或本地模型。

> **注意**：该接入层目前只服务于 `bench/` 评测流程。**REBUILD 方法论本身没有运行时**——`agents/` 下是契约文档，不存在把它们串起来执行的编排器（见上方「这个项目不是什么」）。

## 成熟度声明

这一节是本项目最重要的部分，请认真读。

**已实现并通过测试**
- 原创方法论与阶段门禁（已文档化）
- 确定性状态机：7 状态 / 合法与回退迁移
- 项目 JSON 校验 CLI
- 5 份数据 Schema 的规范定义：项目、证据、决策、实验、KPI 树
- 8 个角色的完整契约
- 单元测试（28 项，Python 3.10–3.13）
- 盲评实验脚手架：编号散列、身份隐藏、评审一致性检查、拒绝不足两名评审与不完整覆盖
- 模型 Provider 接入层（OpenAI 兼容 / Anthropic 兼容两种调用方式）
- scorecard 结构校验：总分与分项一致性、取值域、必填字段
- 基准用例与 32 分评分量表
- 一轮先导实验（1/4 用例，样本不足，见 `bench/PILOT_B03.md`）

**未实现**
- **JSON Schema 的实际校验** —— 5 份 Schema 目前只是规范文件，**没有任何代码读取它们**。CLI 只对 `project.json` 做手写的字段存在性检查。这意味着 Schema 与实际校验之间存在缺口。
- **证据账本** —— 方法论的核心产物是「可追溯的证据账本」，但目前**没有录入与读取路径**：`evidence.schema.json` 已定义却无人使用，证据只能以自由文本散落在各处。
- 多 Agent 运行时调度（子 Agent 目前是方法论契约，不是运行实例）
- **营销数据平台接入** —— 无任何数据源连接器（刻意不包含，非能力缺失）
- 项目持久化与决策历史版本
- DeepSeek Harness 端到端集成

**未验证**
- 在任何宿主中的端到端运行效果
- 与单 Agent / 基础提示词的质量对照（先导实验样本不足，**不构成对照证据**）
- 评审独立性（先导实验的两名评审身份与产生方式无记录）
- 真实商业项目中的 ROI 改善
- 商业价值假设：咨询交付 / 企业内训 / 评测层三条路径**均未验证**
- 在真实客户数据上能否端到端跑完一次完整的 R→E→B→U→I→D

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

**当前状态：一次先导实验（pilot），不是正式评测结果。**

⚠️ **下列数字不得作为结论引用。** 它只证明评测流程可以端到端跑通，不证明 REBUILD 优于任何方案。

| 配置 | 评审甲 | 评审乙 | 均值 |
|---|---|---|---|
| A 普通提示词 | 16 | 13 | 14.5 |
| B 单 Skill 框架 | 19 | 18 | 18.5 |
| C REBUILD 完整 | 32 | 31 | 31.5 |

**为什么这批数据不能当结论用：**

- **样本量不足**：只覆盖 4 个用例中的 1 个（B03），每个配置只运行 1 次（`RUBRIC.md` 要求 ≥3 次）。
- **评审独立性未经验证**：两名评审的身份与产生方式均无留存记录。在补证之前只能视为**自评**，**不能称为「两名独立评审盲评」**。
- **绝对分数偏高**：C 组给出 32/32 与 31/32，接近满分。满分本身是评分尺度可能过松的警示信号。
- **单一用例**：B03 恰是四个用例中最容易拉开差距的一个，其余三个表现未知。

原始逐行评分见 `bench/scorecard.csv`，完整局限声明见 [`bench/PILOT_B03.md`](bench/PILOT_B03.md)。

**本项目目前不声称自己在质量上优于任何方案。** 要得出该结论，须完成 4 用例 × 3 配置 × ≥3 次运行 × ≥2 名可验证独立评审，并公布全部原始输出与失败样本。

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
