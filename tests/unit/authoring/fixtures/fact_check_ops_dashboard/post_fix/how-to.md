# How to run the ops dashboard

This page walks through common operator tasks against the
attune ops dashboard.

## Start the dashboard

```bash
attune ops --port 8765
```

The dashboard binds to ``127.0.0.1`` by default. Workflow
execution is disabled by default; pass ``--allow-run`` to
enable it.

## Allow workflow execution

```bash
attune ops --port 8765 --allow-run
```

To run with workflow execution disabled (the default), omit the
flag.

## Persist run history

By default, runs are persisted under ``~/.attune/ops/runs/``.
See [Storage layout](./storage-layout.md) for details.

## More

- [Configure the dashboard](./configure.md)
