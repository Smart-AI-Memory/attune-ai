# Handoff — release-audit-stage spec shipped; build work queued

**Branch:** `claude/roundtable-audit-workflow-b99ec3` · **PR:**
https://github.com/Smart-AI-Memory/attune-ai/pull/2171 · 2026-08-22

## Goal

Ship the release-audit-stage spec (roundtable-authored) and queue its
build phases in the chair-ratified order.

## Acceptance criteria

- Spec (`requirements.md` R1–R7, `decisions.md` D1–D9) + curated
  roundtable stub merged to main via PR #2171, CI green.
- Build order recorded: Phase X first, then Phase 0, then
  calibration; teeth (Phase 2) unarmed until chair promotion.

## Scope and assumptions

Docs-only on this branch. Code work (Phase X onward) happens on its
own branches — Phase X is already up as PR #2172
(`claude/class-m-receipt-check`). Assumes the class register and
sweep suite remain machine-local until Phase 0 promotes them.

## Current state

- Spec + decisions + curated stub committed and pushed; PR #2171
  open against main.
- Board thread `q-release-audit-roundtable-stage-001` (13 msgs, TTL
  ~7 days from 2026-08-22): all durable content promoted; full
  transcript at `~/.attune/reports/roundtable/<slug>.md`.
- Phase X implemented and shipped separately: PR #2172
  (`attune.classes.class_m` + `mock_worklist`, 29 tests, calibration
  receipt in the PR body).
- Two lessons in the docs outbox (`roundtable-board-draft-kind`,
  `macos-timeout-127-seat-invocation`) awaiting the next sweep.
- Memory: `feedback_governance_spec_drafter_critics` written; corpus
  lint 0 violations.

## Verification

- Spec lint: round-2 draft passed `compiler.lint_draft`; both
  critiques passed `compiler.lint_critique` (receipts in the curated
  stub's provenance section).
- Phase X: 29 tests green locally (incl. real-git `check_range`
  round trip); coverage 85% measured via the /tmp worktree recipe.
- This handoff: sections conform to `templates/agent-handoff.md`
  (the corpus lint failed PR #2171's first CI run on exactly that —
  fixed here).

## Next action

1. **Merge PR #2171** (spec) and **PR #2172** (Phase X) when green —
   each needs its own chair merge word bound to its head SHA.
2. **Phase 0** — rule pack + derived register (R1+R2): promote
   `~/.attune/reports/attune-ai-review/sweep_suite_v2_r7.py` into
   `src/attune/classes/`; derive status, never author. Multi-PR;
   price OQ3's rule→gate-test drift guard here.
3. **Calibration on attune-forms pre-fix commit** (forms-23 ground
   truth) — record recall/precision honestly per R1; no 1.0 bar
   (declined, dissent register).

Delete this file when the branch merges.
