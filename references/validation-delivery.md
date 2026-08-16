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
- Every retained component has one owner and a closed load path to the body in each constrained direction.
- Every retained hardware reference has applicable numeric final-state clearance plus installation and removal checks against its owner and any closure; a render or nominal contact alone does not support `cad-checked` retention.
- Every multipart interface has a numeric final-state interference check and a motion check appropriate to how it actually assembles.
- Straight interfaces record an insertion direction; rotary or compound interfaces record their sampled poses and axes.
- Mating axes and surfaces align.
- Clearance or interference matches the fit profile.
- Moving parts have full travel.
- Fasteners reach the intended thread and stop safely.
- Screw heads, drivers, insert tools, and nut insertion paths are clear.
- Magnet polarity and retention are explicit.
- The assembly sequence remains possible after wires and hardware are installed.
- Removal is checked independently; do not assume insertion is reversible after connectors, adhesive, or neighboring parts are present.

Use `functional_fdm.check_fastener_stack`, `check_tool_access`, and `check_linear_travel` for numeric checks. Put their findings in the `DesignBundle`. Use `DesignPart.expected_size_mm` and `expected_volume_range_mm3` to make execution fail when exported geometry leaves its intended envelope.

Read each `*.mesh-audit.json` after generation. The audit reports risky downward surfaces and near-horizontal candidate regions above the bed. A candidate is not automatically a valid bridge. Confirm two-ended anchoring in the geometry and record it in `PrintPlan`. Do not waive a candidate because a slicer produced no warning.

Use `check_assembly_interference` on every mating part pair in its final assembled coordinates. `check_assembly_insertion_path` samples only straight translation from a clear approach to the modeled final state; it does not prove hinge rotation, bayonet movement, curved insertion, or compound motion. Use `check_rotational_motion_path` for a simple fixed-axis rotation and `check_sampled_motion_path` for explicit caller-supplied poses. These are deterministic collision samples, not motion planning; add samples where clearance changes rapidly and report sample count, step size when known, maximum overlap, and its pose. Add the applicable results to `DesignBundle.assembly_checks`.

For every plug, cable, driver, fastener, or service keep-out, call `check_access_envelope` with the full set of printed parts that the path could cross. When the envelope is a scene object, make `envelope_name` exactly match its `ReferenceComponent.name` so metadata validation can resolve it. Pass the required part names separately so a missing geometry entry becomes a blocking finding. Do not replace this matrix with a few manually selected pair checks: clearing a USB envelope against the body and carrier says nothing about an omitted retainer.

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

Generate only the views needed to inspect the risks present; include assembled and exploded views for multipart work. Inspect static images or the interactive viewer when collaboration benefits from it.

Inspect the result. Do not treat render generation as inspection. Check missing cutouts, disconnected bodies, reversed parts, wrong axes, inaccessible screws, blocked ports, impossible assembly, and poor proportions.

## Interactive preview handoff

Generate the complete `preview/` folder as a portable artifact. Start the bundled server only when interactive review materially helps and the environment can expose a reachable URL safely. When serving, verify:

- `index.html` returns HTTP 200;
- `manifest.json` returns HTTP 200;
- every model URL in the manifest returns HTTP 200 and matches the generated digest;
- all intended parts appear in the viewer.

The server defaults to loopback. Use explicit `--lan` or an explicit non-loopback `--host` only on a trusted network, and share the tokenized URL it prints. Do not expose the review merely to satisfy a ritual. Static model access remains read-only; comment creation and deletion require the session token.

When a server is unnecessary or unsafe, preserve the preview folder and show static images. State that interactive review was not started only when that distinction matters to the handoff.

## Readiness claims

- `concept-ready`: architecture and evidence boundaries are visible; open risks may remain explicit.
- `print-ready`: no applicable `BLOCKING` or `LIKELY_FAILURE` geometry, assembly, fit, motion, or print-plan findings remain, and critical unknown fits are characterized or isolated in a specific test. A disclosed `CAUTION` may remain when it does not contradict the claim.
- `function-confirmed`: representative physical testing demonstrates the intended use.

An unsupported readiness claim is blocking. Unresolved physical uncertainty does not prevent generating and reviewing concept CAD.

In the final user-facing report, distinguish execution failures, blocking findings, likely failures, cautions, outstanding physical tests, and claimed readiness. Summarize every unresolved `CAUTION` or `LIKELY_FAILURE` affecting load paths, enclosure floors or primary walls, retained hardware, fasteners, fit-controlling interfaces, service cycles, critical visible surfaces, or electronics retention. “No blocking findings remain” is not a substitute for disclosing a two-nozzle-width floor or provisional insert fit.

Match source-fidelity prose to each `ReferenceComponent.geometry_basis`; use the factual wording generated in `DESIGN.md` rather than upgrading a derived envelope into an “exact CAD” claim.

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

Regenerate ordinary CAD revisions into one stable output directory. Use scratch directories for transient failed experiments, and preserve editable source, one final generated bundle, and a concise description of important revisions. Keep superseded complete bundles only for evaluation, validator debugging, reproducibility, or explicit user request. Do not create `output-v2`, `output-v3`, and similar folders by default. Reuse `python scripts/run_model.py source/model.py --output-dir output`; `record_iteration.py` remains reserved for physical observations, not unprinted CAD revisions.

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
