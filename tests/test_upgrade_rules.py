"""技能升级规则：就地覆盖不留备份、不降级，消息与 topmind 安装器一致。"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class UpgradeRules(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_no_backup_copy_in_skill_dirs(self):
        for rel in ["SKILL.md", "references/environment.md", "references/import.md", "references/spec.md",
                    "assets/handoff-template.md", "assets/handoff-example.md"]:
            text = self.read(rel)
            self.assertNotIn("先备份", text, rel)
            self.assertNotIn("back up first", text, rel)
            self.assertNotRegex(text, r"复制到同级的 `技能名\.bak-", rel)

    def test_environment_messages_match_installers(self):
        env = self.read("references/environment.md")
        self.assertIn("Upgraded <技能> <旧> -> <新>", env)
        self.assertIn("Already up to date: <技能> <版本>", env)
        self.assertIn("Downgraded <技能> <旧> -> <新>", env)
        self.assertIn("不降级", env)
        self.assertIn("npx @topmindspace/topmind-handoff@latest install", env)
        self.assertIn("npx @topmindspace/topmind-handoff@latest update", env)


if __name__ == "__main__":
    unittest.main()
