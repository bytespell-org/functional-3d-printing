# Annotated visual review

Use annotations to create shared vocabulary before a person identifies or moves a feature. Keep annotation identifiers stable across revisions.

## Coordinate frame

Define the frame in the model and review notes. For a typical electronics enclosure, prefer:

- `+Z`: toward the display or front face;
- `-Z`: toward the battery, base, or rear face;
- `0 degrees / +X`: the USB-C side;
- `+Y / 90 degrees`: counter-clockwise from the USB-C side when viewed from `+Z`;
- radial inward or outward: toward or away from the main axis.

Use functional directions when they are clearer, but include the axis. Example: `-1.0 mm in -Z, toward the base`.

Do not use isolated terms such as left, right, higher, lower, front, back, clockwise, or counter-clockwise. These depend on the camera or observer. State the view or axis.

## Stable feature names

Give each review feature a short stable identifier, such as `usb-c-opening`, `speaker-wire-slot`, `display-seat`, `lid-retention-tab-a`, `battery-end-stop`, or `pcb-standoff-usbc-cw`.

Do not rename an identifier only because its position changed. If a feature is replaced by a different mechanism, retire the old identifier and create a new one.

Add a `ReviewAnnotation` for each feature that controls fit, access, movement, retention, assembly, or appearance. Put its point on the feature center, axis, or interface datum. Assign the owning part when applicable.

## Review practice

Keep unchanged geometry visible for context, show labels in the interactive viewer, and provide a useful camera view or annotated static image for anything difficult to see. Record dimensions, assumptions, and decisions in `DesignRecord`. A user comment is an instruction to work; once the model and its evidence address it, remove the comment. Visual review guides intent but does not prove fit or physical function.
