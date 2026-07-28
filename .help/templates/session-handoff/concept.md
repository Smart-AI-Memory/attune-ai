---
type: concept
name: session-handoff-concept
feature: session-handoff
depth: concept
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Overview

Session-handoff lets one agent session hand a branch's in-flight work
to another — including a session run by a *different provider* — with
the claims and the facts kept separate. `handoff_create` assembles a
packet for the current branch: the git-derived fields (branch, head
SHA, merge base, changed files) are read from git at call time and
recorded as **verified**; the caller's prose (goal, acceptance
criteria, current state, next action) is recorded verbatim as
**asserted**. `handoff_resume` reads the packet back and re-checks
every verified field against the current tree, reporting drift as
warnings.

The receiving side gets a **report, not a go signal**: resume never
checks out branches, never writes, never runs tests. It tells the
next session what was claimed, what is still true, and what moved —
the session decides what to do with that.

Both operations are exposed as MCP tools on the attune server, so any
MCP client — Claude Code, Codex, Antigravity — can create or resume a
packet. There is deliberately no CLI wrapper yet (MCP-only at ship;
a CLI waits for a usage signal).

## Concepts

### The packet: verified frontmatter, asserted body

A packet is one markdown file per branch at
`docs/handoffs/<branch-slug>.md` (slug = branch name with `/` as
`-`). YAML frontmatter carries the machine-verified fields —
`branch`, `head_sha`, `merge_base`, `changed_files`, `created_at`,
`provider`. The markdown body holds the asserted prose sections. This
keeps the file human-readable while making verification mechanical:
resume re-derives the frontmatter facts from git and surfaces the
body untouched under `asserted`.

### Verification rows never claim what was not run

The packet's verification table records claims and probes. A row's
`result` defaults to **"not run"** — a caller cannot fabricate a
passing probe through the create surface. The receiving session
re-runs probes itself and updates its own record.

### The drift report

Resume compares the packet against the live tree and emits report-only
warning codes — never blocking, never auto-fixed:

- `branch_missing` — the packet's branch is absent from the repo
- `head_moved` — current HEAD differs from the packet's `head_sha`
- `files_diverged` — the actual diff set differs from
  `changed_files`
- `packet_stale_days` — the packet is older than 7 days
- `dirty_tree` — uncommitted changes are present at resume time

Report keys come in authority order: `verified`, `warnings`,
`asserted`, `memory`.

### Caps and overwrite semantics

Packets are terse by contract: 2048 bytes per field, 8192 bytes per
rendered packet. Oversize input is rejected with
`{ok: false, reason: "field_over_cap", field, limit}` — never
silently truncated. Re-creating a packet for the same branch
overwrites in place (one packet per branch); the previous packet's
`created_at` is preserved as `superseded_at` so staleness stays
honest.

### Memory linkage, degrade-silent but stated

Create stashes a topic-`handoff` pointer through the session-stash
helpers (the same sanitized path `session_memory_capture` uses);
resume recalls pointers for the slug. When no memory backend is
reachable, the report says so instead of erroring or omitting:
`memory: {status: "skipped", reason: "no_backend"}`. An empty recall
is honestly `{status: "recalled", count: 0}` — a skip and a miss are
different facts.
