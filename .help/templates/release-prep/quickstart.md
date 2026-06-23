---
type: quickstart
name: release-prep-quickstart
feature: release-prep
depth: quickstart
generated_at: 2026-06-23T21:32:41.155408+00:00
source_hash: 63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2
status: generated
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

## Quickstart

Run the gate from the CLI at your project root:

```bash
attune workflow run release-gate
```

The output is the readiness report — the verdict (APPROVED / BLOCKED),
the four quality gates with actual-vs-threshold values, a per-agent
breakdown, and any blockers or warnings. The canonical slug
`release-prep` runs the same workflow.
