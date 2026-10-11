#!/usr/bin/env python3
"""topmind-handoff 仓库检查（CI 用，只用 Python 标准库；scripts/ 不进 npm 包）。

    python3 scripts/check_repo.py

1. 版本一致：package.json、SKILL.md metadata.version、README「当前技能版本」、
   assets/handoff-template.md 与 references/spec.md 示例里的 generator、CHANGELOG 最近版本
2. 接收指引同步：references/spec.md 的中文模板逐字出现在 assets/handoff-template.md、assets/handoff-example.md
3. 引用存在：SKILL.md、references/、assets/、README.md 里的 Markdown 相对链接和 `references/…` `assets/…` 路径
4. 云端清理规则只写一份：除 references/export.md「云端推送与清理」、随包分发的接收指引模板
   和 assets/ 里的包模板外，SKILL.md、README、references 不得再写「删掉更旧 … generated_at」这类规则
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


CLOUD_RULE_RE = re.compile(r'删[^。]{0,40}旧|旧[^。]{0,40}删')


def cloud_rule_errors() -> list[str]:
    """assets/ 是随包分发的包内容（模板与示例），和接收指引一样不算技能文档，不查。"""
    errs = []
    for f in DOCS:
        rel = f.relative_to(ROOT).as_posix()
        if rel == 'references/export.md' or rel.startswith('assets/'):
            continue
        for no, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if line.startswith('>'):
                continue  # 随包分发的接收指引模板
            if 'generated_at' in line and CLOUD_RULE_RE.search(line):
                errs.append(f'{rel}:{no}: 云端清理规则应只写在 references/export.md「云端推送与清理」，这里改成指针')
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
    print('PASS: 版本一致、接收指引同步、引用存在、云端清理规则只有一份')
    return 0


if __name__ == '__main__':
    sys.exit(main())
