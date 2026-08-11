# Physical iteration and skill learning

## Record one iteration

Record these fields after a useful test:

- part and revision;
- printer, nozzle, material, and profile;
- task stage: small test, prototype, or full print;
- measured defect or successful behavior;
- evidence, including location and measurement;
- root cause or current hypothesis;
- smallest design or process change;
- result: pending, failed, improved, or passed;
- promotion state: no, candidate, validated, or promoted.

Use `scripts/record_iteration.py` to append one JSON object to a JSONL file. Store the log with the project or in a user-selected notes location. The skill does not require one global log.

## Diagnose before another print

Classify the cause:

- requirement error;
- measurement error;
- assembly-order error;
- CAD geometry error;
- mesh export error;
- orientation error;
- slicer profile error;
- material condition;
- printer condition;
- unknown.

Change the smallest responsible item. Keep other parameters constant when possible. Add a small fit or isolated feature test when the full part does not isolate the cause.

## Promote a lesson

Keep project-specific dimensions in the project. Promote only reusable behavior.

Use one of these evidence gates:

- Two independent prints reproduce the problem and correction.
- A geometry or slicer inspection proves the mechanism.
- A small dimensional test measures the correction.

When a lesson passes a gate:

1. Update the applicable reference or script.
2. Add a self-test when the lesson affects a tool.
3. Run `scripts/self_test.py`.
4. Run the platform skill validator.
5. Package a new archive.
6. Record the skill revision in the project iteration log.

Do not automatically rewrite the skill from one failed print. Record it as a candidate first.
