"""Read a memory directory, compile views, and check status tips."""

from __future__ import annotations

import re
from pathlib import Path

from topmind_handoff.model import (
    SLICE_TITLE,
    Card,
    ClaimResult,
    Compiled,
    Op,
    compile_ops,
    compiler_version,
    parse_authority,
    parse_card,
    parse_outbox,
    scenario_names,
)

VIEW_ORDER = ("identity", "boundaries", "preference", "project", "fact")


def _ensure_nl(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def load_pieces(repo: Path) -> tuple[dict[str, str], dict[str, str], dict[str, Card], list[Op]]:
    authority_path = repo / "authority.md"
    authority = parse_authority(authority_path.read_text(encoding="utf-8")) if authority_path.is_file() else {}
    tips: dict[str, str] = {}
    ops: list[Op] = []
    outbox = repo / "outbox"
    if outbox.is_dir():
        for path in sorted(outbox.glob("*.md")):
            file_ops = parse_outbox(path.read_text(encoding="utf-8"), path.stem)
            tips[path.stem] = file_ops[-1].op_id if file_ops else ""
            ops.extend(file_ops)
    cards: dict[str, Card] = {}
    environments = repo / "environments"
    if environments.is_dir():
        for path in sorted(environments.glob("*.md")):
            cards[path.stem] = parse_card(path.read_text(encoding="utf-8"), path.stem)
    return authority, tips, cards, ops


def build_compiled(repo: Path) -> Compiled:
    authority, tips, cards, ops = load_pieces(repo)
    claims, proposals = compile_ops(ops, authority)
    return Compiled(claims=claims, proposals=proposals, tips=tips, cards=cards, authority=authority)


def _fact_line(op: Op, suffix: str = "") -> str:
    return f"- {op.text} {{id:{op.claim_id}}}{suffix}"


def _conflict_block(result: ClaimResult) -> list[str]:
    lines = [f"- {{id:{result.claim_id}}} 未裁决"]
    for head in result.heads:
        when = head.at or "无日期"
        label = "撤回" if head.kind == "retract" else head.text
        lines.append(f"  - {head.op_id}（{when}）：{label}")
    return lines


def _section_lines(results: list[ClaimResult], *, inline_detail: bool) -> dict[str, list[str]]:
    sections = {name: [] for name in VIEW_ORDER}
    for result in sorted(results, key=lambda item: item.claim_id):
        if result.conflict or result.retracted or not result.heads:
            continue
        head = result.heads[0]
        if head.kind != "set":
            continue
        bucket = sections.setdefault(head.slice, [])
        bucket.append(_fact_line(head))
        if inline_detail and head.detail:
            bucket.extend(f"  {line}" for line in head.detail.splitlines())
    return sections


def render_scope_view(title: str, results: list[ClaimResult], *, inline_detail: bool) -> str:
    sections = _section_lines(results, inline_detail=inline_detail)
    conflicts = [result for result in results if result.conflict]
    conflicts.sort(key=lambda item: item.claim_id)
    lines = [f"# {title}", ""]
    for slice_name in VIEW_ORDER:
        lines.append(f"## {SLICE_TITLE[slice_name]}")
        body = sections.get(slice_name) or []
        lines.extend(body or ["（无）"])
        lines.append("")
    lines.append("## 冲突")
    if conflicts:
        for result in conflicts:
            lines.extend(_conflict_block(result))
    else:
        lines.append("（无）")
    lines.append("")
    return _ensure_nl("\n".join(lines))


def render_views(compiled: Compiled, *, inline_detail: bool = True) -> dict[str, str]:
    shared = [result for (scope, _cid), result in compiled.claims.items() if scope == "shared"]
    rendered = {"shared.md": render_scope_view("共享", shared, inline_detail=inline_detail)}
    names = scenario_names(compiled.authority, compiled.cards, _all_ops(compiled))
    for name in names:
        scope = f"scenario:{name}"
        results = [result for (item_scope, _cid), result in compiled.claims.items() if item_scope == scope]
        rendered[f"scenario-{name}.md"] = render_scope_view(f"场景：{name}", results, inline_detail=inline_detail)
    return rendered


def _all_ops(compiled: Compiled) -> list[Op]:
    ops: list[Op] = []
    for result in compiled.claims.values():
        ops.extend(result.heads)
        ops.extend(result.unapplied)
    ops.extend(compiled.proposals)
    return ops


def render_status(compiled: Compiled) -> str:
    version = compiler_version()
    lines = ["# STATUS", "", f"compiler: topmind-handoff {version}", "", "## compiled_from"]
    if compiled.tips:
        for origin in sorted(compiled.tips):
            tip = compiled.tips[origin] or "-"
            lines.append(f"- {origin}: {tip}")
    else:
        lines.append("（无）")
    fact_count = sum(
        1
        for result in compiled.claims.values()
        if len(result.heads) == 1 and result.heads[0].kind == "set"
    )
    conflict_count = sum(1 for result in compiled.claims.values() if result.conflict)
    lines.extend(
        [
            "",
            "## counts",
            f"- facts: {fact_count}",
            f"- conflicts: {conflict_count}",
            f"- proposals: {len(compiled.proposals)}",
            "",
            "## conflicts",
        ]
    )
    conflicts = [result for result in compiled.claims.values() if result.conflict]
    if conflicts:
        for result in sorted(conflicts, key=lambda item: (item.scope, item.claim_id)):
            heads = ", ".join(head.op_id for head in result.heads)
            lines.append(f"- id: {result.claim_id}")
            lines.append(f"  scope: {result.scope}")
            lines.append(f"  heads: {heads}")
    else:
        lines.append("（无）")
    lines.extend(["", "## proposals"])
    if compiled.proposals:
        for op in sorted(compiled.proposals, key=lambda item: item.op_id):
            lines.append(f"- op_id: {op.op_id}")
            lines.append(f"  id: {op.claim_id}")
            lines.append(f"  scope: {op.scope}")
            lines.append(f"  origin: {op.origin}")
            lines.append(f"  op: {op.kind}")
            lines.append(f"  text: {op.text}")
    else:
        lines.append("（无）")
    lines.extend(["", "## origins"])
    origins = sorted(set(compiled.tips) | set(compiled.cards))
    if origins:
        for origin in origins:
            card = compiled.cards.get(origin)
            lines.append(f"- id: {origin}")
            lines.append(f"  tip: {compiled.tips.get(origin) or '-'}")
            lines.append(f"  refreshed: {card.refreshed if card else ''}")
            lines.append(f"  stale: {'true' if card and card.stale else 'false'}")
    else:
        lines.append("（无）")
    lines.append("")
    return _ensure_nl("\n".join(lines))


def compile_repo(repo: Path) -> Compiled:
    """Regenerate views and STATUS from outboxes. Existing view text is discarded."""
    repo = Path(repo)
    compiled = build_compiled(repo)
    views = repo / "views"
    views.mkdir(parents=True, exist_ok=True)
    rendered = render_views(compiled, inline_detail=True)
    for path in views.glob("scenario-*.md"):
        if path.name not in rendered:
            path.unlink()
    for name, text in rendered.items():
        (views / name).write_text(text, encoding="utf-8")
    (repo / "STATUS.md").write_text(render_status(compiled), encoding="utf-8")
    return compiled


def _status_tips(text: str) -> dict[str, str]:
    tips: dict[str, str] = {}
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## compiled_from"
            continue
        if not in_section:
            continue
        match = re_tip(line)
        if match:
            origin, tip = match
            tips[origin] = "" if tip == "-" else tip
    return tips


def re_tip(line: str) -> tuple[str, str] | None:
    match = re.match(r"^- ([^:]+):\s*(.*)$", line)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def status_is_valid(repo: Path) -> tuple[bool, str]:
    """A status file is valid only when its tips equal the outbox tips."""
    repo = Path(repo)
    status_path = repo / "STATUS.md"
    if not status_path.is_file():
        return False, "STATUS.md 不存在，视图无效，需要重新编译"
    _authority, tips, _cards, _ops = load_pieces(repo)
    recorded = _status_tips(status_path.read_text(encoding="utf-8"))
    if recorded != tips:
        return False, "STATUS 的信箱末尾与 outbox 不一致，视图无效，需要重新编译"
    return True, "STATUS 与信箱末尾一致"


def save_environment_card(repo: Path, actor: str, origin: str, content: str) -> Path:
    """Replace one origin's environment card. Other origins are refused."""
    if actor != origin:
        raise PermissionError(f"{actor} 只能替换自己的环境卡片 {origin}")
    dest = Path(repo) / "environments" / f"{origin}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_ensure_nl(content), encoding="utf-8")
    return dest


def _apply_overrides(shared: str, overrides: dict[str, str]) -> str:
    if not overrides:
        return shared
    lines = []
    for line in shared.splitlines():
        replaced = False
        for claim_id, text in overrides.items():
            marker = "{id:" + claim_id + "}"
            if marker in line and line.startswith("- "):
                lines.append(f"- {text} {marker}")
                replaced = True
                break
        if not replaced:
            lines.append(line)
    return _ensure_nl("\n".join(lines))


def _conflicts_for_origin(compiled: Compiled, origin: str) -> str:
    blocks: list[str] = []
    for result in sorted(compiled.claims.values(), key=lambda item: (item.scope, item.claim_id)):
        if not result.conflict:
            continue
        if any(head.origin == origin for head in result.heads):
            blocks.extend(_conflict_block(result))
    if not blocks:
        return "（无）\n"
    return _ensure_nl("\n".join(blocks))


def _origin_projection(compiled: Compiled, origin: str) -> str:
    """Sets whose scope is this origin. Conflicts stay in the conflict section."""
    scope = f"origin:{origin}"
    results = [result for (item_scope, _cid), result in compiled.claims.items() if item_scope == scope]
    lines: list[str] = []
    for result in sorted(results, key=lambda item: item.claim_id):
        if result.conflict or result.retracted or not result.heads:
            continue
        head = result.heads[0]
        if head.kind != "set":
            continue
        lines.append(_fact_line(head))
        if head.detail:
            lines.extend(f"  {line}" for line in head.detail.splitlines())
    if not lines:
        return ""
    return "## 本环境范围\n\n" + "\n".join(lines) + "\n"


def startup_read(repo: Path, origin: str) -> str:
    """Shared view, this origin's scenario, its card, and conflicts that involve it.

    Card overrides are applied only in this projection. views/shared.md is not rewritten.
    """
    repo = Path(repo)
    compiled = build_compiled(repo)
    shared_path = repo / "views" / "shared.md"
    shared = shared_path.read_text(encoding="utf-8") if shared_path.is_file() else render_views(compiled)["shared.md"]
    card = compiled.cards.get(origin)
    overrides = card.overrides if card else {}
    projected = _apply_overrides(shared, overrides)
    role = card.role if card else ""
    scenario_path = repo / "views" / f"scenario-{role}.md" if role else None
    if scenario_path and scenario_path.is_file():
        scenario = scenario_path.read_text(encoding="utf-8")
    elif role:
        scenario = render_views(compiled).get(f"scenario-{role}.md", "# 场景\n\n（无）\n")
    else:
        scenario = "（无）\n"
    card_text = card.raw if card else "（无）\n"
    origin_text = _origin_projection(compiled, origin).rstrip("\n")
    parts = [
        f"# 开工读取（{origin})",
        "",
        "## 冲突（与本环境有关）",
        _conflicts_for_origin(compiled, origin).rstrip("\n"),
        "",
        "## 共享",
        projected.rstrip("\n"),
        "",
        f"## 场景：{role or '无'}",
        scenario.rstrip("\n"),
        "",
    ]
    if origin_text:
        parts.extend([origin_text, ""])
    parts.extend(["## 环境卡片", card_text.rstrip("\n"), ""])
    return _ensure_nl("\n".join(parts))
