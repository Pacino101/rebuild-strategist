# Host integration

## DeepSeek Harness (DSH)

`deepseek/SKILL.md` is a directly installable DSH Skill. It compresses the REBUILD
methodology, evidence discipline and companion commands into a single model-readable
operating manual.

### Installation

DSH's skill discovery rule is: look for `<name>/SKILL.md` under a number of "scan roots", and
**scan only one level deep**.

```bash
# User-level installation (applies to all projects)
mkdir -p ~/.dsh/skills/rebuild-strategist
cp harness/deepseek/SKILL.md ~/.dsh/skills/rebuild-strategist/SKILL.md

# Or project-level installation (applies only to the current project)
mkdir -p .dsh/skills/rebuild-strategist
cp harness/deepseek/SKILL.md .dsh/skills/rebuild-strategist/SKILL.md
```

Once installed, **the next model step** will see `rebuild-strategist` in the skill catalog,
with no restart needed.

### Uninstallation

```bash
rm -rf ~/.dsh/skills/rebuild-strategist
```

### Notes

- The file name must be `SKILL.md`, and the directory name must match the `name` in the frontmatter.
- The frontmatter `name` must be kebab-case, and `description` must not be empty —
  if either of these is invalid, the skill is **silently dropped**.
- The skill body is injected into the model context in full. This file is kept under 8 KB,
  so that its middle section is not truncated when compaction happens.

### Capability boundaries

What you get from installing this Skill is **a working method**, not a runtime. Specifically:

- The Skill teaches the model to work through REBUILD's six phases and gates;
- The commands under `core/` provide persistence, validation and an audit trail;
- `core/orchestrator.py` can run the entire loop sequentially **without a host**;
- **Parallel sub-agent scheduling is decided by the host.** True parallelism exists only when DSH
  provides sub-agent capability; this repository does not pretend otherwise.

## Other hosts

REBUILD's methodology and commands do not depend on any particular host. If the target host does not
support the Skill mechanism, use the body of `deepseek/SKILL.md` as the system prompt and run
`core/rebuild_cli.py` in the project root.
