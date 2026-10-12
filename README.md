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
| **不是并行多 Agent 运行时** | `core/orchestrator.py` 会**按顺序**逐个调用角色契约，一次一个模型调用。角色之间不通信、不并行、不互相评审。把顺序调用包装成「多 Agent 协同」正是本项目反对的事。 |
| **不内置任何平台连接器** | 支持导入本地文件（CSV / TSV / JSON / JSONL / TXT / MD / XLSX）与你自建的 HTTP 端点，但**不预置** PostHog / Mautic / 广告平台的连接器或字段映射——那些由你自己给出 URL 与字段路径。 |
| **不保证结论正确** | 它约束的是论证过程是否诚实、可追溯、可证伪，不是结论本身是否正确。 |

**它的商业价值目前是假设，不是结论。** 可能的方向包括咨询交付、企业内训、以及作为评测层（对已有营销方案或 AI 输出做结构化审查）。**这三个方向均未被任何真实项目验证，本仓库不为它们背书。**

目前**已被验证**的是：方法论自洽、状态机确定性、Schema 校验生效、证据账本可写可查、数据源可导入本地文件与自建端点、编排器可零网络干跑并正确拒绝非法迁移、评测脚手架可端到端运行。

**仍未验证**的是它的商业价值，以及它能否在**更多**真实项目上复现同样的效果。

`examples/metro_apartment/` 是一次真实项目的完整运行（已脱敏），它在单位经济上抓到了一个
用营销手段修不好的条款问题。但**这是一个案例，不是样本**——它证明了流程能跑完并算出结论，
不证明方法可推广，也不证明结论被采纳。

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

# 单元测试（211 项）
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

> **注意**：provider 层同时服务于 `bench/` 评测流程与 `core/orchestrator.py` 运行时。编排器按阶段**顺序**调用角色契约，不是并行多 Agent（见上方「这个项目不是什么」）。

## 证据账本

方法论要求「每条关键判断可追溯」，但在此之前**没有地方存证据**——`evidence.schema.json` 定义了却没有任何代码读它。现在它可用了：

```bash
# 写入一条证据（写入前强制校验 schema，不合规直接拒绝）
python core/rebuild_cli.py evidence add projects/my-project \
    --claim "春茶季前两周询价量约为平峰期 3 倍" \
    --type FACT --confidence MEDIUM \
    --source "门店台账 2026-03" --observed-at 2026-03-20 \
    --scope "南涧县自营门店自饮客群" \
    --decision-impact "决定是否把全年预算改为春茶季集中投放"

python core/rebuild_cli.py evidence list   projects/my-project
python core/rebuild_cli.py evidence check  projects/my-project   # schema + 语义质量
python core/rebuild_cli.py evidence gaps   projects/my-project   # 哪些假设还没有证据
python core/rebuild_cli.py evidence export projects/my-project --out ledger.md
```

存储为 `<项目>/evidence.jsonl`：每行一条，可 diff、可人工审阅、无数据库依赖。

**schema 之外还查什么。** schema 只能保证字段齐全、取值合法，保证不了这条证据有用。因此额外检查：

| 情况 | 为什么算问题 |
|---|---|
| 标为 `FACT` 却没有来源 | 事实必须可核验，做不到就该降级为推断 |
| 标为 `ASSUMPTION` 却没写重查条件 | 未验证的前提必须说明什么情况下重查 |
| 标为 `UNKNOWN` 却给 `HIGH` 可信度 | 语义冲突：信息不足不应给高可信度 |
| `decision_impact` 写成「无」 | 不指向任何决策的证据不构成证据 |

这些是**警告而非错误**：不阻断写入，但会出现在 `evidence check` 的输出里。

## 导入你的数据

```bash
# 本地文件：CSV / TSV / JSON / JSONL / TXT / MD / XLSX
python core/rebuild_cli.py source add-file projects/my-project ~/Downloads/orders.csv

# 你自己的 HTTP 端点
python core/rebuild_cli.py source add-url projects/my-project \
    --name my-orders --url https://api.example.com/orders \
    --header-env "Authorization=MY_API_TOKEN" \
    --records-path "data.items" --save-spec

python core/rebuild_cli.py source list   projects/my-project
python core/rebuild_cli.py source verify projects/my-project   # 内容与哈希是否一致
```

