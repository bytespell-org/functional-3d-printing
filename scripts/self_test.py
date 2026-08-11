#!/usr/bin/env python3
"""Run dependency-free regression tests for the functional FDM skill."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from functional_fdm import (  # noqa: E402
    AssemblyCheckResult,
    AssemblyGraph,
    BridgeSpec,
    DesignBundle,
    DesignDelta,
    DesignDecision,
    DesignPart,
    DesignRecord,
    FitProfile,
    InterfaceSpec,
    PrintPlan,
    ReviewAnnotation,
    FunctionalRequirement,
    Severity,
    check_assembly_interference,
    check_fastener_stack,
    check_linear_travel,
    check_tool_access,
)
from functional_fdm.primitives import cantilever_snap, fit_pair, magnet_pocket  # noqa: E402
from functional_fdm.validation import classify_overhang  # noqa: E402
from run_model import resolve_output_plan  # noqa: E402


TETRAHEDRON = """solid test
facet normal 0 0 -1
 outer loop
  vertex 0 0 0
  vertex 0 1 0
  vertex 1 0 0
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex 0 0 0
  vertex 1 0 0
  vertex 0 0 1
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex 0 0 0
  vertex 0 0 1
  vertex 0 1 0
 endloop
endfacet
facet normal 1 1 1
 outer loop
  vertex 1 0 0
  vertex 0 1 0
  vertex 0 0 1
 endloop
