# Changelog

## V3.4.0 — 决策复盘闭环、来源可核验与 Skill 更新

这一版补上的是**最后一段断掉的循环**：D（Decision Review）阶段此前完全没有实现——
`project.json` 里的 `decision_records` 是个永远为空的数组，决策做完就散了，
系统能产出决策却永远学不到自己的决策对不对。

### 新增：决策记录与复盘（`core/decisions.py` + `schemas/outcome.schema.json`）
- 决策入库、按复审日期管理、结果回填，并同步回 `project.json` 的 `decision_records`
  （标注 `PENDING_REVIEW` / `REVIEWED`）。
- **`decision due` 把「该复盘却没复盘」的决策主动摆到眼前**，而不是等使用者想起来。
- **强制区分偏差类型**：`EXECUTION`（执行偏差）/ `STRATEGY`（策略失效）/
  `ASSUMPTION`（假设错误）/ `MIXED` / `UNKNOWN`。选 `UNKNOWN` 必须说明为什么无法归因。
- 结果回填时 `actual` 过短会被拒绝：复盘必须写出实际观察到的结果，
  没有数据时须写「未采集到数据」，不得用印象代替。
- 质量提示：无复审日期、无反证条件、无代价、无关键假设、单选项、
  所选方案不在候选列表、同名选项、期限已过期。
- **模型产出的决策记录不自动入库**：编排器只写运行产物，入库需人工执行
  `decision import`——与证据同一条原则。

### 新增：证据来源可核验（`ledger.provenance_report` + `evidence provenance`）
- `source` 写成 `DOC-001` 形式时视为指向材料库，**可被机器核验**；
  写成自由文本则不能。系统明确区分这两种情况并统计可核验比例。
- **断链是错误而非警告**：指向不存在的材料比自由文本更糟——
  它自称可核验，实际核验不了。
- `evidence add --source-doc DOC-001` 在写入前确认材料存在。

### 更新：宿主接入（`harness/`）
- `harness/deepseek/SKILL.md` 重写：此前完全没有提及 V3.3 引入的任何能力
  （编排器 / 证据账本 / 数据源 / 决策库），现已全部纳入，并补充边界声明。
- 新增 `harness/README.md`：安装步骤、DSH 技能发现规则、卸载方式与能力边界。
- 新增 `tests/test_harness_skill.py`：把「frontmatter 不合法会导致技能被静默丢弃」
  变成 CI 能抓住的错误。

### 变更
- `schemas/` 由 5 份增至 6 份（新增 `outcome.schema.json`）。
- 单元测试由 174 项增至 211 项。

## V3.3.0 — 运行时、证据账本与数据源

这一版把三处「文档里写了、代码里没有」的缺口补上：Schema 只是规范文件、
证据账本无处存放、角色契约没有编排器。**注意：这些是能力补齐，不是质量证明**——
编排器的输出质量尚未在任何真实模型上验证。

### 新增：JSON Schema 校验器（`core/schema_validator.py`）
- 纯标准库实现，覆盖本仓库 Schema 实际使用的关键字，另含 `anyOf` / `oneOf` / `allOf`。
- **未实现的关键字会报 warning，而不是静默忽略。** 静默忽略会让「校验通过」变成假象。
- `rebuild_cli.py validate` 默认执行 schema 校验；新增 `schema` 子命令校验任意 JSON。

### 新增：证据账本（`core/ledger.py`）
- 把 `evidence.schema.json` 从规范文件变成可用的存储：`<项目>/evidence.jsonl`，追加写入、可 diff、无数据库依赖。
- **写入前强制校验**，不合规的记录直接拒绝，不会「先写进去再说」。
- 账本损坏时报错而不是跳过坏行——静默跳过会让证据悄悄消失。
- schema 之外的语义检查（以 warning 呈现）：`FACT` 无来源、`ASSUMPTION` 无重查条件、
  `UNKNOWN` 却给高可信度、`decision_impact` 写成「无」。
- 新增 `evidence add / list / check / gaps / export` 子命令；`gaps` 找出项目里声明了但账本没覆盖的假设与未知项。

