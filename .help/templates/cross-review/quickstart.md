---
type: quickstart
name: cross-review-quickstart
feature: cross-review
depth: quickstart
generated_at: 2026-07-29T00:49:32.207827+00:00
source_hash: 68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d
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
