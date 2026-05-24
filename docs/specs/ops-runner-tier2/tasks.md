# Tasks — Ops Runner Tier 2

**Status:** **complete (2026-05-24)** — Phase 1 complete 2026-05-13 (audit + registry shipped); Phase 2 complete 2026-05-14 (scope picker shipped); Phase 3 + Phase 4 complete 2026-05-14 (persistence + chainable pills shipped together); Phase 5 complete 2026-05-16 (recommendation channel + run-view cards + `code-review` demo integration); Phase 6.1 complete 2026-05-18 (in-memory interaction counters on `/telemetry`); Phase 6.2–6.4 complete 2026-05-24 (UX confirmed across 7-workflow dashboard exercise; one bug fixed in PR #452; follow-ups noted below).

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

**Shipped 2026-05-14** alongside Phase 4 (per the spec's "Phases 3 and 4 ship together" guidance). 32 new tests in `tests/unit/ops/test_persistence_and_history.py`; full ops suite 221 green (was 189 after Phase 2).

- [x] **3.1** `Run.command` field; `to_record()` / `from_record()` round-trip used by the disk writer + the reload path. `to_dict()` already carried `path` from Phase 2; persistence uses `to_record()` which adds the line buffer.
- [x] **3.2** `_persist_run()` in `runner.py` writes `<runs_dir>/<workflow>/<run-id>.json` atomically (`.json.tmp` → `replace`). 200 KB log cap via `_truncate_lines_for_persist()` with a trailing `<TRUNCATED — N bytes more>` marker. Read-only mode is enforced at the `RunnerService` constructor level — `_build_default_runner()` in `server.py` only passes `persistence_dir` when `config.allow_run` is True.
- [x] **3.3** `prune_old_runs()` is called at `create_app()` time when `allow_run` is True. Retention window comes from `config.runs_retention_days` (`--runs-retention-days` CLI flag, default 30). `0` disables the sweep; missing dir is a no-op.
- [x] **3.4** New router `routes/runs_history.py` with `GET /api/runs/{workflow}` (newest 20 metadata-only) and `GET /api/runs/{workflow}/{run_id}` (full record incl. log). List combines in-memory entries (preserves live status) with disk records (dedup by id). Bad workflow names + bad run-ids return 400 BEFORE any disk lookup. The global 404 handler now dispatches JSON for `/api/*` paths so the dashboard JS can parse errors uniformly.
- [x] **3.5** `workflows.html` adds `<div class="recent-runs" data-recent-runs="{{ w.name }}" hidden>` below each workflow's description cell. The strip stays hidden until the JS fetches and populates it.
- [x] **3.6** `run_view.html` adds `<div class="run-view-history" data-recent-runs="{{ run.workflow }}" hidden>` at the top of the page (below the meta line, above the log).
- [x] **3.7** `setupRecentRuns()` + `renderRecentRunsInto()` + `statusClass()` live in `runner.js`. The run-view page loads `runner.js` BEFORE `run_view.js`; `run_view.js` calls the same helper through `window.__attuneRunner.setupRecentRuns`. Failure modes (404, network) leave the strip hidden — history is best-effort and never blocks rendering. `runner.js` is now loaded unconditionally on `/workflows` (was gated on `allow_run`) so read-only users still get the recent-runs strip.
- [x] **3.8** CSS in `static/css/main.css`: `.recent-runs` / `.run-view-history` (flex row, gap 6px) + `.recent-run-chip` (rounded pill, color by status using existing `chip-ok` / `chip-danger` / `chip-warn` / `chip-muted` palette) + `.recent-run-status` muted-text addendum. Hover state borders to `--accent`.
- [x] **3.9** Tests:
      - `test_run_to_record_round_trip` / `test_from_record_tolerates_missing_fields` / `test_from_record_bad_status_defaults_to_completed`
      - `test_truncate_short_log_is_passthrough` / `test_truncate_long_log_appends_marker`
      - `test_persist_run_writes_json` / `test_persist_run_rejects_bad_workflow_name` / `test_persist_run_rejects_bad_run_id` / `test_persist_run_truncates_long_log`
      - `test_runner_writes_record_on_completion` (subprocess → JSON on disk) / `test_runner_skips_persistence_when_dir_is_none`
      - `test_prune_old_runs_deletes_files_past_cutoff` / `test_prune_old_runs_zero_days_disables_sweep` / `test_prune_old_runs_missing_dir_is_noop`
      - `test_list_persisted_runs_returns_newest_first` / `test_list_persisted_runs_rejects_bad_workflow` / `test_load_run_record_rejects_bad_run_id`
      - `test_list_runs_rejects_bad_workflow_name` / `test_list_runs_empty_when_no_history` / `test_list_runs_combines_in_memory_and_disk`
      - `test_get_run_record_rejects_path_traversal` / `test_get_run_record_returns_404_for_missing` / `test_get_run_record_returns_full_log`
      - `test_read_only_mode_disables_persistence` (no writes + no `runs_dir` creation)
      - `test_workflows_page_includes_recent_runs_strip` / `test_workflows_page_loads_runner_js_in_read_only_too`

## Phase 4 — Workflow-name pills become buttons

**Shipped 2026-05-14** alongside Phase 3.

**Note:** Pills live on the **run-view page** (introduced in #251), not the workflows-table log pane. JS for pill handling lives in `static/js/run_view.js`.

- [x] **4.1** Extracted the inline `<script>` block from `run_view.html` into `src/attune/ops/static/js/run_view.js`. Server-injected config flows through a tagged `<script type="application/json" id="run-view-data">` block instead of inline `var STREAM_URL = {{ ... }}` statements — cleaner data/code separation, devtools-inspectable.
- [x] **4.2** `run_view.js::handlePillClick` is wired as a delegated `click` listener on the log container. On match (closest `.log-workflow`): reads `SOURCE_PATH` from the injected config, POSTs `/workflows/<target>/run` with `{path: SOURCE_PATH}`. On 201 → navigates to `/runs/<new_run_id>/view?from=<SOURCE_WORKFLOW>`. On 409 → surfaces an inline `.run-view-error` above the log, doesn't navigate. The clicked pill gets a `.pill-disabled` class for the duration of the request to prevent double-clicks.
- [x] **4.3** `renderChainedFromBadge()` reads `?from=` via `URLSearchParams`, validates the value against the workflow-name regex (rejects `<script>` and similar), and populates the existing `<span class="chained-from" data-chained-from>` slot in the page header with `↩ from <code>name</code>`.
- [x] **4.4** Read-only mode (config `allow_run=False`) is passed through to the JS via the run-view-data block. The click handler short-circuits without POSTing and shows an inline error: "Read-only mode — restart attune ops without --read-only to chain runs."
- [x] **4.5** Handled implicitly — same 409 path as 4.2's busy case, plus a 403 fallback for the rare race where allow_run flips during a session.
- [x] **4.6** CSS: `.log-workflow` gains `cursor: pointer` + hover border + `transition`. `.pill-disabled` dims to 0.55 opacity with a progress cursor. `.run-view-error` styled with `--danger-soft`/`--danger` colors.
- [x] **4.7** Tests:
      - `test_run_view_page_loads_both_js_files` — template references `runner.js` + `run_view.js` and embeds the JSON data block
      - `test_run_view_js_exists_and_exposes_helpers` — checks file presence + `handlePillClick` / `renderChainedFromBadge` / `pillTargetFromEvent` exports
      - `test_run_view_js_validates_from_param` — confirms the regex literal is present for `?from=` validation
      - `test_run_view_data_block_contains_allow_run_and_path` / `test_run_view_data_block_allow_run_false_in_read_only` — JSON block surfaces both keys correctly
      - `test_read_only_mode_disables_persistence` already covers the runner-side guarantee that a pill click can't sneak in via the runner when `allow_run=False`

## Phase 5 — Structured recommendation channel

Goal: workflows can emit JSON recommendations rendered as action cards on the run-view page.

- [x] **5.1** Extend SSE event types in `routes/runner.py`. Existing: `line`, `done`. New: `recommendation`. **Shipped 2026-05-16** — `EventKind` literal extended in `src/attune/ops/runner.py`; `Run` gained a bounded `recommendations` buffer + `emit_recommendation()` broadcast hook + replay-on-subscribe.
- [x] **5.2** Server-side validation. **Shipped** — `RunnerService._validate_recommendation()` + `handle_stdout_line()` parse the new `ATTUNE_REC <json>` stdout marker; bad kind / unknown workflow / path-traversal `args.path` / non-http(s) urls drop with a `logger.warning`.
- [x] **5.3** `run_view.js`: listen for `recommendation` events. **Shipped** — `renderRecommendationCard(payload)` injects an action card into `[data-recommendations]`; also exports `isSafeUrl()` as defense-in-depth for the open-url branch.
- [x] **5.4** Pick ONE workflow to demonstrate end-to-end. **Shipped 2026-05-16** — `code-review` (`src/attune/workflows/code_review.py`) gained `_emit_security_recommendation_if_warranted()`, called at the end of `execute()`. Scans the synthesized review for CWE/CVE ids + common vulnerability-class phrases (SQL/command injection, path traversal, XSS, CSRF, hardcoded secrets, insecure deserialization/random, `eval(`/`exec(`); on a hit it prints an `ATTUNE_REC` marker suggesting `bug-predict` on the same scope. 26 tests in `tests/unit/workflows/test_code_review_recommendations.py` including a runner-validation round-trip.
- [x] **5.5** CSS: `.recommendation-card` action card with hover/click states + severity color. **Shipped** — left-border severity color (critical/high=danger, medium=warn, low/info=muted) + `.btn-rec` button states in `static/css/main.css`.
- [x] **5.6** Tests: 17 tests in `tests/unit/ops/test_recommendations.py` covering subscribe-time replay, the per-run cap, every validation reject branch, marker-line parsing, and the JS export smoke.

## Phase 6 — Telemetry + close

- [x] **6.1** **Shipped 2026-05-18** — process-lifetime in-memory counters for pill clicks, recommendation-card clicks, and scope-picker changes. Backend: `src/attune/ops/interaction_counters.py` (counter store with thread-safe `Counter` buckets + target normalization) + `src/attune/ops/routes/interaction_counters.py` (`POST /api/telemetry/interaction`, `GET /api/telemetry/interactions`). Frontend: `recordInteraction()` helper on `window.__attuneRunner`, called from `handlePillClick`, recommendation-card action handler, and `wireScopeSave`. Telemetry page gains a "Dashboard interactions (this session)" section with three KPI tiles + top-N tables. 22 tests in `tests/unit/ops/test_interaction_counters.py` cover counter store unit behavior, HTTP API edge cases (unknown event → 204, HTML target → bucketed as `(unknown)`, missing event → 422), and the rendered HTML.
- [x] **6.2** **Shipped 2026-05-24** — no bugs surfaced *from* the test-quality-program coverage work during Phase 1–5 (the modules under coverage were workflow shells in `workflows/`, not `ops/runner.py` / `ops/data.py` / `ops/routes/*`). One ops-runner-adjacent bug surfaced *during the Phase 6.3 dashboard exercise*: see Phase 6.3 entry below for the `learn-*` 404 finding and PR #452 fix; not logged in `COVERAGE_BUG_LOG.md` since it came from manual UX exercise, not coverage triage.
- [x] **6.3** **Shipped 2026-05-24** — Patrick exercised the dashboard end-to-end against the attune-ai project itself across seven workflows in a single working day: `code-review` (targeted at `src/attune/spec/state.py`, 245s, $6.01), `bug-predict` (same file + later project-wide, 104s+190s, $4.89+$7.69), `test-gen` (253s, $7.60), `perf-audit` (231s, $4.55), `refactor-plan` (213s, $4.73), `simplify-code` (150s, $5.92), and `dependency-check` (124s, $4.27). All seven completions returned non-trivial structured output (health scores, finding tables, "What I'd Do Next" suggestions). UX confirmed: scope picker stored per-workflow defaults, run history persisted across server restarts, SSE log streaming worked, run-view chained-from badges rendered correctly, recommendation chips clickable for valid targets. **One issue found:** the "What I'd Do Next" suggestion for help-template-backed workflows emitted `learn-<workflow>` chips that 404'd on click — root cause at [workflows/suggestions.py:588](../../../src/attune/workflows/suggestions.py:588) (`f"learn-{workflow_name}"` points at a non-registered workflow). **Fix shipped same day:** [PR #452](https://github.com/Smart-AI-Memory/attune-ai/pull/452) renders `learn-*` as non-clickable info chips. Underlying schema cleanup (`NextAction.kind` field) deferred to `sdk-error-message-fidelity` spec sibling.
- [x] **6.4** **Closed 2026-05-24** — spec complete. Follow-up specs / work that surfaced from Phase 6.3:
  - **`sdk-error-message-fidelity`** (exists as draft) — the dashboard's "Could not start X: TypeError: Failed to fetch" UX when the server is down or the bundled `claude` subprocess fails opaquely is the higher-leverage variant of the same surface. Adjacent: `workflow-failure-exit-propagation` (draft).
  - **`NextAction.kind` schema cleanup** — three-state union (`"workflow"` | `"info"` | `"slash-command"`) on `NextAction` to remove the renderer-side `learn-*` prefix detection added in PR #452. Worth its own slice of the SDK-error spec or a small standalone refactor.
  - **Drift-guard tax** (bug-predict surface #3 from the 2026-05-24 project-wide pass) — "adding a workflow/skill/version trips 4+ uncoupled registries" is the underlying generator of bugs like `learn-*`. Architectural; needs its own spec when it becomes painful enough.

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
