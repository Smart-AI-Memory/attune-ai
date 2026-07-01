# Spec: Memory NodeType Friction Log

> Dogfood the 4 curated `NodeType` members shipped in PR #1207
> (`USER_CONTEXT`, `FEEDBACK`, `PROJECT_CONTEXT`, `REFERENCE`) across
> real sessions, then decide whether the taxonomy/field reinterpretation
> holds up or needs adjustment.

**Status:** requirements drafted
**Owner:** Patrick + agent
**Related:**

- [`project_memory_subsystem_motivation`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_memory_subsystem_motivation.md)
  — the tier-3 research/build history; names this friction log as
  open item #2, "hasn't started yet in earnest"
- `src/attune/memory/nodes.py` — the 4 new `NodeType` members
- `src/attune/memory/graph.py::add_finding` — where curated memory
  gets modeled as `Node`/`Edge`
- PR [#1207](https://github.com/Smart-AI-Memory/attune-ai/pull/1207)
  — the shipping commit (structured one-shot, not a `/spec`)

---

## Problem

PR #1207 mapped the harness auto-memory taxonomy (`user` / `feedback`
/ `project` / `reference`) onto 4 new `MemoryGraph` `NodeType`
members, reinterpreting `severity`/`status` (fields originally shaped
for workflow findings — BUG/VULNERABILITY/PATTERN) to fit curated
memory instead. Tests pass and coverage is high, but **zero real
memory has been written through this path** — the fit was validated
against a symbol-drift experiment (T2a) and unit tests, not against
the actual shape of curated memory as it accumulates over real
sessions. We don't know yet whether:

- the 4-type taxonomy is the right granularity (too coarse? missing a
  type real memory needs?)
- the `severity`/`status` reinterpretation reads naturally when
  someone (agent or Patrick) inspects a populated graph
- `RELATED_TO` edges are sufficient for the `[[link]]` cross-reference
  pattern memory files already use

## Goal

Use the 4 `NodeType`s for real curated-memory writes across a run of
actual sessions (not synthetic tests), observe where the fit is
awkward, and log each friction point as it's found — then render a
verdict.

## Requirements

- **R1 — Real usage, not synthetic.** Friction entries must come from
  actual `MemoryGraph.add_finding()` calls made during real session
  work (this project or others), not from writing test fixtures to
  exercise the new types.
- **R2 — Log friction as it happens.** Each friction point gets a
  dated entry in `decisions.md`: what was being recorded, which
  `NodeType`/field didn't fit cleanly, and the workaround used (if
  any). Capture the good fits too, briefly — absence of friction is
  itself a data point, not just silence.
- **R3 — No schema change without evidence.** Don't extend the
  taxonomy or add fields speculatively while this log is open;
  `project_memory_subsystem_motivation.md` already names this
  discipline ("not built speculatively alongside this").
- **R4 — Graduation threshold.** After roughly 5-10 real sessions'
  worth of curated-memory writes touching these types (whichever
  comes first, session count or a natural pause point), write a
  closing verdict in `decisions.md`: keep-as-is / adjust fields /
  extend taxonomy — citing the specific friction entries that drove
  the call.
- **R5 — Cheap to run.** No new tooling or instrumentation required
  to start — this is an observational log kept by hand during normal
  session work, not a code deliverable in itself. If friction reveals
  a need for lightweight tracking (e.g. a counter), that becomes its
  own follow-up, not a prerequisite.

## Non-goals

- Not building the two-memory-system unification (harness auto-memory
  vs. attune.memory) — that's the bigger, separate open question
  named in `project_memory_subsystem_motivation.md`.
- Not adding Redis/AMS — deliberately deferred per that same memory
  until real friction or corpus size gives a trigger.
- Not a code change in v1 — any schema adjustment is a *possible
  outcome* of R4, not scoped work here.

## Done when

- `decisions.md` has a closing verdict entry citing concrete friction
  (or lack thereof) from real sessions, with a keep/adjust/extend
  recommendation.
- If the verdict is "adjust" or "extend," a follow-up spec or task is
  opened for the actual code change (out of scope here).
