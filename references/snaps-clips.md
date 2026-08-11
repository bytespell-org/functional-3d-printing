# Snaps, clips, and cantilevers

## Required inputs

Record engagement deflection, beam length, root and tip thickness, width, root radius, material, print orientation, cycle count, entry angle, retention angle, and release method.

Do not select a snap only because it fits in the render.

## Conservative beam check

For an untapered rectangular cantilever under small deflection, the bundled check starts with:

`estimated surface strain = 1.5 * root thickness * required deflection / beam length²`

It then applies an orientation penalty when the beam flexes across layer adhesion. This is a screening model. It does not replace nonlinear analysis or physical cycling. Taper, hook load, root geometry, print defects, creep, and large deflection change the real result.

Treat the material limits in `materials.py` as conservative starting assumptions. Override them with qualified material and process data for safety-critical parts.

## Geometry rules

- Put a fillet at the root. Start near half the root thickness when space permits.
- Prefer a beam that tapers toward the tip. This reduces the root strain concentration.
- Use locating lugs to carry shear. Do not make the snap carry all side load.
- Make the entry face shallow enough for assembly.
- Set the retention face from the intended release method.
- Return the beam close to neutral after engagement. Permanent deflection causes creep.
- Add relief around the beam. Check that the mating part does not block deflection.
- Keep a tool path for serviceable snaps.

## FDM orientation

Prefer the beam length and bending strain in the build plane. A vertical beam that opens layer interfaces is a likely failure. If geometry forces weak orientation, split the part or use screws, inserts, magnets, or a separate compliant component.

## Required small mechanism test

After the user approves the snap interface, propose an isolated snap-and-latch test before a full enclosure when the snap is new, small, repeated-use, or uncertain. Test insertion, retention, removal, visible whitening, root cracks, and at least the expected cycle class.
