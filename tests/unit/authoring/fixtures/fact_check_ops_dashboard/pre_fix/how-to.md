# How to run the ops dashboard

This page walks through common operator tasks against the
attune ops dashboard.

## Start the dashboard

```bash
attune ops --port 8765
```

The dashboard binds to ``127.0.0.1`` by default.

## Run the dashboard in read-only mode

Use the `--allow-run` flag to allow workflow execution from the
dashboard UI. Operators who want a strict observation-only
deployment should omit it.

```bash
attune ops --port 8765 --allow-run
```

To run with workflow execution disabled, omit the flag.

## Bind to a specific interface

For development you might bind to all interfaces:

```bash
attune ops --host 0.0.0.0 --port 8765
```

## Persist run history

By default, runs are persisted under ``~/.attune/ops/runs/``.
See [Storage layout](./storage-layout.md) for details.

## More

- [Configure the dashboard](./configure.md)
- [Concept: Template design patterns](../concepts/template-design-patterns.md)
