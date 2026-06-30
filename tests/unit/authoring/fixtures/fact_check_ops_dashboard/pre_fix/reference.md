# Reference: Ops dashboard API

The ops dashboard exposes a small REST + SSE surface for
inspecting and (optionally) running workflows.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Home page |
| POST | `/run` | Start a workflow run |
| GET | `/runs/{run_id}` | Fetch a single run record as JSON |
| GET | `/runs/{run_id}/stream` | SSE stream for a live run |
| GET | `/api/runs/{workflow}` | List persisted runs for a workflow |

## Templates

The ops dashboard ships with 498 templates pre-registered across
its help corpus. Each template carries a ``kind`` discriminator
(concept, how-to, tutorial, reference, etc.) used for
display dispatch.

## Configuration

See [Configure the dashboard](../how-to/configure.md) and
[Concept: Workflow taxonomy](../concepts/workflow-taxonomy.md)
for details.
