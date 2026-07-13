# Tasks: Curated-Memory Productionization

**Status:** complete (2026-07-03) — R1/R3/R4 shipped with live receipts (#1212, #1229; D5/D7/D9/D10); riders T4/T5/T7 done 2026-07-02; T6 drift probe live in `session_hydrate.py` with redis made a core dep 2026-07-04; R2 (on-demand) served by the ratified FT.SEARCH query-first discipline. Substrate later absorbed by memory-unification (#1239), serving/promotion contracts preserved.
**Requirements:** [requirements.md](requirements.md)
**Decisions:** [decisions.md](decisions.md) — D8 records the audit
that produced the rider tasks (T4–T7).

Execution order per D3: R1 ✓ shipped → **T1 (R3)** → T2 (R4) →
T3 (R2, on demand). T4–T7 are audit riders — small, independent,
can interleave. R5 (non-mocked receipt) applies to every task.

---

## T1 — R3: recall-digest render
   — **SHIPPED 2026-07-03** (see D9)

Build the "here is what memory carries" surface, replacing the
`progress`-construct misrender (memory facts strike through as done
tasks).

- **Composition check FIRST**: try a display variant of `progress`
  before minting grammar member #6 (extension recipe: compose before
  new `QuestionType`). → **Composition won** (D9): shipped as
  `progress_style: "report"` (a `list_style`-class presentation
  field), no new QuestionType, answer path unchanged.
- Build as **Redis's first real consumer**: the render pulls from
  `FCALL recall_digest` (86us warm), not the JSON file — proving R2's
  foundation en route. → `attune.memory.recall_digest` (fetch via
  FCALL + pure transform + `python -m` entry printing widget HTML).
- **Receipt:** a live widget render + submit round-trip in a real
  session, sourced from the Redis function call. → 2026-07-03: live
  9-node digest fetched from warm Redis, rendered via `show_widget`
  from production `form_to_widget_html` output; non-mocked real-Redis
  tests in `tests/unit/memory/test_recall_digest.py` green.

## T2 — R4: stash → curated promotion path
   — **SHIPPED 2026-07-03** (see D10)

A deliberate, reviewable step proposing auto-stashed findings for
promotion into the curated graph (agent proposes, Patrick verdicts).
Bulk import is explicitly wrong (the 2026-07-02 supersession
contradiction is the evidence).

- Promotion writes provenance metadata (source stash entry, review
  verdict, date) onto the resulting node. → `attune.memory.promotion`
  (`promotion_candidates` via the hook's own backend resolution;
  per-candidate `decision` verdict form; `promote()` with the
  `promoted_from_*`/`review_*` provenance keys; no promote-all path).
- **Receipt:** one real stashed finding promoted with provenance
  visible on the node. → 2026-07-03: TWO real findings promoted via a
  live widget verdict (`resp-widget-resp-20260703-013922`), provenance
  on both nodes, memory-repo commits `914f376`/`fbf774c`, re-hydrated
  digest carries them first (11 active nodes). Dogfood also caught and
  fixed the status="open" recall-invisibility bug (D10).

## T3 — R2: targeted recall procedures (on demand)

Topic/tag-filtered search + single-node fetch as Redis Functions or
parameterized `FT.SEARCH`. Ship only with a demonstrated consumer —
T1's digest pull is the first; add procedures as consumers appear.

---

## Audit riders (2026-07-02 memory-suite audit — see D8)

## T4 — Harness-corpus hygiene pass + `memory_lint.py` default fix
   — **DONE 2026-07-02** (personal infra, same session as the audit)

The per-project corpus (`~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/`,
78 files) carries **134 violations** (31× R1 name/stem drift, 76× R2
schema drift, 27× R4 dangling links, 2 files with no frontmatter) —
unenforced because `memory_lint.py --check-all`'s bare default scans
only the GLOBAL dir. Graph ingestion silently drops dangling links,
so any future promotion/unification inherits the mess.

