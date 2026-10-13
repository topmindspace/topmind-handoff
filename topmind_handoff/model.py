"""Parse and compile causal memory operations. No clocks, no network."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLICES = ("identity", "boundaries", "preference", "project", "fact")
SLICE_TITLE = {
    "identity": "身份",
    "boundaries": "边界",
    "preference": "偏好",
    "project": "项目",
    "fact": "事实",
}
REVIEW_DAYS = {
    "identity": 180,
    "boundaries": 180,
    "preference": 90,
    "project": 30,
    "fact": 30,
}
CARD_STALE_DAYS = 90
INDEX_LINE_BUDGET = 200
INDEX_BYTE_BUDGET = 25 * 1024


def parse_day(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def review_suffix(op: Op, today: date | None) -> str:
    """Label a current head from its own `at`. The date never picks a chain head."""
    if today is None:
        return ""
    limit = REVIEW_DAYS.get(op.slice)
    written = parse_day(op.at)
    if limit is None or written is None:
        return ""
    if (today - written).days >= limit:
        return " （未复核）"
    return ""


def slice_title(name: str) -> str:
    """Known slices keep their Chinese headings. Anything else stays its own section."""
    return SLICE_TITLE.get(name, f"维度：{name}")


def view_slice_order(present: Iterable[str]) -> list[str]:
    extras = sorted({name for name in present if name not in SLICES})
    return list(SLICES) + extras


def compiler_version() -> str:
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    return str(pkg["version"])


def safe_origin(origin: str) -> str:
    """One path segment. Reject absolute paths and any name that can leave the repo."""
    name = origin.strip()
    if not name or name in {".", ".."} or any(mark in name for mark in ("/", "\\", "\x00")):
        raise ValueError("origin_id 必须是单个路径段")
    if Path(name).name != name:
        raise ValueError("origin_id 必须是单个路径段")
    return name


def scenario_filename(name: str) -> str | None:
    """`scenario-<name>.md` when the name is one path segment. Otherwise None."""
    try:
        safe_origin(name)
    except ValueError:
        return None
    return f"scenario-{name}.md"


def origin_markdown(directory: Path, origin: str) -> Path:
    """Path of `<directory>/<origin>.md` after the single-segment check."""
    name = safe_origin(origin)
    directory = Path(directory)
    candidate = directory / f"{name}.md"
    if candidate.resolve().parent != directory.resolve():
        raise ValueError("origin_id 必须是单个路径段")
    return candidate


@dataclass(frozen=True)
class Op:
    op_id: str
    kind: str
    claim_id: str
    scope: str
    slice: str
    base: str | None
    closes: tuple[str, ...]
    at: str
    text: str
    detail: str
    origin: str
    raw: str


@dataclass
class Card:
    origin: str
    role: str
    refreshed: str
    overrides: dict[str, str]
    raw: str
    stale: bool = False


@dataclass
class ClaimResult:
    scope: str
    claim_id: str
    heads: list[Op] = field(default_factory=list)
    unapplied: list[Op] = field(default_factory=list)

    @property
    def conflict(self) -> bool:
        return len(self.heads) > 1

    @property
    def retracted(self) -> bool:
        return len(self.heads) == 1 and self.heads[0].kind == "retract"


@dataclass
class Compiled:
    claims: dict[tuple[str, str], ClaimResult]
    proposals: list[Op]
    tips: dict[str, str]
    cards: dict[str, Card]
    authority: dict[str, str]


def _parse_closes(value: str) -> tuple[str, ...]:
    text = value.strip()
    if not text or text == "[]":
        return ()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    parts = [part.strip() for part in text.split(",")]
    return tuple(part for part in parts if part)


def parse_outbox(text: str, origin: str) -> list[Op]:
    """Parse one origin's append-only outbox. Origin is the filename, never a field."""
    ops: list[Op] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^- op_id:\s*(\S+)\s*$", line)
        if not match:
            index += 1
            continue
        raw_lines = [line]
        fields: dict[str, str] = {"op_id": match.group(1)}
        index += 1
        while index < len(lines) and not re.match(r"^- op_id:\s*\S+\s*$", lines[index]):
            current = lines[index]
            raw_lines.append(current)
            detail = re.match(r"^  detail:\s*\|\s*$", current)
            if detail:
                block: list[str] = []
                index += 1
                while index < len(lines) and not re.match(r"^- op_id:\s*\S+\s*$", lines[index]):
                    nxt = lines[index]
                    if re.match(r"^  [A-Za-z0-9_]+:\s*", nxt):
                        break
                    raw_lines.append(nxt)
                    block.append(nxt[4:] if nxt.startswith("    ") else nxt.strip())
                    index += 1
                fields["detail"] = "\n".join(block).strip("\n")
                continue
            field_match = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", current)
            if field_match:
                fields[field_match.group(1)] = field_match.group(2).strip()
            index += 1
        claim_id = fields.get("id", "").strip()
        op_id = fields["op_id"]
        if not claim_id or not op_id:
            continue
        base_raw = fields.get("base", "none").strip() or "none"
        kind = fields.get("op", "set").strip() or "set"
        scope = fields.get("scope", "shared").strip() or "shared"
        # Missing slice stays fact. An unknown value, including `environment`, is kept.
        # Coercing it would hide the row under 事实 and a typo must not abort the ledger.
        slice_name = fields.get("slice", "fact").strip() or "fact"
        ops.append(
            Op(
                op_id=op_id,
                kind=kind,
                claim_id=claim_id,
                scope=scope,
                slice=slice_name,
                base=None if base_raw == "none" else base_raw,
                closes=_parse_closes(fields.get("closes", "")),
                at=fields.get("at", "").strip(),
                text=fields.get("text", "").strip(),
                detail=fields.get("detail", "").strip(),
                origin=origin,
                raw="\n".join(raw_lines).rstrip() + "\n",
            )
        )
    return ops


