# Fits and calibration

## Terms

- Clearance fit: guaranteed free space.
- Loose sliding fit: easy movement with visible play.
- Close sliding fit: controlled movement with little play.
- Locating fit: repeatable alignment with limited movement.
- Friction fit: removable retention from surface contact.
- Press or interference fit: assembly requires elastic deformation.
- Snap fit: temporary deformation followed by geometric engagement.

Do not use these terms as synonyms.

## Profile rules

Use `FitProfile`. Each clearance field is per mating side. `hole_diameter_compensation_mm` is added to the modeled hole diameter. A positive press-interference field produces a negative mating gap.

The bundled profile defaults are conservative heuristics. They are not claims about a printer. Keep `characterized=False` until a small physical fit test supports the values.

Record:

- printer and nozzle;
- material and batch when relevant;
- XY and Z orientation;
- hole diameter compensation;
- external dimension compensation;
- elephant-foot allowance;
- close/loose sliding gaps;
- friction and press behavior;
- snap clearance.

## Coupon selection

Prepare a small fit test when any condition applies and it will answer a real uncertainty:

- press, friction, locating, or close sliding fit is function-critical;
- nominal size is below 10 mm;
- the profile is uncharacterized;
- the feature changes orientation;
- repeated movement or sealing matters;
- actual material or printer changed.

Keep the test orientation, wall direction, layer height assumption, and mating geometry equivalent to the final feature. A round-hole test does not fully characterize a long rectangular rail.

Use at least five variants around the current estimate. Mark each variant. Record insertion force, play, retention, removal, and damage. Update the profile only from measured results.

## First-layer effects

Keep critical mating edges away from the first-layer flare or add a small elephant-foot chamfer. Do not compensate the entire part when only the first layer is affected.
