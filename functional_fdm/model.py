"""Shared feature, assembly, and validation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from typing import Any


REQUIREMENT_STATUSES = frozenset({
    "unverified",
    "cad-checked",
    "fdm-plausible",
    "physically-tested",
    "function-confirmed",
})
PROTOTYPE_STAGES = frozenset({"concept", "small-fit-test", "integrated-prototype", "final"})
READINESS_LEVELS = frozenset({"concept-ready", "print-ready", "function-confirmed"})


class Severity(IntEnum):
    INFO = 10
    CAUTION = 20
    LIKELY_FAILURE = 30
    BLOCKING = 40

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    feature: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.name,
            "message": self.message,
            "feature": self.feature,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class FeatureResult:
    name: str
    feature_type: str
    geometry: Any = None
    dimensions: dict[str, float | str | bool] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    interfaces: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    print_notes: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(finding.severity >= Severity.BLOCKING for finding in self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "feature_type": self.feature_type,
            "dimensions": self.dimensions,
            "assumptions": self.assumptions,
            "interfaces": self.interfaces,
            "findings": [finding.as_dict() for finding in self.findings],
            "print_notes": self.print_notes,
            "has_geometry": self.geometry is not None,
        }


@dataclass(frozen=True)
class BridgeSpec:
    """One intentional span that prints between two supported anchors."""

    name: str
    span_mm: float
    width_mm: float
    anchored_ends: bool
    evidence: str
    critical_surface: bool = False

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        if self.span_mm <= 0 or self.width_mm <= 0:
            findings.append(
                Finding(
                    "print-plan.bridge.invalid-size",
                    Severity.BLOCKING,
                    f"Bridge {self.name!r} has a nonpositive span or width.",
                )
            )
        if not self.anchored_ends:
            findings.append(
                Finding(
                    "print-plan.bridge.not-bridge",
                    Severity.BLOCKING,
                    f"Bridge {self.name!r} does not have supported anchors at both ends.",
                    recommendation="Classify it as a cantilever and redesign, reorient, split, or support it.",
                )
            )
        if not self.evidence.strip():
            findings.append(
                Finding(
                    "print-plan.bridge.missing-evidence",
                    Severity.BLOCKING,
                    f"Bridge {self.name!r} has no review or test evidence.",
                    recommendation="Record the span review, material assumption, or physical bridge test.",
                )
            )
        if self.critical_surface:
            findings.append(
                Finding(
                    "print-plan.bridge.critical-surface",
                    Severity.LIKELY_FAILURE,
                    f"Bridge {self.name!r} controls a critical surface.",
                    recommendation="Move the interface, split the part, or validate the bridge physically.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "span_mm": self.span_mm,
            "width_mm": self.width_mm,
            "anchored_ends": self.anchored_ends,
            "evidence": self.evidence,
            "critical_surface": self.critical_surface,
        }


@dataclass(frozen=True)
class PrintPlan:
    """Manufacturing plan for geometry in its exported print orientation."""

    support_mode: str = "unverified"
    reviewed: bool = False
    review_evidence: str = ""
    bridges: tuple[BridgeSpec, ...] = ()
    support_removal_path: str = ""

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        allowed_modes = {"none", "local", "generated", "unverified"}
        if self.support_mode not in allowed_modes:
            findings.append(
                Finding(
                    "print-plan.invalid-support-mode",
                    Severity.BLOCKING,
                    f"Support mode {self.support_mode!r} is invalid.",
                    recommendation="Use none, local, generated, or unverified.",
                )
            )
        if self.support_mode == "unverified":
            findings.append(
                Finding(
                    "print-plan.unverified",
                    Severity.BLOCKING,
                    "The print-oriented part has no verified support plan.",
                    recommendation="Inspect the actual exported orientation and record its support strategy.",
                )
            )
        if not self.reviewed or not self.review_evidence.strip():
            findings.append(
                Finding(
                    "print-plan.missing-review",
                    Severity.BLOCKING,
                    "The print plan has no recorded geometry review evidence.",
                    recommendation="Inspect the support-risk overlay and record the result.",
                )
            )
        if self.support_mode in {"local", "generated"} and not self.support_removal_path.strip():
            findings.append(
                Finding(
                    "print-plan.missing-removal-path",
                    Severity.BLOCKING,
                    "The support plan has no removal path.",
                    recommendation="State how all support can be reached and removed without damaging a critical face.",
                )
            )
        for bridge in self.bridges:
            findings.extend(bridge.validate())
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "support_mode": self.support_mode,
            "reviewed": self.reviewed,
            "review_evidence": self.review_evidence,
            "bridges": [bridge.as_dict() for bridge in self.bridges],
            "support_removal_path": self.support_removal_path,
        }


@dataclass(frozen=True)
class ReviewAnnotation:
    """Stable shared name and model-space location for visual design review."""

    annotation_id: str
    label: str
    position_mm: tuple[float, float, float]
    part: str | None = None
    description: str = ""
    color: str = "#ffd166"

    def validate(self, known_parts: set[str]) -> list[Finding]:
        findings: list[Finding] = []
        if not self.annotation_id.strip() or not self.label.strip():
            findings.append(
                Finding(
                    "review.annotation.missing-name",
                    Severity.BLOCKING,
                    "A review annotation has no stable identifier or label.",
                )
            )
        if self.part is not None and self.part not in known_parts:
            findings.append(
                Finding(
                    "review.annotation.unknown-part",
                    Severity.BLOCKING,
                    f"Annotation {self.annotation_id!r} names unknown part {self.part!r}.",
                )
            )
        if len(self.position_mm) != 3:
            findings.append(
                Finding(
                    "review.annotation.invalid-position",
                    Severity.BLOCKING,
                    f"Annotation {self.annotation_id!r} does not have an XYZ position.",
                )
            )
        if not self.color.startswith("#") or len(self.color) != 7:
            findings.append(
                Finding(
                    "review.annotation.invalid-color",
                    Severity.BLOCKING,
                    f"Annotation {self.annotation_id!r} has invalid color {self.color!r}.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.annotation_id,
            "label": self.label,
            "position_mm": list(self.position_mm),
            "part": self.part,
            "description": self.description,
            "color": self.color,
        }


@dataclass(frozen=True)
class DesignDelta:
    """One optional numeric design change tied to a visible annotation."""

    annotation_id: str
    parameter: str
    before: float
    after: float
    unit: str
    direction: str
    reason: str

    def validate(self, annotation_ids: set[str]) -> list[Finding]:
        findings: list[Finding] = []
        if self.annotation_id not in annotation_ids:
            findings.append(
                Finding(
                    "review.delta.unknown-annotation",
                    Severity.BLOCKING,
                    f"Design delta names unknown annotation {self.annotation_id!r}.",
                )
            )
        if not self.parameter.strip() or not self.unit.strip() or not self.direction.strip():
            findings.append(
                Finding(
                    "review.delta.incomplete",
                    Severity.BLOCKING,
                    f"Design delta for {self.annotation_id!r} lacks parameter, unit, or direction.",
                )
            )
        if self.before == self.after:
            findings.append(
                Finding(
                    "review.delta.no-change",
                    Severity.CAUTION,
                    f"Design delta for {self.annotation_id!r} has no numeric change.",
                )
            )
        if not self.reason.strip():
            findings.append(
                Finding(
                    "review.delta.missing-reason",
                    Severity.BLOCKING,
                    f"Design delta for {self.annotation_id!r} has no reason.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "parameter": self.parameter,
            "before": self.before,
            "after": self.after,
            "delta": self.after - self.before,
            "unit": self.unit,
            "direction": self.direction,
            "reason": self.reason,
        }


@dataclass
class DesignPart:
    name: str
    geometry: Any
    orientation: str
    material: str
    color: str = "#7aa2f7"
    expected_solids: int = 1
    expected_size_mm: tuple[float, float, float] | None = None
    size_tolerance_mm: float = 0.15
    expected_volume_range_mm3: tuple[float, float] | None = None
    features: list[FeatureResult] = field(default_factory=list)
    critical_dimensions: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    print_plan: PrintPlan | None = None

    def findings(self) -> list[Finding]:
        return [finding for feature in self.features for finding in feature.findings]


@dataclass
class ReferenceComponent:
    """Non-printable assembly context shown beside printable geometry."""

    name: str
    geometry: Any
    color: str = "#94a3b8"
    opacity: float = 0.42
    position_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    nominal_size_mm: tuple[float, float, float] | None = None
    notes: list[str] = field(default_factory=list)
    source_id: str | None = None

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        if not self.name.strip():
            findings.append(
                Finding(
                    "reference.missing-name",
                    Severity.BLOCKING,
                    "A reference component has no name.",
                )
            )
        if not self.color.startswith("#") or len(self.color) != 7:
            findings.append(
                Finding(
                    "reference.invalid-color",
                    Severity.BLOCKING,
                    f"Reference component {self.name!r} has invalid color {self.color!r}.",
                )
            )
        if not 0.05 <= self.opacity <= 1.0:
            findings.append(
                Finding(
                    "reference.invalid-opacity",
                    Severity.BLOCKING,
                    f"Reference component {self.name!r} opacity must be between 0.05 and 1.0.",
                )
            )
        if len(self.position_mm) != 3 or len(self.rotation_deg) != 3:
            findings.append(
                Finding(
                    "reference.invalid-transform",
                    Severity.BLOCKING,
                    f"Reference component {self.name!r} requires XYZ position and rotation values.",
                )
            )
        if self.nominal_size_mm is not None and (
            len(self.nominal_size_mm) != 3 or any(value <= 0 for value in self.nominal_size_mm)
        ):
            findings.append(
                Finding(
                    "reference.invalid-size",
                    Severity.BLOCKING,
                    f"Reference component {self.name!r} has invalid nominal dimensions.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": "reference",
            "color": self.color,
            "opacity": self.opacity,
            "position_mm": list(self.position_mm),
            "rotation_deg": list(self.rotation_deg),
            "nominal_size_mm": list(self.nominal_size_mm) if self.nominal_size_mm else None,
            "notes": self.notes,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class InterfaceSpec:
    interface_id: str
    part_a: str
    part_b: str
    joint_type: str
    nominal_geometry: dict[str, Any]
    fit: str
    insertion_direction: tuple[float, float, float]
    removable: bool
    expected_cycles: int
    hardware: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "interface_id": self.interface_id,
            "part_a": self.part_a,
            "part_b": self.part_b,
            "joint_type": self.joint_type,
            "nominal_geometry": self.nominal_geometry,
            "fit": self.fit,
            "insertion_direction": list(self.insertion_direction),
            "removable": self.removable,
            "expected_cycles": self.expected_cycles,
            "hardware": self.hardware,
            "metadata": self.metadata,
        }


@dataclass
class AssemblyGraph:
    parts: set[str] = field(default_factory=set)
    interfaces: list[InterfaceSpec] = field(default_factory=list)

    def add_part(self, name: str) -> None:
        if not name:
            raise ValueError("Part names must not be empty.")
        self.parts.add(name)

    def add_interface(self, interface: InterfaceSpec) -> None:
        self.interfaces.append(interface)

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        identifiers: set[str] = set()
        for interface in self.interfaces:
            if interface.interface_id in identifiers:
                findings.append(
                    Finding(
                        "assembly.duplicate-interface",
                        Severity.BLOCKING,
                        f"Interface id {interface.interface_id!r} is duplicated.",
                    )
                )
            identifiers.add(interface.interface_id)
            missing = {interface.part_a, interface.part_b} - self.parts
            if missing:
                findings.append(
                    Finding(
                        "assembly.missing-part",
                        Severity.BLOCKING,
                        f"Interface {interface.interface_id!r} names missing parts: {sorted(missing)}.",
                    )
                )
            if interface.part_a == interface.part_b:
                findings.append(
                    Finding(
                        "assembly.self-interface",
                        Severity.BLOCKING,
                        f"Interface {interface.interface_id!r} connects a part to itself.",
                    )
                )
            if sum(value * value for value in interface.insertion_direction) <= 1e-12:
                findings.append(
                    Finding(
                        "assembly.no-insertion-direction",
                        Severity.BLOCKING,
                        f"Interface {interface.interface_id!r} has no insertion direction.",
                    )
                )
            if interface.removable and interface.expected_cycles < 1:
                findings.append(
                    Finding(
                        "assembly.invalid-cycle-count",
                        Severity.LIKELY_FAILURE,
                        f"Removable interface {interface.interface_id!r} has no expected cycles.",
                    )
                )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "parts": sorted(self.parts),
            "interfaces": [interface.as_dict() for interface in self.interfaces],
        }


@dataclass
class AssemblyCheckResult:
    """One numeric geometry check for an assembled part pair."""

    name: str
    part_a: str
    part_b: str
    check_type: str
    measurements: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(finding.severity >= Severity.BLOCKING for finding in self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "part_a": self.part_a,
            "part_b": self.part_b,
            "check_type": self.check_type,
            "passed": self.passed,
            "measurements": self.measurements,
            "findings": [finding.as_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class FunctionalRequirement:
    """One intended behavior and the current level of evidence for it."""

    requirement_id: str
    statement: str
    source: str = "user"
    status: str = "unverified"
    verification_method: str = ""
    evidence: tuple[str, ...] = ()

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        if not self.requirement_id.strip() or not self.statement.strip():
            findings.append(
                Finding(
                    "requirement.missing-identity",
                    Severity.BLOCKING,
                    "A functional requirement needs both an identifier and a statement.",
                )
            )
        if self.status not in REQUIREMENT_STATUSES:
            findings.append(
                Finding(
                    "requirement.invalid-status",
                    Severity.BLOCKING,
                    f"Requirement {self.requirement_id!r} uses invalid status {self.status!r}.",
                    recommendation=f"Use one of: {', '.join(sorted(REQUIREMENT_STATUSES))}.",
                )
            )
        if self.status in {"physically-tested", "function-confirmed"} and (
            not self.verification_method.strip() or not any(item.strip() for item in self.evidence)
        ):
            findings.append(
                Finding(
                    "requirement.physical-claim-missing-evidence",
                    Severity.BLOCKING,
                    f"Requirement {self.requirement_id!r} claims physical evidence without a verification method and result.",
                    recommendation="Record the representative physical test method and its observed evidence, or lower the status.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "statement": self.statement,
            "source": self.source,
            "status": self.status,
            "verification_method": self.verification_method,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class DesignDecision:
    """One architecture decision and the reason for it."""

    decision: str
    reason: str
    alternatives: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "alternatives": list(self.alternatives),
        }


@dataclass(frozen=True)
class SourceRecord:
    """Provenance for one fit-controlling drawing, model, or document."""

    source_id: str
    url: str
    product_revision: str = ""
    retrieved_on: str = ""
    license: str = ""
    verified_features: tuple[str, ...] = ()
    notes: str = ""

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        if not self.source_id.strip():
            findings.append(
                Finding(
                    "source.missing-id",
                    Severity.BLOCKING,
                    "A provenance record has no source identifier.",
                )
            )
        if not self.url.strip() or "://" not in self.url:
            findings.append(
                Finding(
                    "source.invalid-url",
                    Severity.BLOCKING,
                    f"Source {self.source_id!r} has no absolute source URL.",
                )
            )
        if self.retrieved_on:
            try:
                date.fromisoformat(self.retrieved_on)
            except ValueError:
                findings.append(
                    Finding(
                        "source.invalid-retrieval-date",
                        Severity.BLOCKING,
                        f"Source {self.source_id!r} has an invalid retrieval date.",
                        recommendation="Use an ISO date such as 2026-08-15 or leave it blank.",
                    )
                )
        if any(not isinstance(item, str) or not item.strip() for item in self.verified_features):
            findings.append(
                Finding(
                    "source.invalid-verified-feature",
                    Severity.BLOCKING,
                    f"Source {self.source_id!r} contains an empty or malformed verified feature.",
                )
            )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "product_revision": self.product_revision,
            "retrieved_on": self.retrieved_on,
            "license": self.license,
            "verified_features": list(self.verified_features),
            "notes": self.notes,
        }


@dataclass
class DesignRecord:
    """Durable design brief stored with the editable Python model."""

    intent: str
    known_dimensions_mm: dict[str, float | list[float] | tuple[float, ...]] = field(default_factory=dict)
    requirements: list[FunctionalRequirement] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    available_materials: list[str] = field(default_factory=list)
    additional_hardware: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[DesignDecision] = field(default_factory=list)
    prototype_stage: str = "concept"
    test_plan: list[str] = field(default_factory=list)
    readiness: str = "concept-ready"
    sources: list[SourceRecord] = field(default_factory=list)

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []
        if not self.intent.strip():
            findings.append(
                Finding(
                    "design-record.missing-intent",
                    Severity.BLOCKING,
                    "The design record has no functional intent.",
                )
            )
        if not self.requirements:
            findings.append(
                Finding(
                    "design-record.missing-requirements",
                    Severity.CAUTION,
                    "The design record has no explicit functional requirements.",
                    recommendation="Record the behaviors that the prototype or final part must demonstrate.",
                )
            )
        identifiers = [requirement.requirement_id for requirement in self.requirements]
        duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
        if duplicates:
            findings.append(
                Finding(
                    "design-record.duplicate-requirement",
                    Severity.BLOCKING,
                    f"Functional requirement identifiers are duplicated: {duplicates}.",
                )
            )
        for requirement in self.requirements:
            findings.extend(requirement.validate())
        if self.prototype_stage not in PROTOTYPE_STAGES:
            findings.append(
                Finding(
                    "design-record.invalid-prototype-stage",
                    Severity.BLOCKING,
                    f"Prototype stage {self.prototype_stage!r} is invalid.",
                    recommendation=f"Use one of: {', '.join(sorted(PROTOTYPE_STAGES))}.",
                )
            )
        if self.readiness not in READINESS_LEVELS:
            findings.append(
                Finding(
                    "design-record.invalid-readiness",
                    Severity.BLOCKING,
                    f"Readiness claim {self.readiness!r} is invalid.",
                    recommendation=f"Use one of: {', '.join(sorted(READINESS_LEVELS))}.",
                )
            )
        source_ids = [source.source_id for source in self.sources]
        duplicate_sources = sorted({item for item in source_ids if source_ids.count(item) > 1})
        if duplicate_sources:
            findings.append(
                Finding(
                    "source.duplicate-id",
                    Severity.BLOCKING,
                    f"Source identifiers are duplicated: {duplicate_sources}.",
                )
            )
        for source in self.sources:
            findings.extend(source.validate())
        for index, decision in enumerate(self.decisions):
            if not decision.decision.strip() or not decision.reason.strip():
                findings.append(
                    Finding(
                        "design-record.incomplete-decision",
                        Severity.BLOCKING,
                        f"Decision {index + 1} requires both a choice and a reason.",
                    )
                )
        return findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "known_dimensions_mm": self.known_dimensions_mm,
            "requirements": [requirement.as_dict() for requirement in self.requirements],
            "assumptions": self.assumptions,
            "open_questions": self.open_questions,
            "available_materials": self.available_materials,
            "additional_hardware": self.additional_hardware,
            "decisions": [decision.as_dict() for decision in self.decisions],
            "prototype_stage": self.prototype_stage,
            "readiness": self.readiness,
            "test_plan": self.test_plan,
            "sources": [source.as_dict() for source in self.sources],
        }


@dataclass
class DesignBundle:
    name: str
    parts: list[DesignPart]
    assembly: AssemblyGraph
    assumptions: dict[str, Any] = field(default_factory=dict)
    bom: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    assembly_instructions: list[str] = field(default_factory=list)
    assembly_checks: list[AssemblyCheckResult] = field(default_factory=list)
    design_record: DesignRecord | None = None
    review_annotations: list[ReviewAnnotation] = field(default_factory=list)
    design_deltas: list[DesignDelta] = field(default_factory=list)
    reference_components: list[ReferenceComponent] = field(default_factory=list)

    def validate_metadata(self) -> list[Finding]:
        findings = list(self.findings)
        part_names = [part.name for part in self.parts]
        reference_names = [component.name for component in self.reference_components]
        duplicates = sorted({name for name in part_names if part_names.count(name) > 1})
        if duplicates:
            findings.append(
                Finding(
                    "design.duplicate-part-name",
                    Severity.BLOCKING,
                    f"Part names are duplicated: {duplicates}.",
                )
            )
        duplicate_references = sorted(
            {name for name in reference_names if reference_names.count(name) > 1}
        )
        if duplicate_references:
            findings.append(
                Finding(
                    "reference.duplicate-name",
                    Severity.BLOCKING,
                    f"Reference component names are duplicated: {duplicate_references}.",
                )
            )
        shared_names = sorted(set(part_names) & set(reference_names))
        if shared_names:
            findings.append(
                Finding(
                    "reference.part-name-collision",
                    Severity.BLOCKING,
                    f"Printable parts and reference components share names: {shared_names}.",
                )
            )
        if set(part_names) != self.assembly.parts:
            findings.append(
                Finding(
                    "design.assembly-part-mismatch",
                    Severity.BLOCKING,
                    "The design parts and assembly graph parts differ.",
                    evidence={"design_parts": sorted(part_names), "assembly_parts": sorted(self.assembly.parts)},
                )
            )
        findings.extend(self.assembly.validate())
        if self.design_record is None:
            findings.append(
                Finding(
                    "design-record.missing",
                    Severity.CAUTION,
                    "The editable model has no structured design record.",
                    recommendation="Record intent, known dimensions, requirements, assumptions, decisions, and the current test stage in the Python model.",
                )
            )
        else:
            findings.extend(self.design_record.validate())
        if len(self.parts) > 1:
            for interface in self.assembly.interfaces:
                pair = tuple(sorted((interface.part_a, interface.part_b)))
                pair_checks = [
                    check
                    for check in self.assembly_checks
                    if tuple(sorted((check.part_a, check.part_b))) == pair
                ]
                if not any(check.check_type == "final-state-interference" for check in pair_checks):
                    findings.append(
                        Finding(
                            "assembly.missing-geometry-check",
                            Severity.BLOCKING,
                            f"Interface {interface.interface_id!r} is missing a final-state interference check.",
                            evidence={"check_type": "final-state-interference", "pair": pair},
                            recommendation="Check final assembled overlap with the actual part geometry.",
                        )
                    )
                joint = interface.joint_type.lower()
                if "hinge" in joint or "rotary" in joint:
                    accepted_motion = {"rotational-motion-path", "sampled-motion-path"}
                elif "bayonet" in joint or "twist" in joint:
                    accepted_motion = {"sampled-motion-path"}
                else:
                    accepted_motion = {"insertion-path", "sampled-motion-path"}
                if not any(check.check_type in accepted_motion for check in pair_checks):
                    findings.append(
                        Finding(
                            "assembly.missing-motion-check",
                            Severity.BLOCKING,
                            f"Interface {interface.interface_id!r} lacks an applicable sampled motion check.",
                            evidence={
                                "joint_type": interface.joint_type,
                                "accepted_check_types": sorted(accepted_motion),
                                "pair": pair,
                            },
                            recommendation="Use linear insertion only for straight translation; use rotational or explicit sampled poses for other motion.",
                        )
                    )
        known_parts = set(part_names)
        known_scene_objects = known_parts | set(reference_names)
        annotation_ids = [annotation.annotation_id for annotation in self.review_annotations]
        duplicate_annotations = sorted(
            {name for name in annotation_ids if annotation_ids.count(name) > 1}
        )
        if duplicate_annotations:
            findings.append(
                Finding(
                    "review.annotation.duplicate-id",
                    Severity.BLOCKING,
                    f"Review annotation identifiers are duplicated: {duplicate_annotations}.",
                )
            )
        for annotation in self.review_annotations:
            findings.extend(annotation.validate(known_scene_objects))
        known_annotations = set(annotation_ids)
        for delta in self.design_deltas:
            findings.extend(delta.validate(known_annotations))
        for check in self.assembly_checks:
            missing = {check.part_a, check.part_b} - known_scene_objects
            if missing:
                findings.append(
                    Finding(
                        "assembly.geometry-check-missing-part",
                        Severity.BLOCKING,
                        f"Assembly geometry check {check.name!r} names missing parts: {sorted(missing)}.",
                    )
                )
            findings.extend(check.findings)
        for part in self.parts:
            findings.extend(part.findings())
            if not part.orientation:
                findings.append(
                    Finding(
                        "design.missing-orientation",
                        Severity.BLOCKING,
                        f"Part {part.name!r} has no print orientation.",
                    )
                )
            if part.print_plan is None:
                findings.append(
                    Finding(
                        "print-plan.missing",
                        Severity.BLOCKING,
                        f"Part {part.name!r} has no printability plan.",
                        recommendation="Record support mode, bridge spans, removal path, and review evidence for the exported orientation.",
                    )
                )
            else:
                findings.extend(part.print_plan.validate())
        for component in self.reference_components:
            findings.extend(component.validate())
            if component.source_id is not None:
                known_sources = {
                    source.source_id
                    for source in (self.design_record.sources if self.design_record else [])
                }
                if component.source_id not in known_sources:
                    findings.append(
                        Finding(
                            "reference.unknown-source",
                            Severity.BLOCKING,
                            f"Reference component {component.name!r} names unknown source {component.source_id!r}.",
                            recommendation="Add the SourceRecord to DesignRecord.sources or remove the invalid link.",
                        )
                    )
        if self.design_record is not None:
            record_findings = self.design_record.validate()
            concept_ready = not any(
                finding.severity >= Severity.BLOCKING for finding in record_findings
            )
            requirement_statuses = [item.status for item in self.design_record.requirements]
            blockers_before_readiness = any(
                finding.severity >= Severity.BLOCKING for finding in findings
            )
            print_ready = (
                concept_ready
                and not blockers_before_readiness
                and bool(requirement_statuses)
                and "unverified" not in requirement_statuses
            )
            function_confirmed = (
                print_ready
                and bool(requirement_statuses)
                and all(
                    status in {"physically-tested", "function-confirmed"}
                    for status in requirement_statuses
                )
                and "function-confirmed" in requirement_statuses
            )
            claimed = self.design_record.readiness
            supported = {
                "concept-ready": concept_ready,
                "print-ready": print_ready,
                "function-confirmed": function_confirmed,
            }.get(claimed, False)
            if not supported:
                findings.append(
                    Finding(
                        "readiness.unsupported-claim",
                        Severity.BLOCKING,
                        f"The design claims {claimed!r} without the required evidence.",
                        evidence={
                            "concept_ready": concept_ready,
                            "print_ready": print_ready,
                            "function_confirmed": function_confirmed,
                        },
                        recommendation="Lower the readiness claim or resolve the findings and evidence gaps that control it.",
                    )
                )
        return findings

    def as_manifest(self) -> dict[str, Any]:
        findings = self.validate_metadata()
        record = self.design_record
        record_blocked = record is None or any(
            finding.severity >= Severity.BLOCKING for finding in record.validate()
        )
        requirement_statuses = [item.status for item in record.requirements] if record else []
        non_readiness_blocked = any(
            finding.severity >= Severity.BLOCKING
            and finding.code != "readiness.unsupported-claim"
            for finding in findings
        )
        concept_ready = not record_blocked
        print_ready = (
            concept_ready
            and not non_readiness_blocked
            and bool(requirement_statuses)
            and "unverified" not in requirement_statuses
        )
        function_confirmed = (
            print_ready
            and all(
                status in {"physically-tested", "function-confirmed"}
                for status in requirement_statuses
            )
            and "function-confirmed" in requirement_statuses
        )
        return {
            "schema_version": 2,
            "name": self.name,
            "parts": [
                {
                    "name": part.name,
                    "orientation": part.orientation,
                    "material": part.material,
                    "color": part.color,
                    "expected_solids": part.expected_solids,
                    "expected_size_mm": list(part.expected_size_mm) if part.expected_size_mm else None,
                    "size_tolerance_mm": part.size_tolerance_mm,
                    "expected_volume_range_mm3": (
                        list(part.expected_volume_range_mm3)
                        if part.expected_volume_range_mm3
                        else None
                    ),
                    "critical_dimensions": part.critical_dimensions,
                    "features": [feature.as_dict() for feature in part.features],
                    "notes": part.notes,
                    "print_plan": part.print_plan.as_dict() if part.print_plan else None,
                }
                for part in self.parts
            ],
            "reference_components": [
                component.as_dict() for component in self.reference_components
            ],
            "assembly": self.assembly.as_dict(),
            "assembly_checks": [check.as_dict() for check in self.assembly_checks],
            "design_record": self.design_record.as_dict() if self.design_record else None,
            "readiness": {
                "claimed": self.design_record.readiness if self.design_record else None,
                "concept_ready": concept_ready,
                "print_ready": print_ready,
                "function_confirmed": function_confirmed,
            },
            "assumptions": self.assumptions,
            "bom": self.bom,
            "assembly_instructions": self.assembly_instructions,
            "review_annotations": [annotation.as_dict() for annotation in self.review_annotations],
            "design_deltas": [delta.as_dict() for delta in self.design_deltas],
            "findings": [finding.as_dict() for finding in findings],
            "blocked": any(finding.severity >= Severity.BLOCKING for finding in findings),
        }
