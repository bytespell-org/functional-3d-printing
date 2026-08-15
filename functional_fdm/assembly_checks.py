"""Semantic checks for assembly paths, hardware stacks, and service access."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

from .model import AssemblyCheckResult, Finding, Severity


@dataclass(frozen=True)
class MotionPose:
    """One deterministic pose relative to the moving geometry's modeled state."""

    translation_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    rotation_deg: float = 0.0
    rotation_origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    label: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "translation_mm": list(self.translation_mm),
            "rotation_axis": list(self.rotation_axis),
            "rotation_deg": self.rotation_deg,
            "rotation_origin_mm": list(self.rotation_origin_mm),
            "label": self.label,
        }


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


def _pose_geometry(geometry: Any, pose: MotionPose) -> Any:
    if len(pose.translation_mm) != 3 or len(pose.rotation_axis) != 3 or len(pose.rotation_origin_mm) != 3:
        raise ValueError("Motion poses require XYZ translation, rotation axis, and rotation origin values.")
    transformed = geometry
    if abs(pose.rotation_deg) > 1e-12:
        axis_length = math.sqrt(sum(value * value for value in pose.rotation_axis))
        if axis_length <= 1e-12:
            raise ValueError("A rotating motion pose requires a nonzero axis.")
        import cadquery as cq

        start = cq.Vector(*pose.rotation_origin_mm)
        end = cq.Vector(*(
            pose.rotation_origin_mm[index] + pose.rotation_axis[index]
            for index in range(3)
        ))
        transformed = transformed.rotate(start, end, pose.rotation_deg)
    if any(abs(value) > 1e-12 for value in pose.translation_mm):
        transformed = _translate(transformed, pose.translation_mm)
    return transformed


def check_sampled_motion_path(
    *,
    fixed_part: str,
    fixed_geometry: Any,
    moving_part: str,
    moving_geometry: Any,
    poses: list[MotionPose] | tuple[MotionPose, ...],
    allowed_interference_mm3: float = 0.01,
    feature: str = "sampled-motion-path",
    path_kind: str = "sampled",
) -> AssemblyCheckResult:
    """Check caller-supplied poses; this is deterministic sampling, not motion planning."""
    if not poses:
        raise ValueError("A sampled motion path requires at least one pose.")
    if allowed_interference_mm3 < 0:
        raise ValueError("Allowed interference must not be negative.")
    maximum = 0.0
    maximum_index = 0
    maximum_pose = poses[0]
    findings: list[Finding] = []
    try:
        for index, pose in enumerate(poses):
            moved = _pose_geometry(moving_geometry, pose)
            overlap = _intersection_volume_mm3(fixed_geometry, moved)
            if overlap > maximum:
                maximum = overlap
                maximum_index = index
                maximum_pose = pose
    except Exception as error:
        maximum = math.nan
        findings.append(
            Finding(
                "assembly.motion-path-check-failed",
                Severity.BLOCKING,
                "The sampled motion path could not be measured.",
                feature,
                {"error": str(error), "path_kind": path_kind},
                "Repair the geometry or poses and rerun the sampled path check.",
            )
        )
    else:
        if maximum > allowed_interference_mm3:
            findings.append(
                Finding(
                    "assembly.motion-path-blocked",
                    Severity.BLOCKING,
                    f"The sampled {path_kind} path reaches {maximum:.3f} mm^3 of solid overlap.",
                    feature,
                    {
                        "fixed_part": fixed_part,
                        "moving_part": moving_part,
                        "path_kind": path_kind,
                        "maximum_overlap_mm3": maximum,
                        "allowed_interference_mm3": allowed_interference_mm3,
                        "sample_index": maximum_index,
                        "sample_count": len(poses),
                        "pose": maximum_pose.as_dict(),
                    },
                    "Change the geometry or sampled motion. Add samples where the path can change direction or clearance rapidly.",
                )
            )
    return AssemblyCheckResult(
        name=feature,
        part_a=fixed_part,
        part_b=moving_part,
        check_type="sampled-motion-path",
        measurements={
            "path_kind": path_kind,
            "sample_count": len(poses),
            "maximum_overlap_mm3": maximum,
            "maximum_sample_index": maximum_index,
            "maximum_pose": maximum_pose.as_dict(),
            "allowed_interference_mm3": allowed_interference_mm3,
        },
        findings=findings,
    )


def check_rotational_motion_path(
    *,
    fixed_part: str,
    fixed_geometry: Any,
    moving_part: str,
    moving_geometry: Any,
    axis: tuple[float, float, float],
    origin_mm: tuple[float, float, float],
    start_angle_deg: float,
    end_angle_deg: float,
    samples: int = 12,
    allowed_interference_mm3: float = 0.01,
    feature: str = "rotational-motion-path",
) -> AssemblyCheckResult:
    """Sample one rotation around a fixed axis; compound motion needs explicit poses."""
    if samples < 2:
        raise ValueError("Rotational motion requires at least two angular intervals.")
    angular_step = (end_angle_deg - start_angle_deg) / samples
    poses = tuple(
        MotionPose(
            rotation_axis=axis,
            rotation_origin_mm=origin_mm,
            rotation_deg=start_angle_deg + angular_step * index,
            label=f"{start_angle_deg + angular_step * index:.6g} deg",
        )
        for index in range(samples + 1)
    )
    result = check_sampled_motion_path(
        fixed_part=fixed_part,
        fixed_geometry=fixed_geometry,
        moving_part=moving_part,
        moving_geometry=moving_geometry,
        poses=poses,
        allowed_interference_mm3=allowed_interference_mm3,
        feature=feature,
        path_kind="rotational",
    )
    result.check_type = "rotational-motion-path"
    result.measurements.update({
        "start_angle_deg": start_angle_deg,
        "end_angle_deg": end_angle_deg,
        "angular_step_deg": angular_step,
        "samples": samples,
    })
    return result


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