def parse_authority(text: str) -> dict[str, str]:
    owners: dict[str, str] = {}
    scope = ""
    for line in text.splitlines():
        scope_match = re.match(r"^- scope:\s*(\S+)\s*$", line)
        if scope_match:
            scope = scope_match.group(1)
            continue
        owner_match = re.match(r"^  owner:\s*(\S+)\s*$", line)
        if owner_match and scope:
            owners[scope] = owner_match.group(1)
            scope = ""
    return owners


def parse_card(text: str, fallback_origin: str) -> Card:
    front, _body = _frontmatter(text)
    overrides = {
        key[len("override.") :]: value
        for key, value in front.items()
        if key.startswith("override.") and value
    }
    return Card(
        origin=front.get("origin") or fallback_origin,
        role=front.get("role", ""),
        refreshed=front.get("refreshed", ""),
        overrides=overrides,
        raw=text if text.endswith("\n") else text + "\n",
        stale=front.get("stale", "") == "true",
    )


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    front: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        front[key.strip()] = value.strip()
    return front, parts[2]


def scenario_names(authority: dict[str, str], cards: dict[str, Card], ops: list[Op]) -> list[str]:
    names: set[str] = set()
    for key in authority:
        if key.startswith("scenario."):
            names.add(key.split(".", 1)[1])
    for card in cards.values():
        if card.role:
            names.add(card.role)
    for op in ops:
        if op.scope.startswith("scenario:"):
            names.add(op.scope.split(":", 1)[1])
    return sorted(names)


def _authority_scope(op: Op) -> str:
    if op.slice in ("identity", "boundaries"):
        return f"shared.{op.slice}"
    if op.scope.startswith("scenario:"):
        return "scenario." + op.scope.split(":", 1)[1]
    return op.scope


def is_proposal(op: Op, authority: dict[str, str]) -> bool:
    """Return True when this op must not enter a view chain."""
    if op.kind == "propose":
        return True
    if op.kind not in ("set", "retract"):
        return True
    if op.slice in ("identity", "boundaries") and op.origin != "human":
        return True
    if op.scope.startswith("origin:"):
        target = op.scope.split(":", 1)[1]
        return op.origin != target
    if op.scope.startswith("scenario:"):
        owner = authority.get(_authority_scope(op))
        if owner and op.origin not in (owner, "human"):
            return True
    return False


def compile_ops(ops: list[Op], authority: dict[str, str]) -> tuple[dict[tuple[str, str], ClaimResult], list[Op]]:
    """Compile a list of operations. Duplicate op_ids collapse to the first."""
    seen: set[str] = set()
    unique: list[Op] = []
    for op in ops:
        if op.op_id in seen:
            continue
        seen.add(op.op_id)
        unique.append(op)

    proposals = [op for op in unique if is_proposal(op, authority)]
    applicable = [op for op in unique if not is_proposal(op, authority)]
    # A demoted op stays out of the view, but a later allowed set may use its op_id as base.
    anchors: dict[tuple[str, str], set[str]] = {}
    for op in proposals:
        anchors.setdefault((op.scope, op.claim_id), set()).add(op.op_id)
    grouped: dict[tuple[str, str], list[Op]] = {}
    for op in applicable:
        grouped.setdefault((op.scope, op.claim_id), []).append(op)

    claims: dict[tuple[str, str], ClaimResult] = {}
    for key, group in grouped.items():
        claims[key] = _compile_claim(key[0], key[1], group, anchors.get(key, set()))
    return claims, proposals


def _compile_claim(scope: str, claim_id: str, ops: list[Op], anchors: set[str] | None = None) -> ClaimResult:
    regular = [op for op in ops if not op.closes]
    merges = [op for op in ops if op.closes]
    linked: dict[str, Op] = {}
    pending = sorted(regular, key=lambda op: op.op_id)
    closed: set[str] = set()
    anchored = set(anchors or ())

    def link_ready() -> None:
        nonlocal pending
        progressed = True
        while progressed:
            progressed = False
            still: list[Op] = []
            for op in pending:
                if op.base is None or op.base in linked or op.base in anchored:
                    linked[op.op_id] = op
                    progressed = True
                else:
                    still.append(op)
            pending = still

    def leaves_now() -> list[Op]:
        cited = {op.base for op in linked.values() if op.base} | closed
        leaves = [op for op in linked.values() if op.op_id not in cited]
        leaves.sort(key=lambda op: op.op_id)
        return leaves

    link_ready()
    remaining = sorted(merges, key=lambda op: op.op_id)
    unapplied = list(pending)
    while remaining:
        leaf_ids = {op.op_id for op in leaves_now()}
        matches = [op for op in remaining if leaf_ids and set(op.closes) == leaf_ids]
        if len(matches) == 1:
            chosen = matches[0]
            remaining = [op for op in remaining if op.op_id != chosen.op_id]
            linked[chosen.op_id] = chosen
            closed.update(chosen.closes)
            link_ready()
            continue
        if len(matches) > 1:
            remaining = [op for op in remaining if op not in matches]
            for chosen in matches:
                linked[chosen.op_id] = chosen
                closed.update(chosen.closes)
            link_ready()
            continue
        unapplied.extend(remaining)
        break

    # Children linked after a close are no longer pending.
    unapplied = [op for op in unapplied if op.op_id not in linked]
    return ClaimResult(scope=scope, claim_id=claim_id, heads=leaves_now(), unapplied=unapplied)
