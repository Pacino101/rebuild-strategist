# DSH adapter — delegation, state and installation

How the REBUILD contracts map onto this DeepSeek Harness. Verified against the installed
Harness (desktop profile, desktop `0.2.0-rc.2`, skill-subsystem packages `0.2.0-rc.2`)
on 2026-10-12. Every claim below is marked with how it was established.

## 1. Delegation mapping

| REBUILD need | DSH mechanism | Notes |
|---|---|---|
| One specialist, fresh context | `subagent` | The child does not see this conversation; the brief must be self-contained. |
| Specialist needing this conversation | `subagent_fork` | Inherits completed turns only, not the in-flight turn. |
| Many independent pieces (audit N competitors, analyse N channels) | `workflow` | Fan out in a script; use `pipeline` for stage chains, `parallel` only at a real barrier. |
| Long-running or parallel computation | background `bash` job | Collect with `job_output` before reporting. |
| Durable cross-turn teammates | Agent Teams (`spawn_teammate`, `send_message`, `team_task_*`) | Only when the agent-team bundle is enabled; prefer `subagent` unless the user asks for teammates. |
| Step tracking | `todo_write` | Tracks implementation steps, not the strategy plan itself. |

Rules that survive delegation: a specialist returns the ten contract fields
(`summary`, `findings[]`, `evidence[]`, `assumptions[]`, `unknowns[]`, `recommendation`,
`confidence`, `dependencies`, `risks`, `next_actions[]`); a specialist never expands scope or
causes external side effects; independent delegations start in one message; the master merges and
never averages contradictory claims into false certainty.

If no delegation tool is available in the session, run the contracts sequentially in one agent and
label the output **simulated role separation** — never imply parallel agents ran.

## 2. Persisting project state

Write state into the workspace, never only into context. Two conventions are supported, and the
state document records which one a project uses in its `storage_convention` field:

**`single-file`** — one document holds everything:

```
<workspace>/.rebuild/state.json          # resources/schemas/project_state.schema.json
```

**`split-files`** — the state document plus sibling artifacts:

```
<workspace>/.rebuild/state.json          # resources/schemas/project_state.schema.json
<workspace>/.rebuild/kpi/kpi_tree.json   # resources/schemas/kpi_tree.schema.json
<workspace>/.rebuild/experiments/*.json  # resources/schemas/experiment.schema.json
<workspace>/.rebuild/evidence/*.json     # resources/schemas/evidence.schema.json
```

`project_state.schema.json` is closed (`additionalProperties: false`) and therefore declares
`storage_convention` explicitly. It can hold `kpi_tree`, `experiments`, `decisions`, `assumptions`,
`tasks`, `risks`, `validation.red_team` and `review` directly, so `single-file` is fully valid;
`split-files` is a convenience for large projects. Choose one per project and do not mix them
silently.

Resume with `PROJECT_CONTINUATION`: read the state file, report the last accepted gate, continue
from there. Never reconstruct a decision that is not in the file — say what is missing and ask for
the minimum artifact.

## 3. How this skill is discovered in DSH

The Harness discovers skills from the filesystem. No build step and no plugin install are
required. *(Established from `@deepseek-ai/dsh-skill-filesystem` `lib/index.js` + README.)*

| Rank | Root | Scope |
|---:|---|---|
| 100 | `<projectRoot>/.dsh/skills` | this workspace only |
| 200 | `<projectRoot>/.agents/skills` | this workspace, shared with other agent tools |
| 300 | profile `customSkillDirs` | profile-defined |
| 400 | `~/.dsh/skills` | every session, every workspace (`.system` skipped) |
| 500 | `~/.agents/skills` | shared agent-config root |
| 600 | `bundledSkillDir` / `$DSH_BUNDLED_SKILL_DIR` | shipped with a package; inactive when unset |

`projectRoot` is the nearest ancestor containing `.git`; with none, the session working directory.
Discovery is **one level deep**: a skill is `<root>/<name>/SKILL.md` or `<root>/<name>.md`.
Nested `**/SKILL.md` is deliberately not discovered.

Frontmatter rules that cause silent loss, so validate before installing:

- `name` and `description` are both required; `name` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- The frontmatter `name` wins over the directory name; the directory only locates the file.
- Unknown extra keys (e.g. `version`) are ignored and harmless.
- Camel-case legacy keys `disableModelInvocation`, `modelInvocable`, `userInvocable` **throw** and
  drop the entire skill. Use the kebab-case forms.
- A rejected skill produces only a local warning: the model catalog cannot distinguish an absent
  skill from an invalid one.

Roots are watched, so a new skill needs no restart. The catalog is republished at the next
`agent/pre-step`, and the loaded `<skill_content>` carries
`Base directory for this skill: <absolute path>`, so the relative paths under `resources/`
resolve from there.

### Install commands

User-wide (works in every workspace):

```bash
mkdir -p ~/.dsh/skills && cp -R <package> ~/.dsh/skills/rebuild-strategist
```

Workspace-only:

```bash
mkdir -p .dsh/skills && cp -R <package> .dsh/skills/rebuild-strategist
```

Both write outside the skill's own directory and therefore need the user's approval under the
current file policy. Do not claim installation until the directory exists **and** a later model
step lists the skill in `<available_skills>`.

## 4. Known Harness constraints

- **Tool-result pruner.** The standard preset configures
  `thresholdChars: 8192`, `headChars: 4096`, `tailChars: 1024`. Trimming runs only when a
  compaction trigger qualifies, so a long skill body normally survives intact but can lose its
  middle once compaction fires. Keep `SKILL.md` as short as practical and put depth in
  `resources/`, which is loaded on demand and never passes through the pruner.
- **`plugin_manager` is disabled** in the standard preset, so its documented `install_bundle`
  route is unavailable without a profile change. The filesystem skill route is the supported path
  for this package.
- **Agent presets are registry rows, not folders.** There is no scanner for an `agents/` directory
  anywhere in the Harness. The contracts in `resources/agents/` are model-facing knowledge that
  works today through `subagent`; a preset dropdown entry would require a bundle that inserts
  `@deepseek-ai/dsh-agent-preset` rows, installed at profile level with approval.
- **A skill name is unique per catalog.** When two roots offer the same name, the nearer scope or
  higher rank wins outright; do not install the same name at rank 100 and rank 400 expecting two
  entries.
- **Third-party Host plugins run in-process outside the workspace sandbox.** Prefer the
  filesystem skill route unless a bundle is genuinely required.

## 5. Verification status

| Claim | Status |
|---|---|
| Frontmatter valid, references resolve, schemas parse, tool statuses honest | **verified** — `tests/verify_package.sh` passes |
| Skill discovery contract and root ranks | **verified** — installed package README + `lib/index.js` |
| Skill loads and returns its body with the correct base directory | **verified** — the `skill` tool returned the body plus `Base directory for this skill: …` on 2026-10-12 20:53–20:55 (harness 0.2.0-rc.2) |
| Skill appears in the catalog without restart | **verified** — `rebuild-strategist` entered `<available_skills>` at the next model step after the files were written, with no restart |
| Entrypoint stays under the 8,192-char pruner threshold | **verified** — `tests/verify_package.sh` asserts the rendered body size |
| Smoke tests T01–T10 executed | **not run** — see `tests/SMOKE_TESTS.md` |
| Any of the ten integrations connected | `not_configured` — see `resources/tool-registry.yaml` |
| Any agent preset contributed to the preset dropdown | **not implemented** — see §4 |

Never upgrade a row in this table without evidence from an actual run.
