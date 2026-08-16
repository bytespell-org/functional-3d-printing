# Enclosures and assembly architecture

## Design backward from assembly

Write the reversible assembly sequence before shaping the shell. Model component envelopes, keep-outs, connectors, plugs, cable bends, fasteners, tools, controls, vents, and service space that can affect it. Use an `AssemblyGraph` for printed-part interfaces and motion.

For every retained component:

1. Assign a deliberate printed owner.
2. Provide opposing constraints in every direction required by normal use.
3. Carry loads to the body through intentional bearing surfaces.
4. Keep installation, connection, service, and removal possible.
5. Prevent closures from accidentally clamping glass, populated PCB regions, batteries, connectors, or solder joints.
6. Make relevant ports and controls deliberately accessible or deliberately enclosed.

Treat all cover glass as fragile unless the manufacturer identifies an approved structural bearing surface. Prefer documented mounting points, safe PCB regions, broad ledges, shoulders, trays, ribs, or short supported posts over tiny contacts and tall towers. A nearby lid or nominal solid contact is not a load path.

For complex electronics, a `+X/-X/+Y/-Y/+Z/-Z` review is useful when named bearing faces and checks do not already make retention obvious. It is a review technique, not a mandatory artifact. `DesignRecord.interface_dispositions` is likewise optional; use it when an electronics enclosure has several documented ports or controls whose accessibility should remain explicit.

Represent supplied hardware as non-printable `ReferenceComponent` geometry in the assembled frame. Use the simplest geometry that preserves fit-controlling dimensions, exits, and keep-outs; direct CAD and purpose-built clearance envelopes may coexist. Keep references out of printable exports and printability audits.

Build datums, supports, passages, bosses, trays, and tool paths before the ergonomic exterior. Check that the hand sequence remains realistic as well as collision-free.

## Closures and access

Choose screws, snaps, slides, magnets, press fits, or threads from service needs and the real assembly path. Read the matching mechanism reference before relying on it.

Continue connector and wire openings through every crossing wall, rim, retainer, and lid. Check the mating plug, cable approach, and tool envelope against every printed part in the route. Check removal after wires and neighboring hardware are installed.
