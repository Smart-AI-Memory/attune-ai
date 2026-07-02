# Decisions: Curated-Memory Productionization

**Status:** requirements draft (2026-07-02)
**Created:** 2026-07-02
**Requirements:** [requirements.md](requirements.md)

---

## Decision log

### D1 — Spec drafted from prototype evidence, not speculation
(decided 2026-07-02)

Patrick chose prototype-first / spec-from-evidence at the 2026-07-02
alignment. This spec was drafted only after the prototype produced
receipts: measured recall latencies (FCALL 86us / FT.SEARCH 181us
medians, ~3.6ms cold), a full live review loop through production
form code, and three concrete frictions (interpreter pinning, the
progress-construct semantics mismatch, the auto-stash supersession
contradiction). Every R-item cites its receipt; anything without one
(e.g. speculative recall endpoints) is excluded by construction (R2).

**Why:** the repo's history shows spec text drifting from code
reality when written ahead of evidence (see the "re-validate a spec's
premise" lessons). Writing the spec after the prototype inverts that
risk.

### D2 — Hook interpreter is pinned, never ambient
(decided 2026-07-02)

The R1 hook must invoke an explicit interpreter known to carry
`redis` (the main venv today), not `python3` from the environment.
Evidence: `hydrate.py` failed with `ModuleNotFoundError: No module
named 'redis'` under the worktree venv on first productionization
contact (2026-07-02). Worktree venvs are synced with a minimal extras
set and will recur.