### 新增：数据源层（`sources/`）
- 本地文件：CSV / TSV / JSON / JSONL / TXT / MD / XLSX。
- **中文编码兜底**：utf-8-sig → utf-8 → gb18030 → big5 → latin-1。乱码喂进模型比没数据更糟。
- **XLSX 用标准库解析**（zipfile + xml.etree），不引入 pandas / openpyxl。
- 自建 HTTP 端点：URL、方法、取值路径由使用者给出；**不内置任何平台连接器**。
- 密钥只从环境变量读取，spec 文件不存密钥；检测到疑似密钥会警告。
- 每条材料存 SHA-256，`source verify` 可校验来源是否被改动。

### 新增：运行时编排器（`core/orchestrator.py`）
- 按阶段顺序调度角色契约、注入证据与材料、收集输出、判定门禁、推进状态、产出决策记录。
- **顺序执行，不假装并行**：一个角色一次模型调用，角色之间不通信。
- **状态迁移由状态机裁决**：模型只回答「应触发哪个事件」；合法性由 `state_machine.json` 决定，
  模型给出非法事件会被拒绝并记入报告。
- **模型提出的证据不自动入账**：写入运行产物供人工审核。自动入账会让证据账本退化成「模型说过的话清单」。
- 默认 `--provider manual`：只生成任务包，零网络请求；`--dry-run` 同样零网络、零状态变更。

### 变更
- `rebuild_cli.validate_project()` 返回值由 `errors` 列表改为 `(errors, warnings)` 元组，
  以便暴露「schema 中未被检查的约束」。这是**破坏性变更**，调用方需同步调整。
- `tests/test_rebuild.py` 的临时文件改写到系统临时目录，不再污染仓库工作区。
- `.gitignore` 增加 `runs/`、`sources/documents/`、`sources/index.jsonl`、`sources/specs/`、`evidence.jsonl`：
  这些目录默认含客户数据与模型输出。
- CI 增加端到端冒烟测试（导入材料 → 写入证据 → 干跑编排），并断言示例目录未被产物污染。

### 测试
- 单元测试由 28 项增至 174 项。
- 编排器测试全部注入假模型，**不产生任何网络请求**。

## V3.2.4 — 边界声明与模型接口文档

### 修正
- **SECURITY.md 的事实性错误**：原文称「作为纯本地工具运行，不产生网络请求」。自 V3.2.2 引入 `bench/provider.py` 后该声明已不成立。现如实说明：不采集行为数据、不含遥测，但启用 `--provider` 时会向用户指定的模型端点发起请求并外发提示词内容；默认手动模式不产生网络请求。

### 文档
- README 新增「**这个项目不是什么**」：它不是投放 / CRM / 分析工具，不是自动化执行系统，不是多 Agent 运行时，不是数据接入层，也不保证结论正确。
- README 明确声明商业价值假设（咨询交付 / 企业内训 / 评测层）**均未被验证**，仓库不为其背书。
- README 新增「**接入你自己的模型**」，记录 provider 层的预设清单、自定义 OpenAI 兼容端点用法、盲评流程接入方式与扩展方法。
- 成熟度声明如实标注两处此前未披露的缺口：
  - **5 份 JSON Schema 没有任何代码读取**，CLI 只对 `project.json` 做手写字段检查；
  - **证据账本只有 Schema、没有录入与读取路径**——而它是方法论的核心产物。
- 快速验证段落修正：克隆地址由占位符改为真实仓库地址，测试数量由「5 项」更正为 28 项。

## V3.2.3 — 先导实验结果与 scorecard 校验

### 修正
- **修复 `bench_runner.py` 中 `reveal()` 的列错位**：此前把 `config_key` 写进 `case_id` 列，导致公布的 scorecard 丢失真实用例编号（B01–B04）。现 `case_id` 取自 manifest，揭示后的配置名单独存放在 `config` 列。
- `summarise()` 改为读取 `config` 列，同时兼容旧的 `config_blinded` 格式。

### 评测
- 公布一次先导实验（用例 B03，每配置 n=1）。**样本量远低于 `RUBRIC.md` 标准，不构成质量对照证据。**
- 新增 `bench/PILOT_B03.md`，逐条声明局限：样本量不足、评审独立性未经验证、单一用例、满分异常。

