# Progressive functional design process

## Clarification policy

Start from information already available in the request, attachments, drawings, listings, and editable source. Extract useful dimensions before asking questions. Keep all supplied dimensions in one simple measurement map. Do not split them into nominal, measured, estimated, or provisional classes.

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
- proposed, user-approved, tested, and rejected decisions;
- material or hardware that the proposal requires;
- current prototype stage;
- smallest next test and its success criteria.
- physical observations and measurements from each completed test.

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

Add stable labels to features that the user can identify or move. Use the same label in the Python model, browser preview, static review image, design record, and conversation. Define the coordinate frame. For every position or size revision, show numeric before and after values, signed change, and direction. Get visual approval before recommending a physical test. See `visual-review.md`.

State the mechanism, required material and hardware, important assumptions, likely support requirement, and known risks. Ask focused design questions after the user can see the proposal.

Approval has narrow scope. Record only the choice that the user approved. Approval of an envelope does not approve a closure. Approval of a material does not approve glue. Approval of a shape does not approve magnets or screws. Keep all unmentioned choices `proposed`. For each `user-approved` decision, record a short quote or precise paraphrase as its approval basis.

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

Do not prepare a test for an interface that the user has not approved. First show the proposed interface and its operation. Then explain in plain language:

- what the small test prints;
- what question it answers;
- what it does not test;
- how much of the final geometry it preserves;
- how the result changes the final model.

Ask before preparing the test unless the user already requested it. Do not use “coupon” without immediately defining it as a small test print.

After a physical test, record the observation, measurement when available, likely cause, smallest change, and next stage. Give assembly instructions that match the printed geometry.
