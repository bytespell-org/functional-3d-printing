# Fasteners, bosses, inserts, and threads

## Standards rule

Use specified hardware and `cq_warehouse` objects. Do not type remembered screw-head or nut dimensions into a model when the library supports the fastener.

Use these library operations where applicable:

- `clearanceHole(..., fit="Close|Normal|Loose")`;
- `clearanceHole(..., captiveNut=True)`;
- `insertHole(HeatSetNut(...), manufacturingCompensation=...)`;
- `threadedHole(...)` or `IsoThread(...)` for modeled threads.

## Complete fastener path

Check screw head, washer, shaft, threaded engagement, tip, tool, and assembly direction. Check collision against boards, batteries, wires, connectors, moving parts, and the exterior.

Use `check_fastener_stack` for screw reach and breakthrough. Use `check_tool_access` for the driver or insert-tool approach. Put a measured hardware stack in the design manifest.

## Tiny screws

M1.6, M2, M2.5, and M3 features are sensitive to hole error and weak bosses. Use a small boss fit test when the hole is not a through-clearance hole. Keep the driver axis clear. Avoid a one-line boss wall. Add a root fillet and gusset where the boss joins a wall.

For direct plastic threads or self-tapping screws, use a pilot diameter from the screw manufacturer or a small physical fit test. Do not infer it only from nominal thread diameter. Control screw length and blind depth. Use torque-limited assembly tests.

## Heat-set inserts

- Specify the actual insert family and size.
- Use `cq_warehouse.fastener.HeatSetNut` when supported.
- Add radial plastic, tool access, insertion direction, bottom relief, and room for displaced plastic.
- Decide whether the insert is flush or recessed.
- Keep the heated tool away from thin walls and protected hardware.
- Print one small boss test with the real insert and tool when compensation is unknown.

Use inserts for repeated service, robust metal threads, or high clamp loads. A heat-set insert does not repair a thin or weakly attached boss.

Use `heat_set_insert_boss` when the boss is a separate functional feature. It uses the selected `HeatSetNut` geometry and checks radial wall thickness. Add a fillet or gusset when you join it to the parent part.

## Captive nuts

Provide an insertion path, rotation stop, axial stop, and removal plan. Account for corner radius and printer error. Do not trap the nut before another required component enters.

## Printed threads

Treat printed threads separately from machine-screw holes.

- Prefer coarse pitch and a generous lead-in.
- Keep support off thread flanks.
- Check pitch against layer height. The bundled check flags pitch below four layers.
- Apply explicit male/female radial clearance from the fit profile.
- Record thread length and expected cycles.
- Use a short thread-pair test.
- Prefer inserts or captured hardware for small, frequently serviced, or highly loaded threads.
