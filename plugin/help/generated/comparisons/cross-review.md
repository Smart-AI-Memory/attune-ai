---
name: cross-review
source: content/features/cross-review.md
tags:
- review
- roundtable
- multi-llm
- advisory
type: comparison
---

# One-shot second-opinion diff review by a different-model seat, advisory only

## Comparison

- **vs `/roundtable`** — the round table convenes every seat for
  deliberation with a chair-ruled promotion flow; cross-review is
  one seat, one pass, on a concrete diff. Use the table for design
  questions, cross-review for "does another model see a problem in
  this change?"
- **vs `/deep-review`** — deep-review is a multi-pass review by
  the same model family driving your session; cross-review's value
  is precisely that the reviewer is a DIFFERENT model with
  different blind spots.
- **vs CI review bots** — cross-review never gates anything; it is
  advisory input to a human, recorded on the board and in the
  ledger.
