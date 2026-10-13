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
from topmind_handoff.compile import compile_repo, startup_read, status_is_valid  # noqa: E402


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

    def test_organize_archives_short_facts_when_the_index_is_over_budget(self) -> None:
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
            blocks = []
            for index in range(220):
                blocks.append(
                    f"""\
- op_id: Grok-demo-sync#{index}
  op: set
  id: fact-{index}
  scope: shared
  slice: fact
  base: none
  at: 2026-10-12
  text: 事实{index}
"""
                )
            write(root, "outbox/Grok-demo-sync.md", "\n".join(blocks))
            before = (root / "outbox" / "Grok-demo-sync.md").read_bytes()
            organize_repo(root, date(2026, 10, 12))
            self.assertEqual((root / "outbox" / "Grok-demo-sync.md").read_bytes(), before)
            slim = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(slim.splitlines()), 200)
            self.assertIn("见 facts/shared-fact.md", slim)
            self.assertNotIn("事实219", slim)
            archived = (root / "facts" / "shared-fact.md").read_text(encoding="utf-8")
            self.assertIn("事实0", archived)
            self.assertIn("事实219", archived)

    def test_own_recompiles_former_owner_out_of_the_scenario(self) -> None:
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
- scope: scenario.writing
  owner: Muse-demo-sync
""",
            )
            write(
                root,
                "outbox/Muse-demo-sync.md",
                """\
- op_id: Muse-demo-sync#1
  op: set
  id: scene-w
  scope: scenario:writing
  base: none
  at: 2026-10-12
  text: 原主人句子
""",
            )
            compile_repo(root)
            self.assertIn("原主人句子", (root / "views" / "scenario-writing.md").read_text(encoding="utf-8"))
            set_scenario_owner(root, "writing", "Grok-demo-sync")
            view = (root / "views" / "scenario-writing.md").read_text(encoding="utf-8")
            status = (root / "STATUS.md").read_text(encoding="utf-8")
            self.assertNotIn("原主人句子", view)
            self.assertIn("原主人句子", status)
            ok, _message = status_is_valid(root)
            self.assertTrue(ok)
            owners = parse_authority((root / "authority.md").read_text(encoding="utf-8"))
            self.assertEqual(owners["scenario.writing"], "Grok-demo-sync")
            self.assertEqual(owners["shared.identity"], "human")
            self.assertEqual(owners["shared.boundaries"], "human")

    def test_startup_override_matches_a_review_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = date(2026, 10, 12)
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
            write(
                root,
                "outbox/Grok-demo-sync.md",
                f"""\
- op_id: Grok-demo-sync#1
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: {(today - timedelta(days=90)).isoformat()}
  text: 深色方案
  detail: |
    原始细节
""",
            )
            write(
                root,
                "environments/Grok-demo-sync.md",
                f"""\
---
origin: Grok-demo-sync
role: writing
refreshed: {today.isoformat()}
override.pref-theme: 覆盖句
---

路径：~/writing
""",
            )
            organize_repo(root, today)
            shared = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("- 深色方案 {id:pref-theme} （未复核）", shared)
            archived = (root / "facts" / "shared-preference.md").read_text(encoding="utf-8")
            self.assertIn("原始细节", archived)
            started = startup_read(root, "Grok-demo-sync")
            self.assertIn("- 覆盖句 {id:pref-theme}", started)
            self.assertNotIn("深色方案", started)
            self.assertNotIn("原始细节", started)
            self.assertEqual((root / "views" / "shared.md").read_text(encoding="utf-8"), shared)

    def test_init_rejects_origin_outside_the_repo(self) -> None:
        script = ROOT / "scripts" / "compile_memory.py"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            origins = [str(base / "escaped"), "../evil", "nested/evil"]
            for index, origin in enumerate(origins):
                repo = base / f"repo-{index}"
                outside = base / "escaped.md"
                proc = subprocess.run(
                    [sys.executable, str(script), "--init", str(repo), "--private", "--origin", origin],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertFalse(repo.exists())
                self.assertFalse(outside.exists())
                self.assertFalse((repo / "evil.md").exists())
                self.assertEqual(list(base.rglob("*.md")), [])
            role_repo = base / "role-repo"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--init",
                    str(role_repo),
                    "--private",
                    "--origin",
                    "Grok-demo-sync",
                    "--role",
                    "../evil",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertFalse(role_repo.exists())
            self.assertFalse((base / "evil.md").exists())

    def test_startup_override_follows_a_collapsed_due_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            today = date(2026, 10, 12)
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
            blocks = []
            for index in range(219):
                blocks.append(
                    f"""\
