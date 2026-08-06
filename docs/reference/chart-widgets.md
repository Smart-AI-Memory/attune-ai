# Chart Widgets

## Reference

### Public API

| Symbol | Purpose |
|--------|---------|
| `attune.widgets.chart_widget_tool.render_chart_widget(chart_id, spec=None, patch=None, backend=None)` | Create or update a chart; returns `{success, html, chart_id, persistence}` or `{success: False, error \| problems}`. |
| `attune.widgets.chart_widget_tool.merge_patch(target, patch)` | RFC 7386 JSON Merge Patch; mirrors the kernel's `applyPatch`. |
| `attune.widgets.chart_spec.validate_chart_spec(payload)` | Validate a raw spec dict into a `ChartSpec`; raises `ChartSpecError` with field-level problems. |
| `attune.widgets.chart_spec.ChartSpec` | The pydantic spec model (`v`, `type`, `data`, `encodings`, `options`). |
| `attune.widgets.chart_spec.ChartSpecError` | Carries `problems` — one message per field-level issue. |
| `attune.widgets.chart_components.expand_component(name, args)` | Expand a named component into a validated `ChartSpec`; `KeyError` lists valid names. |
| `attune.widgets.chart_components.COMPONENTS` | The component registry: `time_series`, `comparison_bars`, `kpi_tile`, `spec_progress`. |

### Chart types and options

| Type | Row shape | Type-specific rules |
|------|-----------|---------------------|
| `bar` | label + value | `options.stacked`, `options.horizontal`; `color` splits series |
| `line` / `scatter` / `area` | x + value | `color` splits series |
| `heatmap` | x + y + cell value | `encodings.color` required |
| `donut` / `treemap` | label + positive value | non-positive rows dropped |
| `box` | label + `min`, `q1`, `median`, `q3`, `max` | stats pre-computed |
| `waterfall` | label + signed delta | `options.total` adds a computed total bar |

`options`: `title` (str), `legend` (bool, default true), `stacked`
(bar only), `horizontal` (bar only), `total` (waterfall only —
enforced). `chart_id` must match `[A-Za-z0-9_-]{1,64}`.

### MCP tool

`chart_render_widget` — `chart_id` + `spec` to create or replace,
`chart_id` + `patch` to update; pass the returned `html` straight to
the widget surface (`mcp__visualize__show_widget`).

<!-- attune-generated: source_hash=71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb feature=chart-widgets kind=reference generated_at=2026-08-06 -->
