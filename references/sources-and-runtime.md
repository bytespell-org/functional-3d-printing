# Sources, licenses, and CAD runtime

## Hardware sources

For fit-controlling hardware, prefer the exact manufacturer's CAD, mechanical drawing, documentation, or source repository. Use an authorized distributor only when it matches the exact part number, and treat community CAD as provisional until primary dimensions verify it.

Create a `SourceRecord` for each used source and link sourced `ReferenceComponent` objects through `source_id`. Record the component's `geometry_basis`:

- `direct-source-cad`: linked source CAD is used directly as non-printable reference geometry;
- `source-derived-envelope`: a simplified envelope is built from or checked against linked source material;
- `measured-envelope`: geometry comes from physical measurements;
- `nominal-envelope`: provisional nominal or assumed geometry.

Attempt exact CAD import when it improves the work. Use it directly when geometry quality, performance, and licensing permit; use simplified envelopes for tolerance, connector, cable, tool, or motion checks. Both may coexist. If exact CAD is available but not used, record why in a `DesignDecision`; this does not block concept work.

Generated reference models are portable artifacts. Do not export third-party CAD when redistribution is unclear. Keep it local for inspection and export only derived geometry when appropriate. Verify outline, mounting features, connector positions, and populated heights before relying on any source model.

Match user-facing claims to `geometry_basis`. Say “Used the linked source CAD directly as non-printable reference geometry” only for `direct-source-cad`; say “Built a simplified reference envelope from or checked against the linked source material” for `source-derived-envelope`.

## Runtime

Use an isolated Python 3.12 environment; CadQuery 2.8.0 does not support the Python 3.13 host used during development.

```bash
uv python install 3.12
uv venv --python 3.12 .venv-functional-cad
uv pip install --python .venv-functional-cad/bin/python \
  cadquery==2.8.0 \
  'cq_warehouse @ git+https://github.com/gumyr/cq_warehouse.git@daa46507ecc429c0e2dce11d9d5ffd09b12a42af'
```

The pinned `cq_warehouse` Git dependency is deliberate. Keep project dependencies unchanged. Published design numbers vary by process and machine; use calibration for final fit.
