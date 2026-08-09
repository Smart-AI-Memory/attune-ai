# memory-status-integrity — tasks

**Status:** active (2026-08-09) — P1 shipped; **P2 OPENED** (chair phase
gate + both residual rulings, D7); P3 tasks unwritten until its phase is
approved
**Design:** [design.md](design.md) · **Decisions:** [decisions.md](decisions.md)

## P1 implementation order

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `curated_audit.py` — parse, scan, age, risk, annotate | attune-ai | done | pure library; no corpus paths hardcoded |
| 2 | `AuditReport` — violations, links, pointer integrity, ranking | attune-ai | done | matches the canonical linter's tolerances (D4) |
| 3 | Hermetic tests, golden set pinning both directions | attune-ai | done | 30 tests, `tmp_path` only |
| 4 | `scripts/audit_curated_memory.py` CLI | attune-ai | done | advisory, always exit 0 |
| 5a | Age annotation: `PersonalMemory.query()` + sweep CLI | attune-ai | done | shipped in #1975; labels only, never reorders |
| 5b | Age annotation: `recall_digest` cards (from `updated_at`) | attune-ai | done | review follow-up — #1975 marked row 5 done while this surface was unshipped |
| 5c | Age annotation: SessionStart hydration line | external | documented | emitter is personal infra (attune-agent-memory repo); capability + one-liner documented in design.md § Surfaces |
| 6 | ~~Sweep entry point in `memory_lint.py`~~ | personal | **void** | already implemented (`--check-all`); hook left untouched |
| 7 | ~~Normalize 7 `node_type:` violations~~ | personal | **void** | not violations — provenance is tolerated (D4). Corpus untouched. |
| 8 | Live-corpus receipt over 271 files | receipt | done | 1 violation, matching `memory_lint` exactly; corpus byte-identical |

## P2 implementation order (opened 2026-08-09, D6 scope + D7 rulings)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | **GATE** — parser alignment with the canonical linter: indented continuation lines (folded/literal block scalars) never parse as top-level keys (D5#3, D6#1) | attune-ai | done | `_parse_frontmatter` collects block-scalar continuations as VALUE content; 4 fixtures pin both directions (false-positive gone, forbidden key still flagged once) |
| 2 | `verified:` preferred over mtime in ranking + the report/CLI states the basis per file | attune-ai | done | `resolve_age_basis` labels (verified / verified-unbound / invalidated / tombstoned / mtime); `AuditReport.age_bases` + CLI/JSON render per row |
| 3 | Canonical linter accepts optional `verified:` (schema amendment + co-located test) | personal | pending | one file, one test (D2); reader/writer co-design — `~/.claude/hooks/memory_lint.py` |
| 4 | Content-digest binding + append-only verdict history (who / when / what-digest); canonicalised formatting-only change preserves verification | attune-ai | done | `attune.memory.verdict_log` — `.verdicts.jsonl` per corpus, whitespace-token-stream digest (reflow/reformat safe), fail-open readers; sweep stays read-only (byte-identical incl. the log, pinned) |
| 5 | keep / wrong / sharper verdict loop — queue capped (~3/triage), one-keystroke; `wrong` TOMBSTONES (never deletes), `sharper` = edit + verify in one motion | attune-ai | done | `scripts/review_curated_memory.py` + `verdict_log.set_verified` (frontmatter writer, digest-neutral); tombstoned rows excluded from the queue; `keep` on `~/.claude` corpora gated on task 3's linter amendment (noted in the CLI docstring) |
| 6 | Verdict propagation to Redis immediately (invalidate/rewrite the key) | attune-ai | done | `verdict_log.propagate_verdict` — DELETE-only of the derived `attune:memory:node:<stem>` (index stays derived, never authored; next hydration rebuilds keep/sharper); fail-open (P15, ratchet-baselined); durable tombstone respect for `wrong` belongs to the external hydrator (reader/writer co-design) |
| 7 | Ref-triggered queue-jump boolean for project-type: `file:`/`sha:` via local git, `pr:`/`issue:` via `gh`, fail-open (D7 ruling) | attune-ai | done | `attune.memory.ref_triggers` — EXPLICIT typed refs only (`pr:123` etc.; bare `#N` deliberately untreated — no state-at-write, would false-fire on shipped-PR provenance); bounded 5 refs/memory, 10 memories/triage, 5s probes; review CLI floats triggered rows with ⚑ reasons + `queue-jumped` count (the hit-rate signal); CUT-line documented in the module |
| 8 | Epistemic status tiers (settled / check-before-acting / suspect) + author-class on render surfaces; strongest framing on the raw tier | attune-ai | done | `epistemic_tier` + `format_status_annotation` (thresholds 10/45 over age × volatility; tombstoned/invalidated always suspect); wired: `PersonalMemory.query` hits gain `status` (verdict-aware basis), digest cards render tier, sweep CLI shows tier column; suspect+project carries the explicit verify-first instruction; raw-tier framing stays memory-security-hardening R1's provenance envelope (cross-linked) |
| 9 | Live-corpus receipt with verified-basis reporting | receipt | pending | PR receipt, never CI |

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
