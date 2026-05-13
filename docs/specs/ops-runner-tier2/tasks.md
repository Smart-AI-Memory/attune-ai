# Tasks — Ops Runner Tier 2

**Status:** Phase 1 audit done 2026-05-12 (see audit.md); Phase 1.3 + Phases 2–5 pending

Phased plan. Each phase is independently shippable + reversible (single-commit revert). See `decisions.md`, `requirements.md`, `design.md` for context.

---

## Phase 1 — Verify `--path` capability per workflow (no code changes yet)

Goal: turn hypothesis H2 ("Workflow `--path` support is unevenly implemented") into a hard fact, populating the `SUPPORTS_PATH_ARG` registry from real inspection.

- [x] **1.1** Grep each workflow class's `execute()` signature and CLI handler for `--path` / `paths` argument acceptance. **Done 2026-05-12** — see [audit.md](audit.md). The grep recipe in the spec needed adapting (it scoped to `src/attune/workflows/*.py` but 4 workflows live in package subdirs like `src/attune/workflows/doc_audit/workflow.py`).
- [x] **1.2** Manually verify by running each workflow with `--help` from the CLI. **Done 2026-05-12.** Key finding: the CLI surface `attune workflow run --help` accepts `--path` UNIFORMLY for all workflows; it becomes a `path=...` kwarg in `workflow.execute(**input_data)`. Whether the workflow consumes that kwarg is the real question — answered per-workflow in audit.md.
- [ ] **1.3** Record findings as `PATH_ARG_REGISTRY` dict (Option 2 from audit.md) in `src/attune/ops/data.py`. Drift-guard test in `tests/unit/ops/test_path_support_registry.py` asserts every workflow has an entry AND that the entry's `kwarg` matches the actual kwarg name in the workflow source. **Pending user approval** to write production code — audit complete; implementation deferred to a separate PR so reviewer can sign off on the three-way (not binary) registry shape.

## Phase 2 — Scope picker (headline feature)

Goal: per-row dropdown that scopes the workflow run to one feature or custom path.

- [ ] **2.1** Add `Feature` dataclass + `list_features()` to `src/attune/ops/data.py`. Reads `.help/features.yaml`, returns `[]` on missing/malformed. Caches result with mtime check.
- [ ] **2.2** Pass `features` + `supports_path` to `workflows.html` from `dashboard.py`.
- [ ] **2.3** Render the `<select>` + hidden `<input type="text">` per row in `workflows.html`. Show `<span class="scope-na">` for workflows where `supports_path[w.name] is False`.
- [ ] **2.4** Update `RunRequest` body to accept `path: str | None` in `routes/runner.py`. Validate via `_validate_file_path`.
- [ ] **2.5** Extend `RunnerService.start_run()` + `_default_command()` to thread `path` into the subprocess invocation.
- [ ] **2.6** `runner.js`: add `getScope(row)`, wire the picker toggle UX (custom path input shows when "Custom path…" is selected), pass scope as POST body.
- [ ] **2.7** CSS: `.scope-picker`, `.scope-custom`, `.scope-na` matching existing `.status-select` aesthetic.
- [ ] **2.8** Tests:
      - `test_list_features_*` — missing file, well-formed file, malformed YAML
      - `test_run_with_path_arg` — POST with `path` ends up in subprocess command
      - `test_run_rejects_invalid_path` — path traversal returns 400
      - `test_run_rejects_path_for_no-path-workflow` — `release-prep` with path returns 400
      - JS parsing: `test_runner_js_workflows_html_has_scope_picker` (assert the template renders the select for path-supporting workflows)

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
