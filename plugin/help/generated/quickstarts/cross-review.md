---
name: cross-review
source: content/features/cross-review.md
tags:
- review
- roundtable
- multi-llm
- advisory
type: quickstart
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
