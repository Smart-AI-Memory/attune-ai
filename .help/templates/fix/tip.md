---
type: tip
name: fix-tip
feature: fix
depth: tip
generated_at: 2026-07-31T11:22:57.025655+00:00
source_hash: 4069f8ae171ca3c4ccb53ebae95b598ce6d800fcd66ed605ccb4583f5d3f9290
status: generated
---

# Outcome-first fixes — state the goal and its probes, get a verified receipt

## Notes & tips

- Preview first. The preview costs nothing and catches malformed probes
  before a run.
- Prefer plural probes that are distinct from the fix target — a target
  probe plus a suite probe plus a scope constraint is the shape that
  actually proves something.
- The receipt distinguishes "changed nothing and the conditions already
  held" from "fixed and verified". If you see the former, check that
  your goal described a real gap.
- Probe subprocesses run with bytecode and pytest-cache writes disabled
  so their own artifacts are never mistaken for the fix's changes.
