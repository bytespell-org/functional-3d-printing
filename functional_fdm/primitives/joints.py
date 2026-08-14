"""Snap, rail, and dovetail primitives with mechanical checks."""

from __future__ import annotations

import math

from ..materials import material_profile
from ..model import FeatureResult, Finding, Severity
from ..profile import FitProfile


def cantilever_snap(
    *,
    engagement_mm: float,
    beam_length_mm: float,
    beam_width_mm: float,
    root_thickness_mm: float,
    tip_thickness_mm: float | None = None,
    root_radius_mm: float | None = None,
    material: str = "PETG",
    reusable: bool = True,
    layer_orientation: str = "in-plane",
    entry_angle_deg: float = 35,
    retention_angle_deg: float = 80,
    name: str = "cantilever-snap",
) -> FeatureResult:
    if min(engagement_mm, beam_length_mm, beam_width_mm, root_thickness_mm) <= 0:
        raise ValueError("Snap dimensions must be positive.")
    if layer_orientation not in ("in-plane", "across-layers"):
        raise ValueError("layer_orientation must be in-plane or across-layers.")
    tip = root_thickness_mm * 0.6 if tip_thickness_mm is None else tip_thickness_mm
    radius = root_thickness_mm * 0.5 if root_radius_mm is None else root_radius_mm
    if not 0 < tip <= root_thickness_mm:
        raise ValueError("tip_thickness_mm must be positive and no larger than root thickness.")
    material_data = material_profile(material)
    base_strain = 1.5 * root_thickness_mm * engagement_mm / (beam_length_mm**2)
    orientation_factor = 1.0 if layer_orientation == "in-plane" else 1.7
    estimated_strain = base_strain * orientation_factor
    allowable = (
        material_data.reusable_snap_strain if reusable else material_data.one_time_snap_strain
    )
    findings: list[Finding] = []
    ratio = estimated_strain / allowable
    if ratio > 1:
        findings.append(
            Finding(
                "snap.strain.excessive",
                Severity.BLOCKING,
                f"Estimated root strain {estimated_strain:.3%} exceeds the conservative {allowable:.3%} limit.",
                name,
                {"estimated_strain": estimated_strain, "allowable_strain": allowable},
                "Lengthen or taper the beam, reduce engagement, change material, or change orientation.",
            )
        )
    elif ratio > 0.75:
        findings.append(
            Finding(
                "snap.strain.low-margin",
                Severity.LIKELY_FAILURE,
                f"Estimated snap strain uses {ratio:.0%} of the conservative limit.",
                name,
                recommendation="Increase margin and print an isolated cycle test after approval.",
            )
        )
    if radius < 0.5 * root_thickness_mm:
        findings.append(
            Finding(
                "snap.root-radius.small",
                Severity.LIKELY_FAILURE,
                "The snap root radius is less than half the beam root thickness.",
                name,
                recommendation="Increase the root radius when adjacent geometry permits it.",
            )
        )
    if layer_orientation == "across-layers":
        findings.append(
            Finding(
                "snap.orientation.weak-z",
                Severity.LIKELY_FAILURE,
                "The snap flexes across layer adhesion.",
                name,
                recommendation="Rotate the part, split the assembly, or redesign the flexure in the XY plane.",
            )
        )
    if beam_width_mm < 3 * root_thickness_mm:
        findings.append(
            Finding(
                "snap.beam.narrow",
                Severity.CAUTION,
                "The snap beam is narrow relative to its thickness.",
                name,
                recommendation="Increase width if the assembly has space.",
            )
        )
    if retention_angle_deg >= 85 and reusable:
        findings.append(
            Finding(
                "snap.release.tool-required",
                Severity.INFO,
                "The steep retention face can require a release tool.",
                name,
            )
        )

    geometry = None
    try:
        import cadquery as cq

        beam = (
            cq.Workplane("YZ")
            .rect(beam_width_mm, root_thickness_mm)
            .workplane(offset=beam_length_mm)
            .rect(beam_width_mm, tip)
            .loft(combine=True)
        )
        entry_run = engagement_mm / max(math.tan(math.radians(entry_angle_deg)), 0.1)
        hook_profile = (
            cq.Workplane("XZ")
            .moveTo(beam_length_mm - max(entry_run, tip), tip / 2)
            .lineTo(beam_length_mm, tip / 2)
            .lineTo(beam_length_mm, tip / 2 + engagement_mm)
            .lineTo(beam_length_mm - max(entry_run, tip), tip / 2)
            .close()
            .extrude(beam_width_mm / 2, both=True)
        )
        geometry = beam.union(hook_profile)
    except ImportError:
        findings.append(
            Finding(
                "dependency.cadquery-missing",
                Severity.BLOCKING,
                "CadQuery is required to build snap geometry.",
                name,
            )
        )

    return FeatureResult(
        name,
        "cantilever-snap",
        geometry,
        dimensions={
            "engagement_mm": engagement_mm,
            "beam_length_mm": beam_length_mm,
            "beam_width_mm": beam_width_mm,
            "root_thickness_mm": root_thickness_mm,
            "tip_thickness_mm": tip,
            "root_radius_mm": radius,
            "estimated_root_strain": round(estimated_strain, 6),
            "conservative_allowable_strain": allowable,
            "entry_angle_deg": entry_angle_deg,
            "retention_angle_deg": retention_angle_deg,
        },
        assumptions={
            "material": material_data.name,
            "reusable": reusable,
            "layer_orientation": layer_orientation,
            "model": "small-deflection rectangular cantilever; FDM orientation factor applied",
        },
        findings=findings,
        print_notes=[
            "Print the beam length and flex direction in the build-plane when possible.",
            "Print an isolated engagement and cycle test before the full assembly when this interface controls success.",
        ],
    )


