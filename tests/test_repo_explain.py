"""Init and compile through scripts/compile_memory.py. The repo explains itself."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.compile import append_outbox  # noqa: E402
from topmind_handoff.package import PACKAGE_VERSION  # noqa: E402

SCRIPT = ROOT / "scripts" / "compile_memory.py"
SECRET = re.compile(
    r"\bsk-[A-Za-z0-9_-]{10,}|\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"
)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def run_case(dest: Path) -> str:
    """One fresh private repo. Returns the observations, or raises AssertionError."""
    notes: list[str] = []

    def ok(name: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(name)
        notes.append(f"OK {name}")

    public = dest.parent / "public-repo"
    refused = _run(["--init", str(public), "--public", "--origin", "Grok-demo-sync"])
    ok("public init writes nothing", refused.returncode != 0 and not public.exists())
    ok("public init says refused", "公开仓库拒绝" in refused.stdout + refused.stderr)

    private = dest
    created = _run(
        [
            "--init",
            str(private),
            "--private",
            "--origin",
            "Grok-demo-sync",
            "--role",
            "writing",
            "--today",
            "2026-10-13",
        ]
    )
    ok("private init exits 0", created.returncode == 0)
    readme = (private / "README.md").read_text(encoding="utf-8")
    status = (private / "STATUS.md").read_text(encoding="utf-8")
    authority = (private / "authority.md").read_text(encoding="utf-8")
    for phrase in (
        "outbox/<origin_id>.md",
        "environments/<origin_id>.md",
        "authority.md",
        "facts/",
        "views/shared.md",
        "views/scenario-<场景>.md",
        "STATUS.md",
        "human",
        "编译产物",
        "可以丢掉",
        "不写密码",
    ):
        ok(f"readme explains {phrase}", phrase in readme)
    ok("status says views are compile products", "编译产物" in status and "不是权威" in status)
    ok("authority names human", "owner: human" in authority and "outbox/human.md" in authority)
    ok("init did not invent a secret", SECRET.search(readme + status + authority) is None)

    other_text = """\
# outbox Other-demo

- op_id: Other-demo#1
  op: set
  id: pref-theme
  scope: shared
  base: none
  at: 2026-10-13
  text: 浅色方案
"""
    own_text = """\
# outbox Grok-demo-sync

- op_id: Grok-demo-sync#1
  op: set
  id: pref-theme
  scope: shared
  base: none
  at: 2026-10-13
  text: 深色方案
"""
    _write(private / "outbox" / "Other-demo.md", other_text)
    _write(private / "outbox" / "Grok-demo-sync.md", own_text)
    before = (private / "outbox" / "Other-demo.md").read_bytes()
    compiled = _run([str(private)])
    ok("compile exits 0", compiled.returncode == 0)
    ok("compile leaves the other outbox", (private / "outbox" / "Other-demo.md").read_bytes() == before)
    view = (private / "views" / "shared.md").read_text(encoding="utf-8")
    ok("conflict keeps both bodies", "未裁决" in view and "深色方案" in view and "浅色方案" in view)
    try:
        append_outbox(private, "Grok-demo-sync", "Other-demo", ["- op_id: Grok-demo-sync#9\n"])
        wrote = True
    except PermissionError:
        wrote = False
    ok("other origin append is refused", not wrote and (private / "outbox" / "Other-demo.md").read_bytes() == before)

    rendered = _run(["--render", str(private), "--origin", "Grok-demo-sync"])
    ok("render exits 0", rendered.returncode == 0)
    ok("package uses the shipped version", f'handoff_version: "{PACKAGE_VERSION}"' in rendered.stdout)
    ok("package invents no secret", SECRET.search(rendered.stdout) is None)
    ok("package has no secret field", "api_key:" not in rendered.stdout and "password:" not in rendered.stdout)
    return "\n".join(notes)


class RepoExplainTests(unittest.TestCase):
    def test_two_fresh_inits_explain_the_same_repo(self) -> None:
        reports = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                reports.append(run_case(base / "repo"))
                print(reports[-1])
        self.assertEqual(reports[0], reports[1])


if __name__ == "__main__":
    unittest.main()
