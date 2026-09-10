---
type: tip
name: cross-review-tip
feature: cross-review
depth: tip
generated_at: 2026-09-10T02:49:28.367557+00:00
source_hash: 58c9e8e81436016ffc446f3411bfe92f56ee98e649190ea7b4c108f275627283
status: generated
---

# One-shot second-opinion diff review by a different-model seat, advisory only

## Notes & tips

- Same-diff runs across two seats are cheap comparative evidence —
  the T3 dogfood used exactly that pairing to test the default.
- The board thread id (`review-<branch-slug>-<stamp>`) is in every
  result; findings worth keeping go through the roundtable
  promotion flow, since board threads are TTL'd and the ledger row
  is what endures.
- Reviewing another branch: check it out in a detached scratch
  worktree and pass that worktree as `repo_root` — the resolver
  reviews whatever `HEAD` is.
