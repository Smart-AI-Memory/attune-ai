# Spec: Multi-Actor Bulletin Board

> Shared, real-time view of which workflows are running and who
> started them — so multiple Claude Code sessions can collaborate
> as a team rather than colliding as solos.
**Status:** approved
**Created:** 2026-05-17
**Owner:** TBD
**Related:**
- [`bulletin_and_pipeline_learner` memory](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_bulletin_and_pipeline_learner.md) — high-level synthesis
- Future spec: `bulletin-curator` (executive-summary agent — separate scope)
- Future spec: `pipeline-learner` (mines bulletin history for canonicalization candidates)

---

## Problem statement

The current runner is **single-actor aware**. `RunnerService._runs`
holds the dashboard's in-flight runs in one Python process; CLI
invocations, `ATTUNE_REC` auto-triggers, scheduled tasks, and
other Claude Code sessions are invisible to each other. Three
concrete consequences observed today (2026-05-17):

1. **Cross-actor overlap can't be diagnosed.** A `bug-predict`
   run on `demo_eval_vuln.py` overlapped with my queue's
   `health-check`. The overlap *looked* like a busy-lock race
   for ~30 minutes of investigation. Forensic on the persisted
   JSON revealed it was a different actor (likely the
   ATTUNE_REC code-review→bug-predict flow), not a race. A
   bulletin would have shown the second actor immediately.

2. **No sequencing rules can be enforced.** "Don't run two
   large-scope workflows simultaneously" or "refuse new starts
   when the account API budget is below threshold" both require
   observability the runner doesn't have.

3. **Multi-session collaboration is solo work in parallel.**
   Patrick reports juggling multiple Claude Code sessions as a
   normal pattern and wants it to feel like teamwork — but
   each session is blind to the others. The shape today is
   "ensemble of solos", not a coordinated team.

The earlier whiteboard concepts (bulletin board + pipeline
learner) presupposed this coordination substrate. This spec
delivers it.

---

## Goals

1. Every actor (dashboard, CLI, ATTUNE_REC trigger, scheduled
   task, other Claude Code session) writes its in-flight run
   state to a shared store every other actor can read.
2. The dashboard renders a "Now running" panel showing all
   in-flight runs across actors, with `actor_id`, workflow,
   scope, started_at, and current status.
