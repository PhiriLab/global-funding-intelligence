#!/usr/bin/env python3
"""Static scanner for externally sourced agent assets.

This scanner deliberately does not execute repository content. It flags high-risk
instruction patterns and likely embedded secrets so a reviewer can inspect them
before allow-listing an external skill, prompt, hook, MCP config, or agent file.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".ps1",
}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}

PATTERNS = {
    "instruction_override": re.compile(
        r"(?i)\b(ignore|disregard|override|forget)\b.{0,50}\b(previous|prior|system|developer|instructions?|rules?)\b"
    ),
    "secret_exfiltration": re.compile(
        r"(?i)\b(reveal|print|show|send|upload|exfiltrate|dump)\b.{0,60}\b(secret|token|api[_ -]?key|password|credential|cookie|authorization)\b"
    ),
    "safeguard_bypass": re.compile(
        r"(?i)\b(disable|bypass|turn off|remove)\b.{0,50}\b(safety|security|guardrail|validation|scanner|protection|permission)\b"
    ),
    "permission_escalation": re.compile(
        r"(?i)\b(grant|elevate|escalate|request)\b.{0,50}\b(admin|root|sudo|write access|permission|privilege)\b"
    ),
    "destructive_shell": re.compile(
        r"(?i)(rm\s+-rf\s+[/~]|mkfs\.|:\(\)\s*\{\s*:\|:\s*&\s*\}|shutdown\s+-h|del\s+/s\s+/q\s+[a-z]:\\)"
    ),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic_api_key": re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"
    ),
}

SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\b\s*[:=]\s*['\"]?)([^'\"\s,;]{8,})"
)
BEARER_TOKEN = re.compile(r"(?i)(\bauthorization\s*:\s*bearer\s+)(\S+)")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    excerpt: str


def redact_sensitive_values(text: str) -> str:
    text = SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", text)
    return BEARER_TOKEN.sub(r"\1[REDACTED]", text)


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"AGENTS.md", "CLAUDE.md"}:
            yield path


def scan_text(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERNS.items():
            if pattern.search(line):
                excerpt = redact_sensitive_values(line.strip())
                if len(excerpt) > 180:
                    excerpt = excerpt[:177] + "..."
                findings.append(Finding(path=path, line=lineno, rule=rule, excerpt=excerpt))
    return findings


def scan_path(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings.extend(scan_text(path, text))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Static scan for risky agent instructions and likely secrets")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit 2 when findings are present",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    findings = scan_path(root)

    if not findings:
        print("agent-asset scan: no high-risk patterns detected")
        return 0

    print(f"agent-asset scan: {len(findings)} finding(s) require review")
    for finding in findings:
        try:
            relative = finding.path.relative_to(root)
        except ValueError:
            relative = finding.path
        print(f"{relative}:{finding.line}: {finding.rule}: {finding.excerpt}")

    return 2 if args.fail_on_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
