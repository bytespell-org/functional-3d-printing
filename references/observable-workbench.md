# Observable workbench

The workbench is a small shared review surface. Its panel shows only a short summary and progress items; point-anchored comments live directly on the model. Printable parts render as solid objects. Non-printable hardware references render as translucent context with distinct visibility chips, so the enclosure and its contents can be positioned and reviewed together without implying that the hardware belongs in the print job. `DesignRecord` remains the source for dimensions, assumptions, questions, and decisions; `record_iteration.py` JSONL remains the source for physical observations and learnings.

## Sidecar

Create the sidecar before sharing a review:

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

The compiled React workbench polls `progress.json` every two seconds with caching disabled. Its source lives in `workbench/`; rebuild with `npm run build` and replace `assets/preview/` with `workbench/dist/`.

Start the generated viewer with the durable server:

```bash
python scripts/serve_preview.py /chosen/output/preview --daemon
```

The launcher binds to `0.0.0.0`, selects a free port, starts a detached process, waits for HTTP 200, and reports LAN URLs. It writes `.preview-server.json`, `.preview-server.pid`, and `.preview-server.log` beside the output. Use it rather than a generic static server because it owns the same-origin endpoints for adding and deleting model comments.
