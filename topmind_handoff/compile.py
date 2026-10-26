"""Read a memory directory, compile views, and check status tips."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

from topmind_handoff.model import (
    CARD_STALE_DAYS,
    INDEX_BYTE_BUDGET,
    INDEX_LINE_BUDGET,
    REVIEW_MARK,
    SLICES,
    Card,
    ClaimResult,
    Compiled,
    Op,
    compile_ops,
    compiler_version,
    origin_markdown,
    over_budget,
    parse_authority,
    parse_day,
    review_suffix,
    scenario_filename,
    parse_card,
    parse_outbox,
    protected_claim_ids,
    safe_origin,
    scenario_names,
    slice_title,
    unique_ops,
    view_slice_order,
)
from topmind_handoff.privacy import assert_private_text

VIEW_ORDER = ("identity", "boundaries", "preference", "project", "fact")
_REVIEW_AS_OF = re.compile(r"^review_as_of:\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
_INDEX_FIT = re.compile(r"^index_fit:\s*(organized|full)\s*$", re.M)
_CITE_EDGE = r"[A-Za-z0-9_.-]"


def _ensure_nl(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def load_pieces(repo: Path) -> tuple[dict[str, str], dict[str, str], dict[str, Card], list[Op]]:
    authority_path = repo / "authority.md"
    authority = parse_authority(_read_source(authority_path)) if authority_path.is_file() else {}
    tips: dict[str, str] = {}
    ops: list[Op] = []
    outbox = repo / "outbox"
    if outbox.is_dir():
        for path in sorted(outbox.glob("*.md")):
            file_ops = parse_outbox(_read_source(path), path.stem)
            tips[path.stem] = file_ops[-1].op_id if file_ops else ""
            ops.extend(file_ops)
    cards: dict[str, Card] = {}
    environments = repo / "environments"
    if environments.is_dir():
        for path in sorted(environments.glob("*.md")):
            cards[path.stem] = parse_card(_read_source(path), path.stem)
    return authority, tips, cards, ops


def _read_source(path: Path) -> str:
    if path.resolve().parent != path.parent.resolve():
        raise ValueError("权威输入路径越界，拒绝读取")
    text = path.read_text(encoding="utf-8")
    assert_private_text(text)
    return text


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


def _section_lines(
    results: list[ClaimResult], *, inline_detail: bool, today: date | None = None
) -> dict[str, list[str]]:
    sections = {name: [] for name in VIEW_ORDER}
    for result in sorted(results, key=lambda item: item.claim_id):
        if result.conflict or result.retracted or not result.heads:
            continue
        head = result.heads[0]
        if head.kind != "set":
            continue
        bucket = sections.setdefault(head.slice, [])
        bucket.append(_fact_line(head, review_suffix(head, today)))
        if inline_detail and head.detail:
            bucket.extend(f"  {line}" for line in head.detail.splitlines())
    return sections


def render_scope_view(
    title: str, results: list[ClaimResult], *, inline_detail: bool, today: date | None = None
) -> str:
    sections = _section_lines(results, inline_detail=inline_detail, today=today)
    conflicts = [result for result in results if result.conflict]
    conflicts.sort(key=lambda item: item.claim_id)
    lines = [f"# {title}", ""]
    for slice_name in view_slice_order(sections):
        lines.append(f"## {slice_title(slice_name)}")
        body = sections.get(slice_name) or []
        # An unknown slice with no rows is not a section. Known slices stay, even when empty.
        if slice_name not in VIEW_ORDER and not body:
            continue
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


def render_views(
    compiled: Compiled, *, inline_detail: bool = True, today: date | None = None
) -> dict[str, str]:
    shared = [result for (scope, _cid), result in compiled.claims.items() if scope == "shared"]
    rendered = {"shared.md": render_scope_view("共享", shared, inline_detail=inline_detail, today=today)}
    names = scenario_names(compiled.authority, compiled.cards, _all_ops(compiled))
    for name in names:
        filename = scenario_filename(name)
        if filename is None:
            continue
        scope = f"scenario:{name}"
        results = [result for (item_scope, _cid), result in compiled.claims.items() if item_scope == scope]
        rendered[filename] = render_scope_view(
            f"场景：{name}", results, inline_detail=inline_detail, today=today
        )
    return rendered


def _all_ops(compiled: Compiled) -> list[Op]:
    ops: list[Op] = []
    for result in compiled.claims.values():
        ops.extend(result.heads)
        ops.extend(result.unapplied)
    ops.extend(compiled.proposals)
    return ops


def render_status(compiled: Compiled, today: date | None = None, *, index_fit: str = "full") -> str:
    version = compiler_version()
    lines = [
        "# STATUS",
        "",
        "本文件和 views/ 是本机编译产物，不是权威。权威是 outbox/、authority.md 和 environments/。对不上就丢掉视图，重新编译。",
        "",
        f"compiler: topmind-handoff {version}",
        f"index_fit: {index_fit if index_fit == 'organized' else 'full'}",
        "",
    ]
    if today is not None:
        lines.append(f"review_as_of: {today.isoformat()}")
        lines.append("")
    lines.append("## compiled_from")
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
    unapplied = [op for result in compiled.claims.values() for op in result.unapplied]
    lines.extend(
        [
            "",
            "## counts",
            f"- facts: {fact_count}",
            f"- conflicts: {conflict_count}",
            f"- proposals: {len(compiled.proposals)}",
            f"- unapplied: {len(unapplied)}",
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
    lines.extend(["", "## unapplied"])
    for op in sorted(unapplied, key=lambda item: item.op_id):
        lines.extend([
            f"- op_id: {op.op_id}", f"  id: {op.claim_id}", f"  scope: {op.scope}",
            "  reason: base 或 closes 未满足当前因果链，需要核对依赖或裁决",
        ])
    if not unapplied:
        lines.append("（无）")
    lines.extend(["", "## 待提炼"])
    refine = refinement_lines(
        list(compiled.claims.values()),
        compiled.cards,
        today,
        known_ids=_current_ids(compiled),
    )
    lines.extend(refine or ["（无）"])
    lines.extend(["", "## origins"])
    origins = sorted(set(compiled.tips) | set(compiled.cards))
    if origins:
        for origin in origins:
            card = compiled.cards.get(origin)
            lines.append(f"- id: {origin}")
            lines.append(f"  tip: {compiled.tips.get(origin) or '-'}")
            lines.append(f"  refreshed: {card.refreshed if card else ''}")
            lines.append(f"  stale: {'true' if card and card_is_due(card, today) else 'false'}")
    else:
        lines.append("（无）")
    lines.append("")
    return _ensure_nl("\n".join(lines))


def stored_index_fit(repo: Path) -> str:
    """`organized` after the user has asked for a fitted index. Absent means one line per claim."""
    path = Path(repo) / "STATUS.md"
    if not path.is_file():
        return "full"
    match = _INDEX_FIT.search(path.read_text(encoding="utf-8"))
    if match is None:
        return "full"
    return match.group(1)


def stored_review_today(repo: Path) -> date | None:
    """The explicit day a previous compile or organize used. Absent means unlabeled views."""
    path = Path(repo) / "STATUS.md"
    if not path.is_file():
        return None
    match = _REVIEW_AS_OF.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return parse_day(match.group(1))


def compile_repo(repo: Path, today: date | None = None) -> Compiled:
    """Regenerate views and STATUS from outboxes. Existing view text is discarded.

    Review labels are rendered from `at` and `today`. A later compile with no day
    reuses `review_as_of` so it does not wipe labels. The day never picks a head.
    """
    repo = Path(repo)
    if today is None:
        today = stored_review_today(repo)
    fit = stored_index_fit(repo)
    compiled = build_compiled(repo)
    views = repo / "views"
    views.mkdir(parents=True, exist_ok=True)
    if fit == "organized":
        # Local import: admin imports this module. Fitting keeps a directory the user already asked for.
        from topmind_handoff.admin import write_index_views

        write_index_views(repo, compiled, today, fit=True)
    else:
        rendered = render_views(compiled, inline_detail=False, today=today)
        for path in views.glob("scenario-*.md"):
            if path.name not in rendered:
                path.unlink()
        for name, text in rendered.items():
            (views / name).write_text(text, encoding="utf-8")
    write_compiled_status(repo, compiled, today=today, index_fit=fit)
    # Local import: admin imports this module. Only a stock README this skill wrote is replaced.
    from topmind_handoff.admin import upgrade_stock_readme

    upgrade_stock_readme(repo)
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


def _digest(parts: dict) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    if path.resolve().parent != path.parent.resolve():
        raise ValueError("编译文件路径越界，视图无效，需要重新编译")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_digest(repo: Path) -> str:
    files = [repo / "authority.md"]
    for directory in ("outbox", "environments"):
        files.extend(sorted((repo / directory).glob("*.md")))
    inputs = {path.relative_to(repo).as_posix(): _file_digest(path) if path.is_file() else None for path in files}
    engine = {path.name: _file_digest(path) for path in sorted(Path(__file__).parent.glob("*.py"))}
    return _digest({"inputs": inputs, "engine": engine, "version": compiler_version()})


def _output_digest(repo: Path, status: str) -> str:
    status = re.sub(r"^output_digest:.*\n?", "", status, flags=re.M)
    outputs = {"STATUS.md": hashlib.sha256(status.encode("utf-8")).hexdigest()}
    for directory in ("views", "facts"):
        for path in sorted((repo / directory).glob("*.md")):
            outputs[path.relative_to(repo).as_posix()] = _file_digest(path)
    return _digest(outputs)


def write_compiled_status(repo: Path, compiled: Compiled, today: date | None, *, index_fit: str) -> None:
    """Bind all authoritative inputs, engine and generated files to one compilation."""
    status = render_status(compiled, today=today, index_fit=index_fit)
    status += f"\ninput_digest: {_input_digest(repo)}\n"
    status += f"output_digest: {_output_digest(repo, status)}\n"
    (repo / "STATUS.md").write_text(status, encoding="utf-8")


def status_is_valid(repo: Path) -> tuple[bool, str]:
    """Validate authoritative content, compiler, STATUS and generated files."""
    repo = Path(repo)
    status_path = repo / "STATUS.md"
    if not status_path.is_file():
        return False, "STATUS.md 不存在，视图无效，需要重新编译"
    try:
        _authority, tips, _cards, _ops = load_pieces(repo)
        status = status_path.read_text(encoding="utf-8")
        if _status_tips(status) != tips:
            return False, "STATUS 的信箱末尾与 outbox 不一致，视图无效，需要重新编译"
        inputs = re.findall(r"^input_digest: ([0-9a-f]{64})$", status, re.M)
        outputs = re.findall(r"^output_digest: ([0-9a-f]{64})$", status, re.M)
        if len(inputs) != 1 or len(outputs) != 1:
            return False, "STATUS 缺少完整性校验，视图无效，需要重新编译"
        if inputs[0] != _input_digest(repo) or outputs[0] != _output_digest(repo, status):
            return False, "编译输入或产物内容已变化，视图无效，需要重新编译"
    except (ValueError, OSError) as exc:
        return False, f"视图无效：{exc}"
    return True, "STATUS、权威输入与编译产物内容一致"


def append_outbox(repo: Path, actor: str, origin: str, blocks: list[str]) -> Path:
    """Append to one origin's outbox. A different actor is refused and nothing is written."""
    assert_private_text(actor)
    dest = origin_markdown(Path(repo) / "outbox", origin)
    origin_name = dest.name[: -len(".md")]
    if actor != origin_name:
        raise PermissionError(f"{actor} 只能追加自己的信箱 {origin_name}")
    if not blocks:
        return dest
    existing = dest.read_text(encoding="utf-8") if dest.is_file() else f"# outbox {origin_name}\n"
    assert_private_text(existing + "\n".join(blocks))
    _authority, _tips, _cards, known = load_pieces(Path(repo))
    unique_ops(known + parse_outbox("\n".join(blocks), origin_name))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not existing.endswith("\n"):
        existing += "\n"
    dest.write_text(existing + "\n".join(blocks) + "\n", encoding="utf-8")
    return dest


