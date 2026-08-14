# Joints and mechanisms

## Sliding rails and dovetails

Record travel, load, fit class, insertion direction, lead-in, end stops, retention, debris relief, and removal. Keep sliding faces away from support. Prepare a short section fit test when the fit is uncertain and the test will answer it.

Do not use a dovetail angle, clearance, or end stop only because it looks conventional. Check whether the part can enter the track after all surrounding geometry exists.

## Hinges

- Record axis, pin diameter, barrel wall, knuckle spacing, axial clearance, swing angle, assembly direction, and capture method.
- Keep the hinge axis unobstructed through full travel.
- Put barrel loads in favorable layers or split the hinge leaves.
- Use a metal pin for small repeated hinges when a printed pin is fragile.
- Treat living hinges as material-specific flexures. PLA is usually a poor repeated-use choice.

Use `pin_hinge_pair` for a pin-and-barrel skeleton. Use `living_hinge` only as a screened small-test geometry. The living-hinge helper blocks repeated PLA use and flex across layer adhesion.

## Detents and latches

Model spring deflection and release. Add a neutral state after engagement. Check accidental release direction, wear, creep, and the user force path.

Use `cantilever_snap`, `u_snap`, or `annular_snap_pair` as the mechanical base. Do not model an unscreened bump and call it a detent.

## Locating joints

Use `tongue_and_groove_pair` for alignment. Use a separate retention feature when pull-off force matters. Use `sliding_rail_pair` or `dovetail_pair` for constrained travel. Add lead-ins, elephant-foot relief, end stops, removal access, and debris clearance.

## Magnets

Measure the magnet batch. Record diameter, thickness, retention, insertion chamfer, bottom wall, extraction path, and polarity.

Retention choices:

- adhesive: add adhesive space and clean access;
- press fit: requires a small pocket fit test;
- snap lip: validate lip strain and insertion;
- captured: verify assembly order and prevent rattle.

For paired magnets, put polarity in the assembly graph and instructions. Check that magnetic pull cannot extract the magnet.

## Bayonet joints

Use a bayonet only after you validate lug-root strength, entry clearance, rotational clearance, track roof printability, hard stops, alignment, assembly force, and release direction. After the user approves the bayonet, propose a short collar-and-lug mechanism test before a full body.

A conventional J-slot or covered track often creates a horizontal roof when printed upright. The roof can be a two-ended bridge, a one-ended capture lip, or a curved unsupported strip. The retention surface is a precision and load-bearing interface. Do not describe that roof as trivial or support-free without a `BridgeSpec`, numeric span, two-ended anchors, exported-orientation review, and a small mechanism test.

Apply the capture identity check: a lug that resists axial pull must pass under a modeled retention surface. That surface is the track roof. Moving the track to an internal vertical wall does not remove the roof. If no roof exists, the joint relies on friction or a detent and is not an axially captured bayonet. Show the locked cross-section and force path before choosing the mechanism.

Prefer these forms in order:

1. an entry and track that remain open through a free edge;
2. a supported helical or diagonal ramp with layer overlap;
3. a separate track ring printed in a favorable orientation;
4. a split lid or collar with the track face on the build plate;
5. a short declared bridge only when the retention face does not depend on its underside quality.

If none of these preserve the required smooth exterior and internal envelope, propose another closure. A twist motion does not justify a support-sensitive lock.

A failed bayonet print is a candidate lesson, not proof that all bayonets are unsuitable. Do not reuse an unvalidated bayonet geometry only because it is CAD-valid.
