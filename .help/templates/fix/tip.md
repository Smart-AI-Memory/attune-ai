---
type: tip
name: fix-tip
feature: fix
depth: tip
generated_at: 2026-07-31T16:03:37.162068+00:00
source_hash: cf3ef4afc553319fc03470fe0a2f92a4bc77eda8b02354d75be6c4141752859d
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
