---
type: quickstart
name: cross-review-quickstart
feature: cross-review
depth: quickstart
generated_at: 2026-09-10T03:32:43.149566+00:00
source_hash: e370de34d241f5aa9c03988ff78a6aa2796d29a284d14b0de149a158c43cec81
status: generated
---

# One-shot second-opinion diff review by a different-model seat, advisory only

## Quickstart

From a Claude Code session in your repo, run the skill:

```text
/cross-review
```

It reviews the current branch against its merge-base with
`origin/main`, briefs the default seat, and renders the findings
as an advisory list plus the ledger row. Variants:

```text
/cross-review staged
/cross-review seat=antigravity
```
