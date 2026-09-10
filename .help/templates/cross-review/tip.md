---
type: tip
name: cross-review-tip
feature: cross-review
depth: tip
generated_at: 2026-09-10T03:32:43.149566+00:00
source_hash: e370de34d241f5aa9c03988ff78a6aa2796d29a284d14b0de149a158c43cec81
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
