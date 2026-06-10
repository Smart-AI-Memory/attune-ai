---
type: task
name: ops-dashboard-task
feature: ops-dashboard
depth: task
generated_at: 2026-06-10T07:07:04.648249+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Work with the ops dashboard

Use the ops dashboard when you need to run workflows, browse per-feature scopes, inspect persisted run history, or monitor live cost data for your Anthropic account.

## Prerequisites

- Access to the project source code under `src/attune/ops/`
- An Anthropic admin API key if you intend to use cost reporting (returned by `load_admin_key()`)

## Start the dashboard server

1. **Launch the server from the CLI.**
   Run the following command to start the dashboard in blocking mode:

   ```
   python -m attune.ops
   ```

   This calls `main()`, which delegates to `cmd_ops()`. The server binds to `127.0.0.1:8765` by default (set by `Config.host` and `Config.port`).

2. **Verify the server is running.**
   `cmd_ops()` returns `0` on success. If the process is blocking and no error is printed, the dashboard is live at `http://127.0.0.1:8765`.

## Configure the dashboard

1. **Locate the `Config` dataclass** in `src/attune/ops/__init__.py`. It controls all runtime paths and feature flags.

2. **Set the fields relevant to your environment:**

   | Field | Default | Purpose |
   |---|---|---|
   | `host` | `'127.0.0.1'` | Address the server binds to |
   | `port` | `8765` | Port the server listens on |
   | `allow_run` | `False` | Permit workflow execution |
   | `specs_roots` | `()` | Paths scanned for spec files |
   | `trusted_hosts` | `()` | Hosts allowed to make requests |
   | `runs_retention_days` | `30` | How long persisted run history is kept |
   | `specs_candidates_enabled` | `False` | Enable spec completion candidate detection |

3. **Use `build_config()`** (exported from `src/attune/ops/__init__.py`) to construct a `Config` instance rather than instantiating it directly. This ensures all derived properties (`telemetry_path`, `runs_dir`, `memory_dir`, `sessions_dir`, `bulletin_dir`) resolve correctly.

## Fetch Anthropic cost data

1. **Check that an admin key is available.**
   Call `load_admin_key()` from `src/attune/ops/anthropic_cost.py`. It returns the key string or `None` if unavailable. The dashboard cannot retrieve cost data without a valid key.

2. **Call `fetch_summary()`** to retrieve account-level cost data:

   ```python
   summary, error = fetch_summary()
   ```

   - On success, `summary` is a `CostSummary` with fields `today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd`, `by_day`, `by_model`, `by_cost_type`, `fetched_at`, and `source`.
   - On failure, `error` is a `CostFetchError` with a `kind` (`CostFetchErrorKind`) and a `message` string.

3. **Force a cache refresh** by passing `refresh=True`:

   ```python
   summary, error = fetch_summary(refresh=True)
   ```

4. **Clear the in-memory cache** during testing by calling `clear_cache()` from `src/attune/ops/anthropic_cost.py`.

## Detect spec completion candidates

1. **Enable candidate detection** by setting `specs_candidates_enabled = True` in your `Config` and populating `specs_roots` with the paths to scan.

2. **Call `detect_candidates()`** from `src/attune/ops/spec_candidates.py`:

   ```python
   candidates = detect_candidates(config)
   ```

   Each returned `Candidate` has a `slug`, `path`, `current_status`, `evidence` list, and `snapshot_hash`.

## Register the CLI subcommand

If you need to extend or re-register the `ops` subcommand on the main `attune` CLI parser, call `add_subparser()` from `src/attune/ops/cli.py` and pass the parent `subparsers` action. This wires `cmd_ops()` as the handler for `attune ops`.

## Verify your changes

Run the ops-related tests to confirm nothing is broken:

```
pytest -k "ops"
```

A passing test suite with no new failures confirms that the dashboard server, cost-reporting, and candidate detection behave correctly. If you modified `Config`, also check that `build_config()` still returns a valid instance with all path properties resolving to accessible locations.
