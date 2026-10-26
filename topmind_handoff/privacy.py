"""Local high-confidence privacy checks. Never echo matched values."""

from __future__ import annotations

import re

_CREDENTIALS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bnpm_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}", re.I),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9+/._-]{16,}", re.I),
)
_HOMES = (
    re.compile(r"/(?:home|Users)/([^/\s\"'<>|`]+)"),
    re.compile(r"[A-Za-z]:\\Users\\([^\\/\s\"'<>|]+)", re.I),
)
_PLACEHOLDERS = {"user", "username", "yourname", "example", "runner", "ubuntu", "public", "shared", "zhangsan"}


def assert_private_text(text: str) -> None:
    """Reject obvious credentials and personal home paths before any write.

    This deliberately does not claim to detect every form of PII. Semantic
    privacy review and user confirmation still apply.
    """
    for pattern in _CREDENTIALS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            raise ValueError(f"隐私检查拒绝：第 {line} 行疑似凭据（内容已隐藏）")
    for pattern in _HOMES:
        for match in pattern.finditer(text):
            if match.group(1).lower() not in _PLACEHOLDERS:
                line = text.count("\n", 0, match.start()) + 1
                raise ValueError(f"隐私检查拒绝：第 {line} 行含个人主目录，请泛化为 ~（内容已隐藏）")
