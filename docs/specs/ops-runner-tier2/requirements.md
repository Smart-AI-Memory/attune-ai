# Requirements — Ops Runner Tier 2

**Status:** draft

User-facing stories and the contracts they imply. See `decisions.md` for context, `design.md` for the technical shape, `tasks.md` for the phase plan.

---

## Personas

- **Pat (project owner)** — runs attune ops daily against his own codebase. Wants fast iteration on one feature at a time.
- **Casey (contributor)** — runs attune ops occasionally to triage a PR. Wants the recommendations the workflow author put there to be one click away.

---

## User stories

### US-1 — Scope a workflow to one feature

**As Pat, when I want to run `code-review` on just `src/attune/memory/`, I want to pick "memory" from a dropdown on the row and click Run.** The dropdown shows the features defined in my project's `.help/features.yaml`, plus an "All of project" default and a "Custom path…" free-form option.

Acceptance:
- The dropdown is populated from `.help/features.yaml` at server start (refreshed if the file changes)
- The default selection is "All of project" on a fresh page load
- Selecting a feature does NOT trigger a run — only the Run button does
- The subprocess command becomes `attune workflow run <workflow> --path <path>` (or `--paths <p1> --paths <p2>` if the feature has multiple paths)
- The output log shows which scope was used (header line: `Scope: memory (src/attune/memory/)`)

### US-2 — Free-form path for ad-hoc scoping

**As Casey, when triaging a PR, I want to scope a workflow run to the exact path the PR touches even if it isn't in `features.yaml`.** Selecting "Custom path…" opens a text input below the dropdown.

Acceptance:
- The text input accepts a single relative path or glob (e.g. `src/attune/workflows/*.py`)
- The value is validated server-side (no path traversal, no absolute paths outside project)
- The input persists across the page lifetime so I can run the same workflow against the same custom scope without re-typing

### US-3 — Workflow doesn't support `--path` → picker disabled

**As Pat, when I'm looking at a row for `release-prep` (which doesn't take `--path`), I want the picker to be visibly disabled with a tooltip explaining why.**

Acceptance:
- The picker is rendered but `disabled` with a `cursor: not-allowed` style
- Hovering shows: "release-prep runs project-wide by design and doesn't accept a --path argument"
- The Run button still works as before

### US-4 — Workflow-name pill becomes a one-click run

**As Pat, when `code-review` finishes and its output recommends running `bug-predict`, I want to click the "bug-predict" pill in the output log and have a new run kick off with the same scope.**

Acceptance:
- Pills are clickable (cursor: pointer, hover state)
- Click triggers POST to `/workflows/<name>/run` with the current row's scope as the `path` body field
- The new run appears in the bug-predict row (not the code-review row)
- A subtle "↩ from code-review on memory" badge appears in the new run's output header

### US-5 — Run history per workflow

**As Pat, when I revisit the dashboard, I want to see "last 5 runs" for each workflow as a strip of clickable chips so I can see what's been happening without scrolling.**

