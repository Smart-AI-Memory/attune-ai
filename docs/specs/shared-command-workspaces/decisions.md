# Shared Command Workspaces — Decisions

## D1 — Artifact tier and authority (2026-08-31, chair)

This work is a **spec**: it crosses `attune-ai` and `attune-forms`, changes a
security boundary, spans more than one session, and requires ten follow-on
adapter examples. Requirements are approved. Implementation remains gated per
task; spec creation is not blanket execution authority.

## D2 — Extend the existing renderer (2026-08-31, round table + chair)

The implementation uses the existing `attune_forms.workspace` schemas,
widget renderer, Markdown renderer, and action collector. The new shared
piece is host-side authority and command adapters in `attune-ai`. A parallel
renderer or client-executable callback model is rejected.

## D3 — Phase plus capability, not a universal state machine

View ids describe presentation. The legal action set supplied by the adapter
defines transitions. One workspace revision spans nested Roundtable and Spec
loops, while progress delivery uses a separate sequence. Confirmation binds
to semantic checkpoints, not to the word `preview`.

This resolves the table's main self-identified risk: Fix's linear interaction
shape must not become universal protocol semantics.

## D4 — Coverage is 90% for this initiative (2026-08-31, chair)

The chair modified promotion candidate 19 from the repository's 85% floor to
**90% changed-production-code coverage**. Board message 21 is the promoted
replacement. Boundary receipts remain mandatory; coverage cannot substitute
for them.

## D5 — Rollout order includes both disputed examples

The pilots are `/roundtable` and `/spec`. The next ten-example cohort begins:

1. `/release-prep`
2. `/bug-predict`

Antigravity originally recommended the first for multi-gate operational
rigor; Codex recommended the second for read-only, low-ceremony breadth. The
chair ruled that both ship, in that order, as the first two of the next ten.
Examples 3–10 are selected later from measured semantic gaps.

## D6 — Truncated promotion UI is a failure receipt

The first seven-item native promotion dialog truncated and could not be
scrolled into view. The chair skipped it; that was surface failure, not a
decline. Three compact batches succeeded. Large triage views therefore need
working scrolling, pagination, or compact batching, and the failed shape is a
regression fixture for the Roundtable adapter.

## Round-table provenance

- Thread: `shared-renderer-command-workspaces-001`
- Full machine-local transcript:
  `~/.attune/reports/roundtable/shared-renderer-command-workspaces-001.md`
- Question: message 1
- Claude: absent, message 2 (workspace API usage cap; no inferred vote)
- Round 1: messages 3–6
- Round 2 critiques: messages 7–8
- Round 3 finals: messages 9–10
- Chair cohort ruling: message 11
- Final synthesis: message 13
- Promoted candidates: 14–18, 20, and replacement 21
- Final promotion ruling: message 22
