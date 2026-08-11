# Functional FDM Mechanical CAD

An agent skill for designing small mechanical parts that can survive contact with a real FDM printer.

The skill uses CadQuery to build editable solid models. It checks fits, assembly paths, fasteners, print orientation, unsupported geometry, and the difference between a CAD claim and a tested physical result. It produces STEP and STL files, static diagnostic renders, an annotated Three.js review page, and concise build notes.

## Annotated 3D review

The browser review gives each critical feature a stable name and shows proposed numeric changes before fabrication.

![Annotated 3D review with named enclosure features and proposed changes](docs/images/annotated-review-overview.png)

Exploded mode separates the enclosure base and display lid while it keeps their shared review labels visible.

![Exploded annotated 3D review showing the enclosure base and display lid](docs/images/annotated-review-exploded.png)

It is meant for parts such as:

- electronics enclosures and removable covers;
- brackets, mounts, spacers, knobs, and adapters;
- press fits, sliding fits, rails, dovetails, and hinges;
- clips, detents, cantilever snaps, and latches;
- M2 through M4 fasteners, captive nuts, and heat-set inserts;
- magnet pockets and simple multipart assemblies.

Decorative mesh generation is outside its scope. Slicing, printer queues, uploads, and printer control are also outside its scope.

## How it works

The agent records the known dimensions, proposes a design, checks the mechanics and FDM risks, and shows an annotated preview. It then recommends a small physical test for any uncertain fit or mechanism. It does not call a function proven until a physical test confirms it.

## How to install

The easiest way to install the skill is to paste this into ChatGPT, Claude Code, Codex, or your preferred coding agent:

```text
Install the /functional-3d-printing skill globally from https://github.com/bytespell-org/functional-3d-printing
```

## Credits

The source and license notes in [`references/sources-and-runtime.md`](references/sources-and-runtime.md) identify the CAD libraries and engineering references used during development.

## License

MIT. See [LICENSE](LICENSE).
