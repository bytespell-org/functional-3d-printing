# Validation and delivery

## Geometry

- CadQuery shape is valid.
- Expected solid count matches.
- Bounding box and volume are plausible.
- STEP export succeeds.
- STL has no boundary or non-manifold edges.
- Mesh component count matches the intended part.
- No accidental tangent-only or zero-thickness connection exists.

## Assembly

- Every named part exists in the graph.
- Every multipart interface has a numeric final-state interference check and an insertion-path check using the actual assembled geometry.
- Every interface has an insertion direction.
- Mating axes and surfaces align.
- Clearance or interference matches the fit profile.
- Moving parts have full travel.
- Fasteners reach the intended thread and stop safely.
- Screw heads, drivers, insert tools, and nut insertion paths are clear.
- Magnet polarity and retention are explicit.
- The assembly sequence remains possible after wires and hardware are installed.

Use `functional_fdm.check_fastener_stack`, `check_tool_access`, and `check_linear_travel` for numeric checks. Put their findings in the `DesignBundle`. Use `DesignPart.expected_size_mm` and `expected_volume_range_mm3` to make execution fail when exported geometry leaves its intended envelope.

Read each `*.mesh-audit.json` after generation. The audit reports risky downward surfaces and near-horizontal candidate regions above the bed. A candidate is not automatically a valid bridge. Confirm two-ended anchoring in the geometry and record it in `PrintPlan`. Do not waive a candidate because a slicer produced no warning.

Use `check_assembly_interference` on every mating part pair in its final assembled coordinates. Use `check_assembly_insertion_path` from a clear approach position to the final state. Add both results to `DesignBundle.assembly_checks`. A valid B-rep and correct nominal diameters do not prove that two parts can occupy the intended assembled state.

## Manufacturability

- Walls and small features are plausible for the nozzle.
- Load direction and layers are compatible.
- Unsupported roofs and inaccessible support cavities are absent.
- Every part has a reviewed `PrintPlan` for its actual exported orientation.
- Every support-free part has no unresolved `unsupported_horizontal_candidates`.
- Every intentional bridge has supported anchors at both ends, a numeric span, and review evidence.
- Precision faces do not depend on rough support interfaces.
- Tall narrow features have ribs or a favorable orientation.
- Snap strain, boss wall, hole size, thread pitch, and insert support pass their feature checks.

## Visual inspection

Generate isometric, front, back, left, right, top, and bottom images. Generate assembled and exploded views for multipart work. Open the interactive viewer.

Inspect the result. Do not treat render generation as inspection. Check missing cutouts, disconnected bodies, reversed parts, wrong axes, inaccessible screws, blocked ports, impossible assembly, and poor proportions.

## Interactive preview handoff

Generate the complete `preview/` folder for every design review. Start the bundled static server and verify:

- `index.html` returns HTTP 200;
- `manifest.json` returns HTTP 200;
- every model URL in the manifest returns HTTP 200;
- all intended parts appear in the viewer.

Give the user a clickable URL that is reachable from the user's browser. Use the current environment's supported port-sharing or preview mechanism. Do not give a remote user a loopback URL. Do not assume that a local path is clickable or interactive.

When the environment cannot expose a server, preserve the complete preview folder as one artifact and say that interactive delivery is unavailable. Show static images as the fallback. Never omit the interactive viewer without explanation.

## Functional evidence

Map each intended behavior to a check or a planned physical test. Report its status as unverified, CAD-checked, FDM-plausible, physically tested, or function-confirmed. A valid solid, clean mesh, collision-free assembly, or attractive render does not confirm physical function.

Before a full-cost prototype, show the proposed geometry and isolate uncertain fits or mechanisms in a low-material test. Include measurable success criteria and assembly instructions.

## Deliverables

Keep editable source separate from generated output.

Track or preserve as source:

- editable parametric Python source;
- concise design inputs and measured constraints;
- authored design notes when the project requires them.

Generate into the selected output directory:

- per-part STEP and STL;
- assembly STEP;
- `design.json` with the design record, parts, interfaces, findings, assumptions, BOM, and output policy;
- generated `DESIGN.md` with material, nozzle, orientation, tolerances, hardware, process recommendations, support expectation, assembly, and calibration;
- static renders;
- interactive Three.js preview;
- small fit or mechanism tests when risk requires them.

Use this output order:

1. Use an explicit `--output-dir` supplied by the caller.
2. Otherwise, use `build/functional-fdm/<design-name>/` under a detected Git project root.
3. When no project root exists, use a temporary directory and report that it is temporary.
4. Use `--in-place` only for deliberate generation beside source.

Before generation, report whether the output contains tracked files or is inside a Git worktree without an ignore rule. Do not create or modify `.gitignore`, `.git/info/exclude`, global ignore files, or repository policy. A project can choose a rule such as `/build/functional-fdm/`, but the skill must only recommend it.

Do not include sliced files, printer jobs, upload controls, or queue data.

## Portable package check

Before distribution, run:

```bash
python scripts/validate_portability.py .
```

After archive creation, run the check again with `--archive`. Reject local paths, private network addresses, managed-session identifiers, generated caches, symlinks, credentials, and repository-specific control endpoints.
