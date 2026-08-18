# Session-Start Integrity — Tasks

**Status:** active (2026-08-18) — requirements approved by chair.

One PR unless noted; personal-infra tasks receipt-verified live.

- **T1** Reconciler provenance: frontmatter parse + `--stamp`
  writer + fail-closed mismatch + STALE TTL + no-provenance warn
  (R1–R3). Tests: `tests/unit/hooks/test_starter_reconciler_*`
  cover match/mismatch/absent/stale × stamp idempotence.
- **T2** Corpus drift-guard test over `docs/specs/*/requirements.md`
  with shrink-only unknown ratchet (R4); fix any offender spec
  status lines found while seeding.
- **T3** Personal orientation regex fix + live re-run receipt (R5).
- **T4** Fleet registry + `scripts/sync_session_hooks.py`
  (`--check`/`--write`) + preflight fleet-audit line + unit tests
  (R6–R7).
- **T5** Live remediation (R8 + R9): projector `--write` across
  registry; retire the global starter — archive it, migrate the
  attune-ai queue to a stamped project-local starter, repoint
  `starter_prompt_nudge.py` at handoffs-first; record receipts in
  `decisions.md`.
- **T6** Ship: pre-flight pinned formatters, commit, PR, CI green.

Concerns: `impl` + `test` + `regression-guard` (T2 ratchet,
projector `--check`) — no `docs`/`release-notes` (internal
infra; changelog on release only if user-visible).
