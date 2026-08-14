"""Fit calculations and small physical fit tests."""

from __future__ import annotations

from ..model import FeatureResult, Finding, Severity
from ..profile import FitClass, FitProfile


def fit_pair(
    nominal_mm: float,
    fit: FitClass,
    profile: FitProfile,
    *,
    name: str = "fit-pair",
) -> FeatureResult:
    male, female = profile.mating_dimensions(nominal_mm, fit)
    findings: list[Finding] = []
    if not profile.characterized and fit in ("close-sliding", "locating", "friction", "press"):
        findings.append(
            Finding(
                "fit.uncalibrated-critical",
                Severity.CAUTION,
                f"The {fit} fit uses a conservative, uncharacterized profile.",
                name,
                {"nominal_mm": nominal_mm, "gap_per_side_mm": profile.gap_per_side(fit)},
                "Prepare a small fit test before the full part when this fit controls success.",
            )
        )
    return FeatureResult(
        name=name,
        feature_type=fit,
        dimensions={
            "nominal_mm": nominal_mm,
            "male_modeled_mm": round(male, 4),
            "female_modeled_mm": round(female, 4),
            "gap_per_side_mm": round(profile.gap_per_side(fit), 4),
        },
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Keep both the small fit test and final fit in the same XY/Z orientation."],
    )


def fit_coupon(
    nominal_mm: float,
    profile: FitProfile,
    *,
    length_mm: float = 8.0,
    kind: str = "cylindrical",
    name: str = "fit-test",
) -> FeatureResult:
    if kind not in ("cylindrical", "slot"):
        raise ValueError("kind must be cylindrical or slot.")
    gaps = profile.coupon_gaps()
    try:
        import cadquery as cq
    except ImportError as error:
        return FeatureResult(
            name,
            "small-fit-test",
            dimensions={"nominal_mm": nominal_mm, "gaps_per_side_mm": str(gaps)},
            assumptions=profile.assumptions(),
            findings=[
                Finding(
                    "dependency.cadquery-missing",
                    Severity.BLOCKING,
                    f"CadQuery is required to build small fit-test geometry: {error}",
                    name,
                )
            ],
        )

    spacing = nominal_mm + 8
    body = cq.Workplane("XY")
    for index, gap in enumerate(gaps):
        x = index * spacing
        block = cq.Workplane("XY").center(x, 0).box(spacing - 1, nominal_mm + 8, length_mm)
        if kind == "cylindrical":
            cutter = cq.Workplane("XY").center(x, 0).circle((nominal_mm + 2 * gap) / 2).extrude(length_mm + 2)
        else:
            cutter = cq.Workplane("XY").center(x, 0).rect(nominal_mm + 2 * gap, nominal_mm / 2).extrude(length_mm + 2)
        body = body.union(block.cut(cutter))
    return FeatureResult(
        name,
        "small-fit-test",
        geometry=body,
        dimensions={"nominal_mm": nominal_mm, "gaps_per_side_mm": str(gaps), "length_mm": length_mm},
        assumptions=profile.assumptions(),
        print_notes=["Mark each position with its gap before printing or include labels in the project model."],
    )
