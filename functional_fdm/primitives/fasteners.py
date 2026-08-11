"""Fastener-aware CadQuery and cq_warehouse wrappers."""

from __future__ import annotations

from ..model import FeatureResult, Finding, Severity
from ..profile import FitProfile
from ..validation import check_hole, check_wall


def _warehouse_ready() -> tuple[object, object]:
    import cadquery as cq
    import cq_warehouse.extensions  # noqa: F401 - registers Workplane methods
    return cq, cq_warehouse.extensions


def clearance_hole(
    workplane: object,
    fastener: object,
    *,
    fit: str = "Normal",
    depth_mm: float | None = None,
    countersunk: bool = True,
    name: str = "clearance-hole",
) -> FeatureResult:
    findings: list[Finding] = []
    try:
        _warehouse_ready()
        diameter = float(getattr(fastener, "clearance_hole_diameters")[fit])
        geometry = workplane.clearanceHole(  # type: ignore[attr-defined]
            fastener=fastener,
            fit=fit,
            depth=depth_mm,
            counterSunk=countersunk,
        )
    except (ImportError, AttributeError, KeyError, ValueError) as error:
        return FeatureResult(
            name,
            "clearance-hole",
            findings=[
                Finding(
                    "fastener.library-error",
                    Severity.BLOCKING,
                    f"Could not create a standards-based clearance hole: {error}",
                    name,
                    recommendation="Install CadQuery and the pinned cq_warehouse revision. Specify a supported fastener object.",
                )
            ],
        )
    return FeatureResult(
        name,
        "clearance-hole",
        geometry,
        dimensions={"hole_diameter_mm": diameter, "depth_mm": depth_mm or "through", "fit": fit, "countersunk": countersunk},
        assumptions={"dimension_source": "cq_warehouse fastener standards table", "fastener": str(fastener)},
        findings=findings,
        print_notes=["Check screw-head and driver clearance in the complete assembly."],
    )


def captive_nut_hole(
    workplane: object,
    nut: object,
    *,
    fit: str = "Normal",
    depth_mm: float | None = None,
    name: str = "captive-nut",
) -> FeatureResult:
    try:
        _warehouse_ready()
        geometry = workplane.clearanceHole(  # type: ignore[attr-defined]
            fastener=nut,
            fit=fit,
            depth=depth_mm,
            captiveNut=True,
        )
    except (ImportError, AttributeError, KeyError, ValueError) as error:
        return FeatureResult(name, "captive-nut", findings=[Finding("fastener.library-error", Severity.BLOCKING, str(error), name)])
    return FeatureResult(
        name,
        "captive-nut",
        geometry,
        dimensions={"fit": fit, "depth_mm": depth_mm or "through"},
        assumptions={"dimension_source": "cq_warehouse", "nut": str(nut)},
        print_notes=["Add an insertion path and a stop. Check that the nut cannot rotate or escape under tightening."],
    )


def heat_set_insert_hole(
    workplane: object,
    insert: object,
    profile: FitProfile,
    *,
    fit: str = "Normal",
    depth_mm: float | None = None,
    installation_side: str = "top",
    name: str = "heat-set-insert",
) -> FeatureResult:
    findings: list[Finding] = []
    if installation_side not in ("top", "bottom", "side"):
        raise ValueError("installation_side must be top, bottom, or side.")
    try:
        _warehouse_ready()
        compensation = profile.hole_diameter_compensation_mm / 2
        geometry = workplane.insertHole(  # type: ignore[attr-defined]
            fastener=insert,
            fit=fit,
            depth=depth_mm,
            manufacturingCompensation=compensation,
        )
    except (ImportError, AttributeError, KeyError, ValueError) as error:
        return FeatureResult(name, "heat-set-insert", findings=[Finding("insert.library-error", Severity.BLOCKING, str(error), name)])
    if not profile.characterized:
        findings.append(
            Finding(
                "insert.uncalibrated-compensation",
                Severity.CAUTION,
                "Insert-hole manufacturing compensation is not calibrated.",
                name,
                recommendation="After approval, print one small insert-boss test with the actual insert and installation tool.",
            )
        )
    return FeatureResult(
        name,
        "heat-set-insert",
        geometry,
        dimensions={"fit": fit, "depth_mm": depth_mm or "library default", "installation_side": installation_side, "radial_compensation_mm": compensation},
        assumptions={"dimension_source": "cq_warehouse HeatSetNut", **profile.assumptions()},
        findings=findings,
        print_notes=["Provide installation-tool clearance and bottom relief for displaced plastic.", "Do not place the insert pocket against a thin unsupported wall."],
    )


