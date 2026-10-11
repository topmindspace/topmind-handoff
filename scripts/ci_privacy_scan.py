#!/usr/bin/env python3
"""隐私与密钥扫描：仓库文件里不得出现密钥形状的字符串、个人主目录路径、个人邮箱。

与 topmind-research 的 ci_privacy_scan.py 同一套规则，只用 Python 标准库。
命中内容打码输出，不在 CI 日志里复现原文。本机额外的屏蔽词放 scripts/.privacy-deny.local（已在 .gitignore）。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_EXTS = {".md", ".py", ".json", ".yml", ".yaml", ".sh", ".txt", ""}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

NIX_HOME = re.compile(r"/(?:home|Users)/([^/\s\"'<>|`]{1,64})")
WIN_HOME = re.compile(r"[A-Za-z]:\\Users\\([^\\/\s\"'<>|]{1,64})", re.I)
# zhangsan：references 里教「路径用户名泛化为 ~」时用的虚构示例
SAFE_HOME = {"user", "username", "yourname", "example", "runner", "ubuntu", "public", "shared", "zhangsan"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
EMAIL_OK = ("example.com", "example.org", "users.noreply.github.com", "noreply.github.com")
SECRETS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"), "API key 形状"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"), "GitHub token 形状"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "GitHub PAT 形状"),
    (re.compile(r"\bnpm_[A-Za-z0-9]{20,}"), "npm token 形状"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "Google API key 形状"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS key 形状"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}"), "Bearer token 形状"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "私钥块"),
    (re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9+/._\-]{16,}"), "密钥赋值"),
)
FORBIDDEN_TRACKED = (
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"\.(pem|key|p12|pfx)$", re.I),
    re.compile(r"(^|/)\.topmind/"),
    re.compile(r"(^|/)__pycache__/"),
)


def redact(value: str) -> str:
    value = value.strip()
    return "***" if len(value) <= 6 else f"{value[:2]}***{value[-1]}(len={len(value)})"


def deny_terms() -> set[str]:
    path = ROOT / "scripts" / ".privacy-deny.local"
    if not path.is_file():
        return set()
    return {l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def scan_text(rel: str, text: str, extra: set[str]) -> list[str]:
    hits: list[tuple[int, str, str]] = []
    for pat in (NIX_HOME, WIN_HOME):
        for m in pat.finditer(text):
            if m.group(1).lower() not in SAFE_HOME:
                hits.append((m.start(), "个人主目录路径", redact(m.group(1))))
    for m in EMAIL.finditer(text):
        if not m.group(0).lower().endswith(EMAIL_OK):
            hits.append((m.start(), "邮箱", redact(m.group(0))))
    for pat, label in SECRETS:
        for m in pat.finditer(text):
            hits.append((m.start(), label, redact(m.group(0))))
    for term in extra:
        pos = text.find(term)
        while pos >= 0:
            hits.append((pos, "本机屏蔽词", redact(term)))
            pos = text.find(term, pos + len(term))
    return [f"{rel}:{text.count(chr(10), 0, p) + 1}: {label}: {v}" for p, label, v in sorted(hits)]


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=False)
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def self_check() -> list[str]:
    """用运行时拼出的样例确认规则有效，源码里不放连续的真实形状字符串。"""
    samples = (
        ("/" + "home/" + "someone1/x", "个人主目录路径"),
        ("leak@" + "corp-internal.invalid", "邮箱"),
        ("sk-" + "abc123def456ghi789", "API key 形状"),
        ("ghp_" + "a" * 22, "GitHub token 形状"),
    )
    return [f"self-check 未命中：{label}" for s, label in samples if not any(label in h for h in scan_text("self", s, set()))]


def main() -> int:
    extra = deny_terms()
    errors: list[str] = []
    checked = 0
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if not p.is_file() or any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.name.startswith(".privacy-deny") or p.suffix.lower() not in SCAN_EXTS:
            continue
        checked += 1
        errors.extend(scan_text(rel.as_posix(), p.read_text(encoding="utf-8", errors="replace"), extra))
    for rel in tracked_files():
        if any(pat.search(rel) for pat in FORBIDDEN_TRACKED):
            errors.append(f"不应纳入 git 的文件：{rel}")
    errors.extend(self_check())
    print(f"privacy scan: {checked} 个文件")
    if errors:
        print(f"FAIL: {len(errors)} 处")
        for e in errors[:50]:
            print(" ", e)
        return 1
    print("PASS: 未发现密钥、个人路径或个人邮箱")
    return 0


if __name__ == "__main__":
    sys.exit(main())