两处刻意设计：

- **中文编码兜底。** 依次尝试 utf-8-sig → utf-8 → gb18030 → big5 → latin-1。中文导出的 CSV 十有八九是 GBK，按 UTF-8 读会整片乱码——**乱码喂进模型比没有数据更糟**，模型会照着乱码编。
- **密钥不进 spec 文件。** spec 只记录「哪个请求头对应哪个环境变量」，真实值运行时从环境变量读取。写在文件里的密钥迟早会进 git。

XLSX 用标准库 `zipfile` + `xml.etree` 解析，**不需要 pandas 或 openpyxl**。每条材料都存 SHA-256，`source verify` 可校验来源是否被改动过。

## 运行编排

```bash
# 默认手动模式：只生成任务包，零网络请求
python core/rebuild_cli.py run projects/my-project --dry-run

# 接上你自己的模型跑完整循环
export DEEPSEEK_API_KEY=sk-xxx
python core/rebuild_cli.py run projects/my-project --provider deepseek

# 提高运行间一致性（但多数 API 在 0 下也不保证完全确定）
python core/rebuild_cli.py run projects/my-project --provider deepseek --temperature 0
```

> ⚠️ **单次运行的输出不是「答案」，只是起点。** 实测同一输入跑三次，
> 决策方向一致但细节差异可达 2.5 倍（反证条件 6/10/15 条）。
> 因此内置了多次运行比对——见下节。

编排器做四件事：按阶段调度角色 → 注入证据与材料 → 请模型判定门禁 → **由状态机裁决迁移**。

三条不可让步的约束：

1. **顺序执行，不假装并行。** 一个角色一次模型调用，依次进行，角色之间不通信。
2. **状态迁移由状态机裁决，不由模型裁决。** 模型只回答「应触发哪个事件」；该事件是否合法、迁移到哪个状态，一律由 `core/state_machine.json` 决定。模型给出非法事件会被拒绝并记入报告。
3. **模型提出的证据不进入账本。** 模型输出不是证据。它建议的条目只写入运行产物供人工审核——自动入账会让「证据账本」退化成「模型说过的话清单」。

产物写入 `<项目>/runs/<时间戳>/`：每个角色的任务包与输出、门禁判定原文、决策记录（经 schema 校验）。`runs/` 默认不提交。

## 多次运行比对

单个输出不能当作答案，所以有了这个：

```bash
# 同一输入重复 3 次（每次重置项目状态）
python core/rebuild_cli.py run projects/my-project --provider deepseek \
    --temperature 0 --repeat 3

# 确定性比对：迁移路径、终态分布、逐阶段门禁档位、条目数量极差
python core/rebuild_cli.py compare projects/my-project --last 3

# 再用模型判定「几次建议在方向上是否一致」
python core/rebuild_cli.py compare projects/my-project --last 3 --judge-with deepseek
```

**两类结论被刻意分开，不能混为一谈：**

| 轴 | 怎么算 | 能说明什么 |
|---|---|---|
| **过程可复现性** | 确定性计算，不用模型 | 路径 / 终态 / 档位是否一致 |
| **结论一致性** | 模型判定，标注 `judged_by_model` | 建议方向是否一致 |

**「迁移路径相同」不等于「建议相同」。** 把前者说成后者是这类工具最容易犯的错。
模型判定的结果也带自己的 caveat——它是参考信号，不是事实。

过程不一致时 `compare` 返回非零退出码，可以直接用在脚本里。

## 成本

跑完一次完整的 R→E→B→U→I→D 的实测消耗：

| 规模 | 模型调用 | tokens | 耗时 |
|---|---|---|---|
| 两阶段 | 6 次 | 28,671 | 56 s |
| **完整六阶段** | **16 次** | **91,723** | **~110 s** |

费用需要你自己给单价——**本项目不内置任何价格**，因为价格会变，
写死在代码里就会变成一个悄悄过期的数字：

```bash
python core/rebuild_cli.py run projects/my-project --provider deepseek \
    --price-input 0.28 --price-output 0.42
```

两条约束：

- **token 是事实，费用是估算。** token 直接读 API 的 `usage` 字段；
  读不到就注明「总数不完整」，**绝不估算**。
