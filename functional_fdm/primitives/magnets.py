"""Magnet pocket primitive and retention checks."""

from __future__ import annotations

from ..model import FeatureResult, Finding, Severity
from ..profile import FitProfile
from ..validation import check_wall


def magnet_pocket(
    *,
    diameter_mm: float,
    thickness_mm: float,
    profile: FitProfile,
    retention: str = "adhesive",
    bottom_thickness_mm: float = 1.2,
    insertion_chamfer_mm: float = 0.3,
    polarity: str = "mark-after-test",
    name: str = "magnet-pocket",
) -> FeatureResult:
    if retention not in ("adhesive", "press-fit", "snap-lip", "captured"):
        raise ValueError("Unsupported retention mode.")
    if min(diameter_mm, thickness_mm, bottom_thickness_mm) <= 0:
        raise ValueError("Magnet dimensions must be positive.")
    findings = check_wall(bottom_thickness_mm, profile, f"{name}-bottom")
    if polarity == "unknown":
        findings.append(
            Finding(
                "magnet.polarity.unknown",
                Severity.BLOCKING,
                "Paired magnet polarity is not defined.",
                name,
                recommendation="Mark and record polarity before adhesive or capture closes the pocket.",
            )
        )
    radial_adjustment = 0.0
    if retention == "press-fit":
        radial_adjustment = -profile.press_interference_per_side_mm
        if not profile.characterized:
            findings.append(
                Finding(
                    "magnet.press-fit.uncalibrated",
                    Severity.CAUTION,
                    "The magnet press fit is not calibrated.",
                    name,
                    recommendation="After the magnet closure is approved, print a small pocket fit test using the available magnets.",
                )
            )
    elif retention == "adhesive":
        radial_adjustment = profile.friction_per_side_mm
    else:
        radial_adjustment = profile.close_sliding_per_side_mm
    pocket_diameter = diameter_mm + 2 * radial_adjustment + profile.hole_diameter_compensation_mm
    pocket_depth = thickness_mm + (0.10 if retention == "adhesive" else 0.0)
    geometry = None
    try:
        import cadquery as cq
        cutter = cq.Workplane("XY").circle(pocket_diameter / 2).extrude(pocket_depth)
        if insertion_chamfer_mm > 0:
            lead = (
                cq.Workplane("XY", origin=(0, 0, pocket_depth - insertion_chamfer_mm))
                .circle(pocket_diameter / 2 + insertion_chamfer_mm)
                .workplane(offset=insertion_chamfer_mm)
                .circle(pocket_diameter / 2)
                .loft(combine=True)
            )
            cutter = cutter.union(lead)
        geometry = cutter
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "magnet-pocket",
        geometry,
        dimensions={"magnet_diameter_mm": diameter_mm, "magnet_thickness_mm": thickness_mm, "pocket_diameter_mm": round(pocket_diameter, 4), "pocket_depth_mm": round(pocket_depth, 4), "bottom_thickness_mm": bottom_thickness_mm},
        assumptions={"retention": retention, "polarity": polarity, **profile.assumptions()},
        findings=findings,
        print_notes=["Measure the actual magnet batch.", "Record polarity in assembly notes before installation.", "Provide a removal path when service is required."],
    )