def save_environment_card(repo: Path, actor: str, origin: str, content: str) -> Path:
    """Replace one origin's environment card. Other origins are refused."""
    assert_private_text(actor)
    dest = origin_markdown(Path(repo) / "environments", origin)
    origin = dest.name[: -len(".md")]
    if actor != origin:
        raise PermissionError(f"{actor} 只能替换自己的环境卡片 {origin}")
    assert_private_text(content)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_ensure_nl(content), encoding="utf-8")
    return dest


_FACT_LINE = re.compile(
    rf"^- (?P<body>.*){{id:(?P<cid>[^}}]+)}}(?P<suffix>\s*{re.escape(REVIEW_MARK)})?\s*$"
)


def _override_line(line: str, overrides: dict[str, str]) -> str | None:
    match = _FACT_LINE.match(line.rstrip())
    if not match or match.group("cid") not in overrides:
        return None
    claim_id = match.group("cid")
    suffix = match.group("suffix") or ""
    return f"- {overrides[claim_id]} {{id:{claim_id}}}{suffix}"


def _is_detail_line(line: str) -> bool:
    return line.startswith("  ") or line.startswith("\t")


def _apply_overrides(shared: str, overrides: dict[str, str]) -> str:
    if not overrides:
        return shared
    source = shared.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(source):
        replacement = _override_line(source[index], overrides)
        if replacement is None:
            kept.append(source[index])
            index += 1
            continue
        kept.append(replacement)
        index += 1
        while index < len(source) and _is_detail_line(source[index]):
            index += 1
    return _ensure_nl("\n".join(kept))


