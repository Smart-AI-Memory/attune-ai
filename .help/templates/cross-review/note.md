---
type: note
name: cross-review-note
feature: cross-review
depth: note
generated_at: 2026-07-29T00:49:32.207827+00:00
source_hash: 68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d
status: generated
---

# One-shot second-opinion diff review by a different-model seat, advisory only

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
