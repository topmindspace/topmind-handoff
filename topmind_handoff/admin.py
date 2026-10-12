"""Init an empty memory repo and run a user-triggered organize pass."""

from __future__ import annotations

import subprocess
from datetime import date, datetime
from pathlib import Path

from topmind_handoff.compile import VIEW_ORDER as SLICE_ORDER
from topmind_handoff.compile import build_compiled, render_status
from topmind_handoff.model import (
    INDEX_BYTE_BUDGET,
    INDEX_LINE_BUDGET,
    REVIEW_DAYS,
    SLICE_TITLE,
    ClaimResult,
    Compiled,
    Op,
    parse_authority,
    scenario_names,
)


class PublicRepoRefused(RuntimeError):
    """Raised when init is asked to write a public memory repo."""


def _nl(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def init_memory_repo(
    path: Path,
    *,
    private: bool,
    origin: str,
    role: str = "general",
    today: str | None = None,
) -> Path:
    """Write a skeleton, compile empty views, and make one local commit.

    A public repo is refused before any directory or file is created.
    """
    if not private:
        raise PublicRepoRefused("公开仓库拒绝")
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"{path} 不是空目录")
    path.mkdir(parents=True, exist_ok=True)
    refreshed = today or date.today().isoformat()
    (path / "README.md").write_text(
        _nl(
            "\n".join(
                [
                    "# 云端记忆",
                    "",
                    "这个目录的 HEAD 是当前记忆。共享视图、场景视图和 STATUS.md 由本机脚本编译，不由 CI 生成。",
                    "开工时读共享视图、本环境所属的一个场景、本环境卡片，以及与本环境有关的冲突。",
                    "编译规则只在 topmind-handoff 的 `references/compile.md`。",
                    "",
                ]
            )
        ),
        encoding="utf-8",
    )
    (path / "authority.md").write_text(
        _nl(
            "\n".join(
                [
                    "# 写入权",
                    "",
                    "- scope: shared.identity",
                    "  owner: human",
                    "- scope: shared.boundaries",
                    "  owner: human",
                    "",
                ]
            )
        ),
        encoding="utf-8",
    )
    outbox = path / "outbox"
    outbox.mkdir()
    (outbox / f"{origin}.md").write_text(_nl(f"# outbox {origin}\n"), encoding="utf-8")
    environments = path / "environments"
    environments.mkdir()
    (environments / f"{origin}.md").write_text(
        _nl(
            "\n".join(
                [
                    "---",
                    f"origin: {origin}",
                    f"role: {role}",
                    f"refreshed: {refreshed}",
                    "---",
                    "",
                    "工具：未填写",
                    "路径：~/",
                    "",
                ]
            )
        ),
        encoding="utf-8",
    )
    from topmind_handoff.compile import compile_repo

    compile_repo(path)
    _git_commit(path, "初始化云端记忆")
    return path