- 费用结果始终带一句 caveat：这是按你给的单价算的估算，**不是账单金额**。

`compare` 会跨运行合计成本。

## 决策记录与复盘

方法论里 D（Decision Review）阶段要求「比较预期与实际、区分执行偏差与策略失效、记录下一步如何改变」。**在此之前这一环完全是空的**——`project.json` 里的 `decision_records` 永远是个空数组，决策做完就散了，系统永远学不到自己的决策对不对。

```bash
# 落一份决策
python core/rebuild_cli.py decision add projects/my-project \
    --question "优先选择哪一项品牌与渠道策略？" \
    --option "春茶季集中投放|需求集中，转化率高" \
    --option "全年均投|稳定但错过峰值" \
    --chosen "春茶季集中投放" \
    --rejected "全年均投|峰值把握不足" \
    --tradeoff "放弃淡季曝光" \
    --assumption "需求集中在 3 月下旬至 4 月上旬" \
    --falsification "若 4 月复购率低于 15% 则推翻" \
    --validation "小规模 A/B 测试" \
    --review-date 2026-05-01

# 到了该复盘的时候，它会主动找上门
python core/rebuild_cli.py decision due projects/my-project

# 回填实际结果
python core/rebuild_cli.py decision outcome projects/my-project --id DR-001 \
    --expected "春茶季销量提升 30%" \
    --actual "实际提升 12%，未达预期" \
    --deviation EXECUTION --next-action ADJUST \
    --notes "投放量不足，不是方向错误"
```

`decision due` 按复审日期把**「该复盘却没复盘」的决策摆到眼前**，而不是等你想起来。`decision outcome` 强制区分偏差类型：

| 偏差类型 | 含义 |
|---|---|
| `EXECUTION` | 执行偏差——方向对、力度不足 |
| `STRATEGY` | 策略失效——方向本身错了 |
| `ASSUMPTION` | 关键假设错误 |
| `MIXED` / `UNKNOWN` | 多重原因 / 无法归因（选 `UNKNOWN` 必须说明理由，不允许含糊过去） |

决策会自动同步回 `project.json` 的 `decision_records`，标注 `PENDING_REVIEW` 或 `REVIEWED`。

> **模型产出的决策记录不会自动入库。** 编排器跑完只把决策记录写进运行产物；要入库必须由人显式执行 `decision import`——与证据同一条原则：模型输出不等于已成立的决策。

## 证据来源可核验

证据的 `source` 有两种写法，系统知道自己在处理哪一种：

- **`DOC-001`**（材料编号）——指向材料库里的一份材料，**可被机器核验**。指向不存在的材料会报错，因为这是「自称可核验但实际核验不了」的断链。
- **自由文本**（如「门店台账 2026-03」）——无法自动核验，只能靠人工。

```bash
python core/rebuild_cli.py source add-file projects/my-project ~/orders.csv
python core/rebuild_cli.py evidence add projects/my-project \
    --claim "..." --type FACT --confidence MEDIUM \
    --source-doc DOC-001 --scope "..." --decision-impact "..."
python core/rebuild_cli.py evidence provenance projects/my-project   # 可核验比例
```

## 成熟度声明

这一节是本项目最重要的部分，请认真读。

**已实现并通过测试**
- 原创方法论与阶段门禁（已文档化）
- 确定性状态机：7 状态 / 合法与回退迁移
- **JSON Schema 校验器**（纯标准库）：type / required / properties / additionalProperties / items / enum / 范围与长度 / anyOf / oneOf / allOf。**未实现的关键字会报警而不是静默通过**
- **证据账本**：JSONL 追加存储、写入前强制 schema 校验、语义质量检查、缺口分析、来源可核验比例、Markdown 导出
- **数据源层**：本地文件（CSV / TSV / JSON / JSONL / TXT / MD / XLSX，含中文编码兜底）+ 自建 HTTP 端点（密钥只走环境变量）+ 内容哈希校验
- **运行时编排器**：按阶段顺序调度角色、注入证据与材料、**逐阶段门禁**（三档：充足 / 降级放行 / 不足）、模型判定门禁、**状态机裁决迁移**（模型的非法事件会被拒绝）、产出经 schema 校验的决策记录。**已在真实模型上跑通**，见 [`docs/VALIDATION_2026-10.md`](docs/VALIDATION_2026-10.md)
- **决策记录与复盘**：决策入库、复审到期主动提醒、结果回填并强制区分执行偏差 / 策略失效 / 假设错误、写回 `project.json`
- 6 份数据 Schema：项目、证据、决策、决策结果、实验、KPI 树
- 8 个角色的完整契约
- DeepSeek Harness Skill 与安装说明（`harness/`）
- 单元测试（211 项，Python 3.10–3.13）
- 盲评实验脚手架：编号散列、身份隐藏、评审一致性检查、拒绝不足两名评审与不完整覆盖
- 模型 Provider 接入层（OpenAI 兼容 / Anthropic 兼容两种调用方式）
- scorecard 结构校验：总分与分项一致性、取值域、必填字段
- 基准用例与 32 分评分量表
- 一轮先导实验（1/4 用例，样本不足，见 `bench/PILOT_B03.md`）

