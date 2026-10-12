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
    LegacyPlan,
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
                pending = replay_package(dest, package)
                self.assertEqual(pending, ["Grok-demo-sync#1"])
                self.assertFalse((dest / "views" / "shared.md").exists())
                self.assertEqual(
                    (dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8"),
                    "# outbox Grok-demo-sync\n",
                )
                added = replay_package(dest, package, confirmed=True)
                self.assertEqual(added, ["Grok-demo-sync#1"])
                view = (dest / "views" / "shared.md").read_text(encoding="utf-8")
                self.assertEqual(view.count("{id:fact-a}"), 1)
                outbox = (dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8")
                again = replay_package(dest, package, confirmed=True)
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
        self.assertEqual(plan_m.anchor_fills, {})
        self.assertEqual(plan_m.text_conflicts, {})
        self.assertEqual(plan_m.unkeyed, [])

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

    def test_receive_keeps_local_text_and_asks_on_conflict(self) -> None:
        claims = [
            {"section": "1. 这个人是谁（Identity）", "text": "称呼：张三", "id": "anchor-name"},
            {"section": "1. 这个人是谁（Identity）", "text": "时区：Asia/Shanghai", "id": "anchor-tz"},
            {"section": "1. 这个人是谁（Identity）", "text": "语言：zh-CN", "id": "anchor-lang"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "浅色方案", "id": "pref-theme"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "偏好深色", "id": "pref-new"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "另一句", "id": "pref-new"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "同一句", "id": "pref-same"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "同一句", "id": "pref-same"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "喜欢步行"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "留下这条"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "不喜欢被称呼：老板"},
            {"section": "5. 事实与记忆（Facts & memories）", "text": "已撤回：不再使用 Vim", "id": "pref-vim"},
        ]
        package = render_legacy_package(claims)
        package += "\n```ops\n- 秘密事实 {id:fact-secret}\n- op_id: Grok-demo-sync#9\n```\n"
        local = {
            "anchors": {"称呼": "李四", "语言": "", "时区": "", "对本智能体的称呼": ""},
            "claims": {
                "pref-theme": "深色方案",
                "pref-keep": "留下这条",
                "pref-vim": "默认 Vim",
            },
        }
        plan = legacy_import_plan(package, local)
        self.assertEqual(plan.anchor_conflicts["称呼"], ("李四", "张三"))
        self.assertEqual(plan.anchor_fills["时区"], "Asia/Shanghai")
        self.assertEqual(plan.anchor_fills["语言"], "zh-CN")
        self.assertNotIn("称呼", plan.anchor_fills)
        self.assertEqual(plan.text_conflicts["pref-theme"], ("深色方案", "浅色方案"))
        self.assertNotIn("pref-theme", plan.additions)
        self.assertNotIn("pref-new", plan.additions)
        self.assertEqual(plan.text_conflicts["pref-new"], ("偏好深色", "另一句"))
        self.assertEqual(plan.additions["pref-same"], "同一句")
        self.assertEqual(plan.unkeyed, ["喜欢步行", "不喜欢被称呼：老板"])
        self.assertNotIn("留下这条", plan.unkeyed)
        self.assertNotIn("fact-secret", plan.additions)
        self.assertNotIn("秘密事实", plan.unkeyed)
        self.assertNotIn("op_id: Grok-demo-sync#9", plan.unkeyed)
        self.assertIn("pref-vim", plan.suggested_deletions)
        self.assertIn("pref-keep", plan.omitted_local_ids)
        self.assertNotIn("pref-theme", plan.omitted_local_ids)

        untouched = apply_legacy_plan(plan, local, confirmed=False)
        self.assertEqual(untouched, local)
        applied = apply_legacy_plan(plan, local, confirmed=True)
        self.assertEqual(applied["anchors"]["称呼"], "李四")
        self.assertEqual(applied["anchors"]["时区"], "Asia/Shanghai")
        self.assertEqual(applied["anchors"]["语言"], "zh-CN")
        self.assertEqual(applied["anchors"]["对本智能体的称呼"], "")
        self.assertEqual(applied["claims"]["pref-theme"], "深色方案")
        self.assertEqual(applied["claims"]["pref-keep"], "留下这条")
        self.assertEqual(applied["claims"]["pref-vim"], "默认 Vim")
        self.assertEqual(applied["claims"]["pref-same"], "同一句")
        self.assertNotIn("pref-new", applied["claims"])
        self.assertNotIn("喜欢步行", applied["claims"].values())
        self.assertNotIn("秘密事实", " ".join(applied["claims"].values()))

        split = render_legacy_package(
            [
                {"text": "时区：Asia/Shanghai", "id": "tz-a"},
                {"text": "时区：UTC", "id": "tz-b"},
            ]
        )
        split_plan = legacy_import_plan(split, {"anchors": {"时区": ""}, "claims": {}})
        self.assertNotIn("时区", split_plan.anchor_fills)
        self.assertEqual(split_plan.anchor_conflicts["时区"], ("Asia/Shanghai", "UTC"))
        split_applied = apply_legacy_plan(split_plan, {"anchors": {"时区": ""}, "claims": {}}, confirmed=True)
        self.assertEqual(split_applied["anchors"]["时区"], "")

        mixed = """\
## 5. 事实与记忆（Facts & memories）

- 新说法 {id:pref-vim}
- 已撤回：旧说法 {id:pref-vim}
"""
        mixed_plan = legacy_import_plan(mixed, local)
        self.assertNotIn("pref-vim", mixed_plan.additions)
        self.assertIn("pref-vim", mixed_plan.suggested_deletions)
        self.assertIn("pref-vim", mixed_plan.text_conflicts)
        mixed_applied = apply_legacy_plan(mixed_plan, local, confirmed=True)
        self.assertEqual(mixed_applied["claims"]["pref-vim"], "默认 Vim")

        hostile = LegacyPlan(
            additions={"pref-theme": "浅色方案", "pref-new": "偏好深色", "pref-split": "甲"},
            anchor_fills={"称呼": "张三", "时区": "Asia/Shanghai"},
            anchor_conflicts={"称呼": ("李四", "张三")},
            text_conflicts={"pref-split": ("甲", "乙"), "pref-theme": ("深色方案", "浅色方案")},
            suggested_deletions=["pref-vim"],
        )
        forced = apply_legacy_plan(hostile, local, confirmed=True)
        self.assertEqual(forced["claims"]["pref-theme"], "深色方案")
        self.assertEqual(forced["anchors"]["称呼"], "李四")
        self.assertEqual(forced["anchors"]["时区"], "Asia/Shanghai")
        self.assertEqual(forced["claims"]["pref-new"], "偏好深色")
        self.assertNotIn("pref-split", forced["claims"])
        self.assertEqual(forced["claims"]["pref-vim"], "默认 Vim")
        self.assertEqual(forced["claims"]["pref-keep"], "留下这条")

    def test_replay_appends_only_after_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            write(dest, "authority.md", AUTHORITY)
            existing = """\
# outbox Grok-demo-sync
- op_id: Grok-demo-sync#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2026-10-12
  text: 本地事实
"""
            other = """\
# outbox Other-demo
- op_id: Other-demo#1
  op: set
  id: fact-b
  scope: shared
  base: none
  at: 2026-10-12
  text: 别人的
"""
            card = """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
---

本地卡片
"""
            write(dest, "outbox/Grok-demo-sync.md", existing)
            write(dest, "outbox/Other-demo.md", other)
            write(dest, "environments/Grok-demo-sync.md", card)
            write(dest, "views/shared.md", "本地视图标记\n")
            package = """\
---
handoff_version: "1.1"
origin_id: Grok-demo-sync
---

```ops
- op_id: Grok-demo-sync#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2026-10-12
  text: 包里的旧句

- op_id: Grok-demo-sync#2
  op: retract
  id: fact-a
  scope: shared
  base: Grok-demo-sync#1
  at: 2026-10-12
  text: 已撤回：本地事实
```
"""
            pending = replay_package(dest, package)
            self.assertEqual(pending, ["Grok-demo-sync#2"])
            self.assertEqual((dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8"), existing)
            self.assertEqual((dest / "outbox" / "Other-demo.md").read_text(encoding="utf-8"), other)
            self.assertEqual((dest / "environments" / "Grok-demo-sync.md").read_text(encoding="utf-8"), card)
            self.assertEqual((dest / "views" / "shared.md").read_text(encoding="utf-8"), "本地视图标记\n")
            self.assertFalse((dest / "STATUS.md").exists())

            added = replay_package(dest, package, confirmed=True)
            self.assertEqual(added, ["Grok-demo-sync#2"])
            outbox = (dest / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8")
            self.assertLess(outbox.index("op_id: Grok-demo-sync#1"), outbox.index("op_id: Grok-demo-sync#2"))
            self.assertIn("op: set", outbox)
            self.assertIn("text: 本地事实", outbox)
            self.assertNotIn("包里的旧句", outbox)
            self.assertEqual((dest / "outbox" / "Other-demo.md").read_text(encoding="utf-8"), other)
            self.assertEqual((dest / "environments" / "Grok-demo-sync.md").read_text(encoding="utf-8"), card)
            shared = (dest / "views" / "shared.md").read_text(encoding="utf-8")
            self.assertIn("{id:fact-b}", shared)
            self.assertNotIn("{id:fact-a}", shared)
            self.assertNotIn("本地视图标记", shared)

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