def heat_set_insert_boss(
    *,
    insert: object,
    boss_outer_diameter_mm: float,
    boss_height_mm: float,
    profile: FitProfile,
    fit: str = "Normal",
    installation_side: str = "top",
    name: str = "heat-set-insert-boss",
) -> FeatureResult:
    """Create a boss and cut it with cq_warehouse HeatSetNut geometry."""
    if min(boss_outer_diameter_mm, boss_height_mm) <= 0:
        raise ValueError("Boss dimensions must be positive.")
    try:
        import cadquery as cq

        blank = cq.Workplane("XY").circle(boss_outer_diameter_mm / 2).extrude(boss_height_mm)
        result = heat_set_insert_hole(
            blank.faces(">Z").workplane(),
            insert,
            profile,
            fit=fit,
            depth_mm=boss_height_mm,
            installation_side=installation_side,
            name=name,
        )
        result.feature_type = "heat-set-insert-boss"
        insert_outer_diameter = float(getattr(insert, "nut_diameter"))
        radial_wall = (boss_outer_diameter_mm - insert_outer_diameter) / 2
        result.dimensions.update({
            "boss_outer_diameter_mm": boss_outer_diameter_mm,
            "boss_height_mm": boss_height_mm,
            "insert_outer_diameter_mm": insert_outer_diameter,
            "radial_wall_mm": radial_wall,
        })
        result.findings.extend(check_wall(radial_wall, profile, name))
        result.print_notes.append("Add a root fillet or gusset where the boss joins the parent part.")
        return result
    except ImportError:
        return FeatureResult(name, "heat-set-insert-boss", findings=[Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name)])


def self_tapping_boss(
    *,
    pilot_diameter_mm: float,
    outer_diameter_mm: float,
    height_mm: float,
    profile: FitProfile,
    screw_length_mm: float,
    floor_clearance_mm: float,
    name: str = "self-tapping-boss",
) -> FeatureResult:
    if min(pilot_diameter_mm, outer_diameter_mm, height_mm, screw_length_mm) <= 0:
        raise ValueError("Boss dimensions must be positive.")
    radial_wall = (outer_diameter_mm - pilot_diameter_mm) / 2
    findings = check_wall(radial_wall, profile, name) + check_hole(pilot_diameter_mm, profile, name)
    if outer_diameter_mm <= pilot_diameter_mm:
        findings.append(Finding("boss.invalid-diameters", Severity.BLOCKING, "Boss OD is not larger than the pilot hole.", name))
    usable_depth = min(height_mm, screw_length_mm)
    if screw_length_mm > height_mm + floor_clearance_mm:
        findings.append(
            Finding(
                "boss.screw-breakthrough",
                Severity.BLOCKING,
                "The screw can exit the boss or enter the protected envelope.",
                name,
                {"screw_length_mm": screw_length_mm, "height_mm": height_mm, "floor_clearance_mm": floor_clearance_mm},
                "Use a shorter screw, a taller boss, or a controlled blind depth.",
            )
        )
    geometry = None
    try:
        import cadquery as cq
        geometry = cq.Workplane("XY").circle(outer_diameter_mm / 2).circle(pilot_diameter_mm / 2).extrude(height_mm)
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "self-tapping-boss",
        geometry,
        dimensions={"pilot_diameter_mm": pilot_diameter_mm, "outer_diameter_mm": outer_diameter_mm, "height_mm": height_mm, "radial_wall_mm": radial_wall, "usable_thread_depth_mm": usable_depth},
        assumptions={"pilot_source": "user or screw manufacturer measurement", **profile.assumptions()},
        findings=findings,
        print_notes=["Add a root fillet and gusset when the boss joins a wall.", "Use a torque-limited assembly test."],
    )


