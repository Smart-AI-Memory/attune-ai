# Three-Ring Memory Audit

**Original audit:** 2026-07-02 (in-session artifact `memory-three-rings`)
**Regenerated:** 2026-07-02 — the original artifact never persisted
(not in `~/.attune/memory/curated_graph.json` (9 nodes checked), not on
disk under `~/.attune/`, not in local Redis `idx:attune_memory`). This
document reconstructs it from receipts and re-verifies every finding
against state as of 2026-07-02 (post-9.4.0).

**Provenance of the reconstruction:** the release_state memory file
(9.4.0 entry), `~/.attune/next_session_starter.md` item #4, curated
node `feedback_20260702115027_05962918a6ef` ("three-ring reframe"),
and fresh verification commands run 2026-07-02 (cited inline below).

**Meta-lesson from the loss itself:** an audit artifact that lives only
in conversation output is not durable. Durable = committed to a git
tree (this file) or written to the curated graph. This is the same
"registered != working" family — "presented to the user" != "persisted."

---

## The three rings

| Ring | System | Home | Regime |
|------|--------|------|--------|
| 1 | Harness auto-memory | `~/.claude/projects/<cwd>/memory/` + `~/.claude/memory/` | File-per-fact, `MEMORY.md` index, `memory_lint.py` schema |
| 2 | Attune curated graph + PersonalMemory | `~/.attune/memory/` (git repo `silversurfer562/attune-agent-memory`) + MCP `personal_memory_*` tools | Curated graph: human-reviewed, 30-day test (D6). PersonalMemory: capture/recall via attune-rag |
| 3 | Redis short-term layer | `attune:memory:*` keys + `idx:attune_memory`, hydrated from ring 2 at SessionStart | TTL-friendly operational recall; `FCALL recall_digest` / `FT.SEARCH` |

The D6 two-layer protocol (ratified 2026-07-02, see
[decisions.md](decisions.md)) governs the ring-2/ring-3 split: curated
graph = durable-only; operational handoff (starter file today, Redis
TTL'd records as evolution path) = short-term.

---

## Per-ring findings

### Ring 1 — harness auto-memory: WORKING, corpus-hygiene debt noted

- Populated and load-bearing (the index loads every session; the
  starter-reconciler and recall hooks fire against it).
- Known debt (from the 2026-07-01 curated-memory eval, recorded in
  `project_curated_memory_eval.md`): the 78-file per-project corpus
  carried 134 schema/link violations, and `memory_lint.py`'s bare
  default silently lints only the GLOBAL dir, not the per-project one.
  Tracked there, not re-litigated here.

### Ring 2 — curated graph + PersonalMemory

**CLOSED — the headline finding.** The shipped 9.3.0 wheel had a broken
PersonalMemory recall round-trip: capture succeeded, recall returned
"No results found" for content captured seconds earlier
(`RagPipeline.run()` result-shape misread). Caught by this audit's
clean-venv + fake-`$HOME` probe of the SHIPPED wheel — identical
commands against main worked, which is why no local testing noticed
(the #1208 fix merged 2026-07-01; v9.3.0 was tagged 2026-06-30).
Fixed in #1208, shipped as **9.4.0** (2026-07-02, merge SHA
`3b345e01b`); closure receipted the same way it was found — fresh
9.4.0 install, recall returns the captured content. Lesson recorded:
"'Fixed' != 'shipped' — audit user-facing features against the PyPI
artifact in a clean venv with an isolated `$HOME`."

**Curated graph state (verified 2026-07-02):** 9 nodes / 7 edges at
memory-repo commit `8fdcc96`; first review pass 6 keep / 1 sharper /
0 wrong. Durable home shipped in #1212
(`~/.attune/memory/curated_graph.json`, `graph.py:104`).

**OPEN — backlog (a): storage-root namespace collision.** Re-verified
2026-07-02, still real:

- `src/attune/memory/personal.py:22` —
  `_GLOBAL_ROOT = Path.home() / ".attune" / "memory"`: PersonalMemory
  writes `<topic>/<kind>.md` dirs plus `summaries_by_path.json`
  directly into that root.
- `src/attune/memory/graph.py:104` puts the curated graph in the SAME
  directory, which since R1 is a git working tree with its own
  `hydrate.py` / `functions.lua` / `.venv`.
- On-disk receipt: `~/.attune/memory/dispatch_test/decision.md` (a
  PersonalMemory topic) and `summaries_by_path.json` sit inside the
  curated repo's tree today.
- Risk: PersonalMemory topic churn pollutes the human-reviewed repo
  (or gets committed by hydration-hook automation); conversely a repo
  clean/reset could delete captured personal memories.
- Proposed fix shape: namespace PersonalMemory under its own subtree
  (e.g. `~/.attune/memory/personal/` with the curated repo ignoring
  it, or a sibling `~/.attune/personal_memory/`), with a migration
  that preserves existing topics + the summaries index, and a recall
  round-trip receipt after the move.

**OPEN — backlog (b): "which memory is which" doc.** Re-verified
2026-07-02: no such doc exists under `docs/` (grep for
harness-vs-attune memory phrasing matches only two spec requirement
files). Two disconnected memory systems were found live 2026-07-01
(harness auto-memory populated; attune MCP memory empty at the time) —
a user-facing page distinguishing harness auto-memory / attune curated
+ PersonalMemory / Redis layer, and when each fires, is still needed.
Suggested home: `docs/reference/memory-systems.md`, projected via the
single-source pipeline if it becomes a feature page.

### Ring 3 — Redis short-term layer: LIVE, first consumer pending

- **R1 convergence receipt landed:** this session (2026-07-02, fresh
  worktree session) opened with
  `[memory-hydrate] 9 active curated nodes warm in Redis` in
  SessionStart context — the remaining R1 proof named in D5. R1 is
  fully receipted; noted in [decisions.md](decisions.md) D7.
- Redis holds `attune:memory:*` + `idx:attune_memory`; warm FCALL
  measured 128us (D5).
- Honest gap (named in the original audit's self-critique): Redis has
  no real CONSUMER yet — hydration proves the write path, nothing
  reads it in anger. R3 (recall-digest render) is deliberately scoped
  as Redis's first real consumer (starter #1).

---

## Backlog re-verification summary (2026-07-02)

| Item | Status | Evidence |
|------|--------|----------|
| PersonalMemory recall broken in shipped wheel | **CLOSED** (9.4.0) | Fresh-install round-trip receipt; release_state 9.4.0 entry |
| (a) Storage-root collision `~/.attune/memory/` | **OPEN** | `personal.py:22` vs `graph.py:104`; `dispatch_test/` + `summaries_by_path.json` inside the curated repo tree |
| (b) "Which memory is which" doc | **OPEN** | No doc under `docs/`; only spec-internal mentions |
| (c) attune-author shim + deferred `.help` regen | **OPEN** | `attune-author --version` still raises `ModuleNotFoundError: No module named 'attune_author'` (pyenv 3.10.11 shim); SessionStart reports `[.help] 1 incomplete` |

Items (a)–(c) remain carried in `~/.attune/next_session_starter.md`
item #4; each should land as its own small PR (a: code + migration,
b: doc, c: local-env fix + regen — (c) is machine-local, not a PR
unless the regen produces committable `.help` content).
