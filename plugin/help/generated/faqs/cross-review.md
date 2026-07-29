---
name: cross-review
source: content/features/cross-review.md
tags:
- review
- roundtable
- multi-llm
- advisory
type: faq
---

# Cross Review FAQ

## Can I make a red cross-review block my merge?

No. The binding posture is board-only advisory; wiring it
into a gate violates the spec. A chair ruling backed by ledger
evidence is the only upgrade path.

## What does it mean when the seat finds nothing?

`NO FINDINGS` is a compliant, recorded outcome
(`status: clean`) — it is evidence, not silence.

## Which seat should I use?

Default `codex`. The first dogfood ledger (five runs,
2026-07-28) recorded codex producing substantive findings on all
three targets while antigravity returned `NO FINDINGS` on both
of its — evidence behind the fixed default.

## Does cross-review modify my repo?

No. Git access is read-only (allowlisted subcommands
only); the one write surface is the ledger row you append
yourself.
