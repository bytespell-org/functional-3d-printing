#!/usr/bin/env python3
"""Build the compiled Three.js workbench and its model manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def parse_part(value: str) -> tuple[str, Path, str]:
    fields = value.split("=", 1)
    if len(fields) != 2:
        raise argparse.ArgumentTypeError("Use NAME=PATH[:COLOR].")
    name, remainder = fields
    path_text, separator, color = remainder.rpartition(":")
    if not separator or not color.startswith("#"):
        path_text, color = remainder, "#4f7cac"
    path = Path(path_text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"STL does not exist: {path}")
    return name, path, color


def parse_json_object(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("Review data must be a JSON object.")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--part", action="append", required=True, type=parse_part)
    parser.add_argument("--title", default="Functional CAD Preview")
    parser.add_argument("--annotation", action="append", default=[], type=parse_json_object)
    parser.add_argument("--progress-url", default="../progress.json")
    args = parser.parse_args()

    asset_root = Path(__file__).resolve().parents[1] / "assets" / "preview"
    output = args.output
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(asset_root, output)
    model_dir = output / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "title": args.title,
        "parts": [],
        "annotations": args.annotation,
        "progress_url": args.progress_url,
    }
    used_names: set[str] = set()
    for index, (name, path, color) in enumerate(args.part):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        filename = (
            f"{index + 1:02d}-{path.stem}-{digest[:12]}{path.suffix.lower()}"
        )
        if filename in used_names:
            raise ValueError(f"Duplicate preview filename: {filename}")
        used_names.add(filename)
        shutil.copy2(path, model_dir / filename)
        manifest["parts"].append(
            {
                "name": name,
                "file": f"models/{filename}",
                "color": color,
                "sha256": digest,
            }
        )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "preview": str(output / "index.html"), "parts": len(args.part)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