def dovetail_pair(
    width_mm: float,
    height_mm: float,
    length_mm: float,
    profile: FitProfile,
    *,
    angle_deg: float = 60,
    fit: str = "close-sliding",
    name: str = "dovetail",
) -> FeatureResult:
    if min(width_mm, height_mm, length_mm) <= 0:
        raise ValueError("Dovetail dimensions must be positive.")
    gap = profile.gap_per_side(fit)  # type: ignore[arg-type]
    findings: list[Finding] = []
    if not profile.characterized:
        findings.append(
            Finding(
                "fit.dovetail.uncalibrated",
                Severity.CAUTION,
                "The dovetail uses an uncharacterized sliding clearance.",
                name,
                recommendation="After approval, print a short dovetail fit test first.",
            )
        )
    geometry = None
    try:
        import cadquery as cq

        shoulder = height_mm / max(math.tan(math.radians(angle_deg)), 0.1)
        male_profile = [(-width_mm / 2, 0), (width_mm / 2, 0), (width_mm / 2 - shoulder, height_mm), (-width_mm / 2 + shoulder, height_mm)]
        female_width = width_mm + 2 * gap
        female_profile = [(-female_width / 2, -gap), (female_width / 2, -gap), (female_width / 2 - shoulder, height_mm + gap), (-female_width / 2 + shoulder, height_mm + gap)]
        male = cq.Workplane("XZ").polyline(male_profile).close().extrude(length_mm)
        female_cutter = cq.Workplane("XZ").polyline(female_profile).close().extrude(length_mm)
        geometry = {"male": male, "female_cutter": female_cutter}
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "dovetail",
        geometry,
        dimensions={"width_mm": width_mm, "height_mm": height_mm, "length_mm": length_mm, "angle_deg": angle_deg, "gap_per_side_mm": gap},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Keep the sliding faces off support interfaces.", "Add a lead-in and an end stop in the parent design."],
    )