_FACT_POINTER = re.compile(r"见 facts/(?P<name>[A-Za-z0-9_-]+)\.md")


def _path_inside(path: Path, directory: Path) -> bool:
    try:
        return path.resolve().parent == directory.resolve()
    except OSError:
        return False


def _archived_override_lines(facts: Path, name: str, overrides: dict[str, str], seen: set[str]) -> list[str]:
    """Override lines from one facts archive. Other lines, including details, stay out."""
    if not name or name in {".", ".."} or any(mark in name for mark in ("/", "\\", "\x00")):
        return []
    candidate = facts / f"{name}.md"
    if not facts.is_dir() or not _path_inside(candidate, facts) or not candidate.is_file():
        return []
    found: list[str] = []
    for archived in candidate.read_text(encoding="utf-8").splitlines():
        replacement = _override_line(archived, overrides)
        if replacement is None:
            continue
        match = _FACT_LINE.match(replacement.rstrip())
        if match is None or match.group("cid") in seen:
            continue
        seen.add(match.group("cid"))
        found.append(replacement)
    return found


def _project_shared(repo: Path, shared: str, overrides: dict[str, str]) -> str:
    """Apply card overrides to the shared index and to due lines archived behind a pointer."""
    projected = _apply_overrides(shared, overrides)
    if not overrides:
        return projected
    seen: set[str] = set()
    for line in projected.splitlines():
        match = _FACT_LINE.match(line.rstrip())
        if match and match.group("cid") in overrides:
            seen.add(match.group("cid"))
    facts = repo / "facts"
    output: list[str] = []
    for line in projected.splitlines():
        output.append(line)
        pointer = _FACT_POINTER.search(line.rstrip())
        if pointer is None:
            continue
        output.extend(_archived_override_lines(facts, pointer.group("name"), overrides, seen))
    return _ensure_nl("\n".join(output))


