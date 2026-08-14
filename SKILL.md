---
name: functional-3d-printing
description: Design, revise, validate, preview, and document small functional FDM parts and assemblies with CadQuery. Use for electronics enclosures, covers, press and sliding fits, rails, dovetails, clips, cantilever snaps, detents, hinges, brackets, mounts, adapters, knobs, bushings, magnets, tiny screws, captive nuts, heat-set inserts, printed threads, and small fit tests. Do not use for decorative models, slicer automation, printer control, queues, uploads, or print-now workflows.
---

# Functional 3D printing

Create geometry that has a high probability of assembling and working after FDM manufacture. A valid or attractive model is not sufficient. Keep the design record in the editable model, physical observations in the iteration JSONL, and the shared browser review limited to progress plus comments anchored directly to the model.

## Default stack

- Use CadQuery for parametric B-rep CAD and STEP/STL export.
- Use `cq_warehouse` for standards-based fasteners, clearance holes, captive nuts, heat-set inserts, and modeled threads.
- Use `functional_fdm` for fit profiles, feature metadata, assembly interfaces, functional primitives, and semantic checks.
- Use `scripts/run_model.py` for bounded execution, validation, export, static renders, interactive preview, and `DESIGN.md`.
- Use `DesignRecord` in the editable Python model as the only record for dimensions, assumptions, open questions, and design decisions. Do not duplicate those facts in `progress.json`.
- Use `scripts/record_iteration.py` as the only physical-learning record. It appends JSONL beside the design or in a user-selected notes location.
- Use `scripts/update_progress.py` only for the review sidecar: a short summary, visible progress items, and model comments. Do not edit its JSON by hand.
- Use the compiled shadcn/Three.js workbench in `assets/preview`; its source is `workbench/`.

Read [references/sources-and-runtime.md](references/sources-and-runtime.md) before installing the CAD runtime or using `cq_warehouse`.

## Workflow

1. Choose a generated-output directory and initialize `<output>/progress.json` with `scripts/update_progress.py init`. Add only useful milestones with `progress`; no prescribed phases or completion ritual applies.
2. Collect intent and supplied dimensions from the request, photos, listings, drawings, and source. Keep one `known_dimensions_mm` map in `DesignRecord`. Treat supplied dimensions as known; ask only when a missing value changes fit, architecture, safety, or normal use. Record explicit assumptions and choices in `DesignRecord` and avoid separate measurement classes.
3. Make an initial CAD proposal without waiting for minor dimensions. Decide architecture, part count, interfaces, insertion directions, removability, print orientation, service method, and any additional hardware. If it depends on material or hardware the user has not supplied, ask before making it required.
4. Show useful assembled, exploded, internal, and print-orientation views. Add stable annotations where a person might point to a feature. Use the defined coordinate frame in [references/visual-review.md](references/visual-review.md), but do not require a separate approval ceremony before continuing.
5. Build a functional skeleton: envelopes, mating surfaces, axes, joint locations, hardware paths, wire bends, tool access, and keep-out zones. Add every supplied component that controls fit or placement as a `ReferenceComponent`; use an exact model when available and a clearly noted measured or nominal envelope otherwise. Use reusable primitives and a `FitProfile` when useful. Propose the smallest fit or mechanism test when uncertainty controls success.
6. Apply FDM rules. Every critical layer needs a supported path, an explicitly bounded bridge with anchors at both ends, or a reviewed removable-support plan. Align load-bearing flexures with layers, keep precision surfaces away from support, and replace trapped roofs, one-ended ledges, and unsupported capture lips with printable architecture.
7. Build a `DesignBundle` with named printable parts, non-printable reference components, and an `AssemblyGraph`. Record every interface and insertion direction. Add final-state interference and insertion-path checks for every mating pair, including hardware references where they control clearance or placement. Reference components appear in the review scene but never in the printable `parts/` output or its printability audits.
8. Run `scripts/run_model.py`, inspect its mesh audits and printability audit, then inspect every static render and browser preview. Check cutouts, orientation, access, alignment, hidden collisions, snap direction, assembly sequence, and whether the prototype tests its stated function.
9. During review, the user annotates the model with the floating **Add comment** action. Comments stay visible on the model and open in place when selected. At the start of each turn after sharing the workbench, inspect them with `update_progress.py show`. Work the comment into the model and evidence, then resolve it by removing it with `comment-remove`. Do not reply to, acknowledge, or status comments.
10. Start `scripts/serve_preview.py <output>/preview --daemon` for interactive review. Verify the viewer, manifest, model files, comment creation/removal, and live sidecar. Give the user the LAN URL printed in `urls`, never a localhost URL. If sharing is unavailable, report that and deliver annotated static images.
11. After a physical test, append the observation, conditions, result, and next decision with `scripts/record_iteration.py`. Distinguish modeled, geometry-checked, FDM-plausible, physically tested, and function-confirmed claims. Build the complete object only after critical tests pass or the user accepts the remaining risk. Run `scripts/validate_portability.py` before public distribution.

