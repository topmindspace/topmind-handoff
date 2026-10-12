"""Render a handoff package and apply a legacy 1.1 import. Same compiler, no network."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from topmind_handoff.compile import compile_repo
from topmind_handoff.model import ROOT, compiler_version, origin_markdown, parse_outbox, safe_origin, scenario_filename

APPENDIX_MARK = "本附录是操作账本，不是新事实。按 op_id 去重重放；不要把这些条目再导入为新的事实或记忆。"
ANCHOR_FIELDS = ("对本智能体的称呼", "称呼", "语言", "时区")


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


def render_package(repo: Path, origin: str) -> str:
    """Compile, then render an offline 1.1 package from the views and this origin's outbox."""
    repo = Path(repo)
    origin = safe_origin(origin)
    compile_repo(repo)
    shared = (repo / "views" / "shared.md").read_text(encoding="utf-8")
    card_path = origin_markdown(repo / "environments", origin)
    card = card_path.read_text(encoding="utf-8") if card_path.is_file() else "（无）\n"
    role = _front(card).get("role", "")
    filename = scenario_filename(role) if role else None
    scenario_path = repo / "views" / filename if filename else None
    if scenario_path is not None and scenario_path.resolve().parent != (repo / "views").resolve():
        scenario_path = None
    scenario = scenario_path.read_text(encoding="utf-8") if scenario_path and scenario_path.is_file() else "（无）\n"
    outbox_path = origin_markdown(repo / "outbox", origin)
    ops_text = outbox_path.read_text(encoding="utf-8") if outbox_path.is_file() else ""
    op_blocks = [op.raw.rstrip("\n") for op in parse_outbox(ops_text, origin)]
    ops_body = "\n\n".join(op_blocks) if op_blocks else "（无）"
    version = compiler_version()
    lines = [
        "---",
        'handoff_version: "1.1"',
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
        "## 视图",
        "",
        shared.rstrip("\n"),
        "",
        scenario.rstrip("\n"),
        "",
        "## 环境卡片",
        "",
        card.rstrip("\n"),
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


def render_legacy_package(claims: list[dict[str, str]], *, mode: str = "migration") -> str:
    """A 1.1 package with no operation appendix. `mode` is recorded and does not change import."""
    grouped: dict[str, list[str]] = {}
    for claim in claims:
        section = claim.get("section") or "5. 事实与记忆（Facts & memories）"
        text = claim["text"]
        claim_id = claim.get("id")
        line = f"- {text}" + (f" {{id:{claim_id}}}" if claim_id else "")
        grouped.setdefault(section, []).append(line)
    version = compiler_version()
    lines = [
        "---",
        'handoff_version: "1.1"',
        "language: zh-CN",
        "scope: private",
        f"mode: {mode}",
        f'generator: "topmind-handoff {version}"',
        "---",
        "",
        receiver_guide(),
        "",
        "# 交接包",
        "",
    ]
    for section, items in grouped.items():
        lines.append(f"## {section}")
        lines.extend(items)
        lines.append("")
    return "\n".join(lines)


def _appendix_ops(package: str, origin: str):
    match = re.search(r"```ops\n(.*?)```", package, re.S)
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


def replay_package(repo: Path, package: str) -> list[str]:
    """Append appendix ops whose op_id is not already in the store, then compile if needed."""
    repo = Path(repo)
    front = _front(package)
    version = front.get("handoff_version", "")
    if version.startswith("2"):
        raise ValueError(f"不支持的交接包大版本 {version}")
    origin = safe_origin(front.get("origin_id") or "unknown")
    dest = origin_markdown(repo / "outbox", origin)
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
    if blocks:
        dest.parent.mkdir(parents=True, exist_ok=True)
        existing = dest.read_text(encoding="utf-8") if dest.is_file() else f"# outbox {origin}\n"
        if not existing.endswith("\n"):
            existing += "\n"
        dest.write_text(existing + "\n".join(blocks) + "\n", encoding="utf-8")
        compile_repo(repo)
    return added


@dataclass
class LegacyPlan:
    additions: dict[str, str] = field(default_factory=dict)
    anchor_conflicts: dict[str, tuple[str, str]] = field(default_factory=dict)
    suggested_deletions: list[str] = field(default_factory=list)
    omitted_local_ids: list[str] = field(default_factory=list)
    mode: str = "migration"


def _claim_items(package: str) -> list[tuple[str | None, str]]:
    items: list[tuple[str | None, str]] = []
    for line in package.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        match = re.search(r"\{id:([^}]+)\}\s*$", body)
        claim_id = match.group(1) if match else None
        if match:
            body = body[: match.start()].strip()
        items.append((claim_id, body))
    return items


def _anchor_of(text: str) -> tuple[str, str] | None:
    for field_name in ANCHOR_FIELDS:
        for separator in ("：", ":"):
            needle = field_name + separator
            if needle in text:
                return field_name, text.split(needle, 1)[1].strip()
    return None


def _is_tombstone(text: str) -> bool:
    lowered = text.lower()
    return "已撤回" in text or "withdrawn" in lowered


def legacy_import_plan(package: str, local: dict) -> LegacyPlan:
    """One import plan for every 1.1 package. `mode` does not select an algorithm."""
    front = _front(package)
    version = front.get("handoff_version", "1.1")
    if version.startswith("2"):
        raise ValueError(f"不支持的交接包大版本 {version}")
    mode = front.get("mode") or "migration"
    local_anchors = dict(local.get("anchors") or {})
    local_claims = dict(local.get("claims") or {})
    plan = LegacyPlan(mode=mode)
    seen: set[str] = set()
    for claim_id, text in _claim_items(package):
        anchor = _anchor_of(text)
        if anchor:
            kind, value = anchor
            current = local_anchors.get(kind, "")
            if current and current != value:
                plan.anchor_conflicts[kind] = (current, value)
            continue
        if claim_id:
            seen.add(claim_id)
        if _is_tombstone(text):
            if claim_id:
                plan.suggested_deletions.append(claim_id)
            continue
        if claim_id and claim_id not in local_claims:
            plan.additions[claim_id] = text
    for claim_id in local_claims:
        if claim_id not in seen:
            plan.omitted_local_ids.append(claim_id)
    plan.suggested_deletions = sorted(set(plan.suggested_deletions))
    plan.omitted_local_ids = sorted(plan.omitted_local_ids)
    return plan


def apply_legacy_plan(plan: LegacyPlan, local: dict, *, confirmed: bool) -> dict:
    """Write only confirmed non-anchor additions. Never delete, never overwrite anchors."""
    result = deepcopy(local)
    result.setdefault("anchors", {})
    result.setdefault("claims", {})
    if not confirmed:
        return result
    for claim_id, text in plan.additions.items():
        result["claims"][claim_id] = text
    return result
