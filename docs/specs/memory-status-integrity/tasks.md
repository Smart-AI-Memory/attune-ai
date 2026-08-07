# memory-status-integrity — tasks

**Status:** in-progress (2026-08-07)
**Design:** [design.md](design.md) · **Decisions:** [decisions.md](decisions.md)

P1 only. P2/P3 tasks are written when their phase is approved.

## P1 implementation order

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `curated_audit.py` — parse, scan, age, risk, annotate | attune-ai | done | pure library; no corpus paths hardcoded |
| 2 | `AuditReport` — violations, links, pointer integrity, ranking | attune-ai | done | matches the canonical linter's tolerances (D4) |
| 3 | Hermetic tests, golden set pinning both directions | attune-ai | done | 30 tests, `tmp_path` only |
| 4 | `scripts/audit_curated_memory.py` CLI | attune-ai | done | advisory, always exit 0 |
| 5 | Wire unverified-age annotation into recall surfaces | attune-ai | done | `PersonalMemory.query()`; labels only, never reorders |
| 6 | ~~Sweep entry point in `memory_lint.py`~~ | personal | **void** | already implemented (`--check-all`); hook left untouched |
| 7 | ~~Normalize 7 `node_type:` violations~~ | personal | **void** | not violations — provenance is tolerated (D4). Corpus untouched. |
| 8 | Live-corpus receipt over 271 files | receipt | done | 1 violation, matching `memory_lint` exactly; corpus byte-identical |

## Testing strategy

Unit tests only, all hermetic. The library is pure functions over a
directory of markdown, so fixtures are cheap and the real corpus is
never touched by CI.

The golden set must pin **both directions** — a change that flags
everything fails as loudly as one that flags nothing. The hours-old
`project` fixture is the D1 boundary marker.

Explicitly not tested in CI: the 266-file corpus. That is a receipt run
recorded in the PR. A test that reads the real home directory would
violate `project_test_isolation_home_dir_leaks`.

## Rollback plan

Revert the commit. P1 is additive — new module, new script, annotation
strings. No schema change, no migration, no corpus writes.

The authorized corpus normalization (task 7) is outside the PR and is
backed up to a timestamped tarball before the edit.
