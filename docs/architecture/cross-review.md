# Cross Review

## Overview

Cross-review sends the real diff you are about to ship to ONE
non-authoring seat at the round table — a **different model**
(Codex or Antigravity) with different blind spots — and renders
its reply as an advisory findings list. The whole mechanism lives
in `attune.roundtable.review`: it resolves the diff read-only,
briefs the seat under an honest truncation manifest, posts the
reply to the shared board, and renders a dogfood-ledger row.

The binding posture is a spec requirement, not a style choice:
**board-only advisory**. A run "succeeds" whenever the review RAN
— including a clean `NO FINDINGS` reply and an ABSENT seat.
Nothing in this feature may gate a merge, wire an exit code, or
block a command. Only a chair ruling backed by the spec's dogfood
ledger can ever upgrade that posture.

Cross-review is deliberately smaller than the full round table:
one seat, one pass, no deliberation, no promotion loop of its own.
It exists because a second model reading the actual diff catches
contract gaps the authoring model reasons past — the first dogfood
ledger rows record exactly that.

## Concepts

### Advisory by construction

`run_review()` returns `ok: True` for every completed run and a
`status` naming what happened: `findings`, `clean`, `absent`, or
`format_noncompliant`. There is no failure exit code to couple a
gate to. Board unreachability degrades to `board: skipped
(<reason>)` — recorded, never fatal.

### The mandatory reply format

The brief instructs the seat to reply with one line per finding —
`FINDING: <file>:<line> [low|medium|high|critical] <claim>` — or
the single line `NO FINDINGS`. `lint_review()` checks compliance;
a noncompliant reply is **flagged, never repaired** — the run
reports `format_noncompliant` and shows the raw reply, so you see
what the seat actually said rather than a cleaned-up fiction.

### The honest truncation manifest

Diffs are packed per-file under a budget (`DIFF_CAP_CHARS`,
60,000 characters). Files that fit are sent whole; files that do
not fit are named in the manifest as omitted. The manifest rides
everywhere the review does — in the brief the seat sees, in the
board post, and in the rendered result — so a partial review is
always visibly partial.

### Seats

The default reviewer seat is `codex` (chair-ruled, OPEN-1). Any
seat in the round table's `SEAT_RECIPES` works — pass
`seat="antigravity"` for the alternative. A seat whose CLI is not
installed or not authenticated produces an `absent` run, which is
a valid, recorded outcome — not an error.

### The dogfood ledger

Every real run appends one row to
`docs/specs/cross-review/receipts.md`: date, seat, target, files
sent/omitted, findings count, and a disposition the human rules
(`not-triaged` until then). Rows are honest by contract — only
real runs, no synthetic entries. The ledger is both the receipt
trail and the evidence base any posture change must cite.

## Design & extension

### Design decisions

- **D1 — composition over new machinery**: seat recipes, the
  invocation runner, the board, and the compiler's role budgets
  are the round table's; review.py only adds diff resolution,
  the brief, lint, and rendering.
- **D2 — read-only git with an everywhere-visible manifest**: the
  resolver allowlists `branch` / `merge-base` / `diff` /
  `rev-parse`; truncation is always declared.
- **D3 — mandatory format, flagged never repaired**.
- **D4 — advisory rendering, no exit-code coupling**.
- **D5 — per-run ledger rows, honest by contract**.
- **OPEN-1..3 (chair-ruled)** — fixed `codex` default, manual-only
  invocation, 60k diff cap ratified on the T3 ledger's diff-size
  evidence.

### Extension points

- **Seat rotation** — the ruled default is fixed `codex`, but
  rotation was explicitly left open pending more ledger evidence;
  `seat=` already accepts any recipe key.
- **Posture upgrade** — the only sanctioned path: accumulate
  ledger rows whose triaged finding quality earns a chair ruling.
- **New seats** — anything added to the round table's
  `SEAT_RECIPES` is immediately usable as a reviewer.

<!-- attune-generated: source_hash=68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d feature=cross-review kind=architecture generated_at=2026-07-29 -->
