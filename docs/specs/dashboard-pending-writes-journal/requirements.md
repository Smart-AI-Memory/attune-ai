# Spec: Dashboard Pending-Writes Journal

> Make ops-dashboard live-state writes (spec status setters,
> any future endpoint that mutates the working tree) durable
> across sessions. Journal each write; expose via API; surface
> in the UI; allow fresh sessions to discover inherited state.

---

## Phase 1: Requirements

**Status:** complete (Phase 1 shipped — pending_writes.py + routes + tests; PRs #469, #492; reconciled 2026-06-06)

### Problem statement

The ops dashboard mutates the working tree live — primarily
through the `PUT /api/cowork/specs/{feature}/{phase}/status`
endpoint (and equivalents in attune-gui's
`/api/cowork/specs/{feature}/{phase}/status`). These writes
are real, intentional edits made by the user via the UI, but:

- They are **never committed** by the dashboard
- When the user closes the browser tab, ends the session,
  or moves to a different worktree, those edits become
  **silent debt** sitting in `git status`
- A fresh session opening to a dirty working tree has **no
  provenance trail** — no way to know whether the edits were
  intentional, who made them, or when
- `git pull --rebase` / `git reset --hard` / `git stash drop`
  can silently destroy the edits
- Worktree-aware workflows (per existing CLAUDE.md lessons)
  compound the problem: a sibling session may overwrite the
  edits or get confused by them

**Today's evidence (2026-05-25 session, 11:00 AM):** 10 spec
status edits sitting unstaged in `attune-ai` main checkout's
working tree. The "other session" Patrick had closed earlier
had made dashboard-driven status advances on 6 specs (covering
`agent-surface-parallelism-evaluation`, `anthropic-cost-integration`,
`coverage-exclusion-policy`, `discovery-sweep-ops-integration`,
`multi-actor-bulletin`, `ops-specs-completion-candidates`).
They were invisible until the fresh session ran `git status`,
and required ad-hoc triage to decide whether to commit, stash,
or discard. Eventually committed as PR #467 — but only after
a question to Patrick, manual review, and a confirmation cycle
that wouldn't have been needed if the writes had been surfaced
proactively.

**Recurrence (2026-05-26 → 2026-05-27):** the same shape fired
again in the `vigorous-pike-a1325f` worktree. A session ended
at 22:25 on 2026-05-26 with 4 dashboard-driven spec status
flips uncommitted (`bulletin-curator/design.md`,
`bulletin-curator/tasks.md`,
`dashboard-pending-writes-journal/design.md`,
`dashboard-pending-writes-journal/requirements.md` — all
flipping `draft → approved`). They sat invisible for 11 hours
until the 2026-05-27 session opened that worktree to address
unrelated PR #484 review comments and discovered 43 dirty
files including the status flips. Recovery via a tar-snapshot
+ 3-way-merge dance against a fresh branch off origin/main
(see PR #488); the status flips landed cleanly as part of the
recovery commit `docs(specs): mark bulletin-curator +
dashboard-pending-writes-journal approved`. Note the irony:
two of the four silently-lost writes were status flips on
THIS spec, the one that exists to prevent exactly this.

This is **a class of bug**, not a one-off: any long-running
service that holds a session-scoped concept of work but
mutates a shared filesystem outside that scope has the same
shape.

### Goals

1. **Durability** — no dashboard-driven edit is ever lost to
   `git pull` / `git reset --hard` / `git stash drop`
2. **Provenance** — every dashboard-driven edit can be
   traced to: when, what file, what action, what session id,
   what dashboard PID
3. **Surfacing** — fresh sessions, currently-running
   dashboard UI, and downstream consumers (session-start
   hooks, shell prompt, etc.) can all discover pending
   edits via a single canonical contract
4. **Frictionless commit path** — once surfaced, committing
   pending edits should be a one-click (UI) or one-command
   (CLI) action

### Non-goals (this spec)

- Auto-commit on heartbeat (rejected during design discussion —
  too many race conditions, git permission complexity, branch
  cleanup burden; humans-in-loop is correct)
- Generalizing to non-dashboard live-state writers (e.g.
  attune-gui sidecar, future MCP write tools) — this spec
  starts with the ops dashboard; a future spec can promote
  the pattern if it generalizes well
- Auditing or replaying historical pre-spec writes — the
  journal is forward-looking from spec-ship date
- Conflict resolution when a user edits the same file the
  dashboard wrote (treat as standard merge conflict; out of
  scope here)

### Acceptance criteria

**Phase 1 (this spec, this session):**

1. Every dashboard write endpoint (`PUT
   /api/cowork/specs/{feature}/{phase}/status` at minimum)
   appends an entry to `~/.attune/ops/pending_writes.jsonl`
   describing the write
2. `GET /api/pending-writes` returns the list of journal
   entries that are still uncommitted (cross-references
   against `git status`)
3. Tests cover: journal write succeeds; API returns
   correctly-filtered list; entries with committed-to-git
   state are filtered out
4. Manual smoke test passes: make a dashboard edit, query the
   API, see the entry; commit the file, query again, entry
   gone

**Phase 2 (future session):**

- UI chip in dashboard topbar: "N unsaved changes" → review
  page with per-file diff + commit/revert actions

**Phase 3 (future session):**

- Session-start hook (CLAUDE.md preamble or attune CLI
  subcommand) that queries the API on fresh-session start and
  surfaces pending writes to the agent for proactive
  human-in-loop triage

### Out of scope (deferred)

- attune-gui sidecar integration (same pattern, different
  endpoint set) — could be a follow-up spec
- Shell-prompt integration (`PS1` hook showing pending count)
  — nice-to-have, not load-bearing

### Audience

attune-ai contributors and downstream consumers of the ops
dashboard. Users of the dashboard who edit spec statuses
benefit directly; agents starting fresh sessions in worktrees
benefit indirectly.
