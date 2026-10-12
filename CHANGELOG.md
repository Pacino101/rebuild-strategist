# Changelog

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
