"""Functional CAD source of truth.

Replace this example with the known measurements, intended behavior, current
assumptions, design decisions, and physical-test results for the real part.
Keep generated STEP, STL, renders, and previews outside this source file.
"""

import cadquery as cq

from functional_fdm import (
    AssemblyGraph,
    DesignBundle,
    DesignDecision,
    DesignPart,
    DesignRecord,
    FitProfile,
    FunctionalRequirement,
    PrintPlan,
    ReferenceComponent,
    ReviewAnnotation,
)
from functional_fdm.primitives import enclosure_shell


def build() -> DesignBundle:
    profile = FitProfile(printer="unknown", nozzle_mm=0.4, material="PETG")
    shell = enclosure_shell(
        internal_length_mm=50,
        internal_width_mm=30,
        internal_height_mm=15,
        wall_mm=1.8,
        floor_mm=1.8,
        profile=profile,
    )
    if shell.geometry is None:
        raise RuntimeError("CadQuery geometry was not created.")
    part = DesignPart(
        name="base",
        geometry=shell.geometry,
        orientation="flat floor on bed; open side up",
        material="PETG",
        expected_size_mm=(53.6, 33.6, 16.8),
        size_tolerance_mm=0.05,
        features=[shell],
        notes=["Example only. Replace all dimensions with measured requirements."],
        print_plan=PrintPlan(
            support_mode="none",
            reviewed=True,
            review_evidence="Open-side-up shell has no horizontal internal roof or declared bridge.",
        ),
    )
    graph = AssemblyGraph({"base"})
    battery_envelope = cq.Workplane("XY").box(
        25.0, 40.0, 10.0, centered=(True, True, False)
    )
    record = DesignRecord(
        intent="Demonstrate the required function with the smallest useful prototype.",
        known_dimensions_mm={
            "internal_length": 50.0,
            "internal_width": 30.0,
            "internal_height": 15.0,
        },
        requirements=[
            FunctionalRequirement(
                "holds-envelope",
                "The part contains the measured internal envelope without interference.",
                status="cad-checked",
                verification_method="Numeric envelope and collision checks",
            )
        ],
        assumptions=["Desktop FDM with a 0.4 mm nozzle."],
        available_materials=[],
        additional_hardware=[],
        decisions=[
            DesignDecision(
                "Start with one open enclosure shell.",
                "This is the smallest geometry that tests the measured envelope.",
            )
        ],
        prototype_stage="concept",
        test_plan=["Use a small fit test if the rendered interface leaves a material uncertainty."],
    )
    return DesignBundle(
        name="functional-cad-example",
        parts=[part],
        reference_components=[
            ReferenceComponent(
                name="battery",
                geometry=battery_envelope,
                color="#38bdf8",
                opacity=0.38,
                position_mm=(0.0, 0.0, 1.8),
                nominal_size_mm=(25.0, 40.0, 10.0),
                notes=["Nominal envelope; replace with a physical measurement."],
            )
        ],
        assembly=graph,
        assumptions={"nozzle_mm": profile.nozzle_mm, "material": profile.material},
        design_record=record,
        review_annotations=[
            ReviewAnnotation(
                "internal-envelope",
                "Internal envelope center",
                (0.0, 0.0, 8.4),
                part="base",
                description="Stable name for discussing envelope position and clearance.",
            )
        ],
    )
