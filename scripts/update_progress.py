#!/usr/bin/env python3
"""Create and atomically update the small observable CAD work sidecar."""

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


SCHEMA_VERSION = 2


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
        "summary": "",
        "updated_at": timestamp,
        "progress": [],
        "comments": [],
    }


def migrate_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Keep visible work and actionable comments from the retired v1 contract."""
    timestamp = now()
    progress = []
    for item in data.get("steps", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        progress.append({
            "id": item["id"],
            "title": str(item.get("title") or item["id"].replace("-", " ").title()),
            "summary": str(item.get("summary") or ""),
            "updated_at": str(item.get("updated_at") or timestamp),
        })
    comments = []
    for item in data.get("review_comments", []):
        if not isinstance(item, dict) or item.get("status") == "resolved" or not item.get("id"):
            continue
        position = item.get("position_mm")
        if not isinstance(position, list) or len(position) != 3:
            continue
        comments.append({
            "id": item["id"],
            "part": str(item.get("part") or "model"),
            "position_mm": position,
            "message": str(item.get("message") or ""),
            "created_at": str(item.get("created_at") or timestamp),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "design_id": str(data.get("design_id") or slugify(str(data.get("title") or "design"))),
        "title": str(data.get("title") or "Design"),
        "summary": str(data.get("summary") or ""),
        "updated_at": timestamp,
        "progress": progress,
        "comments": comments,
    }


def load_sidecar(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.is_file():
        raise ValueError(f"Progress sidecar does not exist: {path}. Run init first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Progress sidecar must be a JSON object.")
    if data.get("schema_version") == 1:
        return migrate_v1(data), True
    validate(data)
    return data, False


def validate(data: object) -> None:
    if not isinstance(data, dict):
        raise ValueError("Progress sidecar must be a JSON object.")
    required = {"schema_version", "design_id", "title", "summary", "updated_at", "progress", "comments"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Progress sidecar is missing: {', '.join(sorted(missing))}.")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {data['schema_version']!r}.")
    if not all(isinstance(data[key], list) for key in ("progress", "comments")):
        raise ValueError("progress and comments must be arrays.")
    for collection in ("progress", "comments"):
        identifiers = [item.get("id") for item in data[collection] if isinstance(item, dict)]
        if len(identifiers) != len(data[collection]) or any(not value for value in identifiers):
            raise ValueError(f"Every {collection} entry must be an object with an id.")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError(f"Duplicate id in {collection}.")
    for item in data["comments"]:
        position = item.get("position_mm")
        if not isinstance(position, list) or len(position) != 3:
            raise ValueError("Every comment requires a three-value position_mm array.")
        if not isinstance(item.get("message"), str) or not item["message"].strip():
            raise ValueError("Every comment requires a message.")


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

    initialize = commands.add_parser("init", help="Create a new minimal work sidecar.")
    initialize.add_argument("sidecar", type=Path)
    initialize.add_argument("--title", required=True)
    initialize.add_argument("--design-id")
    initialize.add_argument("--force", action="store_true")

    progress = commands.add_parser("progress", help="Set the overall summary or add/update one visible progress item.")
    progress.add_argument("sidecar", type=Path)
    progress.add_argument("--id")
    progress.add_argument("--title")
    progress.add_argument("--summary", help="Milestone summary with --id; otherwise the overall summary.")
    progress.add_argument("--overall-summary", help="Set the overall summary while also updating a milestone.")

    comment_add = commands.add_parser("comment-add", help="Attach a comment to a model point.")
    comment_add.add_argument("sidecar", type=Path)
    comment_add.add_argument("--id")
    comment_add.add_argument("--part", required=True)
    comment_add.add_argument("--position", required=True, nargs=3, type=float, metavar=("X", "Y", "Z"))
    comment_add.add_argument("--message", required=True)

    comment_remove = commands.add_parser("comment-remove", help="Remove an addressed or unwanted comment.")
    comment_remove.add_argument("sidecar", type=Path)
    comment_remove.add_argument("--id", required=True)

    show = commands.add_parser("show", help="Validate, migrate, and print the sidecar.")
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
            data, migrated = load_sidecar(path)
            if args.command == "show":
                if migrated:
                    atomic_write(path, data)
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return 0
            timestamp = now()
            if args.command == "progress":
                if args.id:
                    existing = next((item for item in data["progress"] if item["id"] == args.id), None)
                    upsert(data["progress"], {
                        "id": args.id,
                        "title": args.title or (existing["title"] if existing else args.id.replace("-", " ").title()),
                        "summary": args.summary if args.summary is not None else (existing["summary"] if existing else ""),
                        "updated_at": timestamp,
                    })
                    if args.overall_summary is not None:
                        data["summary"] = args.overall_summary
                else:
                    if args.title is not None or (args.summary is None and args.overall_summary is None):
                        raise ValueError("Use progress --summary TEXT to set the overall summary, or provide --id for a milestone.")
                    data["summary"] = args.overall_summary if args.overall_summary is not None else args.summary
            elif args.command == "comment-add":
                identifier = args.id or f"comment-{secrets.token_hex(4)}"
                if any(item["id"] == identifier for item in data["comments"]):
                    raise ValueError(f"Comment already exists: {identifier}")
                data["comments"].append({
                    "id": identifier,
                    "part": args.part,
                    "position_mm": list(args.position),
                    "message": args.message.strip(),
                    "created_at": timestamp,
                })
            elif args.command == "comment-remove":
                before = len(data["comments"])
                data["comments"] = [item for item in data["comments"] if item["id"] != args.id]
                if len(data["comments"]) == before:
                    raise ValueError(f"Unknown comment: {args.id}")
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
