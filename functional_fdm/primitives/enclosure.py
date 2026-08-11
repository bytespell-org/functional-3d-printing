"""Support-aware electronics enclosure shell primitive."""

from __future__ import annotations

from ..model import FeatureResult, Finding, Severity
from ..profile import FitProfile
from ..validation import check_wall


def enclosure_shell(
    *,
    internal_length_mm: float,
    internal_width_mm: float,
    internal_height_mm: float,
    wall_mm: float,
    floor_mm: float,
    profile: FitProfile,
    corner_radius_mm: float = 3.0,
    name: str = "enclosure-shell",
) -> FeatureResult:
    if min(internal_length_mm, internal_width_mm, internal_height_mm, wall_mm, floor_mm) <= 0:
        raise ValueError("Enclosure dimensions must be positive.")
    findings = check_wall(wall_mm, profile, f"{name}-wall") + check_wall(floor_mm, profile, f"{name}-floor")
    if corner_radius_mm < wall_mm:
        findings.append(
            Finding(
                "enclosure.corner-radius.small",
                Severity.CAUTION,
                "The outside corner radius is smaller than the wall thickness.",
                name,
                recommendation="Increase the outside radius to keep the inner corner practical.",
            )
        )
    outer_l = internal_length_mm + 2 * wall_mm
    outer_w = internal_width_mm + 2 * wall_mm
    outer_h = internal_height_mm + floor_mm
    geometry = None
    try:
        import cadquery as cq
        outer = cq.Workplane("XY").box(outer_l, outer_w, outer_h, centered=(True, True, False))
        if corner_radius_mm > 0:
            try:
                outer = outer.edges("|Z").fillet(corner_radius_mm)
            except Exception:
                findings.append(Finding("enclosure.fillet.failed", Severity.CAUTION, "Outer corner fillet failed; use a smaller radius.", name))
        inner = (
            cq.Workplane("XY", origin=(0, 0, floor_mm))
            .box(internal_length_mm, internal_width_mm, internal_height_mm + 1, centered=(True, True, False))
        )
        geometry = outer.cut(inner)
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "enclosure-shell",
        geometry,
        dimensions={"internal_length_mm": internal_length_mm, "internal_width_mm": internal_width_mm, "internal_height_mm": internal_height_mm, "wall_mm": wall_mm, "floor_mm": floor_mm, "outer_length_mm": outer_l, "outer_width_mm": outer_w, "outer_height_mm": outer_h},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Print open-side up unless another orientation has a stronger reason.", "Use through-edge connector openings or self-supporting roofs.", "Choose lid architecture before adding detailed cutouts."],
    )


def snap_lid(
    *,
    opening_length_mm: float,
    opening_width_mm: float,
    plate_thickness_mm: float,
    skirt_depth_mm: float,
    skirt_wall_mm: float,
    profile: FitProfile,
    catch_count: int = 4,
    name: str = "snap-lid",
) -> FeatureResult:
    """Create a locating lid blank. Add qualified snap primitives at its catch sites."""
    if min(opening_length_mm, opening_width_mm, plate_thickness_mm, skirt_depth_mm, skirt_wall_mm) <= 0:
        raise ValueError("Lid dimensions must be positive.")
    if catch_count < 2:
        raise ValueError("A snap lid needs at least two distributed catches.")
    gap = profile.snap_clearance_per_side_mm
    findings = check_wall(plate_thickness_mm, profile, name) + check_wall(skirt_wall_mm, profile, name)
    if not profile.characterized:
        findings.append(
            Finding(
                "lid.snap-fit.uncalibrated",
                Severity.CAUTION,
                "The lid skirt and catch clearance are not calibrated.",
                name,
                recommendation="Print one edge with one catch before the full lid.",
            )
        )
    geometry = None
    try:
        import cadquery as cq

        outer_length = opening_length_mm - 2 * gap
        outer_width = opening_width_mm - 2 * gap
        inner_length = outer_length - 2 * skirt_wall_mm
        inner_width = outer_width - 2 * skirt_wall_mm
        if min(inner_length, inner_width) <= 0:
            raise ValueError("The skirt wall removes the lid opening.")
        plate = cq.Workplane("XY").box(opening_length_mm + 2 * skirt_wall_mm, opening_width_mm + 2 * skirt_wall_mm, plate_thickness_mm, centered=(True, True, False))
        skirt_outer = cq.Workplane("XY", origin=(0, 0, -skirt_depth_mm)).box(outer_length, outer_width, skirt_depth_mm, centered=(True, True, False))
        skirt_inner = cq.Workplane("XY", origin=(0, 0, -skirt_depth_mm - 0.1)).box(inner_length, inner_width, skirt_depth_mm + 0.2, centered=(True, True, False))
        geometry = plate.union(skirt_outer.cut(skirt_inner))
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "snap-lid",
        geometry,
        dimensions={"opening_length_mm": opening_length_mm, "opening_width_mm": opening_width_mm, "plate_thickness_mm": plate_thickness_mm, "skirt_depth_mm": skirt_depth_mm, "skirt_wall_mm": skirt_wall_mm, "gap_per_side_mm": gap, "catch_count": catch_count},
        assumptions={**profile.assumptions(), "retention_geometry": "must use checked cantilever, U, or annular snap primitives"},
        findings=findings,
        print_notes=["Add catches only after snap strain and release are checked.", "Provide a pry or release feature when the lid is serviceable."],
    )


def screw_lid(
    *,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    hole_diameter_mm: float,
    edge_distance_mm: float,
    profile: FitProfile,
    name: str = "screw-lid",
) -> FeatureResult:
    """Create a four-hole lid with explicit edge and driver checks left in metadata."""
    if min(length_mm, width_mm, thickness_mm, hole_diameter_mm, edge_distance_mm) <= 0:
        raise ValueError("Screw-lid dimensions must be positive.")
    findings = check_wall(thickness_mm, profile, name)
    if edge_distance_mm < 1.5 * hole_diameter_mm:
        findings.append(
            Finding(
                "lid.fastener-edge-distance.small",
                Severity.LIKELY_FAILURE,
                "The screw-hole center is close to the lid edge.",
                name,
                recommendation="Increase edge distance or add a local pad.",
            )
        )
    geometry = None
    positions = [
        (x, y)
        for x in (-length_mm / 2 + edge_distance_mm, length_mm / 2 - edge_distance_mm)
        for y in (-width_mm / 2 + edge_distance_mm, width_mm / 2 - edge_distance_mm)
    ]
    try:
        import cadquery as cq

        geometry = (
            cq.Workplane("XY")
            .box(length_mm, width_mm, thickness_mm, centered=(True, True, False))
            .faces(">Z")
            .workplane()
            .pushPoints(positions)
            .hole(hole_diameter_mm, thickness_mm)
        )
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "screw-lid",
        geometry,
        dimensions={"length_mm": length_mm, "width_mm": width_mm, "thickness_mm": thickness_mm, "hole_diameter_mm": hole_diameter_mm, "edge_distance_mm": edge_distance_mm, "hole_count": 4},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Use standards-based head recesses when needed.", "Validate screw length, boss engagement, driver access, and protected-volume clearance."],
    )