3. A small **sequencing rules** module reads the bulletin and
   can block a new start with a clear reason (e.g. *"another
   actor is already running security-audit on a parent of this
   scope"*).
4. Pluggable backend: file-based by default, Redis-Streams as
   an opt-in upgrade via `attune-redis`.

## Non-goals (out of scope for this spec)

- **Curator agent / executive summary.** Lives in a separate
  `bulletin-curator` spec. This spec gives the curator a data
  surface to read from.
- **Pipeline-learner mining workflow.** Reads the bulletin's
  history; defined separately.
- **AMS / semantic-search backed bulletin.** v3 idea; not v1
  or v2.
- **Cross-host coordination.** Same-host multi-actor is the
  v1/v2 scope. Distributed teams across machines is a future
  problem (and the Redis-Streams backend naturally extends
  there).
- **Replacement of `RunnerService._runs`.** That stays as the
  dashboard's in-memory cache. The bulletin is additive — every
  actor writes its events; the dashboard's view layer reads from
  the bulletin alongside its own cache.

---

## Design

### Data model

A bulletin entry is the minimum needed to answer "who is doing
what right now":

```json
{
  "actor_id": "claude-code-session-<uuid>",
  "actor_kind": "claude-code-session | cli | dashboard | scheduled | attune-rec",
  "workflow": "code-review",
  "scope": "src/attune/ops/",
  "run_id": "5e506b3386ab",
  "started_at": "2026-05-17T15:08:07.129158+00:00",
  "current_status": "running | completed | failed | cancelled",
  "last_heartbeat": "2026-05-17T15:09:42.000000+00:00",
  "hostname": "patrick-mbp"
}
```

Each actor writes a **start record** on workflow start, a
**heartbeat** every 30s while running, and a **finish record**
on terminal status. Stale entries (no heartbeat for > 90s) are
GC'd by readers; readers don't trust the writer to clean up
after a crash.

### Backends

```
                           +-------------------+
                           |  BulletinProtocol |
                           +-------------------+
                                    ^
                  -------------------+-------------------
                  |                                     |
       +------------------------+         +-------------------------+
       |  FileBulletinBackend   |         |  RedisStreamBulletin    |
       |  ~/.attune/bulletin/   |         |  XADD attune:bulletin   |
       |    active.jsonl        |         |  XREAD consumer groups  |
       |    archive/YYYY-MM-DD/ |         |  via attune-redis       |
       +------------------------+         +-------------------------+
                v1 default                   v2, opt-in via extra
```

**v1 (file):** `~/.attune/bulletin/active.jsonl` — append-only.
Readers tail + dedupe by `run_id` + drop stale heartbeats.
Daily rotation into `archive/YYYY-MM-DD/` keeps the hot file
small. Concurrent write safety via fcntl advisory lock around
each append. Zero new dependencies.

**v2 (Redis Streams):** uses the existing `attune-redis` plugin
+ `agent-memory-client` machinery. Stream name `attune:bulletin`.
Consumer groups: `dashboard`, `cli`, `curator`. Cross-host
ready as a natural side effect. Opt-in via
`pip install 'attune-ai[bulletin-redis]'` (new extra) or by
having `attune-redis` already installed.

**v3 (AMS-backed history, future):** archive entries flow into
Redis Agent Memory Server for the pipeline-learner's
"find runs similar to this one" query.

### Sequencing rules

A small policy module (`attune.bulletin.rules`) loads a rule
set from `~/.attune/bulletin/rules.yaml` and provides
`can_start(workflow, scope) -> (bool, reason)`:

```yaml
# Example rules
rules:
  - id: no-parent-scope-overlap
    block_if: any_actor_running_on_parent_or_self(scope)
    message: "{other_actor} is already running {other_workflow} on {parent_scope}"

  - id: global-large-scope-throttle
    block_if: >
      workflow.is_expensive and
      count_running_expensive() >= 1
    message: "another expensive workflow is in flight; queue and try again in a minute"

  - id: api-budget-floor
    block_if: account_budget_remaining_usd() < 1.00
    message: "Anthropic API budget below $1.00 floor; raise the cap or wait"
```

Rules are advisory (the dashboard and CLI consult before
starting), not enforced at the SDK boundary. A future spec
could make them hard.

### Wiring per actor

| Actor | Start writes | Heartbeat | Finish writes |
|---|---|---|---|
| **Dashboard `RunnerService.start`** | ✓ | from existing SSE tick | ✓ |
| **CLI `attune workflow run`** | ✓ | from workflow loop | ✓ |
| **ATTUNE_REC auto-trigger** | ✓ (inherited via dashboard) | inherited | inherited |
| **Scheduled task** | ✓ | from task wrapper | ✓ |
| **Other Claude Code session via MCP `code_review` etc.** | ✓ (new) | from MCP handler | ✓ (new) |

The MCP-handler wiring is the only one that's genuinely new
code-path work. The others are 5–10 lines of "write your record
where you already log to disk".

### Dashboard surface

The Workflows tab gains a "Now running across actors" strip
above the workflow table when the bulletin shows any non-self
in-flight runs. Each entry is a chip with `actor_id` (short
form), workflow, scope, and a tooltip showing started_at and
last_heartbeat. Stale entries (heartbeat older than 90s but
not yet GC'd) render as muted with a "stale" marker.

The existing recent-runs strip per workflow stays unchanged.

---

## Acceptance criteria

1. **Cross-actor visibility:** start a workflow from a CLI in
   one terminal, open the dashboard in another browser. The
   dashboard shows the CLI's run in the "Now running" strip
   within 5 seconds.
2. **Sequencing rule fires:** with the example rule
   `no-parent-scope-overlap` enabled, start `security-audit`
   on `src/attune/` from actor A. From actor B, attempt
   `code-review` on `src/attune/security/`. Actor B receives
   a clean rejection with the rule's message.
3. **Stale GC:** kill actor A's process during a run.
   90 seconds later, the bulletin no longer shows that run.
   No other actor needed to clean it up — readers GC.
4. **Backend swap is invisible:** flipping the config from
   `file` to `redis-stream` requires no code changes in
   workflows or the dashboard.
5. **Reasonable failure modes:** if `~/.attune/bulletin/` is
   unwritable, the workflow still runs (bulletin is advisory,
   not gating). Logged at WARN.
6. **No regression:** existing single-actor flows behave
   identically. The bulletin is a new surface; it doesn't
   replace `RunnerService._runs`.

---

## Tasks (phased)

### Phase 1 — File backend, dashboard visibility (~6h)

| # | Task | Effort |
|---|------|--------|
| 1 | `BulletinProtocol` + `FileBulletinBackend` (append, read, GC) | 2h |
| 2 | Actor-ID derivation (Claude Code session env, CLI auto-id, dashboard host) | 30m |
| 3 | Wire write-on-start/heartbeat/finish into `RunnerService` and CLI dispatcher | 1h |
| 4 | "Now running across actors" strip in Workflows tab template + SSE refresh | 1h |
| 5 | Unit tests + integration test with two concurrent writers | 1.5h |

### Phase 2 — Sequencing rules (~3h)

| # | Task | Effort |
|---|------|--------|
| 6 | `attune.bulletin.rules` module + YAML loader | 1h |
| 7 | `can_start()` consultation in `RunnerService.start` and CLI | 30m |
| 8 | Three default rules (parent-scope-overlap, expensive-throttle, api-budget-floor) | 1h |
| 9 | Rule tests | 30m |

### Phase 3 — Redis Streams backend (~4h, opt-in)

| # | Task | Effort |
|---|------|--------|
| 10 | `RedisStreamBulletinBackend` using `agent-memory-client` or direct redis-py | 2h |
| 11 | Backend selection via config (`~/.attune/bulletin/config.yaml`) | 30m |
| 12 | Cross-host test scenario (two machines) | 1h |
| 13 | Docs / migration guide for opt-in | 30m |

### Phase 4 — MCP handler wiring (~2h)

| # | Task | Effort |
|---|------|--------|
| 14 | Wrap each MCP workflow tool to write bulletin entries | 1.5h |
| 15 | Integration test: two Claude Code sessions see each other's MCP-triggered work | 30m |

**Total estimated:** 15h. v1 ships in Phase 1+2 (~9h); Phases 3
and 4 are independent follow-ups.

---

## Open questions

All four initial open questions resolved 2026-05-17 — see
[`decisions.md`](decisions.md). The load-bearing resolution is
the heartbeat: emitted by the wrapper process (not the workflow
loop), which eliminates the truncation risk and lets 90s GC stay
conservative without killing healthy long-running work.

Remaining unknowns surface during implementation, captured in
`decisions.md` as they're resolved.
