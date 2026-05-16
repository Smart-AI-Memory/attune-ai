---
type: quickstart
name: ops-dashboard-quickstart
feature: ops-dashboard
depth: quickstart
generated_at: 2026-05-16T06:19:45.813641+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Quickstart: ops dashboard

Run the attune operations dashboard locally and open it in your browser.

```bash
attune ops
```

The dashboard starts on `http://127.0.0.1:8765` by default.

## Prerequisites

- attune is installed and your project is cloned locally
- You are running the command from your project root

## Step 1: Start the server

```bash
attune ops
```

You should see the server bind to `127.0.0.1:8765`. Open that address in your browser to reach the home page, which shows today's event count, cost KPIs, and a 7-day cost sparkline.

## Step 2: Configure host, port, or retention (optional)

To change defaults, build a config explicitly before launching:

```python
from attune.ops import build_config, create_app

config = build_config(
    host="0.0.0.0",
    port=9000,
    runs_retention_days=14,
)
app = create_app(config)
```

`build_config` resolves your project root and attune home directory automatically; override only what you need.

## Step 3: Explore the dashboard

| Page | What you see |
|---|---|
| Home | `HomeKpis` — today's events, 7-day cost, savings, sparkline |
| Workflows | `WorkflowEntry` list with stage counts and scope picker |
| Sessions | Summarised Claude Code sessions with resume prompts |
| Telemetry | Request totals, cost, savings broken down by workflow and day |

Run a workflow by selecting a feature scope from the picker and clicking its entry. Live log output streams over SSE.

## What you just did

- Started the attune ops dashboard with one command
- Learned where to override host, port, and retention settings
- Located the four main dashboard pages and the data each surfaces

## Next:

Read the ops-dashboard concept page — say **"what is the ops dashboard?"** — to understand how run persistence, trusted-host enforcement, and workflow chaining fit together.
