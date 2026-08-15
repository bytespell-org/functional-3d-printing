# Functional 3D Printing

An agent skill for designing small mechanical parts that can survive contact with a real FDM printer.

The skill uses CadQuery to build editable solid models. Its workflow scales from a one-piece spacer to a serviceable electronics assembly: it validates only the fit, assembly, motion, access, and print risks that are actually present. It produces editable source, STEP/STL files, static diagnostic renders, a portable Three.js review artifact, and concise build notes without confusing CAD checks with physical proof.

## Optional observable 3D review

The browser review gives critical features stable names and keeps the current progress and model comments in one place. Dimensions, assumptions, and decisions stay in the editable `DesignRecord`; physical results stay in the iteration JSONL.

For collaborative iteration, the workbench reads an atomic `progress.json` sidecar and displays point-anchored comments. The server is loopback-only by default; trusted-LAN sharing requires explicit `--lan`, and comment changes require the generated session token. A simple part can stop at static images and the portable preview folder without starting a server.

## Annotated models

Stable annotations make it easy to point to a feature while assembled and exploded views clarify how parts fit together.

It is meant for parts such as:

- electronics enclosures and removable covers;
- brackets, mounts, spacers, knobs, and adapters;
- press fits, sliding fits, rails, dovetails, and hinges;
- clips, detents, cantilever snaps, and latches;
- M2 through M4 fasteners, captive nuts, and heat-set inserts;
- magnet pockets and simple multipart assemblies.

Decorative mesh generation is outside its scope. Slicing, printer queues, uploads, and printer control are also outside its scope.

## How it works

The agent chooses the smallest testable architecture, records known dimensions and source provenance when hardware controls fit, and checks the applicable mechanics and FDM risks. It recommends a small physical test for uncertain critical interfaces. Readiness is stage-based: concept-ready, print-ready, then function-confirmed only after representative physical testing.

`benchmarks/run_benchmarks.py` runs library regressions. [`benchmarks/eval-prompts.json`](benchmarks/eval-prompts.json) is a manual/future agent-evaluation catalog; the benchmark runner validates the catalog but does not claim to execute its prompts.

## How to install

The easiest way to install the skill is to paste this into ChatGPT, Claude Code, Codex, or your preferred coding agent:

```text
Install the /functional-3d-printing skill globally from https://github.com/bytespell-org/functional-3d-printing
```

## Credits

The source and license notes in [`references/sources-and-runtime.md`](references/sources-and-runtime.md) identify the CAD libraries and engineering references used during development.

## License

MIT. See [LICENSE](LICENSE).
