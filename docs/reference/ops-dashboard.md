# Ops Dashboard CLI reference

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

## Description

`attune ops` starts a blocking local web server that serves the operations dashboard UI. It reads project and attune state from a `Config` object built from your project root, host, port, and environment defaults. The dashboard exposes workflow execution, telemetry summaries, spec browsing, and run history over HTTP. You can also invoke it directly as `python -m attune.ops`.

## Usage

```
attune ops [--host HOST] [--port PORT] [--project-root PATH] [--no-browser]
           [--read-only] [--specs-root PATH] [--trusted-host HOST]
           [--runs-retention-days DAYS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Interface address the dashboard server binds to |
| `--port PORT` | `8765` | TCP port the dashboard server listens on |
| `--project-root PATH` | cwd | Project directory to inspect |
| `--no-browser` | (off) | Don't auto-open a browser tab on startup |
| `--read-only` | (off) | Disable workflow execution from the dashboard. Runs are enabled by default; pass this flag to make the dashboard purely observational. |
| `--specs-root PATH` | — | Add a root directory to the federated spec listing; repeatable |
| `--trusted-host HOST` | — | Add a hostname (optionally `host:port`) to the `Host`-header allowlist; repeatable. Use when reaching the dashboard via a tunnel or reverse proxy. |
| `--runs-retention-days DAYS` | `30` | Delete persisted run files older than this many days at startup. Set to `0` to disable pruning. |

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

## Localhost security model

The dashboard is a single-user, same-machine tool. Its protection is
layered, not a multi-user auth system (network exposure is an explicit
non-goal):

1. **Loopback bind.** The server binds `127.0.0.1` by default — not
   reachable off the machine.
2. **Trusted-host middleware.** Requests whose `Host` header isn't on
   the allowlist are rejected (`--trusted-host` extends it).
3. **Read-only flag.** `--read-only` disables all mutation (workflow
   runs, status writes) — purely observational.
4. **Per-process client token.** Every mutating endpoint
   (`POST /workflows/{name}/run`, `PUT /api/specs/{slug}/{phase}/status`,
   the curator/help/dismiss mutations, …) requires an `X-Attune-Client`
   header matching a token minted at startup. The page reads the token
   once (a `<meta name="attune-client-token">` tag) and echoes it on
   mutating requests; `GET /api/session/token` exposes it for
   bootstrap. A client that never loaded the page — a stray `curl`, a
   browser extension, an a11y-traversing tool — gets `403` and cannot
   mutate state. The token resets each server run.

The token gate closes the "accidental mutation from a non-page client"
bug class (see `docs/specs/ops-mutating-endpoint-auth/`). It is *not* a
defense against a local attacker who can read process memory or the
page — that's out of scope for a localhost dev tool.

## Related commands

- `attune help-docs` — browse the help template library with optional `--tag` filters
- `python -m attune.ops` — standalone entry point; equivalent to `attune ops` without the main CLI parser

## See also

- [How-to: use the ops dashboard](../how-to/ops-dashboard.md) — quick start, programmatic API, and integration patterns
- [Tutorial: ops-dashboard walkthrough](../tutorials/ops-dashboard.md) — end-to-end first run with the workflow runner and scope picker
- [Architecture: ops-dashboard](../architecture/ops-dashboard.md) — design decisions and the data-flow diagram

<!-- attune-generated: source_hash=395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42 feature=ops-dashboard kind=cli-reference generated_at=2026-05-14 -->
