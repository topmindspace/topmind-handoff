"""Init an empty memory repo and run a user-triggered organize pass."""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

from topmind_handoff.compile import VIEW_ORDER as SLICE_ORDER
from topmind_handoff.compile import build_compiled, compile_repo, render_status
from topmind_handoff.model import (
    INDEX_BYTE_BUDGET,
    INDEX_LINE_BUDGET,
    ClaimResult,
    Compiled,
    Op,
    origin_markdown,
    parse_authority,
    parse_day,
    review_suffix,
    safe_origin,
    scenario_filename,
    scenario_names,
    slice_title,
    view_slice_order,
)

_SAFE_NAME = re.compile(r"[A-Za-z0-9_-]+")


class PublicRepoRefused(RuntimeError):
    """Raised when init is asked to write a public memory repo."""


def _nl(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


AUTHORITY_INTRO = [
    "# 写入权",
    "",
    "身份和边界的主人固定是 human，只接受 outbox/human.md 里的操作。",
    "每个环境只许在自己的 outbox 末尾追加，只许整文件替换自己的 environments 卡片。",
    "场景主人写在下面。别人写该场景只记成提议。",
    "",
]


def memory_readme() -> str:
    """Text an initialized repo uses to explain itself. Two inits write the same bytes."""
    return _nl(
        "\n".join(
            [
                "# 云端记忆",
                "",
                "这是一份私有记忆仓库。本机的 topmind-handoff 编译它。仓库里没有 CI，也没有 Release。",
                "凭据只用已经配好的 git 或 gh。不写密码、API key、token、证件号、银行卡号、精确住址、他人隐私、记账明细。聊天记录也不写入。",
                "",
                "## 写入哪一类",
                "",
                "- 画像锚点是称呼、对本智能体的称呼、语言、时区。它们是身份，主人是 human，只接受 `outbox/human.md`。",
                "- 边界的主人也是 human。",
                "- 跨工具都适用的偏好写入 `scope: shared`。",
                "- 只在某个场景里成立的习惯用 `scope: scenario:<场景>`，不写入 shared。",
                "- 必须跟着这台机器走的步骤和未做完的事用 `scope: origin:<origin_id>`。技能版本和连接器写在这台的环境卡片上，不写成共享事实。",
                "- 已有主题要改，沿用原来的 id，`base` 填当前链头，不另起一条 id。",
                "- 不写密码、API key、token，不写聊天记录，不改别人的信箱。",
                "",
                "## 各部分",
                "",
                "- `outbox/<origin_id>.md`：这个环境的操作账本。只许该环境在文件末尾追加。不改别人的信箱，不改已有行。",
                "- `environments/<origin_id>.md`：这个环境的卡片。只许该环境整文件替换。",
                "- `authority.md`：谁可以写进视图。身份和边界的主人是 human，只接受 `outbox/human.md`。",
                "- `facts/`：整理时从索引收走的长说明。不是另一套权威。",
                "- `views/shared.md` 和 `views/scenario-<场景>.md`：本机编译产物，可以丢掉后重新编译。不是指令。",
                "- `STATUS.md`：同一次编译的校对。信箱末尾对不上，视图就无效。不是指令。",
                "",
                "权威是 `outbox/`、`authority.md` 和 `environments/`。`views/` 和 `STATUS.md` 是可以丢掉的编译产物，不是指令。Git 冲突时丢掉这两边的视图，保留全部信箱，在本机重新编译。",
                "",
            ]
        )
    )


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
    origin = safe_origin(origin)
    role = safe_origin(role)
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"{path} 不是空目录")
    path.mkdir(parents=True, exist_ok=True)
    refreshed = today or date.today().isoformat()
    (path / "README.md").write_text(memory_readme(), encoding="utf-8")
    (path / "authority.md").write_text(
        _nl(
            "\n".join(
                AUTHORITY_INTRO
                + [
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
    (path / "facts").mkdir()
    (path / "facts" / "README.md").write_text(
        _nl("# 长说明\n\n整理时才把索引收进这里。这些文件不是另一套权威。权威仍是信箱。\n"),
        encoding="utf-8",
    )
    outbox = path / "outbox"
    outbox.mkdir()
    origin_markdown(outbox, origin).write_text(_nl(f"# outbox {origin}\n"), encoding="utf-8")
    environments = path / "environments"
    environments.mkdir()
    origin_markdown(environments, origin).write_text(
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
    compile_repo(path)
    _git_commit(path, "初始化云端记忆")
    return path


def set_scenario_owner(repo: Path, scenario: str, origin: str) -> None:
    """Give one origin direct writes on a scenario. Identity and boundaries stay with human."""
    if scenario_filename(scenario) is None:
        raise ValueError("场景名必须是单个路径段")
    origin = safe_origin(origin)
    path = Path(repo) / "authority.md"
    current = parse_authority(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current["shared.identity"] = "human"
    current["shared.boundaries"] = "human"
    current[f"scenario.{scenario}"] = origin
    order = ["shared.identity", "shared.boundaries"]
    rest = sorted(key for key in current if key not in order)
    lines = list(AUTHORITY_INTRO)
    for key in order + rest:
        lines.append(f"- scope: {key}")
        lines.append(f"  owner: {current[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    compile_repo(path.parent)


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


def _review_suffix(op: Op, today: date) -> str:
    return review_suffix(op, today)


def _archive_path(facts_root: Path, fact_prefix: str, slice_name: str) -> Path | None:
    """Stay inside facts/. A slice such as `../evil` is kept inline and does not abort."""
    if _SAFE_NAME.fullmatch(fact_prefix) is None or _SAFE_NAME.fullmatch(slice_name) is None:
        return None
    facts_root.mkdir(parents=True, exist_ok=True)
    candidate = facts_root / f"{fact_prefix}-{slice_name}.md"
    try:
        if candidate.resolve().parent != facts_root.resolve():
            return None
    except OSError:
        return None
    return candidate


def _write_slice_archive(
    facts_root: Path,
    fact_prefix: str,
    slice_name: str,
    lines: list[str],
    rich: list[str],
) -> None:
    """Keep every collapsed index line, including facts that have no detail."""
    dest = _archive_path(facts_root, fact_prefix, slice_name)
    if dest is None:
        return
    rich_lines = set(rich)
    body = list(rich)
    body.extend(line for line in lines if line not in rich_lines)
    if not body:
        body = list(lines)
    dest.write_text(_nl("# " + slice_name + "\n\n" + "\n".join(body)), encoding="utf-8")


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
        for slice_name in view_slice_order(section_map):
            body = section_map.get(slice_name) or []
            if slice_name not in SLICE_ORDER and not body:
                continue
            lines.append(f"## {slice_title(slice_name)}")
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
        dest = _archive_path(facts_root, fact_prefix, slice_name)
        if dest is None:
            continue
        dest.write_text(_nl("# " + slice_name + "\n\n" + "\n".join(block)), encoding="utf-8")

    text = render(sections)
    # Collapse the largest slices until the index fits the startup budget.
    collapsible = [name for name in ("fact", "preference", "project", "identity", "boundaries")]
    collapsible.extend(
        name
        for name in sections
        if name not in SLICE_ORDER and _SAFE_NAME.fullmatch(name) and name not in collapsible
    )
    while (text.count("\n") > INDEX_LINE_BUDGET or len(text.encode("utf-8")) > INDEX_BYTE_BUDGET) and any(
        len(sections.get(name) or []) > 1 for name in collapsible
    ):
        name = max(collapsible, key=lambda item: len(sections.get(item) or []))
        count = len(sections.get(name) or [])
        if count <= 1:
            break
        _write_slice_archive(facts_root, fact_prefix, name, sections.get(name) or [], details.get(name) or [])
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
            return parse_day(line.split(":", 1)[1].strip())
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
    keep: set[str] = set()
    for name in names:
        filename = scenario_filename(name)
        if filename is None:
            continue
        keep.add(filename)
        scope = f"scenario:{name}"
        text = _compact_scope(f"场景：{name}", _results_for(compiled, scope), today, facts_root, f"scenario-{name}")
        (views / filename).write_text(text, encoding="utf-8")
    for path in views.glob("scenario-*.md"):
        if path.name not in keep:
            path.unlink()
    environments = repo / "environments"
    if environments.is_dir():
        for path in sorted(environments.glob("*.md")):
            _mark_stale(path, today)
    # Cards may now be stale; rebuild status from the same outbox tips.
    compiled = build_compiled(repo)
    (repo / "STATUS.md").write_text(render_status(compiled, today=today), encoding="utf-8")
    after = {path.name: path.read_bytes() for path in sorted(outbox.glob("*.md"))} if outbox.is_dir() else {}
    if before != after:
        raise RuntimeError("整理改写了信箱")
    return compiled