def _results_for(compiled: Compiled, scope: str) -> list[ClaimResult]:
    return [result for (item_scope, _cid), result in compiled.claims.items() if item_scope == scope]


def _current_heads(results: list[ClaimResult]) -> list[Op]:
    heads: list[Op] = []
    for result in results:
        if result.conflict or result.retracted or not result.heads:
            continue
        head = result.heads[0]
        if head.kind == "set":
            heads.append(head)
    return heads


def _current_ids(compiled: Compiled) -> set[str]:
    found: set[str] = set()
    for result in compiled.claims.values():
        for head in _current_heads([result]):
            found.add(head.claim_id)
    return found


def _scope_heads(compiled: Compiled, scope: str) -> dict[str, Op]:
    return {head.claim_id: head for head in _current_heads(_results_for(compiled, scope))}


def cites_claim(text: str, claim_id: str) -> bool:
    """True when text names another claim id as a whole token, not as a prefix."""
    if not text or not claim_id or claim_id not in text:
        return False
    pattern = re.compile(
        r"(?<!" + _CITE_EDGE + r")" + re.escape(claim_id) + r"(?!" + _CITE_EDGE + r")"
    )
    return pattern.search(text) is not None


def card_is_due(card: Card, today: date | None) -> bool:
    if card.stale:
        return True
    if today is None or not card.refreshed:
        return False
    written = parse_day(card.refreshed)
    if written is None:
        return False
    return (today - written).days >= CARD_STALE_DAYS


