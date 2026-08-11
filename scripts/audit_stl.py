#!/usr/bin/env python3
"""Audit STL topology, part count, dimensions, and downward-facing surfaces."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path


Vector = tuple[float, float, float]
Triangle = tuple[Vector, Vector, Vector]


def subtract(a: Vector, b: Vector) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: Vector, b: Vector) -> Vector:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a: Vector, b: Vector) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def length(v: Vector) -> float:
    return math.sqrt(dot(v, v))


def load_binary_stl(data: bytes) -> list[Triangle] | None:
    if len(data) < 84:
        return None
    count = struct.unpack_from("<I", data, 80)[0]
    if 84 + count * 50 != len(data):
        return None
    triangles: list[Triangle] = []
    offset = 84
    for _ in range(count):
        values = struct.unpack_from("<12fH", data, offset)
        triangles.append(
            (
                (values[3], values[4], values[5]),
                (values[6], values[7], values[8]),
                (values[9], values[10], values[11]),
            )
        )
        offset += 50
    return triangles


def load_ascii_stl(data: bytes) -> list[Triangle]:
    text = data.decode("utf-8", errors="replace")
    values = re.findall(
        r"\bvertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", text
    )
    vertices = [(float(x), float(y), float(z)) for x, y, z in values]
    if not vertices or len(vertices) % 3:
        raise ValueError("The file is not a valid binary or ASCII STL.")
    return [tuple(vertices[i : i + 3]) for i in range(0, len(vertices), 3)]  # type: ignore[list-item]


def load_stl(path: Path) -> list[Triangle]:
    data = path.read_bytes()
    triangles = load_binary_stl(data)
    return triangles if triangles is not None else load_ascii_stl(data)


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def rounded_vertex(vertex: Vector, tolerance: float) -> tuple[int, int, int]:
    return tuple(round(value / tolerance) for value in vertex)  # type: ignore[return-value]


def bounds(vertices: list[Vector]) -> dict[str, list[float]]:
    minimum = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    return {
        "min": [round(value, 5) for value in minimum],
        "max": [round(value, 5) for value in maximum],
        "size": [round(maximum[i] - minimum[i], 5) for i in range(3)],
    }


def audit(
    triangles: list[Triangle],
    vertex_tolerance: float,
    bed_tolerance: float,
    overhang_angle: float,
    horizontal_angle: float = 80.0,
    horizontal_min_height: float = 0.6,
) -> dict[str, object]:
    clean: list[Triangle] = []
    triangle_areas: list[float] = []
    normals: list[Vector] = []
    degenerate = 0

    for triangle in triangles:
        normal = cross(subtract(triangle[1], triangle[0]), subtract(triangle[2], triangle[0]))
        magnitude = length(normal)
        if magnitude <= 1e-12:
            degenerate += 1
        clean.append(triangle)
        if magnitude <= 1e-12:
            triangle_areas.append(0.0)
            normals.append((0.0, 0.0, 0.0))
        else:
            triangle_areas.append(magnitude / 2.0)
            normals.append(tuple(value / magnitude for value in normal))  # type: ignore[arg-type]

    if not clean:
        raise ValueError("The STL contains no non-degenerate triangles.")

    vertex_ids: dict[tuple[int, int, int], int] = {}
    vertices: list[Vector] = []
    indexed: list[tuple[int, int, int]] = []
    for triangle in clean:
        ids = []
        for vertex in triangle:
            key = rounded_vertex(vertex, vertex_tolerance)
            if key not in vertex_ids:
                vertex_ids[key] = len(vertices)
                vertices.append(vertex)
            ids.append(vertex_ids[key])
        indexed.append((ids[0], ids[1], ids[2]))

    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(indexed):
        for left, right in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_faces[tuple(sorted((left, right)))].append(face_index)

    sets = DisjointSet(len(clean))
    for face_indexes in edge_faces.values():
        for face_index in face_indexes[1:]:
            sets.union(face_indexes[0], face_index)

    component_faces: dict[int, list[int]] = defaultdict(list)
    for face_index in range(len(clean)):
        component_faces[sets.find(face_index)].append(face_index)

    component_report = []
    for face_indexes in sorted(component_faces.values(), key=len, reverse=True):
        component_vertices = [vertex for index in face_indexes for vertex in clean[index]]
        component_report.append(
            {"triangles": len(face_indexes), "bounds_mm": bounds(component_vertices)}
        )

    mesh_bounds = bounds(vertices)
    bed_z = mesh_bounds["min"][2]
    overhang_area = 0.0
    overhang_triangles = 0
    overhang_z: list[float] = []
    overhang_faces: list[int] = []
    horizontal_faces: list[int] = []
    for face_index, (triangle, normal, area) in enumerate(zip(clean, normals, triangle_areas)):
        on_bed = all(vertex[2] <= bed_z + bed_tolerance for vertex in triangle)
        severity = math.degrees(math.asin(max(0.0, min(1.0, -normal[2]))))
        if not on_bed and severity > overhang_angle + 1e-6:
            overhang_area += area
            overhang_triangles += 1
            overhang_z.extend(vertex[2] for vertex in triangle)
            overhang_faces.append(face_index)
        if (
            not on_bed
            and min(vertex[2] for vertex in triangle) > bed_z + horizontal_min_height
            and severity > horizontal_angle + 1e-6
        ):
            horizontal_faces.append(face_index)

    overhang_sets = DisjointSet(len(clean))
    overhang_face_set = set(overhang_faces)
    for face_indexes in edge_faces.values():
        flagged = [face_index for face_index in face_indexes if face_index in overhang_face_set]
        for face_index in flagged[1:]:
            overhang_sets.union(flagged[0], face_index)
    overhang_groups: dict[int, list[int]] = defaultdict(list)
    for face_index in overhang_faces:
        overhang_groups[overhang_sets.find(face_index)].append(face_index)
    overhang_regions = []
    for face_indexes in overhang_groups.values():
        region_vertices = [vertex for index in face_indexes for vertex in clean[index]]
        overhang_regions.append(
            {
                "area_mm2": round(sum(triangle_areas[index] for index in face_indexes), 3),
                "triangles": len(face_indexes),
                "bounds_mm": bounds(region_vertices),
            }
        )
    overhang_regions.sort(key=lambda region: region["area_mm2"], reverse=True)

    horizontal_sets = DisjointSet(len(clean))
    horizontal_face_set = set(horizontal_faces)
    for face_indexes in edge_faces.values():
        flagged = [face_index for face_index in face_indexes if face_index in horizontal_face_set]
        for face_index in flagged[1:]:
            horizontal_sets.union(flagged[0], face_index)
    horizontal_groups: dict[int, list[int]] = defaultdict(list)
    for face_index in horizontal_faces:
        horizontal_groups[horizontal_sets.find(face_index)].append(face_index)
    horizontal_regions = []
    for face_indexes in horizontal_groups.values():
        region_vertices = [vertex for index in face_indexes for vertex in clean[index]]
        region_bounds = bounds(region_vertices)
        xy_sizes = [size for size in region_bounds["size"][:2] if size > vertex_tolerance]
        horizontal_regions.append(
            {
                "area_mm2": round(sum(triangle_areas[index] for index in face_indexes), 3),
                "triangles": len(face_indexes),
                "estimated_short_span_mm": round(min(xy_sizes), 3) if xy_sizes else 0.0,
                "bounds_mm": region_bounds,
            }
        )
    horizontal_regions.sort(key=lambda region: region["area_mm2"], reverse=True)
    horizontal_area = sum(float(region["area_mm2"]) for region in horizontal_regions)

    signed_volume = 0.0
    for a, b, c in clean:
        signed_volume += dot(a, cross(b, c)) / 6.0

    boundary_edges = sum(1 for faces in edge_faces.values() if len(faces) == 1)
    nonmanifold_edges = sum(1 for faces in edge_faces.values() if len(faces) > 2)
    report: dict[str, object] = {
        "triangles": len(clean),
        "degenerate_triangles": degenerate,
        "vertices": len(vertices),
        "bounds_mm": mesh_bounds,
        "volume_mm3": round(abs(signed_volume), 3),
        "surface_area_mm2": round(sum(triangle_areas), 3),
        "components": len(component_report),
        "component_details": component_report,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "watertight": boundary_edges == 0 and nonmanifold_edges == 0,
        "overhang": {
            "threshold_degrees_from_vertical": overhang_angle,
            "area_mm2": round(overhang_area, 3),
            "triangles": overhang_triangles,
            "z_range_mm": (
                [round(min(overhang_z), 5), round(max(overhang_z), 5)] if overhang_z else None
            ),
            "largest_regions": overhang_regions[:12],
        },
        "unsupported_horizontal_candidates": {
            "threshold_degrees_from_vertical": horizontal_angle,
            "minimum_height_above_bed_mm": horizontal_min_height,
            "area_mm2": round(horizontal_area, 3),
            "regions": horizontal_regions[:24],
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stl", type=Path)
    parser.add_argument("--expected-components", type=int, default=1)
    parser.add_argument("--vertex-tolerance", type=float, default=0.00001)
    parser.add_argument("--bed-tolerance", type=float, default=0.05)
    parser.add_argument("--max-overhang-degrees", type=float, default=45.0)
    parser.add_argument("--max-overhang-area", type=float, default=0.01)
    parser.add_argument("--fail-on-overhang", action="store_true")
    parser.add_argument("--horizontal-angle", type=float, default=80.0)
    parser.add_argument("--horizontal-min-height", type=float, default=0.6)
    parser.add_argument("--max-horizontal-area", type=float, default=5.0)
    parser.add_argument("--max-horizontal-region-area", type=float, default=2.0)
    parser.add_argument("--fail-on-unsupported-horizontal", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    try:
        report = audit(
            load_stl(args.stl),
            args.vertex_tolerance,
            args.bed_tolerance,
            args.max_overhang_degrees,
            args.horizontal_angle,
            args.horizontal_min_height,
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "file": str(args.stl), "failures": [str(error)]}, indent=2))
        return 2

    if report["components"] != args.expected_components:
        failures.append(
            f"Expected {args.expected_components} connected components; found {report['components']}."
        )
    if args.strict and not report["watertight"]:
        failures.append("The STL has boundary or non-manifold edges.")
    overhang = report["overhang"]
    if args.fail_on_overhang and overhang["area_mm2"] > args.max_overhang_area:  # type: ignore[index]
        failures.append(
            f"Downward overhang area {overhang['area_mm2']} mm2 exceeds "  # type: ignore[index]
            f"{args.max_overhang_area} mm2."
        )
    horizontal = report["unsupported_horizontal_candidates"]
    largest_horizontal = max(
        (region["area_mm2"] for region in horizontal["regions"]),  # type: ignore[index]
        default=0.0,
    )
    if args.fail_on_unsupported_horizontal and (
        horizontal["area_mm2"] > args.max_horizontal_area  # type: ignore[index]
        or largest_horizontal > args.max_horizontal_region_area
    ):
        failures.append(
            "Unsupported horizontal candidate area "
            f"{horizontal['area_mm2']} mm2 with largest region {largest_horizontal} mm2 "  # type: ignore[index]
            "requires an explicit bridge or removable-support plan."
        )

    output = {"ok": not failures, "file": str(args.stl), **report, "failures": failures}
    print(json.dumps(output, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
