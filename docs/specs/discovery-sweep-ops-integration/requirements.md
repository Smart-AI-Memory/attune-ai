# Requirements — Discovery-Sweep Ops Dashboard Integration
**Status:** approved (2026-05-13)
**Parent spec:** `docs/specs/discovery-sweep/` (feature-complete on
`main` as of #321)
**Blocks on:** `docs/specs/ops-runner-tier2/` Phase 2 (must ship
first to provide the SSE event-stream + per-workflow scope picker
this spec builds on)

This spec was carved out of the parent `discovery-sweep` spec
during Phase 1.5 (2026-05-13). The parent spec ships
discovery-sweep as a runnable CLI workflow with markdown + JSON
output; this follow-up spec ships the ops dashboard integration
that turns that into a live, clickable, multi-source view.

---

## Problem

`attune workflow run discovery-sweep --path X --json` produces
machine-readable triage output (queue / questions / rejected
buckets per source), but today's only consumption surface is the
terminal. Users running attune in a long-lived environment
(running a daily sweep, tracking findings over time, working
across multiple repos) need a persistent UI that:

- Shows current sweep status without re-running from the CLI
- Highlights changed-since-last-run findings
- Renders per-bucket counts as colored chips in the ops dashboard's
  workflow list
- Streams live progress (per-source start/finish events) during a
  long-running sweep instead of blocking on the CLI

The ops-runner-tier2 spec already ships the necessary
infrastructure: a long-running ops daemon, an SSE event stream
between daemon and dashboard, and a `PATH_ARG_REGISTRY` that the
scope-picker UI reads to know which workflows accept which path
kwargs.

## Users / use cases

| User | Use case |
|---|---|
| Solo developer with multi-repo audits | Single dashboard tab per repo showing current sweep status; click a chip to drill into findings without leaving the browser. |
| Team using attune in CI | Dashboard shows latest sweep result from a scheduled cron run; PR reviewers click through to specific findings during review. |
| Maintainer tracking quality trends | Per-source finding-count time series visible in the dashboard; spot trends like "bug-predict findings rising over the last 4 sweeps." |

## User stories

### US-1: Discovery-sweep row in the workflow list

**As a** user with the ops dashboard open
**I want** the discovery-sweep row to honor the same scope picker
the other workflows use (path / dir / glob)
**So that** I can scope a sweep without leaving the dashboard.

**Resolved (Phase 1.5):** `discovery-sweep` is already in
`PATH_ARG_REGISTRY` as Category A (`kwarg="path"`,
`required=False`). The scope picker already supports it; this
story is mostly a UI-side verification + per-bucket chip rendering.

### US-2: Per-bucket colored chips

**As a** user looking at the workflow list
**I want** each discovery-sweep row to show three colored chips —
queue (red, "act on"), questions (yellow, "needs judgment"),
rejected (gray, "filtered noise") — with the count next to each
**So that** I can see at-a-glance whether the last sweep needs my
attention.

Chip color map echoes the markdown severity colors from Phase 3.2
where useful (queue items skew critical/high, so red; questions
skew unknown/medium, so yellow; rejected is just-shy of severity
threshold, so dim/gray).

### US-3: Click-through to finding detail

**As a** user clicking a chip
**I want** to land on a detail view listing the findings in that
bucket
**So that** I can read individual findings without re-running the
sweep from the CLI.

The detail view should re-use the existing run-view page
(presumably built for ops-runner-tier2) and render the JSON output
that discovery-sweep already produces via `--json`.

### US-4: Live per-source progress

**As a** user who just triggered a sweep from the dashboard
**I want** a live progress bar showing "pattern-scan: done /
bug-predict: in-progress (45s elapsed) / security-audit: pending"
**So that** I know the sweep is alive and which adapter is
currently running.

This requires the engine to emit SSE events as each source starts
and finishes. The fan-out is already
`asyncio.gather(*per_source_tasks)`; per-source telemetry hooks
need wiring.

## Functional requirements

### FR-1: Honor PATH_ARG_REGISTRY

Discovery-sweep MUST appear in the dashboard's workflow picker
using the scope picker UI already used by all Category-A
workflows. No special-casing.

### FR-2: Per-bucket chip rendering

Each discovery-sweep row in the workflow list MUST render three
colored chips reflecting the most recent sweep's bucket counts.
Empty buckets MUST render as `0` (not hidden) so the absence of
findings is visible.

### FR-3: JSON payload contract preserved

The dashboard MUST consume the EXISTING JSON output shape that
Phase 3 ships — top-level
`{queue, questions, rejected, metadata}` with each finding
serializing the Finding dataclass via `dataclasses.asdict()`. The
ops-integration MUST NOT require a separate JSON schema for the
dashboard.

### FR-4: Per-source SSE events

While a sweep runs, the daemon MUST emit SSE events of shape:

```json
{"event": "source_started", "source": "bug-predict", "ts": "..."}
{"event": "source_finished", "source": "bug-predict",
 "ts": "...", "findings_count": 7}
{"event": "source_failed", "source": "X", "ts": "...", "error": "..."}
```

The dashboard reads these and renders the progress bar.

### FR-5: Drill-in re-uses existing run-view page

Clicking a bucket chip MUST navigate to a detail view that
displays the findings in that bucket. The view MUST be the same
template ops-runner-tier2 uses for other workflow run details —
no bespoke discovery-sweep UI.

## Non-functional requirements

### NFR-1: Dashboard works in `--no-llm` mode without ops daemon

Even when the ops daemon isn't running, `discovery-sweep --no-llm
--json` from the CLI MUST produce dashboard-consumable JSON
(saved to a file the dashboard's static-mode page reads). This is
a strict requirement so a user can audit a fresh repo without
spinning up the daemon.

### NFR-2: SSE events don't block source execution

Per-source SSE event emission MUST be fire-and-forget (e.g.,
`asyncio.create_task` on a publish queue, not awaited inline).
A blocked or slow dashboard listener MUST NOT stall the sweep.

### NFR-3: No new dependencies on attune-ai core

This spec ships under `attune-ai`'s existing dep set. Any
SSE-emission code reuses ops-runner-tier2's primitives; no new
top-level packages.

## Open questions

> **DECIDE before Phase 1**: Does the daemon persist sweep history
> (last N runs per scope) or only the latest? The trend-tracking
> use case in the table above implies history; the simpler design
> implies just-latest. Likely just-latest for v1 with a follow-up
> for history.

> **DECIDE before Phase 1**: Where does the rendered JSON live on
> disk? Likely `~/.attune/sweep-results/<scope-hash>.json` keyed
> by the canonicalized scope path. Confirm against the
> ops-runner-tier2 storage layout.

> **DECIDE during Phase 2**: Should the dashboard offer a "re-run
> this sweep" button that triggers the daemon? If yes, that's
> Phase 2 work; if no, this stays read-only and the spec is
> narrower.

## Out of scope

- Multi-repo aggregation (one dashboard showing N repos)
- Slack / GitHub PR comment integrations
- Persistent trend dashboards / time-series storage beyond
  "latest sweep per scope"
- Cross-source finding correlation beyond the existing
  verification rules (dedup-by-location, severity-conflict)
- Auth / multi-user access controls (single-user dashboard
  assumed, inherited from ops-runner-tier2)
