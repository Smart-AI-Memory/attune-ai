# Tasks — Ops Runner Tier 2

**Status:** Phase 1 complete 2026-05-13 (audit + registry shipped); Phase 2 complete 2026-05-14 (scope picker shipped); Phases 3–5 pending

Phased plan. Each phase is independently shippable + reversible (single-commit revert). See `decisions.md`, `requirements.md`, `design.md` for context.

---

## Phase 1 — Verify `--path` capability per workflow (no code changes yet)

Goal: turn hypothesis H2 ("Workflow `--path` support is unevenly implemented") into a hard fact, populating the `SUPPORTS_PATH_ARG` registry from real inspection.

- [x] **1.1** Grep each workflow class's `execute()` signature and CLI handler for `--path` / `paths` argument acceptance. **Done 2026-05-12** — see [audit.md](audit.md). The grep recipe in the spec needed adapting (it scoped to `src/attune/workflows/*.py` but 4 workflows live in package subdirs like `src/attune/workflows/doc_audit/workflow.py`).
- [x] **1.2** Manually verify by running each workflow with `--help` from the CLI. **Done 2026-05-12.** Key finding: the CLI surface `attune workflow run --help` accepts `--path` UNIFORMLY for all workflows; it becomes a `path=...` kwarg in `workflow.execute(**input_data)`. Whether the workflow consumes that kwarg is the real question — answered per-workflow in audit.md.
- [x] **1.3** Record findings as `PATH_ARG_REGISTRY` dict (Option 2 from audit.md) in `src/attune/ops/data.py`. Drift-guard test in `tests/unit/ops/test_path_support_registry.py` asserts every workflow has an entry AND that the entry's `kwarg` matches the actual kwarg name in the workflow source. **Shipped 2026-05-13** — 19 entries (12 Cat A + 2 Cat B + 5 Cat C), `PathArgSpec` dataclass with `kwarg: str` and `required: bool = False`. 25 drift-guard tests covering coverage drift, kwarg drift, shape invariants, and audit-doc presence. All green.

## Phase 2 — Scope picker (headline feature)

Goal: per-row dropdown that scopes the workflow run to one feature or custom path.

**Shipped 2026-05-14.** 20 new tests in `tests/unit/ops/test_scope_picker.py`; full ops suite (189 tests) green.

- [x] **2.1** `Feature` dataclass + `list_features()` in `src/attune/ops/data.py`. Reads `.help/features.yaml`, returns `[]` on missing/malformed. Module-level mtime cache `_FEATURES_CACHE` keyed by absolute YAML path. Path-derivation prefers `/**` directory globs over single-file entries; skips mid-name globs (`code_review_*.py`) — they're not addressable scopes.
- [x] **2.2** `dashboard.py::workflows_page` reads `cfg.project_root`, calls `data.list_features()`, and builds `supports_path = {w.name: w.name in data.PATH_ARG_REGISTRY}` so the template can render either a picker or an `n/a` span.
- [x] **2.3** `workflows.html` renders a `<select data-scope-picker>` with Project-wide + one option per feature with a usable path + "Custom path…", plus a hidden `<input data-scope-custom>`. `<span class="scope-na">` shown when `supports_path[w.name]` is False. A new "Scope" `<th>` sits between Description and Action; both columns are gated on `allow_run` so read-only mode keeps the existing layout.
- [x] **2.4** `routes/runner.py::start_run` reads optional `{"path": "..."}` body via a new `_read_scope()` helper. Empty body / empty string / missing key → `None` (project-wide). Path is validated via `_validate_file_path(allowed_dir=cfg.project_root)`; traversal / outside-root / non-string / malformed-JSON all return 400 BEFORE the runner is touched.
- [x] **2.5** `Run` gained a `path: str | None` field; `to_dict()` exposes it. `RunnerService.start(workflow, *, path=None)` records the scope. `_execute` appends `--path <scope>` after `_command_builder(workflow)` — test fixtures with `(str) → Sequence[str]` signatures keep working unchanged.
- [x] **2.6** `runner.js` adds `getScope(row)` + `wireScopePickerToggle(row)`. Click handler builds `{path: scope}` body only when scope ≠ null; project-wide POSTs stay body-less so existing endpoints don't see a behavior change. Helpers exposed on `window.__attuneRunner`.
- [x] **2.7** CSS `.scope-picker` / `.scope-custom` / `.scope-na` in `static/css/main.css` (matched against existing `.status-select` aesthetic — same arrow glyph, `6px` radius, max-width 220px).
- [x] **2.8** Tests:
      - `test_list_features_*` (6 tests) — missing file, well-formed, malformed YAML, non-mapping features key, glob-only feature → `path=None`, mtime cache invalidation
      - `test_run_with_path_threads_into_subprocess` — `--path <validated>` shows up in the recorded command line
      - `test_run_without_body_runs_project_wide` — no body → no `--path`
      - `test_run_rejects_invalid_path_traversal` — `/etc/passwd` → 400
      - `test_run_rejects_path_outside_project_root` — sibling dir → 400
      - `test_run_rejects_path_for_no_path_workflow` — workflow absent from `PATH_ARG_REGISTRY` → 400
      - `test_run_rejects_non_string_path` / `test_run_rejects_non_object_body` / `test_run_rejects_malformed_json` — input shape rejections
      - `test_run_treats_empty_path_as_project_wide` — empty string → 201
      - `test_workflows_page_renders_scope_picker_for_path_workflow` / `test_workflows_page_renders_n_a_for_no_path_workflow` / `test_workflows_page_no_scope_column_when_read_only` — template surface
      - `test_runner_js_exports_get_scope_and_toggle` / `test_runner_js_default_post_is_no_body` — JS shape

