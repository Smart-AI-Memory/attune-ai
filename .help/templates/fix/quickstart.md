---
type: quickstart
name: fix-quickstart
feature: fix
depth: quickstart
generated_at: 2026-08-02T16:17:23.326205+00:00
source_hash: 02c4fd57871efde0e308241968a30e45d0a63f6ba866385c62a363e28a5f4b4b
status: generated
---

# Fix Receipts — state the goal and its probes, get a verified receipt

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
