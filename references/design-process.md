# Progressive functional design process

## Choose the smallest useful workflow

Use the lightweight path for a simple one-piece part. Add hardware references, interface records, assembly checks, or mechanism tests only when the design contains those risks. Start the collaborative workbench only when visual iteration materially helps.

For a simple part, do not create provenance merely to cite an installed library or standards lookup, and do not use `interface_dispositions` for an obvious hole or opening; keep those facts in dimensions or decisions. Do not hand-author evidence strings that merely restate generated CAD or mesh checks.

Ask users questions directly. Ask only when the answer can change architecture, fit, safety, service, or normal use. First inspect the request, attachments, source tree, and published information; research exact hardware before asking the user to reproduce dimensions that are already available. If a detail is still unknown but work can continue safely, record a conservative assumption and proceed with the smallest testable architecture.

## Record decisions and evidence

Keep the editable Python model as the source of truth. Use `DesignRecord` for intent, known dimensions, requirements, assumptions, open questions, decisions, required material or hardware, prototype stage, and the smallest useful physical test. Use `scripts/record_iteration.py` only for observations from a physical print.

Use only these requirement evidence levels:

- `unverified`: stated or assumed;
- `cad-checked`: supported by dimensions, envelopes, or assembly checks;
- `fdm-plausible`: geometry and print-plan checks support manufacture;
- `physically-tested`: a representative print demonstrates the stated behavior;
- `function-confirmed`: the assembled object performs its intended use.

Do not turn a CAD pass into a physical claim. Show enough geometry to review the proposal, label uncertain features consistently, and state the mechanism, material, hardware, assumptions, support expectations, and known risks.

## Hardware and prototypes

Ask once when unknown hardware materially changes geometry. If the user delegates the choice, use a conventional parameterized option, label it provisional wherever it appears in the model, BOM, or final report, and do not claim print readiness until its critical dimensions are confirmed or physically tested. Offer a no-special-hardware alternative when practical.

Use `concept`, `small-fit-test`, `integrated-prototype`, and `final` as prototype stages. A small test should preserve the real fit, material, orientation, load path, and movement needed to answer one uncertainty, with measurable success criteria.

## Readiness and safety

Use `concept-ready` when architecture, facts, assumptions, and unresolved risks are visible. Use `print-ready` only when applicable geometry, fit, assembly, motion, and print-plan failures are resolved or isolated in a specific test. Use `function-confirmed` only after representative physical testing. Block an unsupported claim, not useful concept work.

Pressure containment, mains electrical systems, vehicle-critical parts, lifting or overhead loads, medical use, restraints, and child-safety-critical mechanisms may receive concept CAD, but must not be called production-ready or function-confirmed without qualified engineering review and representative testing.
