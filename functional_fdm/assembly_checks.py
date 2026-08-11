"""Semantic checks for assembly paths, hardware stacks, and service access."""

from __future__ import annotations

import math
from typing import Any

from .model import AssemblyCheckResult, Finding, Severity


def _shape(geometry: Any) -> Any:
    value = geometry.val() if hasattr(geometry, "val") else geometry
    if value is None:
        raise ValueError("Assembly geometry must contain a shape.")
    return value


def _intersection_volume_mm3(geometry_a: Any, geometry_b: Any) -> float:
    intersection = _shape(geometry_a).intersect(_shape(geometry_b))
    intersection = _shape(intersection)
    solids = intersection.Solids() if hasattr(intersection, "Solids") else []
    return float(sum(solid.Volume() for solid in solids))


def _translate(geometry: Any, offset: tuple[float, float, float]) -> Any:
    if hasattr(geometry, "val"):
        return geometry.translate(offset)
    import cadquery as cq

    return geometry.translate(cq.Vector(*offset))


def check_assembly_interference(
    *,
    part_a: str,
    geometry_a: Any,
    part_b: str,
    geometry_b: Any,
    allowed_interference_mm3: float = 0.01,
    feature: str = "assembled-state",
) -> AssemblyCheckResult:
    """Measure unintended solid overlap in the final assembled state."""
    if allowed_interference_mm3 < 0:
        raise ValueError("Allowed interference must not be negative.")
    findings: list[Finding] = []
    try:
        overlap = _intersection_volume_mm3(geometry_a, geometry_b)
    except Exception as error:
        overlap = math.nan
        findings.append(
            Finding(
                "assembly.interference-check-failed",
                Severity.BLOCKING,
                "The final assembled-state intersection could not be measured.",
                feature,
                {"error": str(error)},
                "Repair the geometry or placement and rerun the intersection check.",
            )
        )
    else:
        if overlap > allowed_interference_mm3:
            findings.append(
                Finding(
                    "assembly.unintended-interference",
                    Severity.BLOCKING,
                    f"The assembled parts overlap by {overlap:.3f} mm^3.",
                    feature,
                    {
                        "part_a": part_a,
                        "part_b": part_b,
                        "overlap_mm3": overlap,
                        "allowed_interference_mm3": allowed_interference_mm3,
                    },
                    "Correct the mating dimensions or explicitly justify and bound an intended interference fit.",
                )
            )
    return AssemblyCheckResult(
        name=feature,
        part_a=part_a,
        part_b=part_b,
        check_type="final-state-interference",
        measurements={
            "overlap_mm3": overlap,
            "allowed_interference_mm3": allowed_interference_mm3,
        },
        findings=findings,
    )


def check_assembly_insertion_path(
    *,
    fixed_part: str,
    fixed_geometry: Any,
    moving_part: str,
    moving_geometry: Any,
    insertion_direction: tuple[float, float, float],
    approach_distance_mm: float,
    samples: int = 12,
    allowed_interference_mm3: float = 0.01,
    feature: str = "assembly-insertion-path",
) -> AssemblyCheckResult:
    """Sample a straight insertion path ending at the modeled assembled state."""
    magnitude = math.sqrt(sum(value * value for value in insertion_direction))
    if magnitude <= 1e-12:
        raise ValueError("Insertion direction must not be zero.")
    if approach_distance_mm <= 0 or samples < 2 or allowed_interference_mm3 < 0:
        raise ValueError("Approach distance and sample count must be positive; allowed interference must not be negative.")
    direction = tuple(value / magnitude for value in insertion_direction)
    maximum = 0.0
    maximum_index = 0
    findings: list[Finding] = []
    try:
        for index in range(samples + 1):
            fraction = index / samples
            remaining = approach_distance_mm * (1.0 - fraction)
            offset = tuple(-value * remaining for value in direction)
            moved = _translate(moving_geometry, offset)
            overlap = _intersection_volume_mm3(fixed_geometry, moved)
            if overlap > maximum:
                maximum = overlap
                maximum_index = index
    except Exception as error:
        maximum = math.nan
        findings.append(
            Finding(
                "assembly.insertion-check-failed",
                Severity.BLOCKING,
                "The assembly insertion path could not be measured.",
                feature,
                {"error": str(error)},
                "Repair the geometry or placement and rerun the insertion-path check.",
            )
        )
    else:
        if maximum > allowed_interference_mm3:
            findings.append(
                Finding(
                    "assembly.insertion-path-blocked",
                    Severity.BLOCKING,
                    f"The insertion path reaches {maximum:.3f} mm^3 of solid overlap.",
                    feature,
                    {
                        "fixed_part": fixed_part,
                        "moving_part": moving_part,
                        "maximum_overlap_mm3": maximum,
                        "allowed_interference_mm3": allowed_interference_mm3,
                        "sample_index": maximum_index,
                        "samples": samples,
                    },
                    "Change the insertion path or mating geometry. Do not rely on force unless the joint is designed and checked as an interference or snap fit.",
                )
            )
    return AssemblyCheckResult(
        name=feature,
        part_a=fixed_part,
        part_b=moving_part,
        check_type="insertion-path",
        measurements={
            "approach_distance_mm": approach_distance_mm,
            "samples": samples,
            "maximum_overlap_mm3": maximum,
            "allowed_interference_mm3": allowed_interference_mm3,
        },
        findings=findings,
    )


