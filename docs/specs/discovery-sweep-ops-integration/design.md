# Design — Discovery-Sweep Ops Dashboard Integration

**Status:** revised 2026-05-13 to Option A (see
[`audit-2026-05-13.md`](audit-2026-05-13.md))
**Requirements:** `requirements.md`
**Parent code:** `docs/specs/discovery-sweep/` (feature-complete on
`main`)
**Builds on:** `docs/specs/ops-runner-tier2/` (subprocess runner +
per-run SSE stream — shipped via PRs #324 / #326 on `release/v6.8.0`)

> The pre-audit draft of this design assumed an in-process daemon
> with a shared `/events` SSE stream. That design didn't match the
> actually-shipped runner (subprocess + per-run stream). The Phase 0
> audit replaced it with **Option A**: workflow emits `ATTUNE_DS`
> prefix lines to stdout, daemon parses its own stdout buffer at
> run completion, daemon writes scope-keyed JSON the dashboard
> reads. Subprocess + single-run invariants preserved. The engine
> also gains an in-process `event_sink` callback for tests and
> future programmatic consumers (not load-bearing for the
> dashboard).

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Ops dashboard (workflows.html + run_view.html)                │
│                                                                │
│  Workflow list row                                             │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ discovery-sweep    [scope picker]  [Run] [chips: 12🔴│ ◀── chip click →
│   │                                          3🟡 27⚪]    │      detail view
│   └──────────────────────────────────────────────────────┘    │
│   - chips read GET /workflows/discovery-sweep/results/<hash>   │
│                                                                │
│  Progress (live during a run)                                  │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ ✓ pattern-scan      ✓ bug-predict   ⏳ security-audit │   │
│   └──────────────────────────────────────────────────────┘    │
│   - reads existing /runs/<run_id>/stream; parses ATTUNE_DS     │
│     prefix lines client-side                                   │
└────────┬───────────────────────────────────────────────────────┘
         │ HTTP / SSE
         ▼
┌────────────────────────────────────────────────────────────────┐
│  Ops daemon (RunnerService — existing)                         │
│                                                                │
│  - existing: spawns subprocess, captures stdout line-by-line,  │
│    broadcasts via /runs/<run_id>/stream                        │
│  - NEW (Phase 2): post-run hook keyed by workflow name. When   │
│    `discovery-sweep` finishes, parse ATTUNE_DS lines from      │
│    `run.lines` and persist                                     │
│    ~/.attune/ops/sweep-results/<scope-hash>.json (atomic)      │
│  - NEW (Phase 2): GET /workflows/discovery-sweep/results/<hash>│
│    (404 if no sweep has run for that scope)                    │
└────────┬───────────────────────────────────────────────────────┘
         │ stdout (already captured)
         ▼
┌────────────────────────────────────────────────────────────────┐
│  attune workflow run discovery-sweep --path <P> [--json]       │
│                                                                │
│  - existing: --json flag produces the final                    │
│    {queue, questions, rejected, metadata} blob.                │
│  - NEW (Phase 1, engine API): event_sink callback fires        │
│    source_started / source_finished / source_failed events.    │
│    In-process consumers (tests, future programmatic callers)   │
│    pass a sink; CLI invocations get None and unchanged output. │
│  - NEW (Phase 1b, stdout): when `ATTUNE_DS_EMIT=1` is set in   │
│    the environment, engine also writes one ATTUNE_DS line per  │
│    source event so the daemon (which captures stdout) can      │
│    parse it. CLI users — including pipe-to-file — see nothing  │
│    extra. (Env-var gate, not TTY detection: see decision #10.) │
└────────────────────────────────────────────────────────────────┘
```

**Resolved (Phase 0 audit):** No shared `/events` SSE stream and no
in-process workflow execution. The existing per-run `/runs/<id>/stream`
SSE carries the lines; dashboard parses `ATTUNE_DS` lines client-side
for live progress; daemon writes scope-keyed JSON at run-complete
for static chip counts.

---

## Engine event shape (in-process `event_sink` API)

The engine's `event_sink` callback receives plain dicts (not
dataclasses, to keep the surface minimal and JSON-serializable
without extra glue). The same shape doubles as the payload for
`ATTUNE_DS` stdout lines in Phase 1b.

## SSE event shape (deprecated — see audit)

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

> **Per Option A revision:** the `sweep_id` field on the dataclasses
> above remains in the engine's emitted event shape (engine doesn't
> know it's running inside a daemon vs. the CLI). Daemon-side
> callers pass `sweep_id=run_id` so the event shape stays
> compatible; CLI callers leave it `None` and the engine emits
> `sweep_id=None` (or omits the key — both behaviors are
> acceptable to downstream parsers).

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
  <scope-hash>.meta.json  # {path, depth, ts, run_id}
```

`<scope-hash> = sha256(canonicalized_scope_path)[:16]` so two
different paths get distinct files. Latest-only for v1 (history
deferred per the requirements DECIDE callout). Only the daemon
writes these files (Phase 2); the CLI never touches them, so the
race the original spec worried about can't happen.

## `ATTUNE_DS` stdout-line format (Phase 1b → Phase 2)

When `ATTUNE_DS_EMIT=1` is set in the environment, the engine
writes one line per source event in this shape:

```
ATTUNE_DS source_started   bug-predict     ts=2026-05-13T12:34:56+00:00
ATTUNE_DS source_finished  bug-predict     ts=2026-05-13T12:35:04+00:00 findings=7
ATTUNE_DS source_failed    security-audit  ts=2026-05-13T12:35:05+00:00 error=BudgetExceededError
ATTUNE_DS final            {<json of the SweepResult>}
```

Whitespace-separated, key=value tail. Parser is one regex per kind,
trivial. The `final` line carries the full JSON blob (the same one
`--json` already produces) so the daemon doesn't need to invoke
`--json` separately — the markdown path emits the JSON as a
sidecar line whenever it sees a non-TTY parent.

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

Clicking a chip navigates to a detail view scoped to the scope-hash
(not a run-id), with a bucket filter:

```
/workflows/discovery-sweep/results/<scope-hash>?bucket=queue
```

The detail page reads `<scope-hash>.json`, filters to the requested
bucket, and renders each Finding via a generic finding-row
component. This is *different from* `ops-runner-tier2`'s
`/runs/<run_id>` view (which shows captured stdout lines for one
specific run); the scope-keyed view shows the *current state* for
a scope regardless of which run produced it.

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
| Event-sink listener stalls block source execution | medium | NFR-2: event sink is fire-and-forget via `asyncio.create_task`; never `await`ed inline. |
| JSON storage grows unboundedly across many scopes | low | Latest-only-per-scope semantics cap storage; manual cleanup or LRU-eviction is post-v1. |
| Daemon parser is fragile to format drift in `ATTUNE_DS` lines | medium | One regex per event kind, locked behind a schema-version line emitted first: `ATTUNE_DS_VERSION 1`. Parser refuses unknown versions. |
| Dashboard caches stale chip counts across run boundaries | low | Workflow row's chip-count endpoint is uncached; sub-second fetch on each render. Phase 2 picks a sensible HTTP cache header. |
| Engine emits `ATTUNE_DS` lines into a TTY by accident | low | `sys.stdout.isatty()` gate at the call site; tested via `FORCE_COLOR`-style override toggling. |
| ~~ops-runner-tier2 Phase 2 ships in a shape that doesn't match this spec's assumptions~~ | resolved | The Phase 0 audit confirmed the actually-shipped shape and revised this design to fit it (Option A). |