def sliding_rail_pair(
    rail_width_mm: float,
    rail_height_mm: float,
    length_mm: float,
    profile: FitProfile,
    *,
    fit: str = "close-sliding",
    name: str = "sliding-rail",
) -> FeatureResult:
    if min(rail_width_mm, rail_height_mm, length_mm) <= 0:
        raise ValueError("Rail dimensions must be positive.")
    gap = profile.gap_per_side(fit)  # type: ignore[arg-type]
    geometry = None
    findings: list[Finding] = []
    try:
        import cadquery as cq
        male = cq.Workplane("XY").box(rail_width_mm, length_mm, rail_height_mm)
        channel = cq.Workplane("XY").box(rail_width_mm + 2 * gap, length_mm, rail_height_mm + gap)
        geometry = {"male": male, "channel_cutter": channel}
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    if not profile.characterized:
        findings.append(Finding("fit.rail.uncalibrated", Severity.CAUTION, "The rail clearance is not calibrated.", name, recommendation="After approval, print a short rail fit test."))
    return FeatureResult(
        name,
        "sliding-rail",
        geometry,
        dimensions={"rail_width_mm": rail_width_mm, "rail_height_mm": rail_height_mm, "length_mm": length_mm, "gap_per_side_mm": gap},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Add a lead-in, travel stop, and debris relief in the parent design."],
    )


def annular_snap_pair(
    *,
    nominal_diameter_mm: float,
    bead_height_mm: float,
    bead_width_mm: float,
    wall_thickness_mm: float,
    profile: FitProfile,
    material: str = "PETG",
    reusable: bool = True,
    split_ring: bool = False,
    name: str = "annular-snap",
) -> FeatureResult:
    """Create a bead and groove cutter with a conservative hoop-strain screen."""
    if min(nominal_diameter_mm, bead_height_mm, bead_width_mm, wall_thickness_mm) <= 0:
        raise ValueError("Annular snap dimensions must be positive.")
    material_data = material_profile(material)
    radial_clearance = profile.snap_clearance_per_side_mm
    required_expansion = max(0.0, bead_height_mm - radial_clearance)
    estimated_hoop_strain = required_expansion / (nominal_diameter_mm / 2)
    if split_ring:
        estimated_hoop_strain *= 0.55
    allowable = (
        material_data.reusable_snap_strain if reusable else material_data.one_time_snap_strain
    )
    findings: list[Finding] = []
    if estimated_hoop_strain > allowable:
        findings.append(
            Finding(
                "snap.annular-strain.excessive",
                Severity.BLOCKING,
                "The estimated annular expansion exceeds the conservative material limit.",
                name,
                {
                    "estimated_hoop_strain": estimated_hoop_strain,
                    "allowable_strain": allowable,
                    "split_ring": split_ring,
                },
                "Reduce bead engagement, add relief slots, increase diameter, or use another joint.",
            )
        )
    if not profile.characterized:
        findings.append(
            Finding(
                "snap.annular-clearance.uncalibrated",
                Severity.CAUTION,
                "The annular snap clearance is not calibrated.",
                name,
                recommendation="After approval, print a short ring-and-groove fit test.",
            )
        )
    geometry = None
    try:
        import cadquery as cq

        bead_radius = nominal_diameter_mm / 2
        bead = (
            cq.Workplane("XZ")
            .moveTo(bead_radius, 0)
            .rect(bead_height_mm, bead_width_mm)
            .revolve(360, (0, 0), (0, 1))
        )
        groove = (
            cq.Workplane("XZ")
            .moveTo(bead_radius + radial_clearance, 0)
            .rect(bead_height_mm + 2 * radial_clearance, bead_width_mm + 2 * radial_clearance)
            .revolve(360, (0, 0), (0, 1))
        )
        geometry = {"bead": bead, "groove_cutter": groove}
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "annular-snap",
        geometry,
        dimensions={
            "nominal_diameter_mm": nominal_diameter_mm,
            "bead_height_mm": bead_height_mm,
            "bead_width_mm": bead_width_mm,
            "wall_thickness_mm": wall_thickness_mm,
            "radial_clearance_mm": radial_clearance,
            "estimated_hoop_strain": round(estimated_hoop_strain, 6),
        },
        assumptions={"material": material_data.name, "reusable": reusable, "split_ring": split_ring},
        findings=findings,
        print_notes=["Keep the bead and groove flanks off support.", "Test insertion, retention, and cycle life with a short mechanism test."],
    )


