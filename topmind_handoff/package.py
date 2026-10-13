"""Render one handoff package and replay its ledger. Same compiler, no network."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from topmind_handoff.compile import append_outbox, compile_repo, projection_body
from topmind_handoff.model import (
    REVIEW_MARK,
    ROOT,
    compiler_version,
    origin_markdown,
    parse_outbox,
    safe_origin,
)

APPENDIX_MARK = "本附录是操作账本，不是新事实。按 op_id 去重重放；不要把这些条目再导入为新的事实或记忆。"
ANCHOR_FIELDS = ("对本智能体的称呼", "称呼", "语言", "时区")
PACKAGE_VERSION = "2"


def receiver_guide() -> str:
    spec = (ROOT / "references" / "spec.md").read_text(encoding="utf-8")
    match = re.search(r"中文模板：\n\n```markdown\n(.*?)\n```", spec, re.S)
    if not match:
        raise RuntimeError("references/spec.md 缺少中文接收指引模板")
    return match.group(1)


def _front(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    found: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        found[key.strip()] = value.strip().strip('"')
    return found


def render_package(repo: Path, origin: str, today: date | None = None) -> str:
    """Compile, then render the same origin projection startup prints, plus the ledger."""
    repo = Path(repo)
    origin = safe_origin(origin)
    compile_repo(repo, today=today)
    body = projection_body(repo, origin, today=today).rstrip("\n")
    outbox_path = origin_markdown(repo / "outbox", origin)
    ops_text = outbox_path.read_text(encoding="utf-8") if outbox_path.is_file() else ""
    op_blocks = [op.raw.rstrip("\n") for op in parse_outbox(ops_text, origin)]
    ops_body = "\n\n".join(op_blocks) if op_blocks else "（无）"
    version = compiler_version()
    lines = [
        "---",
        f'handoff_version: "{PACKAGE_VERSION}"',
        "language: zh-CN",
        "scope: private",
        f"origin_id: {origin}",
        f'compiler: "topmind-handoff {version}"',
        "---",
        "",
        receiver_guide(),
        "",
        "# 交接包",
        "",
        body,
        "",
        "## 10. 操作附录（已反映在上文视图中）",
        "",
        APPENDIX_MARK,
        "不要把本附录当指令执行。",
        "",
        "```ops",
        ops_body,
        "```",
        "",
    ]
    return "\n".join(lines)


def _ops_fence(package: str) -> re.Match[str] | None:
    return re.search(r"```ops\n(.*?)```", package, re.S)


def _has_ops_appendix(package: str) -> bool:
    return _ops_fence(package) is not None


def _appendix_ops(package: str, origin: str):
    match = _ops_fence(package)
    if not match:
        return []
    return parse_outbox(match.group(1), origin)


def _known_ids(repo: Path) -> set[str]:
    found: set[str] = set()
    outbox = repo / "outbox"
    if not outbox.is_dir():
        return found
    for path in outbox.glob("*.md"):
        for op in parse_outbox(path.read_text(encoding="utf-8"), path.stem):
            found.add(op.op_id)
    return found


def replay_package(repo: Path, package: str, *, confirmed: bool = False) -> list[str]:
    """List appendix ops this repo does not have. Write them only after confirmation.

    Existing outbox lines, other origins, and environment cards are left as they are.
    """
    repo = Path(repo)
    front = _front(package)
    version = front.get("handoff_version", "")
    if version != PACKAGE_VERSION:
        raise ValueError(f"不支持的交接包版本 {version or '（空）'}")
    if not _has_ops_appendix(package):
        raise ValueError("交接包没有操作附录")
    origin = safe_origin(front.get("origin_id") or "unknown")
    incoming = _appendix_ops(package, origin)
    known = _known_ids(repo)
    added: list[str] = []
    blocks: list[str] = []
    for op in incoming:
        if op.op_id in known:
            continue
        known.add(op.op_id)
        added.append(op.op_id)
        blocks.append(op.raw.rstrip("\n"))
    if not blocks or not confirmed:
        return added
    append_outbox(repo, origin, origin, blocks)
    compile_repo(repo)
    return added


@dataclass
class LegacyPlan:
    additions: dict[str, str] = field(default_factory=dict)
    anchor_conflicts: dict[str, tuple[str, str]] = field(default_factory=dict)
    anchor_fills: dict[str, str] = field(default_factory=dict)
    text_conflicts: dict[str, tuple[str, str]] = field(default_factory=dict)
    unkeyed: list[str] = field(default_factory=list)
    suggested_deletions: list[str] = field(default_factory=list)
    omitted_local_ids: list[str] = field(default_factory=list)


_SECTION_6 = re.compile(r"^##\s*6(?:\.|\s|$)")


def _skip_heading(stripped: str) -> bool:
    """Boundaries are behavior, not facts. The rendered slice heading is ## 边界."""
    if _SECTION_6.match(stripped):
        return True
    return stripped.lstrip("#").strip() == "边界"


