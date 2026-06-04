# Tasks — Discovery-Sweep Ops Dashboard Integration

**Status:** DONE 2026-05-16. All four phases shipped. Phase 0 audit + Phase 1 + Phase 1b + Phase 2A + Phase 2B shipped 2026-05-13; Phase 3 (Dashboard UI) + Phase 4 (Documentation) shipped 2026-05-16.
**Spec docs:** `requirements.md`, `design.md`, `decisions.md`,
[`audit-2026-05-13.md`](audit-2026-05-13.md)
**Implementation path:** Option A (stdout-emit + sidecar parser)
per the audit. Original draft tasks were rewritten below.

---

## Phase 0 — Re-audit against current ops-runner-tier2 surface — **shipped 2026-05-13**

Read-only design-decision PR confirming the spec's premise against
the actually-shipped runner. Output: Option A adopted.

- [x] **0.1** Inspect PRs #324 / #326 to characterize the actual
      runner surface (subprocess + per-run SSE; no shared
      `/events`; no scope-keyed persistence).
- [x] **0.2** Document mismatches between original design and
      reality.
- [x] **0.3** Propose revised design (Option A) and surface
      decision questions Q1–Q3.

---

## Phase 1 — Engine `event_sink` API + `ATTUNE_DS` stdout emission

Goal: ship the engine-side surface Phase 2 (daemon parser) and
Phase 3 (UI) will build on. No daemon-visible behavior change for
existing CLI callers — both new surfaces are opt-in (event_sink
defaults to None; stdout emission gated on non-TTY detection).

- [x] **1.1** Add an `EventSink` type alias
      (`Callable[[dict[str, Any]], Awaitable[None]]`) and a
      threaded `event_sink: EventSink | None = None` kwarg through
      `DiscoverySweepWorkflow.execute()` → `_run_source()`.
- [x] **1.2** Add a `sweep_id: str | None = None` kwarg. Engine
      doesn't generate it; daemon callers pass `run_id`; CLI
      leaves it None.
- [x] **1.3** Implement `source_started` / `source_finished` /
      `source_failed` event emission inside `_run_source` via a
      `_safe_emit()` wrapper that catches sink exceptions and uses
      `asyncio.create_task` for fire-and-forget delivery (NFR-2).
- [x] **1.4** Add an `_iso_now()` helper
      (`datetime.now(timezone.utc).isoformat()`) used by all event
      timestamps.
