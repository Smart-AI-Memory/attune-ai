---
type: comparison
name: cross-review-comparison
feature: cross-review
depth: comparison
generated_at: 2026-09-10T03:32:43.149566+00:00
source_hash: e370de34d241f5aa9c03988ff78a6aa2796d29a284d14b0de149a158c43cec81
status: generated
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
