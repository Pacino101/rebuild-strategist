# Changelog

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
