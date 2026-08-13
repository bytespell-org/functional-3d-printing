---
name: functional-3d-printing
description: Design, revise, validate, preview, and document small functional FDM parts and assemblies with CadQuery. Use for electronics enclosures, covers, press and sliding fits, rails, dovetails, clips, cantilever snaps, detents, hinges, brackets, mounts, adapters, knobs, bushings, magnets, tiny screws, captive nuts, heat-set inserts, printed threads, small fit tests, STEP/STL exports, assembly reasoning, FDM orientation, support avoidance, and physical-test learning. Do not use for decorative models, slicer automation, printer control, queues, uploads, or print-now workflows.
---

# Functional FDM Mechanical CAD

Create geometry that has a high probability of assembling and working after FDM manufacture. Keep the work observable in a durable progress sidecar. A valid or attractive model is not sufficient.

## Boundary

This skill produces CAD, validation, previews, calibration pieces, and process recommendations. It does not slice, upload, queue, or control a printer. Do not call printer APIs. Do not add a slicer dependency.

## Mechanical truth gate

Before proposing a joint, state what surface carries each required load and whether that surface can be printed in the chosen orientation.

- A rotating lug can resist axial pull only when it passes under a retention surface. That underside is a roof in the print analysis. If no retention surface exists, the joint is not an axially captured bayonet.
- A feature on a vertical wall can still start above empty space. Its location does not prove layer support.
- At concept stage, call support-free behavior `unverified`. Claim support-free only after the print-oriented section, mesh audit, and `PrintPlan` show a supported path for every critical layer.
- If function and support-free manufacture conflict, change the architecture. Do not hide the conflict with chamfers, small dimensions, or optimistic printer assumptions.

## Default stack

- Use CadQuery for parametric B-rep CAD and STEP/STL export.
- Use `cq_warehouse` for standards-based fasteners, clearance holes, captive nuts, heat-set inserts, and modeled threads.
- Use the bundled `functional_fdm` package for fit profiles, feature metadata, assembly interfaces, functional primitives, and semantic checks.
- Use `scripts/run_model.py` for bounded execution, validation, export, static renders, interactive preview, and `DESIGN.md`.
- Use `scripts/update_progress.py` for the canonical `progress.json` sidecar. Record every user answer, explicit assumption, workflow update, and reusable learning through this script. Do not edit the sidecar by hand.
- Use the compiled shadcn/Three.js workbench in `assets/preview`. Its source is in `workbench/` and is generated from the recorded shadcn preset in `workbench/components.json`.
- Use OpenSCAD only when a source model already uses it or a simple parametric operation has a clear advantage.
- Do not use mesh-first modeling for ordinary mechanical parts.

Read [references/sources-and-runtime.md](references/sources-and-runtime.md) before you install the CAD runtime or use `cq_warehouse`.

## Required workflow

1. Choose the generated-output directory and initialize `<output>/progress.json` before asking design questions. Use `scripts/update_progress.py init`. The script owns this file and writes it atomically.
2. Collect the intended function and every supplied dimension from the request, photos, listings, drawings, and existing source. Keep one simple `known_dimensions_mm` map. Record each supplied answer in the progress sidecar immediately. After sharing the workbench, inspect `review_comments` at the start of every turn. Reply to new comments, acknowledge them when the requested action is understood, and resolve them only after the model and evidence are updated. Do not create separate nominal, measured, estimated, or provisional measurement classes.
3. Treat a supplied dimension as known and use it. Check the progress sidecar and design record before asking for a dimension. Never ask for a known value as if it is missing. If final fit needs confirmation, cite the recorded value and explain the exact reason for confirming it. Do not request a complete printer profile or hardware inventory.
4. Ask only when a missing answer can materially change fit, architecture, safety, or normal use. Group related blocking questions into one short request. Otherwise record an explicit assumption with `update_progress.py answer --status assumed` and continue.
5. Keep a durable `DesignRecord` in the editable Python model. Record intent, known dimensions, functional requirements, assumptions, open questions, decisions, extra hardware, prototype stage, and test plan. Use the module docstring for the short human summary. The model record owns design metadata; `progress.json` owns the cross-turn activity trail visible in the workbench.
6. Keep each design choice `proposed` until the user explicitly approves that exact choice. An approval of size, shape, material, or one mechanism does not approve glue, magnets, fasteners, part count, permanent assembly, or another unmentioned choice. Record a concise approval basis for every `user-approved` decision and record the answer in the sidecar.
7. Create an initial CAD proposal. Choose the assembly architecture, part count, interfaces, insertion directions, removability, print orientation, and service method. Do not wait for every minor dimension. Update the proposal step with a summary and evidence after generation.
8. If the proposal depends on a material other than ordinary PLA or on extra items not already supplied, ask whether the user has them before making the design depend on them. Examples include PETG, TPU, magnets, inserts, screws, springs, bearings, and adhesives.
9. Generate and inspect useful images. Show assembled, exploded, internal, and print-orientation views as applicable. Explain operation, installation movement, hardware, assumptions, and FDM risks. Add stable annotations for features that the user might discuss or move. Use one coordinate frame and the common vocabulary in [references/visual-review.md](references/visual-review.md). Align with the user before a full-cost prototype.
10. Create a functional skeleton. Model envelopes, mating surfaces, axes, joint locations, hardware paths, wire bends, tool access, and keep-out zones.
11. Create or load a `FitProfile` only when useful. Do not ask the user for calibration data by default. If an uncertain fit controls success, propose a small fit or mechanism test only after the user approves the interface that it tests. Show the test, name the exact question it answers, state what it does not test, and explain how the result changes the full model. Ask before preparing it unless the user already requested a test.
12. Use reusable primitives. Each feature must return geometry plus assumptions, dimensions, findings, and print notes.
13. Apply FDM design rules. Treat a supported layer path as the default. Allow printing above empty space only for a declared short bridge with supported anchors at both ends or for a reviewed removable-support plan. Align load-bearing flexures with layers. Protect precision faces from support. Replace steep unsupported surfaces, trapped roofs, one-ended ledges, and unsupported capture lips with chamfers, arches, teardrops, open edges, supported ramps, or split parts.
    - Gotcha: a bayonet or twist-lock track usually creates a roof, capture lip, or slot closure. Do not call it support-free because the slot is small or hidden. Treat every track roof as a precision bridge candidate. Prefer an open-edge track, supported ramp, separate ring, split part, or another closure when the retention face would print above empty space.
    - Evidence rule: at concept stage, mark support-free behavior `unverified`. Do not claim zero supports, no horizontal overhangs, or a printable hidden track until the actual print-oriented geometry has a section view, mesh audit, and reviewed `PrintPlan`.