def set_scenario_owner(repo: Path, scenario: str, origin: str) -> None:
    """Give one origin direct writes on a scenario. Identity and boundaries stay with human."""
    path = Path(repo) / "authority.md"
    current = parse_authority(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current["shared.identity"] = "human"
    current["shared.boundaries"] = "human"
    current[f"scenario.{scenario}"] = origin
    order = ["shared.identity", "shared.boundaries"]
    rest = sorted(key for key in current if key not in order)
    lines = ["# 写入权", ""]
    for key in order + rest:
        lines.append(f"- scope: {key}")
        lines.append(f"  owner: {current[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _git_commit(path: Path, message: str) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=handoff@example.com",
            "-c",
            "user.name=topmind-handoff",
            "commit",
            "-m",
            message,
        ],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _parse_day(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _review_suffix(op: Op, today: date) -> str:
    limit = REVIEW_DAYS.get(op.slice)
    written = _parse_day(op.at)
    if limit is None or written is None:
        return ""
    if (today - written).days >= limit:
        return " （未复核）"
    return ""


def _results_for(compiled: Compiled, scope: str) -> list[ClaimResult]:
    return [result for (item_scope, _cid), result in compiled.claims.items() if item_scope == scope]


def _compact_scope(title: str, results: list[ClaimResult], today: date, facts_root: Path, fact_prefix: str) -> str:
    sections: dict[str, list[str]] = {name: [] for name in SLICE_ORDER}
    details: dict[str, list[str]] = {name: [] for name in SLICE_ORDER}
    for result in sorted(results, key=lambda item: item.claim_id):
        if result.conflict or result.retracted or not result.heads:
            continue
        head = result.heads[0]
        if head.kind != "set":
            continue
        line = f"- {head.text} {{id:{head.claim_id}}}{_review_suffix(head, today)}"
        sections.setdefault(head.slice, []).append(line)
        if head.detail or _review_suffix(head, today):
            block = [f"## {head.claim_id}", line]
            if head.detail:
                block.extend(head.detail.splitlines())
            block.append("")
            details.setdefault(head.slice, []).extend(block)

    def render(section_map: dict[str, list[str]]) -> str:
        lines = [f"# {title}", ""]
        for slice_name in SLICE_ORDER:
            lines.append(f"## {SLICE_TITLE[slice_name]}")
            body = section_map.get(slice_name) or []
            lines.extend(body or ["（无）"])
            lines.append("")
        lines.append("## 冲突")
        conflicts = sorted((item for item in results if item.conflict), key=lambda item: item.claim_id)
        if conflicts:
            for result in conflicts:
                lines.append(f"- {{id:{result.claim_id}}} 未裁决")
                for head in result.heads:
                    label = "撤回" if head.kind == "retract" else head.text
                    lines.append(f"  - {head.op_id}（{head.at or '无日期'}）：{label}")
        else:
            lines.append("（无）")
        lines.append("")
        return _nl("\n".join(lines))

    for slice_name, block in details.items():
        if not block:
            continue
        facts_root.mkdir(parents=True, exist_ok=True)
        (facts_root / f"{fact_prefix}-{slice_name}.md").write_text(
            _nl("# " + slice_name + "\n\n" + "\n".join(block)), encoding="utf-8"
        )

    text = render(sections)
    # Collapse the largest slices until the index fits the startup budget.
    collapsible = [name for name in ("fact", "preference", "project", "identity", "boundaries")]
    while (text.count("\n") > INDEX_LINE_BUDGET or len(text.encode("utf-8")) > INDEX_BYTE_BUDGET) and any(
        len(sections.get(name) or []) > 1 for name in collapsible
    ):
        name = max(collapsible, key=lambda item: len(sections.get(item) or []))
        count = len(sections.get(name) or [])
        if count <= 1:
            break
        sections[name] = [f"- 见 facts/{fact_prefix}-{name}.md（{count} 条）"]
        text = render(sections)
    return text


def _mark_stale(card_path: Path, today: date) -> None:
    raw = card_path.read_text(encoding="utf-8")
    card = _card_refreshed(raw)
    if card is None:
        return
    if (today - card).days < 90:
        return
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        front = parts[1]
        body = parts[2] if len(parts) > 2 else ""
        if "stale:" not in front:
            front = front.rstrip() + "\nstale: true\n"
        else:
            front = front.replace("stale: false", "stale: true")
        if "未刷新" not in body:
            body = body.rstrip() + "\n\n未刷新\n"
        card_path.write_text(_nl("---" + front + "---" + body), encoding="utf-8")
        return
    extra = ""
    if "stale: true" not in raw:
        extra += "stale: true\n"
    if "未刷新" not in raw:
        extra += "未刷新\n"
    if extra:
        card_path.write_text(_nl(raw.rstrip() + "\n" + extra), encoding="utf-8")


def _card_refreshed(raw: str) -> date | None:
    for line in raw.splitlines():
        if line.startswith("refreshed:"):
            return _parse_day(line.split(":", 1)[1].strip())
    return None


def organize_repo(repo: Path, today: date | None = None) -> Compiled:
    """Compact the fact index, label due facts, and mark stale cards.

    Outbox files are not rewritten. There is no timer and no resident process.
    """
    repo = Path(repo)
    today = today or date.today()
    outbox = repo / "outbox"
    before = {path.name: path.read_bytes() for path in sorted(outbox.glob("*.md"))} if outbox.is_dir() else {}
    compiled = build_compiled(repo)
    views = repo / "views"
    views.mkdir(parents=True, exist_ok=True)
    facts_root = repo / "facts"
    shared = _results_for(compiled, "shared")
    (views / "shared.md").write_text(
        _compact_scope("共享", shared, today, facts_root, "shared"), encoding="utf-8"
    )
    known_ops: list[Op] = list(compiled.proposals)
    for result in compiled.claims.values():
        known_ops.extend(result.heads)
        known_ops.extend(result.unapplied)
    names = scenario_names(compiled.authority, compiled.cards, known_ops)
    keep = {f"scenario-{name}.md" for name in names}
    for name in names:
        scope = f"scenario:{name}"
        text = _compact_scope(f"场景：{name}", _results_for(compiled, scope), today, facts_root, f"scenario-{name}")
        (views / f"scenario-{name}.md").write_text(text, encoding="utf-8")
    for path in views.glob("scenario-*.md"):
        if path.name not in keep:
            path.unlink()
    environments = repo / "environments"
    if environments.is_dir():
        for path in sorted(environments.glob("*.md")):
            _mark_stale(path, today)
    # Cards may now be stale; rebuild status from the same outbox tips.
    compiled = build_compiled(repo)
    (repo / "STATUS.md").write_text(render_status(compiled), encoding="utf-8")
    after = {path.name: path.read_bytes() for path in sorted(outbox.glob("*.md"))} if outbox.is_dir() else {}
    if before != after:
        raise RuntimeError("整理改写了信箱")
    return compiled