def u_snap(
    *,
    engagement_mm: float,
    beam_length_mm: float,
    beam_width_mm: float,
    root_thickness_mm: float,
    inside_spacing_mm: float,
    material: str = "PETG",
    reusable: bool = True,
    layer_orientation: str = "in-plane",
    name: str = "u-snap",
) -> FeatureResult:
    """Create two opposed cantilevers joined by a root bridge."""
    if inside_spacing_mm <= 0:
        raise ValueError("inside_spacing_mm must be positive.")
    arm = cantilever_snap(
        engagement_mm=engagement_mm,
        beam_length_mm=beam_length_mm,
        beam_width_mm=beam_width_mm,
        root_thickness_mm=root_thickness_mm,
        material=material,
        reusable=reusable,
        layer_orientation=layer_orientation,
        name=f"{name}-arm",
    )
    geometry = None
    if arm.geometry is not None:
        try:
            import cadquery as cq

            offset = (inside_spacing_mm + beam_width_mm) / 2
            left = arm.geometry.translate((0, -offset, 0))
            right = arm.geometry.mirror("XZ").translate((0, offset, 0))
            bridge = cq.Workplane("XY").box(root_thickness_mm, inside_spacing_mm + 2 * beam_width_mm, root_thickness_mm)
            geometry = left.union(right).union(bridge)
        except ImportError:
            pass
    return FeatureResult(
        name,
        "u-snap",
        geometry,
        dimensions={**arm.dimensions, "inside_spacing_mm": inside_spacing_mm},
        assumptions={**arm.assumptions, "arms": 2},
        findings=list(arm.findings),
        print_notes=[*arm.print_notes, "Check that both arms can deflect without contacting enclosed hardware."],
    )


def tongue_and_groove_pair(
    *,
    tongue_width_mm: float,
    tongue_height_mm: float,
    length_mm: float,
    profile: FitProfile,
    fit: str = "locating",
    name: str = "tongue-and-groove",
) -> FeatureResult:
    if min(tongue_width_mm, tongue_height_mm, length_mm) <= 0:
        raise ValueError("Tongue-and-groove dimensions must be positive.")
    gap = profile.gap_per_side(fit)  # type: ignore[arg-type]
    findings: list[Finding] = []
    if not profile.characterized:
        findings.append(Finding("fit.tongue-groove.uncalibrated", Severity.CAUTION, "The locating fit is not calibrated.", name, recommendation="After approval, print a short edge fit test."))
    geometry = None
    try:
        import cadquery as cq

        tongue = cq.Workplane("XY").box(tongue_width_mm, length_mm, tongue_height_mm)
        groove = cq.Workplane("XY").box(tongue_width_mm + 2 * gap, length_mm, tongue_height_mm + gap)
        geometry = {"tongue": tongue, "groove_cutter": groove}
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "tongue-and-groove",
        geometry,
        dimensions={"tongue_width_mm": tongue_width_mm, "tongue_height_mm": tongue_height_mm, "length_mm": length_mm, "gap_per_side_mm": gap},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Add a lead-in and elephant-foot relief at the entry edge.", "Use this joint for alignment. Add separate retention when required."],
    )


