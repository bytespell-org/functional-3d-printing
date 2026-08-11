"""Semantic FDM manufacturability checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import Finding, Severity
from .profile import FitProfile


OverhangClass = Literal[
    "SAFE",
    "LIKELY_SELF_SUPPORTING",
    "MARGINAL",
    "SUPPORT_LIKELY",
    "IMPOSSIBLE_IN_CURRENT_ORIENTATION",
]


@dataclass(frozen=True)
class OverhangAssessment:
    classification: OverhangClass
    findings: tuple[Finding, ...]


def check_wall(thickness_mm: float, profile: FitProfile, feature: str = "wall") -> list[Finding]:
    if thickness_mm <= 0:
        return [Finding("dfm.wall.nonpositive", Severity.BLOCKING, "Wall thickness is not positive.", feature)]
    lines = thickness_mm / profile.nozzle_mm
    if lines < 1.8:
        return [
            Finding(
                "dfm.wall.too-thin",
                Severity.LIKELY_FAILURE,
                f"The {feature} is only {lines:.2f} nozzle widths thick.",
                feature,
                {"thickness_mm": thickness_mm, "nozzle_mm": profile.nozzle_mm},
                "Increase thickness or use a smaller nozzle.",
            )
        ]
    if lines < 3:
        return [
            Finding(
                "dfm.wall.light",
                Severity.CAUTION,
                f"The {feature} is {lines:.2f} nozzle widths thick.",
                feature,
                recommendation="Use more wall thickness on a load path.",
            )
        ]
    return []


def check_hole(diameter_mm: float, profile: FitProfile, feature: str = "hole") -> list[Finding]:
    if diameter_mm <= 0:
        return [Finding("dfm.hole.nonpositive", Severity.BLOCKING, "Hole diameter is not positive.", feature)]
    if diameter_mm < profile.nozzle_mm:
        return [
            Finding(
                "dfm.hole.below-nozzle",
                Severity.LIKELY_FAILURE,
                f"The {feature} diameter is smaller than the nozzle diameter.",
                feature,
                {"diameter_mm": diameter_mm, "nozzle_mm": profile.nozzle_mm},
                "Use a smaller nozzle, make the hole larger, or drill after printing.",
            )
        ]
    if not profile.characterized and diameter_mm <= 3.0:
        return [
            Finding(
                "dfm.hole.uncalibrated-small",
                Severity.CAUTION,
                f"The small {feature} depends on an uncharacterized hole compensation.",
                feature,
                recommendation="Prepare a small hole fit test or plan to drill/ream the feature.",
            )
        ]
    return []


def classify_overhang(
    angle_from_vertical_deg: float,
    span_mm: float,
    profile: FitProfile,
    *,
    is_bridge: bool = False,
    precision_surface: bool = False,
) -> OverhangAssessment:
    if not 0 <= angle_from_vertical_deg <= 90:
        raise ValueError("angle_from_vertical_deg must be from 0 to 90.")
    findings: list[Finding] = []
    if is_bridge:
        if span_mm <= max(5.0, 12 * profile.nozzle_mm):
            classification: OverhangClass = "LIKELY_SELF_SUPPORTING"
        elif span_mm <= max(15.0, 35 * profile.nozzle_mm):
            classification = "MARGINAL"
        else:
            classification = "SUPPORT_LIKELY"
    elif angle_from_vertical_deg <= 45:
        classification = "SAFE"
    elif angle_from_vertical_deg <= 55:
        classification = "LIKELY_SELF_SUPPORTING"
    elif angle_from_vertical_deg <= 65:
        classification = "MARGINAL"
    elif angle_from_vertical_deg < 89:
        classification = "SUPPORT_LIKELY"
    else:
        classification = "IMPOSSIBLE_IN_CURRENT_ORIENTATION"

    if classification in ("MARGINAL", "SUPPORT_LIKELY"):
        findings.append(
            Finding(
                "dfm.overhang.risky",
                Severity.CAUTION if classification == "MARGINAL" else Severity.LIKELY_FAILURE,
                f"Feature is classified as {classification}.",
                evidence={
                    "angle_from_vertical_deg": angle_from_vertical_deg,
                    "span_mm": span_mm,
                    "is_bridge": is_bridge,
                },
                recommendation="Use a chamfer, arch, teardrop, open edge, split, or better orientation.",
            )
        )
    if classification == "IMPOSSIBLE_IN_CURRENT_ORIENTATION":
        findings.append(
            Finding(
                "dfm.overhang.impossible",
                Severity.BLOCKING,
                "A horizontal region starts without underlying material or a valid bridge.",
                recommendation="Redesign or change orientation before export.",
            )
        )
    if precision_surface and classification not in ("SAFE", "LIKELY_SELF_SUPPORTING"):
        findings.append(
            Finding(
                "dfm.support.precision-surface",
                Severity.LIKELY_FAILURE,
                "A precision mating surface is support-sensitive.",
                recommendation="Move the mating surface away from support or split the part.",
            )
        )
    return OverhangAssessment(classification, tuple(findings))


def check_tall_feature(
    height_mm: float, width_mm: float, profile: FitProfile, feature: str = "tower"
) -> list[Finding]:
    if min(height_mm, width_mm) <= 0:
        return [Finding("dfm.feature.nonpositive", Severity.BLOCKING, "Feature dimensions are invalid.", feature)]
    aspect = height_mm / width_mm
    if width_mm < 2 * profile.nozzle_mm and aspect > 4:
        return [
            Finding(
                "dfm.feature.fragile-tall",
                Severity.LIKELY_FAILURE,
                f"The {feature} is narrow and has an aspect ratio of {aspect:.1f}.",
                feature,
                recommendation="Add a rib, widen the feature, shorten it, or change orientation.",
            )
        ]
    return []
