# Decisions: consolidate-claude-md-lessons

## D1 — Editorial ceiling reached at ~15%; domain singletons left intact by design

**Date:** 2026-06-06
**Status:** decided
**PRs:** #646 (worktree-family sample), #647 (all high-redundancy
clusters)

### Context

The spec set a ~30–40% line-cut target for the Lessons Learned section,
with the load-bearing guardrail: *"merge genuine redundancy only; never
drop a distinct lesson — fold specifics into sub-bullets under a richer
header."*

### What was done

Twelve clusters consolidated, one commit each, all editorial and
behavior-neutral:

| Cluster | Change |
|---------|--------|
| Windows / cross-platform | 13 → 3 |
| PyPI trusted-publishing | 9 → 1 |
| Pre-commit & ruff | 15 → 3 |
| Branch-protection & admin-merge | 11 → 3 |
| CodeQL / Scorecard / Copilot | 9 → 3 |
| uv | 13 → 3 |
| SDK (claude-agent-sdk) | 13 → 4 |
| test — mocking & structlog | 12 → 2 |
| test — assertions, coverage, rubric | 13 → 3 |
| CI & workflow-registry | 14 → 5 |
| git-mechanics (tag/stash/rebase/ff) | 12 → 4 |
| SSRF & BaseWorkflow | 10 → 2 |

Net: **435 → ~327 top-level lessons, 7935 → ~6733 lines (−1202, ~15%)**,
zero distinct lessons lost, zero dangling cross-refs. (A 13th commit
added one methodology lesson; a 14th fixed pre-existing
missing-blank-line glitches.)

### Decision

**Stop at ~15%. The 30–40% target is not achievable without violating
the never-drop-a-distinct-lesson guardrail.**

After draining every cluster with genuine duplication, the remaining
lessons are genuinely distinct — domain singletons (RAG / faithfulness,
docs-pipeline / attune-author, Vercel / static-site, release-ceremony).
Each is a measured finding, not a near-duplicate. Reaching 30–40% from
here would require merging unrelated lessons (amputation), which the
guardrail forbids.

~15% with **zero** distinct-lesson loss is the honest ceiling for
faithful editorial consolidation. Reporting the real ceiling is
preferred over padding the number.

### Explicitly out of scope (do not re-litigate)

The domain clusters (RAG, docs-pipeline, Vercel, release-ceremony) were
scanned and left intact deliberately. A future session should NOT
re-open them for line-cut reasons; only consolidate if a genuine
duplicate pair emerges as the corpus grows.

### Method notes (for the next consolidation pass)

Captured as a durable lesson in `.claude/CLAUDE.md`. Summary:

- The title-keyed extract awk matches only lesson *titles* — grep
  bodies too, or a fold leaves a dangling cross-reference.
- Line numbers shift after every deletion — re-grep each sub-cluster
  by content right before editing it.
- Verify per cluster: lesson-count delta, `wc -l`, zero-consecutive-
  blanks, and grep for dangling `existing …lesson` refs.
- Edit tool only (no shell splice); back up `CLAUDE.md` first.
- Wrong/superseded lessons fold into their corrections — that is
  consolidation, not loss.
