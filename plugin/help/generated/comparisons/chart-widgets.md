---
name: chart-widgets
source: content/features/chart-widgets.md
tags:
- charts
- widgets
- visualization
- communication
- widget
type: comparison
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

## Comparison

A number or two is prose; a handful of labelled rows is a markdown
table; shape across many points — a trend, a distribution, a
magnitude ranking — is a chart. And a chart that implies a decision
is a chart *plus* a decision form: the display member reports the
shape, the interactive member collects the answer. Versus writing
SVG or matplotlib code directly: the spec costs ~100 tokens, cannot
execute anything, and stays patchable for the rest of the session.
