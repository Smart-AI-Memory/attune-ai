---
name: release-prep
source: content/features/release-prep.md
tags:
- release
- publishing
- quality
type: quickstart
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
