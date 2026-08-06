---
name: chart-widgets
source: content/features/chart-widgets.md
tags:
- charts
- widgets
- visualization
- communication
- widget
type: task
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

## Tasks

### Update a chart with a merge patch

Reuse the `chart_id`; send only what changed:

```python
result = render_chart_widget(
    "prs-weekly",
    patch={"options": {"title": "Merged PRs, weekly"}},
)
```

### Validate a spec without rendering

```python
from attune.widgets.chart_spec import ChartSpecError, validate_chart_spec

try:
    validate_chart_spec({"v": 1, "type": "bar", "data": []})
except ChartSpecError as exc:
    exc.problems  # ["data: List should have at least 1 item ..."]
```

### Expand a named component

Semantic-role presets expand server-side to full validated specs:

```python
from attune.widgets.chart_components import expand_component

spec = expand_component(
    "time_series",
    {
        "data": [{"date": "2026-08-01", "value": 3}],
        "title": "Daily runs",
    },
)
```

### Apply a merge patch in your own code

```python
from attune.widgets.chart_widget_tool import merge_patch

merged = merge_patch({"a": 1, "b": {"c": 2}}, {"b": {"c": None}, "d": 3})
# {"a": 1, "b": {}, "d": 3}
```
