# Optional observable workbench

Use the workbench only when collaborative visual review or repeated revisions materially help. A simple part does not need a sidecar or running server. Static images and the generated `preview/` folder are sufficient otherwise. Printable parts render as solids; non-printable references render as translucent context without entering printable outputs. `DesignRecord` remains canonical for design facts, and iteration JSONL remains canonical for physical observations.

## Sidecar

When collaboration is justified, create the sidecar before sharing:

```bash
python scripts/update_progress.py init /chosen/output/progress.json --title "ESP32 enclosure"
```

Add or update useful visible milestones. Progress has no prescribed statuses or phases:

```bash
python scripts/update_progress.py progress /chosen/output/progress.json \
  --id visual-review \
  --title "Visual review" \
  --summary "Annotated preview is ready."
```

Set the short summary shown above the milestones without creating a milestone:

```bash
python scripts/update_progress.py progress /chosen/output/progress.json \
  --summary "Checking the lid fit and cable clearance."
```

Use `--overall-summary` when one command should update both a milestone and the short overall summary.

The only other sidecar commands are `comment-add`, `comment-remove`, and `show`. The script writes atomically and migrates a v1 sidecar on first use. Migration preserves its open and acknowledged comments, drops resolved comments, converts steps into progress items, and discards old answers and learnings because they belong in the canonical design and iteration records.

## Comments

The user can choose the comment-plus action beside **Progress**, click a printable or reference model face, and post a note in place. Existing comments stay visible as blue model callouts; selecting one opens its compact delete control. The preview server writes the object name, local point, and message into the same sidecar. At the start of every turn after sharing the workbench, inspect comments:

```bash
python scripts/update_progress.py show /chosen/output/progress.json
```

After updating the model and the relevant evidence, resolve a comment by removing it. Do not post agent replies, acknowledgements, or statuses:

```bash
python scripts/update_progress.py comment-remove /chosen/output/progress.json \
  --id comment-usb-clearance
```

The browser includes an accessible delete control on each selected model comment as well.

## Serving

The compiled React workbench polls `progress.json` and `manifest.json` in under one second with caching disabled. A changed manifest revision rebuilds the Three.js scene automatically, so the user keeps the same URL and does not need to refresh. Preview generation publishes the manifest atomically and keeps recently superseded content-addressed model files briefly, preventing an open browser from mixing revisions.

Start the server once after the first useful concept. For each iteration, update the short progress summary, change the editable model, and run `run_model.py` again with the same output directory. Do not restart the server: it serves the updated files in place. Full CadQuery execution, tessellation, and audit time still applies; the live update removes avoidable server restarts and browser-refresh latency rather than hiding that work.

The workbench source lives in `workbench/`; rebuild it with `npm run build` and replace `assets/preview/` with `workbench/dist/`.

Start a loopback-only durable viewer:

```bash
python scripts/serve_preview.py /chosen/output/preview --daemon
```

For trusted-LAN collaboration, opt in explicitly:

```bash
python scripts/serve_preview.py /chosen/output/preview --lan --daemon
```

The launcher selects a free port, starts a detached process, waits for HTTP 200, and prints a tokenized review URL. LAN mode prints a warning: anyone with that URL can add or delete comments. Static assets remain readable without authentication; comment mutations require the generated session token. The token is runtime-only and is never written into generated portable preview assets. The launcher writes `.preview-server.json`, `.preview-server.pid`, and `.preview-server.log` beside the output.
