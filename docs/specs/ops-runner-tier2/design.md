# Design — Ops Runner Tier 2
**Status:** approved
Technical shape of the work. See `requirements.md` for what we're building, `tasks.md` for the phase plan.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ Browser                                                  │
│  workflows.html  (table, row per workflow)               │
│    ├── scope <select> + <input> per row                  │
│    ├── runner.js (existing) + Tier 2 additions:          │
│    │     ├── scope reader (URL → POST body)              │
│    │     ├── pill click → POST /workflows/X/run          │
│    │     ├── history strip renderer                      │
│    │     └── recommendation card renderer (SSE event)    │
│    └── CSS additions: .scope-picker, .recent-runs, ...   │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP/SSE
┌──────────────────────────────────────────────────────────┐
│ FastAPI / attune.ops.server                              │
│                                                          │
│  routes/dashboard.py                                     │
│    GET /workflows  → renders workflows.html              │
│      passes features, supports_path map, recent runs     │
│                                                          │
│  routes/runner.py  (existing)                            │
│    POST /workflows/{name}/run                            │
│      body now accepts: { "path": str | null }            │
│      validates path, builds command, kicks off run       │
│                                                          │
│    GET /runs/{id}/stream                                 │
│      yields SSE: "line" + new "recommendation" events    │
│                                                          │
│  routes/runs_history.py  (NEW)                           │
│    GET /api/runs/{workflow}    → recent N runs           │
│    GET /api/runs/{workflow}/{run_id}  → full run log     │
│                                                          │
│  data.py                                                 │
│    list_features() → reads .help/features.yaml           │
│    SUPPORTS_PATH_ARG dict                                │
│                                                          │
│  runner.py                                               │
│    RunnerService now writes Run to disk on completion    │
│    Command builder uses path from request body           │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
        ~/.attune/ops/runs/<workflow>/<run-id>.json
        (persisted run history)
```

---

## Module-by-module changes

### `src/attune/ops/data.py`

- **New:** `list_features(project_root: Path) -> list[Feature]` — reads `.help/features.yaml`, returns dataclasses with `name`, `paths`, `description`. Returns `[]` if file missing/malformed (logs warning).
- **New:** `SUPPORTS_PATH_ARG: dict[str, bool]` — explicit per-workflow declaration. A drift-guard test asserts every workflow returned by `list_workflows()` has an entry.

### `src/attune/ops/routes/dashboard.py`

`workflows_page()` (existing) gets two more context vars:

```python
return _render(
    request,
    "workflows.html",
    page="workflows",
    workflows=workflows,
    allow_run=cfg.allow_run,
    features=data.list_features(cfg.project_root),
    supports_path=data.SUPPORTS_PATH_ARG,
)
```

### `src/attune/ops/runner.py`

`RunnerService.start_run()` accepts an optional `path: str | None`. The `_default_command` becomes:

```python
def _default_command(workflow: str, path: str | None = None) -> Sequence[str]:
    cmd = [sys.executable, "-m", "attune.cli_minimal", "workflow", "run", workflow]
    if path:
        cmd.extend(["--path", path])
    return cmd
```

Persistence:
- `Run.to_dict()` already exists; extend to include `scope` and `command` fields
- On completion (whether success or failure), write `~/.attune/ops/runs/<workflow>/<run-id>.json` with the full record + truncated log
- Read-only mode skips the write
- Startup task: prune runs older than 30 days (configurable via `--runs-retention-days`)

### `src/attune/ops/routes/runner.py`

POST body schema (new):

```python
class RunRequest(BaseModel):
    path: str | None = None  # validated server-side
```

If `path` is provided:
- Apply `_validate_file_path(path, allowed_dir=config.project_root)`
- Reject with 400 if validation fails

If the workflow has `SUPPORTS_PATH_ARG[name] is False` and `path` is provided:
- 400 with `"workflow '<name>' does not accept a --path argument"`

### `src/attune/ops/routes/runs_history.py` (NEW)

```python
@router.get("/api/runs/{workflow}")
async def list_runs(workflow: str, request: Request) -> dict:
    """Last 20 persisted runs for a workflow, newest first."""
    # validates workflow name against registry
    # reads ~/.attune/ops/runs/<workflow>/*.json, sorts by started_at desc
    # returns truncated metadata only (no logs)

@router.get("/api/runs/{workflow}/{run_id}")
async def get_run(workflow: str, run_id: str, request: Request) -> dict:
    """Full record of one run including log."""
    # validates run_id is hex-only (no path traversal)
```

### `src/attune/ops/templates/workflows.html`

Per-row addition before the Run button:

```html
<td class="scope-cell">
  {% if supports_path[w.name] %}
    <select class="scope-picker" data-scope="{{ w.name }}"
            aria-label="Scope for {{ w.name }}">
      <option value="" selected>All of project</option>
      <optgroup label="Features">
        {% for f in features %}
          <option value="{{ f.paths|join(' ') }}"
                  title="{{ f.description or '' }}">{{ f.name }}</option>
        {% endfor %}
      </optgroup>
      <option value="__custom__">Custom path…</option>
    </select>
    <input type="text" class="scope-custom" hidden
           placeholder="e.g. src/foo/bar.py"
           aria-label="Custom path for {{ w.name }}" />
  {% else %}
    <span class="scope-na"
          title="{{ w.name }} runs project-wide by design (no --path)">
      project-wide
    </span>
  {% endif %}
