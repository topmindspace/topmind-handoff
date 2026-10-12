"""Compiler tests import the shipped module and drive it with files."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.compile import (  # noqa: E402
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
        self.assertIn("原始细节", shared)
        started = startup_read(self.root, "Grok-demo-sync")
        self.assertIn("覆盖句", started)
        self.assertNotIn("原始细节", started)
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


if __name__ == "__main__":
    unittest.main()