**未实现**
- **并行多 Agent 调度** —— 编排器是顺序执行：一个角色一次模型调用。真正的并行与互相评审需要宿主支持（如 DeepSeek Harness 的子 Agent），本项目不假装具备
- **内置营销数据平台连接器** —— 刻意不包含。数据源层只接受你自己给的文件或端点
- **决策历史版本与依赖回退** —— 决策存了、能复盘，但假设被证伪时还不会自动列出受影响的决策节点
- **营销动作的实际执行** —— 系统产出决策与验证方案，但不投放、不发消息、不写回任何外部系统
- DeepSeek Harness 端到端集成

**未验证**
- 在任何宿主中的端到端运行效果
- 与单 Agent / 基础提示词的质量对照（先导实验样本不足，**不构成对照证据**）
- 评审独立性（先导实验的两名评审身份与产生方式无记录）
- 真实商业项目中的 ROI 改善
- 商业价值假设：咨询交付 / 企业内训 / 评测层三条路径**均未验证**
- ~~在真实客户数据上能否端到端跑完一次完整的 R→E→B→U→I→D~~ —— **已验证一次**，见 `examples/metro_apartment/`（单案例，非样本；局限已在案例 README 中逐条列明）
- 编排器接上真实模型后的输出质量（现有测试全部使用注入的假模型）
- 决策复盘能否在真实项目中按期发生（机制有了，但还没有人真正用过）

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

## 真实项目案例

`examples/metro_apartment/` 是一个**真实商业项目的脱敏版本**，包含三份原始输入材料、
完整产出（决策页、KPI 树、实验卡片、单位经济模型）、以及可一键复现全部数字的 6 个脚本。

它跑出来的结论是：**这不是营销问题，是分成结构问题。** 在给定条款下，
运营方每运营一个月都在烧押金——无论出租率是 60% 还是 93%；甲方回本与乙方保本的约束**交集为空**。

```bash
cd examples/metro_apartment/rebuild && python3 scripts/run_all.py
```

脱敏范围与残留风险见该目录的 [`ANONYMIZATION.md`](examples/metro_apartment/ANONYMIZATION.md)。

## 目录

```text
core/            方法论、状态机、Schema 校验器、证据账本、决策库、编排器、CLI
agents/          主 Agent 与 8 个职能角色契约
sources/         数据源层：本地文件与自建 HTTP 端点
schemas/         项目、证据、决策、决策结果、实验、KPI 数据结构
bench/           基准用例、评分量表、盲评脚手架、评审规程
examples/        案例：nanjiang_tea 为空白框架；metro_apartment 为真实项目脱敏版
harness/         宿主接入说明与可安装的 DeepSeek Harness Skill
tests/           单元测试与静态检查清单
docs/            状态与路线图、首次真实模型验证记录
```

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。核心要求：
新增战略规则必须说明它**影响的决策、适用边界和失败条件**；
新增案例必须标注真实/合成/匿名化属性；
未运行的测试不得标记为通过。

行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，安全报告见 [SECURITY.md](SECURITY.md)。

## 许可证

[MIT License](LICENSE)。许可证仅适用于发布者有权授权的仓库内容；REBUILD 名称、标识及未获授权的第三方素材不因本许可证而自动获得使用许可。