def check_fastener_stack(
    *,
    screw_length_mm: float,
    through_stack_mm: float,
    required_engagement_mm: float,
    available_thread_depth_mm: float,
    protected_clearance_mm: float = 0.5,
    feature: str = "fastener-stack",
) -> list[Finding]:
    """Check reach, engagement, and breakthrough for one fastener path."""
    values = (
        screw_length_mm,
        through_stack_mm,
        required_engagement_mm,
        available_thread_depth_mm,
        protected_clearance_mm,
    )
    if min(values) < 0 or screw_length_mm == 0 or available_thread_depth_mm == 0:
        raise ValueError("Fastener stack dimensions must be positive or zero where permitted.")
    available_engagement = screw_length_mm - through_stack_mm
    findings: list[Finding] = []
    evidence = {
        "screw_length_mm": screw_length_mm,
        "through_stack_mm": through_stack_mm,
        "available_engagement_mm": available_engagement,
        "required_engagement_mm": required_engagement_mm,
        "available_thread_depth_mm": available_thread_depth_mm,
        "protected_clearance_mm": protected_clearance_mm,
    }
    if available_engagement < required_engagement_mm:
        findings.append(
            Finding(
                "fastener.engagement.insufficient",
                Severity.BLOCKING,
                "The screw does not reach the required thread engagement.",
                feature,
                evidence,
                "Use a longer screw or reduce the through-stack thickness.",
            )
        )
    if available_engagement > available_thread_depth_mm - protected_clearance_mm:
        findings.append(
            Finding(
                "fastener.breakthrough-risk",
                Severity.BLOCKING,
                "The screw can bottom out or enter the protected volume.",
                feature,
                evidence,
                "Use a shorter screw, increase blind depth, or add a hard stop.",
            )
        )
    return findings


def check_tool_access(
    *,
    tool_diameter_mm: float,
    access_diameter_mm: float,
    approach_length_mm: float,
    obstruction_distance_mm: float,
    feature: str = "tool-access",
) -> list[Finding]:
    """Check a straight driver or installation-tool approach envelope."""
    if min(tool_diameter_mm, access_diameter_mm, approach_length_mm, obstruction_distance_mm) < 0:
        raise ValueError("Tool access dimensions must not be negative.")
    findings: list[Finding] = []
    if access_diameter_mm < tool_diameter_mm:
        findings.append(
            Finding(
                "assembly.tool-diameter-blocked",
                Severity.BLOCKING,
                "The access opening is smaller than the tool envelope.",
                feature,
                {"tool_diameter_mm": tool_diameter_mm, "access_diameter_mm": access_diameter_mm},
                "Increase the opening or change the fastener orientation.",
            )
        )
    if obstruction_distance_mm < approach_length_mm:
        findings.append(
            Finding(
                "assembly.tool-approach-blocked",
                Severity.BLOCKING,
                "An obstruction intersects the required straight tool approach.",
                feature,
                {
                    "approach_length_mm": approach_length_mm,
                    "obstruction_distance_mm": obstruction_distance_mm,
                },
                "Move the obstruction, shorten the tool path, or change the assembly sequence.",
            )
        )
    return findings


def check_linear_travel(
    *,
    required_travel_mm: float,
    available_travel_mm: float,
    end_clearance_mm: float,
    feature: str = "linear-travel",
) -> list[Finding]:
    """Check that a slider or latch can complete its required travel."""
    if min(required_travel_mm, available_travel_mm, end_clearance_mm) < 0:
        raise ValueError("Travel dimensions must not be negative.")
    if available_travel_mm - end_clearance_mm < required_travel_mm:
        return [
            Finding(
                "assembly.travel.insufficient",
                Severity.BLOCKING,
                "The moving part cannot complete its required travel.",
                feature,
                {
                    "required_travel_mm": required_travel_mm,
                    "available_travel_mm": available_travel_mm,
                    "end_clearance_mm": end_clearance_mm,
                },
                "Increase the travel envelope or reduce the required motion.",
            )
        ]
    return []
