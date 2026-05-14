# Tasks — Discovery-Sweep Ops Dashboard Integration

**Status:** Phase 0 audit shipped 2026-05-13; Phase 1 in progress.
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

- [ ] **1.1** Add an `EventSink` type alias
      (`Callable[[dict[str, Any]], Awaitable[None]]`) and a
      threaded `event_sink: EventSink | None = None` kwarg through
      `DiscoverySweepWorkflow.execute()` → `_run_source()`.
- [ ] **1.2** Add a `sweep_id: str | None = None` kwarg. Engine
      doesn't generate it; daemon callers pass `run_id`; CLI
      leaves it None.
- [ ] **1.3** Implement `source_started` / `source_finished` /
      `source_failed` event emission inside `_run_source` via a
      `_safe_emit()` wrapper that catches sink exceptions and uses
      `asyncio.create_task` for fire-and-forget delivery (NFR-2).
- [ ] **1.4** Add an `_iso_now()` helper
      (`datetime.now(timezone.utc).isoformat()`) used by all event
      timestamps.
- [ ] **1.5** Tests in `tests/unit/workflows/discovery_sweep/test_event_sink.py`:
      - `event_sink=None` is a no-op (preserves today's behavior).
      - Sink fires exactly once per source per outcome
        (`started` + (`finished` xor `failed`)).
      - Event shape matches `design.md` (event/source/sweep_id/
        ts/findings_count|error).
      - A sink that raises doesn't propagate into the sweep.
      - A slow sink doesn't block other sources' execution.
- [ ] **1.6** CHANGELOG entry under `### Added`.

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

## Phase 2B — Daemon-side wiring + HTTP route (deferred)

Goal: auto-persist on run-complete + expose results via HTTP.
**Blocked** on PRs #324 (scope picker), #326 (persistence +
pills), #328 (release 6.8.0) merging to `main`, which unblocks
the conflict-prone runner / template files.

- [ ] **2B.1** Wire the auto-persist hook. Two options to
      evaluate when this opens: (a) wrapper around
      `RunnerService._executor` (modifies `runner.py`); (b)
      external subscriber via `Run.subscribe()` spawned from the
      POST run route (modifies `routes/runner.py`). Option (b) is
      preferred — it's a smaller surface.
- [ ] **2B.2** Add `GET /workflows/discovery-sweep/results/<hash>`
      in a NEW router module `src/attune/ops/routes/sweep_results.py`.
      404 if no sweep has run for that scope.
- [ ] **2B.3** Register the new router in `server.py`.
- [ ] **2B.4** Tests: end-to-end run → file lands; missing file
      → 404; malformed sidecar → 500 with diagnostic.

---

## Phase 3 — Dashboard UI

Goal: render the discovery-sweep row + chips + live progress +
drill-in in the workflows.html dashboard page.

- [ ] **3.1** Discovery-sweep row honors the existing scope picker
      (already supported via `PATH_ARG_REGISTRY` from parent spec
      P1.7 — verify rendering only).
- [ ] **3.2** Per-bucket colored chips on each row (queue / questions
      / rejected). Empty buckets render as `0`, not hidden.
- [ ] **3.3** Live progress bar while a sweep runs — reads SSE
      events and renders `✓ pattern-scan ⏳ bug-predict ⌛ security-audit`
      style sequential status.
- [ ] **3.4** Chip click navigates to detail view with the bucket
      filtered (`?bucket=queue` / `?bucket=questions` / `?bucket=rejected`).
- [ ] **3.5** Detail view renders findings via the generic
      finding-row component. Includes severity badges (same
      Phase 3.2 color tokens), file:line link, evidence
      collapsed by default.
- [ ] **3.6** Tests:
      - `test_workflow_list_chips.py` — chip count loader
        (missing file → zeros, corrupt file → zeros + warning)
      - Smoke test via Playwright (or whatever ops-runner-tier2
        uses for UI testing) — chips render, click navigates,
        detail page loads.

---

## Phase 4 — Documentation + sequencing

- [ ] **4.1** Update `docs/specs/_sequencing.md` to mark
      `discovery-sweep-ops-integration` as DONE.
- [ ] **4.2** Update the parent `docs/specs/discovery-sweep/`
      with a cross-link to this spec's completion.
- [ ] **4.3** Add a "Using the dashboard" section to the user-
      facing discovery-sweep docs (probably in `docs/workflows/`
      or `.help/templates/`).

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
