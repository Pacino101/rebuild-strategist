#!/usr/bin/env bash
# Verify the rebuild-strategist DSH skill package.
# Usage: ./tests/verify_package.sh [path-to-skill-dir]
# Exits non-zero on any failure. Read-only: never modifies the package.
set -u

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL="$ROOT/SKILL.md"
fail=0
note() { printf '  %-6s %s\n' "$1" "$2"; }
ok()   { note "ok" "$1"; }
bad()  { note "FAIL" "$1"; fail=$((fail+1)); }

echo "Verifying skill package at: $ROOT"

# ---------------------------------------------------------------- SKILL.md
[ -f "$SKILL" ] || { bad "SKILL.md missing"; exit 1; }

python3 - "$SKILL" <<'PY' || fail=$((fail+1))
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', s, re.S)
if not m:
    print("  FAIL   frontmatter missing or not delimited by --- lines"); sys.exit(1)
fm, body = m.group(1), s[m.end():]
errs = []
name = re.search(r'^name:\s*(\S+)\s*$', fm, re.M)
if not name:
    errs.append("frontmatter has no name")
elif not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name.group(1)):
    errs.append(f"name '{name.group(1)}' is not kebab-case (fatal: skill is dropped)")
desc = re.search(r'^description:\s*(.+?)(?=\n[a-zA-Z_-]+:|\Z)', fm, re.S | re.M)
if not desc or not re.sub(r'\s+', ' ', desc.group(1)).strip():
    errs.append("frontmatter has no description (fatal: skill is dropped)")
for legacy in ("disableModelInvocation", "modelInvocable", "userInvocable"):
    if legacy in fm:
        errs.append(f"legacy camelCase key '{legacy}' throws and drops the skill")
if len(body.strip()) < 500:
    errs.append("body is suspiciously short")
if errs:
    for e in errs:
        print(f"  FAIL   {e}")
    sys.exit(1)
print(f"  ok     frontmatter valid (name={name.group(1)}, description={len(re.sub(chr(92)+'s+', ' ', desc.group(1)).strip())} chars, body={len(body)} chars)")
PY

# ------------------------------------------------- dead links in SKILL.md
# Resolve exactly as the model is told to: against the skill BASE DIRECTORY.
# So `resources/X.md` -> <base>/resources/X.md, and a bare `X.md` -> <base>/X.md.
# A bare name that only exists under resources/ is a REAL bug, not a pass.
MISSING=$(python3 - "$ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
body = open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
refs = set()
for raw in re.findall(r'`([^`]+)`', body):
    r = raw.strip()
    if r.startswith("resources/"):
        refs.add(r)
    elif re.fullmatch(r'[A-Za-z0-9_-]+\.(?:md|ya?ml|json)', r):
        refs.add(r)          # bare: must exist at the base dir itself
    elif re.fullmatch(r'schemas/?', r):
        refs.add("resources/schemas")
    elif re.fullmatch(r'resources/schemas/?', r):
        refs.add("resources/schemas")
out = [r for r in sorted(refs) if not os.path.exists(os.path.join(root, r))]
print("\n".join(out))
PY
)

# Worst-case rendered size using the REAL installed base path (the exact string the
# loader prints) plus the fixed wrapper the dsh-skill renderer adds.
BASE="$(cd "$ROOT" && pwd)"
python3 - "$ROOT" "$BASE" <<'PY' || fail=$((fail+1))
import os, re, sys
root, base = sys.argv[1], sys.argv[2]
s = open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', s, re.S)
body = s[m.end():] if m else s
wrapper = ('<skill_content name="rebuild-strategist">\n<skill_resources>\n'
           f'Base directory for this skill: {base}\n'
           'Resolve relative paths mentioned by this skill against the base directory before '
           'using them. Load referenced resources only as needed.\n</skill_resources>\n\n'
           '<skill_instructions>\n' + body + '\n</skill_instructions>\n</skill_content>')
n = len(wrapper)
if n >= 8192:
    print(f"  FAIL   rendered body {n} chars exceeds the 8192 pruner threshold (base path {len(base)} chars)")
    sys.exit(1)
print(f"  ok     rendered body {n} chars, under the 8192 pruner threshold")
PY

