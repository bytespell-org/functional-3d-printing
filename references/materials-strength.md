# Materials and structural design

## Material roles

- PLA: rigid, easy, and dimensionally useful for prototypes. Avoid repeated flex and warm service.
- PETG: useful default for tough hobby parts. Check stringing, creep, and rough support faces.
- ABS/ASA: useful for heat and environment. Account for shrinkage and warping. ASA adds UV resistance.
- PA/nylon: tough and fatigue resistant. Moisture control and process stability matter.
- PC: strong and heat resistant, but difficult to print.
- TPU: useful for compliant parts, seals, and soft retention.
- Fiber-filled materials: often stiffer and more dimensionally stable, but can reduce impact resistance and layer adhesion. Do not assume they improve snaps.

Select material from load, temperature, UV, chemical exposure, impact, fatigue, creep, and print capability. Do not select only from tensile strength.

## Structural rules

- Put material on load paths.
- Use fillets and gussets at load transfers.
- Prefer shell and rib stiffness over broad solid fill.
- Increase walls/perimeters before using very high infill for many small functional parts.
- A thin snap beam gets strength from solid geometry and orientation, not infill.
- Keep loaded holes and bosses away from free edges.
- Avoid sharp internal corners at flexure roots.

## Process recommendations

Give recommendations, not slicer commands. Include nozzle, layer-height range, wall range, infill intent, areas to slow, cooling-sensitive bridges, and support expectation.

Examples:

- enclosure shell: 3–4 walls and modest infill;
- small loaded bracket: 4–6 walls, load-aware orientation, and useful multidirectional infill;
- snap arm: solid wall geometry, small layers, and in-plane flex;
- large cosmetic volume: low/adaptive infill is acceptable.

Do not equate 100% infill with a well-designed strong part.
