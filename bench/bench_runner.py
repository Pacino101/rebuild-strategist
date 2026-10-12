#!/usr/bin/env python3
"""
REBUILD Bench Runner — scaffolding for the blind-review controlled experiment.

Responsibilities:
  - generate blind-review packs for three configurations (A plain prompt /
    B single skill / C REBUILD)
  - randomise the presentation order of each case and hide the configuration
    identity
  - call any model API through the provider layer, or render prompts for manual
    pasting
  - collect reviewer scores and write them back into scorecard.csv
  - reveal the configuration identities (only allowed once every reviewer has
    submitted)

Design constraint: standard library only. Model calls go through the optional
provider.py layer; with no API configured it degrades to manual mode and does
not block the flow.
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

# The source prompt each configuration uses. Reviewers see blinded_id, not this
# column.
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

# A total-score gap between two reviewers above this value flags the item for
# review (full marks 32)
AGREEMENT_GAP_THRESHOLD = 6


def ensure_dirs():
    RUNS.mkdir(parents=True, exist_ok=True)
    (BENCH / "prompts").mkdir(parents=True, exist_ok=True)


def load_cases():
    cases = []
    for path in sorted((BENCH / "cases").glob("*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    if not cases:
        raise SystemExit("no case JSON found under bench/cases/")
    return cases


def blind_id(case_id, config_key, salt, run_index=1):
    """Build an unguessable id from case + config + run index + this
    experiment's salt.
    The salt is recorded in the manifest and used only at the reveal stage.
    run_index takes part in the hash so that different runs of the same
    configuration get different ids — otherwise reviewers could infer from
    repeated ids that "the same configuration ran several times", which would
    break the blind review.
    """
    raw = f"{case_id}:{config_key}:{run_index}:{salt}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"X-{digest[:10].upper()}"


def generate_manifest(salt=None, runs_per_config=1, case_filter=None):
    """Build the blind-review manifest: which outputs are presented to
    reviewers, and in what order.

    case_filter restricts the run to certain cases (the first validation usually
    runs just one).
    """
    ensure_dirs()
    cases = load_cases()
    if case_filter:
        cases = [c for c in cases if c["case_id"] == case_filter]
        if not cases:
            available = ", ".join(c["case_id"] for c in load_cases())
            raise SystemExit(f"case {case_filter} not found. Available: {available}")
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
            "duplicate blinded ids would let reviewers infer different runs of "
            "the same configuration. Re-run generate (it will use a new salt)."
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
        "REBUILD blind-review presentation order\n"
        "Note: this list contains no configuration identity. Reviewers must score "
        "each item independently, without comparing them side by side.\n\n"
        + "\n".join(review_order)
        + "\n",
        encoding="utf-8",
    )
    print(f"generated {len(entries)} blind-review items → {order_file}")
    print(f"runs per configuration: {runs_per_config}")
    print(f"Name each configuration's output after its blinded_id in the order "
          f"file and put it under {RUNS}/responses/")
    return manifest


def reviewer_template():
    """Generate a blank scoring sheet whose fields match scorecard.csv."""
    entries_path = RUNS / "review_order.txt"
    if not entries_path.exists():
        raise SystemExit("run `python bench/bench_runner.py generate` first")
    rows = [["blinded_id", "reviewer"] + RUBRIC_DIMENSIONS +
            ["total", "critical_failure_count", "notes"]]
    template = RUNS / "review_template.csv"
    with template.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"scoring sheet template → {template}")
    print("When filled in, save it as review_1.csv / review_2.csv "
          "(for reviewer 1 / reviewer 2)")
    return template


def import_reviews(*paths):
    """Validate the review files and merge them into review_merged.csv.

    utf-8-sig is accepted: reviewers often edit and save in Excel, which adds a
    BOM and turns the first column name into 'blindid' instead of 'blinded_id'.
    """
    validate_header = ["blinded_id", "reviewer"] + RUBRIC_DIMENSIONS
    merged = []
    for path in paths:
        # Try utf-8-sig first; it handles both the with-BOM and without-BOM cases
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [c for c in validate_header if c not in (reader.fieldnames or [])]
            if missing:
                hint = ""
                if reader.fieldnames and "﻿" in (reader.fieldnames[0] or ""):
                    hint = " (a BOM was detected; re-save the file as utf-8)"
                raise SystemExit(
                    f"{path} is missing fields: {', '.join(missing)}{hint}"
                )
            for row in reader:
                if not row.get("blinded_id"):
                    continue
                merged.append(row)
    if not merged:
        raise SystemExit("the review files contain no valid data rows")
    out = RUNS / "review_merged.csv"
    fieldnames = list(merged[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    print(f"merged {len(merged)} review rows → {out}")
    return merged


def reveal():
    """Reveal the configuration identities. Requires at least two reviewers,
    each having submitted every item."""
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("manifest.json not found; run generate first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    mapping = {e["blinded_id"]: e["config_key"] for e in manifest["entries"]}
    # The case id must come from the manifest. Previously config_key was written
    # into the case_id column by mistake, so the published scorecard lost the
    # real case ids (B01–B04).
    case_of = {e["blinded_id"]: e["case_id"] for e in manifest["entries"]}

    merged_path = RUNS / "review_merged.csv"
    if not merged_path.exists():
        raise SystemExit("review_merged.csv not found; run import first")

    with merged_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    reviewers = sorted({r.get("reviewer", "").strip() for r in rows if r.get("reviewer")})
    if len(reviewers) < 2:
        raise SystemExit(
            f"the blind-review protocol requires at least 2 independent "
            f"reviewers; there are only {len(reviewers)}: {reviewers}"
        )

    expected = {e["blinded_id"] for e in manifest["entries"]}
    covered = {r["blinded_id"] for r in rows}
    if covered != expected:
        raise SystemExit(
            f"review coverage is incomplete: missing {sorted(expected - covered)}"
        )

    # Every reviewer must score every item, otherwise the sample sizes per
    # configuration differ and the mean comparison is distorted (a few unscored
    # items in group A would push its mean up or down artificially).
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
            f"{r} is missing {len(missing)} items" for r, missing in incomplete.items()
        )
        raise SystemExit(
            "these reviewers have not scored every item, so the sample sizes per "
            "configuration will differ and the means are not comparable:\n"
            f"  {detail}\n"
            f"  each case × 3 configurations × {manifest['runs_per_config']} runs = "
            f"{len(expected)} items; every reviewer must score all of them."
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
    print(f"identities revealed, written to {out} ({len(key_rows)} rows)")
    print(f"key → {reveal_file}")
    return key_rows


def check_inter_reviewer_agreement():
    """Compare the score gaps between two reviewers. A large gap means the
    rubric is understood differently or the standard has drifted."""
    merged_path = RUNS / "review_merged.csv"
    if not merged_path.exists():
        raise SystemExit("review_merged.csv not found")
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
    print(f"\n=== Reviewer agreement (threshold: a gap > {AGREEMENT_GAP_THRESHOLD} points needs review) ===")
    print(f"comparable items: {total_items}")
    if not gaps:
        print("no gap above the threshold was found.")
    else:
        print(f"{len(gaps)} items show too large a gap; discuss and align, then confirm again:")
        for blinded, gap, scores in sorted(gaps, key=lambda x: -x[1]):
            detail = ", ".join(f"{k}={v:.0f}" for k, v in scores.items())
            print(f"  {blinded}  gap {gap:.0f}  ({detail})")
        print("\nHint: a large gap does not mean one reviewer is wrong; it usually "
              "means one rubric item is understood differently.")
        print("      Align the anchor definitions first and re-score; do not simply "
              "average the two away.")
    return gaps


def summarise():
    """Summarise scores by configuration and check the pass thresholds. Only
    meaningful after reveal."""
    reveal_path = RUNS / "reveal_key.json"
    if not reveal_path.exists():
        raise SystemExit("run reveal before summarising")
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

    print("\n=== Summary by configuration ===")
    print(f"{'Configuration':<28}{'N':>5}{'Mean':>8}{'Honesty':>9}{'Failures':>11}")
    report = {}
    for config in sorted(agg):
        b = agg[config]
        mean = sum(b["totals"]) / len(b["totals"]) if b["totals"] else 0
        honesty = sum(b["honesty"]) / len(b["honesty"]) if b["honesty"] else 0
        report[config] = {"n": b["n"], "mean": mean, "honesty": honesty,
                          "failures": b["failures"]}
        label = CONFIG_LABELS.get(config, config)
        print(f"{label:<28}{b['n']:>5}{mean:>8.2f}{honesty:>9.2f}{b['failures']:>11}")

    print("\n=== Gate check (preset targets, not existing results) ===")
    baseline = report.get("A", {}).get("mean", 0)
    for config, data in sorted(report.items()):
        label = CONFIG_LABELS.get(config, config)
        mean = data["mean"]
        ok_mean = mean >= GATE_THRESHOLDS["mean_total"]
        ok_honesty = data["honesty"] > 0
        lift = ((mean - baseline) / baseline * 100) if baseline else 0
        print(f"{label}")
        print(f"  mean {mean:.2f}/32  {'✓' if ok_mean else '✗'} (threshold ≥24)")
        print(f"  mean honesty {data['honesty']:.2f}  {'✓' if ok_honesty else '✗'} (threshold >0)")
        if config != "A":
            print(f"  lift over A {lift:+.1f}%  "
                  f"{'✓' if lift >= GATE_THRESHOLDS['lift_over_baseline_pct'] else '✗'}"
                  f" (threshold ≥15%)")
        if data["failures"]:
            print(f"  critical failures {data['failures']} — samples scoring 0 on honesty are judged failed by the protocol")

    print("\nNote: the above are the measured results of this run. If a threshold "
          "is not met, record it honestly and analyse why,")
    print("      and do not adjust the rubric or discard failing samples to make "
          "the result look better.")

    check_inter_reviewer_agreement()
    return report


SCORECARD_HEADER = (["case_id", "run_id", "config", "reviewer"] +
                    RUBRIC_DIMENSIONS + ["total", "critical_failure_count", "notes"])


def check_scorecard(path=None):
    """Check that scorecard.csv is internally consistent.

    The earlier CI check merely asserted "the scorecard must be empty". That
    assertion guarded against filling in numbers before running the experiment,
    but it necessarily raises false alarms once real results exist, and it
    cannot spot mis-filled rows. This checks the data itself instead: the value
    ranges, whether the total matches the sum of the dimensions, and whether any
    required field is missing.

    Note: this function only checks internal consistency; it cannot prove that
    the scores came from real reviewers. Sample size and reviewer independence
    are methodological matters and must be stated honestly in the README and the
    PILOT documents.
    """
    target = Path(path) if path else SCORECARD
    if not target.exists():
        raise SystemExit(f"{target} not found")
    with target.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.lstrip("\ufeff") for fn in (reader.fieldnames or [])]
        rows = list(reader)

    problems = []
    missing = [c for c in SCORECARD_HEADER if c not in fieldnames]
    if missing:
        problems.append(f"the header is missing fields: {', '.join(missing)}")

    try:
        known_cases = {c["case_id"] for c in load_cases()}
    except SystemExit:
        known_cases = set()

    for index, row in enumerate(rows, start=2):
        label = f"row {index}"
        for key in ("case_id", "run_id", "config", "reviewer"):
            if not (row.get(key) or "").strip():
                problems.append(f"{label}: {key} is empty")

        config = (row.get("config") or "").strip()
        if config and config not in CONFIG_LABELS:
            problems.append(f"{label}: illegal config value -> {config!r}")

        case_id = (row.get("case_id") or "").strip()
        if case_id and known_cases and case_id not in known_cases:
            problems.append(f"{label}: case_id is not in bench/cases -> {case_id!r}")

        dimensions = []
        for dimension in RUBRIC_DIMENSIONS:
            raw = (row.get(dimension) or "").strip()
            try:
                value = int(raw)
            except ValueError:
                problems.append(f"{label}: {dimension} is not an integer -> {raw!r}")
                continue
            if not 0 <= value <= 4:
                problems.append(f"{label}: {dimension} is outside 0–4 -> {value}")
            dimensions.append(value)

        if len(dimensions) == len(RUBRIC_DIMENSIONS):
            raw_total = (row.get("total") or "").strip()
            try:
                total = int(raw_total)
            except ValueError:
                problems.append(f"{label}: total is not an integer -> {raw_total!r}")
            else:
                if total != sum(dimensions):
                    problems.append(
                        f"{label}: total={total} does not match the sum of the dimensions {sum(dimensions)}"
                    )

        raw_failures = (row.get("critical_failure_count") or "").strip()
        try:
            failures = int(raw_failures)
            if failures < 0:
                problems.append(f"{label}: critical_failure_count is negative")
        except ValueError:
            problems.append(f"{label}: critical_failure_count is not an integer -> {raw_failures!r}")

    if problems:
        print("scorecard structure check failed:")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)

    if not rows:
        print("the scorecard is empty (header only): the evaluation framework is "
              "ready and there are no experiment results yet.")
        print("This is a legal state, but the README must state honestly that "
              "\"no controlled-experiment results have been published yet\".")
    else:
        reviewers = sorted({(r.get("reviewer") or "").strip() for r in rows} - {""})
        cases = sorted({(r.get("case_id") or "").strip() for r in rows} - {""})
        print(
            f"scorecard is internally consistent: {len(rows)} rows / "
            f"{len(reviewers)} reviewers / {len(cases)} cases ({', '.join(cases)})"
        )
        print("An internal check cannot prove that the sample size is sufficient "
              "or the reviewers independent — check the claims in the README.")
    return rows


def render(case_filter=None, out_dir=None):
    """Render the finished prompts. With an API it also generates output
    directly; without one it is for manual pasting."""
    ensure_dirs()
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("run `generate` first")
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
            text = (template + "\n\n---\n\n[The question to answer this time]\n\n"
                    + case["prompt"] + "\n")

        header = (f"[Blinded id] {entry['blinded_id']}\n"
                  f"[Configuration] {entry['config_key']}\n"
                  f"[Case] {entry['case_id']}\n"
                  f"[How to use] Copy everything below and paste it into a model; "
                  f"when the output is complete, save it as "
                  f"{entry['blinded_id']}.txt under {RUNS}/responses/\n\n")
        (out / f"{entry['blinded_id']}.txt").write_text(
            header + text, encoding="utf-8")
        rendered += 1

    print(f"rendered {rendered} prompts → {out}")
    return out


def execute(case_filter=None, provider_name=None, output_dir=None, overrides=None):
    """Call the API to generate every output. With no API it suggests switching
    to manual mode."""
    manifest_path = RUNS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("run `generate` first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in load_cases()}

    if not provider_name:
        print("no provider given. Two options:\n")
        print("  Option 1 (no key needed):")
        print("    python bench/bench_runner.py render"
              + (f" --case {case_filter}" if case_filter else ""))
        print("    copy the prompts into any model and put the output under bench/runs/responses/\n")
        print("  Option 2 (configure an API, run it automatically):")
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
        print(f"configuration check failed: {message}", file=sys.stderr)
        return 1
    print(f"using: {message}\n")

    responses = Path(output_dir) if output_dir else RUNS / "responses"
    responses.mkdir(parents=True, exist_ok=True)

    targets = [e for e in manifest["entries"]
               if not case_filter or e["case_id"] == case_filter]
    print(f"about to make {len(targets)} model calls (each one billed to your API account)")
    confirm = input("Run it? (y/N) ")
    if confirm.strip().lower() not in ("y", "yes"):
        print("cancelled.")
        return 1

    failures = []
    for index, entry in enumerate(targets, start=1):
        case = cases.get(entry["case_id"])
        template = (ROOT / entry["source_prompt"]).read_text(encoding="utf-8")
        if "{{PROMPT}}" in template:
            prompt = template.replace("{{PROMPT}}", case["prompt"])
        else:
            prompt = (template + "\n\n---\n\n[The question to answer this time]\n\n"
                      + case["prompt"])

        label = f"[{index}/{len(targets)}] {entry['case_id']} / {entry['config_key']}"
        print(f"{label} … ", end="", flush=True)
        try:
            text = provider_layer.complete(config, prompt)
        except RuntimeError as exc:
            print(f"failed: {exc}")
            failures.append((entry["blinded_id"], str(exc)))
            continue
        (responses / f"{entry['blinded_id']}.txt").write_text(
            text, encoding="utf-8")
        print(f"done ({len(text)} characters)")

    print(f"\nsucceeded {len(targets) - len(failures)} / {len(targets)}")
    if failures:
        print("failed items:")
        for blinded, reason in failures:
            print(f"  {blinded}: {reason}")
    print(f"output directory: {responses}")
    return 0 if not failures else 1


def main():
    parser = argparse.ArgumentParser(
        description="REBUILD bench blind-review controlled-experiment scaffolding",
        epilog="standard flow: generate → template → import → reveal → summarise",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="generate the blind-review manifest and presentation order")
    g.add_argument("--salt", default=None, help="give a salt so the same order can be reproduced")
    g.add_argument("--runs", type=int, default=1, help="number of repeated runs per configuration")
    g.add_argument("--case", default=None, help="run only the given case, e.g. B03")

    sub.add_parser("template", help="generate a blank scoring sheet")

    r = sub.add_parser("render", help="render finished prompts (for manual pasting)")
    r.add_argument("--case", default=None, help="render only the given case, e.g. B03")
    r.add_argument("--out", default=None, help="output directory")

    e = sub.add_parser("execute", help="call the model API to generate output")
    e.add_argument("--provider", default=None, help="provider name, see provider.py list")
    e.add_argument("--case", default=None, help="run only the given case, e.g. B03")
    e.add_argument("--out", default=None, help="output directory")
    e.add_argument("--base-url", default=None)
    e.add_argument("--model", default=None)
    e.add_argument("--api-key-env", dest="api_key_env", default=None)
    e.add_argument("--api-style", dest="api_style", default=None)
    e.add_argument("--temperature", type=float, default=None)
    e.add_argument("--max-tokens", dest="max_tokens", type=int, default=None)

    i = sub.add_parser("import", help="merge the review files")
    i.add_argument("files", nargs="+", help="review_1.csv review_2.csv ...")

    sub.add_parser("reveal", help="reveal identities and write the scorecard (needs ≥2 reviewers)")

    sub.add_parser("summarise", help="summarise by configuration and check the thresholds")

    c = sub.add_parser("check-scorecard", help="check whether scorecard.csv is internally consistent")
    c.add_argument("--path", default=None, help="defaults to bench/scorecard.csv")

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
