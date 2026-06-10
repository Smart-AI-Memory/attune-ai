---
type: faq
name: ops-dashboard-faq
feature: ops-dashboard
depth: faq
generated_at: 2026-06-10T07:07:04.669090+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Ops Dashboard FAQ

## What is the ops dashboard?

A local operations dashboard that lets you run workflows against a specific feature scope, view persisted run history, chain workflows with a single click, and stream live logs over SSE. You start it with `python -m attune.ops` or via `attune ops` on the CLI.

## How do I start the dashboard?

Run `python -m attune.ops` (calls `main()`) or use the `attune ops` subcommand (registered by `add_subparser()`). Both block until you stop the server. By default the server listens on `127.0.0.1:8765`; you can change the host and port in `Config`.

## What does `Config` control?

`Config` is the central settings dataclass for the dashboard. Its key fields are:

| Field | What it controls |
|---|---|
| `project_root` | Root of your project tree |
| `attune_home` | Where attune reads and writes state |
| `host` / `port` | Server bind address (default `127.0.0.1:8765`) |
| `allow_run` | Whether workflow execution is permitted |
| `specs_roots` | Directories the candidate detector scans |
| `runs_retention_days` | How long persisted run history is kept (default 30) |
| `specs_candidates_enabled` | Whether spec-completion candidate detection is active |

Use `build_config()` to construct a `Config` rather than instantiating it directly.

## How does cost reporting work?

Call `fetch_summary()` to get account-level Anthropic API cost data. It returns a `(CostSummary | None, CostFetchError | None)` tuple. Pass `refresh=True` to bypass the in-memory cache. The `CostSummary` fields cover today, the last 7 days, month-to-date, and the last 30 days, plus breakdowns by day, model, and cost type. If the fetch fails, the `CostFetchError` tells you the `kind` and a human-readable `message`. The dashboard fetches from `https://api.anthropic.com/v1/organizations/cost_report` and requires an admin API key, which `load_admin_key()` resolves.

## How do I tell whether cost data is live or cached?

Check the `source` field on the returned `CostSummary`. It is either `'live'` or `'cached'`. The `fetched_at` field tells you when the data was last retrieved.

## What are spec-completion candidates?

When `specs_candidates_enabled` is `True` in your `Config`, `detect_candidates()` scans your `specs_roots` and returns a list of `Candidate` objects — specs that appear ready to move to the next phase based on file evidence. Each `Candidate` includes a `slug`, `path`, `current_status`, supporting `evidence`, and a `snapshot_hash`.

## How do I run the dashboard in tests?

Use `clear_cache()` (available in both `attune.ops.anthropic_cost` and the candidate-detector module) to reset in-memory caches between test cases. This is a test-only helper and is not part of the public API (`__all__` exports only `create_app`, `build_config`, and `Config`).

## Where are the source files?

All dashboard source lives under `src/attune/ops/`.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
