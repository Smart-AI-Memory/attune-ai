---
type: quickstart
name: fix-quickstart
feature: fix
depth: quickstart
generated_at: 2026-07-31T16:03:37.162068+00:00
source_hash: cf3ef4afc553319fc03470fe0a2f92a4bc77eda8b02354d75be6c4141752859d
status: generated
---

# Outcome-first fixes — state the goal and its probes, get a verified receipt

## Quickstart

Preview a fix without executing anything (the default — nothing runs,
nothing is written):

```bash
attune fix "boundary order must price as bulk" --probe "python -m pytest tests/test_pricing.py -q"
```

Execute it, scoped to one file:

```bash
attune fix "boundary order must price as bulk" --workflow fix --scope src/pricing.py --probe "python -m pytest tests/test_pricing.py -q" --run
```

Read the exit code:

| Exit | Meaning |
|---|---|
| 0 | every probe passed, scope held, and scope was verifiable |
| 1 | the run completed but a done condition failed or could not be verified |
| 2 | the workflow crashed (a partial receipt is still printed) |
| 3 | CLI error or abstention — nothing ran |
