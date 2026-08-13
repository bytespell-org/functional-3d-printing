#!/usr/bin/env python3
"""Create and atomically update the observable functional-CAD progress sidecar."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


SCHEMA_VERSION = 1
DEFAULT_STEPS = (
    ("requirements", "Requirements and known dimensions"),
    ("proposal", "CAD proposal and assumptions"),
    ("visual-review", "Interactive visual review"),
    ("small-test", "Small physical test"),
    ("final-validation", "Final validation and delivery"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "design"


def empty_sidecar(design_id: str, title: str) -> dict[str, Any]:
    timestamp = now()
    return {
        "schema_version": SCHEMA_VERSION,
        "design_id": design_id,
        "title": title,
        "status": "active",
        "phase": "requirements",
        "summary": "Collecting requirements and known dimensions.",
        "updated_at": timestamp,
        "answers": [],
        "steps": [
            {
                "id": step_id,
                "title": step_title,
                "status": "in-progress" if index == 0 else "pending",
                "summary": "",
                "evidence": [],
                "updated_at": timestamp,
            }
            for index, (step_id, step_title) in enumerate(DEFAULT_STEPS)
        ],
        "learnings": [],
        "review_comments": [],
    }


def read_sidecar(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Progress sidecar does not exist: {path}. Run init first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("review_comments", [])
    validate(data)
    return data


def validate(data: object) -> None:
    if not isinstance(data, dict):
        raise ValueError("Progress sidecar must be a JSON object.")
    required = {"schema_version", "design_id", "title", "status", "phase", "summary", "updated_at", "answers", "steps", "learnings", "review_comments"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Progress sidecar is missing: {', '.join(sorted(missing))}.")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {data['schema_version']!r}.")
    if data["status"] not in {"active", "blocked", "ready-for-review", "complete"}:
        raise ValueError(f"Invalid design status: {data['status']!r}.")
    if not all(isinstance(data[key], list) for key in ("answers", "steps", "learnings", "review_comments")):
        raise ValueError("answers, steps, learnings, and review_comments must be arrays.")
    for collection in ("answers", "steps", "learnings", "review_comments"):
        identifiers = [item.get("id") for item in data[collection] if isinstance(item, dict)]
        if len(identifiers) != len(data[collection]) or any(not value for value in identifiers):
            raise ValueError(f"Every {collection} entry must be an object with an id.")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError(f"Duplicate id in {collection}.")
    for comment in data["review_comments"]:
        if comment.get("status") not in {"open", "acknowledged", "resolved"}:
            raise ValueError(f"Invalid review comment status: {comment.get('status')!r}.")
        if comment.get("author") not in {"user", "agent"}:
            raise ValueError(f"Invalid review comment author: {comment.get('author')!r}.")
        if not isinstance(comment.get("position_mm"), list) or len(comment["position_mm"]) != 3:
            raise ValueError("Every review comment requires a three-value position_mm array.")
        if not isinstance(comment.get("replies"), list):
            raise ValueError("Every review comment requires a replies array.")


@contextmanager
def sidecar_lock(path: Path):
    """Serialize script and browser writes without changing the JSON contract."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path.with_suffix(path.suffix + ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    validate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def upsert(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    for index, existing in enumerate(items):
        if existing["id"] == item["id"]:
            items[index] = item
            return
    items.append(item)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init", help="Create a new sidecar with the standard workflow.")
    initialize.add_argument("sidecar", type=Path)
    initialize.add_argument("--title", required=True)
    initialize.add_argument("--design-id")
    initialize.add_argument("--force", action="store_true")

    answer = commands.add_parser("answer", help="Record or replace one user answer or explicit assumption.")
    answer.add_argument("sidecar", type=Path)
    answer.add_argument("--id", required=True)
    answer.add_argument("--question", required=True)
    answer.add_argument("--answer", required=True)
    answer.add_argument("--source", default="user")
    answer.add_argument("--status", choices=("confirmed", "assumed", "needs-confirmation"), default="confirmed")

    step = commands.add_parser("step", help="Update one workflow step and its evidence.")
    step.add_argument("sidecar", type=Path)
    step.add_argument("--id", required=True)
    step.add_argument("--title")
    step.add_argument("--status", choices=("pending", "in-progress", "blocked", "complete"), required=True)
    step.add_argument("--summary", default="")
    step.add_argument("--evidence", action="append", default=[])

    learning = commands.add_parser("learning", help="Record or update one reusable print learning.")
    learning.add_argument("sidecar", type=Path)
    learning.add_argument("--id", required=True)
    learning.add_argument("--statement", required=True)
    learning.add_argument("--evidence", required=True)
    learning.add_argument("--status", choices=("candidate", "validated", "promoted"), default="candidate")
    learning.add_argument("--applies-to", default="this design")

    review_add = commands.add_parser("review-add", help="Attach a review comment to a model point.")
    review_add.add_argument("sidecar", type=Path)
    review_add.add_argument("--id")
    review_add.add_argument("--part", required=True)
    review_add.add_argument("--position", required=True, nargs=3, type=float, metavar=("X", "Y", "Z"))
    review_add.add_argument("--message", required=True)
    review_add.add_argument("--author", choices=("user", "agent"), default="user")

    review_reply = commands.add_parser("review-reply", help="Reply to a model review thread.")
    review_reply.add_argument("sidecar", type=Path)
    review_reply.add_argument("--id", required=True)
    review_reply.add_argument("--message", required=True)
    review_reply.add_argument("--author", choices=("user", "agent"), default="agent")

    review_status = commands.add_parser("review-status", help="Acknowledge or resolve a model review thread.")
    review_status.add_argument("sidecar", type=Path)
    review_status.add_argument("--id", required=True)
    review_status.add_argument("--status", choices=("open", "acknowledged", "resolved"), required=True)

    state = commands.add_parser("status", help="Update the overall phase, status, and summary.")
    state.add_argument("sidecar", type=Path)
    state.add_argument("--phase", required=True)
    state.add_argument("--status", choices=("active", "blocked", "ready-for-review", "complete"), required=True)
    state.add_argument("--summary", required=True)

    show = commands.add_parser("show", help="Validate and print the sidecar.")
    show.add_argument("sidecar", type=Path)
    return root


