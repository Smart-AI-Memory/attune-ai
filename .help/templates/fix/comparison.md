---
type: comparison
name: fix-comparison
feature: fix
depth: comparison
generated_at: 2026-07-31T11:22:57.025655+00:00
source_hash: 4069f8ae171ca3c4ccb53ebae95b598ce6d800fcd66ed605ccb4583f5d3f9290
status: generated
---

# Outcome-first fixes — state the goal and its probes, get a verified receipt

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
