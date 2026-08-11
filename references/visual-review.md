# Annotated visual review

Use annotations to create shared vocabulary before the user identifies or moves a feature. Keep annotation identifiers stable across revisions.

## Coordinate frame

Define the frame in the model and review notes. For a typical electronics enclosure, prefer:

- `+Z`: toward the display or front face;
- `-Z`: toward the battery, base, or rear face;
- `0 degrees / +X`: the USB-C side;
- `+Y / 90 degrees`: counter-clockwise from the USB-C side when viewed from `+Z`;
- radial inward or outward: toward or away from the main axis.

Use functional directions when they are clearer, but include the axis. Example: `-1.0 mm in -Z, toward the base`.

Do not use isolated terms such as left, right, higher, lower, front, back, clockwise, or counter-clockwise. These terms depend on the camera or observer. State the view or axis.

## Stable feature names

Give each review feature a short stable identifier. Examples:

- `usb-c-opening`;
- `speaker-wire-slot`;
- `display-seat`;
- `lid-retention-tab-a`;
- `battery-end-stop`;
- `pcb-standoff-usbc-cw`.

Do not rename an identifier only because its position changed. If a feature is replaced by a different mechanism, retire the old identifier and create a new one.

Add a `ReviewAnnotation` for each feature that controls fit, access, movement, retention, assembly, or appearance. Put its point on the feature center, axis, or interface datum. Assign the owning part when applicable.

## Position and size changes

Represent each proposed revision with `DesignDelta`:

- annotation identifier;
- parameter name;
- numeric before value;
- numeric after value;
- signed delta;
- unit;
- direction in the defined frame;
- reason;
- review status.

Use `proposed`, `visually-approved`, or `rejected` as the review status. The preview computes and displays the signed delta.

For a changed shape that one scalar cannot explain, use several deltas. Example: opening center Z, opening width, and opening height. Do not hide a multi-axis change in one vague sentence.

## Review gate

For each revision:

1. Keep unchanged geometry visible for context.
2. Show labels in the interactive viewer.
3. Show the numeric before and after values in the proposed-change panel.
4. Provide a useful camera view and an annotated static image when the change is hard to see.
5. Ask the user to confirm the named feature and visible direction.
6. Record accepted changes as `visually-approved`.
7. Only then recommend a physical test for that revision.

Visual approval confirms design intent. It does not prove fit or physical function.
