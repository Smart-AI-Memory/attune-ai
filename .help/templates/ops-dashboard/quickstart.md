---
type: quickstart
name: ops-dashboard-quickstart
feature: ops-dashboard
depth: quickstart
generated_at: 2026-06-10T07:07:04.671892+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Quickstart: ops dashboard

Launch the local operations dashboard — a workflow runner with a per-feature scope picker, persisted run history, and live SSE log streaming.

```bash
python -m attune.ops
```

The server starts on `127.0.0.1:8765` by default. Open that address in your browser to see the dashboard.

## Step 1: Build a config

Use `build_config()` to wire up the project root and attune home before starting the server:

```python
from attune.ops import build_config

config = build_config()
print(config.host, config.port)  # 127.0.0.1  8765
```

Expected output:
```
127.0.0.1 8765
```

## Step 2: Create the app

Pass the config to `create_app()` to get a FastAPI application instance without pulling FastAPI into the import chain until you need it:

```python
from attune.ops import create_app

app = create_app()
```

## Step 3: Run the server from the CLI

Start the dashboard with the `ops` subcommand. `cmd_ops` returns `0` on clean exit:

```bash
python -m attune.ops
```

Navigate to `http://127.0.0.1:8765` in your browser. You should see the workflow list, scope picker, and run history panels.

## Step 4: Verify cost data loads

If you have an Anthropic admin key available, confirm the cost summary fetches correctly:

```python
from attune.ops.anthropic_cost import fetch_summary

summary, error = fetch_summary()
if summary:
    print(summary.today_usd, summary.source)
else:
    print(error.kind, error.message)
```

Expected output when the key is present and the fetch succeeds:
```
0.42 live
```

**Next:** Add `specs_roots` to your `Config` to enable the spec-completion candidate detector — set `specs_candidates_enabled=True` and call `detect_candidates(config)` to see which specs are ready to close out.
