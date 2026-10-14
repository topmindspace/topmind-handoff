"""knowledge/ is created by init, filled in only where missing, and never overwritten."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.admin import (  # noqa: E402
    KNOWLEDGE_CATEGORIES,
    KNOWN_STOCK_READMES,
    init_memory_repo,
    knowledge_readme,
    memory_readme,
    write_knowledge_skeleton,
)
from topmind_handoff.compile import compile_repo, status_is_valid  # noqa: E402


class KnowledgeTests(unittest.TestCase):
    def test_init_writes_knowledge_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "mem"
            init_memory_repo(repo, private=True, origin="Grok-demo-sync", today="2026-10-14")
            self.assertEqual((repo / "knowledge" / "README.md").read_text(encoding="utf-8"), knowledge_readme())
            for name, _ in KNOWLEDGE_CATEGORIES:
                self.assertTrue((repo / "knowledge" / name / "通用.md").is_file(), name)
            self.assertIn("## knowledge/ 知识库", (repo / "README.md").read_text(encoding="utf-8"))
            print("OK init writes knowledge/")

    def test_readme_template_is_generic(self) -> None:
        text = knowledge_readme()
        for rule in ("最多两级", "300 行", "子类-限定.md", "新条目加在文件顶部", "rg -n", "不是指令"):
            self.assertIn(rule, text)
        for personal in ("mspd", "Ding", "GrokBot-mspd-sync", "x.com/"):
            self.assertNotIn(personal, text)
        print("OK knowledge README is generic")

    def test_existing_knowledge_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "mem"
            init_memory_repo(repo, private=True, origin="Grok-demo-sync", today="2026-10-14")
            mine = repo / "knowledge" / "README.md"
            mine.write_text("# 我改过的说明\n", encoding="utf-8")
            entry = repo / "knowledge" / "写作" / "通用.md"
            entry.write_text("# 写作 · 通用\n\n## 张三的经验\n", encoding="utf-8")
            (repo / "knowledge" / "提示词" / "通用.md").unlink()
            written = write_knowledge_skeleton(repo)
            self.assertEqual(written, [repo / "knowledge" / "提示词" / "通用.md"])
            compile_repo(repo)
            self.assertEqual(mine.read_text(encoding="utf-8"), "# 我改过的说明\n")
            self.assertIn("张三的经验", entry.read_text(encoding="utf-8"))
            self.assertTrue(status_is_valid(repo))
            print("OK existing knowledge/ untouched")

    def test_compile_ignores_knowledge_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "mem"
            init_memory_repo(repo, private=True, origin="Grok-demo-sync", today="2026-10-14")
            (repo / "knowledge" / "写作" / "通用.md").write_text("## 不该进视图的条目XYZ\n", encoding="utf-8")
            compile_repo(repo)
            for path in list((repo / "views").glob("*.md")) + [repo / "STATUS.md"]:
                self.assertNotIn("XYZ", path.read_text(encoding="utf-8"))
            print("OK compile ignores knowledge/")

    def test_old_stock_readme_upgrade_adds_missing_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "mem"
            init_memory_repo(repo, private=True, origin="Grok-demo-sync", today="2026-10-14")
            import shutil

            shutil.rmtree(repo / "knowledge")
            (repo / "README.md").write_text(KNOWN_STOCK_READMES[0], encoding="utf-8")
            compile_repo(repo)
            self.assertEqual((repo / "README.md").read_text(encoding="utf-8"), memory_readme())
            self.assertTrue((repo / "knowledge" / "README.md").is_file())
            print("OK stock README upgrade adds knowledge/")

    def test_edited_readme_without_knowledge_is_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "mem"
            init_memory_repo(repo, private=True, origin="Grok-demo-sync", today="2026-10-14")
            import shutil

            shutil.rmtree(repo / "knowledge")
            (repo / "README.md").write_text("# 自己写的说明\n", encoding="utf-8")
            compile_repo(repo)
            self.assertFalse((repo / "knowledge").exists())
            print("OK edited README leaves repo alone")


if __name__ == "__main__":
    unittest.main()
