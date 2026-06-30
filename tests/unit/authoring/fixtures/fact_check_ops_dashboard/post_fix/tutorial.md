# Tutorial: extending the ops dashboard

A walkthrough of adding a custom panel to the ops dashboard.

## Configure a custom panel

The dashboard reads custom panel definitions from
``.attune/ops/panels.json``. The schema is a list of panel
records; each record carries a ``title``, a ``kind`` discriminator,
and a body string.

A minimal example:

```json
{
  "panels": [
    {
      "title": "Build status",
      "kind": "callout",
      "body": "All systems green",
      "emphasis": "ok"
    }
  ]
}
```

The panel renders to the structured report area above the
process log when a run completes.

## See also

- [Storage layout](../how-to/storage-layout.md)
