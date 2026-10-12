"""Offline package render and legacy 1.1 import use the shipped entry points."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