def refinement_lines(
    results: list[ClaimResult],
    cards: dict[str, Card],
    today: date | None,
    *,
    known_ids: set[str],
) -> list[str]:
    """List review work. Does not retract, rewrite, or touch outboxes.

    Lines are sentences, not `- ` claims, so a package import does not store them as facts.
    """
    heads = _current_heads(results)
    heads.sort(key=lambda op: (op.scope, op.claim_id, op.op_id))
    lines: list[str] = []
    for head in heads:
        if head.slice not in SLICES:
            lines.append(f"维度 `{head.slice}` 单独成节，没有并进事实。id: {head.claim_id}")
    for head in heads:
        blob = f"{head.text}\n{head.detail}"
        for other in sorted(known_ids):
            if other == head.claim_id:
                continue
            if cites_claim(blob, other):
                lines.append(f"引用 `{head.claim_id}` 提到当前说法 `{other}`。不撤回，不改写。")
    for origin in sorted(cards):
        if card_is_due(cards[origin], today):
            lines.append(f"环境卡片 `{origin}` 未刷新。")
    return lines


def _label_line(line: str, heads: dict[str, Op], today: date | None) -> str:
    if today is None:
        return line
    match = _FACT_LINE.match(line.rstrip())
    if not match:
        return line
    head = heads.get(match.group("cid"))
    if head is None:
        return line
    suffix = review_suffix(head, today)
    return f"- {match.group('body').rstrip()} {{id:{match.group('cid')}}}{suffix}"


def _label_text(text: str, heads: dict[str, Op], today: date | None) -> str:
    if today is None:
        return text
    return _ensure_nl("\n".join(_label_line(line, heads, today) for line in text.splitlines()))


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


def _origin_projection(compiled: Compiled, origin: str, today: date | None = None) -> str:
    """Sets whose scope is this origin, each slice under its own heading.

    Conflicts stay in the conflict section. Origin text is not part of the shared view.
    """
    scope = f"origin:{origin}"
    results = _results_for(compiled, scope)
    sections = _section_lines(results, inline_detail=False, today=today)
    filled = [name for name in view_slice_order(sections) if sections.get(name)]
    if not filled:
        return ""
    lines = ["## 本环境范围", ""]
    for name in filled:
        lines.append(f"### {slice_title(name)}")
        lines.extend(sections[name])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _without_claim_details(text: str) -> str:
    """Drop indented detail under a claim line. Conflict sub-lines are not claim lines."""
    source = text.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(source):
        kept.append(source[index])
        if _FACT_LINE.match(source[index].rstrip()):
            index += 1
            while index < len(source) and _is_detail_line(source[index]):
                index += 1
            continue
        index += 1
    return _ensure_nl("\n".join(kept))