# ------------------------------------------- output-envelope consistency
python3 - "$ROOT" <<'PY' || fail=$((fail+1))
import os, re, sys
root = sys.argv[1]
FIELDS = ["summary", "findings[]", "evidence[]", "assumptions[]", "unknowns[]",
          "recommendation", "confidence", "dependencies", "risks", "next_actions[]"]
targets = ["SKILL.md", "resources/DSH_ADAPTER.md", "resources/AGENT_ROSTER.md"]
bad = []
for t in targets:
    p = os.path.join(root, t)
    if not os.path.exists(p):
        bad.append(f"{t}: missing"); continue
    s = open(p, encoding="utf-8").read()
    if "next_actions" not in s:
        bad.append(f"{t}: does not mention next_actions[]")
    if re.search(r'\bnine\b', s) and "next_actions" in s:
        bad.append(f"{t}: says 'nine' but lists next_actions[]")
if bad:
    for b in bad:
        print(f"  FAIL   output envelope inconsistent: {b}")
    sys.exit(1)
print(f"  ok     output envelope consistent across {len(targets)} files (10 fields)")
PY

# ------------------------------------------------ prose <-> schema agreement
python3 - "$ROOT" <<'PY' || fail=$((fail+1))
import json, os, re, sys
root = sys.argv[1]
SCHEMAS = os.path.join(root, "resources", "schemas")
body = open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
ops = open(os.path.join(root, "resources", "OPERATING_RULES.md"), encoding="utf-8").read()
prose = body + ops
S = {n: json.load(open(os.path.join(SCHEMAS, n), encoding="utf-8"))
     for n in os.listdir(SCHEMAS) if n.endswith(".json")}
errs = []

# 1. Every prose-mandated state element must be representable somewhere in the state schema.
state = S["project_state.schema.json"]
props = state.get("properties", {})
for need, where in [("kpi tree", "kpi_tree"), ("experiments", "experiments"),
                    ("decisions", "decisions"), ("assumptions", "assumptions"),
                    ("tasks", "tasks"), ("risks", "risks"),
                    ("open questions", "open_questions"), ("change log", "change_log"),
                    ("consumer", "consumer"), ("market", "market"),
                    ("opportunity", "opportunity"), ("strategy", "strategy"),
                    ("execution", "execution"), ("review", "review"),
                    ("problem tree", "problem")]:
    if need.split()[0] in prose.lower() and where not in props:
        errs.append(f"prose names '{need}' but project_state has no '{where}' property")
contract = props.get("project_contract", {}).get("properties", {})
for need in ["objective", "audience", "deliverable", "approval_needs", "unknowns", "available_data"]:
    if need not in contract:
        errs.append(f"Project Contract prose names '{need}' but project_contract lacks it")

# 2. Schemas must actually be wired: every schema has $id, and cross-file $refs resolve.
for name, doc in S.items():
    if "$id" not in doc:
        errs.append(f"{name}: missing $id (cannot be referenced)")
    for ref in set(re.findall(r'"\$ref"\s*:\s*"([^"]+)"', json.dumps(doc))):
        if ref.startswith("#/$defs/"):
            if ref[len("#/$defs/"):] not in doc.get("$defs", {}):
                errs.append(f"{name}: unresolved internal $ref {ref}")
        elif ".json#" in ref:
            target, frag = ref.split("#", 1)
            path = os.path.join(SCHEMAS, target)
            if not os.path.exists(path):
                errs.append(f"{name}: $ref points at missing file {target}")
            else:
                other = json.load(open(path, encoding="utf-8"))
                key = frag.rsplit("/", 1)[-1]
                if key not in other.get("$defs", {}):
                    errs.append(f"{name}: $ref {ref} does not resolve in {target}")
        elif ref.endswith(".json"):
            if not os.path.exists(os.path.join(SCHEMAS, ref)):
                errs.append(f"{name}: $ref points at missing file {ref}")
        else:
            errs.append(f"{name}: unsupported $ref {ref}")

# 3. Enums must express what the prose requires.
if "proposal" in prose or "proposals until approved" in prose:
    if "proposed" not in S["experiment.schema.json"]["properties"]["status"]["enum"]:
        errs.append("prose requires proposals-until-approved but experiment status enum lacks 'proposed'")
