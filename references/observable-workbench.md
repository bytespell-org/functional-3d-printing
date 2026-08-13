# Observable workbench

Use one `progress.json` beside the generated `preview/` folder. It is the cross-turn activity record shared by the agent and the user. The editable model's `DesignRecord` remains the source for design metadata included in generated artifacts.

## Required update loop

Create the sidecar before asking questions:

```bash
python scripts/update_progress.py init /chosen/output/progress.json --title "ESP32 enclosure"
```

Record every user answer as soon as it arrives. Use stable, descriptive IDs so a corrected answer replaces the old value:

```bash
python scripts/update_progress.py answer /chosen/output/progress.json \
  --id display-diameter \
  --question "What is the measured display diameter?" \
  --answer "46.2 mm" \
  --source user \
  --status confirmed
```

Record explicit assumptions the same way with `--status assumed`. Use `needs-confirmation` when the provisional answer still blocks final fit.

Update a workflow step after meaningful work. Repeating `--evidence` adds unique evidence without deleting earlier evidence. Valid step states are `pending`, `in-progress`, `blocked`, and `complete`:

```bash
python scripts/update_progress.py step /chosen/output/progress.json \
  --id visual-review \
  --status in-progress \
  --summary "Annotated assembly is ready for review." \
  --evidence "preview/manifest.json"
```

Update the overall phase separately:

```bash
python scripts/update_progress.py status /chosen/output/progress.json \
  --phase visual-review \
  --status ready-for-review \
  --summary "Review the assembly path and USB-C opening before a test print."
```

Record physical findings as learnings:

```bash
python scripts/update_progress.py learning /chosen/output/progress.json \
  --id lid-needs-insertion-path \
  --statement "A fitted lid also needs a collision-free installation path." \
  --evidence "Revision 1 fit in place but could not slide over the body." \
  --status candidate \
  --applies-to "sliding enclosure lids"
```

Use `show` to validate and inspect the sidecar. Never update it with ad hoc JSON editing.

## Model review threads

The user can choose **Comment**, click a model face, and post a note. The durable preview server writes the part, local point, and message into `review_comments` in the same sidecar. Treat open and acknowledged comments as a work queue.

At the beginning of every turn after sharing the workbench URL, inspect the sidecar before changing CAD:

```bash
python scripts/update_progress.py show /chosen/output/progress.json
```

Reply when the requested action is understood, then acknowledge it:

```bash
python scripts/update_progress.py review-reply /chosen/output/progress.json \
  --id review-a1b2c3d4 \
  --author agent \
  --message "I’ll widen this opening by 0.4 mm and rerun the clearance check."

python scripts/update_progress.py review-status /chosen/output/progress.json \
  --id review-a1b2c3d4 \
  --status acknowledged
```

After updating the model and its evidence, add a short result reply and resolve the thread. Do not resolve a comment merely because it was read.

```bash
python scripts/update_progress.py review-reply /chosen/output/progress.json \
  --id review-a1b2c3d4 \
  --author agent \
  --message "Opening widened; the regenerated assembly clears the cable envelope."

python scripts/update_progress.py review-status /chosen/output/progress.json \
  --id review-a1b2c3d4 \
  --status resolved
```

Agents may create a pin with `review-add --part NAME --position X Y Z --message TEXT --author agent`. Coordinates are millimeters in the selected part’s local STL frame, so the pin remains attached in exploded view.

## Workbench behavior

`run_model.py` creates a missing sidecar as a fallback but does not reconstruct omitted conversation history. The agent remains responsible for recording answers as they arrive.

The compiled React workbench polls `progress.json` every two seconds with cache disabled. It displays:

- overall phase, status, summary, update time, and derived completion;
- each workflow step with status, summary, and evidence;
- every confirmed, assumed, or unresolved answer;
- candidate, validated, and promoted print learnings;
- the Three.js model, annotations, deltas, measurement tools, and exploded view.
- point-anchored review threads, status, and agent replies.

The source UI lives in `workbench/`. It was initialized with the current shadcn preset flow and the preset recorded in `workbench/components.json`. Rebuild it with `npm run build`, then replace `assets/preview/` with `workbench/dist/`.

On narrow screens, keep the model full-height and expose only Fit, Comment, and More. Put comment composition above the mobile keyboard, show review threads in a focused sheet, and keep display modes, part visibility, and exploded view inside More. Use a Z-up orbit for one-finger dragging: horizontal motion changes azimuth, vertical motion changes elevation through top and underside views without rolling the model, and two-finger gestures retain zoom and pan. Do not compress the full desktop control surface onto a phone viewport.

## Durable LAN delivery

Start the server with:

```bash
python scripts/serve_preview.py /chosen/output/preview --daemon
```

The launcher binds to `0.0.0.0`, selects a free port, starts a detached process, waits for an HTTP 200, and prints only LAN-reachable URLs. It writes `.preview-server.json`, `.preview-server.pid`, and `.preview-server.log` beside the output. Use this server rather than a generic static server; it owns the narrow same-origin endpoint that records user comments through `update_progress.py`.

Communicate one printed URL to the user. Do not replace it with `localhost` or `127.0.0.1`. If the script cannot identify a LAN address, use the environment's approved port-sharing method and report that URL instead.
