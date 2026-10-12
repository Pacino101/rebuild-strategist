#!/usr/bin/env python3
"""多次运行的比对。

为什么需要它
------------
实测同一输入、同一证据、**temperature=0**，跑三次会得到方向一致但细节差异
达 2.5 倍的输出（反证条件 6/10/15 条）。因此**单次运行的输出不是「答案」，
只是起点**。

这个模块把「多跑几次看看稳不稳」从手工动作变成可用工具。

两类结论必须分开，不能混为一谈
------------------------------
1. **过程可复现性**（本模块确定性计算）：终态、迁移路径、门禁档位、条目数量。
   这些直接可比。
2. **结论是否一致**（需要模型判定）：几份建议在**方向上**是否一致。
   这是自由文本，机械比对做不了。用 `judge_agreement()` 单独判，
   并明确标注它是模型判定，不是事实。

把第 1 类说成第 2 类，是这类工具最容易犯的错——「路径相同」不等于
「建议相同」。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _extra in (_HERE, _HERE.parent, _HERE.parent / "bench"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from orchestrator import extract_json_block  # noqa: E402

#: 路径完全一致
PATH_IDENTICAL = "PATH_IDENTICAL"
#: 终态一致但路径不同
OUTCOME_IDENTICAL = "OUTCOME_IDENTICAL"
#: 终态就不一致
OUTCOME_DIVERGENT = "OUTCOME_DIVERGENT"


class CompareError(Exception):
    """比对无法进行。"""


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

def load_run(run_dir) -> dict:
    path = Path(run_dir) / "run.json"
    if not path.exists():
        raise CompareError(f"{run_dir} 不是一次运行产物（缺少 run.json）")
    return json.loads(path.read_text(encoding="utf-8"))


def collect_runs(project_dir, last=None) -> list[dict]:
    """取项目下的运行产物，按 run_id 升序。`last` 只取最近 N 次。"""
    runs_root = Path(project_dir) / "runs"
    if not runs_root.is_dir():
        raise CompareError(
            f"{runs_root} 不存在。请先用 `run` 生成至少两次运行。"
        )
    dirs = sorted(d for d in runs_root.iterdir() if (d / "run.json").exists())
    if not dirs:
        raise CompareError(f"{runs_root} 下没有可比的运行产物")
    if last:
        dirs = dirs[-last:]
    return [load_run(d) for d in dirs]


# ---------------------------------------------------------------------------
# 抽取可比字段
# ---------------------------------------------------------------------------

def _path_of(report) -> list:
    """迁移路径：(阶段, 事件, 目标状态) 序列。跳过被跳过的阶段。"""
    path = []
    for phase in report.get("phases", []):
        if phase.get("skipped"):
            continue
        transition = phase.get("transition") or {}
        path.append((
            phase.get("phase"),
            transition.get("event"),
            transition.get("to"),
        ))
    return path


def _grades_of(report) -> dict:
    grades = {}
    for phase in report.get("phases", []):
        if phase.get("skipped"):
            continue
        gate = phase.get("gate") or {}
        grades[phase.get("phase")] = gate.get("evidence_grade") or "?"
    return grades


def _decision_of(report) -> dict:
    block = report.get("decision_record") or {}
    record = block.get("record") or {}
    return {
        "produced": bool(record),
        "error": block.get("error"),
        "schema_errors": len(block.get("schema_errors") or []),
        "chosen_option": record.get("chosen_option"),
        "options": len(record.get("options") or []),
        "rejected": len(record.get("rejected_options") or []),
        "falsification": len(record.get("falsification_conditions") or []),
        "validation": len(record.get("validation_actions") or []),
        "assumptions": len(record.get("key_assumptions") or []),
    }


def _spread(values):
    values = [v for v in values if isinstance(v, int)]
    if not values:
        return None
    return {"min": min(values), "max": max(values),
            "range": max(values) - min(values),
            "mean": round(sum(values) / len(values), 2)}


# ---------------------------------------------------------------------------
# 比对
# ---------------------------------------------------------------------------

def compare(reports) -> dict:
    """确定性比对。**只回答过程可复现性，不回答结论是否一致。**"""
    if len(reports) < 2:
        raise CompareError(f"至少需要 2 次运行才能比对，当前 {len(reports)} 次")

    paths = [_path_of(r) for r in reports]
    finals = [r.get("final_state") for r in reports]
    grades = [_grades_of(r) for r in reports]
    decisions = [_decision_of(r) for r in reports]

    if all(p == paths[0] for p in paths):
        verdict = PATH_IDENTICAL
    elif len(set(finals)) == 1:
        verdict = OUTCOME_IDENTICAL
    else:
        verdict = OUTCOME_DIVERGENT

    # 逐阶段门禁档位一致性
    all_phases = []
    for report in reports:
        for phase in report.get("phases", []):
            if not phase.get("skipped") and phase.get("phase") not in all_phases:
                all_phases.append(phase.get("phase"))

    grade_table = {}
    for phase in all_phases:
        seen = Counter(g.get(phase, "（未执行）") for g in grades)
        grade_table[phase] = {
            "distribution": dict(seen),
            "consistent": len(seen) == 1,
        }

    chosen = [d["chosen_option"] for d in decisions]
    # 「未产出决策记录」与「产出了但本轮未做选择」是两回事，必须分开表达，
    # 否则「没跑出结论」会被误读成「结论是不决策」。
    status = [
        "NOT_PRODUCED" if not d["produced"]
        else ("NULL_CHOICE" if d["chosen_option"] is None else "CHOSEN")
        for d in decisions
    ]
    counts = {
        key: _spread([d[key] for d in decisions])
        for key in ("options", "rejected", "falsification", "validation", "assumptions")
    }

    return {
        "runs": len(reports),
        "run_ids": [r.get("run_id") for r in reports],
        "process_verdict": verdict,
        "final_states": dict(Counter(finals)),
        "final_state_consistent": len(set(finals)) == 1,
        "paths": [
            " → ".join(f"{p[0]}:{p[1]}" for p in path) or "（无迁移）"
            for path in paths
        ],
        "path_consistent": all(p == paths[0] for p in paths),
        "gate_grades": grade_table,
        "decisions_produced": sum(1 for d in decisions if d["produced"]),
        "decision_errors": [d["error"] for d in decisions if d["error"]],
        "schema_error_runs": sum(1 for d in decisions if d["schema_errors"]),
        "counts": counts,
        "chosen_options": chosen,
        "decision_status": status,
        "caveat": (
            "以上全部是**过程**指标。「迁移路径相同」不等于「建议相同」——"
            "结论是否一致需要模型判定，请用 judge_agreement()。"
        ),
    }


# ---------------------------------------------------------------------------
# 结论一致性（模型判定，不是事实）
# ---------------------------------------------------------------------------

JUDGE_HEADER = """你是评审。下面是同一个问题、同一批证据下，同一个系统独立跑出的 N 份建议。
请判断它们在**方向上**是否一致——即：决策者照着其中任何一份执行，会不会走到不同的路。