# enums may be declared inline or via $ref to $defs — resolve both.
def enum_of(schema, filename, *path):
    node = S[filename]
    for key in path:
        node = node[key]
    if "$ref" in node:
        ref = node["$ref"]
        if ref.startswith("#/$defs/"):
            return S[filename].get("$defs", {}).get(ref[len("#/$defs/"):], {}).get("enum", [])
        if ".json#" in ref:
            fn, frag = ref.split("#")
            return S[fn].get("$defs", {}).get(frag.rsplit("/", 1)[-1], {}).get("enum", [])
        return []
    return node.get("enum", [])

cal = enum_of(S, "task_packet.schema.json", "properties", "inputs", "items", "properties", "source_status")
if "calculated" not in cal:
    errs.append("prose treats a reproducible calculation as FACT but task_packet source_status lacks 'calculated'")
ev_labels = enum_of(S, "evidence.schema.json", "properties", "label")
for lab in ["FACT", "INTERPRETATION", "HYPOTHESIS", "DECISION", "UNKNOWN"]:
    if lab not in ev_labels:
        errs.append(f"evidence label enum is missing {lab}")

if errs:
    for e in errs:
        print(f"  FAIL   {e}")
    sys.exit(1)
print("  ok     prose requirements are representable, schemas wired, enums complete")
PY

# ------------------------------------------- state document actually validates
# The ad-hoc checker that used to live here was replaced by tests/schema_validator.py plus
# tests/test_validator.py. It twice passed documents it should have rejected, which is
# exactly the "looks like governance, validates nothing" failure this project warns about.
python3 - "$ROOT" <<'PY' || fail=$((fail+1))
import json, os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tests"))
from schema_validator import Validator
SCHEMAS = os.path.join(root, "resources", "schemas")
def load(name):
    with open(os.path.join(SCHEMAS, name), encoding="utf-8") as fh:
        return Validator(json.load(fh), root_dir=SCHEMAS)
state = load("project_state.schema.json")
VALID_STATE = {
 "project_id":"p","project_name":"n","version":"1","current_phase":"B",
 "project_contract":{"objective":"decide","decision_maker":"CEO","audience":"a"},
 "gate_status":{"R":"PASS","E":"PASS_WITH_GAPS"},
 "kpi_tree":{"root":{"metric_name":"m","metric_type":"outcome","definition":"d","unit":"%",
   "period":"p","source_of_truth":"s","owner":"o","target":"+8pp"}},
 "decisions":[],"evidence":[],"assumptions":[],"tasks":[],"risks":[],
 "open_questions":[],"change_log":[],
}
errs = state.iter_errors(VALID_STATE)
if errs:
    print("  FAIL   a documented state document does not validate:")
    for e in errs[:5]: print(f"         {e}")
    sys.exit(1)
bad = [{"garbage": 1}, {}, {"metric_name": "m"}]
if not all(not load("kpi_tree.schema.json").is_valid(b) for b in bad):
    print("  FAIL   kpi_tree accepts a malformed tree")
    sys.exit(1)
print("  ok     full state document validates; malformed KPI trees rejected")
PY
# --------------------------------------------- deterministic arithmetic self-test
if [ -f "$ROOT/tools/strategy_calc.py" ]; then
  if python3 "$ROOT/tools/strategy_calc.py" --check >/tmp/calc.out 2>&1; then
    ok "strategy arithmetic self-test passes (no model involved)"
  else
    bad "strategy_calc self-test failed"
    grep -E "FAIL|RESULT" /tmp/calc.out | head -5 | sed 's/^/         /'
  fi
else
  bad "tools/strategy_calc.py missing — the skill's numbers would have no executable basis"
fi

# --------------------------------------------- adapter contract
if [ -f "$ROOT/tools/check_adapter.py" ]; then
  if python3 "$ROOT/tools/check_adapter.py" --self-test >/tmp/adapter.out 2>&1; then
    ok "adapter checker rejects malformed adapters (self-test)"
  else
    bad "adapter checker self-test failed"
    grep -E "FAIL|RESULT" /tmp/adapter.out | head -5 | sed 's/^/         /'
  fi
  ADAPTERS_OK=0
  python3 "$ROOT/tools/check_adapter.py" --adapter "$ROOT/tools/adapters/csv_export.py" \
      -- --input "$ROOT/examples/adapter/figures.csv" >/tmp/a1.out 2>&1 && ADAPTERS_OK=$((ADAPTERS_OK+1))
  python3 "$ROOT/tools/check_adapter.py" --adapter "$ROOT/tools/adapters/posthog.py" \
      -- --offline "$ROOT/examples/adapter/posthog_retention.json" >/tmp/a2.out 2>&1 && ADAPTERS_OK=$((ADAPTERS_OK+1))
  python3 "$ROOT/tools/check_adapter.py" --adapter "$ROOT/tools/adapters/upstream_json.py" \
      -- --file "$ROOT/examples/adapter/upstream_envelope.json" >/tmp/a3.out 2>&1 && ADAPTERS_OK=$((ADAPTERS_OK+1))
  if [ "$ADAPTERS_OK" -eq 3 ]; then
    ok "3 reference adapters honour the contract (manual, live, tool-to-tool)"
  else
    bad "only $ADAPTERS_OK of 3 reference adapters pass the contract"
    cat /tmp/a1.out /tmp/a2.out /tmp/a3.out 2>/dev/null | grep -E "FAIL|rule" | head -5 | sed 's/^/         /'
  fi
