# Cross Review — Requirements

**Status:** APPROVED (chair, 2026-07-22; OPEN-1..3 held for the
07-27 usage read) — implementation staged post-lift, SECOND after
cross-provider-session-handoff.
**Slug:** `cross-review`
**Provenance:** roundtable `q-multi-llm-obvious-win-001` (chair
same-day amendment: committed, not usage-gated) — see
`docs/reports/roundtable/q-multi-llm-obvious-win-001.md` and
tracking issue #1602.

## Problem

The full roundtable is an occasional instrument (design questions,
spec authoring). The daily-frequency multi-LLM action is smaller: a
pre-merge second opinion from a DIFFERENT model on a real diff —
different model, different blind spots. Today that requires manually
convening the table or hand-briefing a CLI; nothing packages
one-seat adversarial review as a habit-sized action, and nothing
records its findings for the chair.

## Binding posture (chair amendment, 2026-07-22)

Board-only ADVISORY. Never a merge gate, never a CI check, until a
future chair ruling — backed by this spec's dogfood ledger — earns
that upgrade. This is a requirement, not guidance: any task or PR
that wires cross_review output into a blocking path violates the
spec.

## Requirements

### R1 — one-seat review of the real artifact

A `/cross-review` skill (moderator-run, roundtable R1 model: seats
are text-in/text-out; all board and file I/O through the moderator).

- Target: the current branch's diff vs its merge base with
  origin/main by default; `staged` and explicit-path variants
  allowed.
- The reviewer seat receives the ACTUAL unified diff (bounded, R3)
  — never a paraphrase or summary of it.
- Exactly one non-authoring seat per run (Codex or Antigravity when
  the authoring session is Claude; seat choice default is OPEN-1).
- The brief demands adversarial posture: findings with
  file:line anchors, a severity guess, and an explicit
  "no findings" statement when clean — silence is not a pass.

### R2 — board-recorded, advisory-rendered

- Every run posts to a board thread (`review-<branch-slug>-<n>`):
  the target description, the seat's findings, and the moderator's
  disposition note. TTL applies; promotion (Step 6) is the durable
  path.
- The session renders findings as advisory items for the human;
  the tool's exit status is ALWAYS success when the review ran —
  findings never fail a command (binding posture).

### R3 — bounded input, honest truncation accounting

- Diff budget with a named cap; when the diff exceeds it, the tool
  reports WHICH files were sent vs omitted (no silent truncation —
  a review of half the diff must say so, in the board post and the
  rendering).
- Caps live beside the roundtable's role budgets
  (`compiler.ROLE_REPLY_CHARS` pattern).

### R4 — absent-seat and failure honesty

- Missing/unauthenticated/timed-out seat CLI → the run reports
  ABSENT with the reason (roundtable R6); it never falls back to
  the authoring model reviewing itself and never fabricates a
  review.
- A seat reply that ignores the format is posted as-received and
  flagged `format_noncompliant` — not repaired into false
  structure.

### R5 — dogfood ledger (the gate-upgrade evidence)

- `receipts.md` in this spec accrues one row per real run: date,
  seat, target size, findings count, and the human's disposition
  (real / noise / not-triaged). No synthetic rows (D7 discipline).
- The ledger is the ONLY admissible evidence for any future
  chair ruling that upgrades cross_review beyond advisory.

### R6 — OPEN items (resolved at/after the 07-27 usage read)

- OPEN-1: default reviewer seat (fixed default vs rotation).
- OPEN-2: invocation ergonomics — manual-only vs a suggested
  cadence (e.g. a pre-PR reminder); auto-trigger is v1 non-goal
  either way.
- OPEN-3: diff-budget number (frequency and typical diff size from
  the usage read inform the cap).

## Non-goals

- No multi-seat panel — that is the full roundtable.
- No auto-trigger on commit/PR events in v1 (OPEN-2 decides only
  whether a *suggestion* surface exists).
- No CI wiring, no exit-code gating, no required check — see
  Binding posture.
- No new subsystem: reuses roundtable Board, seat invocation
  recipes, and budget patterns.

## Dependencies

- Sequenced AFTER cross-provider-session-handoff (chair ruling).
- Roundtable core on main (already shipped); no transport-stack
  dependency for the mechanism itself — the sequencing is a chair
  ruling, not a code dependency.
- OPEN-1..3 rulings at the 07-27 sitting (usage-signal read).