def main() -> int:
    args = parser().parse_args()
    path: Path = args.sidecar
    with sidecar_lock(path):
        if args.command == "init":
            if path.exists() and not args.force:
                raise ValueError(f"Refusing to replace existing progress sidecar: {path}")
            data = empty_sidecar(args.design_id or slugify(args.title), args.title)
        else:
            data = read_sidecar(path)
            if args.command == "show":
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return 0
            timestamp = now()
            if args.command == "answer":
                upsert(data["answers"], {"id": args.id, "question": args.question, "answer": args.answer, "source": args.source, "status": args.status, "recorded_at": timestamp})
            elif args.command == "step":
                existing = next((item for item in data["steps"] if item["id"] == args.id), None)
                title = args.title or (existing["title"] if existing else args.id.replace("-", " ").title())
                evidence = list(dict.fromkeys([*(existing.get("evidence", []) if existing else []), *args.evidence]))
                upsert(data["steps"], {"id": args.id, "title": title, "status": args.status, "summary": args.summary, "evidence": evidence, "updated_at": timestamp})
            elif args.command == "learning":
                upsert(data["learnings"], {"id": args.id, "statement": args.statement, "evidence": args.evidence, "status": args.status, "applies_to": args.applies_to, "recorded_at": timestamp})
            elif args.command == "review-add":
                identifier = args.id or f"review-{secrets.token_hex(4)}"
                if any(item["id"] == identifier for item in data["review_comments"]):
                    raise ValueError(f"Review comment already exists: {identifier}")
                data["review_comments"].append({
                    "id": identifier,
                    "part": args.part,
                    "position_mm": list(args.position),
                    "message": args.message.strip(),
                    "author": args.author,
                    "status": "open",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "replies": [],
                })
            elif args.command in {"review-reply", "review-status"}:
                comment = next((item for item in data["review_comments"] if item["id"] == args.id), None)
                if comment is None:
                    raise ValueError(f"Unknown review comment: {args.id}")
                if args.command == "review-reply":
                    comment["replies"].append({
                        "id": f"reply-{secrets.token_hex(4)}",
                        "author": args.author,
                        "message": args.message.strip(),
                        "created_at": timestamp,
                    })
                else:
                    comment["status"] = args.status
                comment["updated_at"] = timestamp
            elif args.command == "status":
                data.update({"phase": args.phase, "status": args.status, "summary": args.summary})
            data["updated_at"] = timestamp
        atomic_write(path, data)
    print(json.dumps({"ok": True, "sidecar": str(path), "command": args.command, "updated_at": data["updated_at"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2), file=sys.stderr)
        sys.exit(2)