- op_id: Grok-demo-sync#{index}
  op: set
  id: pref-{index}
  scope: shared
  slice: preference
  base: none
  at: {today.isoformat()}
  text: 偏好{index}
"""
                )
            aged = (today - timedelta(days=90)).isoformat()
            blocks.append(
                f"""\
- op_id: Grok-demo-sync#219
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: {aged}
  text: 深色方案
  detail: |
    原始细节
"""
            )
            write(root, "outbox/Grok-demo-sync.md", "\n".join(blocks))
            write(
                root,
                "environments/Grok-demo-sync.md",
                f"""\
---
origin: Grok-demo-sync
role: writing
refreshed: {today.isoformat()}
override.pref-theme: 覆盖句
---

路径：~/writing
""",
            )
            organize_repo(root, today)
            shared_path = root / "views" / "shared.md"
            shared = shared_path.read_text(encoding="utf-8")
            self.assertIn("见 facts/shared-preference.md", shared)
            self.assertNotIn("深色方案", shared)
            self.assertNotIn("覆盖句", shared)
            archived = (root / "facts" / "shared-preference.md").read_text(encoding="utf-8")
            self.assertIn("- 深色方案 {id:pref-theme} （未复核）", archived)
            self.assertIn("原始细节", archived)
            self.assertIn("偏好0", archived)
            self.assertIn("偏好218", archived)
            secret = base / "secret.md"
            secret.write_text("SECRET_OUTSIDE\n", encoding="utf-8")
            shared_path.write_text(shared + "- 见 facts/../../secret.md\n", encoding="utf-8")
            shared = shared_path.read_text(encoding="utf-8")
            started = startup_read(root, "Grok-demo-sync")
            self.assertIn("- 覆盖句 {id:pref-theme}", started)
            self.assertNotIn("深色方案", started)
            self.assertNotIn("原始细节", started)
            self.assertNotIn("偏好218", started)
            self.assertNotIn("SECRET_OUTSIDE", started)
            self.assertEqual(shared_path.read_text(encoding="utf-8"), shared)
            script = ROOT / "scripts" / "compile_memory.py"
            proc = subprocess.run(
                [sys.executable, str(script), "--startup", str(root), "--origin", "Grok-demo-sync"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("- 覆盖句 {id:pref-theme}", proc.stdout)
            self.assertNotIn("深色方案", proc.stdout)
            self.assertNotIn("原始细节", proc.stdout)
            self.assertNotIn("SECRET_OUTSIDE", proc.stdout)
            self.assertEqual(shared_path.read_text(encoding="utf-8"), shared)

    def test_own_rejects_scenario_outside_the_repo(self) -> None:
        script = ROOT / "scripts" / "compile_memory.py"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            write(
                repo,
                "authority.md",
                """\
- scope: shared.identity
  owner: human
- scope: shared.boundaries
  owner: human
- scope: scenario.writing
  owner: Muse-demo-sync
""",
            )
            before = (repo / "authority.md").read_bytes()
            outside = base / "evil.md"
            commands = [
                ["--scenario", "../evil", "--origin", "Grok-demo-sync"],
                ["--scenario", "nested/evil", "--origin", "Grok-demo-sync"],
                ["--scenario", str(base / "escaped"), "--origin", "Grok-demo-sync"],
                ["--scenario", "writing", "--origin", "../evil"],
            ]
            for extra in commands:
                proc = subprocess.run(
                    [sys.executable, str(script), "--own", str(repo), *extra],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual((repo / "authority.md").read_bytes(), before)
                self.assertFalse(outside.exists())
                self.assertFalse((repo / "evil.md").exists())
                self.assertFalse((base / "escaped.md").exists())
                self.assertEqual(list(repo.rglob("*.md")), [repo / "authority.md"])

    def test_fact_review_survives_compile_and_refinement_does_not_retract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = date(2026, 10, 13)
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
            old = (today - timedelta(days=30)).isoformat()
            young = (today - timedelta(days=29)).isoformat()
            identity_old = (today - timedelta(days=180)).isoformat()
            preference_old = (today - timedelta(days=90)).isoformat()
            project_young = (today - timedelta(days=29)).isoformat()
            write(
                root,
                "outbox/human.md",
                f"""\
- op_id: human#1
  op: set
  id: identity.name
  scope: shared
  slice: identity
  base: none
  at: {identity_old}
  text: 称呼示例
- op_id: human#2
  op: set
  id: boundaries.note
  scope: shared
  slice: boundaries
  base: none
  at: {identity_old}
  text: 边界旧例
