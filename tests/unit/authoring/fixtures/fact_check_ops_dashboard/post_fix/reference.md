# Reference: Ops dashboard API

The ops dashboard exposes a small REST + SSE surface for
inspecting and (optionally) running workflows.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Home page |
| POST | `/workflows/{name}/run` | Start a workflow run |
| GET | `/runs/{run_id}` | Fetch a single run record as JSON |
| GET | `/runs/{run_id}/stream` | SSE stream for a live run |
| GET | `/api/runs/{workflow}` | List persisted runs for a workflow |

## Configuration

See [Configure the dashboard](../how-to/configure.md) for
details.
