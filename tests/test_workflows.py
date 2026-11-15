"""High-level CLI and API workflows: auto base chaining, per-origin current work, topic handoff, conflict resolution, and cleanup."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.admin import init_memory_repo  # noqa: E402
from topmind_handoff.compile import (  # noqa: E402
    build_compiled,
    record_retract,
    record_resolve,
    record_set,
    record_work,
    startup_read,
    status_is_valid,
)
from topmind_handoff.package import render_package  # noqa: E402

SCRIPT = ROOT / "scripts" / "compile_memory.py"


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "mem"
        init_memory_repo(
            self.repo,
            private=True,
            origin="Grok-demo-sync",
            role="writing",
            today="2026-11-15",
        )

    def test_auto_base_prevents_false_conflict_across_origins(self) -> None:
        oid1 = record_set(
            self.repo,
            origin="Grok-demo-sync",
            claim_id="pref-theme",
            text="浅色方案",
            slice_name="preference",
        )
        self.assertEqual(oid1, "Grok-demo-sync#1")
        oid2 = record_set(
            self.repo,
            origin="ClaudeCode-demo-sync",
            claim_id="pref-theme",
            text="深色方案",
        )
        self.assertEqual(oid2, "ClaudeCode-demo-sync#1")
        compiled = build_compiled(self.repo)
        result = compiled.claims[("shared", "pref-theme")]
        self.assertFalse(result.conflict)
        self.assertEqual([h.op_id for h in result.heads], ["ClaudeCode-demo-sync#1"])
        self.assertEqual(result.heads[0].slice, "preference")
        self.assertEqual(result.heads[0].text, "深色方案")
        ok, _ = status_is_valid(self.repo)
        self.assertTrue(ok)

    def test_per_origin_current_work_and_cross_origin_awareness(self) -> None:
        res1 = _cli(
            "--work",
            str(self.repo),
            "--origin",
            "Grok-demo-sync",
            "--text",
            "正在撰写交接机制文档，下一步补充示例",
            "--today",
            "2026-11-15",
        )
        self.assertEqual(res1.returncode, 0, res1.stdout + res1.stderr)
        res2 = _cli(
            "--work",
            str(self.repo),
            "--origin",
            "ClaudeCode-demo-sync",
            "--text",
            "正在实现 CLI 自动化参数，产出在 topmind_handoff/cli.py",
            "--today",
            "2026-11-15",
        )
        self.assertEqual(res2.returncode, 0, res2.stdout + res2.stderr)
        res3 = _cli(
            "--work",
            str(self.repo),
            "--origin",
            "Grok-demo-sync",
            "--text",
            "交接机制文档已完稿，等待审阅",
            "--today",
            "2026-11-15",
        )
        self.assertEqual(res3.returncode, 0, res3.stdout + res3.stderr)

        startup = startup_read(self.repo, "ClaudeCode-demo-sync")
        self.assertIn("# 开工读取（ClaudeCode-demo-sync）", startup)
        self.assertNotIn("\n# 共享\n", startup)
        self.assertIn("[Grok-demo-sync] 交接机制文档已完稿，等待审阅 {id:work.Grok-demo-sync}", startup)
        self.assertNotIn("正在撰写交接机制文档，下一步补充示例", startup)
        self.assertIn(
            "[ClaudeCode-demo-sync] 正在实现 CLI 自动化参数，产出在 topmind_handoff/cli.py {id:work.ClaudeCode-demo-sync}",
            startup,
        )

        done_res = _cli(
            "--work",
            str(self.repo),
            "--origin",
            "Grok-demo-sync",
            "--done",
            "--today",
            "2026-11-15",
        )
        self.assertEqual(done_res.returncode, 0, done_res.stdout + done_res.stderr)
        startup_after = startup_read(self.repo, "ClaudeCode-demo-sync")
        self.assertNotIn("work.Grok-demo-sync", startup_after)
        self.assertIn("work.ClaudeCode-demo-sync", startup_after)

    def test_local_work_and_named_topic_handoff(self) -> None:
        record_work(
            self.repo,
            origin="Grok-demo-sync",
            text="本机草稿整理在 ~/drafts",
            local=True,
        )
        other_view = startup_read(self.repo, "ClaudeCode-demo-sync")
        own_view = startup_read(self.repo, "Grok-demo-sync")
        self.assertNotIn("本机草稿整理", other_view)
        self.assertIn("本机草稿整理在 ~/drafts {id:work.current}", own_view)

        record_work(
            self.repo,
            origin="Grok-demo-sync",
            topic="handoff-v08",
            text="已完成方案设计，请编程环境接手实现",
        )
        record_work(
            self.repo,
            origin="ClaudeCode-demo-sync",
            topic="handoff-v08",
            text="已完成代码实现与测试验证",
        )
        compiled = build_compiled(self.repo)
        proj = compiled.claims[("shared", "project.handoff-v08")]
        self.assertFalse(proj.conflict)
        self.assertEqual(proj.heads[0].text, "已完成代码实现与测试验证")
        self.assertEqual(proj.heads[0].origin, "ClaudeCode-demo-sync")

    def test_retract_then_set_again_chains_cleanly(self) -> None:
        record_set(self.repo, origin="Grok-demo-sync", claim_id="temp-fact", text="第一版说法")
        record_retract(self.repo, origin="Grok-demo-sync", claim_id="temp-fact")
        self.assertTrue(build_compiled(self.repo).claims[("shared", "temp-fact")].retracted)

        record_set(self.repo, origin="ClaudeCode-demo-sync", claim_id="temp-fact", text="重新启用后的新说法")
        result = build_compiled(self.repo).claims[("shared", "temp-fact")]
        self.assertFalse(result.conflict)
        self.assertFalse(result.retracted)
        self.assertEqual(result.heads[0].text, "重新启用后的新说法")

    def test_conflict_detection_and_cli_resolve(self) -> None:
        record_set(
            self.repo,
            origin="Grok-demo-sync",
            claim_id="pref-editor",
            text="使用 Vim",
            slice_name="preference",
            base="none",
        )
        record_set(
            self.repo,
            origin="ClaudeCode-demo-sync",
            claim_id="pref-editor",
            text="使用 VSCode",
            slice_name="preference",
            base="none",
        )
        self.assertTrue(build_compiled(self.repo).claims[("shared", "pref-editor")].conflict)

        blocked = _cli(
            "--set",
            str(self.repo),
            "--origin",
            "Grok-demo-sync",
            "--id",
            "pref-editor",
            "--text",
            "试图直接覆盖",
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("未裁决冲突", blocked.stdout)

        resolved = _cli(
            "--resolve",
            str(self.repo),
            "--origin",
            "Grok-demo-sync",
            "--id",
            "pref-editor",
            "--text",
            "主力用 VSCode，终端用 Vim",
        )
        self.assertEqual(resolved.returncode, 0, resolved.stdout + resolved.stderr)
        after = build_compiled(self.repo).claims[("shared", "pref-editor")]
        self.assertFalse(after.conflict)
        self.assertEqual(after.heads[0].text, "主力用 VSCode，终端用 Vim")

    def test_cli_replay_preview_and_confirm(self) -> None:
        record_set(self.repo, origin="Grok-demo-sync", claim_id="fact-sync", text="跨端同步条目")
        pkg_text = render_package(self.repo, "Grok-demo-sync")
        pkg_file = Path(self.temp.name) / "pkg.md"
        pkg_file.write_text(pkg_text, encoding="utf-8")

        peer = Path(self.temp.name) / "peer"
        init_memory_repo(peer, private=True, origin="ClaudeCode-demo-sync", role="coding", today="2026-11-15")

        preview = _cli("--replay", str(peer), "--file", str(pkg_file))
        self.assertEqual(preview.returncode, 0)
        self.assertIn("preview: Grok-demo-sync#1", preview.stdout)
        self.assertNotIn(("shared", "fact-sync"), build_compiled(peer).claims)

        confirmed = _cli("--replay", str(peer), "--file", str(pkg_file), "--confirm")
        self.assertEqual(confirmed.returncode, 0)
        self.assertIn("replayed: Grok-demo-sync#1", confirmed.stdout)
        self.assertIn(("shared", "fact-sync"), build_compiled(peer).claims)
        ok, _ = status_is_valid(peer)
        self.assertTrue(ok)

    def test_idempotent_same_day_set_and_authority_guards(self) -> None:
        oid1 = record_set(
            self.repo,
            origin="Grok-demo-sync",
            claim_id="pref-lang",
            text="全程中文",
            slice_name="preference",
        )
        oid2 = record_set(
            self.repo,
            origin="Grok-demo-sync",
            claim_id="pref-lang",
            text="全程中文",
            slice_name="preference",
        )
        self.assertEqual(oid1, oid2)

        with self.assertRaises(ValueError):
            record_set(
                self.repo,
                origin="Grok-demo-sync",
                claim_id="env-other",
                text="越权写入",
                scope="origin:Other-demo",
            )

        record_set(
            self.repo,
            origin="human",
            claim_id="identity.name",
            text="称呼：张三",
            slice_name="identity",
        )
        with self.assertRaises(ValueError):
            record_retract(
                self.repo,
                origin="Grok-demo-sync",
                claim_id="identity.name",
            )

        bad_day = _cli(str(self.repo), "--today", "2026-99-99")
        self.assertNotEqual(bad_day.returncode, 0)
        self.assertIn("日期格式无效", bad_day.stdout)


if __name__ == "__main__":
    unittest.main()
