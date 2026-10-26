"""Behavioral regressions from the cross-tool design review. Synthetic data only."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.admin import init_memory_repo, organize_repo
from topmind_handoff.compile import append_outbox, compile_repo, save_environment_card, startup_read, status_is_valid
from topmind_handoff.package import legacy_import_plan, render_package, replay_package


def put(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def op(oid: str, *, cid: str = "claim-a", slice_name: str = "fact", base: str = "none", kind: str = "set", closes: str = "[]", text: str = "事实", scope: str = "shared") -> str:
    return (
        f"- op_id: {oid}\n  op: {kind}\n  id: {cid}\n  scope: {scope}\n"
        f"  slice: {slice_name}\n  base: {base}\n  closes: {closes}\n"
        f"  at: 2020-01-01\n  text: {text}\n"
    )


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class HardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_human_claim_cannot_be_downgraded_or_closed_by_another_origin(self) -> None:
        for protected in ("identity", "boundaries"):
            for category in ("fact", "unknown"):
                for kind in ("set", "retract", "close"):
                    with self.subTest(protected=protected, category=category, kind=kind):
                        root = self.root / f"{protected}-{category}-{kind}"
                        put(root, "outbox/human.md", op("human#1", slice_name=protected, text="用户原文"))
                        put(root, "outbox/Grok-demo-sync.md", op(
                            "Grok-demo-sync#1", slice_name=category, base="human#1",
                            kind="set" if kind == "close" else kind,
                            closes="[human#1]" if kind == "close" else "[]", text="环境改写",
                        ))
                        result = compile_repo(root)
                        self.assertEqual([h.origin for h in result.claims[("shared", "claim-a")].heads], ["human"])
                        self.assertEqual(len(result.proposals), 1)

    def test_card_override_keeps_human_claim_in_plain_and_archived_projection(self) -> None:
        for organized in (False, True):
            with self.subTest(organized=organized):
                root = self.root / str(organized)
                claims = op("human#1", slice_name="boundaries", text="用户原文")
                if organized:
                    claims += "".join(op(f"human#{i+2}", cid=f"other-{i}", slice_name="boundaries") for i in range(220))
                put(root, "outbox/human.md", claims)
                put(root, "environments/Grok-demo-sync.md", "---\nrole: writing\noverride.claim-a: 环境改写\n---\n")
                compile_repo(root)
                if organized:
                    organize_repo(root, date(2026, 10, 26))
                body = startup_read(root, "Grok-demo-sync").split("## 环境卡片", 1)[0]
                self.assertNotIn("环境改写", body)
                self.assertIn("用户原文", body)

    def test_check_and_startup_reject_changed_inputs_or_outputs(self) -> None:
        mutations = {
            "authority": lambda r: put(r, "authority.md", "- scope: scenario.writing\n  owner: Other-demo-sync\n"),
            "card": lambda r: put(r, "environments/Grok-demo-sync.md", "---\nrole: coding\n---\n"),
            "middle": lambda r: put(r, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1", text="篡改正文")),
            "view": lambda r: put(r, "views/shared.md", "篡改视图\n"),
            "missing": lambda r: (r / "views/shared.md").unlink(),
            "status": lambda r: put(r, "STATUS.md", (r / "STATUS.md").read_text().replace("facts: 1", "facts: 999")),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                root = self.root / name
                put(root, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1"))
                put(root, "environments/Grok-demo-sync.md", "---\nrole: writing\n---\n")
                compile_repo(root)
                self.assertTrue(status_is_valid(root)[0])
                mutate(root)
                self.assertFalse(status_is_valid(root)[0])
                before = snapshot(root)
                with self.assertRaises(ValueError):
                    startup_read(root, "Grok-demo-sync")
                self.assertEqual(snapshot(root), before)
                compile_repo(root)
                self.assertTrue(status_is_valid(root)[0])

    def test_package_missing_cross_origin_base_is_rejected_without_writes(self) -> None:
        source = self.root / "source"
        put(source, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1"))
        put(source, "outbox/ClaudeCode-demo-sync.md", op("ClaudeCode-demo-sync#1", base="Grok-demo-sync#1", text="后继"))
        package = render_package(source, "ClaudeCode-demo-sync")
        dest = self.root / "dest"
        dest.mkdir()
        for confirmed in (False, True):
            with self.assertRaisesRegex(ValueError, "依赖|裁决"):
                replay_package(dest, package, confirmed=confirmed)
            self.assertEqual(snapshot(dest), {})
        put(dest, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1"))
        replay_package(dest, package, confirmed=True)
        self.assertIn("后继", (dest / "views/shared.md").read_text())
        self.assertEqual(replay_package(dest, package, confirmed=True), [])

    def test_identical_duplicates_are_idempotent_but_changed_payload_is_rejected(self) -> None:
        original = op("Grok-demo-sync#1")
        put(self.root, "outbox/Grok-demo-sync.md", original + original)
        compile_repo(self.root)
        before = (self.root / "views/shared.md").read_bytes()
        self.assertEqual((self.root / "views/shared.md").read_text().count("{id:claim-a}"), 1)
        package = render_package(self.root, "Grok-demo-sync").replace("  text: 事实", "  text: 另一正文")
        current = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "op_id"):
            replay_package(self.root, package, confirmed=True)
        self.assertEqual(snapshot(self.root), current)
        with self.assertRaisesRegex(ValueError, "op_id"):
            append_outbox(self.root, "Grok-demo-sync", "Grok-demo-sync", [op("Grok-demo-sync#1", text="另一正文")])
        self.assertEqual(snapshot(self.root), current)
        put(self.root, "outbox/Grok-demo-sync.md", original + op("Grok-demo-sync#1", text="另一正文"))
        with self.assertRaisesRegex(ValueError, "op_id"):
            compile_repo(self.root)
        self.assertEqual((self.root / "views/shared.md").read_bytes(), before)

    def test_organize_preserves_all_source_cards_and_derives_staleness(self) -> None:
        put(self.root, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1"))
        put(self.root, "environments/Other-demo-sync.md", "---\nrole: writing\nrefreshed: 2020-01-01\n---\n")
        before = snapshot(self.root)
        organize_repo(self.root, date(2026, 10, 26))
        for name, content in before.items():
            self.assertEqual((self.root / name).read_bytes(), content)
        status = (self.root / "STATUS.md").read_text()
        self.assertIn("环境卡片 `Other-demo-sync` 未刷新", status)
        self.assertIn("stale: true", status)
        self.assertTrue(status_is_valid(self.root)[0])

    def test_today_labels_are_read_only_and_do_not_choose_a_head(self) -> None:
        put(self.root, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1"))
        compile_repo(self.root)
        before = snapshot(self.root)
        early = startup_read(self.root, "Grok-demo-sync", today=date(2020, 1, 2))
        late = startup_read(self.root, "Grok-demo-sync", today=date(2026, 10, 26))
        self.assertNotIn("未复核", early)
        self.assertIn("未复核", late)
        self.assertIn("{id:claim-a}", early)
        self.assertIn("{id:claim-a}", late)
        self.assertEqual(snapshot(self.root), before)

    def test_sensitive_origin_is_rejected_before_initialization(self) -> None:
        marker = "ghp_" + "x" * 40
        with self.assertRaises(ValueError) as raised:
            init_memory_repo(self.root, private=True, origin=marker)
        self.assertNotIn(marker, str(raised.exception))
        self.assertEqual(snapshot(self.root), {})
        with self.assertRaises(ValueError) as raised:
            save_environment_card(self.root, marker, "Grok-demo-sync", "普通内容")
        self.assertNotIn(marker, str(raised.exception))
        self.assertEqual(snapshot(self.root), {})

    def test_sensitive_values_are_blocked_before_writes_and_not_echoed(self) -> None:
        values = ["ghp_" + "x" * 40, "sk-" + "x" * 32, "-----BEGIN " + "PRIVATE KEY-----", "/" + "Users/" + "private-person/data"]
        for index, marker in enumerate(values):
            with self.subTest(index=index):
                root = self.root / str(index)
                root.mkdir()
                for write in (
                    lambda: append_outbox(root, "Grok-demo-sync", "Grok-demo-sync", [op("Grok-demo-sync#1", text=marker)]),
                    lambda: save_environment_card(root, "Grok-demo-sync", "Grok-demo-sync", marker),
                ):
                    with self.assertRaises(ValueError) as raised:
                        write()
                    self.assertNotIn(marker, str(raised.exception))
                    self.assertEqual(snapshot(root), {})
                put(root, "outbox/Grok-demo-sync.md", op("Grok-demo-sync#1", text=marker))
                before = snapshot(root)
                with self.assertRaises(ValueError) as raised:
                    render_package(root, "Grok-demo-sync")
                self.assertNotIn(marker, str(raised.exception))
                self.assertEqual(snapshot(root), before)
                result = subprocess.run([sys.executable, str(ROOT / "scripts/compile_memory.py"), "--render", str(root), "--origin", "Grok-demo-sync"], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(marker, result.stdout + result.stderr)
                package = f'---\nhandoff_version: "2"\norigin_id: Grok-demo-sync\n---\n```ops\n{op("Grok-demo-sync#1", text=marker)}```\n'
                dest = root / "receive"
                for receiver in (
                    lambda: replay_package(dest, package, confirmed=True),
                    lambda: legacy_import_plan(package, {}),
                ):
                    with self.assertRaises(ValueError) as raised:
                        receiver()
                    self.assertNotIn(marker, str(raised.exception))
                    self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
