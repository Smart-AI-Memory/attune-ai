# Design: Dashboard Pending-Writes Journal

**Status:** draft (2026-05-25)

**Phase 1 scope:** journal writer + API endpoint. UI chip
(Phase 2) and session-start hook (Phase 3) are sketched at
the bottom for design coherence, not for this session's
implementation.

---

## Architecture

Three layers, each addressing a distinct damage mode:

```text
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌──────────────┐        ┌──────────────────────────┐  │
│  │  Dashboard   │ writes │ ~/.attune/ops/           │  │
│  │  endpoints   ├───────►│   pending_writes.jsonl   │  │
│  │  (mutating)  │        │   (append-only JOURNAL)  │  │
│  └──────────────┘        └────────────┬─────────────┘  │
│                                       │ reads           │
│                                       ▼                 │
│                          ┌──────────────────────────┐  │
│                          │ GET /api/pending-writes  │  │
│                          │   (cross-refs git status │  │
│                          │    to filter committed)  │  │
│                          └────────────┬─────────────┘  │
│                                       │ consumed by    │
│              ┌───────────────────────┼─────────────┐  │
│              ▼                       ▼             ▼  │
│      ┌───────────────┐     ┌──────────────┐  ┌──────┐│
│      │ Dashboard UI  │     │ Session-     │  │ Other ││
│      │ chip + review │     │ start hook   │  │ tools ││
│      │ (Phase 2)     │     │ (Phase 3)    │  │       ││
│      └───────────────┘     └──────────────┘  └──────┘│
└─────────────────────────────────────────────────────────┘
```

**Why three layers, not one shot:**

- The **journal** is the source of truth — durable, append-only,
  easy to inspect, no in-memory state to lose
- The **API** is the contract — multiple consumers can read
  without each re-implementing the git-status cross-reference
- The **consumers** address distinct surfaces (in-session
  user vs fresh-session agent vs anyone else who wants the
  signal) without coupling

---

## Data model

### Journal entry shape

```jsonc
{
  "ts": "2026-05-25T15:00:00.000Z",      // ISO 8601 UTC, microsecond precision OK
  "session_id": "...",                    // CLAUDE_CODE_SESSION_ID or "dashboard-<pid>" if no session
  "dashboard_pid": 35492,                 // OS PID of the dashboard process that made the write
  "endpoint": "PUT /api/cowork/specs/{feature}/{phase}/status",  // canonical endpoint name
  "action": "set_spec_status",            // human-readable action
  "file_path": "docs/specs/coverage-exclusion-policy/decisions.md",  // POSIX path, project-relative
  "project_root": "/Users/patrickroebuck/attune-ai",   // absolute, for disambiguation
  "before_sha256": "457e21fa...",         // sha256 of file content BEFORE the write (or null if file was new)
  "after_sha256": "36985342..."           // sha256 of file content AFTER the write
}
```

**Why these fields:**

- `ts` — for ordering, age display, age-based pruning (future)
- `session_id` + `dashboard_pid` — provenance for triage ("which session made this? still running?")
- `endpoint` + `action` — for human readability ("this is a spec status edit, not a random write")
- `file_path` + `project_root` — for git-status cross-reference, and for disambiguating worktree-local edits
- `before_sha256` / `after_sha256` — verifies the journal entry matches actual disk state at filter time; lets the API detect "user reverted manually" without losing audit

### Storage

`~/.attune/ops/pending_writes.jsonl` (one JSON object per line, append-only).

Rationale: matches existing telemetry pattern
(`~/.attune/telemetry/usage.jsonl`). Atomic appends are
trivial with POSIX semantics (`open(path, 'a')` + `write` +
`fsync`). Journal grows linearly with dashboard activity; a
future maintenance task can prune entries whose file is
committed AND whose `after_sha256` matches `git show
HEAD:<file>` (i.e. fully reconciled).

---

## API: `GET /api/pending-writes`

### Request

`GET /api/pending-writes` — no params.

Future Phase 2 may add `?project_root=<path>` filtering for
multi-project dashboards; out of scope here.

### Response

```jsonc
{
  "pending": [
    {
      "ts": "2026-05-25T15:00:00.000Z",
      "session_id": "abc-123",
      "dashboard_pid": 35492,
      "dashboard_still_running": false,    // computed: kill(pid, 0) succeeds
      "endpoint": "PUT /api/cowork/specs/{feature}/{phase}/status",
      "action": "set_spec_status",
      "file_path": "docs/specs/coverage-exclusion-policy/decisions.md",
      "project_root": "/Users/patrickroebuck/attune-ai",
      "before_sha256": "457e21fa...",
      "after_sha256": "36985342...",
      "current_disk_sha256": "36985342...",  // computed at API time
      "matches_journal": true,               // current_disk == after_sha
      "is_committed": false,                 // git status check
      "age_seconds": 1234
    }
    // ... more pending entries
  ],
  "summary": {
    "total_entries": 12,
    "uncommitted_count": 5,
    "stale_dashboard_count": 3,          // entries whose dashboard PID is dead
    "drifted_count": 1                   // entries where matches_journal=false
  }
}
```