只比较**方向**（做 / 不做 / 先验证 / 换方案……），不要因为措辞、条目数量、
详略程度不同就判为不一致。

## 各次运行的建议

"""

JUDGE_FOOTER = """

## 输出格式

只输出一个 JSON 对象：

```json
{
  "agree": true 或 false,
  "direction": "用一句话概括这些建议的共同方向；若不一致则写明有哪几个方向",
  "groups": [["第几次运行的编号，例如 r1"], ["r3"]],
  "why": "判定理由，需引用具体措辞",
  "confidence": "HIGH | MEDIUM | LOW"
}
```

`groups` 是把方向相同的运行归到一组。若全部一致，就只有一组。
不确定时把 `confidence` 标低，不要为了给出结论而勉强归类。
"""


def build_judge_packet(reports) -> str:
    lines = [JUDGE_HEADER]
    for index, report in enumerate(reports, 1):
        decision = _decision_of(report)
        lines.append(f"### r{index}（run_id {report.get('run_id')}）")
        lines.append("")
        if not decision["produced"]:
            lines.append(f"（未产出决策记录：{decision['error'] or '未知原因'}）")
        else:
            lines.append(f"**选择**：{decision['chosen_option']}")
            record = (report.get("decision_record") or {}).get("record") or {}
            rejected = record.get("rejected_options") or []
            if rejected:
                lines.append("")
                lines.append("**放弃**：" + "；".join(
                    str(r.get("name")) for r in rejected[:4]
                ))
        lines.append("")
    lines.append(JUDGE_FOOTER)
    return "\n".join(lines)


def judge_agreement(reports, completions):
    """用模型判定 N 份建议在方向上是否一致。

    `completions` 是一个 `callable(prompt) -> str`，由调用方提供——
    本模块不直接碰网络，便于测试与替换。

    返回的结论带 `judged_by_model: True` 标记：它是**模型判定**，不是事实。
    """
    if len(reports) < 2:
        raise CompareError("至少需要 2 次运行才能判定一致性")
    packet = build_judge_packet(reports)
    raw = completions(packet)
    verdict = extract_json_block(raw)
    if not isinstance(verdict, dict):
        return {
            "judged_by_model": True,
            "error": "模型输出无法解析为 JSON",
            "raw": raw[:2000],
        }
    verdict["judged_by_model"] = True
    verdict["caveat"] = (
        "这是**模型判定**，不是事实。它本身也可能出错，也会受温度影响。"
        "把它当作一个参考信号，不要当作结论。"
    )
    return verdict


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def render_markdown(result: dict) -> str:
    lines = [
        "# 多次运行比对",
        "",
        f"运行次数：**{result['runs']}**　"
        f"run_id：{', '.join(str(r) for r in result['run_ids'])}",
        "",
        "## 一、过程可复现性（确定性计算）",
        "",
        f"**判定：`{result['process_verdict']}`**",
        "",
        f"- 终态分布：{json.dumps(result['final_states'], ensure_ascii=False)}",
        f"- 迁移路径一致：{'是' if result['path_consistent'] else '否'}",
        "",
        "| 运行 | 迁移路径 |",
        "|---|---|",
    ]
    for run_id, path in zip(result["run_ids"], result["paths"]):
        lines.append(f"| {run_id} | {path} |")

    lines += ["", "### 逐阶段门禁档位", "",
              "| 阶段 | 分布 | 一致 |", "|---|---|---|"]
    for phase, info in result["gate_grades"].items():
        dist = "、".join(f"{k}×{v}" for k, v in info["distribution"].items())
        lines.append(f"| {phase} | {dist} | {'✅' if info['consistent'] else '❌'} |")

    lines += ["", "### 决策条目数量", "",
              "| 项 | 最小 | 最大 | 极差 | 均值 |", "|---|---|---|---|---|"]
    for key, spread in result["counts"].items():
        if spread is None:
            continue
        lines.append(
            f"| {key} | {spread['min']} | {spread['max']} | "
            f"**{spread['range']}** | {spread['mean']} |"
        )

    if result["decision_errors"]:
        lines += ["", "### 决策记录生成失败", ""]
        lines += [f"- {e}" for e in result["decision_errors"]]

    lines += ["", "## 二、各次建议（原文）", ""]
    for run_id, chosen, state in zip(result["run_ids"], result["chosen_options"],
                                     result.get("decision_status", [])):
        if state == "NOT_PRODUCED":
            shown = "（未产出决策记录）"
        elif state == "NULL_CHOICE":
            shown = f"（本轮未做出选择——chosen_option 为 null）{chosen or ''}"
        else:
            shown = chosen
        lines += [f"**{run_id}**：{shown}", ""]

    lines += [
        "> ⚠️ " + result["caveat"],
        "",
        "## 三、结论一致性",
        "",
        "需要模型判定：`judge_agreement()`。它给出的是**参考信号**，不是事实。",
        "",
    ]
    return "\n".join(lines)
