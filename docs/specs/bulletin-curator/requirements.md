# Spec: Bulletin Curator

> An Opus-tier agent that reads the bulletin + adjacent
> surfaces, ranks what needs attention, produces an executive
> summary, and dispatches focused follow-ups via
> `AskUserQuestion`. Fires on-demand when Patrick opens the
> bulletin — not continuously.
**Status:** complete (Phases 2–3 shipped #631–#635; Task 4.1 optional manual verify)
**Created:** 2026-05-17
**Owner:** TBD
**Related:**
- [`multi-actor-bulletin`](../multi-actor-bulletin/requirements.md) — provides the bulletin data surface this agent reads
- [`pipeline-learner`](../pipeline-learner/requirements.md) — sibling consumer of the bulletin's archived history
- [`project_bulletin_and_pipeline_learner.md`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_bulletin_and_pipeline_learner.md) — high-level synthesis

---

## Problem statement

Today the dashboard's surfaces are **passive**: `/sessions`,
`/specs`, `/workflows`, completion-candidates, discovery-sweep
findings, telemetry. Each shows what's there. None of them
**rank** items, **synthesize across them**, or **pull Patrick
into a focused decision**. The result is that important things
sit in plain sight without surfacing — the user has to know to
go looking.

What's missing is a **briefing layer** that distills the
underlying state into "here are the top N things that need your
attention right now, here's why each ranks where it does, and
here's the one question that would unblock the next step."

The bulletin board (separate spec) provides one piece of data
the curator needs: who-is-running-what across actors. The
curator is the agent that synthesizes *across* the bulletin and
the other surfaces to produce ranked, actionable output.

---

## Goals

1. **On-demand executive summary** — when Patrick opens the
   bulletin (or hits a `/curator` route, or invokes
   `attune curator`), an Opus-tier agent reads the available
   sources and returns a fresh 2–3 paragraph summary of what's
   notable.
2. **Ranked attention list** — the same call returns a
   prioritized list of N items with a short rationale per item
   (severity, age, blocking-something-else, etc.).
3. **Focused follow-ups** — for items that need a decision
   (approve / dismiss / dig deeper), the curator emits an
   `AskUserQuestion`-shaped payload that the dashboard renders
   as an actionable card. Patrick's choice routes back into the
   right next workflow or status update.
4. **No hallucinated facts** — every claim in the summary
   traces to a specific source row (run id, spec slug, finding
   id) that's clickable in the rendered output.

## Non-goals

- **Replacing the underlying surfaces.** `/sessions`, `/specs`,
  etc. stay. The curator distills; it doesn't displace.
- **Always-on agent.** No continuous polling, no background
  daemon. Fire on-demand, cache for ~5 minutes, refresh on
  next open.
- **Writing status fields.** The curator can suggest
  transitions (e.g. "this spec looks ready to mark complete")
  but never writes to the status field directly. Patrick's
  authority is preserved per the existing
  completion-candidates discipline.
- **Cross-host / multi-tenant.** Same-host, single-user v1.
- **A separate "agent personality"** beyond a clear system
  prompt. The curator is a Claude Opus invocation with a
  curation role, not a new persona to maintain.

---

## Design

### Sources read

| Source | What | Read via |
|---|---|---|
| Bulletin (now-running) | Active runs across actors | `attune.bulletin.read_active()` |
| Bulletin (archive) | Recent terminal-status entries | `attune.bulletin.read_archive(since=...)` |
| `/specs` data | Open / draft / approved / complete specs + completion-candidates | `attune.ops.data.list_specs()` |
| Discovery-sweep findings | Queue / questions / rejected buckets | `attune.workflows.discovery_sweep.read_buckets()` |
| Telemetry | Recent cost spikes, error spikes, p95 anomalies | `attune.telemetry` summary functions |
| ATTUNE_REC | Pending recommendation cards on recent runs | `attune.ops.recommendations.pending()` |
| `git status` + recent commits | Uncommitted work, branch state | `subprocess.run(["git", ...])` |

### Curator agent invocation

```python
# Pseudocode — actual interface TBD
from attune.curator import run_curator

result = await run_curator(
    project_root=Path("."),
    max_items=5,
    cache_ttl_seconds=300,
)
# result.summary: str (2-3 paragraphs)
# result.items: list[CuratorItem]
# result.questions: list[AskUserQuestionPayload]
# result.sources_consulted: list[str]
# result.cost_usd: float
```

The invocation:

1. Reads all sources in parallel (most are local file/IO; fast).
2. Builds a compact context block per source (bullet summaries,
   not raw dumps — controls token spend).
3. Invokes `claude_agent_sdk.query()` with an Opus model and a
   curator system prompt.
4. Forces structured output via `output_format` (the same
   `WORKFLOW_OUTPUT_SCHEMA` pattern used by code-review /
   security-audit, adapted for curator items).
5. Caches the result for 5 minutes keyed on the source-state
   hash so refresh-spam doesn't re-spend budget.

### Curator item shape

```json
{
  "id": "spec-X-completion-candidate",
  "title": "deprecated-module-retirement looks ready to mark complete",
  "severity": "info | nudge | warn | block",
  "rationale": "all 3 tasks marked done; PR #209 merged; no open issues citing this slug; edit-age 6 days",
  "sources": ["docs/specs/deprecated-module-retirement/tasks.md", "PR #209"],
  "suggested_action": {
    "kind": "ask | open | run | dismiss",
    "payload": "..."
  }
}
```

`suggested_action.kind`:

- `ask` — emit an `AskUserQuestion` payload (e.g. *"Mark this
  spec complete? \[Yes / Not yet / Dismiss for 14 days\]"*)
- `open` — link to the deep-dive surface (`/specs/<slug>`,
  `/runs/<id>/view`, etc.)
- `run` — propose a workflow run with pre-filled scope
- `dismiss` — suppress this item for N days

### Dashboard surface

New `/curator` route. Renders the executive summary at the top,
ranked items as cards below, and surfaces any
`AskUserQuestion`-shaped payloads as inline actionable forms.
A "Refresh" button forces a re-curate, bypassing the 5-min
cache. The bulletin's "Now running across actors" strip
(from the multi-actor-bulletin spec) gets a "View briefing"
link that jumps to `/curator`.

CLI equivalent: `attune curator` prints the summary +
top items + any questions to stdout. Useful for terminal-first
workflows where Patrick isn't in the browser.

### Tier + cost model

- Model: Opus (current generation — currently `claude-opus-4-7`).
  Synthesis quality matters; this is the highest-leverage
  invocation in the dashboard, not a hot path.
- Cost cap per call: $0.50 (well above expected; controls
  catastrophic prompt-bloat).
- Cache TTL: 5 min, keyed on source-state hash. A no-change
  refresh is free.
- Expected per-call cost: $0.05–$0.15 based on similar
  Opus synthesis tasks. Patrick's daily curator usage at this
  cost = trivial.

---

## Acceptance criteria

1. **Honest synthesis** — fabricate a fixture state with 3
   known items (a stale spec, a queued sweep finding, a failed
   run with ATTUNE_REC). Run the curator. The returned items
   include all three with correct titles and rationales drawn
   from the source data, no invented entries.
2. **Actionable follow-ups** — at least one item in the
   fixture surfaces an `AskUserQuestion` payload that the
   dashboard renders correctly as a clickable card.
3. **Source clickability** — every claim in the summary
   resolves to at least one source row that produces a
   valid clickable link in the rendered output.
4. **Cache works** — two refreshes within 5 min without
   source-state change hit the cache (cost: $0). Source-state
   change invalidates.
5. **CLI equivalence** — `attune curator` produces the same
   summary + items + questions as the web `/curator`.
6. **Honest empty state** — when no items rank above the
   noise threshold, the curator says so cleanly ("nothing
   pressing right now") rather than padding with low-value
   filler.

---

## Tasks (phased)

### Phase 1 — Source readers + cache scaffolding (~3h)

| # | Task | Effort |
|---|------|--------|
| 1 | `attune.curator.sources` module — one reader per source listed above | 1.5h |
| 2 | Source-state hash for cache invalidation | 30m |
| 3 | Mock fixtures for each source (used by tests) | 1h |

### Phase 2 — Agent invocation + structured output (~3h)

| # | Task | Effort |
|---|------|--------|
| 4 | Curator system prompt + output schema | 1h |
| 5 | `attune.curator.run_curator()` async entry point | 1h |
| 6 | Cost cap + cache-key plumbing | 30m |
| 7 | Unit tests against fixtures (deterministic — mock the SDK) | 30m |

### Phase 3 — Dashboard `/curator` + CLI (~3h)

| # | Task | Effort |
|---|------|--------|
| 8 | `/curator` route + template (summary + cards + AskUserQuestion forms) | 1.5h |
| 9 | CLI `attune curator` subcommand | 1h |
| 10 | Bulletin → curator cross-link | 30m |

### Phase 4 — Live verification (~1h)

| # | Task | Effort |
|---|------|--------|
| 11 | Run against real attune-ai state, eyeball output, iterate prompt | 1h |

**Total estimated:** 10h. Phases 1+2 deliver the headless API;
Phase 3 makes it visible. Each phase is independently shippable.

---

## Open questions

1. **Source weighting.** Should each source carry an explicit
   weight in the ranker prompt, or trust the LLM to balance
   them? Lean: no explicit weights in v1; document the prompt's
   ranking heuristics in the system prompt and iterate based on
   what Patrick consistently down-votes.
2. **Down-vote mechanism.** When Patrick dismisses an item with
   *"this isn't actually important"*, where does that signal
   live? Per-item suppression for N days is simple. Learning
   what *kinds* of items he down-votes is the v2 idea (probably
   a small classifier or a preference file the curator reads as
   another source).
3. **Curator-of-the-curator.** Patrick has multiple projects.
   Does each project get its own curator output, or is there a
   meta-curator across projects? Lean: per-project for v1; the
   bulletin board's actor-id already gives us
   "project = working directory" as a natural boundary.
