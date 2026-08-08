# redis-config-truth — decisions

## D1 — Spec originated by chair promotion from the round table

**Date:** 2026-08-08 · **Status:** RULED (chair: Patrick, promotion
form in-session)

Origin: roundtable thread `q-short-term-memory-enhancements-001`
(1 round, halted on convergence; full transcript machine-local at
`~/.attune/reports/roundtable/`, subsystem-wide record at
`docs/reports/roundtable/q-short-term-memory-enhancements-001.md`).
All three seats independently ranked the same two items first, and
the chair promoted them as this spec's mandate:

- C1 — one canonical Redis connection resolver used everywhere
  (→ R1, R2).
- C2 — graceful degradation made observable: classified failures,
  loud-once on non-self-healing classes (→ R3).

Evidence receipt: the live 2026-08-08 `AuthenticationError`
incident — `requirepass` on, `REDIS_PASSWORD` set,
password-less `REDIS_URL`, four independent env readers, silent
fail-open hooks (→ R4 pins it as the regression guard).

Chair rulings recorded with the promotion (scope guards for this
spec): batch-primitive generalization stays DEFERRED (rule of
three); facade restructure/prune is GATED on usage evidence; no
cluster, no new backends, no capability additions (Non-goals).
The full subsystem-wide record, including per-seat positions and
the two member-originated questions, lives in the tracked
roundtable report — this spec's decisions do not restate it.
