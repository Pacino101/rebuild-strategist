#!/usr/bin/env python3
"""REBUILD 运行时编排器。

把 `agents/` 下的角色契约真正跑起来：按阶段调度角色、注入证据与材料、
收集输出、判定门禁、推进状态、产出决策记录。

三条不可让步的设计约束
----------------------
1. **顺序执行，不假装并行。** 每个角色一次模型调用，依次进行。本编排器
   不是多 Agent 并行运行时——若宿主（如 DeepSeek Harness）提供子 Agent
   能力，并行应由宿主负责。把顺序调用说成「多 Agent 协同」是本项目明确
   反对的那类自欺。

2. **状态迁移由状态机裁决，不由模型裁决。** 模型只负责判断「门禁是否
   通过、应触发哪个事件」；该事件是否合法、会迁移到哪个状态，一律由
   `core/state_machine.json` 决定。模型给出非法事件时会被拒绝。

3. **模型提出的证据不进入证据账本。** 模型输出不是证据。模型建议的
   证据条目写入 `proposed_evidence.jsonl` 供人工审核，绝不自动入账。
   自动入账会让「证据账本」退化成「模型说过的话清单」。
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _extra in (_HERE, _ROOT, _ROOT / "bench"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import ledger as ledger_module  # noqa: E402
import schema_validator as sv  # noqa: E402

#: 阶段顺序，与 core/state_machine.json 的状态一致（BLOCKED 除外）。
PHASES = ["DISCOVER", "EVIDENCE", "STRATEGY", "ECONOMICS", "EXECUTION", "REVIEW"]

#: 每个阶段需要哪些角色。空列表表示该阶段只由主 Agent 完成框架工作。
PHASE_ROLES = {
    "DISCOVER": [],
    "EVIDENCE": ["customer_evidence", "market_structure"],
    "STRATEGY": ["positioning_strategy", "red_team"],
    "ECONOMICS": ["business_model"],
    "EXECUTION": ["growth_system", "measurement_experiment"],
    "REVIEW": ["learning_review"],
}

ROLE_LABELS = {
    "master_agent": "主 Agent（编排与门禁）",
    "customer_evidence": "客户证据",
    "market_structure": "市场结构",
    "positioning_strategy": "定位与战略",
    "business_model": "商业模型",
    "growth_system": "增长系统",
    "measurement_experiment": "测量与实验",
    "red_team": "反证审查",
    "learning_review": "复盘学习",
}

#: 任务包里每个文档最多注入多少字符。材料多时按此截断，并在包里注明。
DOCUMENT_EXCERPT_CHARS = 4000

#: 任务包里最多注入多少条证据。
DEFAULT_MAX_EVIDENCE = 60


class OrchestratorError(Exception):
    """编排过程中的可预期错误，消息面向使用者。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state_machine() -> dict:
    return json.loads((_HERE / "state_machine.json").read_text(encoding="utf-8"))


def load_role_contract(role: str) -> str:
    path = _ROOT / "agents" / f"{role}.md"
    if not path.exists():
        raise OrchestratorError(f"找不到角色契约：{path}")
    return path.read_text(encoding="utf-8")