</td>
```

Recent-runs strip below each row (history chip per-workflow):

```html
<div class="recent-runs" data-recent-runs="{{ w.name }}"></div>
```

(Populated by JS via `GET /api/runs/{w.name}` after DOMContentLoaded. Each chip is a link to `/runs/{run_id}/view` — the user can browse prior runs of this workflow with one click.)

### `src/attune/ops/templates/run_view.html` (Run-view page integration — post-#251)

PR #251 introduced this page. Tier 2 extends it with three Tier 2-specific elements:

```html
<!-- Inline run-history navigator at the top of the run-view page,
     showing the last 5 runs of THIS workflow as chips. Click a chip
     to switch the page to that run's view. Same data source as the
     workflows-table strip, just a different layout. -->
<div class="run-view-history" data-recent-runs="{{ run.workflow }}"></div>

<!-- Below the log pane: a slot for structured recommendation cards
     (Phase 5). The log pane is unchanged — recommendations come from
     a separate SSE event type ("recommendation"), not parsed from
     the log stream. -->
<div class="run-view-recommendations" data-recs></div>

<!-- A "← from <source-workflow>" badge in the header when this run
     was chained from a workflow-name pill click in another run.
     Hidden by default; set by JS when the source query param is
     present in the URL (e.g. `/runs/{id}/view?from=code-review`). -->
<span class="chained-from" hidden></span>
```

### `src/attune/ops/static/js/runner.js` (Workflows-table launcher only)

Additions on the workflows page (responsible for scope-pick + Run + recent-runs strip):
- `getScope(row)` — reads the picker + custom input, returns string or null
- `setupScopePicker(row)` — wires the "Custom path…" toggle behavior
- `setupRecentRuns(row)` — fetches `/api/runs/<name>`, renders chips that link to `/runs/<run_id>/view`

The existing `attach(button)` for the Run button is extended to read `getScope(row)` and pass it in the POST body, then navigate to `/runs/<run_id>/view` (already does this since #251 — Tier 2 just adds the `?from=<workflow>` query param if this run was chained from another).

### `src/attune/ops/static/js/run_view.js` (NEW — run-view page logic)

PR #251 inlines a small script in `run_view.html`. Tier 2 extracts it to its own file and adds:
- `setupPillHandlers()` — `.log-workflow` pills get a click listener that POSTs `/workflows/<target>/run` with the current scope, then navigates to `/runs/<new_run_id>/view?from=<this-workflow>`
- `renderRecommendationCard(payload)` — appends a `.recommendation-card` to `.run-view-recommendations` when a `recommendation` SSE event arrives
- `setupRunViewHistory()` — fetches `/api/runs/<workflow>`, renders chips in `.run-view-history`. Clicking a chip is a same-tab navigation to that run's view (browser back works).
- `renderChainedFromBadge()` — reads `?from=` from the URL, populates `.chained-from` if present

### `src/attune/ops/static/css/main.css`

New selectors:
- `.scope-picker`, `.scope-custom` — combobox styling matching the existing `.status-select`
- `.scope-na` — disabled-looking inline span
- `.recent-runs`, `.run-view-history` — flex strip of chips (same styling, two locations)
- `.recent-run-chip` — clickable chip with outcome color (`chip-ok`/`chip-danger`/`chip-warn`)
- `.recommendation-card` — action card in the run-view recommendations slot, hover/click states + severity color
- `.chained-from` — small badge in the run-view header showing the source workflow

---

## Failure modes & their handling

| Failure | Behavior |
|---------|----------|
| `.help/features.yaml` missing | Picker shows only "All of project" + "Custom path…" |
| `.help/features.yaml` malformed YAML | Same as missing + warning log line at server start |
| `SUPPORTS_PATH_ARG` missing entry for a registered workflow | Drift-guard test fails CI; runtime falls back to "no --path" |
| User submits custom path that fails validation | 400 with the validation error inline in the log pane |
| Persistence dir not writable | Warning logged; runs proceed in memory only; recent-runs strip empty |
| Workflow emits a `recommendation` event with bad payload | Server drops the event with warning; UI doesn't render anything |
| `--read-only` flag set + pill clicked | 403 with toast: "Read-only mode: re-launch without --read-only to run workflows" |

---

## Security

- Path validation uses existing `_validate_file_path` (covered by extensive tests)
- Persistence writes go through the same `_validate_file_path` to ensure run_id is safe (already a UUID hex)
- SSE `recommendation` events emitted by workflows are validated against an allowlist of `kind` values before broadcast
- No `innerHTML` in the new JS — same security guarantee as Tier 1 (enforced by existing test)

---

## Backward compatibility

- POST `/workflows/{name}/run` without a body: still works (path=None means project-wide)
- Workflows that don't emit `recommendation` events: still render the Tier 1 regex parser output
- Old in-memory run history is replaced by disk-backed; no migration needed (in-memory was per-process anyway)
- The `--read-only` flag continues to gate all mutations
