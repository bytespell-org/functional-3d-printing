"""Functional FDM mechanical-design helpers."""

from .materials import MaterialProfile, material_profile
from .assembly_checks import (
    check_assembly_insertion_path,
    check_assembly_interference,
    check_fastener_stack,
    check_linear_travel,
    check_tool_access,
)
from .model import (
    AssemblyCheckResult,
    AssemblyGraph,
    BridgeSpec,
    DesignBundle,
    DesignDelta,
    DesignDecision,
    DesignPart,
    DesignRecord,
    FeatureResult,
    Finding,
    FunctionalRequirement,
    InterfaceSpec,
    PrintPlan,
    ReviewAnnotation,
    Severity,
)
from .profile import FitProfile

__all__ = [
    "AssemblyCheckResult",
    "AssemblyGraph",
    "BridgeSpec",
    "DesignBundle",
    "DesignDelta",
    "DesignDecision",
    "DesignPart",
    "DesignRecord",
    "FeatureResult",
    "Finding",
    "FitProfile",
    "FunctionalRequirement",
    "InterfaceSpec",
    "PrintPlan",
    "ReviewAnnotation",
    "MaterialProfile",
    "Severity",
    "material_profile",
    "check_assembly_insertion_path",
    "check_assembly_interference",
    "check_fastener_stack",
    "check_linear_travel",
    "check_tool_access",
]