def pcb_standoff(
    *,
    height_mm: float,
    outer_diameter_mm: float,
    hole_diameter_mm: float,
    profile: FitProfile,
    board_clearance_mm: float = 0.5,
    name: str = "pcb-standoff",
) -> FeatureResult:
    if min(height_mm, outer_diameter_mm, hole_diameter_mm) <= 0:
        raise ValueError("Standoff dimensions must be positive.")
    radial_wall = (outer_diameter_mm - hole_diameter_mm) / 2
    findings = check_wall(radial_wall, profile, name) + check_hole(hole_diameter_mm, profile, name)
    if radial_wall <= 0:
        findings.append(Finding("standoff.invalid-diameters", Severity.BLOCKING, "Standoff OD is not larger than the hole.", name))
    geometry = None
    try:
        import cadquery as cq
        geometry = cq.Workplane("XY").circle(outer_diameter_mm / 2).circle(hole_diameter_mm / 2).extrude(height_mm)
    except ImportError:
        findings.append(Finding("dependency.cadquery-missing", Severity.BLOCKING, "CadQuery is required.", name))
    return FeatureResult(
        name,
        "pcb-standoff",
        geometry,
        dimensions={"height_mm": height_mm, "outer_diameter_mm": outer_diameter_mm, "hole_diameter_mm": hole_diameter_mm, "radial_wall_mm": radial_wall, "board_clearance_mm": board_clearance_mm},
        assumptions=profile.assumptions(),
        findings=findings,
        print_notes=["Check screw-head, component, trace, and driver clearance against the real PCB envelope."],
    )


def printed_thread_pair(
    *,
    major_diameter_mm: float,
    pitch_mm: float,
    length_mm: float,
    profile: FitProfile,
    layer_height_mm: float = 0.2,
    clearance_per_side_mm: float | None = None,
    hand: str = "right",
    name: str = "printed-thread-pair",
) -> FeatureResult:
    """Create FDM-adjusted ISO thread solids with explicit radial clearance."""
    if min(major_diameter_mm, pitch_mm, length_mm, layer_height_mm) <= 0:
        raise ValueError("Thread dimensions must be positive.")
    if hand not in ("right", "left"):
        raise ValueError("hand must be right or left.")
    clearance = (
        profile.close_sliding_per_side_mm
        if clearance_per_side_mm is None
        else clearance_per_side_mm
    )
    findings: list[Finding] = []
    if pitch_mm < 4 * layer_height_mm:
        findings.append(
            Finding(
                "thread.pitch.too-fine",
                Severity.LIKELY_FAILURE,
                "Thread pitch is less than four planned layers.",
                name,
                {"pitch_mm": pitch_mm, "layer_height_mm": layer_height_mm},
                "Use a coarser pitch, lower layer height, or metal hardware.",
            )
        )
    if major_diameter_mm < 6 and profile.nozzle_mm >= 0.4:
        findings.append(
            Finding(
                "thread.small-for-fdm",
                Severity.CAUTION,
                "This thread is small for direct FDM printing with the assumed nozzle.",
                name,
                recommendation="Use a heat-set insert or print a short thread-pair test first.",
            )
        )
    if not profile.characterized:
        findings.append(
            Finding(
                "thread.clearance.uncalibrated",
                Severity.CAUTION,
                "Male/female thread clearance is not calibrated.",
                name,
                recommendation="Print a short male/female thread-pair test.",
            )
        )
    geometry = None
    try:
        from cq_warehouse.thread import IsoThread

        external_major = major_diameter_mm - 2 * clearance
        internal_major = major_diameter_mm + 2 * clearance
        if external_major <= 0:
            raise ValueError("Clearance removes the external thread.")
        external = IsoThread(
            major_diameter=external_major,
            pitch=pitch_mm,
            length=length_mm,
            external=True,
            hand=hand,
            end_finishes=("chamfer", "fade"),
        )
        internal = IsoThread(
            major_diameter=internal_major,
            pitch=pitch_mm,
            length=length_mm,
            external=False,
            hand=hand,
            end_finishes=("chamfer", "fade"),
        )
        geometry = {"external_thread": external, "internal_thread_cutter": internal}
    except (ImportError, ValueError) as error:
        findings.append(
            Finding(
                "thread.library-error",
                Severity.BLOCKING,
                f"Could not create cq_warehouse thread geometry: {error}",
                name,
            )
        )
    return FeatureResult(
        name,
        "printed-thread-pair",
        geometry,
        dimensions={
            "nominal_major_diameter_mm": major_diameter_mm,
            "pitch_mm": pitch_mm,
            "length_mm": length_mm,
            "radial_clearance_mm": clearance,
            "layer_height_mm": layer_height_mm,
        },
        assumptions={"thread_profile": "ISO 60 degree via cq_warehouse", "hand": hand, **profile.assumptions()},
        findings=findings,
        print_notes=[
            "Print a short pair before the full part.",
            "Keep the lead-in clean and avoid support on thread flanks.",
            "Use coarse threads for repeated printed assembly when possible.",
        ],
    )
