#!/usr/bin/env python3
"""Render deterministic diagnostic PNG views from one or more STL files."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from audit_stl import Triangle, cross, length, load_stl, subtract


Vector = tuple[float, float, float]


@dataclass(frozen=True)
class Mesh:
    path: Path
    triangles: list[Triangle]
    color: tuple[int, int, int]


VIEWS: dict[str, tuple[Vector, Vector]] = {
    "iso": ((1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "back": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
}


def normalize(vector: Vector) -> Vector:
    magnitude = length(vector)
    if magnitude <= 1e-12:
        raise ValueError("Cannot normalize a zero vector.")
    return tuple(value / magnitude for value in vector)  # type: ignore[return-value]


def dot(left: Vector, right: Vector) -> float:
    return sum(a * b for a, b in zip(left, right))


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid RGB color: {value!r}")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)  # type: ignore[return-value]


def render(
    meshes: list[Mesh],
    output: Path,
    camera: Vector,
    up_hint: Vector,
    size: int,
    explode_mm: float = 0.0,
    mesh_edges: bool = False,
) -> None:
    camera = normalize(camera)
    right = normalize(cross(up_hint, camera))
    up = normalize(cross(camera, right))
    all_triangles: list[tuple[list[tuple[float, float]], float, tuple[int, int, int]]] = []
    projected_points: list[tuple[float, float]] = []
    light = normalize((-0.4, -0.6, 1.0))

    for mesh_index, mesh in enumerate(meshes):
        offset = ((mesh_index - (len(meshes) - 1) / 2) * explode_mm, 0.0, 0.0)
        for triangle in mesh.triangles:
            moved = [
                (vertex[0] + offset[0], vertex[1] + offset[1], vertex[2] + offset[2])
                for vertex in triangle
            ]
            points = [(dot(vertex, right), dot(vertex, up)) for vertex in moved]
            projected_points.extend(points)
            depth = sum(dot(vertex, camera) for vertex in moved) / 3
            raw_normal = cross(subtract(moved[1], moved[0]), subtract(moved[2], moved[0]))
            if length(raw_normal) <= 1e-12:
                continue
            normal = normalize(raw_normal)
            lighting = 0.55 + 0.45 * abs(dot(normal, light))
            all_triangles.append((points, depth, shade(mesh.color, lighting)))

    if not projected_points:
        raise ValueError("No triangles to render.")
    min_x = min(point[0] for point in projected_points)
    max_x = max(point[0] for point in projected_points)
    min_y = min(point[1] for point in projected_points)
    max_y = max(point[1] for point in projected_points)
    span = max(max_x - min_x, max_y - min_y, 1e-6)
    scale = size * 0.82 / span
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    image = Image.new("RGB", (size, size), (247, 248, 251))
    draw = ImageDraw.Draw(image)
    grid_color = (225, 228, 234)
    for index in range(1, 10):
        position = round(index * size / 10)
        draw.line((position, 0, position, size), fill=grid_color)
        draw.line((0, position, size, position), fill=grid_color)

    for points, _, color in sorted(all_triangles, key=lambda item: item[1]):
        screen = [
            (
                size / 2 + (x - center_x) * scale,
                size / 2 - (y - center_y) * scale,
            )
            for x, y in points
        ]
        draw.polygon(screen, fill=color)
        if mesh_edges:
            draw.line(screen + [screen[0]], fill=shade(color, 0.65), width=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stl", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--colors", default="#4f7cac,#e07a5f,#81b29a,#f2cc8f")
    parser.add_argument("--size", type=int, default=900)
    parser.add_argument("--explode-mm", type=float, default=0.0)
    parser.add_argument("--mesh-edges", action="store_true")
    args = parser.parse_args()
    if args.size < 128:
        raise ValueError("--size must be at least 128.")
    colors = [parse_color(value) for value in args.colors.split(",")]
    meshes = [Mesh(path, load_stl(path), colors[index % len(colors)]) for index, path in enumerate(args.stl)]
    for name, (camera, up) in VIEWS.items():
        explode = args.explode_mm if name == "iso" else 0.0
        suffix = "exploded_iso" if name == "iso" and explode > 0 else name
        render(meshes, args.output / f"{suffix}.png", camera, up, args.size, explode, args.mesh_edges)
    return 0


if __name__ == "__main__":
    sys.exit(main())