## Reference routing

- Read [references/fits-calibration.md](references/fits-calibration.md) for mating dimensions and fit tests.
- Read [references/snaps-clips.md](references/snaps-clips.md) for snaps, clips, latches, and cantilever checks.
- Read [references/fasteners-inserts-threads.md](references/fasteners-inserts-threads.md) for screws, bosses, captive nuts, inserts, and threads.
- Read [references/joints-mechanisms.md](references/joints-mechanisms.md) for rails, dovetails, hinges, detents, magnets, and bayonets.
- Read [references/enclosures-assembly.md](references/enclosures-assembly.md) for electronics and multipart architecture.
- Read [references/materials-strength.md](references/materials-strength.md) for material and structural recommendations.
- Read [references/orientation-supports.md](references/orientation-supports.md) for FDM orientation, overhangs, bridges, and support avoidance.
- Read [references/validation-delivery.md](references/validation-delivery.md) before declaring a design ready.
- Read [references/iteration-loop.md](references/iteration-loop.md) after physical feedback.
- Read [references/design-process.md](references/design-process.md) for clarification policy, proposal review, hardware checks, and source records.
- Read [references/visual-review.md](references/visual-review.md) when the user reviews a visible feature.
- Read [references/observable-workbench.md](references/observable-workbench.md) before initializing, serving, or handing off the workbench.

## Model contract

Create a Python file with `build()` that returns `functional_fdm.DesignBundle`.

```python
from functional_fdm import AssemblyGraph, DesignBundle, DesignPart, DesignRecord, FitProfile, PrintPlan, ReferenceComponent, ReviewAnnotation

def build():
    profile = FitProfile(printer="unknown", nozzle_mm=0.4, material="PETG")
    graph = AssemblyGraph({"base"})
    return DesignBundle(
        name="example",
        parts=[DesignPart(
            "base", geometry, "flat floor on bed; open side up", "PETG",
            print_plan=PrintPlan(
                support_mode="none", reviewed=True,
                review_evidence="Inspected the exported orientation and support-risk audit.",
            ),
        )],
        reference_components=[ReferenceComponent(
            "battery", battery_envelope,
            color="#38bdf8", opacity=0.38,
            position_mm=(0.0, 0.0, 2.0),
            nominal_size_mm=(25.0, 40.0, 10.0),
            notes=["Nominal supplier envelope; verify with physical measurement."],
        )],
        assembly=graph,
        assumptions={"nozzle_mm": profile.nozzle_mm, "material": profile.material},
        design_record=DesignRecord(
            intent="State what the object must do.",
            known_dimensions_mm={"measured_width": 42.0},
            assumptions=["State each unconfirmed value or behavior."],
            prototype_stage="concept",
            test_plan=["Review the rendered concept, then isolate the uncertain fit."],
        ),
        review_annotations=[ReviewAnnotation(
            "usb-c-opening", "USB-C opening center", (26.6, 0.0, 6.2), part="base"
        )],
    )
```

Run the model in its CadQuery environment, supplying an output directory when the caller has one:

```bash
python scripts/run_model.py model.py --output-dir /chosen/output/design-name
python scripts/update_progress.py init /chosen/output/design-name/progress.json --title "Design name"
python scripts/serve_preview.py /chosen/output/design-name/preview --daemon
```

## Mandatory stop conditions

Do not declare a design ready when a material issue remains:

- A missing dimension changes fit, retention, load, heat, electrical safety, or assembly.
- A critical fit has no adequate fit-test evidence.
- A snap exceeds its conservative strain limit or flexes across weak layers without a justified test.
- Hardware, wire, tool, and moving-part envelopes or paths are incomplete; a fastener can enter a protected volume.
- Exported bounds or volume disagree with the declared envelope, or the mesh is invalid, wrong-count, open, or non-manifold.
- A precision interface is support-sensitive without a validated print plan; a support-free claim has unresolved horizontal candidates, undeclared spans, or unsupported bridge anchors.
- A trapped cavity, capture lip, steep unsupported region, or bayonet retention roof controls fit, movement, sealing, optical quality, or safety without a printable plan.
- An assembly lacks insertion direction, service access, numeric final-state interference, or insertion-path checks against actual geometry.
- Any semantic finding is `BLOCKING`, or renders and the browser preview were not inspected.
- A claimed physical behavior lacks a matching test criterion and JSONL iteration record.
- The interactive preview cannot create and remove comments, unless the environment cannot expose it and that limitation is explicitly reported.
