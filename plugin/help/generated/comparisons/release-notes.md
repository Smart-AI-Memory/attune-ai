---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: comparison
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

## Comparison

Release-notes is the **advisory** half of the release pair. The two
share the "release prep" idea but differ in kind:

| Workflow | Slug(s) | Kind | What it does |
|----------|---------|------|--------------|
| `release-notes` (this feature) | `release-notes` | Advisory (SDK) | Drafts a changelog + an LLM go/no-go. Does not block. Subscription-billed with depth budget caps. |
| `release-prep` | `release-prep`, `release-gate` | Deterministic gate (agent team) | Runs real `bandit` / `ruff` / `pytest` / docstring checks against hard thresholds and returns an APPROVED / BLOCKED verdict. CLI-only. |

Reach for **release-notes** when you want the changelog written and a
recommendation. Reach for **release-prep** (`attune workflow run
release-gate`) when you need an enforced gate on measured numbers. A
common flow is release-notes to draft the notes and read the
landscape, then release-prep to gate the actual ship.

Two adjacent tools the `/release` skill also exposes: `dependency_check`
(dependency audit / vulnerability scan) and `secure_release` (the
composite security pipeline).