### CI
- 移除「scorecard 必须为空」的断言。该断言只能防住「还没跑实验就填数」，一旦产生真实数据必然误报，且无法识别填错的行。
- 改为执行 `bench_runner.py check-scorecard`：校验表头、取值域、总分与分项之和一致性、必填字段。

### 文档
- README 的「当前 scorecard 为空」声明改为与仓库实际数据一致，并明确标注先导实验的局限。
- README 成熟度声明同步：模型 Provider 接入层列为已实现，多 Agent 运行时调度仍为未实现。

## V3.2.2 — Provider 接入层
- 新增 `bench/provider.py`：OpenAI 兼容与 Anthropic 兼容两种调用方式。
- `bench_runner.py` 增加 `render` 与 `execute` 子命令。

## V3.2.1 — 盲评对照实验脚手架
- 新增 `bench/bench_runner.py`：编号散列、呈现顺序打乱、身份隐藏、评审一致性检查，并拒绝不足两名评审或不完整覆盖。
- 新增 `bench/HOWTO.md`、`bench/REVIEW_PROTOCOL.md`、`bench/prompts/`。
- 新增 `tests/test_bench_runner.py`。
- `.gitignore` 增加 `bench/runs/`（含盐值与未公开的模型输出）。

## V3.2.0 — Original Decision-Centric OS

### 方法论
- 移除第三方营销工具集成目录与工具注册表。
- 将系统重心改为原创决策协议、证据追溯、显式取舍、单位经济和反证闭环。
- 六阶段决策循环（R-E-B-U-I-D）带阶段门禁与回退路径。
- 南涧茶厂示例改为待核验框架，不预设项目成果。

### 工程
- 增加确定性状态机与本地 CLI。
- 增加 JSON Schema、基准案例、盲评规程和成熟度声明。
- 增加 GitHub Actions CI（Python 3.10–3.13）。

### 角色契约分化
- 重写 8 个职能角色契约。此前各角色共用同一份通用模板（除标题外内容完全一致），角色边界模糊。
- 每个角色现包含独立使命、输入边界与越权拒绝规则、角色专属交付字段、专属追问清单、专属失败模式。
- 主 Agent 增加按阶段调度的角色调度表、降级规则、冲突处理与越权处理规则。

### 仓库基建
- 修正 `docs/STATUS_AND_ROADMAP.md`：原文称 GitHub CI「未配置」，但 `.github/workflows/tests.yml` 已存在。
- 清理 `__pycache__` 与 `.pyc` 残留。
- 新增 `SECURITY.md`、`CODE_OF_CONDUCT.md`、PR 与 Issue 模板。
- LICENSE 版权署名由占位式 `REBUILD Project Contributors` 改为实际作者。
- README 按「决策中心方法论 OS」定位重写，明确区分已实现 / 未实现 / 未验证。

### 评测脚手架（V3.2.1 提前落地）
- 新增 `bench/bench_runner.py`：五步流程 generate → template → import → reveal → summarise，仅标准库。
- 三组对照配置：A 普通提示词基线、B 结构化框架、C REBUILD 全流程。
- 盲评防护：SHA-256 编号散列、呈现顺序打乱、配置身份隐藏、同 salt 可复现。
- 强制校验：少于 2 名独立评审拒绝揭示；任一评审未覆盖全部条目拒绝揭示；两名评审分差 > 6 分提示复核。
- 新增 `bench/REVIEW_PROTOCOL.md`（评分锚点与常见误判）、`bench/HOWTO.md`（操作手册）。
- 新增 `bench/prompts/A_plain.txt`、`bench/prompts/B_skill.txt`。
- 新增 `tests/test_bench_runner.py`，9 项测试覆盖上述防护机制；总测试数 5 → 14。
- 修复 `bench_runner.py` 中 3 处未关闭的文件句柄（由 `-W error::ResourceWarning` 检查发现）。
- CI 增加 ResourceWarning 严格模式、bench CLI 冒烟测试，以及 scorecard 空表守卫。
- `.gitignore` 排除 `bench/runs/`（含未公开回答与盐值）。
