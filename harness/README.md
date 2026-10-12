# 宿主接入

## DeepSeek Harness（DSH）

`deepseek/SKILL.md` 是一个可直接安装的 DSH Skill。它把 REBUILD 的方法论、
证据纪律与配套命令压缩成一份模型可读的操作说明。

### 安装

DSH 的技能发现规则是：在若干「扫描根目录」下找 `<名称>/SKILL.md`，**只扫描一层**。

```bash
# 用户级安装（对所有项目生效）
mkdir -p ~/.dsh/skills/rebuild-strategist
cp harness/deepseek/SKILL.md ~/.dsh/skills/rebuild-strategist/SKILL.md

# 或者项目级安装（只对当前项目生效）
mkdir -p .dsh/skills/rebuild-strategist
cp harness/deepseek/SKILL.md .dsh/skills/rebuild-strategist/SKILL.md
```

装好后**下一个模型步骤**即可在技能目录中看到 `rebuild-strategist`，无需重启。

### 卸载

```bash
rm -rf ~/.dsh/skills/rebuild-strategist
```

### 注意

- 文件名必须是 `SKILL.md`，目录名必须与 frontmatter 中的 `name` 一致。
- frontmatter 的 `name` 必须是 kebab-case，且 `description` 不能为空——
  这两项任一不合法，技能会被**静默丢弃**。
- 技能正文会被整体注入模型上下文。本文件已控制在 8 KB 以内，
  以免在压缩发生时被截断中间部分。

### 能力边界

装上这个 Skill 得到的是**一套工作方法**，不是运行时。具体来说：

- Skill 教模型按 REBUILD 的六个阶段和门禁工作；
- `core/` 下的命令提供落盘、校验与留痕；
- `core/orchestrator.py` 可以在**没有宿主**的情况下顺序跑完整个循环；
- **并行子 Agent 调度由宿主决定**。DSH 提供子 Agent 能力时才有真并行，
  本仓库不假装具备。

## 其他宿主

REBUILD 的方法论与命令不依赖任何特定宿主。若目标宿主不支持 Skill 机制，
把 `deepseek/SKILL.md` 的正文作为系统提示词，并在项目根目录运行
`core/rebuild_cli.py` 即可。
