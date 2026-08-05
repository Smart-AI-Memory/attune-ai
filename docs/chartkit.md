# chartkit — charts the model specs, a sealed kernel renders

chartkit gives an LLM a cheap way to create and update charts: emit a
small declarative JSON spec (or a patch against one), and a sealed
~6.7KB JS kernel renders it as themable SVG. The model never writes
renderer code. Updates are JSON Merge Patch (RFC 7386), so changing a
title or swapping data costs tens of tokens, not a re-emitted widget.

## Create a chart

Call the `chart_render_widget` MCP tool with a `chart_id` and a full
`spec`, then pass the returned `html` to the widget surface
(`mcp__visualize__show_widget`).

```json
{
  "v": 1,
  "type": "bar",
  "data": [
    {"month": "Jan", "sales": 12},
    {"month": "Feb", "sales": 19}
  ],
  "encodings": {
    "x": {"field": "month", "type": "nominal"},
    "y": {"field": "sales", "type": "quantitative"}
  },
  "options": {"title": "Monthly sales"}
}
```

Chart types: `bar`, `line`, `scatter`, `area`, `heatmap`. Encoding
field types: `quantitative`, `nominal`, `temporal`. A `color` encoding
splits series (bar/line/scatter/area) or carries cell values (heatmap,
where it is required). `options`: `title`, `legend` (default true),
`stacked` (bar).

## Update a chart — send a patch, not a widget

The current spec persists per `chart_id` in session memory. To update,
send the same `chart_id` with a `patch` (RFC 7386: objects merge,
`null` deletes a key, arrays and scalars replace wholesale):

```jsonc
// patch — swap the data, keep everything else
{"data": [{"month": "Mar", "sales": 25}, {"month": "Apr", "sales": 31}]}
```

When persistence is unavailable the tool says so explicitly and asks
for a full `spec` — degradation is always legible, never silent.

## Named components

Semantic-role presets in `attune.widgets.chart_components` expand to
full specs server-side (`expand_component(name, args)`):

- `time_series` — line over temporal x; optional `series_field`.
- `comparison_bars` — nominal categories; optional `series_field`,
  `stacked`.
- `kpi_tile` — a metric as a current-vs-prior comparison bar (a
  dedicated numeric-tile mark is a kernel v2 candidate).
- `spec_progress` — spec task state as a status strip: one full-height
  stacked bar per task, colored by status (`done` / `in_flight` /
  `blocked` / anything else), legend as the key. Pass
  `tasks=[{"task": "T1", "status": "done"}, ...]`.

## The seal

The kernel lives in `src/attune/widgets/chartkit/` and is sealed:
kernel source imports nothing outside itself, nothing in attune
imports kernel internals, and the built artifact stays ≤ 20,480 bytes
— all three enforced in CI by `scripts/check_chartkit_boundary.py`.
Renderers build SVG via `createElementNS` and `textContent` only, so
spec strings can never execute. Colors and text use host CSS
variables (`--chartkit-c1..c6`, `--text-primary`, `--border`) and
adapt to light/dark automatically.

The spec contract is `spec.schema.json` (JS side) mirrored by
`attune.widgets.chart_spec` (server side); sync tests keep them
aligned. Extraction to a standalone package is deliberately a copy,
not surgery.
