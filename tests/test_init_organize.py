"""Init and organize drive the shipped admin functions."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.admin import PublicRepoRefused, init_memory_repo, organize_repo, set_scenario_owner  # noqa: E402
from topmind_handoff.model import parse_authority  # noqa: E402
from topmind_handoff.compile import compile_repo  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


class InitOrganizeTests(unittest.TestCase):
    def test_init_private_commits_and_public_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            public = base / "public-repo"
            with self.assertRaises(PublicRepoRefused):
                init_memory_repo(public, private=False, origin="Grok-demo-sync")
            self.assertFalse(public.exists())

            private = base / "private-repo"
            init_memory_repo(
                private,
                private=True,
                origin="Grok-demo-sync",
                role="writing",
                today="2026-10-12",
            )
            shared = (private / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("（无）", shared)
            self.assertTrue((private / "views" / "scenario-writing.md").is_file())
            self.assertTrue((private / "authority.md").is_file())
            self.assertTrue((private / "outbox" / "Grok-demo-sync.md").is_file())
            self.assertFalse((private / ".github").exists())
            listed = subprocess.check_output(["git", "ls-files"], cwd=private, text=True)
            self.assertNotIn(".github/workflows", listed)
            self.assertIn("views/shared.md", listed)
            count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=private, text=True)
            self.assertEqual(count.strip(), "1")
            set_scenario_owner(private, "writing", "Grok-demo-sync")
            owners = parse_authority((private / "authority.md").read_text(encoding="utf-8"))
            self.assertEqual(owners["scenario.writing"], "Grok-demo-sync")
            self.assertEqual(owners["shared.identity"], "human")
            self.assertEqual(owners["shared.boundaries"], "human")

    def test_organize_compacts_labels_and_keeps_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "authority.md",
                """\
- scope: shared.identity
  owner: human
- scope: shared.boundaries
  owner: human
""",
            )
            today = date(2026, 10, 12)
            blocks = [
                f"""\
- op_id: human#1
  op: set
  id: identity.name
  scope: shared
  slice: identity
  base: none
  at: {(today - timedelta(days=180)).isoformat()}
  text: 称呼示例
""",
                f"""\
- op_id: human#2
  op: set
  id: pref-old
  scope: shared
  slice: preference
  base: none
  at: {(today - timedelta(days=90)).isoformat()}
  text: 偏好旧例
""",
                f"""\
- op_id: human#3
  op: set
  id: pref-new
  scope: shared
  slice: preference
  base: none
  at: {(today - timedelta(days=89)).isoformat()}
  text: 偏好新例
""",
                f"""\
- op_id: human#4
  op: set
  id: project-old
  scope: shared
  slice: project
  base: none
  at: {(today - timedelta(days=30)).isoformat()}
  text: 项目旧例
""",
                f"""\
- op_id: human#5
  op: set
  id: project-new
  scope: shared
  slice: project
  base: none
  at: {(today - timedelta(days=29)).isoformat()}
  text: 项目新例
""",
                f"""\
- op_id: human#6
  op: set
  id: boundaries.note
  scope: shared
  slice: boundaries
  base: none
  at: {(today - timedelta(days=180)).isoformat()}
  text: 边界旧例
""",
            ]
            for index in range(30):
                detail = "\n".join(f"    细节{index}-{line}" for line in range(10))
                blocks.append(
                    f"""\
- op_id: Grok-demo-sync#{index}
  op: set
  id: fact-{index}
  scope: shared
  slice: fact
  base: none
  at: 2026-10-01
  text: 事实{index}
  detail: |
{detail}
"""
                )
            write(root, "outbox/human.md", "".join(blocks[:6]))
            write(root, "outbox/Grok-demo-sync.md", "\n".join(blocks[6:]))
            write(
                root,
                "environments/Grok-demo-sync.md",
                """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-01-01
---

路径：~/writing
""",
            )
            aged = (today - timedelta(days=90)).isoformat()
            fresh = (today - timedelta(days=89)).isoformat()
            write(
                root,
                "environments/Aged-demo-sync.md",
                f"""\
---
origin: Aged-demo-sync
role: writing
refreshed: {aged}
---

路径：~/aged
""",
            )
            write(
                root,
                "environments/Fresh-demo-sync.md",
                f"""\
---
origin: Fresh-demo-sync
role: writing
refreshed: {fresh}
---

路径：~/fresh
""",
            )
            compile_repo(root)
            write(root, "views/scenario-retired.md", "# 旧场景\n\n手工\n")
            fat = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertGreater(len(fat.splitlines()), 200)
            before = {
                path.name: path.read_bytes()
                for path in sorted((root / "outbox").glob("*.md"))
            }
            organize_repo(root, today)
            after = {
                path.name: path.read_bytes()
                for path in sorted((root / "outbox").glob("*.md"))
            }
            self.assertEqual(before, after)
            slim = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(slim.splitlines()), 200)
            self.assertNotIn("细节0-3", slim)
            detail_files = list((root / "facts").rglob("*.md"))
            self.assertTrue(detail_files)
            self.assertTrue(any("细节0-3" in path.read_text(encoding="utf-8") for path in detail_files))
            self.assertIn("- 称呼示例 {id:identity.name} （未复核）", slim)
            self.assertIn("- 边界旧例 {id:boundaries.note} （未复核）", slim)
            self.assertIn("- 偏好旧例 {id:pref-old} （未复核）", slim)
            self.assertIn("- 偏好新例 {id:pref-new}", slim)
            self.assertNotIn("- 偏好新例 {id:pref-new} （未复核）", slim)
            self.assertIn("- 项目旧例 {id:project-old} （未复核）", slim)
            self.assertNotIn("- 项目新例 {id:project-new} （未复核）", slim)
            self.assertFalse((root / "views" / "scenario-retired.md").exists())
            card = (root / "environments" / "Grok-demo-sync.md").read_text(encoding="utf-8")
            self.assertIn("未刷新", card)
            self.assertTrue((root / "environments" / "Grok-demo-sync.md").is_file())
            aged_card = (root / "environments" / "Aged-demo-sync.md").read_text(encoding="utf-8")
            fresh_card = (root / "environments" / "Fresh-demo-sync.md").read_text(encoding="utf-8")
            self.assertIn("未刷新", aged_card)
            self.assertNotIn("未刷新", fresh_card)


if __name__ == "__main__":
    unittest.main()
