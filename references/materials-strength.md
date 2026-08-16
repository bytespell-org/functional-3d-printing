# Materials and structural design

Choose material from load, temperature, UV, chemicals, impact, fatigue, creep, and printer capability—not tensile strength alone.

- PLA is rigid and dimensionally useful; avoid warm service and repeated flex.
- PETG is tougher but can creep and leave rough support faces.
- ABS/ASA improve heat resistance; account for shrinkage and warping.
- PA and PC suit demanding loads when the printer and drying process support them.
- TPU suits compliant parts and soft retention.
- Fiber-filled materials may improve stiffness while reducing impact resistance or layer adhesion.

## Structural judgment

- Put material on load paths and use fillets or gussets at transfers.
- Prefer shell and rib stiffness to broad solid fill; increase walls before excessive infill.
- Orient layers for the actual load, especially flexures and loaded holes.
- Keep bosses tied into walls, ribs, or a supported floor.
- Use broad known-safe bearing regions around fragile hardware.
- Express floors and primary walls in nozzle widths. A reusable floor or primary wall below roughly three nozzle widths needs an explicit reason; geometry below the existing likely-failure threshold remains a likely failure.

Give process recommendations rather than slicer commands: nozzle, layer-height range, wall intent, infill intent, sensitive bridges, slow regions, and support expectation. Do not equate 100% infill with a well-designed strong part.