14. Build a `DesignBundle` with named parts and an `AssemblyGraph`. Record every interface and insertion direction. Add final-state interference and insertion-path checks for every mating part pair.
15. Use the output directory selected for the sidecar. Prefer an explicit caller path. Otherwise use the tool's project build default. Do not generate beside editable source without explicit `--in-place` intent. Do not edit project ignore files.
16. Run `scripts/run_model.py`. Inspect each generated `*.mesh-audit.json` and the manifest's `printability_audit`. Reject invalid solids, wrong solid counts, mesh faults, missing assembly data, unresolved horizontal candidates, and `BLOCKING` findings. Do not accept a model-authored “support-free” claim as evidence.
17. Inspect all static views and the browser preview. Check missing cutouts, reversed parts, access, alignment, proportions, hidden collisions, snap direction, assembly sequence, and whether the prototype tests its stated function. For a position or size revision, add a `DesignDelta` tied to a visible `ReviewAnnotation`. Show before, after, signed delta, direction, and reason. Do not rely on words such as higher, lower, left, or behind without the defined frame.
18. Deliver the observable interactive workbench during design review. Start `scripts/serve_preview.py <output>/preview --daemon`; a generic static server cannot accept model comments. The detached process must survive the calling agent process. Verify the viewer, manifest, model files, annotations, comment creation, proposed changes, and live progress sidecar. Give the user the clickable local-network URL printed in `urls`; never communicate a `127.0.0.1` or `localhost` URL. If direct LAN access is unavailable, use the environment's approved port-sharing method. If no sharing method exists, package the complete output, state that interactive delivery is unavailable, and continue with annotated static images. Do not silently omit the workbench.
19. Get visual approval for each pending design delta before recommending its physical test. Record the accepted delta as `visually-approved`. Then prepare the smallest useful physical test for each uncertain fit or mechanism. Use plain language such as “small fit test.” Provide print orientation, material recommendation, success criteria, exact assembly instructions, and the decision that the result will inform. This skill does not operate a slicer or printer.
20. Record physical feedback with `scripts/record_iteration.py`, in the Python design record, and as a learning in `progress.json`. Distinguish modeled, geometry-checked, FDM-plausible, physically tested, and function-confirmed claims. Keep new learnings `candidate` until the learning rule allows promotion.
21. Build the complete object only after critical tests pass or the user accepts the remaining risk. Run `scripts/validate_portability.py` before public distribution. Deliver editable source separately from generated output.

## Reference routing

- Read [references/fits-calibration.md](references/fits-calibration.md) for all mating dimensions and small fit tests.
- Read [references/snaps-clips.md](references/snaps-clips.md) for snaps, clips, latches, and cantilever checks.
- Read [references/fasteners-inserts-threads.md](references/fasteners-inserts-threads.md) for screws, bosses, captive nuts, inserts, and threads.
- Read [references/joints-mechanisms.md](references/joints-mechanisms.md) for rails, dovetails, hinges, detents, magnets, and bayonets.
- Read [references/enclosures-assembly.md](references/enclosures-assembly.md) for electronics and multipart architecture.
- Read [references/materials-strength.md](references/materials-strength.md) for material and structural recommendations.
- Read [references/orientation-supports.md](references/orientation-supports.md) for FDM orientation, overhangs, bridges, and support avoidance.
- Read [references/validation-delivery.md](references/validation-delivery.md) before declaring a design ready.
- Read [references/iteration-loop.md](references/iteration-loop.md) after physical feedback.
- Read [references/design-process.md](references/design-process.md) for clarification policy, proposal review, hardware checks, source records, and phased prototype gates.
- Read [references/visual-review.md](references/visual-review.md) whenever the user reviews, identifies, moves, resizes, or compares visible features.
- Read [references/observable-workbench.md](references/observable-workbench.md) before initializing, updating, serving, or handing off the progress sidecar and workbench.