Acceptance:
- Each row on the Workflows tab shows up to 5 most-recent chips: outcome (✓ / ✗), elapsed time, scope, age (e.g. "2m ago")
- The same chip strip also appears at the top of the run-view page (`/runs/<id>/view`) for the current run's workflow — lets the user switch between recent runs without leaving the page
- Clicking any chip navigates to `/runs/<run_id>/view` (the full-page viewer from #251)
- History persists across server restarts (writes to `~/.attune/ops/runs/<workflow>/<run-id>.json`)
- The current "last 20 runs in memory" behavior is removed (persisted history supersedes it)

### US-6 — Structured recommendations as action cards

**As a workflow author, I want my workflow to be able to emit machine-readable recommendations that the dashboard renders as proper action cards (not regex-parsed prose).**

Acceptance:
- A workflow opts in by emitting an SSE event with `event: recommendation` and a JSON payload like `{"kind": "next-workflow", "name": "bug-predict", "args": {"path": "src/foo"}, "label": "Run bug-predict to verify the fix"}`
- The dashboard renders these as cards in the **run-view page**'s recommendations slot (below the log) — NOT inline in the log stream
- Clicking a card runs the named workflow with the given args and navigates to the new run's view page
- The Tier-1 regex parser stays as a fallback for non-opted-in workflows (parsed inline in the log)

---

## Contracts

### C-1 — `.help/features.yaml` source

The server reads `.help/features.yaml` once at startup and on file-mtime change. Shape (Python type-hint form):

```yaml
features:
  - name: "memory"                  # str — appears in the dropdown
    paths: ["src/attune/memory/"]   # list[str] — passed as --path arg(s)
    description: "Memory subsystem" # str — tooltip on hover (optional)
  - name: "ops"
    paths: ["src/attune/ops/"]
    description: "Operations dashboard"
```

If the file is missing or malformed, the picker shows ONLY "All of project" + "Custom path…" — never crashes.

### C-2 — Path validation server-side

Custom paths must pass:
- Relative path (no leading `/`)
- No `..` traversal segments
- Resolved path stays inside `config.project_root`
- Glob characters (`*`, `?`, `[...]`) allowed
- Result is forwarded to the subprocess as one or more `--path` arguments

Reuses `_validate_file_path` already in the codebase.

### C-3 — Workflow `--path` capability registry

A new dict in `attune.ops.data` (or a method on the workflow info dataclass):

```python
SUPPORTS_PATH_ARG = {
    "code-review": True,
    "bug-predict": True,
    "simplify-code": True,
    "perf-audit": True,
    "test-gen": True,
    "doc-audit": True,
    "security-audit": True,
    "refactor-plan": True,
    "release-prep": False,
    "health-check": False,
    "dependency-check": False,
    "rag-code-gen": False,
    "research-synthesis": False,
    "test-audit": False,
    "secure-release": False,
    "orchestrated-health-check": False,
    "deep-review": True,
    "doc-gen": True,
    "doc-orchestrator": True,
}
```

To verify, not invent: Phase 1 of `tasks.md` is to grep each workflow's CLI handler / `execute()` signature and confirm. The registry is the SINGLE source of truth (template uses it, runner uses it, drift-guard test asserts every registered workflow appears in it).

### C-4 — SSE recommendation event shape

```json
{
  "kind": "next-workflow",       // future kinds: "open-file", "open-url", "external-action"
  "name": "bug-predict",          // workflow name (must match registry)
  "args": {"path": "src/foo"},    // forwarded to /workflows/<name>/run
  "label": "Run bug-predict",     // button text in the UI
  "rationale": "...",             // optional, shown on hover
  "severity": "info"              // info | warn | critical, drives card color
}
```

Validated server-side before broadcast (drops bad payloads with a warning log line).

### C-5 — Persistence schema

```
~/.attune/ops/runs/<workflow>/<run-id>.json
```

```json
{
  "id": "abc12345",
  "workflow": "code-review",
  "scope": {"kind": "feature", "name": "memory", "paths": ["src/attune/memory/"]},
  "started_at": "2026-05-11T22:00:00Z",
  "completed_at": "2026-05-11T22:03:24Z",
  "status": "completed",
  "exit_code": 0,
  "command": ["python", "-m", "attune.cli_minimal", "workflow", "run", "code-review", "--path", "src/attune/memory/"],
  "log": "<first 200 KB of the log, then a truncation marker>"
}
```

Read-only mode (`attune ops --read-only`) does NOT write new files but reads existing ones. Logs older than 30 days are pruned at startup.

### C-6 — Read-only mode

Per existing `--read-only` flag (already enforced for the Specs status-flip): all Tier 2 mutation paths must respect it.

- Scope picker is shown but Run is disabled (already true in #240 pattern)
- Workflow-name pill clicks return 403 with a friendly message
- Recommendation cards render as visible-but-disabled

---

## Non-goals (named here so the spec doesn't drift)

- Multi-project ops (covered in `decisions.md` Out of scope)
- Editor integration for file-path chips (separate spec if/when)
- Run cancellation
- Sharing runs across users
- Workflow scheduling (cron-like) from the dashboard
