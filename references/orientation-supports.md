# Orientation, overhangs, bridges, and support avoidance

## Orientation first

For each part, record the service load and flex direction. FDM parts are anisotropic. Prefer tensile and bending loads in the build plane. Avoid opening layer interfaces in snaps, hooks, hinge barrels, and screw bosses.

Change the part architecture when one orientation cannot provide both strength and manufacturability. Split and join parts when the added interface is less risky than weak layers or trapped support.

## Risk classes

Use the semantic classes from `classify_overhang`:

- `SAFE`
- `LIKELY_SELF_SUPPORTING`
- `MARGINAL`
- `SUPPORT_LIKELY`
- `IMPOSSIBLE_IN_CURRENT_ORIENTATION`

Angle alone is not enough. Consider span, bridge direction, nozzle, material, cooling assumption, surface precision, and load.

Prefer geometry where each new layer has a reliable supported path. Treat steep unsupported surfaces as design risks, not routine slicer cleanup. Increase severity when an unsupported region is long, follows a curved perimeter, cannot use a true bridge path, traps support, or controls fit, locking, motion, sealing, optical quality, or safety.

The bundled heuristic treats up to 45 degrees from vertical as a conservative safe region, then increases risk. This is not an absolute printer limit. Calibrated printers and cooling can do more. Geometry near a precision fit requires more caution than a hidden cosmetic surface.

## Supported-layer rule

Assume that each new layer needs material below it. Treat printing above empty space as an exception that needs evidence.

Distinguish these cases:

- A self-supporting overhang has enough overlap with the preceding layer.
- A bridge spans between supported anchors at both ends.
- A cantilever or capture lip has support at only one end. It is not a bridge.
- A floating island begins without any material below it.

Do not infer that a horizontal region is printable because it is connected to the rest of the solid. Connectivity is not layer support. Do not use a support-free note, a clean static render, a valid B-rep, or the absence of a slicer warning as proof.

For every exported print orientation:

1. Run the STL audit.
2. Inspect `unsupported_horizontal_candidates` and the risky-overhang regions.
3. Inspect the bottom, side, and section views.
4. Record a `PrintPlan` with support mode and review evidence.
5. Declare each intentional bridge with numeric span, width, two-ended anchoring, and evidence.
6. Redesign unresolved candidates before physical manufacture.

The mesh audit is conservative. It identifies candidate regions; it does not prove that a span has two anchors. The geometry review must confirm that distinction. A later optional slicer check can add evidence but cannot replace this check.

## Redesign order

1. Change orientation.
2. Open a hidden roof through a free edge.
3. Use a chamfer, arch, teardrop, or bridge with supported endpoints.
4. Use a sacrificial membrane that is accessible and intentional.
5. Split the part and add a controlled joint.
6. Use small local support only when earlier options are worse.

Use large or trapped support only when function requires it and the removal path is complete. Keep bridges short and noncritical. If bridge behavior controls function or appearance, use a small physical test before the full part.

Keep precision mating faces, threads, sealing faces, rails, and snap engagement faces off support interfaces.

## Small features

Check thin pins, tabs, towers, holes, bosses, embossed text, thread crests, magnet lips, and bridges against nozzle width and layer height. Recommend slower small-feature and bridge printing when appropriate, but do not operate a slicer.
