---
type: comparison
name: release-prep-comparison
feature: release-prep
depth: comparison
generated_at: 2026-06-23T21:32:41.155408+00:00
source_hash: 63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2
status: generated
---

# Deterministic pre-release gate — four agents run real bandit, ruff, pytest, and docstring checks against hard thresholds

## Comparison

Release-prep is the **gate** half of the release pair:

| Workflow | Slug(s) | Kind | What it does |
|----------|---------|------|--------------|
| `release-prep` (this feature) | `release-prep`, `release-gate` | Deterministic gate (agent team) | Runs real bandit / ruff / pytest / docstring checks against hard thresholds; returns APPROVED / BLOCKED. CLI-only; $0 by default. |
| `release-notes` | `release-notes` | Advisory (SDK) | Drafts a changelog + an LLM go/no-go. Does not block. Subscription-billed with depth budget caps. |

Reach for **release-prep** when you need an enforced gate on measured
numbers. Reach for **release-notes** when you want the changelog drafted
and a recommendation. A common flow is release-notes to draft and read
the landscape, then release-prep to gate the actual ship.

When all gates pass, the report's next step points at **secure-release**
(`attune workflow run secure-release`), the composite security pipeline.
