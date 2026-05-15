---
type: quickstart
name: ops-dashboard-quickstart
feature: ops-dashboard
depth: quickstart
generated_at: 2026-05-14T14:43:23.571481+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Quickstart: ops dashboard

Start the local operations dashboard — a workflow runner with a per-feature scope picker, persisted run history, and live log streaming.

```bash
attune ops
```

The dashboard starts on `http://127.0.0.1:8765` by default.

## Prerequisites

- attune is installed and your project is cloned locally
- You are running the command from your project root

## Step 1: Build a config

```python
from attune.ops import build_config

config = build_config()
print(config.host, config.port)
# 127.0.0.1 8765
```

`build_config()` resolves your `project_root` and `attune_home` automatically. Override the defaults with keyword arguments — for example, `port=9000` or `allow_run=True` to enable workflow execution.

## Step 2: Launch the server

```bash
attune ops
```

Or from Python:

```python
from attune.ops import create_app

app = create_app()   # returns the FastAPI application object
```

The server blocks until you stop it. You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

## Step 3: Open the dashboard

Navigate to `http://127.0.0.1:8765` in your browser. The home page shows today's event count, today's cost, seven-day cost, and a daily cost sparkline drawn from your telemetry data.

To confirm the dashboard is reading your project's features, check that the scope picker lists entries from `.help/features.yaml` in your project root.

## Next:

Read the `ops-dashboard` concept page to understand how telemetry summaries, run retention, and trusted-host middleware fit together — say **"what is the ops dashboard?"** to open it.
