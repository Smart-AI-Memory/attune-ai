# Architecture: Ops dashboard

A high-level view of how the dashboard's pieces connect.

## Components

The dashboard is composed of:

- A FastAPI application serving HTML pages + JSON endpoints
- A ``RunnerService`` managing subprocess execution + SSE streams
- A persistence layer writing run records to
  ``~/.attune/ops/runs/<workflow>/<id>.json``

## Run lifecycle

1. POST `/workflows/{name}/run` enqueues a workflow
2. The runner spawns ``attune workflow run <name>`` as a subprocess
3. stdout is captured line-by-line and broadcast over SSE
4. On completion, the run record is persisted
