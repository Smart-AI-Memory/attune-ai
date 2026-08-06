---
type: quickstart
name: chart-widgets-quickstart
feature: chart-widgets
depth: quickstart
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

## Quickstart

Render a bar chart and hand the HTML to the widget surface:

```python
from attune.widgets.chart_widget_tool import render_chart_widget

result = render_chart_widget(
    "prs-weekly",
    spec={
        "v": 1,
        "type": "bar",
        "data": [
            {"week": "W27", "prs": 14},
            {"week": "W28", "prs": 22},
        ],
        "encodings": {
            "x": {"field": "week", "type": "nominal"},
            "y": {"field": "prs", "type": "quantitative"},
        },
        "options": {"title": "PRs merged per week"},
    },
)
result["success"]      # True
result["html"]         # kernel + spec, pass to show_widget
result["persistence"]  # "stored — next update may send a patch"
```

In a Claude Code session with the plugin, you never call this
yourself — ask for a chart and Claude drives the
`chart_render_widget` MCP tool. The hands-on narrative — ask, patch,
tour the types, export SVG — is the "Chart Widgets with Claude"
tutorial in the docs (`docs/tutorials/chart-widgets.md`).
