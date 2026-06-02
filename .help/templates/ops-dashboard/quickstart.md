---
type: quickstart
name: ops-dashboard-quickstart
feature: ops-dashboard
depth: quickstart
generated_at: 2026-06-02T10:56:02.734874+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Quickstart: ops dashboard

Launch the local operations dashboard in your terminal with one command:

```bash
python -m attune.ops
```

The server starts on `127.0.0.1:8765` by default and blocks until you stop it.

## Prerequisites

- The project is cloned and installed locally
- Your shell is in the project root

## Step 1: Build a config

Use `build_config()` to point the dashboard at your project:

```python
from attune.ops import build_config

config = build_config()
print(config.host, config.port)  # 127.0.0.1 8765
```

Expected output:
```
127.0.0.1 8765
```

## Step 2: Create the app

Pass the config to `create_app()` to get the FastAPI application without pulling the framework into your import path until you need it:

```python
from attune.ops import create_app

app = create_app()
```

No output means success — the factory returned without error.

## Step 3: Start the server

Run the dashboard as a module. The process blocks and streams logs to your terminal:

```bash
python -m attune.ops
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

Open `http://127.0.0.1:8765` in your browser to see the workflow runner, scope picker, and run history.

## What you just did

- Built a `Config` that locates your project root and attune state directories
- Created the FastAPI app via the lazy `create_app()` factory
- Started the dashboard server on `127.0.0.1:8765`

## Next:

Read the `Config` dataclass fields — particularly `specs_roots`, `allow_run`, and `runs_retention_days` — to customize how the dashboard discovers specs and retains run history.
