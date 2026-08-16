#!/usr/bin/env python3
"""Run library regressions and validate the separate manual agent-eval catalog."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from functional_fdm import (  # noqa: E402
    AssemblyGraph,
    BridgeSpec,
    FitProfile,
    InterfaceSpec,
    PrintPlan,
    ReviewAnnotation,
    DesignDelta,
    Severity,
    check_assembly_insertion_path,
    check_assembly_interference,
    check_fastener_stack,
    check_linear_travel,
    check_rotational_motion_path,
    check_tool_access,
)
from functional_fdm.primitives import (  # noqa: E402
    annular_snap_pair,
    cantilever_snap,
    fit_coupon,
    fit_pair,
    heat_set_insert_hole,
    living_hinge,
    magnet_pocket,
    pcb_standoff,
    printed_thread_pair,
    pin_hinge_pair,
    self_tapping_boss,
    sliding_rail_pair,
    tongue_and_groove_pair,
)
from functional_fdm.validation import classify_overhang  # noqa: E402


def check_stable_output_reuse() -> tuple[bool, object]:
    model_source = '''
import os
import cadquery as cq
from functional_fdm import AssemblyGraph, DesignBundle, DesignPart, DesignRecord, PrintPlan, ReferenceComponent

PLAN = PrintPlan(support_mode="none", reviewed=True, review_evidence="Boxes sit flat on the bed.")
def build():
    if os.environ.get("OUTPUT_REUSE_REVISION") == "first":
        parts = [
            DesignPart("base", cq.Workplane("XY").box(10, 10, 2), "flat", "PLA", print_plan=PLAN),
            DesignPart("lid", cq.Workplane("XY").box(8, 8, 2).translate((15, 0, 0)), "flat", "PLA", print_plan=PLAN),
        ]
        references = [ReferenceComponent("board", cq.Workplane("XY").box(5, 5, 1), geometry_basis="nominal-envelope")]
    else:
        parts = [DesignPart("body", cq.Workplane("XY").box(12, 12, 3), "flat", "PLA", print_plan=PLAN)]
        references = []
    return DesignBundle(
        name="output-reuse",
        parts=parts,
        reference_components=references,
        assembly=AssemblyGraph({part.name for part in parts}),
        design_record=DesignRecord(intent="Exercise stable output reuse."),
    )
'''
    with tempfile.TemporaryDirectory(prefix="functional-fdm-output-reuse-") as temporary:
        root = Path(temporary)
        output = root / "output"
        model = root / "model.py"
        model.write_text(model_source, encoding="utf-8")
        command = [sys.executable, str(SKILL_ROOT / "scripts" / "run_model.py")]
        first_environment = dict(os.environ)
        first_environment["OUTPUT_REUSE_REVISION"] = "first"
        first_run = subprocess.run(
            [*command, str(model), "--output-dir", str(output)],
            check=False,
            text=True,
            capture_output=True,
            env=first_environment,
        )
        sentinel = output / "sentinel.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        second_run = subprocess.run(
            [*command, str(model), "--output-dir", str(output)],
            check=False,
            text=True,
            capture_output=True,
        )
        manifest = json.loads((output / "preview" / "manifest.json").read_text(encoding="utf-8"))
        current_names = [item["name"] for item in manifest["parts"]]
        obsolete = [
            output / "parts" / "base.stl",
            output / "parts" / "lid.stl",
            output / "reference-models" / "board.stl",
            output / "renders" / "base",
            output / "renders" / "lid",
        ]
        ok = (
            first_run.returncode == 0
            and second_run.returncode == 0
            and (output / "parts" / "body.stl").is_file()
            and sentinel.is_file()
            and not any(path.exists() for path in obsolete)
            and current_names == ["body"]
            and all((output / "preview" / item["file"]).is_file() for item in manifest["parts"])
        )
        return ok, {
            "first_exit": first_run.returncode,
            "second_exit": second_run.returncode,
            "current_parts": current_names,
            "obsolete_remaining": [str(path.relative_to(output)) for path in obsolete if path.exists()],
            "sentinel_preserved": sentinel.is_file(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", action="store_true", help="Require CadQuery/cq_warehouse geometry checks.")
    args = parser.parse_args()
    profile = FitProfile(printer="benchmark", material="PETG", characterized=False)
    results: list[dict[str, object]] = []

    eval_catalog_path = SKILL_ROOT / "benchmarks" / "eval-prompts.json"
    eval_catalog = json.loads(eval_catalog_path.read_text(encoding="utf-8"))
    eval_cases = eval_catalog.get("cases", [])
    eval_ids = [item.get("id") for item in eval_cases if isinstance(item, dict)]
    detail_paths = [
        item.get("details")
        for item in eval_cases
        if isinstance(item, dict) and item.get("details") is not None
    ]
    details_ok = all(
        isinstance(relative, str)
        and relative.startswith("benchmarks/cases/")
        and ".." not in Path(relative).parts
        and (SKILL_ROOT / relative).is_file()
        for relative in detail_paths
    )
    catalog_ok = (
        eval_catalog.get("schema_version") == 1
        and len(eval_ids) == len(eval_cases)
        and all(isinstance(identifier, str) and identifier for identifier in eval_ids)
        and len(set(eval_ids)) == len(eval_ids)
        and details_ok
        and all(
            isinstance(item.get("prompt"), str)
            and item["prompt"].strip()
            and isinstance(item.get("criteria"), list)
            and item["criteria"]
            for item in eval_cases
            if isinstance(item, dict)
        )
    )

    def blocked(feature: object) -> bool:
        findings = feature.findings
        if args.geometry:
            return any(finding.severity >= Severity.BLOCKING for finding in findings)
        return any(
            finding.severity >= Severity.BLOCKING
            and not finding.code.startswith("dependency.")
            and not finding.code.endswith(".library-error")
            for finding in findings
        )

    def case(identifier: str, condition: bool, evidence: object) -> None:
        results.append({"id": identifier, "ok": bool(condition), "evidence": evidence})

    snap = cantilever_snap(
        engagement_mm=0.6,
        beam_length_mm=20,
        beam_width_mm=7,
        root_thickness_mm=1.2,
        material="PETG",
        reusable=True,
        layer_orientation="in-plane",
    )
    graph = AssemblyGraph({"base", "lid"})
    graph.add_interface(InterfaceSpec("lid-snap", "base", "lid", "cantilever-snap", {"engagement_mm": 0.6}, "snap", (0, 0, -1), True, 100))
    case("snap-box", not blocked(snap) and not graph.validate(), snap.as_dict())

    boss = self_tapping_boss(pilot_diameter_mm=1.7, outer_diameter_mm=5.5, height_mm=7, profile=profile, screw_length_mm=6, floor_clearance_mm=1)
    standoff = pcb_standoff(height_mm=5, outer_diameter_mm=5.5, hole_diameter_mm=2.2, profile=profile)
    stack = check_fastener_stack(screw_length_mm=6, through_stack_mm=1.6, required_engagement_mm=3, available_thread_depth_mm=5, protected_clearance_mm=0.4)
    tool = check_tool_access(tool_diameter_mm=5, access_diameter_mm=6, approach_length_mm=20, obstruction_distance_mm=25)
    case("tiny-screw-enclosure", not blocked(boss) and not blocked(standoff) and not stack and not tool, {"boss": boss.as_dict(), "standoff": standoff.as_dict(), "stack": [item.as_dict() for item in stack], "tool": [item.as_dict() for item in tool]})

    unknown_polarity = magnet_pocket(diameter_mm=6, thickness_mm=2, profile=profile, retention="press-fit", polarity="unknown")
    marked_polarity = magnet_pocket(diameter_mm=6, thickness_mm=2, profile=profile, retention="adhesive", polarity="north-out")
    case("magnet-latch", blocked(unknown_polarity) and not blocked(marked_polarity), {"unknown": unknown_polarity.as_dict(), "marked": marked_polarity.as_dict()})

    rail = sliding_rail_pair(8, 3, 30, profile)
    travel = check_linear_travel(required_travel_mm=20, available_travel_mm=22, end_clearance_mm=1)
    case("slider", any(finding.code == "fit.rail.uncalibrated" for finding in rail.findings) and not travel, rail.as_dict())

    press = fit_pair(6, "press", profile)
    coupon = fit_coupon(6, profile)
    case("press-fit-shaft", any(finding.code == "fit.uncalibrated-critical" for finding in press.findings) and (coupon.geometry is not None or not args.geometry), {"fit": press.as_dict(), "coupon": coupon.as_dict()})

    thread = printed_thread_pair(major_diameter_mm=12, pitch_mm=1.5, length_mm=8, profile=profile, layer_height_mm=0.2)
    case("printed-threads", (not args.geometry) or (not blocked(thread) and thread.geometry is not None), thread.as_dict())

    weak_clip = cantilever_snap(engagement_mm=1.0, beam_length_mm=12, beam_width_mm=5, root_thickness_mm=2.0, material="PETG", reusable=True, layer_orientation="across-layers")
    case("cantilever-clip", any(finding.code == "snap.orientation.weak-z" for finding in weak_clip.findings), weak_clip.as_dict())

    if args.geometry:
        import cadquery as cq
        from cq_warehouse.fastener import HeatSetNut
        insert = HeatSetNut(size="M3-0.5-Standard", fastener_type="McMaster-Carr")
        target = cq.Workplane("XY").box(12, 12, 8).faces(">Z").workplane()
        insert_feature = heat_set_insert_hole(target, insert, profile, depth_mm=5)
        insert_ok = not blocked(insert_feature) and insert_feature.geometry is not None
        insert_evidence = insert_feature.as_dict()
    else:
        insert_ok = True
        insert_evidence = "Geometry check skipped. Use --geometry in the CadQuery environment."
    case("heat-set-insert", insert_ok, insert_evidence)

    roof = classify_overhang(90, 20, profile, is_bridge=False, precision_surface=True)
    one_ended_lip = PrintPlan(
        support_mode="none",
        reviewed=True,
        review_evidence="The lip is attached to one wall.",
        bridges=(BridgeSpec("capture-lip", 3.0, 20.0, False, "One wall supports the lip."),),
    )
    case(
        "support-avoidance",
        roof.classification == "IMPOSSIBLE_IN_CURRENT_ORIENTATION"
        and any(f.severity >= Severity.BLOCKING for f in roof.findings)
        and any(f.code == "print-plan.bridge.not-bridge" for f in one_ended_lip.validate()),
        {
            "classification": roof.classification,
            "findings": [f.as_dict() for f in roof.findings],
            "one_ended_lip": [f.as_dict() for f in one_ended_lip.validate()],
        },
    )

    track_roof = BridgeSpec(
        "bayonet-track-roof",
        8.0,
        2.0,
        True,
        "The exported upright track closes across two supported ends.",
        critical_surface=True,
    )
    case(
        "bayonet-track-roof",
        any(f.code == "print-plan.bridge.critical-surface" for f in track_roof.validate()),
        {"findings": [f.as_dict() for f in track_roof.validate()]},
    )

    annotation = ReviewAnnotation(
        "usb-c-opening",
        "USB-C opening center",
        (26.6, 0.0, 6.2),
        part="base",
    )
    delta = DesignDelta(
        "usb-c-opening",
        "center_z",
        7.2,
        6.2,
        "mm",
        "-Z toward base",
        "Align the opening with the connector center.",
    )
    case(
        "annotated-position-revision",
        not annotation.validate({"base"})
        and not delta.validate({"usb-c-opening"})
        and delta.as_dict()["delta"] == -1.0,
        {"annotation": annotation.as_dict(), "delta": delta.as_dict()},
    )

    if args.geometry:
        import cadquery as cq

        fixed = cq.Workplane("XY").box(10, 10, 10)
        colliding = cq.Workplane("XY").box(10, 10, 10).translate((5, 0, 0))
        clear = cq.Workplane("XY").box(10, 10, 10).translate((10.1, 0, 0))
        collision = check_assembly_interference(part_a="fixed", geometry_a=fixed, part_b="moving", geometry_b=colliding)
        final_clear = check_assembly_interference(part_a="fixed", geometry_a=fixed, part_b="moving", geometry_b=clear)
        path_clear = check_assembly_insertion_path(
            fixed_part="fixed",
            fixed_geometry=fixed,
            moving_part="moving",
            moving_geometry=clear,
            insertion_direction=(-1, 0, 0),
            approach_distance_mm=8,
        )
        path_blocker = cq.Workplane("XY").box(3, 10, 10).translate((14, 0, 0))
        path_blocked = check_assembly_insertion_path(
            fixed_part="path-blocker",
            fixed_geometry=path_blocker,
            moving_part="moving",
            moving_geometry=clear,
            insertion_direction=(-1, 0, 0),
            approach_distance_mm=8,
        )
        collision_ok = not collision.passed and final_clear.passed and path_clear.passed and not path_blocked.passed

        rotating_arm = cq.Workplane("XY").box(12, 2, 2).translate((6, 0, 0))
        clear_rotating_fixed = cq.Workplane("XY").box(2, 2, 2).translate((-5, -5, 0))
        blocked_rotating_fixed = cq.Workplane("XY").box(3, 3, 3).translate((0, 6, 0))
        rotational_clear = check_rotational_motion_path(
            fixed_part="clear-stop",
            fixed_geometry=clear_rotating_fixed,
            moving_part="arm",
            moving_geometry=rotating_arm,
            axis=(0, 0, 1),
            origin_mm=(0, 0, 0),
            start_angle_deg=0,
            end_angle_deg=90,
            samples=18,
        )
        rotational_blocked = check_rotational_motion_path(
            fixed_part="blocked-stop",
            fixed_geometry=blocked_rotating_fixed,
            moving_part="arm",
            moving_geometry=rotating_arm,
            axis=(0, 0, 1),
            origin_mm=(0, 0, 0),
            start_angle_deg=0,
            end_angle_deg=90,
            samples=18,
        )
        collision_evidence = {
            "collision": collision.as_dict(),
            "final_clear": final_clear.as_dict(),
            "path_clear": path_clear.as_dict(),
            "path_blocked": path_blocked.as_dict(),
        }
    else:
        collision_ok = True
        collision_evidence = "Geometry check skipped. Use --geometry in the CadQuery environment."
    case("assembly-interference", collision_ok, collision_evidence)
    if args.geometry:
        case(
            "rotational-motion-path",
            rotational_clear.passed and not rotational_blocked.passed,
            {"clear": rotational_clear.as_dict(), "blocked": rotational_blocked.as_dict()},
        )
    else:
        case("rotational-motion-path", True, "Geometry check skipped. Use --geometry in the CadQuery environment.")

    annular = annular_snap_pair(nominal_diameter_mm=50, bead_height_mm=0.5, bead_width_mm=1.2, wall_thickness_mm=1.8, profile=profile, split_ring=True)
    tongue = tongue_and_groove_pair(tongue_width_mm=2, tongue_height_mm=1.5, length_mm=20, profile=profile)
    hinge = pin_hinge_pair(pin_diameter_mm=2, barrel_outer_diameter_mm=6, knuckle_length_mm=8, profile=profile)
    living = living_hinge(length_mm=20, width_mm=8, thickness_mm=0.5, material="PLA", expected_cycles=100)
    mechanisms_ok = not blocked(annular) and not blocked(tongue) and not blocked(hinge) and blocked(living)
    if args.geometry:
        mechanisms_ok = mechanisms_ok and all(feature.geometry is not None for feature in (annular, tongue, hinge))
    case("joint-library", mechanisms_ok, {"annular": annular.as_dict(), "tongue": tongue.as_dict(), "hinge": hinge.as_dict(), "living_hinge_rejection": living.as_dict()})

    if args.geometry:
        reuse_ok, reuse_evidence = check_stable_output_reuse()
        case("stable-output-reuse", reuse_ok, reuse_evidence)

    failures = [result for result in results if not result["ok"]]
    print(json.dumps({
        "ok": not failures and catalog_ok,
        "regression_cases": results,
        "failures": failures,
        "agent_eval_catalog": {
            "path": str(eval_catalog_path.relative_to(SKILL_ROOT)),
            "valid": catalog_ok,
            "case_count": len(eval_cases),
            "executed": False,
            "note": "Prompts are a manual/future agent-evaluation catalog; this runner does not execute agents.",
        },
    }, indent=2))
    return 0 if not failures and catalog_ok else 1


if __name__ == "__main__":
    sys.exit(main())
