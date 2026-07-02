# Spec: Curated-Memory Productionization

> Turn the 2026-07-02 prototype (git-backed curated graph -> Redis
> hydration -> microsecond recall -> widget rendering) into wired,
> durable product surfaces. Drafted FROM prototype evidence, per
> Patrick's prototype-first decision — every requirement below traces
> to a measured receipt, not speculation.

**Status:** requirements approved (Patrick, 2026-07-02)
**Owner:** Patrick + agent
**Related:**

- `docs/specs/memory-nodetype-friction-log/` — the R4 dogfood log this
  spec's evidence comes from (incl. the 2026-07-02 first review pass:
  6 keep / 1 sharper / 0 wrong)
- `silversurfer562/attune-agent-memory` (private) — the memory repo:
  `curated_graph.json` (durable home), `hydrate.py`, `functions.lua`
- PR [#1212](https://github.com/Smart-AI-Memory/attune-ai/pull/1212)
  — `MemoryGraph.curated()` durable home + `find_similar` containment
  scoring
- `.claude/rules/attune/communication-grammar.md` — the construct
  family primitive #6 extends

---

## Problem

The architecture Patrick articulated 2026-07-02 (git long-term ->
Redis short-term -> microsecond recall -> widget rendering) exists as
a receipted prototype, but nothing is *wired*: hydration is a manual
script run, recall is a manual FCALL, the digest renders only when the
agent hand-drives the form pipeline, and nothing pulls the memory repo
before hydrating on a second machine. Measured prototype receipts:

- `FCALL recall_digest` median **86us**; `FT.SEARCH` median **181us**;
  first FCALL ~3.6ms cold (wants a warming call).
- Full review loop worked end-to-end through production code
  (`form_from_dict` -> `form_to_widget_html` -> submit ->
  `collect_form_response` -> `update_node` -> re-hydrate -> git push).
- Friction found: `hydrate.py` assumes an interpreter with `redis`
  installed (worktree venv lacked it — the hook must pin one); the
  digest currently renders through the `progress` construct, where
  memory facts read as strikethrough "done tasks" (wrong semantics);
  the Stop-hook auto-stash captured a superseded hypothesis alongside
  its correction (promotion needs curation, not bulk copy).

## Goal

A fresh session bootstraps useful recall with zero manual steps:
SessionStart pulls the memory repo, hydrates Redis, warms the
function, and the agent can query and render recall as a
purpose-built widget. The convergence test from the transition
protocol: a fresh session can orient from curated recall alone.

## Requirements

- **R1 — SessionStart hydration hook.** A registered hook that:
  (a) `git pull`s the memory repo (multi-machine sync; skip gracefully
  offline), (b) runs hydration into `attune:memory:*` +
  `idx:attune_memory`, (c) issues one warming `FCALL` (~3.6ms cold vs
  86us warm). Must pin an interpreter that has `redis` (evidence: the
  worktree-venv `ModuleNotFoundError`). Degrade silently to no-op when
  Redis is down — never block session start.
- **R2 — Targeted recall procedures.** Beyond `recall_digest`: at
  least a topic/tag-filtered search and a single-node fetch as Redis
  Functions or parameterized `FT.SEARCH` calls, so recall cost stays
  microsecond-class rather than falling back to file reads. Ship only
  procedures with a demonstrated consumer (R3-style discipline — no
  speculative endpoints).
- **R3 — Recall-digest widget primitive (grammar #6).** A construct
  whose semantics are "here is what memory carries," not task
  progress. Evidence: rendering memory facts through the `progress`
  construct strikes them through as done tasks. Follows the
  communication-grammar extension recipe (additive `QuestionType` or
  composition; `AskUserQuestion` fallback; dogfooded live round-trip).
- **R4 — Stash -> curated promotion path.** A deliberate, reviewable
  step that proposes auto-stashed findings for promotion into the
  curated graph (agent proposes, Patrick's review verdict pattern
  applies). Evidence the path must be curatorial: the 2026-07-02
  auto-stash contradiction (superseded hypothesis stashed next to its
  correction). Bulk import is explicitly wrong.
- **R5 — Receipts over registration.** Each requirement lands with a
  non-mocked round-trip receipt (registered != working): R1 proves a
  fresh session hydrated + warmed by reading the hook's own log; R3
  proves a live widget submit; R4 proves one real promotion with
  provenance metadata.

## Non-goals

- Not migrating harness `~/.claude/.../memory/*.md` files wholesale —
  the transition protocol is deficiency-driven routing, not bulk
  copy (proposed 2026-07-02, discussion open).
- Not multi-user / team memory — single-operator loop first.
- Not AMS index integration — we namespace `attune:memory:*` beside
  AMS's `memory_records`; merging them is a separate decision.
- Not retiring the friction log — R4 evidence keeps accruing there.

## Done when

- A fresh session on this machine reaches warm recall with zero manual
  steps, receipted by the hook log (R1).
- One targeted recall procedure and the recall-digest widget are used
  live in a real session (R2, R3).
- At least one stashed finding has been promoted through the R4 path
  with review provenance on the resulting node.
- Frictions found during the build are logged in the friction-log
  spec, and this spec's decisions.md records scope changes with
  evidence.