- [x] **1.5** Tests in `tests/unit/workflows/discovery_sweep/test_event_sink.py`:
      - `event_sink=None` is a no-op (preserves today's behavior).
      - Sink fires exactly once per source per outcome
        (`started` + (`finished` xor `failed`)).
      - Event shape matches `design.md` (event/source/sweep_id/
        ts/findings_count|error).
      - A sink that raises doesn't propagate into the sweep.
      - A slow sink doesn't block other sources' execution.
- [x] **1.6** CHANGELOG entry under `### Added`.

### Phase 1b — `ATTUNE_DS` stdout emission — **shipped 2026-05-13**

New `src/attune/workflows/discovery_sweep/ds_stdout.py` module owns
the format. Engine wires `ds_stdout.is_emission_enabled()` →
`emit_version_line()` / `emit_event_line()` / `emit_final_line()` at
the right points in `execute()` and `_emit_event`.

- [x] **1b.1** Emission gated on the **`ATTUNE_DS_EMIT=1`** env var
      (not `sys.stdout.isatty()` — that would pollute the
      legitimate `attune workflow run … > out.md` pipe-to-file
      UX). Daemon sets the env var when spawning. See decision #10.
- [x] **1b.2** `ATTUNE_DS_VERSION 1` emitted as the first line.
- [x] **1b.3** `ATTUNE_DS final <json>` emitted once the sweep
      completes (single-line; embedded newlines stripped).
- [x] **1b.4** Tests in `test_ds_stdout.py` (18 cases): formatter /
      parser round-trips for every event kind, emission gate
      semantics, engine wiring (version-line-first, per-source
      events, failed source emits source_failed, final line carries
      SweepResult JSON, user event_sink + stdout side-channel
      co-exist).

---

## Phase 2A — Sweep-results storage primitives — **shipped 2026-05-13**

Goal: ship the scope-keyed persistence module as a pure utility
that anyone can compose, without touching the runner. The
auto-persist hook + HTTP route + server wiring split off into
Phase 2B (blocked until PRs #324 / #326 / #328 land on `main` and
unblock the conflict-prone files).

- [x] **2A.1** Parser + persistence primitives in NEW file
      `src/attune/ops/sweep_results.py`:
      - `scope_hash(path)` — sha256 of canonicalized path, first
        16 hex chars. Equivalent paths (`./src`, `src/`,
        absolute) collapse to the same digest.
      - `parse_lines(lines)` — walks captured stdout, returns the
        final SweepResult JSON dict or `None`. Refuses unknown
        `ATTUNE_DS_VERSION` values.
      - `persist_result(scope_path, sweep_dict, config)` — atomic
        write via tempfile + `os.replace` in the same dir, so a
        partial write never corrupts the read side.
      - `read_result(digest, config)` — reads `<hash>.json` or
        returns `None`.
      - `persist_from_lines(scope_path, lines, config)` —
        composition wrapper the Phase 2B daemon hook will call.
      - `is_persistence_enabled()` — feature flag
        (`ATTUNE_OPS_SWEEP_RESULTS=1`).
- [x] **2A.2** Storage layout: `~/.attune/ops/sweep-results/`,
      one `<hash>.json` per scope. Latest-only semantics (history
      deferred per decisions.md #3).
- [x] **2A.3** Tests in `tests/unit/ops/test_sweep_results.py`
      (24 cases): persistence-flag gate (3), scope_hash
      canonicalization + collision properties (5), parse_lines
      round-trips + edge cases (6), persist+read +
      latest-only-semantics + atomic write (8), persist_from_lines
      composition (2). 92.16% coverage; only defensive error
      branches uncovered.

## Phase 2B — Daemon-side wiring + HTTP route — **shipped 2026-05-13**

Goal: auto-persist on run-complete + expose results via HTTP.
Shipped despite PRs #324 / #326 / #328 still being open by using
option (c) below — a `server.py`-only wiring that monkey-patches
`runner.start` post-construction. No touch on the conflict-prone
`runner.py` / `routes/runner.py`.

- [x] **2B.1** Auto-persist wiring. **Option (c) chosen** over
      the original (a) / (b): wrap `app.state.runner.start` at
      app-construction time in `server.py`. The wrap spawns
      `watch_and_persist(run, config)` as a background task for
      every `discovery-sweep` run. Watcher lives in NEW file
      `src/attune/ops/sweep_results_watcher.py` so the logic is
      testable in isolation. `getattr(run, "path", None)` lets
      the watcher gracefully no-op on today's path-less `main`;
      persistence activates automatically once PR #324 (which
      adds `Run.path`) lands.
- [x] **2B.2** GET endpoint added in NEW file
      `src/attune/ops/routes/sweep_results.py`. Path parameter
      validated as 16 lowercase hex chars (400 if not); 404 on
      missing file or corrupt JSON.
- [x] **2B.3** Router registered in `server.py` (one new
      `app.include_router` line + the `runner.start` wrap, both
      gated by `sweep_results.is_persistence_enabled()`).
- [x] **2B.4** Tests:
      - `tests/unit/ops/test_sweep_results_watcher.py` (10 cases)
        — workflow-name filtering, success-persists,
        no-op-on-failure / no-path / empty-path, fault
        tolerance (persist exception caught, missing final line
        logs info no crash).
      - `tests/unit/ops/test_sweep_results_route.py` (4 cases)
        — malformed hash → 400 (4 variants), missing → 404,
        success round-trip, corrupt sidecar → 404.

**Coverage:** `sweep_results_watcher.py` 90.24%, `routes/sweep_results.py`
100%. Only the watcher's defensive subscription-exception branch
is uncovered (Run.subscribe() doesn't realistically raise).

**Feature flag:** `ATTUNE_OPS_SWEEP_RESULTS=1` env var. When unset,
the runner-start wrap and the route are both effectively dormant
(route still registered but read-only; watcher never spawned).

---

## Phase 3 — Dashboard UI

Goal: render the discovery-sweep row + chips + live progress +
drill-in in the workflows.html dashboard page.

- [x] **3.1** Discovery-sweep row honors the existing scope picker.
      `PATH_ARG_REGISTRY["discovery-sweep"]` already routes the scope
      through; verified rendering on the workflows page.
- [x] **3.2** Per-bucket colored chips on the discovery-sweep row
      (queue / questions / rejected). Server-rendered for first paint;
      `runner.js` refreshes them on scope-picker change via
      `/api/workflows/discovery-sweep/chips`. Empty buckets render as
      `0`. The chip row carries a `data-has-result` attribute so the
      template can dim chips when no sweep is recorded for the scope.
- [x] **3.3** Live progress panel on `/runs/<id>/view` for
      discovery-sweep runs. Static `<li>` per source emitted server-
      side in alphabetical order; `run_view.js`'s
      `parseSweepEventLine` + `updateSweepProgress` flip the
      `data-state` attribute on each item as `ATTUNE_DS source_*`
      events arrive on the SSE stream. Renders the four states
      `pending / running / finished / failed` with glyph + detail
      text (findings count for finished, error class for failed).
- [x] **3.4** Chip click navigates to the detail page with the
      bucket filtered:
      `/workflows/discovery-sweep/results/<scope-hash>?bucket=<key>`.
      Detail-page bucket nav also offers an "All" link to clear
      the filter.
- [x] **3.5** Detail page (`sweep_detail.html`) renders each finding
      via a uniform row layout with severity chips, source chips,
      file:line link, tags, routing metadata, and a collapsed
      Evidence `<details>`. JSON read API moved to
      `/api/workflows/discovery-sweep/results/<hash>` so the bare
      URL serves HTML.
- [x] **3.6** Tests in `tests/unit/ops/test_workflow_list_chips.py`
      (9 cases) — chip-count loader (missing / corrupt / populated /
      empty-fields), workflows-page rendering (chip block markers,
      anchor hrefs, count reflection), JS-source guards (runner.js
      exports + run_view.js source-event parser presence), and the
      run_view progress panel markup with a disk-loaded discovery-
      sweep run. Existing route tests expanded to cover the moved
      JSON endpoint + the new chips API + the new HTML detail
      route (24 cases total in `test_sweep_results_route.py`).

---

## Phase 4 — Documentation + sequencing

- [x] **4.1** `docs/specs/_sequencing.md` marks this spec DONE
      (2026-05-16).
- [x] **4.2** Parent spec `docs/specs/discovery-sweep/tasks.md`
      cross-link updated to note completion of the carved-out
      ops-dashboard work.
- [x] **4.3** User-facing guide added at
      `docs/how-to/discovery-sweep-on-the-dashboard.md` covering
      enabling persistence, triggering a sweep, reading chips,
      watching live progress, drilling into findings, and a
      troubleshooting section.

---

## Definition of done

- All four phases shipped on `main`
- Dashboard renders discovery-sweep with chips + live progress
- Detail view works with the existing run-view component
- Manual smoke test on at least one real repo (run a sweep, see
  the chips update live, click through to a finding)
- This spec is marked DONE in `_sequencing.md`

---

## Out of scope (post-spec follow-ups)

- Multi-repo aggregation
- Slack / GitHub PR comment integrations
- Trend dashboards / time-series storage
- Auth / multi-user (inherited from ops-runner-tier2 single-user
  assumption)
- Re-run-from-dashboard button — deferred to a v2 if user demand
  exists; v1 is read-only after the CLI / cron triggers the
  sweep.