def check_access_envelope(
    *,
    envelope_name: str,
    envelope_geometry: Any,
    part_geometries: dict[str, Any],
    required_parts: list[str] | tuple[str, ...] | set[str],
    allowed_interference_mm3: float = 0.01,
    feature: str = "service-access-envelope",
) -> list[AssemblyCheckResult]:
    """Check one plug, cable, tool, or service envelope against every required part.

    ``required_parts`` is intentionally separate from ``part_geometries`` so an
    omitted retainer or cover becomes a blocking result instead of silently
    shrinking the validation matrix.
    """
    if allowed_interference_mm3 < 0:
        raise ValueError("Allowed interference must not be negative.")
    names = tuple(dict.fromkeys(required_parts))
    if not names:
        raise ValueError("At least one required printed part must be named.")

    results: list[AssemblyCheckResult] = []
    for part_name in names:
        check_name = f"{feature}:{part_name}"
        findings: list[Finding] = []
        if part_name not in part_geometries:
            overlap = math.nan
            findings.append(
                Finding(
                    "assembly.access-envelope-part-missing",
                    Severity.BLOCKING,
                    "A required printed part is missing from the access-envelope check.",
                    check_name,
                    {
                        "envelope": envelope_name,
                        "missing_part": part_name,
                        "required_parts": list(names),
                        "provided_parts": sorted(part_geometries),
                    },
                    "Add the missing printed-part geometry and rerun the complete access matrix.",
                )
            )
        else:
            try:
                overlap = _intersection_volume_mm3(part_geometries[part_name], envelope_geometry)
            except Exception as error:
                overlap = math.nan
                findings.append(
                    Finding(
                        "assembly.access-envelope-check-failed",
                        Severity.BLOCKING,
                        "The access envelope intersection could not be measured.",
                        check_name,
                        {"envelope": envelope_name, "part": part_name, "error": str(error)},
                        "Repair the geometry or placement and rerun the complete access matrix.",
                    )
                )
            else:
                if overlap > allowed_interference_mm3:
                    findings.append(
                        Finding(
                            "assembly.access-envelope-blocked",
                            Severity.BLOCKING,
                            f"The {envelope_name} envelope overlaps {part_name} by {overlap:.3f} mm^3.",
                            check_name,
                            {
                                "envelope": envelope_name,
                                "part": part_name,
                                "overlap_mm3": overlap,
                                "allowed_interference_mm3": allowed_interference_mm3,
                            },
                            "Open the full service path through this part or change the assembly architecture.",
                        )
                    )
        results.append(
            AssemblyCheckResult(
                name=check_name,
                part_a=part_name,
                part_b=envelope_name,
                check_type="access-envelope-clearance",
                measurements={
                    "overlap_mm3": overlap,
                    "allowed_interference_mm3": allowed_interference_mm3,
                },
                findings=findings,
            )
        )
    return results


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
    """Sample straight translation ending at the modeled state; not curved or compound motion."""
    magnitude = math.sqrt(sum(value * value for value in insertion_direction))
    if magnitude <= 1e-12:
        raise ValueError("Insertion direction must not be zero.")
    if approach_distance_mm <= 0 or samples < 2 or allowed_interference_mm3 < 0:
        raise ValueError("Approach distance and sample count must be positive; allowed interference must not be negative.")
    direction = tuple(value / magnitude for value in insertion_direction)
    linear_step = approach_distance_mm / samples
    poses = tuple(
        MotionPose(
            translation_mm=tuple(
                -value * approach_distance_mm * (1.0 - index / samples)
                for value in direction
            ),
            label=f"linear sample {index}/{samples}",
        )
        for index in range(samples + 1)
    )
    result = check_sampled_motion_path(
        fixed_part=fixed_part,
        fixed_geometry=fixed_geometry,
        moving_part=moving_part,
        moving_geometry=moving_geometry,
        poses=poses,
        allowed_interference_mm3=allowed_interference_mm3,
        feature=feature,
        path_kind="linear insertion",
    )
    result.check_type = "insertion-path"
    result.measurements.update({
        "approach_distance_mm": approach_distance_mm,
        "linear_step_mm": linear_step,
        "samples": samples,
    })
    result.findings = [
        replace(
            finding,
            code={
                "assembly.motion-path-blocked": "assembly.insertion-path-blocked",
                "assembly.motion-path-check-failed": "assembly.insertion-check-failed",
            }.get(finding.code, finding.code),
        )
        for finding in result.findings
    ]
    return result


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
