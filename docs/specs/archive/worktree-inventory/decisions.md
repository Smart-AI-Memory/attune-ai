# Spec: Worktree Inventory — Decisions

> Pre-committed decisions captured 2026-05-15.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Lives where | **Sub-section on `/sessions` page** | The data source (encoded keys under `~/.claude/projects/`) is already walked for the session list. Marginal cost is one `group_by`; no new route. Conceptually grouped with "what sessions exist" — the same set of users care about both. |
| Data source | Reuses `enumerate_project_encoded_keys()` introduced in `ops-sessions-page/` spec | Single source of truth for "which encoded keys belong to this project." Avoids two divergent globs in the same module. |
| Time window | **Last 3 days** (mirrors sessions list) | Same answer for the same reason: stale data isn't useful for cleanup decisions. |
| List cap | **Top 10 by last-activity desc**; "show all" expands | Bounds the panel's vertical footprint. Worktree counts trail off after the top few; rarely meaningful beyond 10 for visual scan. |
| Orphan detection | Decode candidate paths from the encoded key, test each for existence | The `path.replace('/', '-')` encoding is irreversible. Pragmatic candidate-test approach (replace each `-` with `/` for plausible decodings, test on disk) is good enough for a "this looks dead" signal. False-negative is fine; false-positive (flagging an alive key as orphaned) is the failure mode to avoid. |
| Orphan rendering | Visual chip ("orphaned"), no auto-delete | Surface, don't act. Cleanup is the user's decision. |
| Delete affordance | **Not in v1** | Out of scope. May land later as a separate feature if usage validates it. |
| Failure modes | Silent skip + WARN log | Same discipline as ops-sessions-page: an unreadable key is Claude Code's problem, not the user's. Don't surface a broken row. |
| Cross-project scope | Out of scope — current project only | Mirrors ops-sessions-page. Cross-project worktree inventory is a hypothetical we don't need yet. |
| New routes | **None** | All work happens inside the existing `GET /sessions` handler. No `GET /api/worktrees` JSON endpoint in v1; can add later if a separate consumer emerges. |

---

## Implementation sketch

Implementation lives entirely in `src/attune/ops/`:

1. **`data.py`** — add a `WorktreeInventoryRow` dataclass
   and a `list_worktree_inventory(project_root, *, days=3)`
   function. Internally:
   - Calls `enumerate_project_encoded_keys(project_root)`
     (shared helper from ops-sessions-page).
   - For each key, count session JSONLs whose mtime is
     within the window; find the newest mtime.
   - Resolve the canonical and worktree-slug labels from
     the key.
   - Test orphan status with candidate-decoding lookup.
   - Sort and cap.
2. **`routes/dashboard.py`** — `sessions_page()` handler
   gets a second piece of context: `worktree_inventory =
   data.list_worktree_inventory(cfg.project_root)`.
   No new route.
3. **`templates/sessions.html`** — render the panel after
   the resume card and before the session list, only when
   `worktree_inventory` has >1 entry (otherwise just one
   entry = the current project, no inventory value).
4. **Tests** — `tests/unit/ops/test_worktree_inventory.py`:
   key enumeration, orphan detection, sort + cap, render
   path.

Total estimate: ~80 LOC source + ~150 LOC tests + small
template block.

---

## Failure modes

| Mode | Behavior |
|---|---|
| `~/.claude/projects/` doesn't exist | No panel rendered (no inventory at all). |
| Single encoded key unreadable (perm) | Skip with WARN log; rest of inventory renders. |
| Candidate-decoding probe hits a permission error on the candidate path | Conservatively report "exists" (avoid false orphan flag). |
| Only one key (no worktrees yet) | Panel hidden; redundant with the session list. |
| Many keys (>100) | Top-10 cap holds; "show all" expands the list. |

---

## Non-goals (v1)

- No delete or rename actions.
- No cross-project view.
- No `GET /api/worktrees` JSON endpoint.
- No live-tracking of worktree mutations.
- No grouping by branch or any git-aware metadata —
  this is an inventory of *encoded keys*, not of git
  worktrees.

---

## Decision-change log

- 2026-05-15 — Initial spec. Split out from the
  ops-sessions-page spec's interactive review on the same
  day. The original conversation suggested a worktree
  inventory as an "opportunity" sitting on data the sessions
  page would already load; consensus was that it should
  ship as its own spec/PR so the ops-sessions-page spec
  stays focused on its single concern (starter prompts +
  resume affordance). Cross-spec dependency: this spec
  consumes `enumerate_project_encoded_keys()` from
  ops-sessions-page's S3 and must ship after it.
