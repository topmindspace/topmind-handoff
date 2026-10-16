"""Compiler tests import the shipped module and drive it with files."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.compile import (  # noqa: E402
    append_outbox,
    compile_repo,
    save_environment_card,
    startup_read,
    status_is_valid,
)
from topmind_handoff.model import compile_ops, parse_authority, parse_outbox  # noqa: E402

AUTHORITY = """\
# 写入权

- scope: shared.identity
  owner: human
- scope: shared.boundaries
  owner: human
- scope: scenario.writing
  owner: Grok-demo-sync
- scope: scenario.coding
  owner: ClaudeCode-demo-sync
"""


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


class CompileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, "authority.md", AUTHORITY)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_distinct_ids_conflict_propose_closes_and_replay(self) -> None:
        write(
            self.root,
            "outbox/Grok-demo-sync.md",
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2020-01-01
  text: 甲事实
- op_id: Grok-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2020-01-01
  text: 深色方案
- op_id: Grok-demo-sync#3
  op: set
  id: scene-w
  scope: scenario:writing
  base: none
  at: 2026-02-01
  text: 主环境句子
""",
        )
        write(
            self.root,
            "outbox/ClaudeCode-demo-sync.md",
            """\
- op_id: ClaudeCode-demo-sync#1
  op: set
  id: fact-b
  scope: shared
  base: none
  at: 2026-10-01
  text: 乙事实
- op_id: ClaudeCode-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2026-10-01
  text: 浅色方案
- op_id: ClaudeCode-demo-sync#3
  op: set
  id: scene-c
  scope: scenario:coding
  base: none
  at: 2026-10-01
  text: 编程场景句子
""",
        )
        write(
            self.root,
            "outbox/Muse-demo-sync.md",
            """\
- op_id: Muse-demo-sync#1
  op: set
  id: scene-w
  scope: scenario:writing
  base: none
  at: 2026-10-12
  text: 非主环境句子
""",
        )
        write(
            self.root,
            "environments/Grok-demo-sync.md",
            """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
override.fact-a: 覆盖句只在本环境
---

路径：~/writing
""",
        )
        first = compile_repo(self.root)
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        writing = (self.root / "views" / "scenario-writing.md").read_text(encoding="utf-8")
        coding = (self.root / "views" / "scenario-coding.md").read_text(encoding="utf-8")
        status = (self.root / "STATUS.md").read_text(encoding="utf-8")

        self.assertIn("甲事实", shared)
        self.assertIn("乙事实", shared)
        self.assertIn("未裁决", shared)
        self.assertIn("深色方案", shared)
        self.assertIn("浅色方案", shared)
        self.assertNotIn("非主环境句子", writing)
        self.assertIn("主环境句子", writing)
        self.assertNotIn("编程场景句子", writing)
        self.assertIn("编程场景句子", coding)
        self.assertNotIn("主环境句子", coding)
        self.assertIn("非主环境句子", status)
        self.assertNotIn("覆盖句只在本环境", shared)

        second = compile_repo(self.root)
        self.assertEqual(
            (self.root / "views" / "shared.md").read_text(encoding="utf-8"),
            shared,
        )
        self.assertEqual(first.tips, second.tips)
        valid, _message = status_is_valid(self.root)
        self.assertTrue(valid)

        # Same op_id replayed inside an outbox does not duplicate the fact.
        outbox = self.root / "outbox" / "Grok-demo-sync.md"
        outbox.write_text(outbox.read_text(encoding="utf-8") + outbox.read_text(encoding="utf-8"), encoding="utf-8")
        compile_repo(self.root)
        again = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        self.assertEqual(again.count("{id:fact-a}"), 1)

        # A hand-edited view is discarded and rebuilt from the outboxes.
        (self.root / "views" / "shared.md").write_text("手工合并\n", encoding="utf-8")
        compile_repo(self.root)
        rebuilt = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        self.assertNotIn("手工合并", rebuilt)
        self.assertIn("甲事实", rebuilt)

        started = startup_read(self.root, "Grok-demo-sync")
        self.assertIn("覆盖句只在本环境", started)
        self.assertIn("主环境句子", started)
        self.assertNotIn("编程场景句子", started)
        self.assertIn("深色方案", started)
        self.assertNotIn("覆盖句只在本环境", (self.root / "views" / "shared.md").read_text(encoding="utf-8"))

    def test_override_drops_the_original_detail(self) -> None:
        write(
            self.root,
            "outbox/human.md",
            """\
- op_id: human#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2026-10-12
  text: 甲事实
  detail: |
    原始细节
""",
        )
        write(
            self.root,
            "environments/Grok-demo-sync.md",
            """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
override.fact-a: 覆盖句
---

路径：~/writing
""",
        )
        compile_repo(self.root)
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        self.assertIn("甲事实", shared)
        self.assertNotIn("原始细节", shared)
        started = startup_read(self.root, "Grok-demo-sync")
        self.assertIn("覆盖句", started)
        self.assertNotIn("原始细节", started)
        self.assertEqual((self.root / "views" / "shared.md").read_text(encoding="utf-8"), shared)
        from topmind_handoff.compile import open_claim

        opened = open_claim(self.root, "fact-a")
        self.assertIn("原始细节", opened)
        self.assertEqual((self.root / "views" / "shared.md").read_text(encoding="utf-8"), shared)

    def test_closes_leaves_one_head_and_clock_does_not_win(self) -> None:
        authority = parse_authority(AUTHORITY)
        left = parse_outbox(
            """\
- op_id: Grok-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2020-01-01
  text: 深色方案
""",
            "Grok-demo-sync",
        )
        right = parse_outbox(
            """\
- op_id: ClaudeCode-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2026-12-01
  text: 浅色方案
""",
            "ClaudeCode-demo-sync",
        )
        claims, _proposals = compile_ops(left + right, authority)
        result = claims[("shared", "pref-theme")]
        self.assertEqual(len(result.heads), 2)
        self.assertCountEqual([head.op_id for head in result.heads], ["Grok-demo-sync#2", "ClaudeCode-demo-sync#2"])

        later = parse_outbox(right[0].raw.replace("at: 2026-12-01", "at: 2030-01-01"), "ClaudeCode-demo-sync")
        claims_later, _ = compile_ops(left + later, authority)
        self.assertEqual(
            [head.op_id for head in claims_later[("shared", "pref-theme")].heads],
            [head.op_id for head in result.heads],
        )

        human = parse_outbox(
            """\
- op_id: human#1
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  closes: [Grok-demo-sync#2, ClaudeCode-demo-sync#2]
  at: 2026-10-12
  text: 裁决句
""",
            "human",
        )
        parent = parse_outbox(
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: pref-fork
  scope: shared
  base: none
  at: 2026-01-01
  text: 根
- op_id: Grok-demo-sync#4
  op: set
  id: pref-fork
  scope: shared
  base: Grok-demo-sync#1
  at: 2020-01-01
  text: 左支
""",
            "Grok-demo-sync",
        )
        sibling = parse_outbox(
            """\
- op_id: ClaudeCode-demo-sync#4
  op: set
  id: pref-fork
  scope: shared
  base: Grok-demo-sync#1
  at: 2026-12-01
  text: 右支
""",
            "ClaudeCode-demo-sync",
        )
        forked, _ = compile_ops(parent + sibling, authority)
        fork_heads = forked[("shared", "pref-fork")].heads
        self.assertEqual(len(fork_heads), 2)
        self.assertCountEqual([head.text for head in fork_heads], ["左支", "右支"])

        closed, _ = compile_ops(left + right + human, authority)
        heads = closed[("shared", "pref-theme")].heads
        self.assertEqual(len(heads), 1)
        self.assertEqual(heads[0].op_id, "human#1")
        self.assertEqual(heads[0].text, "裁决句")

        partial = parse_outbox(
            """\
- op_id: human#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  closes: [Grok-demo-sync#2]
  at: 2026-10-13
  text: 只盖一边
""",
            "human",
        )
        still_open, _ = compile_ops(left + right + partial, authority)
        open_heads = still_open[("shared", "pref-theme")].heads
        self.assertEqual(len(open_heads), 2)
        self.assertNotIn("human#2", [head.op_id for head in open_heads])

        twin_a = parse_outbox(
            """\
- op_id: human#3
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  closes: [Grok-demo-sync#2, ClaudeCode-demo-sync#2]
  at: 2026-10-14
  text: 裁决甲
""",
            "human",
        )
        twin_b = parse_outbox(
            """\
- op_id: Muse-demo-sync#3
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  closes: [ClaudeCode-demo-sync#2, Grok-demo-sync#2]
  at: 2030-01-01
  text: 裁决乙
""",
            "Muse-demo-sync",
        )
        twins, _ = compile_ops(left + right + twin_a + twin_b, authority)
        twin_heads = twins[("shared", "pref-theme")].heads
        self.assertEqual(len(twin_heads), 2)
        self.assertCountEqual([head.text for head in twin_heads], ["裁决甲", "裁决乙"])

    def test_sets_based_on_a_close_stay_on_the_chain(self) -> None:
        authority = parse_authority(AUTHORITY)
        grok = parse_outbox(
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2026-01-01
  text: 深色方案
""",
            "Grok-demo-sync",
        )
        claude = parse_outbox(
            """\
- op_id: ClaudeCode-demo-sync#1
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2026-02-01
  text: 浅色方案
""",
            "ClaudeCode-demo-sync",
        )
        human = parse_outbox(
            """\
- op_id: human#1
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  closes: [Grok-demo-sync#1, ClaudeCode-demo-sync#1]
  at: 2026-03-01
  text: 裁决句
""",
            "human",
        )
        continued = parse_outbox(
            """\
- op_id: Grok-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: human#1
  at: 2020-01-01
  text: 左续
""",
            "Grok-demo-sync",
        )
        alone, _ = compile_ops(grok + claude + human + continued, authority)
        alone_heads = alone[("shared", "pref-theme")].heads
        self.assertEqual(len(alone_heads), 1)
        self.assertEqual(alone_heads[0].op_id, "Grok-demo-sync#2")
        self.assertEqual(alone_heads[0].text, "左续")

        sibling = parse_outbox(
            """\
- op_id: ClaudeCode-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: human#1
  at: 2030-01-01
  text: 右续
""",
            "ClaudeCode-demo-sync",
        )
        forked, _ = compile_ops(grok + claude + human + continued + sibling, authority)
        fork_heads = forked[("shared", "pref-theme")].heads
        self.assertEqual(len(fork_heads), 2)
        self.assertCountEqual([head.text for head in fork_heads], ["左续", "右续"])
        self.assertNotIn("human#1", [head.op_id for head in fork_heads])

    def test_identity_boundaries_and_card_owner(self) -> None:
        write(
            self.root,
            "outbox/human.md",
            """\
- op_id: human#1
  op: set
  id: identity.name
  scope: shared
  slice: identity
  base: none
  at: 2026-10-12
  text: 人类身份句
- op_id: human#2
  op: set
  id: boundaries.ledger
  scope: shared
  slice: boundaries
  base: none
  at: 2026-10-12
  text: 人类边界句
""",
        )
        write(
            self.root,
            "outbox/ClaudeCode-demo-sync.md",
            """\
- op_id: ClaudeCode-demo-sync#9
  op: set
  id: identity.name
  scope: shared
  slice: identity
  base: none
  at: 2026-10-12
  text: 机器身份句
- op_id: ClaudeCode-demo-sync#10
  op: set
  id: boundaries.ledger
  scope: shared
  slice: boundaries
  base: none
  at: 2026-10-12
  text: 机器边界句
""",
        )
        compile_repo(self.root)
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        status = (self.root / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("人类身份句", shared)
        self.assertIn("人类边界句", shared)
        self.assertNotIn("机器身份句", shared)
        self.assertNotIn("机器边界句", shared)
        self.assertIn("机器身份句", status)

        card = self.root / "environments" / "Grok-demo-sync.md"
        with self.assertRaises(PermissionError):
            save_environment_card(self.root, "ClaudeCode-demo-sync", "Grok-demo-sync", "origin: Grok-demo-sync\n")
        self.assertFalse(card.exists())
        save_environment_card(self.root, "Grok-demo-sync", "Grok-demo-sync", "---\norigin: Grok-demo-sync\nrole: writing\n---\n")
        self.assertTrue(card.is_file())
        self.assertFalse((self.root / "environments" / "ClaudeCode-demo-sync.md").exists())

    def test_save_environment_card_rejects_origin_outside_the_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            repo.mkdir()
            outside = base / "escaped.md"
            before = {path for path in base.rglob("*") if path.is_file()}
            for origin in (str(base / "escaped"), "../evil", "nested/evil"):
                with self.assertRaises(ValueError):
                    save_environment_card(repo, origin, origin, "---\norigin: x\n---\n")
            after = {path for path in base.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(outside.exists())
            self.assertFalse((repo / "evil.md").exists())

    def test_hostile_scenario_name_is_not_written_outside_the_repo(self) -> None:
        write(
            self.root,
            "environments/Grok-demo-sync.md",
            """\
---
origin: Grok-demo-sync
role: ../evil
refreshed: 2026-10-12
---

路径：~/writing
""",
        )
        compile_repo(self.root)
        self.assertFalse((self.root / "evil.md").exists())
        self.assertFalse((self.root.parent / "evil.md").exists())
        self.assertTrue((self.root / "views" / "shared.md").is_file())

    def test_mismatched_status_is_invalid(self) -> None:
        write(
            self.root,
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
        compile_repo(self.root)
        ok, _message = status_is_valid(self.root)
        self.assertTrue(ok)
        status = self.root / "STATUS.md"
        status.write_text(status.read_text(encoding="utf-8").replace("Grok-demo-sync#1", "Grok-demo-sync#999"), encoding="utf-8")
        ok, message = status_is_valid(self.root)
        self.assertFalse(ok)
        self.assertIn("无效", message)

    def test_origin_scope_is_only_in_that_startup_read(self) -> None:
        write(
            self.root,
            "outbox/Grok-demo-sync.md",
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: local-tool
  scope: origin:Grok-demo-sync
  base: none
  at: 2026-10-12
  text: 只在 Grok
""",
        )
        write(
            self.root,
            "outbox/ClaudeCode-demo-sync.md",
            """\
- op_id: ClaudeCode-demo-sync#1
  op: set
  id: local-tool
  scope: origin:Grok-demo-sync
  base: none
  at: 2026-10-12
  text: 别人写的环境句
- op_id: ClaudeCode-demo-sync#2
  op: set
  id: local-editor
  scope: origin:ClaudeCode-demo-sync
  base: none
  at: 2026-10-12
  text: 只在 Claude
""",
        )
        compile_repo(self.root)
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        status = (self.root / "STATUS.md").read_text(encoding="utf-8")
        self.assertNotIn("只在 Grok", shared)
        self.assertNotIn("只在 Claude", shared)
        self.assertNotIn("别人写的环境句", shared)
        self.assertIn("别人写的环境句", status)
        grok = startup_read(self.root, "Grok-demo-sync")
        claude = startup_read(self.root, "ClaudeCode-demo-sync")
        self.assertIn("只在 Grok", grok)
        self.assertNotIn("只在 Claude", grok)
        self.assertNotIn("别人写的环境句", grok)
        self.assertIn("只在 Claude", claude)
        self.assertNotIn("只在 Grok", claude)

    def test_set_based_on_a_proposal_stays_on_the_chain(self) -> None:
        write(
            self.root,
            "outbox/Muse-demo-sync.md",
            """\
- op_id: Muse-demo-sync#1
  op: set
  id: scene-w
  scope: scenario:writing
  base: none
  at: 2026-10-12
  text: 非主环境句子
- op_id: Muse-demo-sync#2
  op: propose
  id: scene-prop
  scope: scenario:writing
  base: none
  at: 2026-10-12
  text: 显式提议
- op_id: Muse-demo-sync#3
  op: set
  id: scene-split
  scope: scenario:writing
  base: none
  at: 2026-10-12
  text: 分叉提议
""",
        )
        write(
            self.root,
            "outbox/Grok-demo-sync.md",
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: scene-w
  scope: scenario:writing
  base: Muse-demo-sync#1
  at: 2026-10-12
  text: 接上提议
- op_id: Grok-demo-sync#2
  op: set
  id: scene-prop
  scope: scenario:writing
  base: Muse-demo-sync#2
  at: 2026-10-12
  text: 接上显式提议
- op_id: Grok-demo-sync#3
  op: set
  id: scene-split
  scope: scenario:writing
  base: Muse-demo-sync#3
  at: 2026-10-12
  text: 甲续
- op_id: Grok-demo-sync#4
  op: set
  id: local-tool
  scope: origin:Grok-demo-sync
  base: ClaudeCode-demo-sync#2
  at: 2026-10-12
  text: 自己接上
- op_id: Grok-demo-sync#5
  op: set
  id: fact-x
  scope: shared
  base: Missing#1
  at: 2026-10-12
  text: 悬空句
""",
        )
        write(
            self.root,
            "outbox/ClaudeCode-demo-sync.md",
            """\
- op_id: ClaudeCode-demo-sync#1
  op: set
  id: name
  scope: shared
  slice: identity
  base: none
  at: 2026-10-12
  text: 机器自称
- op_id: ClaudeCode-demo-sync#2
  op: set
  id: local-tool
  scope: origin:Grok-demo-sync
  base: none
  at: 2026-10-12
  text: 别人的环境提议
""",
        )
        write(
            self.root,
            "outbox/human.md",
            """\
- op_id: human#1
  op: set
  id: name
  scope: shared
  slice: identity
  base: ClaudeCode-demo-sync#1
  at: 2026-10-12
  text: 张三
- op_id: human#2
  op: set
  id: scene-split
  scope: scenario:writing
  base: Muse-demo-sync#3
  at: 2026-10-12
  text: 乙续
""",
        )
        compile_repo(self.root)
        writing = (self.root / "views" / "scenario-writing.md").read_text(encoding="utf-8")
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        status = (self.root / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("- 接上提议 {id:scene-w}", writing)
        self.assertNotIn("非主环境句子", writing)
        self.assertIn("- 接上显式提议 {id:scene-prop}", writing)
        self.assertNotIn("- 显式提议 {id:scene-prop}", writing)
        self.assertIn("未裁决", writing)
        self.assertIn("甲续", writing)
        self.assertIn("乙续", writing)
        self.assertNotIn("分叉提议", writing)
        self.assertIn("- 张三 {id:name}", shared)
        self.assertNotIn("机器自称", shared)
        self.assertNotIn("悬空句", shared)
        self.assertIn("非主环境句子", status)
        self.assertIn("机器自称", status)
        self.assertIn("显式提议", status)
        self.assertIn("分叉提议", status)
        started = startup_read(self.root, "Grok-demo-sync")
        self.assertIn("自己接上", started)
        self.assertNotIn("别人的环境提议", started)

    def test_startup_read_does_not_follow_a_hostile_scenario_role(self) -> None:
        views = self.root / "views"
        views.mkdir(parents=True)
        (views / "scenario-writing").mkdir()
        planted = self.root / "evil.md"
        planted.write_text("LEAKED_SCENARIO\n", encoding="utf-8")
        write(
            self.root,
            "environments/Grok-demo-sync.md",
            """\
---
origin: Grok-demo-sync
role: writing/../../evil
refreshed: 2026-10-12
---

路径：~/writing
""",
        )
        before = {path for path in self.root.rglob("*") if path.is_file()}
        started = startup_read(self.root, "Grok-demo-sync")
        after = {path for path in self.root.rglob("*") if path.is_file()}
        self.assertNotIn("LEAKED_SCENARIO", started)
        self.assertEqual(before, after)
        outside = self.root.parent / f"symlink-secret-{self.root.name}.md"
        link = views / "scenario-writing.md"
        try:
            outside.write_text("SYMLINK_LEAK\n", encoding="utf-8")
            link.symlink_to(outside)
            write(
                self.root,
                "environments/Grok-demo-sync.md",
                """\
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
---

路径：~/writing
""",
            )
            followed = startup_read(self.root, "Grok-demo-sync")
            self.assertNotIn("SYMLINK_LEAK", followed)
            self.assertNotIn("LEAKED_SCENARIO", followed)
        finally:
            outside.unlink(missing_ok=True)

    def test_unknown_slice_stays_out_of_fact_and_compile_continues(self) -> None:
        write(
            self.root,
            "outbox/Grok-demo-sync.md",
            """\
- op_id: Grok-demo-sync#1
  op: set
  id: env-push
  scope: origin:Grok-demo-sync
  slice: environment
  base: none
  at: 2026-10-13
  text: 环境步骤只在本环境
- op_id: Grok-demo-sync#2
  op: set
  id: odd-left
  scope: shared
  slice: not-a-slice
  base: none
  at: 2020-01-01
  text: 左怪
- op_id: Grok-demo-sync#5
  op: set
  id: odd-kept
  scope: shared
  slice: not-a-slice
  base: none
  at: 2026-10-13
  text: 怪维度单独成节
- op_id: Grok-demo-sync#3
  op: set
  id: fact-later
  scope: shared
  slice: fact
  base: none
  at: 2026-10-13
  text: 后面的事实
- op_id: Grok-demo-sync#4
  op: set
  id: env-bad
  scope: shared
  slice: ../evil
  base: none
  at: 2026-10-13
  text: 越界维度
""",
        )
        write(
            self.root,
            "outbox/ClaudeCode-demo-sync.md",
            """\
- op_id: ClaudeCode-demo-sync#1
  op: set
  id: odd-left
  scope: shared
  slice: not-a-slice
  base: none
  at: 2026-12-01
  text: 右怪
""",
        )
        write(self.root, "outbox/Other-demo.md", "# outbox Other-demo\n- 别人的原文\n")
        foreign = (self.root / "outbox" / "Other-demo.md").read_bytes()
        parsed = parse_outbox(
            (self.root / "outbox" / "Grok-demo-sync.md").read_text(encoding="utf-8"),
            "Grok-demo-sync",
        )
        self.assertEqual(parsed[0].slice, "environment")
        self.assertEqual(parsed[1].slice, "not-a-slice")
        self.assertEqual(parsed[2].slice, "not-a-slice")
        compile_repo(self.root)
        self.assertEqual((self.root / "outbox" / "Other-demo.md").read_bytes(), foreign)
        self.assertFalse((self.root / "evil.md").exists())
        self.assertFalse((self.root.parent / "evil.md").exists())
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        fact = _section(shared, "## 事实")
        self.assertIn("后面的事实", fact)
        self.assertNotIn("环境步骤只在本环境", shared)
        self.assertNotIn("左怪", fact)
        self.assertNotIn("右怪", fact)
        self.assertNotIn("越界维度", fact)
        self.assertNotIn("怪维度单独成节", fact)
        odd = _section(shared, "## 维度：not-a-slice")
        self.assertIn("怪维度单独成节", odd)
        self.assertNotIn("左怪", odd)
        self.assertIn("未裁决", shared)
        self.assertIn("左怪", shared)
        self.assertIn("右怪", shared)
        later = (self.root / "outbox" / "ClaudeCode-demo-sync.md").read_text(encoding="utf-8")
        later = later.replace("at: 2026-12-01", "at: 2099-01-01")
        write(self.root, "outbox/ClaudeCode-demo-sync.md", later)
        compile_repo(self.root)
        again = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        self.assertIn("左怪", again)
        self.assertIn("右怪", again)
        self.assertIn("未裁决", _section(again, "## 冲突"))
        try:
            append_outbox(self.root, "Grok-demo-sync", "Other-demo", ["- op_id: Grok-demo-sync#9\n"])
        except PermissionError:
            refused = True
        else:
            refused = False
        self.assertTrue(refused)
        self.assertEqual((self.root / "outbox" / "Other-demo.md").read_bytes(), foreign)
        started = startup_read(self.root, "Grok-demo-sync")
        self.assertIn("环境步骤只在本环境", started)
        self.assertNotIn("事实", _heading_above(started, "环境步骤只在本环境"))
        self.assertNotIn("环境步骤只在本环境", (self.root / "views" / "shared.md").read_text(encoding="utf-8"))

    def test_stock_readme_upgrades_and_a_personal_note_stays(self) -> None:
        from topmind_handoff.admin import KNOWN_STOCK_READMES, memory_readme

        write(self.root, "outbox/Grok-demo-sync.md", "# outbox Grok-demo-sync\n")
        before = (self.root / "outbox" / "Grok-demo-sync.md").read_bytes()
        write(self.root, "README.md", KNOWN_STOCK_READMES[0])
        compile_repo(self.root)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertEqual(readme, memory_readme())
        self.assertIn("称呼：", readme)
        self.assertIn("base: none", readme)
        self.assertEqual((self.root / "outbox" / "Grok-demo-sync.md").read_bytes(), before)
        compile_repo(self.root)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), readme)
        noted = KNOWN_STOCK_READMES[1] + "人加的一句。\n"
        write(self.root, "README.md", noted)
        compile_repo(self.root)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), noted)
        self.assertEqual((self.root / "outbox" / "Grok-demo-sync.md").read_bytes(), before)

    def test_scope_move_retracts_the_old_chain(self) -> None:
        write(
            self.root,
            "outbox/Grok-demo-sync.md",
            """\
# outbox Grok-demo-sync

- op_id: Grok-demo-sync#1
  op: set
  id: habit
  scope: shared
  slice: preference
  base: none
  at: 2026-10-13
  text: 写作习惯只在写作
- op_id: Grok-demo-sync#2
  op: retract
  id: habit
  scope: shared
  base: Grok-demo-sync#1
  at: 2026-10-13
  text: 写作习惯只在写作
- op_id: Grok-demo-sync#3
  op: set
  id: habit
  scope: scenario:writing
  base: none
  at: 2026-10-13
  text: 写作习惯只在写作
- op_id: Grok-demo-sync#4
  op: set
  id: habit
  scope: scenario:writing
  base: Grok-demo-sync#1
  at: 2026-10-13
  text: 不该接上旧范围
""",
        )
        compiled = compile_repo(self.root)
        moved = compiled.claims[("scenario:writing", "habit")]
        self.assertEqual([op.op_id for op in moved.heads], ["Grok-demo-sync#3"])
        self.assertEqual([op.op_id for op in moved.unapplied], ["Grok-demo-sync#4"])
        shared = (self.root / "views" / "shared.md").read_text(encoding="utf-8")
        writing = (self.root / "views" / "scenario-writing.md").read_text(encoding="utf-8")
        self.assertNotIn("写作习惯只在写作", shared)
        self.assertEqual(writing.count("写作习惯只在写作"), 1)
        self.assertNotIn("不该接上旧范围", writing)


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    collecting = False
    found: list[str] = []
    for line in lines:
        if line == heading and not collecting:
            collecting = True
            continue
        if collecting and line.startswith("#"):
            break
        if collecting:
            found.append(line)
    return "\n".join(found)


def _heading_above(text: str, sentence: str) -> str:
    previous = ""
    for line in text.splitlines():
        if line.startswith("#"):
            previous = line
        if sentence in line:
            return previous
    return ""


if __name__ == "__main__":
    unittest.main()
