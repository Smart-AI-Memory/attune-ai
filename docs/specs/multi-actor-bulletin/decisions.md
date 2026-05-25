# Decisions: Multi-Actor Bulletin Board
**Status:** complete
Resolutions on open questions, captured as Patrick reviewed the
[`requirements.md`](requirements.md) draft.

---

## 2026-05-17 — Open questions resolved

### Heartbeat cadence — 30s beat / 90s GC, **emitted by the wrapper process**

**Decision:** keep 30s heartbeat / 90s GC. **Decouple heartbeat
emission from workflow progress.** The actor's wrapper process
(dashboard `RunnerService`, CLI dispatcher, MCP handler, etc.)
runs an independent `asyncio` task that ticks every 30s
regardless of what the workflow is doing internally.

**Why:** Patrick's only concern on the cadence was truncation of
healthy long-running work — some SDK calls can block >60s
inside `claude_agent_sdk.query()` without progress signals
reaching the wrapper. Decoupling solves that: as long as the
wrapper process is alive, heartbeats fire. A GC'd entry then
truly indicates a dead wrapper (crash, machine sleep, terminal
closed), not slow work.

**How to apply:**

- Heartbeat task lives in the wrapper, started before the
  workflow's `execute()` call and cancelled on terminal status.
- Wrapper failures (uncaught exceptions, OS-level kills) stop
  the task naturally — `asyncio.CancelledError` or process exit.
- Workflow loop itself does not emit heartbeats. Workflows
  don't need to know the bulletin exists.

### Actor ID stability — best-judgment scheme per actor kind

**Decision:** Patrick deferred. Going with:

| Actor kind | Actor ID format |
|---|---|
| Claude Code session | `cc-session-${CLAUDE_CODE_SESSION_ID}` |
| Dashboard process | `dashboard-${hostname}-${port}-${start_iso_date}` |
| Raw CLI (one-shot) | `cli-${hostname}-${pid}-${start_iso_date}` |
| ATTUNE_REC auto-trigger | inherits parent actor ID + `triggered_by_run_id` field |
| Scheduled task | `scheduled-${task_id}` |

**Why:** the design constraint is "stable enough to be useful
on a single host within a single working day, with no extra
state to track." Hostname + PID + date for CLIs gives that
without a persistent ID file. Claude Code sessions get a
genuinely stable ID for free. Scheduled tasks already have a
durable identifier.

**How to apply:** centralize the derivation in
`attune.bulletin.actor.derive_actor_id(kind)` so we have one
place to change if the scheme proves wrong.

### Privacy / multi-user — file permissions for v1

**Decision:** rely on `0700` directory perms on
`~/.attune/bulletin/` and `0600` on individual files. No
per-workflow or per-scope opt-out tag in v1.

**Why:** Patrick: *"for now I'm inclined to rely on file
permissions but am open to pushback."* I don't have pushback —
file perms match how the rest of `~/.attune/` already works
(telemetry, memory, ops runs), and the bulletin is per-user
either way. The privacy concern only escalates if the bulletin
ever becomes a shared store (Phase 3 Redis Streams with
cross-host access). Revisit then.

**How to apply:**

- On first write to `~/.attune/bulletin/`, set directory to
  `0700` and individual files to `0600`. Match the pattern
  already used in `attune.memory` modules.
- Phase 3 Redis backend will need its own privacy story
  (auth, ACLs, namespacing per user); flag at that phase.

### Rule authoring — YAML for v1

**Decision:** rules live in `~/.attune/bulletin/rules.yaml`,
loaded at runtime. No Python rules in v1.

**Why:** Patrick agreed. YAML is the right authoring surface
for v1 — declarative, easy to share, harder to weaponize than
Python. If users hit the YAML ceiling we'll know via specific
unmet asks, and a Python escape hatch can be added incrementally.

**How to apply:**

- `attune.bulletin.rules.load(path)` returns a list of `Rule`
  objects parsed from YAML.
- Each rule has `id`, `block_if` (a small DSL expression), and
  `message` (a template with `{other_actor}`, `{other_workflow}`,
  etc. substitutions).
- The DSL surface is intentionally minimal — a fixed set of
  predicates (`any_actor_running_on_parent_or_self`,
  `count_running_expensive`, `account_budget_remaining_usd`)
  rather than arbitrary expressions. Predicates compose with
  `and`/`or`/`not`. Adding a new predicate is a Python change,
  not a config change.