### Filter semantics

The API returns ALL journal entries (not filtered to
uncommitted), but ENRICHES each with computed fields:

- `dashboard_still_running` — `kill(pid, 0)` check
- `current_disk_sha256` — sha256 of file at API call time
- `matches_journal` — does current_disk_sha == after_sha
- `is_committed` — does `git status --porcelain <file>`
  return empty for this file? (file is clean in git)

Consumers filter as needed. The dashboard UI chip would
show `uncommitted_count`. A session-start hook would show
entries where `is_committed=false`. An auditor might want
entries where `matches_journal=false` to investigate manual
reverts.

**Why enriched-not-filtered:** the journal is the source of
truth; filtering varies per consumer. Better to enrich once
and let consumers slice than re-implement git-status checks
in every consumer.

---

## Implementation: Phase 1

### Module placement

- **Journal writer:** new module
  `src/attune/ops/pending_writes.py` with:
  - `JournalEntry` dataclass matching the schema above
  - `append_entry(entry: JournalEntry) -> None` — appends to
    JSONL, atomic, swallows errors with WARNING log (don't
    let journal failures block the actual write)
  - `JOURNAL_PATH` constant pointing at
    `~/.attune/ops/pending_writes.jsonl`
  - Helper: `compute_file_sha256(path: Path) -> str | None`
- **API endpoint:** new route in
  `src/attune/ops/routes/pending_writes.py`:
  - `GET /api/pending-writes` — reads journal, enriches,
    returns JSON per the schema above
  - Helper: `_load_journal_entries() -> Iterator[dict]`
  - Helper: `_enrich(entry: dict, project_root: Path) -> dict`
- **Wire-in to existing write endpoint:**
  in the spec-status setter route (currently in
  `src/attune/ops/routes/cowork_specs.py` for attune-ai),
  call `pending_writes.append_entry(...)` after the
  successful write, BEFORE returning the response.

### Tests

- `tests/unit/ops/test_pending_writes.py`:
  - `append_entry` writes one line per call (parametric on
    entry shapes)
  - `append_entry` survives `IOError` (logs WARNING, does
    not raise) — journal failure must not block actual write
  - `compute_file_sha256` handles: existing file, missing
    file, unreadable file
- `tests/unit/ops/test_pending_writes_api.py`:
  - Empty journal returns `{pending: [], summary: {...}}`
  - Single entry: returns enriched with all computed fields
  - Entry whose file is now committed: `is_committed=true`
  - Entry whose file was manually reverted: `matches_journal=false`
  - Entry whose dashboard PID is dead: `dashboard_still_running=false`
  - Use `tmp_path` for project_root + journal path
- `tests/unit/ops/test_cowork_specs_journal.py` (or extend
  existing test file):
  - PUT /api/cowork/specs/.../.../status appends to journal
  - Failed write (e.g. invalid status) does NOT append

### Wire to startup config

The dashboard's `app.state` likely already exposes
`attune_home` (the `~/.attune` directory). The journal
path derives from that. No new config needed.

---

## Phase 2 (sketched — not this session)

- **Topbar chip** in `base.html`: yellow indicator with
  count when `uncommitted_count > 0`
- **Review page** at `/pending-writes/view`: list of pending
  entries with per-file `git diff` rendered, "Commit
  selected" and "Revert selected" buttons
- **Commit action** opens a small modal: review the commit
  message (auto-generated from the action types), confirm,
  commit + push to a `chore(dashboard)` branch OR to
  current branch per a config flag

## Phase 3 (sketched — not this session)

- **Session-start hook**: CLAUDE.md preamble that runs at
  session start, queries `GET /api/pending-writes` (if the
  dashboard is running on a known port), surfaces any
  uncommitted entries to the agent for triage
- **CLI subcommand**: `attune ops pending` shows pending
  writes from terminal; `attune ops pending --commit-all`
  one-shots the commit path

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Journal writes block the actual write endpoint | `append_entry` is wrapped in try/except; failures log WARNING; actual write proceeds regardless |
| Journal grows unbounded over months | Future maintenance task prunes fully-reconciled entries; out of scope for Phase 1 |
| sha256 computation is slow on large files | Spec status files are tiny (<100KB); not a concern. Pre-emptively cap journal entries to files under 10MB if it ever matters. |
| Concurrent appends from multiple dashboard processes | POSIX `O_APPEND` is atomic per write under the page size; entries fit in <1KB; no race. |
| API endpoint returns stale data if cache layer added | No cache layer in Phase 1; if added later, invalidate on every `append_entry`. |
| Worktree-local edits get mixed with main-checkout edits | `project_root` field in each entry disambiguates; API filters by current project_root by default (future enhancement) |
