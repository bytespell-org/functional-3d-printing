#!/usr/bin/env python3
"""Reject local, private, generated, or unsafe content in a reusable skill."""

from __future__ import annotations

import argparse
import json
import re
import tarfile
from pathlib import Path, PurePosixPath


SKILL_NAME = "functional-3d-printing"
SELF = "scripts/validate_portability.py"
FORBIDDEN_PATH_PARTS = {
    ".git",
    "." + "mat" + "riarch",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "node_modules",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key", ".p12"}
FORBIDDEN_TEXT = (
    ("private-platform-name", re.compile(r"\b" + "mat" + "riarch" + r"\b", re.IGNORECASE)),
    ("owner-project-name", re.compile(r"\b" + "ha" + "uck" + r"(?:-home)?\b", re.IGNORECASE)),
    ("managed-session-id", re.compile(r"\bsession-[0-9a-f-]{16,}\b", re.IGNORECASE)),
    ("linux-home-path", re.compile(r"/(?:home|Users)/[^/\s'\"]+/")),
    ("windows-home-path", re.compile(r"[A-Za-z]:\\Users\\[^\\\s'\"]+\\")),
    ("private-ipv4", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)


def portable_path(name: str, *, archive: bool) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        findings.append({"code": "unsafe-path", "path": name})
    parts = path.parts[1:] if archive and path.parts and path.parts[0] == SKILL_NAME else path.parts
    if archive and (not path.parts or path.parts[0] != SKILL_NAME):
        findings.append({"code": "wrong-archive-root", "path": name})
    for part in parts:
        if part in FORBIDDEN_PATH_PARTS:
            findings.append({"code": "generated-or-private-path", "path": name})
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        findings.append({"code": "private-or-generated-file", "path": name})
    return findings


def scan_text(name: str, data: bytes) -> list[dict[str, str]]:
    if name.endswith(SELF) or b"\x00" in data:
        return []
    text = data.decode("utf-8", errors="ignore")
    findings: list[dict[str, str]] = []
    for code, pattern in FORBIDDEN_TEXT:
        match = pattern.search(text)
        if match:
            findings.append({"code": code, "path": name, "match": match.group(0)[:120]})
    return findings


def scan_directory(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if PurePosixPath(relative).parts[:1] == (".git",):
            # The skill can be the root of its own Git repository. Repository
            # metadata is not part of the distributable skill payload.
            continue
        findings.extend(portable_path(relative, archive=False))
        if path.is_symlink():
            findings.append({"code": "symlink-not-portable", "path": relative})
        elif path.is_file():
            findings.extend(scan_text(relative, path.read_bytes()))
    return findings


def scan_archive(path: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            findings.extend(portable_path(member.name, archive=True))
            if member.issym() or member.islnk():
                findings.append({"code": "archive-symlink-not-portable", "path": member.name})
            elif member.isfile():
                stream = archive.extractfile(member)
                if stream is not None:
                    relative = PurePosixPath(member.name)
                    name = PurePosixPath(*relative.parts[1:]).as_posix()
                    findings.extend(scan_text(name, stream.read()))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    root = args.skill.resolve()
    findings = scan_directory(root)
    if args.archive is not None:
        findings.extend(scan_archive(args.archive.resolve()))
    result = {
        "ok": not findings,
        "skill": str(root),
        "archive": str(args.archive.resolve()) if args.archive else None,
        "findings": findings,
    }
    print(json.dumps(result, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
