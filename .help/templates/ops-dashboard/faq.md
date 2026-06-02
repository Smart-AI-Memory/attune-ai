---
type: faq
name: ops-dashboard-faq
feature: ops-dashboard
depth: faq
generated_at: 2026-06-02T10:56:02.731464+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Ops Dashboard FAQ

## What is the ops dashboard?

A local operations dashboard that lets you run workflows, pick a feature scope, stream live logs over SSE, and browse persisted run history. Run it with `python -m attune.ops` or via the `attune ops` CLI subcommand.

## How do I start the dashboard?

Call `cmd_ops(args)` or run `python -m attune.ops`. The server binds to `127.0.0.1:8765` by default. You can change the host and port through the `host` and `port` fields on `Config`.

## What does `Config` control?

`Config` is the central configuration dataclass. Its key fields include:

- `project_root` and `attune_home` — where the dashboard reads project and attune state from
- `host` / `port` — server bind address (defaults: `127.0.0.1` / `8765`)
- `allow_run` — whether workflow execution is permitted
- `specs_roots` — paths the candidate detector searches
- `runs_retention_days` — how long persisted run history is kept (default: `30`)
- `specs_candidates_enabled` — whether the spec-completion candidate detector is active

## How do I get the Anthropic cost data?

Call `fetch_summary(refresh=False)`. It returns a `(CostSummary | None, CostFetchError | None)` tuple. If the request fails, inspect the `CostFetchError` fields — `kind` (a `CostFetchErrorKind`) and `message` — to understand why. Pass `refresh=True` to bypass the in-memory cache and fetch a fresh result.

## What does `CostSummary` contain?

`CostSummary` holds account-level cost data fetched from the Anthropic admin cost report:

- `today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd` — pre-aggregated totals
- `by_day`, `by_model`, `by_cost_type` — breakdowns as lists of tuples
- `fetched_at` — when the data was retrieved
- `source` — either `'live'` or `'cached'`

## What are spec completion candidates?

Candidates are specs that the detector identifies as potentially complete. `detect_candidates(config)` returns a list of `Candidate` objects, each with a `slug`, `path`, `current_status`, `evidence` list, and `snapshot_hash`. The detector only runs when `specs_candidates_enabled` is `True` on your `Config`.

## How do I reset the cost cache in tests?

Call `clear_cache()`. This empties the in-memory cache and is intended for test use only.

## Do I need to import FastAPI directly?

No. `create_app()` uses a lazy import so that importing `attune` does not pull in FastAPI. Similarly, `build_config()` lazy-imports the config builder. Only the symbols in `__all__` — `create_app`, `build_config`, and `Config` — are part of the public API.

## Where are the source files?

All ops dashboard code lives under `src/attune/ops/`.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
