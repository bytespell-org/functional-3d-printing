# Functional FDM Mechanical CAD

An agent skill for designing small mechanical parts that can survive contact with a real FDM printer.

The skill uses CadQuery to build editable solid models. It checks fits, assembly paths, fasteners, print orientation, unsupported geometry, and the difference between a CAD claim and a tested physical result. It produces STEP and STL files, static diagnostic renders, an annotated Three.js review page, and concise build notes.

It is meant for parts such as:

- electronics enclosures and removable covers;
- brackets, mounts, spacers, knobs, and adapters;
- press fits, sliding fits, rails, dovetails, and hinges;
- clips, detents, cantilever snaps, and latches;
- M2 through M4 fasteners, captive nuts, and heat-set inserts;
- magnet pockets and simple multipart assemblies.

Decorative mesh generation is outside its scope. Slicing, printer queues, uploads, and printer control are also outside its scope.

## What the skill changes

Most generated CAD workflows stop when a solid is valid. This skill keeps checking:

- Does the part fit the supplied dimensions?
- Can each component enter and leave along a real assembly path?
- Can a screwdriver, wire, connector, or insert tool reach its target?
- Does a bridge have support at both ends?
- Is a capture lip a hidden one-ended cantilever?
- Does the proposed print orientation put the load across weak layer interfaces?
- Does a small test preserve the fit or mechanism that it claims to test?
- Did a physical test confirm the function, or did the CAD only make it plausible?

The skill blocks a design when required evidence is missing. It records assumptions instead of presenting them as measurements.

## Workflow

1. Record the intended function and all supplied dimensions in the editable model.
2. Propose an assembly architecture without making the user answer every minor question first.
3. Ask before the design depends on unconfirmed hardware or material.
4. Generate CadQuery geometry and named assembly interfaces.
5. Check dimensions, collisions, insertion paths, tool access, and FDM risks.
6. Render static views and an interactive browser preview.
7. Label important features with stable names and show numeric before-and-after design changes.
8. Get visual approval before recommending a physical test.
9. Use the smallest test that preserves the uncertain fit, load path, and print orientation.
10. Record the result and update the model before building the complete object.

## Interactive review

The generated Three.js preview includes:

- orbit, pan, zoom, fit, and camera reset;
- orthographic and perspective views;
- component visibility and exploded view;
- transparent and wireframe modes;
- point-to-point measurement;
- named feature annotations;
- a proposed-change panel with before, after, signed delta, direction, reason, and approval state.

The shared coordinate vocabulary prevents camera-dependent requests such as “move the hole lower.” A revision can instead say: `usb-c-opening center_z: 7.2 → 6.2 mm, -1.0 mm in -Z toward the base`.

## Install

The repository root is the skill root. Clone it into your Codex skills directory:

```bash
git clone https://github.com/bytespell-org/functional-3d-printing.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/functional-3d-printing"
```

The repository is currently private. GitHub authentication is required until its visibility changes.

You can also ask a compatible agent to install the skill from this repository URL.

## CAD runtime

The tested runtime uses Python 3.12, CadQuery 2.8.0, and a pinned `cq_warehouse` revision. Create an isolated environment:

```bash
uv python install 3.12
uv venv --python 3.12 .venv-functional-cad
uv pip install --python .venv-functional-cad/bin/python \
  cadquery==2.8.0 \
  'cq_warehouse @ git+https://github.com/gumyr/cq_warehouse.git@daa46507ecc429c0e2dce11d9d5ffd09b12a42af'
```

Copy [`assets/functional-cad-project/model.py`](assets/functional-cad-project/model.py) as the editable source for a new design. Keep generated STEP, STL, render, and preview files outside the source directory.

Run the model:

```bash
PYTHONPATH=/path/to/functional-3d-printing \
  .venv-functional-cad/bin/python \
  /path/to/functional-3d-printing/scripts/run_model.py \
  model.py \
  --output-dir /tmp/my-functional-part
```

Serve the interactive preview:

```bash
python /path/to/functional-3d-printing/scripts/serve_preview.py \
  /tmp/my-functional-part/preview \
  --host 127.0.0.1 \
  --port 0 \
  --open
```

## Validate the skill

The dependency-free checks run without CadQuery:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/self_test.py
PYTHONDONTWRITEBYTECODE=1 python benchmarks/run_benchmarks.py
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_portability.py .
```

The benchmark suite covers snap fits, small screw bosses, magnets, sliders, press fits, printed threads, clips, inserts, support avoidance, and joint metadata.

## Repository layout

```text
SKILL.md                   Agent workflow and stop conditions
functional_fdm/            Reusable metadata, validation, and CAD primitives
scripts/                   Execution, mesh audit, rendering, preview, and tests
references/                FDM design and mechanical feature guidance
assets/                    Starter model and browser preview
benchmarks/                Functional design regression cases
agents/openai.yaml         Skill interface metadata
```

## Credits

The source and license notes in [`references/sources-and-runtime.md`](references/sources-and-runtime.md) identify the CAD libraries and engineering references used during development.

The README was edited with the concrete-writing rules from Peter Yang's MIT-licensed [No AI Slop](https://github.com/petergyang/no-ai-slop) skill. No No AI Slop code is bundled here.

## License

No license has been selected. The repository is private. Choose a license before making it public.
