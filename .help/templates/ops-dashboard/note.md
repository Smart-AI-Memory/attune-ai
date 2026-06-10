---
type: note
name: ops-dashboard-note
feature: ops-dashboard
depth: note
generated_at: 2026-06-10T07:07:04.676642+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Note: ops dashboard

## What the ops dashboard is

`attune ops` is a local operations dashboard for the workflow OS. You run it as a blocking server process — either via `python -m attune.ops` (the `main()` entry point) or through the `attune` CLI after `add_subparser` registers the `ops` subcommand. The server address and port default to `127.0.0.1:8765`, both configurable through `Config`.

The dashboard provides a per-feature scope picker, persisted workflow run history, clickable workflow chaining, and live SSE log streaming. Run history is retained for `runs_retention_days` days (default: 30); the disk root for persisted runs is available at `Config.runs_dir`.

## Public surface

Three names are exported at the package boundary via `__all__`: `create_app`, `build_config`, and `Config`.

- **`create_app()`** — lazily imports the FastAPI application factory, so importing `attune` does not pull in FastAPI as a side effect.
- **`build_config()`** — lazily imports the config builder that produces a `Config` instance.
- **`Config`** — the central configuration dataclass. It locates `project_root`, `attune_home`, spec roots, and derived paths such as `telemetry_path`, `runs_dir`, `memory_dir`, `sessions_dir`, and `bulletin_dir`.

## Cost reporting

Anthropic API cost data is fetched from `https://api.anthropic.com/v1/organizations/cost_report` using API version `2023-06-01`. The result is a `CostSummary`, which carries today's spend, 7-day, month-to-date, and 30-day totals, plus breakdowns by day, model, and cost type. The `source` field indicates whether the data came from a live request or the in-memory cache.

`fetch_summary(*, refresh: bool = False)` returns a `(CostSummary | None, CostFetchError | None)` tuple. A `CostFetchError` pairs a `CostFetchErrorKind` with a human-readable `message`; it is returned rather than raised so callers can handle partial failures without exception handling.

`load_admin_key()` returns the admin API key or `None` if unavailable. `clear_cache()` empties the in-memory cache and is intended for use in tests only.

## Spec completion detection

When `Config.specs_candidates_enabled` is `True`, `detect_candidates(config)` scans the configured `specs_roots` and returns a list of `Candidate` dataclasses. Each `Candidate` carries a `slug`, a `path`, a `current_status`, a list of `evidence` strings, and a `snapshot_hash`. Dismissed candidates are tracked in `spec_completion_dismissed.json` under the `ops` subdirectory of `attune_home`.

## Source

`src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