## Phase 3 — Persistence (recent runs)

Goal: replace in-memory run history with disk-backed per-workflow history.

- [ ] **3.1** Extend `Run.to_dict()` to include `scope` and `command` fields. Add `from_dict()` for reload.
- [ ] **3.2** On run completion, write `~/.attune/ops/runs/<workflow>/<run-id>.json`. Truncate log to first 200 KB with a `<TRUNCATED — N bytes more>` marker. Skip writes in `--read-only` mode.
- [ ] **3.3** Startup task: prune runs older than 30 days (configurable via `--runs-retention-days`).
- [ ] **3.4** New router `routes/runs_history.py`:
      - `GET /api/runs/{workflow}` → list 20 newest runs (metadata only)
      - `GET /api/runs/{workflow}/{run_id}` → full record + log
- [ ] **3.5** `workflows.html`: add `<div class="recent-runs" data-recent-runs="{{ w.name }}">` below each workflow row. Each chip is a link to `/runs/<run_id>/view` (the per-run page from #251).
- [ ] **3.6** `run_view.html`: add `<div class="run-view-history" data-recent-runs="{{ run.workflow }}">` at the top of the run-view page — same data, second location, makes "switch between recent runs of this workflow" a one-click navigation.
- [ ] **3.7** JS: `setupRecentRuns()` (on workflows.html via runner.js) and the same logic on run-view via the new `run_view.js` (Phase 4.1) — both fetch `/api/runs/<workflow>` and render chips that link to the run-view page.
- [ ] **3.8** CSS: `.recent-runs`, `.run-view-history`, `.recent-run-chip` (color by outcome: ✓ ok, ✗ danger). Same chip class in both locations.
- [ ] **3.9** Tests:
      - `test_run_persists_to_disk` — file written on completion
      - `test_run_persists_truncates_long_log` — 1MB log → 200KB on disk + marker
      - `test_run_skips_write_in_read_only` — `--read-only` doesn't write
      - `test_get_recent_runs_returns_sorted` — newest first
      - `test_get_run_rejects_path_traversal` — `run_id="../../etc/passwd"` returns 400
      - `test_prune_old_runs` — files older than 30 days are deleted at startup
      - `test_run_view_history_renders` — run-view page shows last-5 chips for the same workflow

## Phase 4 — Workflow-name pills become buttons

Goal: Tier 1 pills (inert today) on the run-view page trigger a follow-on run carrying the source run's scope.

**Note:** Pills now live on the **run-view page** (introduced in #251), not the workflows-table log pane. The JS for pill handling moves into a new `run_view.js` file.

- [ ] **4.1** Extract the inline `<script>` block from `run_view.html` into `src/attune/ops/static/js/run_view.js`. (Currently inline as a one-off — Tier 2 needs the file for testing + multiple features.)
- [ ] **4.2** `run_view.js`: attach click handlers to `.log-workflow` pills. On click:
      - Read the source run's scope from the page context (server-injected as `{{ run.scope|tojson }}` once Phase 2 lands)
      - POST `/workflows/<target>/run` with `{path: scope}`
      - On success, navigate to `/runs/<new_run_id>/view?from=<source-workflow>`
      - On 409 (busy), surface inline above the log without navigating
- [ ] **4.3** `run_view.js`: `renderChainedFromBadge()` — reads `?from=` from the URL, populates `.chained-from` in the page header if present. Renders as "↩ from <source-workflow>".
- [ ] **4.4** Handle read-only mode: pill click in `--read-only` shows a toast "Read-only mode: re-launch without --read-only to chain runs". No POST.
- [ ] **4.5** Handle disabled target (already running): the existing 409 handler in `formatErrorDetail` already covers this; surface above the log on the source run-view page (don't navigate away from a successful prior run).
- [ ] **4.6** CSS: `.log-workflow` pill hover state, `.pill-disabled` for `--read-only`, `.chained-from` badge styling.
- [ ] **4.7** Tests:
      - `test_run_view_js_exists` — file is served at `/static/js/run_view.js`
      - `test_run_view_page_loads_run_view_js` — template references the new file
      - `test_pill_click_carries_scope` (manual): visual smoke from the browser
      - `test_read_only_pill_returns_403` — POST while `--read-only` returns 403

## Phase 5 — Structured recommendation channel

Goal: workflows can emit JSON recommendations rendered as action cards on the run-view page.

- [ ] **5.1** Extend SSE event types in `routes/runner.py`. Existing: `line`, `done`. New: `recommendation`.
- [ ] **5.2** Server-side validation: `kind` must be in allowlist (`next-workflow`, `open-url`), `name` must be a registered workflow, `args.path` must pass `_validate_file_path`. Drop bad payloads with warning log.
- [ ] **5.3** `run_view.js`: listen for `recommendation` events. Render an action card into the page's `.run-view-recommendations` slot via `renderRecommendationCard(payload)`.
- [ ] **5.4** Pick ONE workflow to demonstrate end-to-end. Candidate: `code-review` emitting `{"kind": "next-workflow", "name": "bug-predict", "args": {"path": "<same scope>"}, "label": "Run bug-predict to verify"}` when it finds CWE-style issues.
- [ ] **5.5** CSS: `.recommendation-card` action card with hover/click states + severity color.
- [ ] **5.6** Tests:
      - `test_recommendation_event_emitted` — workflow emits, server broadcasts
      - `test_recommendation_event_validated` — bad payload dropped
      - `test_recommendation_card_renders` — JS smoke

## Phase 6 — Telemetry + close

- [ ] **6.1** Add lightweight telemetry: pill click counts, recommendation card click counts, scope picker usage rates (in-memory only — no PII, no network). Surface in the existing `/telemetry` tab.
- [ ] **6.2** Update `docs/COVERAGE_BUG_LOG.md` if any bugs surfaced during Phase 1–5 work.
- [ ] **6.3** Patrick uses the new dashboard for at least one real feature scope; confirms the UX feels right.
- [ ] **6.4** Close this spec. Open follow-up specs if any Phase 3/4 ideas surfaced (e.g. editor integration for file-path chips).

---

## Out of scope (parking lot)

- Multi-project ops
- Editor integration for file-path chips
- Run cancellation
- Sharing runs across users (multi-user persistence)
- Workflow scheduling from the dashboard

---

## Rollback plan

Each phase is a single squash-merge commit. Rollback = `git revert <commit>`. The spec's phasing ensures that reverting any phase leaves earlier phases working independently:

- Revert Phase 5 → pills + scope picker + persistence still work, just no structured recs
- Revert Phase 4 → pills go back to inert (Tier 1 behavior)
- Revert Phase 3 → recent-runs strip disappears; in-memory history restored
- Revert Phase 2 → scope picker gone; project-wide runs only (current behavior)
- Revert Phase 1 → `SUPPORTS_PATH_ARG` removed; no other code depends on it yet
