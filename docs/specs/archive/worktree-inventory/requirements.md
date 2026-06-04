# Spec: Worktree Inventory

> A small affordance on the ops dashboard's `/sessions`
> page that surfaces every worktree this project has spawned
> with Claude Code sessions in the last 3 days. Helps with
> orphan-worktree cleanup; reuses data already loaded by the
> sessions listing.

---

## Motivation

A multi-worktree dev pattern (Cowork spawns, `git worktree
add` for stacked PRs) produces dozens of encoded keys under
`~/.claude/projects/`. attune-ai itself has 47 distinct
worktree-encoded keys at the time this spec was drafted.
Most are orphaned — the worktree directory was removed but
the encoded key under `~/.claude/projects/` lingers because
Claude Code never deletes it.

The ops-sessions-page spec introduces a multi-key glob to
surface sessions across all those keys. We're already
walking them. The marginal work to also surface a
"worktrees touched in the last 3 days" list is one
`group_by` over data we have in hand.

This isn't a worktree-management tool. It's a visibility
affordance — the same way the Specs page surfaces "what's
in-flight." Cleanup actions can come later if they prove
useful.

---

## User story

> As a developer who's been using worktrees aggressively, I
> want to see which worktrees actually have recent activity
> so I can confidently delete the ones that don't.

The affordance lives where worktree-related context already
lives — the Sessions page. No new top-level route.

---

## Functional requirements

### F1 — Inventory section on `/sessions`

A small panel near the top of `/sessions` (or near the
bottom of the resume-card region, TBD during design)
showing:

| Worktree | Sessions (3d) | Last activity | Worktree path exists? |
|---|---|---|---|
| `<canonical>` (the project root itself) | N | timestamp | yes |
| `<worktree-slug>` | N | timestamp | yes / **no — orphaned** |

Rows sort by last-activity desc. Cap at, say, 10 most-
recently-active worktrees by default; "show all" expands.

### F2 — Orphan detection

For each encoded key, check whether the decoded path
exists on disk. If not, mark the row as "orphaned" with
a visual chip. Reverse-encoding is irreversible (`/` and
`-` both encode to `-`), so use a pragmatic check:
candidate decodings (`-` → `/`) and test each for
existence. If none exists, mark orphaned.

### F3 — Failure modes (silent)

- `~/.claude/projects/` doesn't exist → no panel rendered.
- A single encoded key is unreadable (perm) → skip with
  WARN log; don't surface a broken row.
- Worktree existence check fails (perm on the candidate
  decoded path) → conservatively report "exists" rather
  than falsely flagging as orphaned.

---

## Non-goals (initial release)

- No delete action. Surfacing only. Cleanup is a separate
  decision the user makes outside the dashboard.
- No cross-project worktree view. This is scoped to the
  current project's encoded keys, same as ops-sessions-page.
- No worktree-creation UI.
- No live-tracking of worktree mutations (the panel reads
  on page load, period).

---

## Cross-spec dependencies

- `docs/specs/ops-sessions-page/` — introduces the
  multi-key glob and the shared helper
  `enumerate_project_encoded_keys()` in
  `src/attune/ops/data.py`. This spec consumes that helper
  and adds a `group_by(encoded_key)` pass on top of the
  already-loaded session records. Must ship AFTER the
  ops-sessions-page spec's S3 (which is where the helper
  lands).

---

## Success criteria

- The `/sessions` page renders an inventory panel
  alongside the session list when there are >1 worktree
  keys with sessions in the window.
- Orphaned keys are visually distinct from active ones.
- No new HTTP routes; reuses `/sessions`'s data.
- Zero increase to page-load cost (the data is already
  walked for the session list).
