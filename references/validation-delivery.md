# Validation and delivery

Validate the risks present, then bound the claim to what was checked.

## Geometry and print plan

- Confirm valid CadQuery shapes, expected solids, plausible bounds and volume, STEP export, and watertight single-part meshes.
- Inspect each `*.mesh-audit.json`; a downward horizontal candidate is not automatically a valid bridge.
- Give every printable part a reviewed `PrintPlan` in its exported orientation.
- Check nozzle-scale walls, layer direction, unsupported roofs, support removal, critical faces, and tall narrow features.

## Assembly, access, and motion

Use numeric checks for applicable final-state fit, assembly, travel, fastener reach, driver access, cable routes, and service removal. `check_assembly_insertion_path` samples straight translation only. Use `check_rotational_motion_path` for fixed-axis rotation or `check_sampled_motion_path` for caller-supplied poses; these are sampled collision checks, not motion planning.

For a plug, cable, driver, or service keep-out, call `check_access_envelope` with every printed part present in that service state. If the envelope is also review geometry, its name must match `ReferenceComponent.name`.

Inspect useful static views. Use the interactive workbench only when collaboration helps; see `observable-workbench.md`. A generated render is not proof that it was inspected.

## Readiness and reporting

- `concept-ready`: architecture and evidence boundaries are visible.
- `print-ready`: no applicable `BLOCKING` or `LIKELY_FAILURE` finding remains, and critical unknown fits are characterized or isolated in a specific test.
- `function-confirmed`: representative physical testing demonstrates the intended use.

`CAUTION` findings remain visible but do not automatically prevent print readiness. In the final report, distinguish execution failures, blockers, likely failures, important cautions, outstanding physical tests, and the readiness claim. Surface unresolved cautions that materially affect load paths, retained hardware, fasteners, fit, service, critical surfaces, or electronics. Match source wording to each reference component's `geometry_basis`.

## Output

Keep editable source separate from generated output. A normal bundle contains per-part STEP/STL, assembly STEP, `design.json`, generated `DESIGN.md`, static renders, and the portable preview. Keep slicing, printer jobs, uploads, and queues out of scope.

Regenerate ordinary revisions into one stable output directory. Use scratch space for disposable experiments. Preserve one final bundle and concise revision notes; keep superseded bundles only for evaluation, debugging, reproducibility, or explicit user request. Use `record_iteration.py` only for physical observations.

Output selection order is explicit `--output-dir`, project `build/functional-fdm/<design-name>/`, temporary storage when no project exists, then deliberate `--in-place`. Report tracked or unignored output paths; do not edit ignore files.

Before distribution, run:

```bash
python scripts/validate_portability.py .
```

Run it again with `--archive` after packaging. Reject local paths, private addresses, session identifiers, caches, symlinks, credentials, and repository-specific control endpoints.
