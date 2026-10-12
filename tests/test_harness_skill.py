"""宿主接入文件测试。

DSH 的技能发现规则很严格：frontmatter 里 `name` 不是 kebab-case、
或 `description` 为空，技能会被**静默丢弃**——没有报错，只是不出现。
所以这里把它变成 CI 能抓住的错误。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "harness" / "deepseek" / "SKILL.md"

#: 技能正文会被整体注入模型上下文；超过这个量级在压缩时可能被截断中间部分。
RENDERED_BUDGET = 8192
WRAPPER_ALLOWANCE = 300

KebabCase = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

#: 这些驼峰键在 DSH 中会导致技能被丢弃，出现过就说明用了旧写法。
LEGACY_KEYS = ("disableModelInvocation", "modelInvocable", "userInvocable")


def parse_frontmatter(text):
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


class SkillFileTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        self.frontmatter, self.body = parse_frontmatter(self.text)

    def test_skill_file_exists(self):
        self.assertTrue(SKILL.exists(), f"{SKILL} 不存在")

    def test_frontmatter_is_delimited(self):
        self.assertIsNotNone(
            self.frontmatter,
            "frontmatter 缺失或未用 --- 行分隔（技能会被丢弃）",
        )

    def test_name_is_kebab_case(self):
        match = re.search(r"^name:\s*(\S+)\s*$", self.frontmatter, re.M)
        self.assertIsNotNone(match, "frontmatter 缺少 name（技能会被丢弃）")
        self.assertRegex(
            match.group(1), KebabCase,
            f"name '{match.group(1)}' 不是 kebab-case（技能会被静默丢弃）",
        )

    def test_installed_path_matches_skill_name(self):
        """仓库内按宿主分目录（harness/deepseek/），但 DSH 要求安装后的
        目录名等于 skill 名。所以安装说明必须写对目标路径，否则技能装上去
        也发现不了——而且是静默发现不了。"""
        match = re.search(r"^name:\s*(\S+)\s*$", self.frontmatter, re.M)
        skill_name = match.group(1)
        readme = (ROOT / "harness" / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f".dsh/skills/{skill_name}/SKILL.md", readme,
            f"安装说明未给出正确的目标路径（应为 .dsh/skills/{skill_name}/SKILL.md）",
        )
        self.assertIn(
            f".dsh/skills/{skill_name}", readme,
            "安装说明未给出 mkdir 目标目录",
        )

    def test_description_present_and_substantial(self):
        match = re.search(
            r"^description:\s*(.+?)(?=\n[a-zA-Z_-]+:|\Z)", self.frontmatter, re.S | re.M
        )
        self.assertIsNotNone(match, "frontmatter 缺少 description（技能会被丢弃）")
        description = re.sub(r"\s+", " ", match.group(1)).strip()
        self.assertGreater(len(description), 40, "description 过短，不利于技能被正确选用")

    def test_no_legacy_camel_case_keys(self):
        for key in LEGACY_KEYS:
            self.assertNotIn(key, self.frontmatter, f"旧写法键 '{key}' 会导致技能被丢弃")

    def test_rendered_size_within_budget(self):
        rendered = len(self.body) + WRAPPER_ALLOWANCE
        self.assertLess(
            rendered, RENDERED_BUDGET,
            f"技能正文渲染后约 {rendered} 字符，超过 {RENDERED_BUDGET} 的安全上限",
        )

    def test_body_mentions_core_constraints(self):
        for token in ("FACT", "ASSUMPTION", "UNKNOWN", "门禁"):
            self.assertIn(token, self.body, f"技能正文未提及 {token}")

    def test_body_points_at_real_commands(self):
        cli = ROOT / "core" / "rebuild_cli.py"
        for subcommand in ("evidence", "decision", "source", "run"):
            self.assertIn(f"rebuild_cli.py {subcommand}", self.body,
                          f"技能正文未介绍 {subcommand} 子命令")
        self.assertTrue(cli.exists())

    def test_body_states_boundaries(self):
        # 技能是模型的操作说明，必须把「不是什么」写进去，否则模型会越权承诺
        self.assertIn("不是", self.body)
        self.assertIn("不保证结论正确", self.body)


class HarnessReadmeTests(unittest.TestCase):
    def test_install_instructions_exist(self):
        readme = ROOT / "harness" / "README.md"
        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")
        self.assertIn(".dsh/skills", text)
        self.assertIn("SKILL.md", text)

    def test_no_unverifiable_claims_about_host_parallelism(self):
        text = (ROOT / "harness" / "README.md").read_text(encoding="utf-8")
        self.assertIn("不假装具备", text)


if __name__ == "__main__":
    unittest.main()
