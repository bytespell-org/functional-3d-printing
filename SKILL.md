---
name: functional-3d-printing
description: Design, revise, validate, preview, and document small functional FDM parts and assemblies with CadQuery. Use for electronics enclosures, covers, fits, rails, clips, brackets, mounts, adapters, magnets, screws, inserts, printed threads, moving mechanisms, and fit tests. Do not use for decorative models, slicing, printer control, queues, uploads, or print-now workflows.
---

# Functional 3D printing

Design from the assembly backward. A clean mesh or attractive shell is not enough; every component must enter, attach, function, and leave again through modeled paths.

## Tools and records

- Use CadQuery for editable B-rep CAD and STEP/STL export.
- Use `cq_warehouse` for standard hardware and `functional_fdm` for profiles, primitives, records, and checks.
- Return a `DesignBundle` from `build()` and generate with `scripts/run_model.py`.
- Keep dimensions, assumptions, decisions, and test intent in `DesignRecord` inside the model.
- Keep only a short summary, progress, and model comments in `progress.json`; mutate it with `scripts/update_progress.py`.
- Append physical results with `scripts/record_iteration.py`; never turn CAD evidence into a physical claim.
- Use the compiled Three.js workbench in `assets/preview`; source lives in `workbench/`.

Read [references/sources-and-runtime.md](references/sources-and-runtime.md) before installing the CAD runtime.

## Assembly-first workflow

1. **Identify and research the exact hardware.** Resolve the board/product variant and revision first. Search official manufacturer product pages, documentation, repositories, and CAD downloads before asking the user for dimensions; then use authorized distributor material as a secondary source. Record source URLs, revision, license, and what the model proves. Ask only for missing physical measurements that change the design. Put supplied dimensions in one `known_dimensions_mm` map and model every fit-controlling item as a non-printable `ReferenceComponent`, including plugs, wire exits, bend space, tools, fastener heads, and moving hardware.
2. **Write the reversible assembly sequence.** State how each component enters, seats, attaches, connects, and is removed after wiring. Define one coordinate frame and insertion direction for every motion. Ask only when a missing answer changes fit, architecture, normal use, loading, heat, safety, or service.
3. **Assign ownership and load paths.** Say which printed part retains each component and where forward, rearward, torque, and service loads end. A closure may not silently retain unrelated hardware. Reject floating retainers, one-sided stops, inaccessible fasteners, and parts that can move together out of the body.
4. **Choose architecture before surface design.** Decide part count, joints, hardware, service cycle, print orientation, and the smallest test that isolates uncertain fit or strength. Do not require material or hardware the user has not supplied without asking.
5. **Build the functional skeleton.** Model passages, datums, bearing faces, bosses, mating surfaces, wire routes, keep-outs, tool columns, and component trays before the ergonomic shell. Prefer short broad supports, continuous walls, gussets, and direct compression/shear paths over tall towers or delicate PLA flexures.
6. **Prove movement and access.** Build an `AssemblyGraph`. Check final interference and the complete insertion/removal path for every interface. Check each plug, cable, tool, and service envelope against every printed part it traverses with `check_access_envelope`; do not hand-pick a partial pair list. Model opposing bearing faces and numeric gaps for every retained direction.
7. **Apply FDM architecture, then the shell.** Give every critical layer a supported path, bounded two-ended bridge, or reviewed removable-support plan. Keep precision faces away from support. Build the approved exterior last, then intersect internal supports with it so bosses and magnet bridges cannot escape the silhouette.
8. **Generate and inspect.** Run `scripts/run_model.py`; inspect mesh audits, static views, and the browser workbench. Isolate printed parts and hardware, inspect internals and underside, and verify that the live manifest references every existing model file. Treat generated renders as evidence only after opening them.
9. **Work comments directly.** After sharing the workbench, run `update_progress.py show`. Change the model and evidence, then remove the addressed comment with `comment-remove`; do not reply or add statuses.
10. **Share observably.** Start `scripts/serve_preview.py <output>/preview --daemon` once and keep regenerating into the same output directory. The open workbench picks up atomic manifest revisions automatically; do not restart the server or ask the user to refresh. Update the short progress summary before a longer CAD run, verify the viewer, model URLs, and comment flow, then give the LAN URL. After physical feedback, record one observation and the smallest responsible next change in the iteration JSONL.

## Model minimum

Return named printable `DesignPart` objects, contextual `ReferenceComponent` objects, an `AssemblyGraph`, a `DesignRecord`, reviewed `PrintPlan` objects, and numeric assembly checks. Reference components belong in review and clearance checks, never printable output.

```python
from functional_fdm import AssemblyGraph, DesignBundle, DesignPart, DesignRecord, PrintPlan, ReferenceComponent

def build():
    return DesignBundle(
        name="example",
        parts=[DesignPart("body", body, "open side up", "PLA", print_plan=PrintPlan(
            support_mode="none", reviewed=True,
            review_evidence="Inspected the exported orientation and support audit.",
        ))],
        reference_components=[ReferenceComponent("battery", battery, nominal_size_mm=(25, 40, 10))],
        assembly=AssemblyGraph({"body"}),
        design_record=DesignRecord(
            intent="State the required function.",
            known_dimensions_mm={"measured_width": 42.0},
            assumptions=["Battery dimensions are nominal until measured."],
            prototype_stage="concept",
            test_plan=["Verify the uncertain fit before the full assembly."],
        ),
    )
```

```bash
python scripts/run_model.py model.py --output-dir /chosen/output/design-name
python scripts/update_progress.py init /chosen/output/design-name/progress.json --title "Design name"
python scripts/serve_preview.py /chosen/output/design-name/preview --daemon
```

## Reference routing

- Enclosures and load paths: [references/enclosures-assembly.md](references/enclosures-assembly.md)
- Fits and small tests: [references/fits-calibration.md](references/fits-calibration.md)
- Fasteners: [references/fasteners-inserts-threads.md](references/fasteners-inserts-threads.md)
- Joints and magnets: [references/joints-mechanisms.md](references/joints-mechanisms.md)
- Snaps and flexures: [references/snaps-clips.md](references/snaps-clips.md)
- Material and strength: [references/materials-strength.md](references/materials-strength.md)
- Orientation and supports: [references/orientation-supports.md](references/orientation-supports.md)
- Validation and delivery: [references/validation-delivery.md](references/validation-delivery.md)
- Clarification and evidence: [references/design-process.md](references/design-process.md)
- Physical feedback: [references/iteration-loop.md](references/iteration-loop.md)
- Visual review: [references/visual-review.md](references/visual-review.md)
- Workbench operation: [references/observable-workbench.md](references/observable-workbench.md)

## Stop conditions

Do not call a design ready while any fit-controlling dimension, material dependency, retention direction, hardware path, insertion/removal path, load path, print plan, mesh audit, browser review, or blocking finding remains unresolved. Distinguish modeled, geometry-checked, FDM-plausible, physically tested, and function-confirmed claims.

Run `scripts/validate_portability.py` before public distribution.
