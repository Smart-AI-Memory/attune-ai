# memory-status-integrity — tasks

**Status:** active (2026-08-09) — P1 shipped; **P2 attune-ai side
COMPLETE** (tasks 1/2/4-9 done across #2013/#2014/#2017/#2018 + the
task-9 receipt, every code PR through a codex D11 lane). P2 stays open
on **task 3 only** (canonical `memory_lint.py` accepts `verified:` —
in flight as chip session task_47bd4a3b). **P3 OPENED** (chair
2026-08-09; the phase's measure-first gate executed at authoring —
findings in decisions D8).
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
| 3 | Canonical linter accepts optional `verified:` (schema amendment + co-located test) | personal | done | shipped 2026-08-09 on the chair's machine: `~/.claude/hooks/memory_lint.py` accepts optional top-level `verified:` (strict YYYY-MM-DD, timestamps tolerated by prefix — matches `curated_audit._parse_date`, D4), flags malformed values, keeps the closed schema otherwise; `--fix-all` preserves a valid `verified:`; co-located `test_memory_lint.py` covers accept/malformed/closed-schema + live-fire hook exits 0/2; `--check-all` receipt: 0 violations across 271 files before AND after. Unblocks `keep` verdicts on `~/.claude` corpora via `scripts/review_curated_memory.py` (task 5 gate lifted) |
| 4 | Content-digest binding + append-only verdict history (who / when / what-digest); canonicalised formatting-only change preserves verification | attune-ai | done | `attune.memory.verdict_log` — `.verdicts.jsonl` per corpus, whitespace-token-stream digest (reflow/reformat safe), fail-open readers; sweep stays read-only (byte-identical incl. the log, pinned) |
| 5 | keep / wrong / sharper verdict loop — queue capped (~3/triage), one-keystroke; `wrong` TOMBSTONES (never deletes), `sharper` = edit + verify in one motion | attune-ai | done | `scripts/review_curated_memory.py` + `verdict_log.set_verified` (frontmatter writer, digest-neutral); tombstoned rows excluded from the queue; `keep` on `~/.claude` corpora gated on task 3's linter amendment (noted in the CLI docstring) |
| 6 | Verdict propagation to Redis immediately (invalidate/rewrite the key) | attune-ai | done | `verdict_log.propagate_verdict` — DELETE-only of the derived `attune:memory:node:<stem>` (index stays derived, never authored; next hydration rebuilds keep/sharper); fail-open (P15, ratchet-baselined); durable tombstone respect for `wrong` belongs to the external hydrator (reader/writer co-design) |
| 7 | Ref-triggered queue-jump boolean for project-type: `file:`/`sha:` via local git, `pr:`/`issue:` via `gh`, fail-open (D7 ruling) | attune-ai | done | `attune.memory.ref_triggers` — EXPLICIT typed refs only (`pr:123` etc.; bare `#N` deliberately untreated — no state-at-write, would false-fire on shipped-PR provenance); bounded 5 refs/memory, 10 memories/triage, 5s probes; review CLI floats triggered rows with ⚑ reasons + `queue-jumped` count (the hit-rate signal); CUT-line documented in the module |
| 8 | Epistemic status tiers (settled / check-before-acting / suspect) + author-class on render surfaces; strongest framing on the raw tier | attune-ai | done | `epistemic_tier` + `format_status_annotation` (thresholds 10/45 over age × volatility; tombstoned/invalidated always suspect); wired: `PersonalMemory.query` hits gain `status` (verdict-aware basis), digest cards render tier, sweep CLI shows tier column; suspect+project carries the explicit verify-first instruction; raw-tier framing stays memory-security-hardening R1's provenance envelope (cross-linked) |
| 9 | Live-corpus receipt with verified-basis reporting | receipt | done | 2026-08-09, post-#2018 machinery: **273 files / 13 roots**; bases all `mtime` (zero `verified:` in the wild — honest pre-adoption baseline); tiers 134 settled / 138 check-before-acting / 1 suspect (`project_attune_ai_dev_consolidation`, 66d — matches its known-parked status); integrity 0 schema / 0 type / 0 broken links / 0 dangling; the ONE orphan found (`feedback_model_routing_hybrid.md`, missing MEMORY.md pointer) was fixed in the same session — the sweep caught a real atomic-write violation on its first receipt run |

## P3 implementation order (opened 2026-08-09, D8 — full R6: recall-frequency ranking)

Grounded in the D8 measurement: the telemetry PIPE exists
(`~/.attune/telemetry/memory_events.jsonl`, 4,217 events) but no event
names a curated stem — so P3 instruments first, accrues, then ranks.
Ordering is strict: 2/3 before 4, 4 before 5, 5 before 6; 7-8 ride on
accrued data.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | **GATE** — measure existing recall telemetry before building | receipt | done | executed at authoring (D8): raw tier has per-item identity; curated tier has NO per-stem serve records |
| 2 | Instrument curated serve events: `PersonalMemory.query` hits and `recall_digest` fetches emit a `curated_recall` event naming served stems | attune-ai | done | `attune.memory.serve_telemetry.log_curated_recall` — same sink/envelope as the hook writer (one stream for the task-4 reader), `ATTUNE_MEMORY_TELEMETRY`/`DO_NOT_TRACK` respected, stems-only (pinned by test: envelope fields + stems and nothing else), fail-open, 100% measured |
| 3 | Hydration serve records: the SessionStart `[memory-hydrate]` emitter names hydrated stems | external | pending | personal infra (`~/.attune/memory/session_hydrate.py`) — capability documented, same pattern as P1 task 5c; the highest-volume curated surface, so the frequency term under-counts until this lands |
| 4 | `serve_counts` reader: per-stem serve frequency over a window (default 30d) from `memory_events.jsonl` | attune-ai | done | `serve_telemetry.serve_counts` — includes rotated siblings (a 30d window can span the size-rotation); malformed lines/timestamps skipped, missing sink → all-zero, unreadable sibling warns-and-skips without costing the live counts; window/path/today injectable; 100% measured |
| 5 | R6 ranking term: fold serve frequency into `risk_score` — age × volatility × frequency factor | attune-ai | done | `frequency_factor` (log-scaled, floor 0.25) × age × volatility; serves=None stays NEUTRAL age-only; `AuditReport.rank_basis` + `serves_by_stem`; CLIs opt into the live sink explicitly (library/tests stay home-dir-clean) and render basis + per-row serves |
| 6 | Acceptance regression — the two proof cases pinned in OPPOSITE directions | attune-ai | done | `TestAcceptanceProofCases`: pip-audit shape (8w stale, served every session) ranks TOP with visible unverified-age; rag-gate shape (hours old) scores ZERO and reads settled — the sweep never claims a detection the mechanism cannot make |
| 7 | Review cadence wiring (resolves OQ3): the capped top-3 queue surfaces on an existing weekly surface | attune-ai | pending | ride the Daily/weekly report surface, no new mechanism (D8 of the sibling: hook-driven layers demonstrably empower) |
| 8 | Live receipt with the frequency term active, after an accrual window | receipt | pending | gated on ≥2 weeks of curated serve data post-task-2; record basis distribution + the top-ranked shift vs the task-9 age-only baseline |

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
