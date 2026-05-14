# Ops Dashboard CLI reference

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

## Description

`attune ops` starts a blocking local web server that serves the operations dashboard UI. It reads project and attune state from a `Config` object built from your project root, host, port, and environment defaults. The dashboard exposes workflow execution, telemetry summaries, spec browsing, and run history over HTTP. You can also invoke it directly as `python -m attune.ops`.

## Usage

```
attune ops [--host HOST] [--port PORT] [--allow-run] [--specs-root PATH]
           [--trusted-host HOST] [--runs-retention-days DAYS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Interface address the dashboard server binds to |
| `--port PORT` | `8765` | TCP port the dashboard server listens on |
| `--allow-run` | `False` | Permit the dashboard to trigger workflow runs |
| `--specs-root PATH` | — | Add a root directory to the federated spec listing; repeatable |
| `--trusted-host HOST` | — | Add a host to the `Host`-header allowlist; repeatable |
| `--runs-retention-days DAYS` | `30` | Delete persisted run files older than this many days |

## Output

`attune ops` is a blocking server process. On successful startup it prints the listening address and then runs until interrupted:

```
INFO:     Started server process [38201]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

The dashboard UI is then available in your browser at the printed URL. API responses from the server are JSON; for example, the home-page KPIs endpoint returns:

```json
{
  "today_events": 14,
  "today_cost": 0.032,
  "seven_day_cost": 0.187,
  "seven_day_savings": 0.054,
  "sparkline": [
    {"day": "2026-05-08", "events": 3, "cost": 0.021},
    {"day": "2026-05-09", "events": 11, "cost": 0.166}
  ]
}
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Server shut down cleanly (process interrupted or stopped normally) |
| `1` | Startup failed — for example, the port is already in use or a required path is invalid |

## Environment variables

| Variable | Description |
|----------|-------------|
| `ATTUNE_HOME` | Overrides the default attune home directory (`~/.attune`) |
| `ATTUNE_OPS_SWEEP_RESULTS` | When set to a non-empty value, enables persistence of discovery-sweep results under `<attune_home>/ops/sweep-results/` |

## Related commands

- `attune help-docs` — browse the full template library, including `--tag`-filtered searches across all 498 templates
- `python -m attune.ops` — standalone entry point; equivalent to `attune ops` without the main CLI parser

<!-- attune-generated: source_hash=395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42 feature=ops-dashboard kind=cli-reference generated_at=2026-05-14 -->
