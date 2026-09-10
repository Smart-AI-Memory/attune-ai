---
type: quickstart
name: cross-review-quickstart
feature: cross-review
depth: quickstart
generated_at: 2026-09-10T02:49:28.367557+00:00
source_hash: 58c9e8e81436016ffc446f3411bfe92f56ee98e649190ea7b4c108f275627283
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