def organize_advice(shared: str, scenario: str) -> str:
    """Prompt text when an index is past the startup budget. It does not write or retract."""
    notes: list[str] = []
    limit = f"{INDEX_LINE_BUDGET} 行或 {INDEX_BYTE_BUDGET // 1024}KB"
    if over_budget(shared):
        notes.append(f"共享索引超过预算（{limit}）。")
    if over_budget(scenario):
        notes.append(f"本场景索引超过预算（{limit}）。")
    if not notes:
        return ""
    lines = ["## 建议整理", ""]
    for note in notes:
        lines.append(f"- {note}做完这一轮再问要不要整理云端记忆。不自动运行 --organize。")
    lines.append("")
    return _ensure_nl("\n".join(lines))


def projection_body(repo: Path, origin: str, today: date | None = None) -> str:
    """One origin projection shared by startup and the offline package.

    Reads views when they are inside the repo. Does not write files.
    """
    repo = Path(repo)
    origin = safe_origin(origin)
    use_views = (repo / "STATUS.md").is_file()
    if use_views:
        valid, message = status_is_valid(repo)
        if not valid:
            raise ValueError(message)
    compiled = build_compiled(repo)
    if today is None:
        today = stored_review_today(repo)
    views = repo / "views"
    rendered = render_views(compiled, inline_detail=False, today=today)
    shared_path = views / "shared.md"
    if use_views and shared_path.is_file() and _path_inside(shared_path, views):
        shared = shared_path.read_text(encoding="utf-8")
    else:
        shared = rendered["shared.md"]
    card = compiled.cards.get(origin)
    _authority, _tips, _cards, source_ops = load_pieces(repo)
    protected = protected_claim_ids(source_ops)
    overrides = {cid: text for cid, text in (card.overrides.items() if card else ()) if cid not in protected}
    projected = _without_claim_details(
        _label_text(
            _project_shared(repo, shared, overrides),
            _scope_heads(compiled, "shared"),
            today,
        )
    )
    role = card.role if card else ""
    filename = scenario_filename(role) if role else None
    scenario_path = views / filename if filename else None
    if scenario_path is not None and not _path_inside(scenario_path, views):
        scenario_path = None
    if use_views and scenario_path is not None and scenario_path.is_file():
        scenario = scenario_path.read_text(encoding="utf-8")
    elif filename:
        scenario = rendered.get(filename, "# 场景\n\n（无）\n")
    else:
        scenario = "（无）\n"
    scenario = _without_claim_details(
        _label_text(scenario, _scope_heads(compiled, f"scenario:{role}") if role else {}, today)
    )
    card_text = card.raw if card else "（无）\n"
    origin_text = _origin_projection(compiled, origin, today=today).rstrip("\n")
    visible: list[ClaimResult] = list(_results_for(compiled, "shared"))
    if role:
        visible.extend(_results_for(compiled, f"scenario:{role}"))
    visible.extend(_results_for(compiled, f"origin:{origin}"))
    refine = refinement_lines(visible, compiled.cards, today, known_ids=_current_ids(compiled))
    parts = [
        f"复核基准：{today.isoformat() if today else '未指定'}",
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
    parts.extend(
        [
            "## 环境卡片",
            card_text.rstrip("\n"),
            "",
            "## 待提炼",
            "\n".join(refine) if refine else "（无）",
            "",
        ]
    )
    pending = [op for result in visible for op in result.unapplied]
    if pending:
        parts.extend(["## 未应用", ""])
        parts.extend(f"- {op.op_id}：base 或 closes 未满足当前因果链" for op in pending)
        parts.append("")
    advice = organize_advice(projected, scenario)
    if advice:
        parts.extend([advice.rstrip("\n"), ""])
    return _ensure_nl("\n".join(parts))


def _also_scenario(repo: Path, origin: str, also: str, today: date | None) -> str:
    """One extra scenario view. The card role is not changed."""
    if scenario_filename(also) is None:
        raise ValueError("场景名必须是单个路径段")
    compiled = build_compiled(repo)
    card = compiled.cards.get(origin)
    role = card.role if card else ""
    if also == role:
        return ""
    if today is None:
        today = stored_review_today(repo)
    filename = scenario_filename(also)
    views = repo / "views"
    path = views / filename if filename else None
    rendered = render_views(compiled, inline_detail=False, today=today)
    if (repo / "STATUS.md").is_file() and path is not None and path.is_file() and _path_inside(path, views):
        text = path.read_text(encoding="utf-8")
    elif filename:
        text = rendered.get(filename, f"# 场景：{also}\n\n（无）\n")
    else:
        text = "（无）\n"
    text = _without_claim_details(
        _label_text(text, _scope_heads(compiled, f"scenario:{also}"), today)
    )
    return _ensure_nl(f"## 另带场景：{also}\n\n{text.rstrip()}")


def startup_read(repo: Path, origin: str, today: date | None = None, also: str | None = None) -> str:
    """Shared view, this origin's scenario, its card, and conflicts that involve it.

    Card overrides are applied only in this projection. views/shared.md is not rewritten.
    Due labels, the 待提炼 list, and an organize prompt are printed. Nothing is retracted.
    """
    repo = Path(repo)
    origin = safe_origin(origin)
    body = projection_body(repo, origin, today=today).rstrip("\n")
    if also:
        extra = _also_scenario(repo, origin, also, today).rstrip("\n")
        if extra:
            body = f"{body}\n\n{extra}"
    return _ensure_nl(f"# 开工读取（{origin})\n\n{body}")


def open_claim(repo: Path, claim_id: str) -> str:
    """Print one claim from the outbox. Does not write files or follow facts/ pointers."""
    claim_id = claim_id.strip()
    if not claim_id or any(mark in claim_id for mark in ("/", "\\", "\x00", "\n", " ")):
        raise ValueError("id 无效")
    repo = Path(repo)
    compiled = build_compiled(repo)
    today = stored_review_today(repo)
    blocks: list[str] = [f"# 打开 {claim_id}", ""]
    found = False
    for scope, cid in sorted(compiled.claims):
        if cid != claim_id:
            continue
        found = True
        result = compiled.claims[(scope, cid)]
        blocks.append(f"## {scope}")
        if result.conflict:
            blocks.append("未裁决")
            for head in result.heads:
                blocks.extend(_open_head(head, today))
        elif result.retracted:
            blocks.append("已撤回")
        elif result.heads:
            blocks.extend(_open_head(result.heads[0], today))
        blocks.append("")
    proposals = [op for op in compiled.proposals if op.claim_id == claim_id]
    if proposals:
        found = True
        blocks.append("## 提议")
        for op in proposals:
            blocks.append(f"- op_id: {op.op_id}")
            blocks.append(f"  scope: {op.scope}")
            blocks.append(f"  text: {op.text}")
            if op.detail:
                blocks.append("  detail: |")
                blocks.extend(f"    {line}" for line in op.detail.splitlines())
        blocks.append("")
    if not found:
        return _ensure_nl(f"没有这条当前说法：{claim_id}")
    return _ensure_nl("\n".join(blocks))


def _open_head(head: Op, today: date | None) -> list[str]:
    lines = [
        f"- slice: {head.slice}",
        f"  at: {head.at}",
        f"  text: {head.text}{review_suffix(head, today)}",
    ]
    if head.detail:
        lines.append("  detail: |")
        lines.extend(f"    {line}" for line in head.detail.splitlines())
    return lines
