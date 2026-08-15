---
name: functional-3d-printing
description: Design, revise, validate, preview, and document functional FDM parts and small assemblies with CadQuery. Use for spacers, knobs, brackets, adapters, mounts, replacement parts, electronics enclosures, calibrated fits, clips, rails, hinges, magnets, fasteners, threads, and mechanism tests. Do not use for decorative models, slicing, printer control, uploads, queues, or print-now workflows.
---

# Functional 3D printing

Create the smallest testable CAD solution. Work backward from fit, load, assembly, service, and print orientation. Validate the risks actually present; do not turn a simple part into an enclosure workflow or a CAD check into a physical claim.

## Scale the workflow

**Simple part** — One-piece spacers, knobs, brackets, adapters, mounts, and replacements need a `DesignBundle`, named `DesignPart` objects, `DesignRecord`, reviewed `PrintPlan`, valid geometry, mesh inspection, and an `AssemblyGraph` that may have one part and no interfaces. Add no hardware references, assembly checks, sidecar, server, comments, or iteration log unless useful.

**Fit or assembly** — Escalate for mating parts, fit-controlling objects, connectors, cables, fasteners, magnets, joints, threads, or motion. Add only the relevant `ReferenceComponent` and `SourceRecord` provenance, `InterfaceSpec` records, numeric checks, and small fit or mechanism tests. Read the mechanism-specific references before modeling.

**Collaborative iteration** — Use annotations, `progress.json`, comments, the live workbench, and physical-iteration JSONL only when visual collaboration or repeated revisions justify them. Otherwise keep the generated preview and static images as artifacts without starting a server.

## Core workflow

1. Capture intent and supplied dimensions. For exact hardware, identify the variant and research primary manufacturer sources before asking for missing fit-controlling measurements; see [sources-and-runtime.md](references/sources-and-runtime.md).
2. Choose the smallest architecture and test that preserve the real load, fit, motion, and print orientation. For assemblies, define ownership, interfaces, reversible sequence, and service access before shaping the shell; see [enclosures-assembly.md](references/enclosures-assembly.md).
3. Build editable CadQuery geometry and return `DesignBundle`. Use the maintained [model template](assets/functional-cad-project/model.py) rather than copying an inline example.
4. Validate only applicable risks. Straight insertion checks prove sampled translation only; use rotational or explicit sampled poses for hinges, bayonets, curved, or compound motion. See [validation-delivery.md](references/validation-delivery.md).
5. Run the model, inspect the exported meshes and views, and report evidence at its actual level. Record physical results only after a physical test.

## Output contract

- Preserve editable Python source plus generated STEP, STL, manifest, and useful review images.
- Give every printable part a reviewed `PrintPlan` in its exported orientation.
- Keep non-printable hardware in `ReferenceComponent` objects and out of printable outputs.
- Keep assumptions, requirements, decisions, readiness, tests, and provenance in `DesignRecord`.
- Use `scripts/record_iteration.py` only for physical observations.

## Evidence and readiness

Use only `unverified`, `cad-checked`, `fdm-plausible`, `physically-tested`, and `function-confirmed` requirement statuses. Physical claims require a representative verification method and recorded evidence.

Claim **concept-ready** when architecture, known facts, assumptions, and unresolved risks are visible; **print-ready** only when applicable geometry, fit, assembly, motion, and print-plan blockers are resolved or isolated by a specific test; and **function-confirmed** only after representative physical testing. Block an unsupported readiness claim, not useful concept CAD.

Do not claim production readiness or function confirmation for pressure containment, mains electrical systems, vehicle-critical parts, lifting or overhead loads, medical use, restraints, or child-safety-critical mechanisms without qualified engineering review and representative testing.

## Commands

```bash
python scripts/run_model.py model.py --output-dir /chosen/output/design-name
python scripts/validate_portability.py .
```

When collaborative review is useful, read [observable-workbench.md](references/observable-workbench.md), then explicitly choose loopback or LAN serving. Do not expose a LAN review implicitly.

## Reference router

- Fits and small tests: [fits-calibration.md](references/fits-calibration.md)
- Fasteners and inserts: [fasteners-inserts-threads.md](references/fasteners-inserts-threads.md)
- Joints, magnets, hinges, and bayonets: [joints-mechanisms.md](references/joints-mechanisms.md)
- Snaps and flexures: [snaps-clips.md](references/snaps-clips.md)
- Material and strength: [materials-strength.md](references/materials-strength.md)
- Orientation and supports: [orientation-supports.md](references/orientation-supports.md)
- Clarification, stages, safety, and evidence: [design-process.md](references/design-process.md)
- Physical feedback: [iteration-loop.md](references/iteration-loop.md)
- Visual review: [visual-review.md](references/visual-review.md)
