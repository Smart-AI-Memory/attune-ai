# Design — Discovery-Sweep Ops Dashboard Integration

**Status:** draft (2026-05-13)
**Requirements:** `requirements.md`
**Parent code:** `docs/specs/discovery-sweep/` (feature-complete on
`main`)
**Builds on:** `docs/specs/ops-runner-tier2/` (SSE event stream +
workflow-list dashboard surface — must ship first)

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Ops dashboard (workflows.html)                                │
│                                                                │
│  Workflow list row                                             │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ discovery-sweep    [scope picker]  [Run] [chips: 12🔴│ ◀── chip click →
│   │                                          3🟡 27⚪]    │      detail view
│   └──────────────────────────────────────────────────────┘    │
│                                                                │
│  Progress (live during a run)                                  │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ ✓ pattern-scan      ✓ bug-predict   ⏳ security-audit │   │
│   │                                                       │   │
│   │ Findings so far: 8 queue, 2 questions, 4 rejected    │   │
│   └──────────────────────────────────────────────────────┘    │
└────────┬───────────────────────────────────────────────────────┘
         │ SSE: source_started / source_finished events
         ▼
┌────────────────────────────────────────────────────────────────┐
│  Ops daemon (from ops-runner-tier2)                            │
│                                                                │
│  - HTTP endpoint: POST /workflows/discovery-sweep/run          │
│    body: {path, depth?, no_llm?, source?, verbose?}            │
│  - SSE stream: GET /events                                     │
│    emits source_started, source_finished, source_failed        │
│  - Static JSON: GET /workflows/discovery-sweep/results/<hash>  │
│    returns the most recent sweep's JSON                        │
└────────┬───────────────────────────────────────────────────────┘
         │ asyncio.create_task(workflow.execute(...))
         ▼
┌────────────────────────────────────────────────────────────────┐
│  DiscoverySweepWorkflow.execute()                              │
│   (already shipped — Phase 1–3)                                │
│                                                                │
│  Engine fan-out via asyncio.gather(per-source tasks)           │
│  This spec adds: per-source telemetry hooks fired around       │
│  each task — emit "source_started" before, "source_finished"   │
│  or "source_failed" after.                                     │
└────────────────────────────────────────────────────────────────┘
```

**Resolved (Phase 1.5 of parent spec):** SSE event stream is a
core deliverable of ops-runner-tier2. This spec reuses that stream
rather than building a parallel one.

---

## SSE event shape

```python
@dataclass
class SourceStartedEvent:
    event: Literal["source_started"]
    source: str
    sweep_id: str          # ops daemon assigns when the sweep
                           # starts; lets dashboard correlate
                           # events across N concurrent sweeps
    ts: str                # ISO-8601 with timezone

@dataclass
class SourceFinishedEvent:
    event: Literal["source_finished"]
    source: str
    sweep_id: str
    ts: str
    findings_count: int    # raw count from this source, BEFORE
                           # verification rules route them

@dataclass
class SourceFailedEvent:
    event: Literal["source_failed"]
    source: str
    sweep_id: str
    ts: str
    error: str             # type(exc).__name__ — full traceback
                           # stays in the daemon's stderr log
```

Three events per source per sweep. With 7 sources (pattern-scan +
6 LLM) that's ~21 events per sweep — trivial to render.

---

## Per-source telemetry hook in the engine

Currently:

```python
# src/attune/workflows/discovery_sweep/workflow.py
gathered = await asyncio.gather(
    *(_run_source(s, paths, allocations[s.name]) for s in sources),
    return_exceptions=False,
)
```

`_run_source(source, paths, budget_usd)` calls
`source.discover(...)` and returns
`(source_name, findings_or_exception)`. The proposed change adds
an optional `event_sink: Callable[[dict], Awaitable[None]] | None`
kwarg threaded through `execute()` → `_run_source`:

```python
async def _run_source(
    source: FindingSource,
    paths: list[str],
    budget_usd: float,
    *,
    event_sink: EventSink | None = None,
    sweep_id: str | None = None,
) -> tuple[str, list[Finding] | BaseException]:
    if event_sink is not None and sweep_id is not None:
        await event_sink({
            "event": "source_started",
            "source": source.name,
            "sweep_id": sweep_id,
            "ts": _iso_now(),
        })
    try:
        findings = await source.discover(paths, budget_usd)
    except Exception as exc:  # noqa: BLE001
        if event_sink is not None and sweep_id is not None:
            await event_sink({
                "event": "source_failed",
                "source": source.name,
                "sweep_id": sweep_id,
                "ts": _iso_now(),
                "error": type(exc).__name__,
            })
        return source.name, exc
    if event_sink is not None and sweep_id is not None:
        await event_sink({
            "event": "source_finished",
            "source": source.name,
            "sweep_id": sweep_id,
            "ts": _iso_now(),
            "findings_count": len(findings),
        })
    return source.name, findings
