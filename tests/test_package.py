"""Offline package render and legacy 1.1 import use the shipped entry points."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.package import (  # noqa: E402
    APPENDIX_MARK,
    apply_legacy_plan,
    legacy_import_plan,
    render_legacy_package,
    render_package,
    replay_package,
)

AUTHORITY = """\
# 写入权

- scope: shared.identity
  owner: human
- scope: shared.boundaries
  owner: human
"""


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


class PackageTests(unittest.TestCase):
    def test_offline_package_replays_without_duplicating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "authority.md", AUTHORITY)
            write(
                root,
                "outbox/Grok-demo-sync.md",
                """\
- op_id: Grok-demo-sync#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2026-10-12
  text: 甲事实
""",
            )
            write(
                root,
                "environments/Grok-demo-sync.md",
                """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
---

卡片标记甲
""",
            )
            package = render_package(root, "Grok-demo-sync")
            self.assertIn('handoff_version: "1.1"', package)
            self.assertIn("甲事实", package)
            self.assertIn("卡片标记甲", package)
            self.assertIn("Grok-demo-sync#1", package)
            self.assertIn(APPENDIX_MARK, package)
            self.assertIn("## 10. 操作附录", package)

            with tempfile.TemporaryDirectory() as other:
                dest = Path(other)
                write(dest, "authority.md", AUTHORITY)
                write(dest, "outbox/Grok-demo-sync.md", "# outbox Grok-demo-sync\n")
                added = replay_package(dest, package)
                self.assertEqual(added, ["Grok-demo-sync#1"])
                view = (dest / "views" / "shared.md").read_text(encoding="utf-8")
                self.assertEqual(view.count("{id:fact-a}"), 1)
                outbox = (dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8")
                again = replay_package(dest, package)
                self.assertEqual(again, [])
                self.assertEqual((dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8"), outbox)
                self.assertEqual((dest / "views" / "shared.md").read_text(encoding="utf-8"), view)

    def test_legacy_import_confirms_and_ignores_mode(self) -> None:
        claims = [
            {"section": "1. 这个人是谁（Identity）", "text": "称呼：张三", "id": "anchor-name"},
            {"section": "1. 这个人是谁（Identity）", "text": "语言：zh-CN", "id": "anchor-lang"},
            {"section": "1. 这个人是谁（Identity）", "text": "时区：Asia/Shanghai", "id": "anchor-tz"},
            {"section": "2. 怎么跟他说话（Communication）", "text": "对本智能体的称呼：助手", "id": "anchor-agent"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "偏好深色", "id": "pref-new"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "已撤回：不再把默认编辑器记为 Vim", "id": "pref-vim"},
        ]
        migration = render_legacy_package(claims, mode="migration")
        sync = render_legacy_package(claims, mode="sync")
        for package in (migration, sync):
            self.assertIn('handoff_version: "1.1"', package)
            self.assertNotIn("## 10. 操作附录", package)
            self.assertNotIn("```ops", package)
        local = {
            "anchors": {
                "称呼": "张三",
                "语言": "zh-CN",
                "时区": "UTC",
                "对本智能体的称呼": "助手",
            },
            "claims": {"pref-vim": "默认编辑器 Vim", "pref-keep": "留下这条"},
        }
        plan_m = legacy_import_plan(migration, local)
        plan_s = legacy_import_plan(sync, local)
        self.assertEqual(plan_m.additions, plan_s.additions)
        self.assertEqual(plan_m.suggested_deletions, plan_s.suggested_deletions)
        self.assertEqual(plan_m.omitted_local_ids, plan_s.omitted_local_ids)
        self.assertIn("pref-vim", plan_m.suggested_deletions)
        self.assertIn("pref-keep", plan_m.omitted_local_ids)
        self.assertIn("pref-new", plan_m.additions)
        self.assertIn("时区", plan_m.anchor_conflicts)

        untouched = apply_legacy_plan(plan_m, local, confirmed=False)
        self.assertEqual(untouched, local)
        applied = apply_legacy_plan(plan_m, local, confirmed=True)
        self.assertEqual(applied["anchors"]["时区"], "UTC")
        self.assertEqual(applied["anchors"]["称呼"], "张三")
        self.assertEqual(applied["claims"]["pref-vim"], "默认编辑器 Vim")
        self.assertEqual(applied["claims"]["pref-keep"], "留下这条")
        self.assertEqual(applied["claims"]["pref-new"], "偏好深色")

    def test_legacy_section_6_is_not_stored_as_a_fact(self) -> None:
        package = """\
