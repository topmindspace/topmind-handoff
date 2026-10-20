"""Standalone docs: install commands, quoted memory README, no other skill names."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.admin import memory_readme  # noqa: E402
from topmind_handoff.model import parse_outbox  # noqa: E402

FORBIDDEN = (
    "topmind-capture",
    "topmind-memory",
    "topmind-organize",
    "topmind-write",
    "topmind-writing-skills",
    "topmind-skills",
    "topmind-wechat",
)


def scanned_files() -> list[Path]:
    groups = [
        [ROOT / "SKILL.md", ROOT / "README.md", ROOT / "evals" / "evals.json"],
        sorted((ROOT / "references").glob("*.md")),
        sorted((ROOT / "assets").glob("*.md")),
        sorted((ROOT / "examples").glob("*.md")),
        sorted((ROOT / "bin").glob("*.js")),
    ]
    return [path for group in groups for path in group]


class StandaloneDocs(unittest.TestCase):
    def test_no_other_skill_names(self) -> None:
        for path in scanned_files():
            text = path.read_text(encoding="utf-8")
            for name in FORBIDDEN:
                self.assertNotIn(name, text, f"{path.relative_to(ROOT)} mentions {name}")

    def test_install_commands_are_in_the_docs_a_person_or_package_reads(self) -> None:
        for rel in ("README.md", "references/environment.md", "references/spec.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("npx @topmindspace/topmind-handoff@latest install", text, rel)
            self.assertIn("npx @topmindspace/topmind-handoff@latest update", text, rel)

    def test_example_quotes_the_init_readme(self) -> None:
        text = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        start = "<!-- memory-readme:start -->\n"
        end = "<!-- memory-readme:end -->"
        begin = text.index(start) + len(start)
        stop = text.index(end, begin)
        self.assertEqual(text[begin:stop], memory_readme())

    def test_example_op_parses(self) -> None:
        text = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        start = "<!-- op-sample:start -->\n"
        end = "<!-- op-sample:end -->"
        body = text[text.index(start) + len(start) : text.index(end)]
        fenced = body.split("```", 2)[1]
        inner = fenced.split("\n", 1)[1]
        ops = parse_outbox(inner, "Grok-demo-sync")
        self.assertEqual([op.claim_id for op in ops], ["pref-zh"])
        self.assertEqual(ops[0].scope, "shared")
        self.assertEqual(ops[0].text, "全程中文")
