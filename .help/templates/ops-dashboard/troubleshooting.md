---
type: troubleshooting
name: ops-dashboard-troubleshooting
feature: ops-dashboard
depth: troubleshooting
generated_at: 2026-05-14T14:43:23.566706+00:00
source_hash: 395f221f9a789d9b8851995c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Troubleshoot ops dashboard

The ops dashboard is a local server (`attune ops`) that serves a workflow runner with a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. Use this page when the dashboard fails to start, returns unexpected results, or behaves inconsistently.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Dashboard won't start | Confirm the port is free: `lsof -i :8765`. Check that `project_root` and `attune_home` resolve to existing paths. |
| `403` or connection refused from a remote host | Verify the client's `Host` header is listed in `trusted_hosts`. `TrustedHostMiddleware` rejects any host not on the allowlist. |
| KPI numbers on the home page are missing or zero | Check that `Config.telemetry_path` exists and contains valid event records. Confirm `last_event_at` is not `None` in `TelemetrySummary`. |
| Workflow list is empty or features don't appear | Confirm `.help/features.yaml` exists under `project_root`. Run `list_features(<project_root>)` directly in a Python shell to see what it returns. |
| Run history is missing | Check that `Config.runs_dir` exists on disk. The directory is not created until the first write. Confirm `runs_retention_days` (default `30`) hasn't pruned entries you expect to see. |
| SSE log stream stops or never starts | Check that `allow_run` is `True` in your config — the dashboard disables run execution when this flag is `False`. |
| Server binds to the wrong address | `host` defaults to `127.0.0.1`. If you need LAN access, pass `--host 0.0.0.0` and add the client hostname to `trusted_hosts`. |
| Intermittent failures after env changes | Check `ATTUNE_OPS_SWEEP_RESULTS` (`ENABLE_ENV`) and `ATTUNE_HOME`. Both are read at startup; stale values from a previous shell session can override your config. |

## Diagnosis steps

Work through these in order — earlier steps are faster and don't require code changes.

### 1. Reproduce with the minimal command

Run the dashboard directly to confirm the failure isn't caused by a wrapper or launcher:

```bash
python -m attune.ops
```

Or via the CLI:

```bash
attune ops
```

If the failure disappears, the problem is in how the surrounding context calls `cmd_ops()` or constructs its `argparse.Namespace`.

### 2. Inspect the resolved config

`build_config()` assembles every runtime path and flag. Print the config before the server starts to confirm all fields are what you expect:

```python
from attune.ops import build_config
cfg = build_config()
print(cfg)
```

Pay attention to `project_root`, `attune_home`, `host`, `port`, `allow_run`, `trusted_hosts`, and `runs_retention_days`. A wrong path here explains most startup and data-missing symptoms.

### 3. Check that key directories exist

The dashboard reads from several directories that may not exist until first use:

```bash
# Substitute your actual attune_home and project_root values
ls ~/.attune/runs/
ls ~/.attune/memory/
ls ~/.attune/sessions/
ls <project_root>/.help/features.yaml
```

`Config.runs_dir` and related paths are not created until the first write. Create them manually if needed:

```bash
mkdir -p ~/.attune/runs ~/.attune/memory ~/.attune/sessions
```

### 4. Enable debug logging

Re-run with Python logging set to `DEBUG` to surface config resolution, middleware decisions, and telemetry reads:

```bash
PYTHONASYNCIODEBUG=1 python -m attune.ops
```

Or add this before calling `create_app()` in your own code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 5. Run the related tests

```bash
pytest -k "ops" -v
```

If a test covers the failing path, its fixtures show you the minimal valid inputs. A newly failing test after a dependency upgrade points to an external change rather than a code bug.

## Common fixes

**Port already in use**
Change the port with `--port`:
```bash
attune ops --port 8766
```
Or free the existing process: `kill $(lsof -ti :8765)`.

**Host rejected by `TrustedHostMiddleware`**
Add the client's hostname or IP to `trusted_hosts` when calling `build_config()`, or pass it on the CLI if your launcher supports it. The middleware compares the `Host` request header exactly — `localhost` and `127.0.0.1` are treated as distinct values.

**Features not loading from `.help/features.yaml`**
Confirm the file exists and is valid YAML. Call `list_features()` to test parsing independently:
```python
from attune.ops.accessors import list_features
print(list_features("/path/to/project"))
```

**Runs pruned unexpectedly**
`runs_retention_days` defaults to `30`. If you need longer history, pass a higher value to `build_config()`:
```python
cfg = build_config(runs_retention_days=90)
```

**Sweep results not appearing**
The `ATTUNE_OPS_SWEEP_RESULTS` environment variable (`ENABLE_ENV`) must be set for sweep result data to be read. Results are stored under `ops/sweep-results/` within `attune_home`.

**Dependency version drift**
If the dashboard worked previously without a code change, check whether a recent `pip install` changed FastAPI or a related package:
```bash
pip show fastapi starlette
```
Pin versions in your lockfile if the upgrade introduced a regression.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