## Model contract

Create a Python file with `build()` that returns `functional_fdm.DesignBundle`.

```python
from functional_fdm import AssemblyGraph, DesignBundle, DesignDelta, DesignPart, DesignRecord, FitProfile, PrintPlan, ReviewAnnotation

def build():
    profile = FitProfile(printer="unknown", nozzle_mm=0.4, material="PETG")
    # Build CadQuery geometry and feature results here.
    graph = AssemblyGraph({"base"})
    return DesignBundle(
        name="example",
        parts=[DesignPart(
            "base",
            geometry,
            "flat floor on bed; open side up",
            "PETG",
            print_plan=PrintPlan(
                support_mode="none",
                reviewed=True,
                review_evidence="Inspected the exported orientation and support-risk audit.",
            ),
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
        design_deltas=[DesignDelta(
            "usb-c-opening", "center_z", 7.2, 6.2, "mm", "-Z toward base",
            "Align the opening with the connector center.", review_status="proposed"
        )],
    )
```

Run it in the CadQuery environment. Supply an output directory when the caller has one:

```bash
python scripts/run_model.py model.py --output-dir /chosen/output/design-name
```

Without `--output-dir`, a Git project uses `build/functional-fdm/<design-name>/`. A standalone model uses a reported temporary directory. The tool reports whether a project output is tracked or ignored. It never modifies `.gitignore`. Use `--in-place` only when generated files beside the source are intentional.

Initialize the progress sidecar before asking design questions:

```bash
python scripts/update_progress.py init /chosen/output/design-name/progress.json --title "Design name"
```

Record answers and work as it happens. See the observable-workbench reference for all commands. Start the generated viewer as a detached LAN service:

```bash
python scripts/serve_preview.py /chosen/output/design-name/preview --daemon
```

The command prints one or more LAN URLs and writes server PID, log, and connection metadata beside the output. Verify the URL and communicate it to the user.

## Mandatory stop conditions

Do not declare the design ready when any condition applies:

- A missing dimension can change fit, retention, load, heat, electrical safety, or assembly.
- A critical fit has no approved small fit test or other adequate evidence.
- A snap exceeds its conservative strain limit or flexes across weak layers without a justified test.
- A screw, insert, driver, wire, plug, magnet, hinge, or moving part lacks a complete envelope or path.
- A fastener can enter a PCB, battery, wire, exterior surface, or protected cavity.
- Exported bounds or volume differ from the declared part envelope.
- A precision interface is support-sensitive without a validated reason.
- A print-oriented part lacks a reviewed `PrintPlan`.
- A support-free claim has unresolved horizontal candidates or undeclared spans.
- A support-free claim is based only on a concept description, feature location, or valid solid instead of exported-orientation evidence.
- A captured bayonet lug has no modeled axial retention roof, or its retention roof has no supported-layer plan.
- A declared bridge lacks supported anchors at both ends, numeric span, or review evidence.
- A steep unsupported region controls fit, locking, movement, sealing, optical quality, or user safety.
- A trapped cavity requires inaccessible support.
- A part has invalid geometry, wrong solid count, boundary edges, or non-manifold edges.
- An assembly interface has no insertion direction or cannot be serviced as required.
- A multipart interface lacks numeric final-state interference and insertion-path checks using the actual assembled geometry.
- Any semantic finding is `BLOCKING`.
- The agent generated renders but did not inspect them.
- The progress sidecar is missing, invalid, stale relative to the current work, or omits a user answer.
- The workbench does not display the same answers, steps, and learnings stored in `progress.json`.
- The agent did not deliver the interactive preview or explicitly report that the environment cannot expose it.
- The preview server will die with the agent process, or the shared URL uses `127.0.0.1` or `localhost`.
- A position or size revision lacks a stable annotation, numeric before/after values, signed delta, defined direction, or visual review.
- A proposed design delta is sent to a physical-test workflow before the user visually approves it.
- A claimed physical behavior has no matching evidence level or test criterion.
- A design choice is marked `user-approved` without evidence that the user approved that exact choice.

## Learning rule

One failed print is evidence, not a universal rule. Record it as a candidate. Promote a lesson only after two independent reproductions, a measured small test, or a geometry/mechanics proof. Update the reference or tool, add a regression test, run all benchmarks, validate the skill, and rebuild the archive.
