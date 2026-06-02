---
type: task
name: ops-dashboard-task
feature: ops-dashboard
depth: task
generated_at: 2026-06-02T10:56:02.703759+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Work with the ops dashboard

Use the ops dashboard when you need to start the local operations server, retrieve Anthropic cost data, or modify how the dashboard is configured and launched.

## Prerequisites

- Access to the project source code under `src/attune/ops/`
- An Anthropic admin API key if you intend to fetch cost reports (the key is read by `load_admin_key()`)

## Start the dashboard server

1. **Launch from the CLI.** Run the `attune ops` command. Internally this calls `cmd_ops(args)`, which starts the blocking FastAPI server and returns `0` on clean exit.

2. **Or run the module directly.** Execute `python -m attune.ops`. This calls `main()`, which is the standalone entry point equivalent to the CLI command.

3. **Confirm the server is running.** The process blocks and the terminal stays active. The server listens on the host and port defined in `Config` (`host` defaults to `127.0.0.1`, `port` defaults to `8765`). Open `http://127.0.0.1:8765` in a browser — the dashboard UI should load.

## Configure the dashboard

1. **Locate the `Config` dataclass** in `src/attune/ops/`. It controls every path and runtime option the dashboard reads at startup.

2. **Set the fields you need.** The most commonly adjusted fields are:

   | Field | Type | Default | Purpose |
   |---|---|---|---|
   | `host` | `str` | `'127.0.0.1'` | Interface the server binds to |
   | `port` | `int` | `8765` | Port the server listens on |
   | `allow_run` | `bool` | `False` | Permits workflow execution from the UI |
   | `specs_roots` | `tuple[Path, ...]` | `()` | Directories scanned for spec completion candidates |
   | `specs_candidates_enabled` | `bool` | `False` | Enables the spec completion candidate detector |
   | `runs_retention_days` | `int` | `30` | How long persisted run history is kept |
   | `trusted_hosts` | `tuple[str, ...]` | `()` | Hosts allowed to connect |

3. **Use `build_config()`** to construct a `Config` instance rather than instantiating `Config` directly. `build_config()` handles the lazy import of the config builder module so that importing `attune` does not pull in FastAPI.

## Fetch Anthropic cost data

1. **Check that an admin key is available.** Call `load_admin_key()`. It returns the key as a string, or `None` if the key is unavailable. If it returns `None`, cost fetching will fail.

2. **Call `fetch_summary()`** to retrieve the current cost data:

   ```python
   summary, error = fetch_summary()
   ```

   Pass `refresh=True` to bypass the in-memory cache and force a live request to `https://api.anthropic.com/v1/organizations/cost_report`.

3. **Inspect the result.** On success, `summary` is a `CostSummary` with these fields:

   | Field | Type | Description |
   |---|---|---|
   | `today_usd` | `float` | Spend for today |
   | `seven_day_usd` | `float` | Spend over the last 7 days |
   | `month_to_date_usd` | `float` | Spend month-to-date |
   | `thirty_day_usd` | `float` | Spend over the last 30 days |
   | `by_day` | `list[tuple[date, float]]` | Daily breakdown |
   | `by_model` | `list[tuple[str, float]]` | Breakdown by model |
   | `by_cost_type` | `list[tuple[str, float]]` | Breakdown by cost type |
   | `source` | `Literal['live', 'cached']` | Whether data came from a live call or cache |

   On failure, `error` is a `CostFetchError` with a `kind` (`CostFetchErrorKind`) and a `message` string describing what went wrong.

4. **Clear the cache if needed.** Call `clear_cache()` in `src/attune/ops/anthropic_cost.py` to empty the in-memory cache. This is intended for test use, but you can also call it manually to force the next `fetch_summary()` call to hit the API.

## Register the CLI subcommand

If you need to modify how `attune ops` is exposed on the command line, edit `add_subparser()` in `src/attune/ops/cli.py`. This function registers the `ops` subparser on the main attune CLI parser.

## Run the tests

Run the test suite targeting this module to catch regressions before they affect other developers:

```
pytest -k "ops"
```

## Verify success

- `cmd_ops()` exits with return code `0` on a clean shutdown.
- `fetch_summary()` returns a `CostSummary` where `source` is `'live'` after a `refresh=True` call.
- `load_admin_key()` returns a non-`None` string when the admin key is correctly configured.
- The dashboard UI is reachable at `http://<host>:<port>` (default `http://127.0.0.1:8765`) after `cmd_ops()` or `main()` starts the server.
