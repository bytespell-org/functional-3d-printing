# Progressive functional design process

## Proportional workflow

Use the smallest workflow that matches the risk. A simple one-piece part needs the bundle, named part, design record, reviewed print plan, valid geometry, mesh inspection, and a one-part assembly graph; it does not automatically need references, assembly checks, a progress sidecar, comments, or a server. Escalate to fit/assembly records and checks only for mating parts, exact hardware, access paths, or mechanisms. Escalate again to the collaborative workbench only when visual iteration materially helps.

## Clarification policy

Start from information already available in the request, attachments, drawings, listings, and editable source. Extract useful dimensions before asking questions. Keep all supplied dimensions in one simple measurement map. Do not split them into nominal, measured, estimated, or provisional classes.

Resolve the exact product, variant, and hardware revision before treating a family name such as “ESP32” as fit-controlling truth. If the identity is not recoverable from an attached link, photo, handoff, or source tree, ask for that identity first. Once identified, research it for the user before asking them to measure it. Use this order:

1. manufacturer product page, documentation, repository, mechanical drawing, or CAD download;
2. authorized distributor documentation tied to the exact manufacturer part number;
3. clearly identified community CAD only as a provisional visual reference that must be checked against primary dimensions.

Record sources with `SourceRecord` and link sourced hardware through `ReferenceComponent.source_id`; see `sources-and-runtime.md`. Check at least the outer profile, mounting features, connector positions, and populated heights against published dimensions before trusting downloaded CAD. Do not silently substitute a nearby development-board variant. If no adequate source exists, make a conservative reference envelope and ask only for the physical measurements that control the chosen architecture.

Treat every supplied dimension as known. Use it until the user changes it. Before asking for any dimension, inspect the measurement map. If final fit needs a second measurement, cite the value already recorded and explain why confirmation matters. Never ask for the same value as if the user did not supply it.

Ask only when an answer can materially change:

- mating geometry or required clearance;
- architecture or part count;
- normal use or required access;
- retention, loading, heat, or safety;
- assembly order or serviceability.

Group related blocking questions into one short request. Do not ask for a complete printer profile, all available hardware, or every minor dimension. Record a conservative assumption when work can continue safely.

## Functional record

Keep the design history in the editable Python model. Use the module docstring for a concise human summary. Use `DesignRecord` for machine-readable data that can flow into `design.json` and `DESIGN.md`.

Record:

- intended function;
- known dimensions;
- requirements and their evidence status;
- assumptions and open questions;
- decisions and their reasons;
- material or hardware that the proposal requires;
- current prototype stage;
- smallest next test and its success criteria.

Record physical observations and measurements with `scripts/record_iteration.py`, not in `DesignRecord`.

Use these requirement evidence levels:

- `unverified`: stated or assumed, with no check;
- `cad-checked`: checked by dimensions, envelopes, or assembly geometry;
- `fdm-plausible`: print orientation and manufacturability checks pass;
- `physically-tested`: a printed sample demonstrates the specified behavior;
- `function-confirmed`: the assembled object performs the intended use.

Do not convert a CAD pass into a physical or functional claim.

## Proposal and review

Create enough CAD to make the proposal concrete. Do not delay all modeling until every detail is known.

Show views that answer practical questions:

- assembled shape;
- exploded relationship;
- internal clearances;
- installation or removal movement;
- intended print orientation;
- uncertain fits and unsupported regions.

Add stable labels to features that the user can identify or move. Use the same label in the Python model, browser preview, static review image, design record, and conversation. Define the coordinate frame. For a position or size revision, describe the changed dimensions and direction clearly when that helps review. See `visual-review.md`.

State the mechanism, required material and hardware, important assumptions, likely support requirement, and known risks. Ask focused design questions after the user can see the proposal.

Record each design decision and its reason plainly. Do not infer that a request for one feature authorizes unrelated hardware, permanent assembly, or material dependencies; ask only when the missing choice materially changes scope, cost, safety, or normal use.

## Material and hardware policy

Do not ask for a complete inventory first. Ordinary PLA and a 0.4 mm nozzle are the neutral starting assumption when the request gives no process information.

When a proposal depends on something else, identify the exact item and ask whether it is available before finalizing the dependency. This applies to PETG, ASA, TPU, magnets, machine screws, inserts, nuts, springs, pins, bearings, adhesives, and special tools. Do not ask again for an item that the user already supplied or confirmed.

When the best mechanism needs unavailable hardware, offer a no-hardware alternative and explain the tradeoff.

## Prototype gates

Use these stages:

1. `concept`: enough geometry and images to review architecture and operation;
2. `small-fit-test`: the smallest geometry that preserves the real fit, print orientation, load path, and assembly movement;
3. `integrated-prototype`: all important interfaces in one assembly, without unnecessary cosmetic or bulk material;
4. `final`: complete geometry after critical tests pass or the user accepts the remaining risk.

A small fit or mechanism test must have explicit success criteria. Examples include insertion force, retained load, free travel, cycle count, measured play, release method, glass clearance, screw seating, or wire passage.

When a fit or mechanism has real uncertainty, prepare the smallest useful test. Show the interface and its operation, then explain in plain language:

- what the small test prints;
- what question it answers;
- what it does not test;
- how much of the final geometry it preserves;
- how the result changes the final model.

Ask before preparing the test only when it would exceed the user's scope or require new material, hardware, cost, or authority. Do not use “coupon” without immediately defining it as a small test print.

After a physical test, record the observation, measurement when available, likely cause, smallest change, and next stage. Give assembly instructions that match the printed geometry.

## Readiness and safety

Use `concept-ready` when the architecture is visible and known facts, assumptions, questions, and risks are explicit. Use `print-ready` only when applicable geometry, assembly, fit, motion, and print-plan blockers are resolved or isolated in a specific test. Use `function-confirmed` only after representative physical testing. Block an unsupported readiness claim, not useful concept work.

Pressure containment, mains electrical systems, vehicle-critical parts, lifting or overhead loads, medical use, restraints, and child-safety-critical mechanisms may receive concept CAD, but must not be called production-ready or function-confirmed without qualified engineering review and representative testing.
