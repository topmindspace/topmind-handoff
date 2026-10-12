#!/usr/bin/env python3
"""topmind-handoff 仓库检查（CI 用，只用 Python 标准库；scripts/ 不进 npm 包）。

    python3 scripts/check_repo.py

1. 版本一致：package.json、SKILL.md metadata.version、README「当前技能版本」、
   assets/handoff-template.md 与 references/spec.md 示例里的 generator、CHANGELOG 最近版本
2. 接收指引同步：references/spec.md 的中文模板逐字出现在 assets/handoff-template.md、assets/handoff-example.md
3. 引用存在：SKILL.md、references/、assets/、README.md 里的 Markdown 相对链接和 `references/…` `assets/…` 路径
4. 快照选举和删除旧包的说法只允许出现在 references/compile.md。
   其他技能文档和 evals 再写 generated_at 选举或旧文件夹清理，就算失败。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / 'SKILL.md', ROOT / 'README.md', *sorted((ROOT / 'references').glob('*.md')),
        *sorted((ROOT / 'assets').glob('*.md'))]
PATH_RE = re.compile(r'`((?:references|assets)/[\w./-]+\.md)`')
LINK_RE = re.compile(r'\]\(([^)\s]+)\)')


def versions() -> dict[str, str | None]:
    def grab(path: str, pattern: str) -> str | None:
        m = re.search(pattern, (ROOT / path).read_text(encoding='utf-8'), re.M)
        return m.group(1) if m else None
    return {
        'package.json': json.loads((ROOT / 'package.json').read_text(encoding='utf-8')).get('version'),
        'SKILL.md metadata.version': grab('SKILL.md', r'^\s+version:\s*"?([\d.]+)"?\s*$'),
        'README.md 当前技能版本': grab('README.md', r'当前技能版本 `([\d.]+)`'),
        'assets/handoff-template.md generator': grab('assets/handoff-template.md', r'topmind-handoff ([\d.]+)"'),
        'references/spec.md generator 示例': grab('references/spec.md', r'^generator: ".*topmind-handoff ([\d.]+)"'),
        'CHANGELOG.md': grab('CHANGELOG.md', r'^##\s+\[?v?(\d+\.\d+\.\d+)'),
    }


def guide_errors() -> list[str]:
    spec = (ROOT / 'references' / 'spec.md').read_text(encoding='utf-8')
    m = re.search(r'中文模板：\n\n```markdown\n(.*?)\n```', spec, re.S)
    if not m:
        return ['references/spec.md 找不到中文接收指引模板']
    return [f'{f} 的接收指引与 references/spec.md 中文模板不一致'
            for f in ('assets/handoff-template.md', 'assets/handoff-example.md')
            if m.group(1) not in (ROOT / f).read_text(encoding='utf-8')]


def ref_errors() -> list[str]:
    errs = []
    for f in DOCS:
        rel = f.relative_to(ROOT).as_posix()
        for no, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            for target in PATH_RE.findall(line):
                if not (ROOT / target).exists():
                    errs.append(f'{rel}:{no}: 引用不存在：{target}')
            for target in LINK_RE.findall(line):
                if re.match(r'^(https?:|mailto:|#)', target):
                    continue
                path = target.split('#', 1)[0]
                if path and not (f.parent / path).exists():
                    errs.append(f'{rel}:{no}: 相对链接不存在：{target}')
    return errs


RULE_HOME = 'references/compile.md'
ELECTION_RE = re.compile(r'generated_at.{0,80}(最新|选举|当前事实)|(最新|选举|当前事实).{0,80}generated_at')
DELETE_RE = re.compile(r'旧文件夹|删掉该来源|删除旧包|只留该来源')


def cloud_rule_errors() -> list[str]:
    """快照选举和旧包清理只允许写在编译规则这一处。"""
    errs = []
    files = list(DOCS) + [ROOT / 'evals' / 'evals.json']
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel == RULE_HOME:
            continue
        for no, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if ELECTION_RE.search(line) or DELETE_RE.search(line):
                errs.append(f'{rel}:{no}: 快照选举或旧包清理只能写在 {RULE_HOME}')
    return errs


def main() -> int:
    errs: list[str] = []
    v = versions()
    for k, val in v.items():
        print(f'  {k}: {val}')
    if None in v.values() or len(set(v.values())) != 1:
        errs.append('版本号不一致或缺失')
    errs += guide_errors() + ref_errors() + cloud_rule_errors()
    if errs:
        print(f'FAIL: {len(errs)} 处')
        for e in errs:
            print(f'  ✗ {e}')
        return 1
    print('PASS: 版本一致、接收指引同步、引用存在、快照选举只在编译规则一处')
    return 0


if __name__ == '__main__':
    sys.exit(main())