- Fix the lint default (scan global + per-project dirs, or require an
  explicit path) — personal infra, `~/.claude/hooks/memory_lint.py`.
- Mechanical corpus normalization: underscore stems, `metadata.type`
  nesting, drop `originSessionId`, repair link slugs.
- **Receipt:** `memory_lint.py --check-all <project dir>` → 0
  violations, run explicitly against the per-project path.
- **Done receipt (2026-07-02):** bare `--check-all` now sweeps the
  global dir + all `~/.claude/projects/*/memory` dirs; the attune-ai
  corpus was already clean (a parallel task fixed the 134), but the
  multi-dir sweep surfaced 153 MORE hidden violations across six
  other project corpora — `--fix-all` migrated 74 files; R3 relaxed
  to accept table-form indexes; all 10 corpora now lint 0. Backup:
  `~/.attune/memory-corpus-backup-20260702-210218.tgz`.

## T5 — `personal_memory_recall` dedup fix
   — **DONE 2026-07-02** (commit `b38c2ed08` on this branch)

Live observation (2026-07-02): recall for a store containing ONE
topic returned the same file twice (`dispatch_test/decision.md`,
scores 7.501 / 7.5). Root cause (controlled repro, not the guessed
double-indexing): with cwd = home, the project-root default
(`cwd/.attune/memory`) IS the global root — the corpus was scanned
twice, project boost accounting for the exact 0.001 score gap.

- Fix: constructor collapses an identical project root; `query()`
  dedups by path (best score wins).
- **Receipt:** two non-mocked regression tests against real
  attune_rag (54/54 green); live MCP re-verify needs the plugin
  server restarted (it holds the pre-fix module).

## T6 — "Registered ≠ working" drift self-report for the MCP surface

Same-session split-brain observed 2026-07-02: the SessionStart
hydration hook reached Redis while the plugin MCP server's venv
lacked `[redis]` — `redis_health_check` failed until a manual
`uv sync --extra redis`. The suite should surface this itself.

- Extend the hydration hook (or a SessionStart sibling) to also probe
  the MCP-tool env's Redis reachability and print a loud
  `[memory-drift]` line on mismatch (pattern: D5's loud no-op).
- Durable half: decide where `[redis]` belongs for worktree syncs
  (dev extra vs documented sync flags) so the gap stops recurring
  per worktree.
- **Receipt:** a deliberately-broken env produces the drift line in
  fresh-session context.

## T7 — Recall-eval as a release gate
   — **DONE 2026-07-02** (this branch; chosen over a broad
   docs+testing pass via a live pushback form, Patrick's pick)

9.3.0 shipped with `PersonalMemory.query()` 100% broken (hit@1 0/18)
and no gate caught it — all local testing ran main, not the artifact.

- `scripts/release_recall_gate.py`: builds/accepts the wheel,
  installs into a clean venv with isolated `$HOME` and
  `ANTHROPIC_API_KEY=""`, runs 3 capture→recall round-trips through
  the user-facing CLI, asserts hit@3 = 3/3 and no duplicate paths
  (the 9.4.x dedup class). Exit 1 = do not publish.
- Enforced in `publish-pypi.yml` (build job, before artifact upload)
  AND advisory in the release-execute skill (pre-tag, so failures
  surface before tagging).
- **Receipt:** maiden run against the 9.4.0 wheel passed 3/3
  (2026-07-02); next release exercises the CI enforcement.

---

## Deferred (noted, not tasked)

- **Subsystem consolidation review** — `attune.memory` is 42 modules
  / ~11.5k LOC with overlapping stores (`simple_storage`,
  `file_stash`, `file_session`, `summary_index`, …) while live value
  concentrates in a few hooks. Run the subsystem-value-gate review
  only AFTER T1–T2 settle occupancy — consolidating before the
  occupant moves in repeats the build-ahead-of-use pattern.