def load_project(project_dir) -> dict:
    path = Path(project_dir) / "project.json"
    if not path.exists():
        raise OrchestratorError(f"找不到项目文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    project_dir: Path
    provider_name: str = "manual"
    phases: list = field(default_factory=lambda: list(PHASES))
    dry_run: bool = False
    max_evidence: int = DEFAULT_MAX_EVIDENCE
    max_documents: int = 10
    temperature: float = 0.3
    max_tokens: int = 4096

    def __post_init__(self):
        self.project_dir = Path(self.project_dir)
        unknown = [p for p in self.phases if p not in PHASES]
        if unknown:
            raise OrchestratorError(
                f"未知阶段：{unknown}。可用阶段：{PHASES}"
            )


# ---------------------------------------------------------------------------
# 上下文收集
# ---------------------------------------------------------------------------

def collect_context(project_dir, max_evidence=DEFAULT_MAX_EVIDENCE,
                    max_documents=10) -> dict:
    """汇总项目状态、证据账本与原始材料，供任务包使用。"""
    project_dir = Path(project_dir)
    project = load_project(project_dir)

    ledger = ledger_module.Ledger(project_dir)
    evidence = ledger.load()
    truncated = False
    if len(evidence) > max_evidence:
        evidence = evidence[:max_evidence]
        truncated = True

    documents = []
    index_path = project_dir / "sources" / "index.jsonl"
    if index_path.exists():
        from sources import DocumentStore  # 延迟导入，避免无 sources 时的硬依赖

        store = DocumentStore(project_dir)
        for entry in store.list()[:max_documents]:
            try:
                document = store.get(entry["doc_id"])
            except Exception:  # noqa: BLE001 - 单个文档损坏不应中断整个编排
                continue
            excerpt = document.content[:DOCUMENT_EXCERPT_CHARS]
            documents.append({
                "doc_id": document.doc_id,
                "origin": document.origin,
                "media_type": document.media_type,
                "sha256": document.sha256[:12],
                "chars": len(document.content),
                "truncated": len(document.content) > DOCUMENT_EXCERPT_CHARS,
                "excerpt": excerpt,
                "meta": document.meta,
            })

    return {
        "project": project,
        "evidence": evidence,
        "evidence_truncated": truncated,
        "evidence_total": len(ledger.load()),
        "documents": documents,
    }


# ---------------------------------------------------------------------------
# 任务包
# ---------------------------------------------------------------------------

def build_task_packet(role: str, phase: str, context: dict) -> str:
    """按主 Agent 契约的要求组装任务包：目标、输入、输出、证据要求、验收标准。"""
    project = context["project"]
    label = ROLE_LABELS.get(role, role)

    lines = [
        f"# 任务包 — {label}（阶段 {phase}）",
        "",
        "## 一、角色契约",
        "",
        load_role_contract(role),
        "",
        "## 二、项目背景",
        "",
        f"- **决策问题**：{project.get('decision_question', '（未填写）')}",
        f"- **当前阶段**：{project.get('current_state', '（未填写）')}",
        f"- **决策期限**：{project.get('decision_deadline') or '（未设定）'}",
        f"- **目标**：{'；'.join(project.get('goals') or []) or '（未填写）'}",
        f"- **约束**：{'；'.join(project.get('constraints') or []) or '（未填写）'}",
        "",
    ]

    known_facts = project.get("known_facts") or []
    if known_facts:
        lines += ["**项目声称的已知事实（未经账本核验，请勿当成已核实证据）**", ""]
        lines += [f"- {fact}" for fact in known_facts]
        lines += [""]

    assumptions = project.get("assumptions") or []
    unknowns = project.get("unknowns") or []
    if assumptions or unknowns:
        lines += ["**待验证假设与未知项**", ""]
        lines += [f"- 假设：{item}" for item in assumptions]
        lines += [f"- 未知：{item}" for item in unknowns]
        lines += [""]

    lines += ["## 三、证据账本", ""]
    if context["evidence"]:
        lines += [
            "| ID | 类型 | 可信度 | 主张 | 来源 | 适用范围 | 会改变什么决策 |",
            "|---|---|---|---|---|---|---|",
        ]
        for record in context["evidence"]:
            def cell(value):
                text = str(value if value is not None else "")
                return text.replace("|", "\\|").replace("\n", " ")

            lines.append(
                "| {id} | {type} | {conf} | {claim} | {src} | {scope} | {impact} |".format(
                    id=cell(record.get("id")), type=cell(record.get("type")),
                    conf=cell(record.get("confidence")), claim=cell(record.get("claim")),
                    src=cell(record.get("source") or "（未提供）"),
                    scope=cell(record.get("scope")),
                    impact=cell(record.get("decision_impact")),
                )
            )
        lines += [""]
        if context.get("evidence_truncated"):
            lines += [
                f"> 注意：账本共 {context['evidence_total']} 条，此处仅注入前 "
                f"{len(context['evidence'])} 条，**其余未展示**。",
                "",
            ]
    else:
        lines += [
            "**证据账本为空。** 这意味着本项目目前没有任何已核验证据。",
            "你的结论必须据此降级：把关键判断标为 UNKNOWN，并给出补证路径，",
            "不得假装掌握了事实。",
            "",
        ]

    lines += ["## 四、原始材料", ""]
    if context["documents"]:
        for document in context["documents"]:
            lines += [
                f"### {document['doc_id']} — {document['origin']}",
                "",
                f"- 类型：{document['media_type']}　字符数：{document['chars']}"
                f"　指纹：{document['sha256']}",
            ]
            if document.get("meta"):
                meta_bits = {
                    k: v for k, v in document["meta"].items()
                    if k in ("rows", "columns", "records", "encoding", "status", "sheet")
                }
                if meta_bits:
                    lines.append(f"- 概况：{json.dumps(meta_bits, ensure_ascii=False)}")
            if document["truncated"]:
                lines.append(
                    f"- ⚠️ 仅展示前 {DOCUMENT_EXCERPT_CHARS} 字符，"
                    f"**其余内容未展示**"
                )
            lines += ["", "```text", document["excerpt"], "```", ""]
    else:
        lines += ["（本项目尚未导入任何原始材料）", ""]

    lines += [
        "## 五、你必须输出",
        "",
        "严格按以下顺序，用 Markdown 输出：",
        "",
        "1. **结论摘要** — 不超过 5 条",
        "2. **证据表** — 主张 / 类型 / 来源或依据 / 可信度 / 限制",
        "3. **关键假设与未知项**",
        "4. **对主决策的影响** — 支持、反对，或暂不能判断",
        "5. **可执行的下一步验证** — 每项写明验证方法与停止条件",
        "",
        "## 六、证据要求",
        "",
        "- 每条主张标注 `FACT` / `INFERENCE` / `ASSUMPTION` / `UNKNOWN` 之一。",
        "- 引用账本中的证据时写出编号（如 `E-003`）。",
        "- `FACT` 必须可核验；做不到就降级为 `INFERENCE` 或 `ASSUMPTION`。",
        "- 可信度标 `HIGH` / `MEDIUM` / `LOW`，并给出理由。",
        "",
        "## 七、禁止事项",
        "",
        "- 不得编造数据、访谈、来源、竞品信息或实验结果。",
        "- 不得把示例数字、行业均值当成真实数据。",
        "- 不得用「建议做内容营销」「提升转化率」这类无法验证的结论充数。",
        "- 不要越权回答属于其他角色的问题（见角色契约中的输入边界）。",
        "",
        "## 八、验收标准",
        "",
        "- 每个结论都能追溯到账本证据、原始材料，或被明确标为假设。",
        "- 不满足上述要求时，明确写出「需要什么数据才能判断」，而不是给一个猜测。",
        "",
    ]
    return "\n".join(lines)


#: 每个阶段有**各自不同**的门禁标准，直接取自 core/REBUILD_METHOD.md。
#:
#: 这一点此前被写错了：早期版本对所有阶段套用同一套「证据是否充足」的标准，
#: 结果 DISCOVER 永远无法通过——因为 R 阶段本来就发生在补证之前，
#: 它要求的是「问题有没有界定清楚」，不是「证据够不够」。
#: 这个缺陷是接真实模型跑出来的，单元测试完全没发现。
PHASE_GATES = {
    "DISCOVER": {
        "title": "R 界定现实",
        "criteria": [
            "业务目标与观察到的症状**分开写**；两者混为一谈即不通过。",
            "缺少基线时必须标记为未知，**不得伪造基准**——但只要未知被如实标记，本阶段即可通过。",
            "说清楚「现在真正需要决定什么」、决策期限与约束。",
        ],
        "note": "本阶段**不要求证据充足**。它发生在补证之前，要求的是问题界定质量。"
                "把未知项如实列出来，就是通过。",
    },
    "EVIDENCE": {
        "title": "E 建立证据",
        "criteria": [
            "关键结论必须可追溯——能指出来源或明确指出没有来源。",
            "推断不得伪装成事实（`INFERENCE` 不得写成 `FACT`）。",
            "未知项要给出**补证路径**，而不是留空。",
        ],
        "note": "本阶段不要求未知全部消除，要求的是「知道自己在不知道什么」。",
    },
    "STRATEGY": {
        "title": "B 战略下注",
        "criteria": [
            "必须能回答「为什么选 A 而不是 B」。",
            "选项之间必须有**实质差异**；若本质相同，退回重构。",
            "写出放弃项与代价。",
        ],
        "note": "本阶段的失败模式是「给了选项但选项没有区别」，不是「证据不够」。",
    },
    "ECONOMICS": {
        "title": "U 商业成立性",
        "criteria": [
            "关键财务指标必须写明公式、分子分母、时间范围、数据来源。",
            "数据缺失时输出**区间或待验证假设**，不得给单一精确值。",
            "不得混淆收入/毛利/贡献利润/ROAS。",
        ],
        "note": "本阶段允许带假设推进——只要每个假设都被标注且给出区间。"
                "「数据不全」本身不是阻断理由，「用点估计掩盖数据不全」才是。",
    },
    "EXECUTION": {
        "title": "I 执行与观测",
        "criteria": [
            "没有测量设计的行动**不得称为实验**。",
            "每项行动绑定负责人、成本、截止时间、领先指标、结果指标与停止条件。",
        ],
        "note": "本阶段的失败模式是「把行动写成了愿望」。",
    },
    "REVIEW": {
        "title": "D 决策复盘",
        "criteria": [
            "复盘不能只写「效果良好」。",
            "必须比较**预期与实际**，并区分执行偏差、策略失效与假设错误。",
            "记录下一步如何改变。",
        ],
        "note": "本阶段的失败模式是「用印象代替数据」。没有数据时须写明「未采集到数据」。",
    },
}


def build_gate_packet(phase: str, context: dict, outputs: dict) -> str:
    """请主 Agent 判定阶段门禁。"""
    machine = load_state_machine()
    transitions = machine["transitions"].get(phase, {})
    gate = PHASE_GATES.get(phase, {"title": phase, "criteria": [], "note": ""})

    lines = [
        f"# 门禁判定 — 阶段 {phase}（{gate['title']}）",
        "",
        "你是 REBUILD 主 Agent。下面是本阶段各角色的输出，请判定阶段门禁是否通过，",
        "并选择一个迁移事件。",
        "",
        "## 本阶段可选事件",
        "",
    ]
    for event, target in transitions.items():
        lines.append(f"- `{event}` → {target}")
    lines += [
        "",
        f"## 本阶段门禁标准（{gate['title']}，来自 core/REBUILD_METHOD.md）",
        "",
    ]
    lines += [f"{i}. {c}" for i, c in enumerate(gate["criteria"], 1)]
    if gate["note"]:
        lines += ["", f"> **注意**：{gate['note']}"]
    lines += [
        "",
        "**只按本阶段的标准判定。** 不要用其他阶段的标准——每个阶段要求的东西不同，",
        "拿后一阶段的标准卡前一阶段，会让流程永远无法推进。",
        "",
        "## 证据账本现状",
        "",
        f"- 账本共 {context['evidence_total']} 条记录。",
        f"- 原始材料 {len(context['documents'])} 份。",
        "",
        "## 本阶段角色输出",
        "",
    ]
    for role, text in outputs.items():
        lines += [f"### {ROLE_LABELS.get(role, role)}", "", text.strip(), ""]

    lines += [
        "## 你的输出格式",
        "",
        "只输出一个 JSON 对象，不要任何其他文字：",
        "",
        "```json",
        "{",
        '  "event": "上面列表中的某个事件名",',
        '  "passed": true 或 false,',
        '  "evidence_grade": "SUFFICIENT | DEGRADED | INSUFFICIENT",',
        '  "reason": "判定理由，需引用具体输出内容",',
        '  "limitations": ["若降级放行，逐条写明本次结论在哪些方面不成立或未验证"],',
        '  "blocking_gaps": ["仍然缺失、必须补证的具体项"]',
        "}",
        "```",
        "",
        "## 三种合法结果（必须选其一，不要默认选最保守的那个）",
        "",
        "**① `SUFFICIENT` —— 放行。** 证据足以支撑本阶段结论，正常推进。",
        "",
        "**② `DEGRADED` —— 降级放行。** 证据不完整，但**决策本身仍可做出**，只要：",
        "   - 逐条写明 `limitations`：哪些结论不成立、哪些是假设、哪些未经实测；",
        "   - 结论按证据强度降级表述（「在 X 假设成立的前提下成立」，而不是「成立」）；",
        "   - `blocking_gaps` 列出在下一阶段之前必须补齐的项。",
        "   方法论明确允许「停留、补证或**降级输出**」。真实项目几乎不可能等到证据齐全才决策，",
        "   降级放行往往是正确选择——只要局限被写清楚，而不是被隐藏。",
        "",
        "**③ `INSUFFICIENT` —— 回退或需要澄清。** 适用于：决策**根本无法做出**，",
        "   而不只是证据不够漂亮。例如存在 P0 级一票否决项未核（命中即推翻全部结论）、",
        "   关键条款口径互相冲突且无法裁决、或所需数据只有决策者本人能提供。",
        "",
        "**判定要点：**",
        "",
        "- 本系统最严重的失败**不是**「带着不完整的证据推进」，",
        "  而是**「推进时假装证据是完整的」**。前者靠 `limitations` 解决，后者不可接受。",
        "- 如果你发现自己在列很多 gap 但仍然能够写出一个有条件的结论——那应该选 `DEGRADED`，",
        "  而不是 `INSUFFICIENT`。",
        "- 只有当**存在一票否决项未核**、或**结论方向会因缺失信息而反转**时，才选 `INSUFFICIENT`。",
        "- 不要因为「还不够完美」而阻断。阻断的代价是决策被无限期推迟，这本身也是一种损失。",
        "",
    ]
    return "\n".join(lines)


def build_decision_record_packet(context: dict, phase_outputs: dict) -> str:
    lines = [
        "# 决策记录",
        "",
        "综合全部阶段的角色输出，产出一份决策记录。",
        "",
        f"决策问题：{context['project'].get('decision_question')}",
        "",
        "## 各阶段输出摘要",
        "",
    ]
    for phase, outputs in phase_outputs.items():
        for role, text in outputs.items():
            lines += [f"### [{phase}] {ROLE_LABELS.get(role, role)}", "", text.strip(), ""]

    lines += [
        "## 输出格式",
        "",
        "只输出一个 JSON 对象，字段与 schemas/decision_record.schema.json 一致：",
        "",
        "```json",
        "{",
        '  "decision_id": "DR-001",',
        '  "question": "...",',
        '  "deadline": null,',
        '  "options": [{"name": "...", "rationale": "...", "risks": ["..."]}],',
        '  "chosen_option": "采用的方案名，或 null",',
        '  "rejected_options": [{"name": "...", "reason": "..."}],',
        '  "tradeoffs": ["..."],',
        '  "key_assumptions": ["..."],',
        '  "falsification_conditions": ["..."],',
        '  "validation_actions": ["..."],',
        '  "review_date": "YYYY-MM-DD"',
        "}",
        "```",
        "",
        "硬性要求：`options` 至少 2 个且必须实质不同；必须写出放弃项与代价；",
        "每条关键假设都要配一个能推翻它的条件。",
        "",
        "**关于 `chosen_option`：** 如果本轮的结论是「先补证再决策」，"
        "把它写为 `null`——这是**正确**的取值，不要为了填满字段而编一个方案。",
        "此时必须在 `validation_actions` 里写明补什么才能决策。",
        "编一个自己并不推荐的方案填进去，比留空严重得多。",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 输出解析
# ---------------------------------------------------------------------------

def extract_json_block(text: str):
    """从模型输出里取出第一个 JSON 对象。取不到返回 None。"""
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        stripped = "\n".join(lines)
    start = stripped.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(stripped[start:index + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---------------------------------------------------------------------------
# 编排器
# ---------------------------------------------------------------------------

class Orchestrator:
    def __init__(self, config: RunConfig, completer=None, run_label=None):
        self.config = config
        self.project_dir = config.project_dir
        self._completer = completer
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        if run_label:
            # 重复运行时用后缀区分，否则同一秒内的多次运行会写进同一个目录
            self.run_id = f"{self.run_id}-{run_label}"
        self.run_dir = self.project_dir / "runs" / self.run_id
        self.state_machine = load_state_machine()
        self.log: list[str] = []

    # -------------------------------------------------------------- provider
    def _resolve_provider(self):
        """加载并校验 provider 配置。未知名称要**尽早**报错。

        此前未知 provider 会在每个角色调用里各失败一次，被记成一串
        「角色失败」——使用者看到的是 6 个角色都挂了，而不是「你把 provider
        名字写错了」。前者会让人去查网络，后者才是真正的原因。
        """
        try:
            import provider as provider_layer  # bench/provider.py
        except ImportError as exc:
            raise OrchestratorError(f"无法加载 bench/provider.py：{exc}") from exc
        try:
            config = provider_layer.ProviderConfig.from_preset(self.config.provider_name)
        except ValueError as exc:
            raise OrchestratorError(str(exc)) from exc
        config.temperature = self.config.temperature
        config.max_tokens = self.config.max_tokens
        ok, message = provider_layer.check_available(config)
        if not ok:
            raise OrchestratorError(f"provider 配置不可用：{message}")
        return provider_layer, config

    def _complete(self, prompt: str) -> str:
        if self._completer is not None:
            return self._completer(prompt)
        if self.config.provider_name == "manual":
            raise OrchestratorError(
                "manual 模式不调用模型。请用 `--provider <名称>` 指定模型，"
                "或使用 `--dry-run` 只生成任务包。"
            )
        provider_layer, config = self._resolve_provider()
        return provider_layer.complete(config, prompt)

    # -------------------------------------------------------------- 落盘
    def _write(self, relative: str, text: str) -> Path:
        path = self.run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _note(self, message: str):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    # -------------------------------------------------------------- 主流程
    def run(self) -> dict:
        context = collect_context(
            self.project_dir,
            max_evidence=self.config.max_evidence,
            max_documents=self.config.max_documents,
        )
        current_state = context["project"].get("current_state")
        if current_state not in PHASES and current_state != "BLOCKED":
            raise OrchestratorError(f"项目状态非法：{current_state}")

        manual = self.config.provider_name == "manual" and self._completer is None

        # 尽早失败：provider 名称写错、密钥缺失之类的问题，应该在写任何产物之前
        # 就报出来，而不是等 6 个角色各失败一次。
        if not self.config.dry_run and not manual and self._completer is None:
            self._resolve_provider()

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._note(f"run_id={self.run_id} provider={self.config.provider_name} "
                   f"dry_run={self.config.dry_run}")

        report = {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "provider": self.config.provider_name,
            "mode": "dry-run" if self.config.dry_run else (
                "manual" if manual else "model"
            ),
            "initial_state": current_state,
            "phases": [],
            "gate_rejections": [],
            "evidence_total": context["evidence_total"],
            "documents": len(context["documents"]),
        }

        phase_outputs = {}
        state = current_state

        for phase in self.config.phases:
            if phase != state and not self.config.dry_run:
                self._note(f"跳过 {phase}（当前状态为 {state}）")
                report["phases"].append({"phase": phase, "skipped": True,
                                         "reason": f"当前状态为 {state}"})
                continue

            result = self._run_phase(phase, context, manual)
            report["phases"].append(result)
            if result.get("role_outputs"):
                phase_outputs[phase] = result["role_outputs"]

            if self.config.dry_run:
                continue

            gate = self._run_gate(phase, context, result.get("role_outputs") or {})
            result["gate"] = gate

            if gate.get("event"):
                try:
                    transition = self._apply_transition(
                        state, gate["event"], gate.get("reason", "")
                    )
                except OrchestratorError as exc:
                    self._note(f"拒绝非法迁移：{exc}")
                    report["gate_rejections"].append({
                        "phase": phase,
                        "event": gate["event"],
                        "error": str(exc),
                    })
                    state = "BLOCKED"
                    break
                result["transition"] = transition
                state = transition["to"]
                self._persist_state(state)
                self._note(f"{phase} + {gate['event']} → {state}")
            if state == "BLOCKED":
                self._note(f"阶段 {phase} 判定为需要澄清，编排停止")
                break

        if not self.config.dry_run and phase_outputs and not manual:
            record = self._produce_decision_record(context, phase_outputs)
            report["decision_record"] = record

        ran = [p for p in report["phases"] if not p.get("skipped")]
        if not ran and not self.config.dry_run:
            report["hint"] = self._skip_hint(current_state)
            self._note(report["hint"])

        report["final_state"] = state
        report["log"] = self.log
        self._write("run.json", json.dumps(report, ensure_ascii=False, indent=2))
        return report

    # -------------------------------------------------------------- 单阶段
    def _run_phase(self, phase: str, context: dict, manual: bool) -> dict:
        roles = PHASE_ROLES.get(phase, [])
        result = {"phase": phase, "roles": roles, "role_outputs": {}, "packets": []}

        for role in roles:
            packet = build_task_packet(role, phase, context)
            packet_path = self._write(f"{phase}/{role}.packet.md", packet)
            result["packets"].append(str(packet_path.relative_to(self.run_dir)))

            if self.config.dry_run or manual:
                continue

            try:
                output = self._complete(packet)
            except OrchestratorError:
                raise
            except Exception as exc:  # noqa: BLE001 - 单角色失败不应丢失其他产物
                self._note(f"角色 {role} 调用失败：{exc}")
                result["role_outputs"][role] = ""
                result.setdefault("errors", []).append({"role": role, "error": str(exc)})
                continue

            self._write(f"{phase}/{role}.md", output)
            result["role_outputs"][role] = output
            self._note(f"{phase}/{role} 完成（{len(output)} 字符）")

        if phase == "DISCOVER" and not (self.config.dry_run or manual):
            # DISCOVER 没有职能角色，由主 Agent 自己完成问题界定
            packet = build_task_packet("master_agent", phase, context)
            self._write(f"{phase}/master_agent.packet.md", packet)
            try:
                output = self._complete(packet)
                self._write(f"{phase}/master_agent.md", output)
                result["role_outputs"]["master_agent"] = output
            except Exception as exc:  # noqa: BLE001
                result.setdefault("errors", []).append(
                    {"role": "master_agent", "error": str(exc)}
                )

        return result

    # -------------------------------------------------------------- 门禁
    def _run_gate(self, phase: str, context: dict, outputs: dict) -> dict:
        # 角色全部调用失败时，role_outputs 里是一串空字符串——字典本身仍然为真。
        # 若不做内容检查，就会拿着空输入再去调一次模型，白花一次调用。
        if not outputs or not any(str(v).strip() for v in outputs.values()):
            return {"event": None, "passed": False,
                    "reason": "本阶段没有任何有效角色输出，无法判定门禁——"
                              "可能是所有角色调用都失败了，请查看 errors 字段"}

        packet = build_gate_packet(phase, context, outputs)
        self._write(f"{phase}/gate.packet.md", packet)
        try:
            raw = self._complete(packet)
        except Exception as exc:  # noqa: BLE001
            self._note(f"门禁判定调用失败：{exc}")
            return {"event": None, "passed": False, "reason": f"门禁判定失败：{exc}"}

        self._write(f"{phase}/gate.raw.md", raw)
        verdict = extract_json_block(raw)
        if not isinstance(verdict, dict):
            self._note(f"{phase} 门禁输出无法解析为 JSON，视为不通过")
            return {"event": None, "passed": False,
                    "reason": "门禁输出无法解析为 JSON，按不通过处理"}
        verdict.setdefault("passed", False)
        return verdict

    def _apply_transition(self, state: str, event: str, reason: str = "") -> dict:
        transitions = self.state_machine["transitions"].get(state, {})
        if event not in transitions:
            raise OrchestratorError(
                f"状态 {state} 不接受事件 '{event}'。"
                f"合法事件：{sorted(transitions)}"
            )
        return {"from": state, "event": event, "to": transitions[event],
                "reason": reason}

    def _skip_hint(self, state: str) -> str:
        """所有请求的阶段都被跳过时，给出一条**可操作**的说明。

        BLOCKED 是特例：它不在 PHASES 里，此前会输出「可用序列：[]」，
        对使用者毫无帮助——而且它恰恰是最需要指引的状态。
        这个问题是真实运行暴露出来的，不是单元测试发现的。
        """
        if state == "BLOCKED":
            exits = sorted(self.state_machine["transitions"].get("BLOCKED", {}))
            return (
                "项目当前处于 BLOCKED（等待澄清），因此不执行任何阶段。"
                "BLOCKED 不是阶段序列中的一环：需先解除阻塞，"
                f"触发 {exits} 之一才能回到 DISCOVER 重新开始。"
                "若阻塞来自门禁判定的证据不足，请先补齐证据再修改 project.json 的 current_state。"
            )
        if state not in PHASES:
            return f"项目当前状态 {state} 不在阶段序列中，无法执行。"
        remaining = PHASES[PHASES.index(state):]
        return (
            f"请求的阶段全部被跳过：项目当前状态是 {state}，"
            f"只能从该阶段起按顺序执行。可用序列：{remaining}"
        )

    def _persist_state(self, state: str):
        path = self.project_dir / "project.json"
        project = json.loads(path.read_text(encoding="utf-8"))
        project["current_state"] = state
        project["last_updated"] = _now()
        path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # -------------------------------------------------------------- 决策记录
    def _produce_decision_record(self, context: dict, phase_outputs: dict) -> dict:
        packet = build_decision_record_packet(context, phase_outputs)
        self._write("decision_record.packet.md", packet)
        try:
            raw = self._complete(packet)
        except Exception as exc:  # noqa: BLE001
            self._note(f"决策记录生成失败：{exc}")
            return {"error": str(exc)}
        self._write("decision_record.raw.md", raw)

        record = extract_json_block(raw)
        if not isinstance(record, dict):
            return {"error": "模型输出无法解析为 JSON，原始输出见 decision_record.raw.md"}

        errors, warnings = sv.validate(
            record, sv.load_schema(_ROOT / "schemas" / "decision_record.schema.json")
        )
        self._write("decision_record.json",
                    json.dumps(record, ensure_ascii=False, indent=2))
        result = {"record": record, "schema_errors": errors, "schema_warnings": warnings}
        if errors:
            self._note(f"决策记录不符合 schema：{len(errors)} 项错误")
        return result


def run_repeated(config: RunConfig, repeats: int, completer=None):
    """同一输入重复运行 N 次，用于观察运行间一致性。

    每次运行前把项目状态**重置回起始值**——否则第二次会从第一次的终态开始，
    那就不是「同一输入」了。全部跑完后也恢复到起始值，避免「重复运行」这个
    动作本身改变了项目。
    """
    if repeats < 1:
        raise OrchestratorError("repeats 至少为 1")

    project_path = Path(config.project_dir) / "project.json"
    if not project_path.exists():
        raise OrchestratorError(f"找不到项目文件：{project_path}")

    def read_state():
        return json.loads(project_path.read_text(encoding="utf-8")).get("current_state")

    def write_state(state):
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["current_state"] = state
        project_path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    original_state = read_state()
    reports = []
    try:
        for index in range(1, repeats + 1):
            write_state(original_state)
            orchestrator = Orchestrator(config, completer=completer,
                                        run_label=f"r{index}")
            reports.append(orchestrator.run())
    finally:
        write_state(original_state)
    return reports


# ---------------------------------------------------------------------------
# 证据建议（人工审核，不自动入账）
# ---------------------------------------------------------------------------

def collect_proposed_evidence(run_dir) -> list[dict]:
    """从角色输出中提取模型建议的证据条目，供**人工审核**。

    返回的条目不会被自动写入证据账本。模型输出不是证据——
    自动入账会让账本退化成「模型说过的话清单」。
    """
    run_dir = Path(run_dir)
    proposals = []
    for path in sorted(run_dir.rglob("*.md")):
        if path.name.endswith((".packet.md", ".raw.md")):
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.startswith("|---"):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 3:
                continue
            if cells[0].lower() in ("主张", "claim", "id"):
                continue
            proposals.append({
                "from": str(path.relative_to(run_dir)),
                "claim": cells[0][:300],
                "cells": cells[:8],
            })
    return proposals
