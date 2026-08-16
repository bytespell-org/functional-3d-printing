#!/usr/bin/env python3
"""Build the compiled Three.js workbench and its model manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
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


def parse_reference(value: str) -> dict[str, object]:
    parsed = parse_json_object(value)
    name = parsed.get("name")
    path = parsed.get("path")
    if not isinstance(name, str) or not name.strip():
        raise argparse.ArgumentTypeError("Reference JSON requires a non-empty name.")
    if not isinstance(path, str) or not Path(path).is_file():
        raise argparse.ArgumentTypeError(f"Reference STL does not exist: {path}")
    for field in ("position_mm", "rotation_deg"):
        values = parsed.get(field, [0.0, 0.0, 0.0])
        if not isinstance(values, list) or len(values) != 3 or not all(
            isinstance(item, (int, float)) for item in values
        ):
            raise argparse.ArgumentTypeError(f"Reference {field} requires three numbers.")
        parsed[field] = [float(item) for item in values]
    opacity = parsed.get("opacity", 0.42)
    if not isinstance(opacity, (int, float)) or not 0.05 <= opacity <= 1.0:
        raise argparse.ArgumentTypeError("Reference opacity must be between 0.05 and 1.0.")
    parsed["opacity"] = float(opacity)
    parsed["color"] = parsed.get("color", "#94a3b8")
    return parsed


def write_json_atomic(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--part", action="append", required=True, type=parse_part)
    parser.add_argument("--reference", action="append", default=[], type=parse_reference)
    parser.add_argument("--title", default="Functional CAD Preview")
    parser.add_argument("--annotation", action="append", default=[], type=parse_json_object)
    parser.add_argument("--progress-url", default="", help="Optional progress sidecar URL that enables collaborative review controls.")
    args = parser.parse_args()

    asset_root = Path(__file__).resolve().parents[1] / "assets" / "preview"
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(asset_root, output, dirs_exist_ok=True)
    model_dir = output / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "title": args.title,
        "parts": [],
        "references": [],
        "annotations": args.annotation,
        "progress_url": args.progress_url or None,
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
                "role": "printable",
                "sha256": digest,
            }
        )
    for index, reference in enumerate(args.reference):
        source = Path(str(reference["path"]))
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        filename = f"ref-{index + 1:02d}-{source.stem}-{digest[:12]}{source.suffix.lower()}"
        if filename in used_names:
            raise ValueError(f"Duplicate preview filename: {filename}")
        used_names.add(filename)
        shutil.copy2(source, model_dir / filename)
        manifest["references"].append(
            {
                "name": reference["name"],
                "file": f"models/{filename}",
                "role": "reference",
                "color": reference["color"],
                "opacity": reference["opacity"],
                "position_mm": reference["position_mm"],
                "rotation_deg": reference["rotation_deg"],
                "nominal_size_mm": reference.get("nominal_size_mm"),
                "notes": reference.get("notes", []),
                "source_id": reference.get("source_id"),
                "geometry_basis": reference.get("geometry_basis", "nominal-envelope"),
                "sha256": digest,
            }
        )
    revision_payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["revision"] = hashlib.sha256(revision_payload).hexdigest()
    write_json_atomic(output / "manifest.json", manifest)

    active_models = {
        Path(str(item["file"])).name
        for collection in (manifest["parts"], manifest["references"])
        for item in collection
    }
    stale_before = time.time() - 60.0
    for candidate in model_dir.iterdir():
        if (
            candidate.is_file()
            and candidate.name not in active_models
            and candidate.stat().st_mtime < stale_before
        ):
            candidate.unlink()
    print(json.dumps({
        "ok": True,
        "preview": str(output / "index.html"),
        "parts": len(args.part),
        "references": len(args.reference),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
