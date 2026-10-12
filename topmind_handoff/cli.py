"""Command line for the local memory compiler. No network."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from topmind_handoff.admin import PublicRepoRefused, init_memory_repo, organize_repo, set_scenario_owner
from topmind_handoff.compile import compile_repo, startup_read, status_is_valid
from topmind_handoff.package import render_package

USAGE = """\
用法：
  python3 scripts/compile_memory.py <记忆目录>
  python3 scripts/compile_memory.py --check <记忆目录>
  python3 scripts/compile_memory.py --init <目录> --private --origin <origin_id> [--role 场景] [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --init <目录> --public --origin <origin_id>
  python3 scripts/compile_memory.py --organize <记忆目录> [--today YYYY-MM-DD]
  python3 scripts/compile_memory.py --render <记忆目录> --origin <origin_id> [--out 文件]
  python3 scripts/compile_memory.py --own <记忆目录> --scenario <场景> --origin <origin_id>
  python3 scripts/compile_memory.py --startup <记忆目录> --origin <origin_id>
"""


def _day(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 2
    if argv[0] == "--check":
        ok, message = status_is_valid(Path(argv[1]))
        print(message)
        return 0 if ok else 1
    if argv[0] == "--init":
        return _init(argv[1:])
    if argv[0] == "--organize":
        return _organize(argv[1:])
    if argv[0] == "--render":
        return _render(argv[1:])
    if argv[0] == "--own":
        return _own(argv[1:])
    if argv[0] == "--startup":
        return _startup(argv[1:])
    if argv[0].startswith("--"):
        print(USAGE)
        return 2
    compile_repo(Path(argv[0]))
    print(f"compiled {argv[0]}")
    return 0


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


def _organize(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    today = _day(args.today) if args.today else None
    organize_repo(Path(args.path), today)
    print(f"organized {args.path}")
    return 0


def _render(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        text = render_package(Path(args.path), args.origin)
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
    args = parser.parse_args(argv)
    try:
        print(startup_read(Path(args.path), args.origin), end="")
    except ValueError as exc:
        print(str(exc))
        return 1
    return 0


