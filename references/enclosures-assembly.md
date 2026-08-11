# Enclosures and assembly architecture

## Start with the assembly

Before surface detail, define:

- component envelopes and keep-outs;
- board support and fasteners;
- battery swelling and wire exits;
- plugs and cable bend radius;
- speaker diaphragm, acoustic opening, and wire path;
- display or glass protrusion;
- controls and human access;
- lid architecture and service cycle;
- tool access and assembly order.

Use an `AssemblyGraph`. Each interface records two parts, joint type, nominal geometry, fit, insertion direction, removability, cycles, and hardware.

## Lid selection

- Screw lid: best for service, clamp control, and predictable retention. Check bosses, inserts, screw length, and driver access.
- Snap lid: useful for tool-free access. Requires strain, orientation, clearance, and cycle validation.
- Sliding lid: useful when there is a clear insertion path and end stop.
- Magnet lid: easy service but requires retained magnets and polarity control.
- Press lid: simple but sensitive to calibration, creep, and wear.
- Threaded lid: good for round forms when size and pitch are printable.

Do not choose a joint before you know how the internal hardware enters.

## Cutouts

Continue each connector or wire opening through every wall, rim, lip, and lid that crosses its path. Include the mating plug, not only the receptacle. Open the cutout through a free edge when this removes an unsupported closing roof and does not weaken retention.

## Serviceability

Check removal after wires and plugs are connected. Keep batteries away from screw tips, hot inserts, and sharp ribs. Never make the lid clamp a display, battery pouch, or populated board unless the hardware permits that load.