def pin_hinge_pair(
    *,
    pin_diameter_mm: float,
    barrel_outer_diameter_mm: float,
    knuckle_length_mm: float,
    profile: FitProfile,
    axial_clearance_mm: float | None = None,
    printed_pin: bool = False,
    name: str = "pin-hinge",
) -> FeatureResult:
    if min(pin_diameter_mm, barrel_outer_diameter_mm, knuckle_length_mm) <= 0:
        raise ValueError("Hinge dimensions must be positive.")
    radial_wall = (barrel_outer_diameter_mm - pin_diameter_mm) / 2
    radial_gap = profile.close_sliding_per_side_mm
    axial_gap = profile.close_sliding_per_side_mm if axial_clearance_mm is None else axial_clearance_mm
    findings: list[Finding] = []
    if radial_wall < max(1.2, 3 * profile.nozzle_mm):
        findings.append(Finding("hinge.barrel-wall.thin", Severity.LIKELY_FAILURE, "The hinge barrel has little radial material.", name, recommendation="Increase barrel diameter or reduce pin diameter."))
    if printed_pin and pin_diameter_mm < 2 * profile.nozzle_mm:
        findings.append(Finding("hinge.printed-pin.fragile", Severity.LIKELY_FAILURE, "The printed pin is too small for the assumed nozzle.", name, recommendation="Use a metal pin or increase the pin diameter."))
    if not profile.characterized:
        findings.append(Finding("fit.hinge.uncalibrated", Severity.CAUTION, "The rotating clearance is not calibrated.", name, recommendation="After approval, print one hinge-knuckle fit test."))
    geometry = None
    try:
        import cadquery as cq

        barrel = cq.Workplane("YZ").circle(barrel_outer_diameter_mm / 2).circle(pin_diameter_mm / 2 + radial_gap).extrude(knuckle_length_mm)
        pin = cq.Workplane("YZ").circle(pin_diameter_mm / 2).extrude(3 * knuckle_length_mm + 2 * axial_gap)
        geometry = {"barrel": barrel, "pin": pin}
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "pin-hinge",
        geometry,
        dimensions={"pin_diameter_mm": pin_diameter_mm, "barrel_outer_diameter_mm": barrel_outer_diameter_mm, "knuckle_length_mm": knuckle_length_mm, "radial_gap_mm": radial_gap, "axial_clearance_mm": axial_gap},
        assumptions={**profile.assumptions(), "printed_pin": printed_pin},
        findings=findings,
        print_notes=["Check the complete swing envelope and pin insertion path.", "Orient barrels so repeated load does not split weak layer interfaces."],
    )


def living_hinge(
    *,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    material: str,
    expected_cycles: int,
    layer_orientation: str = "in-plane",
    name: str = "living-hinge",
) -> FeatureResult:
    if min(length_mm, width_mm, thickness_mm) <= 0 or expected_cycles < 1:
        raise ValueError("Living-hinge dimensions and cycles must be positive.")
    findings: list[Finding] = []
    material_name = material.upper()
    if material_name == "PLA" and expected_cycles > 5:
        findings.append(Finding("hinge.material.pla-fatigue", Severity.BLOCKING, "PLA is not a suitable default for this repeated living hinge.", name, recommendation="Use a separate pin hinge or a qualified flexible material."))
    if layer_orientation != "in-plane":
        findings.append(Finding("hinge.orientation.weak-z", Severity.BLOCKING, "The hinge flexes across layer adhesion.", name, recommendation="Rotate or split the part so flex occurs in the build-plane."))
    geometry = None
    try:
        import cadquery as cq

        geometry = cq.Workplane("XY").box(length_mm, width_mm, thickness_mm)
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "living-hinge",
        geometry,
        dimensions={"length_mm": length_mm, "width_mm": width_mm, "thickness_mm": thickness_mm, "expected_cycles": expected_cycles},
        assumptions={"material": material_name, "layer_orientation": layer_orientation, "qualification": "small physical test required"},
        findings=findings,
        print_notes=["Use a material-specific bend test before the assembly.", "Do not use injection-molded hinge dimensions without FDM qualification."],
    )