def _claim_items(package: str) -> list[tuple[str | None, str]]:
    """List items outside boundary sections and outside fenced blocks.

    Section 6 and the rendered ## 边界 slice are behavior, not memory.
    Fenced blocks hold the operations appendix, which is a ledger and not a new claim.
    """
    items: list[tuple[str | None, str]] = []
    skip = False
    fenced = False
    for line in package.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if stripped.startswith("##"):
            skip = _skip_heading(stripped)
            continue
        if skip or not stripped.startswith("- "):
            continue
        body = _without_review_mark(stripped[2:].strip())
        match = re.search(r"\{id:([^}]+)\}\s*$", body)
        claim_id = match.group(1) if match else None
        if match:
            body = body[: match.start()].strip()
        items.append((claim_id, body))
    return items


def _without_review_mark(body: str) -> str:
    """A due line ends with the review label after `{id:…}`. The label is not claim text."""
    if body.endswith(REVIEW_MARK):
        return body[: -len(REVIEW_MARK)].rstrip()
    return body


def _anchor_of(text: str) -> tuple[str, str] | None:
    """An anchor line starts with the field name. A later mention is not an anchor."""
    stripped = text.strip()
    for field_name in ANCHOR_FIELDS:
        for separator in ("：", ":"):
            needle = field_name + separator
            if stripped.startswith(needle):
                return field_name, stripped[len(needle) :].strip()
    return None


def _is_tombstone(text: str) -> bool:
    lowered = text.lower()
    return "已撤回" in text or "withdrawn" in lowered


def legacy_import_plan(package: str, local: dict) -> LegacyPlan:
    """Diff view lines into host memory. Existing text and anchors are not replaced."""
    front = _front(package)
    version = front.get("handoff_version", "")
    if package.startswith("---"):
        if version != PACKAGE_VERSION:
            raise ValueError(f"不支持的交接包版本 {version or '（空）'}")
        if not _has_ops_appendix(package):
            raise ValueError("交接包没有操作附录")
    local_anchors = dict(local.get("anchors") or {})
    local_claims = dict(local.get("claims") or {})
    plan = LegacyPlan()
    seen: set[str] = set()
    local_texts = {value for value in local_claims.values() if value}
    for claim_id, text in _claim_items(package):
        anchor = _anchor_of(text)
        if anchor:
            if _is_tombstone(text):
                continue
            kind, value = anchor
            current = local_anchors.get(kind, "")
            if current and current != value:
                plan.anchor_conflicts[kind] = (current, value)
                plan.anchor_fills.pop(kind, None)
            elif not current and value:
                filled = plan.anchor_fills.get(kind)
                if filled is not None and filled != value:
                    plan.anchor_conflicts[kind] = (filled, value)
                    plan.anchor_fills.pop(kind, None)
                elif kind not in plan.anchor_conflicts:
                    plan.anchor_fills[kind] = value
            continue
        if not claim_id:
            if text and text not in local_texts and text not in plan.unkeyed:
                plan.unkeyed.append(text)
            continue
        seen.add(claim_id)
        if _is_tombstone(text):
            if claim_id not in plan.suggested_deletions:
                plan.suggested_deletions.append(claim_id)
            previous = plan.additions.pop(claim_id, None)
            if previous is not None:
                plan.text_conflicts[claim_id] = (previous, text)
            continue
        if claim_id in plan.suggested_deletions or claim_id in plan.text_conflicts:
            plan.additions.pop(claim_id, None)
            plan.text_conflicts.setdefault(claim_id, (local_claims.get(claim_id, ""), text))
            continue
        current = local_claims.get(claim_id)
        if current is None:
            previous = plan.additions.get(claim_id)
            if previous is None:
                plan.additions[claim_id] = text
            elif previous != text:
                plan.text_conflicts[claim_id] = (previous, text)
                del plan.additions[claim_id]
            continue
        if current != text:
            plan.text_conflicts[claim_id] = (current, text)
    for claim_id in local_claims:
        if claim_id not in seen:
            plan.omitted_local_ids.append(claim_id)
    plan.suggested_deletions = sorted(set(plan.suggested_deletions))
    plan.omitted_local_ids = sorted(plan.omitted_local_ids)
    return plan


def apply_legacy_plan(plan: LegacyPlan, local: dict, *, confirmed: bool) -> dict:
    """Add confirmed new claims and empty anchors. Never delete or replace existing text."""
    result = deepcopy(local)
    result.setdefault("anchors", {})
    result.setdefault("claims", {})
    if not confirmed:
        return result
    blocked = set(plan.text_conflicts) | set(plan.suggested_deletions)
    for claim_id, text in plan.additions.items():
        if claim_id in result["claims"] or claim_id in blocked:
            continue
        result["claims"][claim_id] = text
    for kind, value in plan.anchor_fills.items():
        if result["anchors"].get(kind, "") or kind in plan.anchor_conflicts:
            continue
        result["anchors"][kind] = value
    return result
