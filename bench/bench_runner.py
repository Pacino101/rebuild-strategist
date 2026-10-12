#!/usr/bin/env python3
"""
REBUILD Bench Runner — 盲评对照实验脚手架。

职责边界：
  - 生成三组配置（A 普通提示词 / B 单 Skill / C REBUILD）的盲评包
  - 随机化每个用例的呈现顺序，隐藏配置身份
  - 通过 provider 层调用任意模型 API，或渲染提示词供手动粘贴
  - 收集评审打分，回填 scorecard.csv
  - 揭示配置身份（仅在全部评审提交后才可执行）

设计约束：仅使用 Python 标准库。模型调用走 provider.py 的可选接入层，
未配置 API 时降级为手动模式，不阻塞流程。
"""
import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"
sys.path.insert(0, str(BENCH))

import provider as provider_layer
RUNS = BENCH / "runs"
SCORECARD = BENCH / "scorecard.csv"

RUBRIC_DIMENSIONS = [
    "problem_definition",
    "evidence_discipline",
    "strategic_tradeoffs",
    "business_loop",
    "validation_design",
    "falsification",
    "execution",
    "honesty",
]

CONFIG_LABELS = {
    "A": "config_A_plain_prompt",
    "B": "config_B_single_skill",
    "C": "config_C_rebuild_full",
}

# 各配置使用的原始提示词来源。评审看到的是 blinded_id，看不到这一列。
CONFIG_PROMPTS = {
    "A": "bench/prompts/A_plain.txt",
    "B": "bench/prompts/B_skill.txt",
    "C": "harness/deepseek/SKILL.md",
}

GATE_THRESHOLDS = {
    "mean_total": 24,
    "lift_over_baseline_pct": 15,
    "reproducible_number_pct": 90,
}

# 两名评审总分差超过此值即提示复核（满分 32）
AGREEMENT_GAP_THRESHOLD = 6


def ensure_dirs():
    RUNS.mkdir(parents=True, exist_ok=True)
    (BENCH / "prompts").mkdir(parents=True, exist_ok=True)


