# Handoff — release-audit-stage spec shipped; build work queued

**Branch:** `claude/roundtable-audit-workflow-b99ec3` · **PR:**
https://github.com/Smart-AI-Memory/attune-ai/pull/2171 · 2026-08-22

## Verified state (commands actually run)

- Spec + decisions + curated stub committed (`fca6bbf4f`), pushed,
  PR #2171 open against main. Docs-only.
- Board thread `q-release-audit-roundtable-stage-001` (13 msgs,
  TTL ~7 days from 2026-08-22): everything durable is promoted;
  full transcript at `~/.attune/reports/roundtable/<slug>.md`.
- Memory corpus lint: 0 violations (fixed a wrong `[[global:]]`
  prefix in `project_exceptions_removal_held_for_major`).
- Two lessons in the docs outbox
  (`roundtable-board-draft-kind`, `macos-timeout-127-seat-invocation`)
  awaiting the next outbox sweep digest.

## Next actions (chair-ratified order, D8 + feedback picks)

1. **Phase X — class-M receipt check** (independent, ships first):
   PR metadata + commit-trailer check per R6 of
   `docs/specs/release-audit-stage/requirements.md`. Structured
   one-shot; no Phase 0 dependency.
2. **Phase 0 — rule pack + derived register** (R1+R2, blocking for
   the stage): promote `~/.attune/reports/attune-ai-review/
   sweep_suite_v2_r7.py` into `src/attune/classes/`; derive status,
   never author it. Multi-PR.
3. **Calibration on attune-forms pre-fix commit** (with or right
   after Phase 0): the forms-23 defects are pinned ground truth;
   record recall/precision honestly per R1 (no 1.0 bar — declined,
   see dissent register).

## Risks / open

- OQ3's rule→gate-test identity mapping needs its own drift guard
  (R2) — the seat flagged it as unpriced scope; price it in Phase 0.
- Teeth (Phase 2) arm ONLY on a chair-recorded promotion naming the
  rule-pack version (R5) — do not wire the hard-block early.

Delete this file when the branch merges.
