"""Command line for the local memory compiler. No network."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from topmind_handoff.admin import PublicRepoRefused, init_memory_repo, organize_repo, set_scenario_owner
from topmind_handoff.compile import (
    compile_repo,
    open_claim,
    record_retract,
    record_resolve,
    record_set,
    record_work,
    startup_read,
    status_is_valid,
)
from topmind_handoff.package import render_package, replay_package

USAGE = """\
用法：
  python3 scripts/compile_memory.py <记忆目录> [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --check <记忆目录>
  python3 scripts/compile_memory.py --init <目录> --private --origin <origin_id> [--role 场景] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --init <目录> --public --origin <origin_id>
  python3 scripts/compile_memory.py --set <记忆目录> --origin <origin_id> --id <claim_id> --text <正文> [--scope 范围] [--slice 维度] [--base op_id] [--detail 长说明] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --retract <记忆目录> --origin <origin_id> --id <claim_id> [--scope 范围] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --resolve <记忆目录> --origin <origin_id> --id <claim_id> --text <正文> [--scope 范围] [--slice 维度] [--detail 长说明] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --work <记忆目录> --origin <origin_id> [--text 正文] [--topic 专项] [--local] [--done] [--detail 长说明] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --replay <记忆目录> --file <交接包> [--confirm]
  python3 scripts/compile_memory.py --organize <记忆目录> [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --open <记忆目录> --id <claim_id>
  python3 scripts/compile_memory.py --render <记忆目录> --origin <origin_id> [--out 文件] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --own <记忆目录> --scenario <场景> --origin <origin_id>
  python3 scripts/compile_memory.py --startup <记忆目录> --origin <origin_id> [--also <场景>] [--today YYYY-MM-DD]
"""


def _day(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"日期格式无效（应为 YYYY-MM-DD）：{value}") from exc


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 2
    if argv[0] == "--check":
        if len(argv) != 2:
            print(USAGE)
            return 2
        ok, message = status_is_valid(Path(argv[1]))
        print(message)
        return 0 if ok else 1
    if argv[0] == "--init":
        return _init(argv[1:])
    if argv[0] == "--set":
        return _set(argv[1:])
    if argv[0] == "--retract":
        return _retract(argv[1:])
    if argv[0] == "--resolve":
        return _resolve(argv[1:])
    if argv[0] == "--work":
        return _work(argv[1:])
    if argv[0] == "--replay":
        return _replay(argv[1:])
    if argv[0] == "--organize":
        return _organize(argv[1:])
    if argv[0] == "--open":
        return _open(argv[1:])
    if argv[0] == "--render":
        return _render(argv[1:])
    if argv[0] == "--own":
        return _own(argv[1:])
    if argv[0] == "--startup":
        return _startup(argv[1:])
    if argv[0].startswith("--"):
        print(USAGE)
        return 2
    return _compile(argv)


def _init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--role", default="general")
    parser.add_argument("--today")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--private", action="store_true")
    group.add_argument("--public", action="store_true")
    args = parser.parse_args(argv)
    try:
        init_memory_repo(
            Path(args.path),
            private=not args.public,
            origin=args.origin,
            role=args.role,
            today=args.today,
        )
    except (PublicRepoRefused, ValueError) as exc:
        print(str(exc))
        return 1
    print(f"initialized {args.path}")
    return 0


def _compile(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        compile_repo(Path(args.path), today)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"compiled {args.path}")
    return 0


def _organize(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        organize_repo(Path(args.path), today)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"organized {args.path}")
    return 0


def _open(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    try:
        print(open_claim(Path(args.path), args.id), end="")
    except ValueError as exc:
        print(str(exc))
        return 1
    return 0


def _render(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--out")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        text = render_package(Path(args.path), args.origin, today=today)
    except ValueError as exc:
        print(str(exc))
        return 1
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


def _own(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args(argv)
    try:
        set_scenario_owner(Path(args.path), args.scenario, args.origin)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"{args.origin} owns scenario.{args.scenario}")
    return 0


def _startup(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--also")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        print(startup_read(Path(args.path), args.origin, today=today, also=args.also), end="")
    except ValueError as exc:
        print(str(exc))
        return 1
    return 0


def _set(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--id", required=True, dest="claim_id")
    parser.add_argument("--text", required=True)
    parser.add_argument("--scope", default="shared")
    parser.add_argument("--slice", dest="slice_name")
    parser.add_argument("--base")
    parser.add_argument("--detail", default="")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        op_id = record_set(
            Path(args.path),
            origin=args.origin,
            claim_id=args.claim_id,
            text=args.text,
            scope=args.scope,
            slice_name=args.slice_name,
            base=args.base,
            detail=args.detail,
            today=today,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"set {op_id} ({args.scope} {args.claim_id})")
    return 0


def _retract(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--id", required=True, dest="claim_id")
    parser.add_argument("--scope", default="shared")
    parser.add_argument("--text", default="已撤回")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        op_id = record_retract(
            Path(args.path),
            origin=args.origin,
            claim_id=args.claim_id,
            scope=args.scope,
            text=args.text,
            today=today,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"retracted {op_id} ({args.scope} {args.claim_id})")
    return 0


def _resolve(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--id", required=True, dest="claim_id")
    parser.add_argument("--text", required=True)
    parser.add_argument("--scope", default="shared")
    parser.add_argument("--slice", dest="slice_name")
    parser.add_argument("--detail", default="")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        op_id = record_resolve(
            Path(args.path),
            origin=args.origin,
            claim_id=args.claim_id,
            text=args.text,
            scope=args.scope,
            slice_name=args.slice_name,
            detail=args.detail,
            today=today,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"resolved {op_id} ({args.scope} {args.claim_id})")
    return 0


def _work(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--text", default="")
    parser.add_argument("--topic")
    parser.add_argument("--scope")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--done", action="store_true")
    parser.add_argument("--detail", default="")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    try:
        today = _day(args.today) if args.today else None
        op_id = record_work(
            Path(args.path),
            origin=args.origin,
            text=args.text,
            topic=args.topic,
            scope=args.scope,
            local=args.local,
            done=args.done,
            detail=args.detail,
            today=today,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    action = "done" if args.done else "work"
    print(f"{action} {op_id}")
    return 0


def _replay(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--file", required=True, dest="pkg_file")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    try:
        pkg_text = Path(args.pkg_file).read_text(encoding="utf-8")
        added = replay_package(Path(args.path), pkg_text, confirmed=args.confirm)
    except (ValueError, OSError) as exc:
        print(str(exc))
        return 1
    mode = "replayed" if args.confirm else "preview"
    print(f"{mode}: {', '.join(added) if added else 'none'}")
    return 0