def load_cases():
    cases = []
    for path in sorted((BENCH / "cases").glob("*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    if not cases:
        raise SystemExit("bench/cases/ 下没有找到用例 JSON")
    return cases


def blind_id(case_id, config_key, salt, run_index=1):
    """由 case + config + 运行序号 + 本次实验盐值生成不可猜测的编号。
    salt 记录在 manifest 中，只有揭示阶段才使用。
    run_index 参与散列，使同一配置的不同次运行获得不同编号——
    否则评审会从重复编号推断出「同一配置跑了多次」，破坏盲评。
    """
    raw = f"{case_id}:{config_key}:{run_index}:{salt}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"X-{digest[:10].upper()}"


def generate_manifest(salt=None, runs_per_config=1, case_filter=None):
    """生成盲评 manifest：决定哪些输出以什么顺序呈现给评审。

    case_filter 限定只跑某些用例（首次验证通常只跑一个）。
    """
    ensure_dirs()
    cases = load_cases()
    if case_filter:
        cases = [c for c in cases if c["case_id"] == case_filter]
        if not cases:
            available = ", ".join(c["case_id"] for c in load_cases())
            raise SystemExit(f"找不到用例 {case_filter}。可用: {available}")
    salt = salt or f"{datetime.now(timezone.utc).timestamp():.0f}"
    rng = random.Random(salt)

    entries = []
    for case in cases:
        for config_key in ("A", "B", "C"):
            for run_index in range(1, runs_per_config + 1):
                entries.append(
                    {
                        "case_id": case["case_id"],
                        "config_key": config_key,
                        "run_index": run_index,
                        "blinded_id": blind_id(case["case_id"], config_key, salt, run_index),
                        "source_prompt": CONFIG_PROMPTS[config_key],
                    }
                )

    rng.shuffle(entries)

    ids = [e["blinded_id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise SystemExit(
            "盲评编号出现重复，会让评审推断出同配置的不同次运行。"
            "请重新运行 generate（会换用新的盐值）。"
        )
    for order, entry in enumerate(entries, start=1):
        entry["presentation_order"] = order

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "salt": salt,
        "runs_per_config": runs_per_config,
        "total_items": len(entries),
        "entries": entries,
    }
    (RUNS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    review_order = [
        f"{e['presentation_order']:>3}. {e['blinded_id']}  ({e['case_id']})"
        for e in entries
    ]
    order_file = RUNS / "review_order.txt"
    order_file.write_text(
        "REBUILD 盲评呈现顺序\n"
        "注意：此列表不含配置身份。评审须逐份独立评分，不要横向对比。\n\n"
        + "\n".join(review_order)
        + "\n",
        encoding="utf-8",
    )
    print(f"已生成 {len(entries)} 条盲评项 → {order_file}")
    print(f"每组运行次数: {runs_per_config}")
    print(f"请将各配置输出按 order 文件中的 blinded_id 命名后放入 {RUNS}/responses/")
    return manifest


def reviewer_template():
    """生成空白评分表，字段与 scorecard.csv 一致。"""
    entries_path = RUNS / "review_order.txt"
    if not entries_path.exists():
        raise SystemExit("请先运行 `python bench/bench_runner.py generate`")
    rows = [["blinded_id", "reviewer"] + RUBRIC_DIMENSIONS +
            ["total", "critical_failure_count", "notes"]]
    template = RUNS / "review_template.csv"
    with template.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"评分表模板 → {template}")
    print("填写后另存为 review_1.csv / review_2.csv（对应评审 1 / 评审 2）")
    return template


def import_reviews(*paths):
    """校验评审文件并合并，写入 review_merged.csv。

    兼容 utf-8-sig：评审常在 Excel 中编辑并保存，会带上 BOM，
    导致首列列名变成 'blindid' 而非 'blinded_id'。
    """
    validate_header = ["blinded_id", "reviewer"] + RUBRIC_DIMENSIONS
    merged = []
    for path in paths:
        # 先用 utf-8-sig 试，能同时处理有无 BOM 两种情况
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [c for c in validate_header if c not in (reader.fieldnames or [])]
            if missing:
                hint = ""
                if reader.fieldnames and "﻿" in (reader.fieldnames[0] or ""):
                    hint = "（检测到 BOM，请用 utf-8 重新保存）"
                raise SystemExit(
                    f"{path} 缺少字段: {', '.join(missing)}{hint}"
                )
            for row in reader:
                if not row.get("blinded_id"):
                    continue
                merged.append(row)
    if not merged:
        raise SystemExit("评审文件中没有有效数据行")
    out = RUNS / "review_merged.csv"
    fieldnames = list(merged[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    print(f"已合并 {len(merged)} 行评审 → {out}")
    return merged


def reveal():
    """揭示配置身份。要求至少两位评审各自提交全部条目。"""
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("找不到 manifest.json，请先运行 generate")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    mapping = {e["blinded_id"]: e["config_key"] for e in manifest["entries"]}
    # 用例编号必须来自 manifest。此前误将 config_key 写进 case_id 列，
    # 导致公布的 scorecard 丢失真实用例编号（B01–B04）。
    case_of = {e["blinded_id"]: e["case_id"] for e in manifest["entries"]}

    merged_path = RUNS / "review_merged.csv"
    if not merged_path.exists():
        raise SystemExit("找不到 review_merged.csv，请先运行 import")

    with merged_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    reviewers = sorted({r.get("reviewer", "").strip() for r in rows if r.get("reviewer")})
    if len(reviewers) < 2:
        raise SystemExit(
            f"盲评规程要求至少 2 名独立评审，当前只有 {len(reviewers)} 名：{reviewers}"
        )

    expected = {e["blinded_id"] for e in manifest["entries"]}
    covered = {r["blinded_id"] for r in rows}
    if covered != expected:
        raise SystemExit(
            f"评审覆盖不完整：缺少 {sorted(expected - covered)}"
        )

    # 每名评审都必须评完全部条目，否则各配置的样本量不等，
    # 均分对比将失真（A 组少评几条会被人为拉高或拉低）。
    per_reviewer = {}
    for row in rows:
        reviewer = row.get("reviewer", "").strip()
        per_reviewer.setdefault(reviewer, set()).add(row["blinded_id"])
    incomplete = {
        r: sorted(expected - items) for r, items in per_reviewer.items()
        if items != expected
    }
    if incomplete:
        detail = "; ".join(
            f"{r} 缺 {len(missing)} 条" for r, missing in incomplete.items()
        )
        raise SystemExit(
            "以下评审未评完全部条目，各配置样本量将不等，均分不可比：\n"
            f"  {detail}\n"
            f"  每个用例 × 3 组 × {manifest['runs_per_config']} 次 = "
            f"{len(expected)} 条，每名评审须全部评完。"
        )

    key_rows = []
    for row in rows:
        record = {
            "case_id": case_of.get(row["blinded_id"], "?"),
            "run_id": row["blinded_id"],
            "config": mapping.get(row["blinded_id"], "?"),
            "reviewer": row.get("reviewer", ""),
        }
        for dim in RUBRIC_DIMENSIONS:
            record[dim] = row.get(dim, "")
        record["total"] = row.get("total", "")
        record["critical_failure_count"] = row.get("critical_failure_count", "")
        record["notes"] = row.get("notes", "")
        key_rows.append(record)

    out = SCORECARD
    out.parent.mkdir(parents=True, exist_ok=True)
    header = (["case_id", "run_id", "config", "reviewer"] +
              RUBRIC_DIMENSIONS + ["total", "critical_failure_count", "notes"])
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(key_rows)

    reveal_file = RUNS / "reveal_key.json"
    reveal_file.write_text(
        json.dumps(
            {
                "revealed_at": datetime.now(timezone.utc).isoformat(),
                "reviewers": reviewers,
                "mapping": mapping,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"已揭示身份，写入 {out}（{len(key_rows)} 行）")
    print(f"对照表 → {reveal_file}")
    return key_rows


def check_inter_reviewer_agreement():
    """比较两名评审的分差。分差过大说明量表理解不一致或存在标准漂移。"""
    merged_path = RUNS / "review_merged.csv"
    if not merged_path.exists():
        raise SystemExit("找不到 review_merged.csv")
    with merged_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_item = {}
    for row in rows:
        try:
            score = float(row["total"])
        except (ValueError, TypeError, KeyError):
            continue
        by_item.setdefault(row["blinded_id"], {})[row.get("reviewer", "")] = score

    gaps = []
    for blinded, scores in by_item.items():
        if len(scores) < 2:
            continue
        values = list(scores.values())
        gap = max(values) - min(values)
        if gap > AGREEMENT_GAP_THRESHOLD:
            gaps.append((blinded, gap, scores))

    total_items = len([s for s in by_item.values() if len(s) >= 2])
    print(f"\n=== 评审一致性（阈值：分差 > {AGREEMENT_GAP_THRESHOLD} 分需复核）===")
    print(f"可对比条目: {total_items}")
    if not gaps:
        print("未发现超过阈值的分差。")
    else:
        print(f"发现 {len(gaps)} 条分差过大，需讨论对齐后重新确认：")
        for blinded, gap, scores in sorted(gaps, key=lambda x: -x[1]):
            detail = ", ".join(f"{k}={v:.0f}" for k, v in scores.items())
            print(f"  {blinded}  分差 {gap:.0f}  ({detail})")
        print("\n提示：分差大不等于某位评审错误，通常说明量表某一项理解不一致。")
        print("      应先对齐锚点定义再复评，不要直接取平均值了事。")
    return gaps


def summarise():
    """按配置汇总评分，检查通过门槛。仅在 reveal 之后有意义。"""
    reveal_path = RUNS / "reveal_key.json"
    if not reveal_path.exists():
        raise SystemExit("请先运行 reveal 再汇总")
    reveal = json.loads(reveal_path.read_text(encoding="utf-8"))
    mapping = reveal["mapping"]

    with SCORECARD.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    agg = {}
    for row in rows:
        config = row.get("config") or mapping.get(row.get("config_blinded", ""), "?")
        try:
            total = float(row["total"])
        except (ValueError, TypeError):
            continue
        bucket = agg.setdefault(config, {"totals": [], "honesty": [], "failures": 0, "n": 0})
        bucket["totals"].append(total)
        bucket["n"] += 1
        try:
            bucket["honesty"].append(float(row["honesty"]))
        except (ValueError, TypeError):
            pass
        try:
            bucket["failures"] += int(row.get("critical_failure_count") or 0)
        except (ValueError, TypeError):
            pass

    print("\n=== 按配置汇总 ===")
    print(f"{'配置':<28}{'样本':>5}{'均分':>8}{'诚实性':>9}{'致命失败':>11}")
    report = {}
    for config in sorted(agg):
        b = agg[config]
        mean = sum(b["totals"]) / len(b["totals"]) if b["totals"] else 0
        honesty = sum(b["honesty"]) / len(b["honesty"]) if b["honesty"] else 0
        report[config] = {"n": b["n"], "mean": mean, "honesty": honesty,
                          "failures": b["failures"]}
        label = CONFIG_LABELS.get(config, config)
        print(f"{label:<28}{b['n']:>5}{mean:>8.2f}{honesty:>9.2f}{b['failures']:>11}")

    print("\n=== 门槛检查（预设目标，非既有成绩）===")
    baseline = report.get("A", {}).get("mean", 0)
    for config, data in sorted(report.items()):
        label = CONFIG_LABELS.get(config, config)
        mean = data["mean"]
        ok_mean = mean >= GATE_THRESHOLDS["mean_total"]
        ok_honesty = data["honesty"] > 0
        lift = ((mean - baseline) / baseline * 100) if baseline else 0
        print(f"{label}")
        print(f"  均分 {mean:.2f}/32  {'✓' if ok_mean else '✗'} (门槛 ≥24)")
        print(f"  诚实性均值 {data['honesty']:.2f}  {'✓' if ok_honesty else '✗'} (门槛 >0)")
        if config != "A":
            print(f"  相对 A 提升 {lift:+.1f}%  "
                  f"{'✓' if lift >= GATE_THRESHOLDS['lift_over_baseline_pct'] else '✗'}"
                  f" (门槛 ≥15%)")
        if data["failures"]:
            print(f"  致命失败 {data['failures']} 次 — 诚实性 0 分样本按规程判定失败")

    print("\n注意：以上为本次实测结果。若未达门槛，应如实记录并分析原因，")
    print("      不得调整量表或丢弃失败样本来美化结果。")

    check_inter_reviewer_agreement()
    return report


SCORECARD_HEADER = (["case_id", "run_id", "config", "reviewer"] +
                    RUBRIC_DIMENSIONS + ["total", "critical_failure_count", "notes"])


def check_scorecard(path=None):
    """校验 scorecard.csv 是否自洽。

    先前的 CI 检查只断言「scorecard 必须为空」。那个断言能防住「还没跑实验就填数」，
    但一旦有了真实结果就必然误报，且无法识别填错的行。这里改为校验数据本身：
    取值域、总分与分项之和是否一致、必填字段是否缺失。

    注意：本函数只校验结构自洽，无法证明评分来自真实评审。
    样本量与评审独立性属于方法学问题，须在 README 与 PILOT 文档中如实声明。
    """
    target = Path(path) if path else SCORECARD
    if not target.exists():
        raise SystemExit(f"找不到 {target}")
    with target.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.lstrip("\ufeff") for fn in (reader.fieldnames or [])]
        rows = list(reader)

    problems = []
    missing = [c for c in SCORECARD_HEADER if c not in fieldnames]
    if missing:
        problems.append(f"表头缺少字段: {', '.join(missing)}")

    try:
        known_cases = {c["case_id"] for c in load_cases()}
    except SystemExit:
        known_cases = set()

    for index, row in enumerate(rows, start=2):
        label = f"第 {index} 行"
        for key in ("case_id", "run_id", "config", "reviewer"):
            if not (row.get(key) or "").strip():
                problems.append(f"{label}: {key} 为空")

        config = (row.get("config") or "").strip()
        if config and config not in CONFIG_LABELS:
            problems.append(f"{label}: config 取值非法 -> {config!r}")

        case_id = (row.get("case_id") or "").strip()
        if case_id and known_cases and case_id not in known_cases:
            problems.append(f"{label}: case_id 不在 bench/cases 中 -> {case_id!r}")

        dimensions = []
        for dimension in RUBRIC_DIMENSIONS:
            raw = (row.get(dimension) or "").strip()
            try:
                value = int(raw)
            except ValueError:
                problems.append(f"{label}: {dimension} 不是整数 -> {raw!r}")
                continue
            if not 0 <= value <= 4:
                problems.append(f"{label}: {dimension} 超出 0–4 -> {value}")
            dimensions.append(value)

        if len(dimensions) == len(RUBRIC_DIMENSIONS):
            raw_total = (row.get("total") or "").strip()
            try:
                total = int(raw_total)
            except ValueError:
                problems.append(f"{label}: total 不是整数 -> {raw_total!r}")
            else:
                if total != sum(dimensions):
                    problems.append(
                        f"{label}: total={total} 与分项之和 {sum(dimensions)} 不一致"
                    )

        raw_failures = (row.get("critical_failure_count") or "").strip()
        try:
            failures = int(raw_failures)
            if failures < 0:
                problems.append(f"{label}: critical_failure_count 为负")
        except ValueError:
            problems.append(f"{label}: critical_failure_count 不是整数 -> {raw_failures!r}")

    if problems:
        print("scorecard 结构校验失败：")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)

    if not rows:
        print("scorecard 为空（仅表头）：评测框架已就绪，尚无实验结果。")
        print("这是合法状态，但 README 必须如实说明「尚未公布任何对照实验结果」。")
    else:
        reviewers = sorted({(r.get("reviewer") or "").strip() for r in rows} - {""})
        cases = sorted({(r.get("case_id") or "").strip() for r in rows} - {""})
        print(
            f"scorecard 结构自洽：{len(rows)} 行 / {len(reviewers)} 名评审 / "
            f"{len(cases)} 个用例（{', '.join(cases)}）"
        )
        print("结构校验不能证明样本量充足或评审独立——请核对 README 中的声明。")
    return rows


def render(case_filter=None, out_dir=None):
    """渲染提示词成品。有 API 时同时直接生成输出，无 API 时供人工粘贴。"""
    ensure_dirs()
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("请先运行 `generate`")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    out = Path(out_dir) if out_dir else RUNS / "prompts_ready"
    out.mkdir(parents=True, exist_ok=True)
    cases = {c["case_id"]: c for c in load_cases()}

    rendered = 0
    for entry in manifest["entries"]:
        if case_filter and entry["case_id"] != case_filter:
            continue
        case = cases.get(entry["case_id"])
        if case is None:
            continue
        template_path = ROOT / entry["source_prompt"]
        template = template_path.read_text(encoding="utf-8")
        if "{{PROMPT}}" in template:
            text = template.replace("{{PROMPT}}", case["prompt"])
        else:
            text = (template + "\n\n---\n\n【本次要回答的问题】\n\n"
                    + case["prompt"] + "\n")

        header = (f"【盲评编号】{entry['blinded_id']}\n"
                  f"【配置】{entry['config_key']}\n"
                  f"【用例】{entry['case_id']}\n"
                  f"【用法】复制以下全部内容，粘贴给模型；输出完成后另存为 "
                  f"{entry['blinded_id']}.txt 放入 {RUNS}/responses/\n\n")
        (out / f"{entry['blinded_id']}.txt").write_text(
            header + text, encoding="utf-8")
        rendered += 1

    print(f"已渲染 {rendered} 份提示词 → {out}")
    return out


def execute(case_filter=None, provider_name=None, output_dir=None, overrides=None):
    """调用 API 生成全部输出。无 API 时提示改用手动模式。"""
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("请先运行 `generate`")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in load_cases()}

    if not provider_name:
        print("未指定 provider。两种方式：\n")
        print("  方式一（无需密钥）：")
        print("    python bench/bench_runner.py render"
              + (f" --case {case_filter}" if case_filter else ""))
        print("    复制提示词到任意模型，拿回输出放入 bench/runs/responses/\n")
        print("  方式二（配置 API，自动跑）：")
        print("    python bench/provider.py check deepseek")
        print("    export DEEPSEEK_API_KEY=sk-xxx")
        print("    python bench/bench_runner.py execute --provider deepseek"
              + (f" --case {case_filter}" if case_filter else ""))
        return 1

    config = provider_layer.ProviderConfig.from_preset(provider_name)
    for attr, value in (overrides or {}).items():
        setattr(config, attr, value)

    ok, message = provider_layer.check_available(config)
    if not ok:
        print(f"配置检查未通过：{message}", file=sys.stderr)
        return 1
    print(f"使用：{message}\n")

    responses = Path(output_dir) if output_dir else RUNS / "responses"
    responses.mkdir(parents=True, exist_ok=True)

    targets = [e for e in manifest["entries"]
               if not case_filter or e["case_id"] == case_filter]
    print(f"将调用 {len(targets)} 次模型（每次费用由你的 API 账户承担）")
    confirm = input("确认执行？(y/N) ")
    if confirm.strip().lower() not in ("y", "yes"):
        print("已取消。")
        return 1

    failures = []
    for index, entry in enumerate(targets, start=1):
        case = cases.get(entry["case_id"])
        template = (ROOT / entry["source_prompt"]).read_text(encoding="utf-8")
        if "{{PROMPT}}" in template:
            prompt = template.replace("{{PROMPT}}", case["prompt"])
        else:
            prompt = (template + "\n\n---\n\n【本次要回答的问题】\n\n"
                      + case["prompt"])

        label = f"[{index}/{len(targets)}] {entry['case_id']} / {entry['config_key']}"
        print(f"{label} … ", end="", flush=True)
        try:
            text = provider_layer.complete(config, prompt)
        except RuntimeError as exc:
            print(f"失败：{exc}")
            failures.append((entry["blinded_id"], str(exc)))
            continue
        (responses / f"{entry['blinded_id']}.txt").write_text(
            text, encoding="utf-8")
        print(f"完成（{len(text)} 字符）")

    print(f"\n成功 {len(targets) - len(failures)} / {len(targets)}")
    if failures:
        print("失败条目：")
        for blinded, reason in failures:
            print(f"  {blinded}: {reason}")
    print(f"输出目录：{responses}")
    return 0 if not failures else 1


def main():
    parser = argparse.ArgumentParser(
        description="REBUILD bench 盲评对照实验脚手架",
        epilog="标准流程: generate → template → import → reveal → summarise",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="生成盲评 manifest 与呈现顺序")
    g.add_argument("--salt", default=None, help="指定盐值以便复现同一顺序")
    g.add_argument("--runs", type=int, default=1, help="每组重复运行次数")
    g.add_argument("--case", default=None, help="只跑指定用例，如 B03")

    sub.add_parser("template", help="生成空白评分表")

    r = sub.add_parser("render", help="渲染提示词成品（供手动粘贴）")
    r.add_argument("--case", default=None, help="只渲染指定用例，如 B03")
    r.add_argument("--out", default=None, help="输出目录")

    e = sub.add_parser("execute", help="调用模型 API 生成输出")
    e.add_argument("--provider", default=None, help="provider 名称，见 provider.py list")
    e.add_argument("--case", default=None, help="只跑指定用例，如 B03")
    e.add_argument("--out", default=None, help="输出目录")
    e.add_argument("--base-url", default=None)
    e.add_argument("--model", default=None)
    e.add_argument("--api-key-env", dest="api_key_env", default=None)
    e.add_argument("--api-style", dest="api_style", default=None)
    e.add_argument("--temperature", type=float, default=None)
    e.add_argument("--max-tokens", dest="max_tokens", type=int, default=None)

    i = sub.add_parser("import", help="合并评审文件")
    i.add_argument("files", nargs="+", help="review_1.csv review_2.csv ...")

    sub.add_parser("reveal", help="揭示身份并写入 scorecard（需 ≥2 名评审）")

    sub.add_parser("summarise", help="按配置汇总并检查门槛")

    c = sub.add_parser("check-scorecard", help="校验 scorecard.csv 结构是否自洽")
    c.add_argument("--path", default=None, help="默认 bench/scorecard.csv")

    args = parser.parse_args()
    if args.cmd == "generate":
        generate_manifest(salt=args.salt, runs_per_config=args.runs,
                          case_filter=args.case)
    elif args.cmd == "template":
        reviewer_template()
    elif args.cmd == "render":
        render(case_filter=args.case, out_dir=args.out)
    elif args.cmd == "execute":
        overrides = {
            k: v for k, v in {
                "base_url": args.base_url,
                "model": args.model,
                "api_key_env": args.api_key_env,
                "api_style": args.api_style,
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
            }.items() if v is not None
        }
        return execute(case_filter=args.case, provider_name=args.provider,
                       output_dir=args.out, overrides=overrides)
    elif args.cmd == "import":
        import_reviews(*args.files)
    elif args.cmd == "reveal":
        reveal()
    elif args.cmd == "summarise":
        summarise()
    elif args.cmd == "check-scorecard":
        check_scorecard(args.path)


if __name__ == "__main__":
    sys.exit(main())