```

`event_sink` is `None` by default — CLI invocations get exactly
today's behavior. Daemon invocations pass a sink that pushes to
the SSE stream (and is itself wrapped in `asyncio.create_task` per
NFR-2 so a slow listener doesn't stall the sweep).

---

## Storage layout

Daemon writes the JSON output of each sweep to:

```
~/.attune/ops/sweep-results/
  <scope-hash>.json       # latest sweep result for this scope
  <scope-hash>.meta.json  # {path, depth, ts, sweep_id}
```

`<scope-hash> = sha256(canonicalized_scope_path)[:16]` so two
different paths get distinct files. Latest-only for v1 (history
deferred per the requirements DECIDE callout).

---

## Dashboard rendering

The workflow list row pulls counts from `<scope-hash>.json`:

```python
# Pseudocode for the dashboard's per-row data loader
def chip_counts(workflow_name: str, scope: str) -> dict[str, int]:
    if workflow_name != "discovery-sweep":
        return {}
    hash_ = scope_hash(scope)
    path = f"~/.attune/ops/sweep-results/{hash_}.json"
    if not path.exists():
        return {"queue": 0, "questions": 0, "rejected": 0}
    data = json.loads(path.read_text())
    return {
        "queue": len(data.get("queue", [])),
        "questions": len(data.get("questions", [])),
        "rejected": len(data.get("rejected", [])),
    }
```

Chip rendering uses the parent spec's Phase 3.2 ANSI severity
colors as design tokens (red / yellow / dim) translated to CSS:

| Bucket | Token | CSS |
|---|---|---|
| queue | `severity.high` | `--severity-high: #e54848;` |
| questions | `severity.medium` | `--severity-medium: #e5b048;` |
| rejected | `severity.dim` | `--severity-dim: #8888aa;` |

Reusing the parent's color tokens keeps the CLI markdown and the
dashboard visually consistent.

---

## Detail view (drill-in)

Clicking a chip navigates to the existing
`ops-runner-tier2`-shipped run-detail page with a query param
narrowing the bucket:

```
/workflows/discovery-sweep/<sweep-id>?bucket=queue
```

The detail page reads the same `<scope-hash>.json`, filters to
the requested bucket, and renders each Finding via a generic
finding-row component (created here, generalized later by
ops-runner-tier2 if more workflows adopt the JSON-emit pattern).

---

## Tests

| Test file | What it covers |
|---|---|
| `tests/unit/workflows/discovery_sweep/test_event_sink.py` | `_run_source` calls event_sink with the correct event shape; sink is fire-and-forget (a slow sink doesn't block the sweep); None sink is a no-op. |
| `tests/unit/ops/test_sweep_results_storage.py` | scope-hash collision properties, latest-only semantics, atomic-write behavior of the JSON file. |
| `tests/integration/ops/test_sweep_via_dashboard.py` | `@pytest.mark.integration` — spins up the daemon, triggers a sweep via HTTP, verifies SSE events arrive in order and JSON file lands. |
| `tests/unit/ops/test_workflow_list_chips.py` | Dashboard chip-count loader; missing-file returns zero counts; corrupt file returns zero counts with a logged warning. |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| SSE listener stalls block source execution (race between fan-out and slow consumer) | medium | NFR-2: event sink is fire-and-forget via `asyncio.create_task`; never `await`ed inline. |
| JSON storage grows unboundedly across many scopes | low | Latest-only-per-scope semantics cap storage; manual cleanup or LRU-eviction is post-v1. |
| Daemon and CLI write the same JSON file simultaneously (race) | low | Atomic write via `tempfile.NamedTemporaryFile` + `os.replace` in the same dir. CLI runs typically don't touch the daemon's storage path, but make the write safe in case they do. |
| Dashboard listens stale SSE events from a prior sweep | low | `sweep_id` correlates events; the dashboard filters by the most recent sweep_id and ignores older. |
| ops-runner-tier2 Phase 2 ships in a shape that doesn't match this spec's assumptions | high | This spec is a draft; finalize the SSE shape + storage layout against ops-runner-tier2's actual surface before opening implementation PRs. |
