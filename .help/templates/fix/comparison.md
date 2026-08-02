---
type: comparison
name: fix-comparison
feature: fix
depth: comparison
generated_at: 2026-08-02T16:17:23.326205+00:00
source_hash: 02c4fd57871efde0e308241968a30e45d0a63f6ba866385c62a363e28a5f4b4b
status: generated
---

# Fix Receipts — state the goal and its probes, get a verified receipt

## Comparison

| | `attune fix` | `/fix-test` skill | `attune workflow run` |
|---|---|---|---|
| Surface | CLI | Claude Code conversation | CLI |
| You supply | goal + probes + scope | a failing test | workflow name + inputs |
| Verification | probes run by the CLI, independently | the skill re-runs the test as it iterates | whatever the workflow reports |
| Best for | a known outcome you want verified | a failure you want diagnosed | direct access to a specific workflow |

`attune workflow run` is unchanged and remains the expert path.
Outcome-first does not mean the internal machinery disappears — it
means you should not *need* it.
