"""真实项目案例的脱敏守卫。

`examples/metro_apartment/` 是真实商业项目的脱敏版。脱敏一旦被后续改动破坏
（比如有人回滚了文件、或新加了一份未脱敏材料），泄露是**不可逆的**——
一旦推进公开仓库，历史里就永久留痕。

因此这里把「脱敏是否完整」变成 CI 能抓住的错误。

**本测试刻意只检查通用模式，不包含任何原始术语清单。**
把术语清单写进测试文件，等于把脱敏又还原了一遍。
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "metro_apartment"

#: 只扫案例内容本身；说明文档里会引用这些模式作为示例命令。
CONTENT_DIRS = ["source", "rebuild"]

#: 通用泄露模式。命中即说明脱敏被破坏。
#: 负向后顾用于排除「同一集团」「该集团」这类普通行文，避免误报。
_GENERIC = "同该本双两母子各"

LEAK_PATTERNS = [
    (re.compile(rf"(?<![{_GENERIC}])[一-龥]{{2,12}}(有限公司|股份有限公司|研究院|事务所)"),
     "疑似公司/机构全称"),
    (re.compile(rf"(?![{_GENERIC}])[一-龥]{{2,10}}集团"),
     "疑似集团公司名"),
    (re.compile(r"[一-龥]{2,6}(路|街|道)[0-9]+号"),
     "具体门牌号"),
    (re.compile(r"[一-龥]{2,5}地铁站"),
     "具体地铁站名"),
    (re.compile(r"〔\s*20\d{2}\s*〕\s*\d+\s*号"),
     "具体政策文号"),
    (re.compile(r"/Users/[^\s`\"']*"),
     "本地绝对路径（含用户名）"),
    (re.compile(r"/home/[^\s`\"']*"),
     "本地绝对路径"),
    (re.compile(r"[A-Za-z]:\\\\Users\\\\", re.I),
     "Windows 本地路径"),
]

#: 允许出现的例外（说明文档中的示例命令等），按相对路径 + 行号内容判断。
ALLOWED_SUBSTRINGS = [
    "/Users/",   # ANONYMIZATION.md 内的自查命令
    "有限公司",   # 同上
    "地铁站",     # 同上
]


def case_content_files():
    files = []
    for directory in CONTENT_DIRS:
        base = CASE / directory
        if base.exists():
            files.extend(p for p in base.rglob("*") if p.is_file())
    return sorted(files)


class AnonymizationGuardTests(unittest.TestCase):
    def test_case_exists(self):
        self.assertTrue(CASE.is_dir(), f"{CASE} 不存在")

    def test_required_files_present(self):
        for name in ("README.md", "ANONYMIZATION.md", "project.json"):
            self.assertTrue((CASE / name).exists(), f"缺少 {name}")

    def test_source_material_present(self):
        sources = list((CASE / "source").glob("*.txt"))
        self.assertGreaterEqual(len(sources), 3, "源材料不应少于 3 份")

    def test_no_leak_patterns_in_case_content(self):
        problems = []
        for path in case_content_files():
            if path.suffix in {".json"} and path.stat().st_size > 2_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if any(token in line for token in ALLOWED_SUBSTRINGS):
                    continue
                for pattern, label in LEAK_PATTERNS:
                    if pattern.search(line):
                        problems.append(
                            f"{path.relative_to(ROOT)}:{lineno} 命中「{label}」"
                        )
        self.assertEqual(problems, [], "脱敏可能被破坏：\n  " + "\n  ".join(problems))

    def test_project_json_conforms_to_schema(self):
        import sys
        sys.path.insert(0, str(ROOT / "core"))
        import schema_validator as sv

        errors, warnings = sv.validate_file(
            CASE / "project.json", ROOT / "schemas" / "project.schema.json"
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_project_json_declares_every_assumption_as_unevidenced(self):
        """案例的价值之一是「假设全部未经验证」—— ledger 为空时它应当如实反映。"""
        data = json.loads((CASE / "project.json").read_text(encoding="utf-8"))
        self.assertGreater(len(data["assumptions"]), 0)
        self.assertGreater(len(data["unknowns"]), 0)

    def test_no_evidence_ledger_committed(self):
        # 真实项目的证据账本默认不入库（.gitignore 已排除 evidence.jsonl）
        self.assertFalse((CASE / "evidence.jsonl").exists())

    def test_reproduction_scripts_have_no_hardcoded_paths(self):
        scripts = CASE / "rebuild" / "scripts"
        for path in scripts.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "/Users/", text,
                f"{path.name} 含硬编码本地路径，他人无法复现",
            )

    def test_case_readme_states_limitations(self):
        text = (CASE / "README.md").read_text(encoding="utf-8")
        for token in ("Known deviations", "What this case does not prove", "anonymisation"):
            self.assertIn(token, text, f"案例 README 缺少「{token}」一节")


if __name__ == "__main__":
    unittest.main()