- op_id: human#3
  op: set
  id: pref-old
  scope: shared
  slice: preference
  base: none
  at: {preference_old}
  text: 偏好旧例
- op_id: human#4
  op: set
  id: project-new
  scope: shared
  slice: project
  base: none
  at: {project_young}
  text: 项目新例
""",
            )
            write(
                root,
                "outbox/Grok-demo-sync.md",
                f"""\
- op_id: Grok-demo-sync#1
  op: set
  id: fact-old
  scope: shared
  slice: fact
  base: none
  at: {old}
  text: 旧事实
- op_id: Grok-demo-sync#2
  op: set
  id: fact-young
  scope: shared
  slice: fact
  base: none
  at: {young}
  text: 年轻事实
- op_id: Grok-demo-sync#3
  op: set
  id: fact-cloud
  scope: shared
  slice: fact
  base: none
  at: {young}
  text: 两个来源
- op_id: Grok-demo-sync#4
  op: set
  id: fact-join
  scope: shared
  slice: fact
  base: none
  at: {young}
  text: 本机已补上 fact-cloud
""",
            )
            write(
                root,
                "environments/Aged-demo-sync.md",
                f"""\
---
origin: Aged-demo-sync
role: writing
refreshed: {(today - timedelta(days=90)).isoformat()}
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
refreshed: {(today - timedelta(days=89)).isoformat()}
---

路径：~/fresh
""",
            )
            before = {
                path.name: path.read_bytes()
                for path in sorted((root / "outbox").glob("*.md"))
            }
            compile_repo(root, today)
            shared = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("- 旧事实 {id:fact-old} （未复核）", shared)
            self.assertIn("- 年轻事实 {id:fact-young}", shared)
            self.assertNotIn("- 年轻事实 {id:fact-young} （未复核）", shared)
            self.assertIn("- 称呼示例 {id:identity.name} （未复核）", shared)
            self.assertIn("- 边界旧例 {id:boundaries.note} （未复核）", shared)
            self.assertIn("- 偏好旧例 {id:pref-old} （未复核）", shared)
            self.assertNotIn("- 项目新例 {id:project-new} （未复核）", shared)
            compile_repo(root)
            self.assertEqual((root / "views" / "shared.md").read_text(encoding="utf-8"), shared)
            started = startup_read(root, "Grok-demo-sync", today=today)
            self.assertIn("- 旧事实 {id:fact-old} （未复核）", started)
            self.assertNotIn("- 年轻事实 {id:fact-young} （未复核）", started)
            self.assertIn("引用 `fact-join` 提到当前说法 `fact-cloud`。不撤回，不改写。", started)
            self.assertIn("两个来源", started)
            self.assertIn("本机已补上 fact-cloud", started)
            organize_repo(root, today)
            after = {
                path.name: path.read_bytes()
                for path in sorted((root / "outbox").glob("*.md"))
            }
            self.assertEqual(before, after)
            organized = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("- 旧事实 {id:fact-old} （未复核）", organized)
            self.assertIn("本机已补上 fact-cloud", organized)
            self.assertNotIn("已撤回", organized)
            status = (root / "STATUS.md").read_text(encoding="utf-8")
            self.assertIn("引用 `fact-join` 提到当前说法 `fact-cloud`。不撤回，不改写。", status)
            self.assertIn("环境卡片 `Aged-demo-sync` 未刷新。", status)
            self.assertNotIn("环境卡片 `Fresh-demo-sync` 未刷新。", status)
            self.assertIn("未刷新", (root / "environments" / "Aged-demo-sync.md").read_text(encoding="utf-8"))
            self.assertTrue((root / "environments" / "Aged-demo-sync.md").is_file())
            self.assertNotIn("未刷新", (root / "environments" / "Fresh-demo-sync.md").read_text(encoding="utf-8"))
            compile_repo(root)
            kept = (root / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("- 旧事实 {id:fact-old} （未复核）", kept)
            self.assertNotIn("- 年轻事实 {id:fact-young} （未复核）", kept)
            self.assertIn("本机已补上 fact-cloud", kept)
            again = startup_read(root, "Grok-demo-sync", today=today)
            self.assertIn("- 旧事实 {id:fact-old} （未复核）", again)
            self.assertIn("引用 `fact-join` 提到当前说法 `fact-cloud`。不撤回，不改写。", again)
            self.assertEqual(before, {path.name: path.read_bytes() for path in (root / "outbox").glob("*.md")})


if __name__ == "__main__":
    unittest.main()
