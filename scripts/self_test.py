#!/usr/bin/env python3
"""Run dependency-free regression tests for the functional FDM skill."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
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
    ReferenceComponent,
    ReviewAnnotation,
    SourceRecord,
    FunctionalRequirement,
    Severity,
    check_access_envelope,
    check_assembly_interference,
    check_fastener_stack,
    check_linear_travel,
    check_tool_access,
)
from functional_fdm.primitives import cantilever_snap, fit_pair, magnet_pocket  # noqa: E402
from functional_fdm.validation import classify_overhang  # noqa: E402
from run_model import resolve_output_plan  # noqa: E402
from serve_preview import PreviewHandler, REVIEW_TOKEN_ENV, build_review_urls  # noqa: E402


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

        access_results = check_access_envelope(
            envelope_name="USB-C plug and cable",
            envelope_geometry=FakeGeometry(0),
            part_geometries={
                "body": FakeGeometry(0),
                "carrier": FakeGeometry(0),
                "retainer": FakeGeometry(81.123),
            },
            required_parts=("body", "carrier", "retainer"),
            feature="usb-service",
        )
        if len(access_results) != 3 or access_results[0].check_type != "access-envelope-clearance":
            raise RuntimeError("Access-envelope matrix did not cover every required part.")
        if access_results[0].findings or access_results[1].findings:
            raise RuntimeError("Clear access-envelope pairs produced findings.")
        if not any(f.code == "assembly.access-envelope-blocked" for f in access_results[2].findings):
            raise RuntimeError("A retainer blocking the USB envelope was not rejected.")

        omitted_access = check_access_envelope(
            envelope_name="USB-C plug and cable",
            envelope_geometry=FakeGeometry(0),
            part_geometries={"body": FakeGeometry(0), "carrier": FakeGeometry(0)},
            required_parts=("body", "carrier", "retainer"),
            feature="usb-service",
        )
        if not any(
            f.code == "assembly.access-envelope-part-missing"
            for f in omitted_access[2].findings
        ):
            raise RuntimeError("An omitted retainer silently shrank the USB clearance matrix.")

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
        if len([f for f in missing_checks if f.code in {"assembly.missing-geometry-check", "assembly.missing-motion-check"}]) != 2:
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
                    alternatives=("screw cover",),
                )
            ],
            prototype_stage="small-fit-test",
            test_plan=["Measure insertion force and complete ten cycles."],
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
        if any(f.code.startswith("design-record.") for f in recorded.validate_metadata()):
            raise RuntimeError("A complete design record produced findings.")
        if manifest["readiness"]["claimed"] != "concept-ready" or not manifest["readiness"]["concept_ready"]:
            raise RuntimeError("Concept readiness was not exported consistently.")

        invalid_record = DesignRecord(
            intent="Invalid evidence claims.",
            requirements=[
                FunctionalRequirement("claim", "Works physically.", status="physically-tested"),
                FunctionalRequirement("bad-status", "Uses a closed vocabulary.", status="done"),
            ],
            prototype_stage="prototype-ish",
            readiness="function-confirmed",
            sources=[
                SourceRecord("board", "not-an-absolute-url", retrieved_on="yesterday"),
                SourceRecord("board", "https://example.com/duplicate"),
            ],
        )
        invalid_bundle = DesignBundle(
            "invalid-record",
            [DesignPart("base", None, "flat", "PLA", print_plan=safe_print_plan)],
            AssemblyGraph({"base"}),
            design_record=invalid_record,
            reference_components=[ReferenceComponent("board", None, source_id="missing-source")],
        )
        invalid_codes = {finding.code for finding in invalid_bundle.validate_metadata()}
        expected_invalid = {
            "requirement.physical-claim-missing-evidence",
            "requirement.invalid-status",
            "design-record.invalid-prototype-stage",
            "source.invalid-url",
            "source.invalid-retrieval-date",
            "source.duplicate-id",
            "reference.unknown-source",
            "readiness.unsupported-claim",
        }
        if not expected_invalid <= invalid_codes:
            raise RuntimeError(f"Evidence/provenance validation missed: {sorted(expected_invalid - invalid_codes)}")

        sourced_record = DesignRecord(
            intent="Locate exact hardware.",
            requirements=[FunctionalRequirement("located", "Hardware is located.", status="cad-checked", verification_method="CAD envelope")],
            sources=[SourceRecord("board-drawing", "https://example.com/board.pdf", product_revision="V4", verified_features=("outline", "mounting holes"))],
        )
        sourced_bundle = DesignBundle(
            "sourced",
            [DesignPart("base", None, "flat", "PLA", print_plan=safe_print_plan)],
            AssemblyGraph({"base"}),
            design_record=sourced_record,
            reference_components=[ReferenceComponent("board", None, source_id="board-drawing")],
        )
        if any(f.severity >= Severity.BLOCKING for f in sourced_bundle.validate_metadata()):
            raise RuntimeError("Valid linked provenance produced a blocking finding.")
        if sourced_bundle.as_manifest()["reference_components"][0]["source_id"] != "board-drawing":
            raise RuntimeError("Reference provenance link was not exported.")

        confirmed_record = DesignRecord(
            intent="Confirm representative function.",
            requirements=[FunctionalRequirement(
                "holds-load",
                "The part holds the representative load.",
                status="function-confirmed",
                verification_method="Representative load test for 24 hours",
                evidence=("No deformation or release after 24 hours at the specified load.",),
            )],
            prototype_stage="final",
            readiness="function-confirmed",
        )
        confirmed_bundle = DesignBundle(
            "confirmed",
            [DesignPart("part", None, "flat", "PLA", print_plan=safe_print_plan)],
            AssemblyGraph({"part"}),
            design_record=confirmed_record,
        )
        confirmed_manifest = confirmed_bundle.as_manifest()
        if any(f.severity >= Severity.BLOCKING for f in confirmed_bundle.validate_metadata()) or not confirmed_manifest["readiness"]["function_confirmed"]:
            raise RuntimeError("Representative physical evidence did not support function-confirmed readiness.")

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
            reference_components=[
                ReferenceComponent(
                    "battery",
                    None,
                    position_mm=(1.0, 2.0, 3.0),
                    rotation_deg=(0.0, 0.0, 90.0),
                    nominal_size_mm=(25.0, 40.0, 10.0),
                )
            ],
        )
        review_manifest = review_bundle.as_manifest()
        if review_manifest["design_deltas"][0]["delta"] != -1.0:
            raise RuntimeError("The design delta did not preserve the signed change.")
        if any(f.code.startswith("review.") for f in review_bundle.validate_metadata()):
            raise RuntimeError("Complete review metadata produced findings.")
        if review_manifest["reference_components"][0]["role"] != "reference":
            raise RuntimeError("Reference component metadata was not included in the manifest.")
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

        incomplete_decision = DesignRecord(
            intent="Require a reason for every recorded choice.",
            decisions=[DesignDecision("Use magnets.", "")],
        )
        if not any(f.code == "design-record.incomplete-decision" for f in incomplete_decision.validate()):
            raise RuntimeError("A decision without a reason was accepted.")

        preview = root / "preview"
        preview_command = [
            sys.executable,
            str(scripts / "build_preview.py"),
            "--output",
            str(preview),
            "--part",
            f"test={stl}:#4f7cac",
            "--reference",
            json.dumps({
                    "name": "battery",
                    "path": str(stl),
                    "color": "#38bdf8",
                    "opacity": 0.38,
                    "position_mm": [1, 2, 3],
                    "rotation_deg": [0, 0, 90],
                    "nominal_size_mm": [25, 40, 10],
            }),
            "--annotation",
            json.dumps(annotation.as_dict()),
            "--progress-url",
            "../progress.json",
        ]
        run(preview_command, 0)
        for required in ("index.html", "manifest.json"):
            if not (preview / required).is_file():
                raise RuntimeError(f"Preview is missing {required}.")
        if not list((preview / "assets").glob("*.js")):
            raise RuntimeError("Preview is missing its compiled JavaScript bundle.")
        if not list((preview / "assets").glob("*.css")):
            raise RuntimeError("Preview is missing its compiled stylesheet.")
        preview_manifest = json.loads((preview / "manifest.json").read_text(encoding="utf-8"))
        if preview_manifest["annotations"][0]["id"] != "usb-c-opening":
            raise RuntimeError("Preview annotation data is missing.")
        if preview_manifest["progress_url"] != "../progress.json":
            raise RuntimeError("Preview does not point to the observable progress sidecar.")
        preview_part = preview_manifest["parts"][0]
        if not re.search(r"-[0-9a-f]{12}\.stl$", preview_part["file"]):
            raise RuntimeError("Preview model URL is not content-addressed.")
        if len(preview_part.get("sha256", "")) != 64:
            raise RuntimeError("Preview manifest is missing the full model digest.")
        if len(preview_manifest.get("revision", "")) != 64:
            raise RuntimeError("Preview manifest is missing its live revision digest.")
        preview_reference = preview_manifest["references"][0]
        if preview_reference["role"] != "reference" or preview_reference["position_mm"] != [1.0, 2.0, 3.0]:
            raise RuntimeError("Preview reference component transform is missing.")
        if not preview_reference["file"].startswith("models/ref-"):
            raise RuntimeError("Reference component was not isolated from printable part naming.")

        static_preview = root / "static-preview"
        run([
            sys.executable,
            str(scripts / "build_preview.py"),
            "--output",
            str(static_preview),
            "--part",
            f"test={stl}:#4f7cac",
        ], 0)
        static_manifest = json.loads((static_preview / "manifest.json").read_text(encoding="utf-8"))
        if static_manifest["progress_url"] is not None:
            raise RuntimeError("A static/simple preview enabled collaborative progress implicitly.")

        previous_revision = preview_manifest["revision"]
        previous_model = preview / preview_part["file"]
        stl.write_text(stl.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        run(preview_command, 0)
        refreshed_manifest = json.loads((preview / "manifest.json").read_text(encoding="utf-8"))
        if refreshed_manifest["revision"] == previous_revision:
            raise RuntimeError("A changed model did not publish a new preview revision.")
        refreshed_model = preview / refreshed_manifest["parts"][0]["file"]
        if not previous_model.is_file() or not refreshed_model.is_file():
            raise RuntimeError("Live preview publication removed a model needed by an open browser.")

        class HeaderProbe(PreviewHandler):
            def __init__(self, path: str):
                self.path = path
                self.request_version = "HTTP/1.1"
                self._headers_buffer: list[bytes] = []
                self.sent_headers: list[tuple[str, str]] = []

            def send_header(self, keyword: str, value: str) -> None:
                self.sent_headers.append((keyword, value))

            def flush_headers(self) -> None:
                pass

        for asset_path in (
            "/preview/",
            "/preview/manifest.json",
            "/preview/models/test.stl",
            "/preview/models/test.step",
        ):
            probe = HeaderProbe(asset_path)
            probe.end_headers()
            cache_headers = [
                value
                for keyword, value in probe.sent_headers
                if keyword.lower() == "cache-control"
            ]
            if cache_headers != [
                "no-store, no-cache, must-revalidate, max-age=0"
            ]:
                raise RuntimeError(
                    f"Preview asset did not disable browser caching: {asset_path}"
                )

        progress = root / "progress.json"
        progress_script = str(scripts / "update_progress.py")
        run([sys.executable, progress_script, "init", str(progress), "--title", "Test enclosure"], 0)
        run([
            sys.executable, progress_script, "progress", str(progress),
            "--summary", "Reviewing the enclosure.",
        ], 0)
        run([
            sys.executable, progress_script, "progress", str(progress),
            "--id", "visual-review", "--title", "Visual review",
            "--summary", "Ready for review.", "--overall-summary", "Checking cable clearance.",
        ], 0)
        run([
            sys.executable, progress_script, "comment-add", str(progress),
            "--id", "comment-usb-clearance", "--part", "test",
            "--position", "0.25", "0.5", "0.75",
            "--message", "Add a little more cable clearance.",
        ], 0)
        progress_data = json.loads(progress.read_text(encoding="utf-8"))
        if progress_data["schema_version"] != 2 or progress_data["progress"][0]["title"] != "Visual review" or progress_data["summary"] != "Checking cable clearance.":
            raise RuntimeError("Visible progress was not recorded.")
        comment = progress_data["comments"][0]
        if comment["position_mm"] != [0.25, 0.5, 0.75]:
            raise RuntimeError("Model review point was not preserved.")
        if "author" in comment or "updated_at" in comment:
            raise RuntimeError("Comment contains retired attribution or status metadata.")

        class DeleteProbe(PreviewHandler):
            def __init__(self, path: str, progress_path: Path, authorization: str = ""):
                self.path = path
                self.progress_path = progress_path
                self.manifest_path = root / "preview" / "manifest.json"
                self.mutation_token = "test-token"
                self.headers = {"Authorization": authorization}
                self.response: tuple[int, object] | None = None

            def send_json(self, status: int, value: object) -> None:
                self.response = (status, value)

        unauthenticated_delete = DeleteProbe("/api/review-comments/comment-usb-clearance", progress)
        unauthenticated_delete.do_DELETE()
        if unauthenticated_delete.response != (401, {"ok": False, "error": "A valid review session token is required."}):
            raise RuntimeError("Preview DELETE accepted an unauthenticated mutation.")

        delete_probe = DeleteProbe("/api/review-comments/comment-usb-clearance", progress, "Bearer test-token")
        delete_probe.do_DELETE()
        if delete_probe.response != (200, {"ok": True}):
            raise RuntimeError("Preview DELETE did not invoke comment removal.")
        if json.loads(progress.read_text(encoding="utf-8"))["comments"]:
            raise RuntimeError("Preview DELETE did not remove the addressed comment.")

        deterministic_token = "deterministic-review-token-for-tests"
        base_url_examples = ["http://127.0.0.1:12345/preview/"]
        generated_review_urls = build_review_urls(base_url_examples, deterministic_token)
        if generated_review_urls != [
            f"http://127.0.0.1:12345/preview/#token={deterministic_token}"
        ]:
            raise RuntimeError("Review URL generation did not use a browser fragment.")
        if any("?token=" in url for url in generated_review_urls) or any(
            deterministic_token in base or "token=" in base for base in base_url_examples
        ):
            raise RuntimeError("A base or generated review URL transports the token in a query string.")

        daemon_info = root / "daemon-info.json"
        daemon_pid = root / "daemon.pid"
        daemon_log = root / "daemon.log"
        daemon_environment = dict(os.environ)
        daemon_environment["PYTHONDONTWRITEBYTECODE"] = "1"
        daemon_environment[REVIEW_TOKEN_ENV] = deterministic_token
        daemon_result = subprocess.run(
            [
                sys.executable,
                str(scripts / "serve_preview.py"),
                str(preview),
                "--daemon",
                "--info-file",
                str(daemon_info),
                "--pid-file",
                str(daemon_pid),
                "--log-file",
                str(daemon_log),
            ],
            check=False,
            text=True,
            capture_output=True,
            env=daemon_environment,
        )
        if daemon_result.returncode:
            raise RuntimeError(f"Daemon preview failed: {daemon_result.stdout}\n{daemon_result.stderr}")
        daemon_output = json.loads(daemon_result.stdout)
        child_pid = int(daemon_output["pid"])

        def http_request(
            url: str,
            *,
            method: str = "GET",
            token: str = "",
            value: dict[str, object] | None = None,
        ) -> tuple[int, bytes]:
            headers: dict[str, str] = {}
            data = None
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if value is not None:
                headers["Content-Type"] = "application/json"
                data = json.dumps(value).encode("utf-8")
            request = urllib.request.Request(url, method=method, headers=headers, data=data)
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.read()

        try:
            persisted_text = daemon_info.read_text(encoding="utf-8")
            persisted = json.loads(persisted_text)
            if deterministic_token in persisted_text or "review_urls" in persisted or "urls" in persisted:
                raise RuntimeError("Persistent server info contains a token or tokenized URL field.")
            if persisted.get("base_urls") != daemon_output.get("base_urls"):
                raise RuntimeError("Daemon output and persistent safe base URLs differ.")
            if any(deterministic_token in url or "token=" in url for url in persisted["base_urls"]):
                raise RuntimeError("A persisted base URL contains mutation capability.")
            review_urls = daemon_output.get("review_urls", [])
            if not review_urls or any("#token=" not in url or "?token=" in url for url in review_urls):
                raise RuntimeError("Daemon parent did not return fragment-token review URLs.")
            if daemon_output.get("urls") != review_urls:
                raise RuntimeError("The compatibility urls field does not match review_urls.")

            process_line = subprocess.run(
                ["ps", "-p", str(child_pid), "-o", "command="],
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            if deterministic_token in process_line or "--token" in process_line:
                raise RuntimeError("Daemon child command arguments expose the review token.")

            base_url = persisted["base_urls"][0]
            if http_request(review_urls[0])[0] != 200:
                raise RuntimeError("Static preview failed without authentication.")
            api_url = urllib.parse.urljoin(base_url, "/api/review-comments")
            comment_payload = {
                "part": "test",
                "position_mm": [0.1, 0.2, 0.3],
                "message": "Authenticated integration test.",
            }
            if http_request(api_url, method="POST", value=comment_payload)[0] != 401:
                raise RuntimeError("Unauthenticated comment creation was accepted.")
            if http_request(api_url, method="POST", token="wrong-token", value=comment_payload)[0] != 401:
                raise RuntimeError("An incorrect bearer token was accepted.")
            if http_request(api_url, method="POST", token=deterministic_token, value=comment_payload)[0] != 201:
                raise RuntimeError("The daemon child did not receive the environment token.")
            created_comment = json.loads(progress.read_text(encoding="utf-8"))["comments"][0]
            delete_url = f"{api_url}/{created_comment['id']}"
            if http_request(delete_url, method="DELETE")[0] != 401:
                raise RuntimeError("Unauthenticated comment deletion was accepted.")
            if http_request(delete_url, method="DELETE", token="wrong-token")[0] != 401:
                raise RuntimeError("Incorrect-token comment deletion was accepted.")
            if http_request(delete_url, method="DELETE", token=deterministic_token)[0] != 200:
                raise RuntimeError("Authenticated comment deletion failed.")

            # Exercise legacy query input only to prove it is redacted from logs.
            if http_request(f"{base_url}?token={deterministic_token}")[0] != 200:
                raise RuntimeError("Legacy query URL could not load for browser migration.")
            time.sleep(0.1)
            if deterministic_token in daemon_log.read_text(encoding="utf-8"):
                raise RuntimeError("Daemon log contains the review token.")
        finally:
            os.kill(child_pid, signal.SIGTERM)
            for _ in range(30):
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)

        legacy = root / "legacy-progress.json"
        legacy.write_text(json.dumps({
            "schema_version": 1,
            "design_id": "legacy",
            "title": "Legacy enclosure",
            "summary": "Legacy review.",
            "steps": [{"id": "review", "title": "Review", "summary": "In progress."}],
            "review_comments": [
                {"id": "open", "part": "test", "position_mm": [0, 0, 0], "message": "Open", "author": "user", "status": "open"},
                {"id": "ack", "part": "test", "position_mm": [1, 0, 0], "message": "Acknowledged", "author": "user", "status": "acknowledged"},
                {"id": "done", "part": "test", "position_mm": [2, 0, 0], "message": "Resolved", "author": "user", "status": "resolved"},
            ],
        }), encoding="utf-8")
        run([sys.executable, progress_script, "show", str(legacy)], 0)
        legacy_data = json.loads(legacy.read_text(encoding="utf-8"))
        if legacy_data["schema_version"] != 2 or len(legacy_data["progress"]) != 1 or [item["id"] for item in legacy_data["comments"]] != ["open", "ack"]:
            raise RuntimeError("v1 sidecar did not migrate safely.")
        if any("author" in item or "updated_at" in item for item in legacy_data["comments"]):
            raise RuntimeError("v1 migration retained retired comment fields.")

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
        expected_default = (project / "build" / "functional-fdm" / "closure").resolve()
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

    print(json.dumps({"ok": True, "tests": 51}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