else
  bad "tools/check_adapter.py missing — the adapter contract would be unenforceable"
fi

# --------------------------------------------- validator + adversarial suite
if [ -f "$ROOT/tests/test_validator.py" ]; then
  if python3 "$ROOT/tests/test_validator.py" >/tmp/validator.out 2>&1; then
    ok "schemas are quality-checked: adversarial documents rejected, valid ones accepted"
  else
    bad "schema validator or adversarial suite failed (see below)"
    sed 's/^/         /' /tmp/validator.out | grep -E "FAIL|Error" | head -5
  fi
else
  bad "tests/test_validator.py missing — schemas cannot be quality-checked"
fi

# -------------------------------------------------------- release readiness
python3 - "$ROOT" <<'PY' || fail=$((fail+1))
import os, re, sys
root = sys.argv[1]
required = {
    "LICENSE": "an explicit licence",
    "README.md": "an entry point for visitors",
    "CONTRIBUTING.md": "contribution rules",
    "CHANGELOG.md": "a change history",
    ".gitignore": "so client state is not committed accidentally",
    "SKILL.md": "the skill itself",
    "tests/SMOKE_TESTS.md": "behavioural tests",
    "tests/RESULTS.md": "the honest test log",
    "tests/schema_validator.py": "the schema validator",
    "tests/test_validator.py": "validator unit + adversarial tests",
    ".github/workflows/verify.yml": "CI so the claims are checked automatically",
    "examples/refusal-demo/demo.py": "the rules executed without a model",
    "tools/strategy_calc.py": "deterministic strategy arithmetic",
    "tools/check_adapter.py": "the adapter contract, enforced",
    "tools/adapters/csv_export.py": "a reference data adapter (manual path)",
    "tools/adapters/posthog.py": "a live-API adapter (product analytics)",
    "tools/adapters/upstream_json.py": "a tool-to-tool adapter (MCP / warehouse)",
    "resources/ADAPTER_CONTRACT.md": "how to plug in your own data or model",
    "resources/schemas/adapter_output.schema.json": "the adapter output contract",
}
errs = [f"{f} is missing ({why})" for f, why in required.items()
        if not os.path.exists(os.path.join(root, f))]

# README must not over-claim: no test may be described as passing while RESULTS says UNVERIFIED.
res = os.path.join(root, "tests", "RESULTS.md")
if os.path.exists(res):
    r = open(res, encoding="utf-8").read()
    if "UNVERIFIED" in r:
        readme = open(os.path.join(root, "README.md"), encoding="utf-8").read().lower()
        for phrase in ["all tests pass", "tests pass", "fully tested", "all smoke tests pass",
                       "tests passing"]:
            if phrase in readme:
                errs.append(f"README claims '{phrase}' while tests/RESULTS.md records UNVERIFIED runs")

# The legacy archive must be marked superseded, not presented as current guidance.
leg = os.path.join(root, "docs", "LEGACY_SKILL_V3.md")
if os.path.exists(leg) and "SUPERSEDED" not in open(leg, encoding="utf-8").read()[:600].upper():
    errs.append("docs/LEGACY_SKILL_V3.md is not banner-marked as superseded")

if errs:
    for e in errs:
        print(f"  FAIL   {e}")
    sys.exit(1)
print(f"  ok     release-ready: {len(required)} required files present, no over-claiming in README")
PY

echo
if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS (all static checks)"
else
  echo "RESULT: FAIL ($fail check(s) failed)"
fi
exit "$fail"
