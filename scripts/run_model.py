#!/usr/bin/env python3
"""Execute and validate a functional CadQuery model with bounded runtime."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))


@dataclass(frozen=True)
class OutputPlan:
    path: Path
    mode: str
    project_root: Path | None
    git_tracked: bool
    git_ignored: bool
    temporary: bool
    warnings: tuple[str, ...]

    def manifest(self) -> dict[str, object]:
        result = asdict(self)
        result["path"] = str(self.path)
        result["project_root"] = str(self.project_root) if self.project_root else None
        result["warnings"] = list(self.warnings)
        return result


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "design"


def design_slug(model: Path) -> str:
    if model.stem.lower() in {"model", "main", "design"} and model.parent.name:
        return slugify(model.parent.name)
    return slugify(model.stem)


def nearest_existing_directory(path: Path) -> Path:
    candidate = path if path.is_dir() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def git_project_root(path: Path) -> Path | None:
    candidate = nearest_existing_directory(path.resolve())
    try:
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode:
        return None
    return Path(result.stdout.strip()).resolve()


def git_output_state(path: Path) -> tuple[Path | None, bool, bool]:
    root = git_project_root(path)
    if root is None:
        return None, False, False
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None, False, False
    relative = relative or "."
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--", relative],
        check=False,
        text=True,
        capture_output=True,
    ).stdout.strip() != ""
    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", relative],
        check=False,
    ).returncode == 0
    return root, tracked, ignored


def resolve_output_plan(
    model: Path,
    requested: Path | None = None,
    *,
    in_place: bool = False,
) -> OutputPlan:
    model = model.resolve()
    if requested is not None and in_place:
        raise ValueError("Use either --output-dir or --in-place, not both.")

    temporary = False
    if requested is not None:
        output = requested.resolve()
        mode = "explicit"
    elif in_place:
        output = model.parent / f"{design_slug(model)}-output"
        mode = "in-place"
    else:
        model_root = git_project_root(model)
        if model_root is not None:
            output = model_root / "build" / "functional-fdm" / design_slug(model)
            mode = "project-default"
        else:
            output = Path(tempfile.mkdtemp(prefix=f"functional-fdm-{design_slug(model)}-"))
            mode = "temporary"
            temporary = True

    project_root, tracked, ignored = git_output_state(output)
    warnings: list[str] = []
    if tracked:
        warnings.append(
            "The output directory contains Git-tracked files. Generated CAD artifacts can create large diffs."
        )
    elif project_root is not None and not ignored:
        warnings.append(
            "The output directory is inside a Git worktree but is not ignored. "
            "Consider a project-specific ignore rule; this tool will not edit ignore files."
        )
    if temporary:
        warnings.append(
            "No project root was found. The output directory is temporary and can be removed by the operating system."
        )
    return OutputPlan(
        path=output,
        mode=mode,
        project_root=project_root,
        git_tracked=tracked,
        git_ignored=ignored,
        temporary=temporary,
        warnings=tuple(warnings),
    )


def markdown(bundle: object, manifest: dict[str, object]) -> str:
    lines = [f"# {manifest['name']}", ""]
    record = manifest.get("design_record")
    if record:
        lines.extend(["## Functional design record", "", f"- Intent: {record['intent']}"])
        lines.append(f"- Prototype stage: {record['prototype_stage']}")
        lines.append(f"- Readiness claim: {record.get('readiness', 'concept-ready')}")
        if record.get("known_dimensions_mm"):
            lines.append(f"- Known dimensions: {record['known_dimensions_mm']} mm")
        for assumption in record.get("assumptions", []):
            lines.append(f"- Assumption: {assumption}")
        for question in record.get("open_questions", []):
            lines.append(f"- Open question: {question}")
        lines.extend(["", "### Functional requirements", ""])
        requirements = record.get("requirements", [])
        if not requirements:
            lines.append("- No explicit functional requirements recorded.")
        for requirement in requirements:
            lines.append(
                f"- **{requirement['status']} — {requirement['requirement_id']}**: "
                f"{requirement['statement']}"
            )
            if requirement.get("verification_method"):
                lines.append(f"  - Verification: {requirement['verification_method']}")
            for evidence in requirement.get("evidence", []):
                lines.append(f"  - Evidence: {evidence}")
        sources = record.get("sources", [])
        if sources:
            lines.extend(["", "### Sources", ""])
            for source in sources:
                lines.append(f"- **{source['source_id']}**: {source['url']}")
                if source.get("product_revision"):
                    lines.append(f"  - Product/revision: {source['product_revision']}")
                if source.get("retrieved_on"):
                    lines.append(f"  - Retrieved: {source['retrieved_on']}")
                if source.get("verified_features"):
                    lines.append(f"  - Verified features: {source['verified_features']}")
                if source.get("license"):
                    lines.append(f"  - License: {source['license']}")
                if source.get("notes"):
                    lines.append(f"  - Notes: {source['notes']}")
        lines.extend(["", "### Design decisions", ""])
        decisions = record.get("decisions", [])
        if not decisions:
            lines.append("- No design decisions recorded.")
        for decision in decisions:
            lines.append(f"- {decision['decision']} — {decision['reason']}")
        lines.extend(["", "### Prototype test plan", ""])
        test_plan = record.get("test_plan", [])
        if not test_plan:
            lines.append("- No physical test planned.")
        for item in test_plan:
            lines.append(f"- {item}")
        lines.extend(["", "### Additional material and hardware", ""])
        if record.get("available_materials"):
            lines.append(f"- Available materials: {record['available_materials']}")
        additional_hardware = record.get("additional_hardware", [])
        if not additional_hardware:
            lines.append("- No additional hardware recorded.")
        for item in additional_hardware:
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(["## Process assumptions", ""])
    for key, value in manifest.get("assumptions", {}).items():  # type: ignore[union-attr]
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Parts", ""])
    for part in manifest["parts"]:  # type: ignore[index]
        lines.append(f"### {part['name']}")
        lines.append("")
        lines.append(f"- Material: {part['material']}")
        lines.append(f"- Orientation: {part['orientation']}")
        if part.get("actual_size_mm"):
            lines.append(f"- Actual bounds: {part['actual_size_mm']} mm")
        if part.get("critical_dimensions"):
            lines.append(f"- Critical dimensions: {part['critical_dimensions']}")
        for note in part.get("notes", []):
            lines.append(f"- {note}")
        feature_notes = sorted({
            note
            for feature in part.get("features", [])
            for note in feature.get("print_notes", [])
        })
        for note in feature_notes:
            lines.append(f"- Process note: {note}")
        lines.append("")
    reference_components = manifest.get("reference_components", [])
    if reference_components:
        lines.extend(["## Non-printable reference components", ""])
        for component in reference_components:  # type: ignore[union-attr]
            lines.append(f"### {component['name']}")
            lines.append("")
            lines.append(f"- Position: {component['position_mm']} mm")
            lines.append(f"- Rotation: {component['rotation_deg']} degrees")
            if component.get("nominal_size_mm"):
                lines.append(f"- Nominal envelope: {component['nominal_size_mm']} mm")
            if component.get("source_id"):
                lines.append(f"- Source: {component['source_id']}")
            for note in component.get("notes", []):
                lines.append(f"- {note}")
            lines.append("")
    lines.extend(["## Hardware BOM", ""])
    for item in manifest.get("bom", []):  # type: ignore[union-attr]
        lines.append(f"- {item}")
    lines.extend(["", "## Assembly", ""])
    for index, instruction in enumerate(manifest.get("assembly_instructions", []), 1):  # type: ignore[arg-type]
        lines.append(f"{index}. {instruction}")
    lines.extend(["", "## Validation findings", ""])
    findings = manifest.get("findings", [])  # type: ignore[assignment]
    if not findings:
        lines.append("- No semantic findings.")
    for finding in findings:  # type: ignore[union-attr]
        lines.append(f"- **{finding['severity']} — {finding['code']}**: {finding['message']}")
        if finding.get("recommendation"):
            lines.append(f"  - Action: {finding['recommendation']}")
    lines.extend(["", "## Small physical tests", "", "Use a small fit or mechanism test whenever it answers a real uncertainty. State what it tests, what it does not test, and how the result changes the full model. Do not request printer calibration data by default.", ""])
    return "\n".join(lines)


def load_bundle(model: Path) -> object:
    spec = importlib.util.spec_from_file_location("functional_model", model)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load model: {model}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build"):
        raise RuntimeError("Model must define build() and return DesignBundle.")
    bundle = module.build()
    from functional_fdm import DesignBundle
    if not isinstance(bundle, DesignBundle):
        raise TypeError("build() did not return functional_fdm.DesignBundle.")
    return bundle


def worker(model: Path, output: Path, output_policy: dict[str, object]) -> int:
    import cadquery as cq
    from functional_fdm import Severity

    bundle = load_bundle(model)
    manifest = bundle.as_manifest()
    manifest["output_policy"] = output_policy
    output.mkdir(parents=True, exist_ok=True)
    part_dir = output / "parts"
    reference_dir = output / "reference-models"
    render_dir = output / "renders"
    part_dir.mkdir(exist_ok=True)
    reference_dir.mkdir(exist_ok=True)
    render_dir.mkdir(exist_ok=True)
    failures: list[str] = []
    preview_parts: list[str] = []
    preview_review: list[str] = []
    preview_references: list[str] = []
    stl_paths: list[Path] = []

    for annotation in bundle.review_annotations:
        preview_review.extend(["--annotation", json.dumps(annotation.as_dict())])
    for part in bundle.parts:
        geometry = part.geometry.val() if isinstance(part.geometry, cq.Workplane) else part.geometry
        if geometry is None or not hasattr(geometry, "isValid") or not geometry.isValid():
            failures.append(f"Part {part.name!r} is not a valid CadQuery shape.")
            continue
        solid_count = len(geometry.Solids())
        if solid_count != part.expected_solids:
            failures.append(f"Part {part.name!r} has {solid_count} solids; expected {part.expected_solids}.")
        bounds = geometry.BoundingBox()
        actual_size = (bounds.xlen, bounds.ylen, bounds.zlen)
        actual_volume = sum(solid.Volume() for solid in geometry.Solids())
        manifest_part = next(item for item in manifest["parts"] if item["name"] == part.name)
        manifest_part["actual_size_mm"] = [round(value, 6) for value in actual_size]
        manifest_part["actual_volume_mm3"] = round(actual_volume, 6)
        if part.expected_size_mm is not None:
            for axis, actual, expected in zip("XYZ", actual_size, part.expected_size_mm):
                if abs(actual - expected) > part.size_tolerance_mm:
                    failures.append(
                        f"Part {part.name!r} {axis} size is {actual:.3f} mm; "
                        f"expected {expected:.3f} +/- {part.size_tolerance_mm:.3f} mm."
                    )
        if part.expected_volume_range_mm3 is not None:
            low, high = part.expected_volume_range_mm3
            if not low <= actual_volume <= high:
                failures.append(
                    f"Part {part.name!r} volume is {actual_volume:.3f} mm^3; "
                    f"expected {low:.3f} to {high:.3f} mm^3."
                )
        step_path = part_dir / f"{part.name}.step"
        stl_path = part_dir / f"{part.name}.stl"
        cq.exporters.export(geometry, str(step_path))
        cq.exporters.export(geometry, str(stl_path), tolerance=0.05, angularTolerance=0.1)
        stl_paths.append(stl_path)
        preview_parts.extend(["--part", f"{part.name}={stl_path}:{part.color}"])
        audit = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("audit_stl.py")), str(stl_path), "--expected-components", str(part.expected_solids), "--strict"],
            check=False,
            text=True,
            capture_output=True,
        )
        (part_dir / f"{part.name}.mesh-audit.json").write_text(audit.stdout, encoding="utf-8")
        if audit.returncode:
            failures.append(f"Part {part.name!r} failed the STL mesh audit.")
        try:
            audit_report = json.loads(audit.stdout)
        except json.JSONDecodeError:
            audit_report = None
            failures.append(f"Part {part.name!r} produced an unreadable STL mesh audit.")
        if audit_report is not None:
            horizontal = audit_report.get("unsupported_horizontal_candidates", {})
            manifest_part["printability_audit"] = {
                "overhang": audit_report.get("overhang"),
                "unsupported_horizontal_candidates": horizontal,
            }
            horizontal_regions = [
                region
                for region in horizontal.get("regions", [])
                if float(region.get("area_mm2", 0.0)) > 2.0
            ]
            horizontal_area = float(horizontal.get("area_mm2", 0.0))
            has_significant_horizontal = horizontal_area > 5.0 or bool(horizontal_regions)
            if has_significant_horizontal:
                plan = part.print_plan
                if plan is None or plan.support_mode == "unverified":
                    failures.append(
                        f"Part {part.name!r} has {horizontal_area:.3f} mm^2 of unsupported "
                        "horizontal candidates without a verified bridge or removable-support plan."
                    )
                elif plan.support_mode == "none":
                    if not plan.bridges:
                        failures.append(
                            f"Part {part.name!r} claims support-free printing but has "
                            f"{horizontal_area:.3f} mm^2 of unsupported horizontal candidates "
                            "and no declared two-ended bridges."
                        )
                    else:
                        declared_spans = sorted(bridge.span_mm for bridge in plan.bridges)
                        candidate_spans = sorted(
                            float(region.get("estimated_short_span_mm", 0.0))
                            for region in horizontal_regions
                        )
                        if len(candidate_spans) > len(declared_spans):
                            failures.append(
                                f"Part {part.name!r} has {len(candidate_spans)} significant horizontal "
                                f"regions but only {len(declared_spans)} reviewed bridge declarations."
                            )
                        elif any(
                            candidate > declared + 0.5
                            for candidate, declared in zip(candidate_spans, declared_spans)
                        ):
                            failures.append(
                                f"Part {part.name!r} has a horizontal candidate wider than its "
                                "declared reviewed bridge span."
                            )
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name("render_stl_views.py")), str(stl_path), "--output", str(render_dir / part.name), "--colors", part.color],
            check=True,
        )

    for component in bundle.reference_components:
        geometry = (
            component.geometry.val()
            if isinstance(component.geometry, cq.Workplane)
            else component.geometry
        )
        solids = geometry.Solids() if geometry is not None and hasattr(geometry, "Solids") else []
        if not solids:
            failures.append(
                f"Reference component {component.name!r} has no renderable solid geometry."
            )
            continue
        stl_path = reference_dir / f"{component.name}.stl"
        # Reference hardware is visual context rather than a manufacturing
        # mesh. Use a lighter tessellation so detailed supplier assemblies do
        # not make the browser preview or repository unnecessarily large.
        cq.exporters.export(geometry, str(stl_path), tolerance=0.15, angularTolerance=0.3)
        preview_references.extend(
            [
                "--reference",
                json.dumps(
                    {
                        "name": component.name,
                        "path": str(stl_path),
                        "color": component.color,
                        "opacity": component.opacity,
                        "position_mm": list(component.position_mm),
                        "rotation_deg": list(component.rotation_deg),
                        "nominal_size_mm": (
                            list(component.nominal_size_mm)
                            if component.nominal_size_mm
                            else None
                        ),
                        "notes": component.notes,
                        "source_id": component.source_id,
                    }
                ),
            ]
        )

    progress_path = output / "progress.json"
    preview_progress = ["--progress-url", "../progress.json"] if progress_path.exists() else []

    if stl_paths:
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name("render_stl_views.py")), *map(str, stl_paths), "--output", str(render_dir / "assembly"), "--explode-mm", "15"],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("build_preview.py")),
                "--output",
                str(output / "preview"),
                "--title",
                bundle.name,
                *preview_parts,
                *preview_references,
                *preview_review,
                *preview_progress,
            ],
            check=True,
        )
        assembly = cq.Assembly(name=bundle.name)
        for part in bundle.parts:
            geometry = part.geometry.val() if isinstance(part.geometry, cq.Workplane) else part.geometry
            color_text = part.color.lstrip("#")
            if len(color_text) != 6:
                failures.append(f"Part {part.name!r} has invalid color {part.color!r}.")
                color = cq.Color(0.5, 0.5, 0.5)
            else:
                color = cq.Color(*(int(color_text[index:index + 2], 16) / 255 for index in (0, 2, 4)))
            assembly.add(geometry, name=part.name, color=color)
        try:
            assembly.save(str(output / "assembly.step"))
        except Exception as error:
            failures.append(f"Assembly STEP export failed: {error}")

    semantic_blockers = [
        finding for finding in bundle.validate_metadata() if finding.severity >= Severity.BLOCKING
    ]
    failures.extend(f"{finding.code}: {finding.message}" for finding in semantic_blockers)
    manifest["execution_failures"] = failures
    manifest["blocked"] = bool(failures) or manifest["blocked"]
    (output / "design.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "DESIGN.md").write_text(markdown(bundle, manifest), encoding="utf-8")
    result = {
        "ok": not failures,
        "output": str(output),
        "output_policy": output_policy,
        "parts": len(stl_paths),
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output-dir", "--output", dest="output_dir", type=Path)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write to <model-directory>/<design-name>-output instead of a build or temporary directory.",
    )
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output-policy-json", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.output_dir is None or args.output_policy_json is None:
            parser.error("Worker mode requires --output-dir and --output-policy-json.")
        return worker(
            args.model.resolve(),
            args.output_dir.resolve(),
            json.loads(args.output_policy_json),
        )
    try:
        plan = resolve_output_plan(args.model, args.output_dir, in_place=args.in_place)
    except ValueError as error:
        parser.error(str(error))
    for warning in plan.warnings:
        print(f"Output warning: {warning}", file=sys.stderr)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        str(args.model.resolve()),
        "--output-dir",
        str(plan.path),
        "--output-policy-json",
        json.dumps(plan.manifest()),
        "--worker",
    ]
    try:
        result = subprocess.run(command, check=False, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "failure": f"Model execution exceeded {args.timeout} seconds."}, indent=2))
        return 124
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
