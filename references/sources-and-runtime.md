# Sources, licenses, and CAD runtime

## Hardware source discovery

For a named board or component, search primary sources before asking the user to reproduce information that is already published. Prefer the exact manufacturer's CAD, mechanical drawing, product documentation, and source repository. Use authorized distributor documents only when they match the exact manufacturer part number. Treat community models as provisional unless primary dimensions independently verify the fit-controlling geometry.

Create one `SourceRecord` per drawing, model, or document with a stable `source_id`, absolute URL, product/revision, retrieval date, license or redistribution constraint, and the features actually checked. Link each sourced `ReferenceComponent` through `source_id`. Its `position_mm` and `rotation_deg` already own the scene transform; do not duplicate transforms in provenance.

Record each reference component's `geometry_basis` as `direct-source-cad`, `source-derived-envelope`, `measured-envelope`, or `nominal-envelope`. When exact manufacturer CAD is available, attempt to import and inspect it. Prefer using it directly as non-printable visual/reference geometry when licensing, geometry quality, and runtime performance permit, while retaining purpose-built simplified envelopes for connector, cable, tool, tolerance, or motion checks. Direct CAD and simplified envelopes may coexist. If direct CAD is not used, record why in a `DesignDecision`; it is not an unconditional blocker for concept work.

`ReferenceComponent` geometry is exported into the generated reference-model and portable-preview artifacts. Therefore use `direct-source-cad` there only when redistribution is permitted. When license terms are unclear, keep the imported CAD outside `DesignBundle` for local inspection/checks, link its `SourceRecord`, and put only a `source-derived-envelope` into the generated bundle. Never convert source CAD to STL merely to evade its redistribution terms.

Match user-facing claims to the recorded basis:

- `direct-source-cad`: “Used the manufacturer CAD directly as non-printable reference geometry.”
- `source-derived-envelope`: “Built a simplified reference envelope checked against the manufacturer CAD and drawing.”
- `measured-envelope`: “Built the reference geometry from physical measurements.”
- `nominal-envelope`: “Used provisional nominal reference geometry.”

Never say “built from the exact manufacturer CAD” unless the relevant reference is `direct-source-cad`. A detailed STEP file is not automatically correct—verify outline, mounting features, connectors, and maximum populated heights before using it for clearance.

## Runtime

Use Python 3.12 for the tested runtime. CadQuery 2.8.0 does not support the Python 3.13 host used during development.

Create an isolated environment. Do not modify the host project dependencies:

```bash
uv python install 3.12
uv venv --python 3.12 .venv-functional-cad
uv pip install --python .venv-functional-cad/bin/python \
  cadquery==2.8.0 \
  'cq_warehouse @ git+https://github.com/gumyr/cq_warehouse.git@daa46507ecc429c0e2dce11d9d5ffd09b12a42af'
```

`cq_warehouse` was not available under its project name in the tested package registry. The pinned Git dependency is deliberate.

## Reviewed implementations

- CadQuery: `https://github.com/CadQuery/cadquery`, parametric OCCT B-rep modeling, STEP/STL/3MF export, and assemblies.
- cq_warehouse: `https://github.com/gumyr/cq_warehouse`, revision `daa46507ecc429c0e2dce11d9d5ffd09b12a42af`, Apache-2.0. Use its APIs and installed standards data. Do not copy its tables.
- Flowful CAD skill: `https://github.com/flowful-ai/cad-skill`, revision `fe4215970d39f388ff1afc411fac49a9c5f79756`, PolyForm Noncommercial 1.0.0. Only workflow concepts were retained. No code was copied.
- FreeCAD-AI: `https://github.com/ghbalf/freecad-ai`, revision `2fc448f6bf991774125ff6b87361e605a7fb4cc9`, LGPL-2.1 code. Its focused skill organization was reviewed. No code or dimension tables were copied.
- three-cad-viewer: `https://github.com/bernhard-42/three-cad-viewer`, revision `86e08c70c0969fcef9d32d31ecf95df6406aa95c`, MIT. It validated the value of trees, measurements, exploded view, grids, axes, and camera controls.
- occt-import-js: `https://github.com/kovacsv/occt-import-js`, revision `41e470890ae0f9dc69ac50ffd5fc73e03576f4eb`. It remains a candidate for direct STEP viewing.
- Three.js: `0.185.1`, MIT, loaded by the bundled viewer from jsDelivr.

## Engineering references

- Plastic snap-fit design manual hosted by MIT Fab Central: `https://fab.cba.mit.edu/classes/S62.12/people/vernelle.noel/Plastic_Snap_fit_design.pdf`.
- Protolabs Network FDM snap-fit guide: `https://www.hubs.com/knowledge-base/how-design-snap-fit-joints-3d-printing/`.
- Prusa FDM modeling guidance: `https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135`.
- Prusa material guide: `https://help.prusa3d.com/filament-material-guide`.
- Prusa infill guide: `https://help.prusa3d.com/article/infill-patterns_177130`.

Published numbers vary by process and machine. Use these sources to define checks and conservative assumptions. Use calibration for final fit.