---
handoff_version: "1.1"
mode: migration
---

## 5. 事实与记忆（Facts & memories）

- 偏好深色 {id:pref-new}
- 已撤回：旧偏好 {id:pref-old}

## 6. 边界（Boundaries）

- 不携带记账明细 {id:boundaries.ledger}
- 已撤回：旧边界 {id:boundaries.old}

## 边界

- 人类写下的边界 {id:boundaries.human}

## 7. 其他

- 另一事实 {id:fact-next}
"""
        local = {"anchors": {}, "claims": {"pref-keep": "留下这条", "boundaries.old": "本地旧边界"}}
        plan = legacy_import_plan(package, local)
        self.assertNotIn("boundaries.ledger", plan.additions)
        self.assertNotIn("boundaries.old", plan.additions)
        self.assertNotIn("boundaries.ledger", plan.suggested_deletions)
        self.assertNotIn("boundaries.old", plan.suggested_deletions)
        self.assertIn("pref-new", plan.additions)
        self.assertEqual(plan.additions["pref-new"], "偏好深色")
        self.assertIn("boundaries.human", plan.additions)
        self.assertIn("fact-next", plan.additions)
        self.assertIn("pref-old", plan.suggested_deletions)
        self.assertIn("boundaries.old", plan.omitted_local_ids)
        applied = apply_legacy_plan(plan, local, confirmed=True)
        self.assertNotIn("boundaries.ledger", applied["claims"])
        self.assertNotIn("不携带记账明细", " ".join(applied["claims"].values()))
        self.assertEqual(applied["claims"]["pref-new"], "偏好深色")
        self.assertEqual(applied["claims"]["boundaries.human"], "人类写下的边界")
        self.assertEqual(applied["claims"]["boundaries.old"], "本地旧边界")
        self.assertEqual(applied["claims"]["pref-keep"], "留下这条")

    def test_replay_rejects_origin_id_outside_the_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            repo.mkdir()
            write(repo, "authority.md", AUTHORITY)
            outside = base / "escaped.md"
            origins = [str(base / "escaped"), "../escaped", "nested/escaped", "..\\escaped"]
            before = {path for path in base.rglob("*") if path.is_file()}
            for origin in origins:
                package = "\n".join(
                    [
                        "---",
                        'handoff_version: "1.1"',
                        f"origin_id: {origin}",
                        "---",
                        "```ops",
                        "- op_id: evil#1",
                        "  op: set",
                        "  id: fact-a",
                        "  scope: shared",
                        "  base: none",
                        "  at: 2026-10-12",
                        "  text: 越界",
                        "```",
                        "",
                    ]
                )
                with self.assertRaises(ValueError):
                    replay_package(repo, package)
            after = {path for path in base.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(outside.exists())
            self.assertFalse((repo / "outbox").exists())

    def test_render_rejects_origin_outside_the_repo(self) -> None:
        script = ROOT / "scripts" / "compile_memory.py"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            repo.mkdir()
            write(repo, "authority.md", AUTHORITY)
            outside = base / "escaped.md"
            before = {path for path in base.rglob("*") if path.is_file()}
            for origin in (str(base / "escaped"), "../evil", "nested/evil"):
                with self.assertRaises(ValueError):
                    render_package(repo, origin)
            proc = subprocess.run(
                [sys.executable, str(script), "--render", str(repo), "--origin", "../evil"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            after = {path for path in base.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(outside.exists())
            self.assertFalse((repo / "evil.md").exists())


if __name__ == "__main__":
    unittest.main()