endfacet
endsolid test
"""


def box_facets(minimum: tuple[float, float, float], maximum: tuple[float, float, float]) -> str:
    x0, y0, z0 = minimum
    x1, y1, z1 = maximum
    vertices = (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    )
    faces = (
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    )
    lines: list[str] = []
    for face in faces:
        lines.extend(["facet normal 0 0 0", " outer loop"])
        lines.extend(
            f"  vertex {vertices[index][0]} {vertices[index][1]} {vertices[index][2]}"
            for index in face
        )
        lines.extend([" endloop", "endfacet"])
    return "\n".join(lines)


def run(command: list[str], expected: int) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"Expected exit {expected}, got {result.returncode}: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> int:
    scripts = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="functional-fdm-self-test-") as temporary:
        root = Path(temporary)
        stl = root / "tetrahedron.stl"
        stl.write_text(TETRAHEDRON, encoding="utf-8")
        run([sys.executable, str(scripts / "audit_stl.py"), str(stl), "--expected-components", "1", "--strict"], 0)
        run([sys.executable, str(scripts / "audit_stl.py"), str(stl), "--expected-components", "2", "--strict"], 1)

        unsupported = root / "unsupported-horizontal.stl"
        unsupported.write_text(
            "solid unsupported\n"
            + box_facets((0, 0, 0), (2, 2, 2))
            + "\n"
            + box_facets((0, 0, 4), (10, 10, 5))
            + "\nendsolid unsupported\n",
            encoding="utf-8",
        )
        audit_result = run(
            [
                sys.executable,
                str(scripts / "audit_stl.py"),
                str(unsupported),
                "--expected-components",
                "2",
                "--fail-on-unsupported-horizontal",
            ],
            1,
        )
        if "requires an explicit bridge or removable-support plan" not in audit_result.stdout:
            raise RuntimeError("Unsupported horizontal geometry did not produce the expected failure.")

        profile = FitProfile(printer="test", material="PETG")
        profile_path = root / "profile.json"
        profile.save(profile_path)
        loaded = FitProfile.load(profile_path)
        if loaded.mating_dimensions(6, "close-sliding") != profile.mating_dimensions(6, "close-sliding"):
            raise RuntimeError("FitProfile round-trip changed dimensions.")
        fit = fit_pair(6, "press", profile)
        if not any(finding.code == "fit.uncalibrated-critical" for finding in fit.findings):
            raise RuntimeError("Uncalibrated press fit did not request a small fit test.")

        snap = cantilever_snap(engagement_mm=2, beam_length_mm=6, beam_width_mm=3, root_thickness_mm=2, material="PLA", layer_orientation="across-layers")
        if not any(finding.severity >= Severity.BLOCKING for finding in snap.findings):
            raise RuntimeError("Unsafe cantilever did not produce a blocking finding.")
        magnet = magnet_pocket(diameter_mm=6, thickness_mm=2, profile=profile, polarity="unknown")
        if not magnet.blocked:
            raise RuntimeError("Unknown paired-magnet polarity did not block the feature.")

        assessment = classify_overhang(90, 20, profile, precision_surface=True)
        if assessment.classification != "IMPOSSIBLE_IN_CURRENT_ORIENTATION":
            raise RuntimeError("Horizontal unsupported roof was not rejected.")

        safe_print_plan = PrintPlan(
            support_mode="none",
            reviewed=True,
            review_evidence="The exported test orientation has no horizontal roof.",
        )
        if safe_print_plan.validate():
            raise RuntimeError("A complete support-free print plan produced findings.")
        false_bridge = PrintPlan(
            support_mode="none",
            reviewed=True,
            review_evidence="Reviewed the candidate region.",
            bridges=(
                BridgeSpec("one-ended-lip", 3.0, 10.0, False, "One wall supports the lip."),
            ),
        )
        if not any(f.code == "print-plan.bridge.not-bridge" for f in false_bridge.validate()):
            raise RuntimeError("A one-ended cantilever was accepted as a bridge.")

        graph = AssemblyGraph({"a", "b"})
        graph.add_interface(InterfaceSpec("joint", "a", "b", "slide", {}, "close-sliding", (1, 0, 0), True, 10))
        if graph.validate():
            raise RuntimeError("Valid assembly metadata produced findings.")

        if check_fastener_stack(screw_length_mm=6, through_stack_mm=2, required_engagement_mm=3, available_thread_depth_mm=5, protected_clearance_mm=0.5):
            raise RuntimeError("Valid fastener stack produced findings.")
        if not check_fastener_stack(screw_length_mm=10, through_stack_mm=2, required_engagement_mm=3, available_thread_depth_mm=5, protected_clearance_mm=0.5):
            raise RuntimeError("Fastener breakthrough was not detected.")
        if check_tool_access(tool_diameter_mm=5, access_diameter_mm=6, approach_length_mm=20, obstruction_distance_mm=25):
            raise RuntimeError("Valid tool approach produced findings.")
        if not check_linear_travel(required_travel_mm=20, available_travel_mm=18, end_clearance_mm=1):
            raise RuntimeError("Insufficient travel was not detected.")

        class FakeSolid:
            def __init__(self, volume: float):
                self.volume = volume

            def Volume(self) -> float:
                return self.volume

        class FakeIntersection:
            def __init__(self, volume: float):
                self.volume = volume

            def Solids(self) -> list[FakeSolid]:
                return [FakeSolid(self.volume)] if self.volume > 0 else []

        class FakeGeometry:
            def __init__(self, overlap: float):
                self.overlap = overlap

            def intersect(self, other: object) -> FakeIntersection:
                return FakeIntersection(self.overlap)

        collision = check_assembly_interference(
            part_a="base",
            geometry_a=FakeGeometry(165.89),
            part_b="lid",
            geometry_b=FakeGeometry(0),
        )
        if collision.passed or not any(f.code == "assembly.unintended-interference" for f in collision.findings):
            raise RuntimeError("Final-state assembly interference was not blocked.")

        multipart_graph = AssemblyGraph({"base", "lid"})
        multipart_graph.add_interface(InterfaceSpec("lid", "base", "lid", "sliding collar", {}, "loose", (0, 0, -1), True, 10))
        unchecked = DesignBundle(
            "unchecked",
            [
                DesignPart("base", None, "flat", "PETG", print_plan=safe_print_plan),
                DesignPart("lid", None, "flat", "PETG", print_plan=safe_print_plan),
            ],
            multipart_graph,
        )
        missing_checks = unchecked.validate_metadata()
        if len([f for f in missing_checks if f.code == "assembly.missing-geometry-check"]) != 2:
            raise RuntimeError("Multipart design without final-state and insertion-path checks was not blocked.")

        complete_checks = [
            AssemblyCheckResult("final", "base", "lid", "final-state-interference"),
            AssemblyCheckResult("path", "base", "lid", "insertion-path"),
        ]
        checked = DesignBundle(
            "checked",
            [
                DesignPart("base", None, "flat", "PETG", print_plan=safe_print_plan),
                DesignPart("lid", None, "flat", "PETG", print_plan=safe_print_plan),
            ],
            multipart_graph,
            assembly_checks=complete_checks,
        )
        if any(f.code == "assembly.missing-geometry-check" for f in checked.validate_metadata()):
            raise RuntimeError("Complete assembly geometry checks were not recognized.")

        record = DesignRecord(
            intent="Test a removable functional cover.",
            known_dimensions_mm={"width": 42.0},
            requirements=[
                FunctionalRequirement(
                    "retains",
                    "The cover remains attached during normal use.",
                    status="physically-tested",
                    verification_method="Ten-cycle small mechanism test",
                    evidence=("small test revision 2 passed",),
                )
            ],
            assumptions=["0.4 mm nozzle"],
            available_materials=["PLA"],
            decisions=[
                DesignDecision(
                    "Use a sliding cover.",
                    "It needs no additional hardware.",
                    status="user-approved",
                    alternatives=("screw cover",),
                    approval_basis="User approved the sliding cover only.",
                )
            ],
            prototype_stage="small-fit-test",
            test_plan=["Measure insertion force and complete ten cycles."],
            iterations=[{"revision": 1, "result": "passed", "observation": "Ten cycles completed."}],
        )
        recorded = DesignBundle(
            "recorded",
            [DesignPart("base", None, "flat", "PLA", print_plan=safe_print_plan)],
            AssemblyGraph({"base"}),
            design_record=record,
        )
        manifest = recorded.as_manifest()
        if manifest["design_record"]["prototype_stage"] != "small-fit-test":
            raise RuntimeError("Design record was not included in the manifest.")
        if manifest["design_record"]["iterations"][0]["result"] != "passed":
            raise RuntimeError("Physical iteration history was not included in the manifest.")
        if any(f.code.startswith("design-record.") for f in recorded.validate_metadata()):
            raise RuntimeError("A complete design record produced findings.")

        annotation = ReviewAnnotation(
            "usb-c-opening",
            "USB-C opening center",
            (10.0, 0.0, 4.0),
            part="base",
            description="Center datum for connector alignment.",
        )
        delta = DesignDelta(
            "usb-c-opening",
            "center_z",
            5.0,
            4.0,
            "mm",
            "-Z toward base",
            "Align the opening with the connector center.",
        )
        review_bundle = DesignBundle(
            "reviewed-change",
            [DesignPart("base", None, "flat", "PLA", print_plan=safe_print_plan)],
            AssemblyGraph({"base"}),
            design_record=record,
            review_annotations=[annotation],
            design_deltas=[delta],
        )
        review_manifest = review_bundle.as_manifest()
        if review_manifest["design_deltas"][0]["delta"] != -1.0:
            raise RuntimeError("The design delta did not preserve the signed change.")
        if any(f.code.startswith("review.") for f in review_bundle.validate_metadata()):
            raise RuntimeError("Complete review metadata produced findings.")
        bad_delta = DesignDelta(
            "missing-feature",
            "center_z",
            5.0,
            4.0,
            "mm",
            "-Z",
            "Test missing annotation validation.",
        )
        if not any(
            finding.code == "review.delta.unknown-annotation"
            for finding in bad_delta.validate({annotation.annotation_id})
        ):
            raise RuntimeError("A design delta without a known annotation was accepted.")

        vague_approval = DesignRecord(
            intent="Reject vague or unsupported approval records.",
            decisions=[DesignDecision("Use magnets.", "Fast access.", status="accepted")],
        )
        vague_findings = vague_approval.validate()
        if not any(f.code == "design-record.invalid-decision-status" for f in vague_findings):
            raise RuntimeError("The vague accepted decision status was not blocked.")

        missing_basis = DesignRecord(
            intent="Require scoped approval evidence.",
            decisions=[DesignDecision("Use magnets.", "Fast access.", status="user-approved")],
        )
        basis_findings = missing_basis.validate()
        if not any(f.code == "design-record.missing-approval-basis" for f in basis_findings):
            raise RuntimeError("A user-approved decision without an approval basis was not blocked.")

        preview = root / "preview"
        run(
            [
                sys.executable,
                str(scripts / "build_preview.py"),
                "--output",
                str(preview),
                "--part",
                f"test={stl}:#4f7cac",
                "--annotation",
                json.dumps(annotation.as_dict()),
                "--delta",
                json.dumps(delta.as_dict()),
            ],
            0,
        )
        for required in ("index.html", "viewer.js", "styles.css", "manifest.json"):
            if not (preview / required).is_file():
                raise RuntimeError(f"Preview is missing {required}.")
        preview_manifest = json.loads((preview / "manifest.json").read_text(encoding="utf-8"))
        if preview_manifest["annotations"][0]["id"] != "usb-c-opening":
            raise RuntimeError("Preview annotation data is missing.")
        if preview_manifest["deltas"][0]["review_status"] != "proposed":
            raise RuntimeError("Preview design delta data is missing.")

        log = root / "iterations.jsonl"
        run([
            sys.executable, str(scripts / "record_iteration.py"),
            "--log", str(log), "--part", "test", "--stage", "small-test",
            "--defect", "binds", "--evidence", "measured", "--cause", "clearance",
            "--change", "increase clearance", "--result", "improved", "--promotion", "candidate",
        ], 0)
        record = json.loads(log.read_text(encoding="utf-8").strip())
        if record["schema_version"] != 1 or record["promotion"] != "candidate":
            raise RuntimeError("Iteration record content is invalid.")

        run([sys.executable, str(SKILL_ROOT / "benchmarks" / "run_benchmarks.py")], 0)
        run([sys.executable, str(scripts / "validate_portability.py"), str(SKILL_ROOT)], 0)

        project = root / "project"
        source = project / "cad" / "closure" / "model.py"
        source.parent.mkdir(parents=True)
        source.write_text("def build(): pass\n", encoding="utf-8")
        run(["git", "init", "-q", str(project)], 0)
        default_plan = resolve_output_plan(source)
        expected_default = project / "build" / "functional-fdm" / "closure"
        if default_plan.path != expected_default or default_plan.mode != "project-default":
            raise RuntimeError("Project output did not use the generic build directory.")
        if default_plan.git_ignored or default_plan.git_tracked or not default_plan.warnings:
            raise RuntimeError("Unignored project output did not produce the expected warning.")

        (project / ".gitignore").write_text("/build/functional-fdm/\n", encoding="utf-8")
        ignored_plan = resolve_output_plan(source)
        if not ignored_plan.git_ignored or ignored_plan.warnings:
            raise RuntimeError("Ignored project output produced an incorrect Git warning.")

        tracked_output = project / "tracked-output"
        tracked_output.mkdir()
        (tracked_output / "assembly.step").write_text("generated\n", encoding="utf-8")
        run(["git", "-C", str(project), "add", "tracked-output/assembly.step"], 0)
        tracked_plan = resolve_output_plan(source, tracked_output)
        if not tracked_plan.git_tracked or not tracked_plan.warnings:
            raise RuntimeError("Tracked output was not detected.")

        explicit = root / "chosen-output"
        explicit_plan = resolve_output_plan(source, explicit)
        if explicit_plan.path != explicit.resolve() or explicit_plan.mode != "explicit":
            raise RuntimeError("Explicit output directory was not preserved.")

        standalone = root / "standalone" / "part.py"
        standalone.parent.mkdir()
        standalone.write_text("def build(): pass\n", encoding="utf-8")
        temporary_plan = resolve_output_plan(standalone)
        if temporary_plan.mode != "temporary" or not temporary_plan.temporary:
            raise RuntimeError("Standalone model did not use a temporary output directory.")

    print(json.dumps({"ok": True, "tests": 23}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
