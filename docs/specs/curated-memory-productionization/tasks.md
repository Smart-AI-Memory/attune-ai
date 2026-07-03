# Tasks: Curated-Memory Productionization

**Status:** drafted 2026-07-02 (from the memory-suite audit session)
**Requirements:** [requirements.md](requirements.md)
**Decisions:** [decisions.md](decisions.md) — D8 records the audit
that produced the rider tasks (T4–T7).

Execution order per D3: R1 ✓ shipped → **T1 (R3)** → T2 (R4) →
T3 (R2, on demand). T4–T7 are audit riders — small, independent,
can interleave. R5 (non-mocked receipt) applies to every task.

---

## T1 — R3: recall-digest render (NEXT)

Build the "here is what memory carries" surface, replacing the
`progress`-construct misrender (memory facts strike through as done
tasks).

- **Composition check FIRST**: try a display variant of `progress`
  before minting grammar member #6 (extension recipe: compose before
  new `QuestionType`).
- Build as **Redis's first real consumer**: the render pulls from
  `FCALL recall_digest` (86us warm), not the JSON file — proving R2's
  foundation en route.
- **Receipt:** a live widget render + submit round-trip in a real
  session, sourced from the Redis function call.

## T2 — R4: stash → curated promotion path

A deliberate, reviewable step proposing auto-stashed findings for
promotion into the curated graph (agent proposes, Patrick verdicts).
Bulk import is explicitly wrong (the 2026-07-02 supersession
contradiction is the evidence).

- Promotion writes provenance metadata (source stash entry, review
  verdict, date) onto the resulting node.
- **Receipt:** one real stashed finding promoted with provenance
  visible on the node.

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

9.3.0 shipped with `PersonalMemory.query()` 100% broken (hit@1 0/18)
and no gate caught it — all local testing ran main, not the artifact.
Golden queries already exist (`docs/specs/lessons-corpus-rag/golden_queries.json`;
the memory-recall-eval spec has the harness).

- Wire a recall smoke-eval against the BUILT artifact (clean venv,
  isolated `$HOME`) into release-prep — pass/fail on hit@3 above a
  floor, not a benchmark.
- **Receipt:** the gate run visible in the next release's prep log.

---

## Deferred (noted, not tasked)

- **Subsystem consolidation review** — `attune.memory` is 42 modules
  / ~11.5k LOC with overlapping stores (`simple_storage`,
  `file_stash`, `file_session`, `summary_index`, …) while live value
  concentrates in a few hooks. Run the subsystem-value-gate review
  only AFTER T1–T2 settle occupancy — consolidating before the
  occupant moves in repeats the build-ahead-of-use pattern.
